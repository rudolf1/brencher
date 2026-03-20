# import asyncio
import json
import logging
import threading
from typing import Any, Generator

import docker
import pytest
import requests

from app import App
from conftest import EventuallyFn  # type: ignore[import-not-found]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestDockerContainer:

	@pytest.fixture(autouse=True)
	def setup_teardown(self) -> Generator[None, Any, None]:
		"""Set up and tear down test environment"""
		# Setup
		yield None

		# Teardown
		client = docker.from_env()
		container = client.containers.get("brencher_plain-container")
		container.stop(timeout=10)
		container.remove(force=True)
		logger.info("Container brencher_plain-container stopped and removed")

	@pytest.mark.asyncio
	async def test_start(self, eventually: EventuallyFn) -> None:  # type: ignore[no-any-unimported]
		logger.info(f"Starting")

		app = App(cli_env_ids_str="brencher_local1")
		# app.runWeb(5001)
		processing = threading.Thread(target=lambda: app.runWeb(5001), daemon=True)
		processing.start()

		eventually(
			lambda: requests.get("http://localhost:5001/state", timeout=5000).status_code == 200,
			20.0,
			1.0,
		)

		# await asyncio.sleep(5000)

		state_data = requests.get("http://localhost:5001/state", timeout=5000).json()
		logger.info(f"Application state: {json.dumps(state_data, indent=2)}")

		branches_data = requests.get("http://localhost:5001/branches", timeout=5000).json()
		logger.info(f"Application branches: {json.dumps(branches_data, indent=2)}")

		assert "brencher_local1" in state_data, "Missing 'brencher_local1' field in response"
		assert len(state_data["brencher_local1"]["pipeline"]) > 0, "Steps defined for 'brencher_local1' are empty"

		assert "brencher_local1" in branches_data, "Missing 'brencher_local1' field in response"
		assert len(branches_data["brencher_local1"]) > 0, "No branches found for 'brencher_local1'"

# TODO Verify DockerContainerDeploy step status is running and has correct image and ports
# {
#   "container_id": "213d161d7d08a0a4a45d666c2f31ad186a212e156ef310673cea24ff9eaa99d7",
#   "container_name": "brencher_plain-container",
#   "image": "brencher_plain:auto-0c711a54",
#   "status": "running",
#   "ports": {
#     "5001/tcp": [
#       {
#         "HostIp": "0.0.0.0",
#         "HostPort": "5002"
#       },
#       {
#         "HostIp": "::",
#         "HostPort": "5002"
#       }
#     ]
#   }
# }
