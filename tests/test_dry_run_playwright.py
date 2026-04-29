import logging
import threading
from typing import Any, Generator

import docker
import pytest
import requests
from playwright.sync_api import Page, sync_playwright
from app import App
from .conftest import EventuallyFn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

APP_PORT = 5003
APP_URL = f"http://localhost:{APP_PORT}"
ENV_ID = "brencher_local1"
CONTAINER_NAME = "brencher_plain-container"


def _get_pipeline_step(state_data: Any, env_id: str, step_name: str) -> Any:
    pipeline = state_data[env_id]["pipeline"]
    for step in pipeline:
        if step["name"] == step_name:
            return step
    return None

@pytest.mark.skip
class TestDryRunPlaywright:

    @pytest.fixture(autouse=True)
    def setup_teardown(self) -> Generator[None, Any, None]:
        yield None

        client = docker.from_env()
        containers = client.containers.list(filters={"name": CONTAINER_NAME}, all=True)
        for container in containers:
            container.stop(timeout=10)
            container.remove(force=True)
            logger.info(f"Container {CONTAINER_NAME} stopped and removed")

    def test_dry_run_prevents_deploy_until_disabled(self, eventually: EventuallyFn) -> None:
        # Start app with brencher_local1 with main branch pre-selected.
        # App starts with dry=True by default (SharedStateHolderInMemory default).
        app = App(cli_env_ids_str=f"{ENV_ID}:main")
        server_thread = threading.Thread(target=lambda: app.runWeb(APP_PORT), daemon=True)
        server_thread.start()

        # Wait for server to be up
        eventually(
            lambda: requests.get(f"{APP_URL}/state", timeout=5).status_code == 200,
            timeout=20.0,
            interval=1.0,
        )
        logger.info("Server is up")

        # Wait for the pipeline to stabilize with dry=True:
        # DockerContainerDeploy should return status="dry-run"
        def _deploy_is_dry_run() -> bool:
            state_data = requests.get(f"{APP_URL}/state", timeout=5).json()
            step = _get_pipeline_step(state_data, ENV_ID, "DockerContainerDeploy")
            if step is None or step.get("error"):
                return False
            return step["status"].get("status") == "dry-run"

        eventually(_deploy_is_dry_run, timeout=120.0, interval=2.0)
        logger.info("Pipeline is in dry-run mode")

        # Verify no real container was created
        docker_client = docker.from_env()
        real_containers = docker_client.containers.list(filters={"name": CONTAINER_NAME}, all=True)
        assert len(real_containers) == 0, "Container should NOT exist during dry run"

        # Open browser and click the dry-run button to disable dry run
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page: Page = browser.new_page()
            page.goto(APP_URL)
            page.wait_for_load_state("networkidle")

            # The dry-run button shows ⏸ when active (dry=True) and ▶ when disabled (dry=False).
            # It is inside the h3 heading for brencher_local1.
            dry_run_btn = page.locator(f'h3:has-text("{ENV_ID}") button.dry-run-btn')
            dry_run_btn.wait_for(state="visible", timeout=10000)

            # Verify button indicates dry-run is currently active (title contains "Dry run on")
            btn_title = dry_run_btn.get_attribute("title") or ""
            assert "Dry run on" in btn_title, f"Expected dry run to be active, got title: {btn_title!r}"
            logger.info(f"Dry-run button title before click: {btn_title!r}")

            # Click to disable dry run
            dry_run_btn.click()
            logger.info("Clicked dry-run button to disable dry run")

            # Wait for button to update to "Running" state (title no longer says "Dry run on")
            page.wait_for_function(
                """(envId) => {
                    const h3s = [...document.querySelectorAll('h3.env-title')];
                    const h3 = h3s.find(el => el.textContent.includes(envId));
                    if (!h3) return false;
                    const btn = h3.querySelector('button.dry-run-btn');
                    return btn && !btn.title.includes('Dry run on');
                }""",
                arg=ENV_ID,
                timeout=10000,
            )

            browser.close()

        # Wait for pipeline to re-run and actually deploy the container
        def _deploy_is_running() -> bool:
            state_data = requests.get(f"{APP_URL}/state", timeout=5).json()
            step = _get_pipeline_step(state_data, ENV_ID, "DockerContainerDeploy")
            if step is None or step.get("error"):
                return False
            return step["status"].get("status") == "running"

        eventually(_deploy_is_running, timeout=300.0, interval=5.0)
        logger.info("Container deployed and running after dry run disabled")

        # Final sanity: real container must exist and be running
        containers = docker_client.containers.list(filters={"name": CONTAINER_NAME})
        assert len(containers) == 1, "Container should exist and be running after deploy"
        assert containers[0].status == "running"
