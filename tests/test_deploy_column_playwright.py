import logging
import socket
import threading
import time
from typing import Any, Generator

import docker
import pytest
import requests

from app import App
from tests.configs import nginx
from tests.conftest import EventuallyFn, assert_equal
from tests.playwright_helper import brencher_page


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

APP_PORT = 5004
APP_URL = f"http://localhost:{APP_PORT}"
CONTAINER_NAME = "test_plain-container"
TARGET_BRANCH = "test/main"

_server_thread: threading.Thread | None = None


def _is_port_free(port: int, timeout: float = 5.0) -> bool:
    """Check if a port is available for binding."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if result != 0:
                return True
        except Exception:
            return True
        time.sleep(0.1)
    return False


def _get_state() -> dict[str, Any]:
    response = requests.get(f"{APP_URL}/state", timeout=5)
    assert response.status_code == 200, f"Expected status 200 from /state, got {response.status_code}"
    data = response.json()
    assert isinstance(data, dict), f"Expected dict from /state, got {type(data)}"
    return data


def _get_deployed_short_hash(env_id: str, branch: str) -> str:
    state = _get_state()
    env_state = state.get(env_id)
    assert isinstance(env_state, dict), f"No environment state for {env_id}: {state}"

    pipeline = env_state.get("pipeline")
    assert isinstance(pipeline, list), f"Pipeline is not list for {env_id}: {env_state}"

    step = next((p for p in pipeline if p.get("name") == "GitUnmerge"), None)
    assert isinstance(step, dict), f"GitUnmerge step not found in pipeline: {pipeline}"
    assert not bool(step.get("is_running")), f"GitUnmerge is still running: {step}"

    status = step.get("status")
    assert isinstance(status, dict), f"GitUnmerge status is not an object: {status}"

    columns = status.get("columns")
    assert isinstance(columns, dict), f"GitUnmerge columns missing: {status}"

    deployed = columns.get("Deployed")
    assert isinstance(deployed, dict), f"Deployed column missing: {columns}"

    value = deployed.get(branch)
    assert isinstance(value, str) and len(value) == 8, f"Deployed value for {branch} invalid: {value}"
    return value


def _pick_target_commit(env_id: str, branch: str) -> str:
    response = requests.get(f"{APP_URL}/branches", timeout=5)
    assert response.status_code == 200, f"Expected status 200 from /branches, got {response.status_code}"
    data = response.json()
    assert isinstance(data, dict), f"Expected dict from /branches, got {type(data)}"

    env_branches = data.get(env_id, {})
    assert isinstance(env_branches, dict), f"Expected env branch map for {env_id}, got {env_branches}"

    commits = env_branches.get(branch, [])
    assert isinstance(commits, list), f"Expected commits list for {branch}, got {commits}"

    for commit in commits:
        if not isinstance(commit, dict):
            continue
        hexsha = commit.get("hexsha")
        if isinstance(hexsha, str) and len(hexsha) >= 8:
            return hexsha

    raise AssertionError(f"Unable to find any commit for branch {branch}.")


def _assert_deployed_hash_available(env_id: str, branch: str) -> None:
    value = _get_deployed_short_hash(env_id, branch)
    assert isinstance(value, str) and len(value) == 8


class TestDeployColumnPlaywright:

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

        _is_port_free(APP_PORT, timeout=5.0)

        stop_and_remove_container()
        yield None

        if _server_thread and _server_thread.is_alive():
            _server_thread.join(timeout=2.0)
            logger.info("Waited for server thread to finish")

        _is_port_free(APP_PORT, timeout=5.0)
        stop_and_remove_container()
        _server_thread = None

    def test_deployed_column_updates_after_apply_changes_and_deploy(self, eventually: EventuallyFn) -> None:
        global _server_thread

        env = nginx.test_local1
        env.state.set_branches([(TARGET_BRANCH, "HEAD")])
        env.state.set_dry(True)

        app = App({env.id: env})
        _server_thread = threading.Thread(target=lambda: app.runWeb(APP_PORT), daemon=True)
        _server_thread.start()

        eventually(
            lambda: assert_equal(
                requests.get(f"{APP_URL}/state", timeout=5).status_code,
                200,
                "Server did not respond with 200 OK within timeout",
            ),
            timeout=20,
            interval=0.5,
        )

        target_commit = _pick_target_commit(env.id, TARGET_BRANCH)

        with brencher_page(APP_URL, env.id) as page:
            page.verify_dry_run_on()
            page.set_branch_desired_commit(TARGET_BRANCH, target_commit)
            page.verify_apply_changes_visible()
            page.set_apply_changes()

            eventually(lambda: page.verify_apply_changes_hidden(), timeout=20, interval=0.5)

            page.set_dry_run_off()
            eventually(lambda: page.verify_dry_run_off(), timeout=20, interval=0.5)
            page.click_refresh()

            eventually(
                lambda: _assert_deployed_hash_available(env.id, TARGET_BRANCH),
                timeout=90,
                interval=1.0,
            )

            deployed_short_hash = _get_deployed_short_hash(env.id, TARGET_BRANCH)

            eventually(
                lambda: page.verify_branch_column_value(TARGET_BRANCH, "Deployed", deployed_short_hash),
                timeout=30,
                interval=0.5,
            )
