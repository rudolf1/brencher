import logging
from contextlib import contextmanager
from typing import Generator

from playwright.sync_api import Locator, Page, sync_playwright


logger = logging.getLogger(__name__)


class BrencherPage:

    def __init__(self, page: Page, env_id: str, action_logger: logging.Logger) -> None:
        self._page = page
        self._env_id = env_id
        self._logger = action_logger

    def _dry_run_button(self) -> Locator:
        button = self._page.locator(f'h3:has-text("{self._env_id}") button.dry-run-btn')
        button.wait_for(state="visible", timeout=10000)
        return button

    def _apply_changes_button(self) -> Locator:
        button = self._page.locator("#apply-changes")
        button.wait_for(state="visible", timeout=10000)
        return button

    def _branch_checkbox(self, branch_name: str) -> Locator:
        checkbox = self._page.locator(
            f'input[type="checkbox"][data-env="{self._env_id}"][value="{branch_name}"]'
        )
        checkbox.wait_for(state="visible", timeout=10000)
        return checkbox

    def _desired_commit_select(self, branch_name: str) -> Locator:
        select = self._page.locator(
            f'select.desired-commit[data-env="{self._env_id}"][data-branch="{branch_name}"]'
        )
        select.wait_for(state="visible", timeout=10000)
        return select

    def verify_dry_run_on(self) -> None:
        btn_title = self._dry_run_button().get_attribute("title") or ""
        assert "Dry run on" in btn_title, f"Expected dry run to be active, got title: {btn_title!r}"
        self._logger.info(f"Dry-run button title before click: {btn_title!r}")

    def set_dry_run_off(self) -> None:
        self._dry_run_button().click()
        self._logger.info("Clicked dry-run button to disable dry run")

    def set_branch_unselected(self, branch_name: str) -> None:
        checkbox = self._branch_checkbox(branch_name)
        if checkbox.is_checked():
            checkbox.uncheck()
            self._logger.info("Unchecked branch '%s'", branch_name)

    def set_branch_desired_commit(self, branch_name: str, commit_hash: str) -> None:
        self._desired_commit_select(branch_name).select_option(value=commit_hash)
        self._logger.info("Set desired commit for branch '%s' to '%s'", branch_name, commit_hash)

    def set_apply_changes(self) -> None:
        self._apply_changes_button().click()
        self._logger.info("Clicked Apply Changes")

    def set_simulate_branch_state_conflict(self) -> None:
        self._page.evaluate(
            """({ envId }) => {
                const currentToken =
                    (typeof serverTokenByEnv !== 'undefined' && serverTokenByEnv[envId])
                        ? serverTokenByEnv[envId]
                        : 'server-token';
                const staleToken = `${currentToken}-stale`;
                if (typeof serverTokenByEnv !== 'undefined') {
                    // Simulate stale client-side token so next apply uses an outdated value.
                    serverTokenByEnv[envId] = staleToken;
                }
            }""",
            {
                "envId": self._env_id,
            },
        )
        self._logger.info("Set stale branch token for '%s'", self._env_id)

    def click_refresh(self) -> None:
        self._page.locator("#refresh-branches").click()
        self._logger.info("Clicked refresh button")

    def verify_dry_run_off(self) -> None:
        self._page.wait_for_function(
            """(targetEnvId) => {
                const h3s = [...document.querySelectorAll('h3.env-title')];
                const h3 = h3s.find(el => el.textContent.includes(targetEnvId));
                if (!h3) return false;
                const btn = h3.querySelector('button.dry-run-btn');
                return btn && !btn.title.includes('Dry run on');
            }""",
            arg=self._env_id,
            timeout=10000,
        )

    def verify_apply_changes_visible(self) -> None:
        self._page.wait_for_function(
            """() => {
                const btn = document.querySelector('#apply-changes');
                return !!btn && !btn.classList.contains('hidden');
            }""",
            timeout=10000,
        )
        self._logger.info("Apply Changes button is visible")

    def verify_apply_changes_hidden(self) -> None:
        self._page.wait_for_function(
            """() => {
                const btn = document.querySelector('#apply-changes');
                return !!btn && btn.classList.contains('hidden');
            }""",
            timeout=10000,
        )
        self._logger.info("Apply Changes button is hidden")

    def verify_branch_column_value(self, branch_name: str, column_name: str, expected_value: str, timeout_ms: int = 10000) -> None:
        self._page.wait_for_function(
            """({ envId, branchName, columnName, expectedValue }) => {
                const row = document.querySelector(`tr.branch-row[data-env="${envId}"][data-branch="${branchName}"]`);
                if (!row) return false;
                const table = row.closest('table.branches-table');
                if (!table) return false;
                const headers = [...table.querySelectorAll('thead th')].map(th => (th.textContent || '').trim());
                const colIdx = headers.indexOf(columnName);
                if (colIdx === -1) return false;
                const cells = [...row.querySelectorAll('td')];
                if (cells.length <= colIdx) return false;
                return ((cells[colIdx].textContent || '').trim() === expectedValue);
            }""",
            arg={
                "envId": self._env_id,
                "branchName": branch_name,
                "columnName": column_name,
                "expectedValue": expected_value,
            },
            timeout=timeout_ms,
        )
        self._logger.info(
            "Verified column '%s' for branch '%s' equals '%s'",
            column_name,
            branch_name,
            expected_value,
        )

    def verify_pipeline_step_status(self, step_name: str, expected_status: str, timeout_ms: int = 10000) -> None:
        """
        Verify that a pipeline step reaches the expected status by polling the page DOM.
        
        Args:
            step_name: Name of the pipeline step (e.g., "DockerContainerDeploy")
            expected_status: Expected status value ("running", "ok", "error", or "dry-run")
            timeout_ms: Timeout in milliseconds (default 10000)
        """
        # JavaScript to check pipeline step status
        js_check = """(stepName, expectedStatus) => {
            const jobItems = document.querySelectorAll('.job-item');
            for (const item of jobItems) {
                const headerText = item.querySelector('.job-header')?.textContent || '';
                if (headerText.includes(stepName)) {
                    const spinner = item.querySelector('.step-spinner');
                    const errorIndicator = item.querySelector('span[title="Error"]');
                    
                    if (expectedStatus === 'running') {
                        return spinner !== null;
                    } else if (expectedStatus === 'ok') {
                        return spinner === null && errorIndicator === null;
                    } else if (expectedStatus === 'error') {
                        return errorIndicator !== null;
                    } else if (expectedStatus === 'dry-run') {
                        // For dry-run, check the spoiler content
                        const spoiler = item.querySelector('.job-spoiler');
                        if (spoiler && spoiler.style.display !== 'none') {
                            const statusText = spoiler.textContent;
                            return statusText.includes('dry-run') || statusText.includes('dry_run');
                        }
                        return false;
                    }
                }
            }
            return false;
        }"""
        
        self._page.wait_for_function(
            js_check,
            arg=[step_name, expected_status],
            timeout=timeout_ms,
        )
        self._logger.info(f"Pipeline step '{step_name}' reached status '{expected_status}'")


@contextmanager
def brencher_page(
    app_link: str,
    env_id: str,
    action_logger: logging.Logger | None = None,
) -> Generator[BrencherPage, None, None]:
    active_logger = action_logger or logger
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(app_link)
        page.wait_for_load_state("networkidle")
        try:
            yield BrencherPage(page, env_id, active_logger)
        finally:
            browser.close()
