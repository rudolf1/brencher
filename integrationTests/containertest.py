import sys
from pathlib import Path

# Add backend to path so we can import modules
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
	sys.path.insert(0, str(backend_path))

import pytest
import logging
import asyncio
from app import App
import threading
import docker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestDockerContainer:

	@pytest.fixture(autouse=True)
	def setup_teardown(self):
		"""Set up and tear down test environment"""
		# Setup
		yield

		# Teardown
		client = docker.from_env()
		container = client.containers.get("brencher_plain-container")
		container.stop(timeout=10)
		container.remove(force=True)
		logger.info("Container brencher_plain-container stopped and removed")

	@pytest.mark.asyncio
	async def test_start(self) -> None:

		logger.info(f"Starting")

		app = App(cli_env_ids_str="brencher_local1")
		# app.runWeb(5001)
		processing = threading.Thread(target=lambda: app.runWeb(5001), daemon = True)
		processing.start()


		await asyncio.sleep(5)
		# Verify container is still running
		# Verify application is responding on /state endpoint
		import requests

		response = requests.get("http://localhost:5001/state", timeout=5000)
		assert response.status_code == 200, "Failed to get /state endpoint"
		state_data = response.json()

		assert "brencher_local1" in state_data, "Missing 'brencher_local1' field in response"
		logger.info(f"Application state: {state_data}")

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
		# await asyncio.sleep(5000)

