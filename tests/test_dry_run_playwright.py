import logging
import threading
from typing import Any, Callable, Generator

import docker
import pytest
import requests
from app import App
from .conftest import EventuallyFn
from .playwright_helper import brencher_page
from configs import brencher_local1

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

APP_PORT = 5003
APP_URL = f"http://localhost:{APP_PORT}"
ENV_ID = "brencher_local1"
CONTAINER_NAME = "brencher_plain-container"


def _check_state(url: str, predicate: Callable[[Any], bool]) -> bool:
    state_data = requests.get(f"{url}/state", timeout=5).json()
    return predicate(state_data)

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
        # Start app with brencher_local1 with main branch pre-selected and dry mode on.
        env = brencher_local1.brencher_local1
        env.state.set_branches([("main", "HEAD")])
        env.state.set_dry(True)
        app = App({"brencher_local1": env})
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
        eventually(
            lambda: _check_state(APP_URL, lambda s: next(
                p for p in s[ENV_ID]["pipeline"] if p["name"] == "DockerContainerDeploy"
            )["status"].get("status") == "dry-run"),
            timeout=120.0,
            interval=2.0,
        )
        logger.info("Pipeline is in dry-run mode")

        # Verify no real container was created
        docker_client = docker.from_env()
        real_containers = docker_client.containers.list(filters={"name": CONTAINER_NAME}, all=True)
        assert len(real_containers) == 0, "Container should NOT exist during dry run"

        # Open browser and disable dry run from the UI.
        with brencher_page(APP_URL) as page:
            page.verify_dry_run_on()
            page.set_dry_run_off()
            page.verify_dry_run_off()
            page.click_refresh()

        # Wait for pipeline to re-run and actually deploy the container
        eventually(
            lambda: _check_state(APP_URL, lambda s: next(
                p for p in s[ENV_ID]["pipeline"] if p["name"] == "DockerContainerDeploy"
            )["status"].get("status") == "running"),
            timeout=300.0,
            interval=5.0,
        )
        logger.info("Container deployed and running after dry run disabled")

        # Final sanity: real container must exist and be running
        containers = docker_client.containers.list(filters={"name": CONTAINER_NAME})
        assert len(containers) == 1, "Container should exist and be running after deploy"
        assert containers[0].status == "running"
