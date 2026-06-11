import logging
import threading
import time
from typing import Any, Generator

import docker
import pytest
import requests
import socket

from app import App
from tests.configs import nginx
from tests.conftest import EventuallyFn, assert_equal
from tests.playwright_helper import brencher_page


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


class TestApplyChangesPlaywright:

    @pytest.fixture(autouse=True)
    def setup_teardown(self) -> Generator[None, Any, None]:
        global _server_thread
        
        def stop_and_remove_container() -> None:
            client = docker.from_env()
            try:
                container = client.containers.get(CONTAINER_NAME)
                container.stop(timeout=10)
                container.remove(force=True)
                logger.info("Container %s stopped and removed", CONTAINER_NAME)
            except Exception:
                logger.info("Container %s not found, no need to stop/remove", CONTAINER_NAME)

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

    def test_apply_button_hides_after_apply_branch_change(self, eventually: EventuallyFn) -> None:
        global _server_thread
        
        # Start app with one pre-selected branch so unchecking creates pending changes.
        env = nginx.test_local1
        env.state.set_branches([("test/main", "HEAD")])
        env.state.set_dry(True)
        app = App({env.id: env})
        _server_thread = threading.Thread(target=lambda: app.runWeb(APP_PORT), daemon=True)
        _server_thread.start()

        eventually(
            lambda: assert_equal(
                requests.get(f"{APP_URL}/state", timeout=5).status_code,
                200,
                "Server did not respond with 200 OK within timeout",
            )
        )

        with brencher_page(APP_URL, env.id) as page:
            page.set_branch_unselected("test/main")
            page.verify_apply_changes_visible()
            page.set_apply_changes()
            eventually(lambda: page.verify_apply_changes_hidden(), timeout=10, interval=0.5)

    def test_apply_button_reappears_on_branch_conflict(self, eventually: EventuallyFn) -> None:
        global _server_thread
        
        env = nginx.test_local1
        env.state.set_branches([("test/main", "HEAD")])
        env.state.set_dry(True)
        app = App({env.id: env})
        _server_thread = threading.Thread(target=lambda: app.runWeb(APP_PORT), daemon=True)
        _server_thread.start()

        eventually(
            lambda: assert_equal(
                requests.get(f"{APP_URL}/state", timeout=5).status_code,
                200,
                "Server did not respond with 200 OK within timeout",
            )
        )

        with brencher_page(APP_URL, env.id) as page:
            page.set_branch_unselected("test/main")
            page.verify_apply_changes_visible()
            # Set stale token in client JS object so backend returns a real conflict on apply.
            page.set_simulate_branch_state_conflict()
            page.set_apply_changes()
            eventually(lambda: page.verify_apply_changes_visible(), timeout=10, interval=0.5)
