import logging
import threading
import time
import socket
from typing import Any, Callable, Generator, TypeVar

import docker
import pytest
import requests
from app import App
from .conftest import EventuallyFn, assert_equal, check_state
from .playwright_helper import brencher_page
from tests.configs import nginx

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

APP_PORT = 5003
APP_URL = f"http://localhost:{APP_PORT}"
CONTAINER_NAME = "test_plain-container"

# Module-level reference to server thread to ensure proper cleanup
_server_thread: threading.Thread | None = None


def _is_port_free(port: int, timeout: float = 5.0) -> bool:
    """Check if a port is available for binding."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result != 0:
                return True
        except Exception:
            return True
        time.sleep(0.1)
    return False

class TestDryRunPlaywright:

    @pytest.fixture(autouse=True)
    def setup_teardown(self) -> Generator[None, Any, None]:
        global _server_thread
        
        def stop_and_remove_container() -> None:
            client = docker.from_env()
            try:
                container = client.containers.get(CONTAINER_NAME)
                container.stop(timeout=10)
                container.remove(force=True)
                logger.info(f"Container {CONTAINER_NAME} stopped and removed")
            except Exception:
                logger.info(f"Container {CONTAINER_NAME} not found, no need to stop/remove")
        
        # Ensure port is free before starting
        _is_port_free(APP_PORT, timeout=5.0)
        
        stop_and_remove_container()
        yield None
        
        # Clean up server thread
        if _server_thread and _server_thread.is_alive():
            _server_thread.join(timeout=2.0)
            logger.info("Waited for server thread to finish")
        
        # Ensure port is free after test
        _is_port_free(APP_PORT, timeout=5.0)
        
        stop_and_remove_container()
        _server_thread = None


    def test_dry_run_prevents_deploy_until_disabled(self, eventually: EventuallyFn) -> None:
        global _server_thread
        
        # Start app with nginx_local1 with main branch pre-selected and dry mode on.
        env = nginx.test_local1
        env.state.set_branches([("test/main", "HEAD")])
        env.state.set_dry(True)
        app = App({env.id: env})
        _server_thread = threading.Thread(target=lambda: app.runWeb(APP_PORT), daemon=True)
        _server_thread.start()

        # Wait for server to be up
        eventually(lambda: assert_equal(requests.get(f"{APP_URL}/state", timeout=5).status_code, 200, "Server did not respond with 200 OK within timeout"))
        logger.info("Server is up")

        # Wait for the pipeline to stabilize with dry=True:
        # DockerContainerDeploy should return status="dry-run"
        with brencher_page(APP_URL, env.id) as page:
            eventually(
                lambda: check_state(APP_URL, lambda s: assert_equal(next(
                    p for p in s[env.id]["pipeline"] if p["name"] == "SharedStateHolderInMemory"
                )["status"]['dry'], True, "Pipeline step status is not 'running'")),
            )

            # page.verify_pipeline_step_status("DockerContainerDeploy", "dry-run")
            logger.info("Pipeline is in dry-run mode")

            # Verify no real container was created
            docker_client = docker.from_env()
            real_containers = docker_client.containers.list(filters={"name": CONTAINER_NAME}, all=True)
            assert len(real_containers) == 0, "Container should NOT exist during dry run"

            # Disable dry run from the UI.
            page.verify_dry_run_on()
            page.set_dry_run_off()
            page.verify_dry_run_off()
            page.click_refresh()  # TODO Remove it

            # Wait for pipeline to re-run and actually deploy the container
            eventually(
                lambda: check_state(APP_URL, lambda s: assert_equal(next(
                    p for p in s[env.id]["pipeline"] if p["name"] =="SharedStateHolderInMemory"
                )["status"]['dry'], False, "Pipeline step status is not 'running'")),
            )
            # Wait for pipeline to re-run and actually deploy the container
            eventually(
                lambda: check_state(APP_URL, lambda s: assert_equal({p["name"] for p in s[env.id]["pipeline"] if bool(p['is_running'])}, set(), "Pipeline still running")),
                timeout=20,
                interval=1.0,
            )
            # page.verify_pipeline_step_status("DockerContainerDeploy", "running")
        logger.info("Container deployed and running after dry run disabled")

        # Final sanity: real container must exist and be running
        containers = docker_client.containers.list(filters={"name": CONTAINER_NAME})
        assert len(containers) == 1, "Container should exist and be running after deploy"
        assert containers[0].status == "running"
