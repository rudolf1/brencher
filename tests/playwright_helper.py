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

    def verify_dry_run_on(self) -> None:
        btn_title = self._dry_run_button().get_attribute("title") or ""
        assert "Dry run on" in btn_title, f"Expected dry run to be active, got title: {btn_title!r}"
        self._logger.info(f"Dry-run button title before click: {btn_title!r}")

    def set_dry_run_off(self) -> None:
        self._dry_run_button().click()
        self._logger.info("Clicked dry-run button to disable dry run")

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


@contextmanager
def brencher_page(
    app_link: str,
    env_id: str = "brencher_local1",
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
