import hashlib
import logging
import os
from dataclasses import dataclass
from typing import List, Dict, Callable, Any, Optional, cast

import docker
from docker.models.containers import Container
from docker.models.images import Image

from enironment import AbstractStep
from steps.git import CheckoutMerged

logger = logging.getLogger(__name__)


@dataclass
class DockerImageBuildResult:
	"""Result of building a Docker image"""
	image_name: str
	image_tag: str
	full_image: str
# build_logs: List[str]


class DockerImageBuild(AbstractStep[DockerImageBuildResult]):
	"""Build a single Docker image from a Dockerfile"""

	def __init__(self,
	             wd: CheckoutMerged,
	             dockerfile_path: str,
	             image_name: str,
	             image_tag: Callable[[], str] | str,
	             build_context: Optional[str] = None,
	             build_args: Optional[Dict[str, str]] = None,
	             nocache: bool = False,
	             **kwargs: Any) -> None:
		super().__init__(**kwargs)
		self.wd = wd
		self.dockerfile_path = dockerfile_path
		self.image_name = image_name
		self.image_tag = image_tag
		self.build_context = build_context or "."
		self.build_args = build_args or {}
		self.nocache = nocache

	def progress(self) -> DockerImageBuildResult:
		"""Build the Docker image"""
		wd_path = self.wd.progress().wd

		# Construct full image name with tag
		tag = self.image_tag
		if callable(tag):
			tag = tag()
		full_image = f"{self.image_name}:{tag}"

		# Build context path (relative to working directory)
		build_context_path = os.path.join(wd_path, self.build_context)
		dockerfile_absolute = os.path.join(wd_path, self.dockerfile_path)

		logger.info(f"Building Docker image: {full_image}")
		logger.info(f"  Dockerfile: {dockerfile_absolute}")
		logger.info(f"  Build context: {build_context_path}")
		logger.info(f"  Build args: {self.build_args}")

		client = docker.DockerClient(base_url='unix://var/run/docker.sock')

		# Check if image already exists locally
		existing_image = client.images.list(full_image)
		if len(existing_image) > 0 and not self.nocache:
			logger.info(f"Image {full_image} already exists locally with ID: {existing_image}")
			build_logs: List[str] = []
		else:
			# Build the image
			build_logs = []
			image, logs = client.images.build(
				path=build_context_path,
				dockerfile=os.path.relpath(dockerfile_absolute, build_context_path),
				tag=full_image,
				buildargs=self.build_args,
				nocache=self.nocache,
				rm=True
			)

			# for log in logs:
			# 	if 'stream' in log:
			# 		log_msg = log['stream'].strip()
			# 		if log_msg:
			# 			logger.debug(log_msg)
			# 			build_logs.append(log_msg)

			logger.info(f"Successfully built image: {full_image} (ID: {image.id})")

		return DockerImageBuildResult(
			image_name=self.image_name,
			image_tag=tag,
			full_image=full_image,
			# build_logs=build_logs
		)


@dataclass
class DockerContainerCheckResult:
	"""Result of checking a Docker container"""
	container_name: str
	exists: bool
	status: str
	image: str
	version: str
	created: str
	started: str
	ports: Dict[str, Any]
	health: Optional[str]


class DockerContainerCheck(AbstractStep[Dict[str, DockerContainerCheckResult]]):
	"""Check if a Docker container exists and get its status"""

	def __init__(self,
	             container_name: str,
	             **kwargs: Any) -> None:
		super().__init__(**kwargs)
		self.container_name = container_name

	def progress(self) -> Dict[str, DockerContainerCheckResult]:
		"""Check the Docker container status"""
		logger.info(f"Checking container: {self.container_name}")

		client = docker.DockerClient(base_url='unix://var/run/docker.sock')

		container = (containers[0] if (
			containers := client.containers.list(filters={"name": self.container_name}, all=True)) else None)

		if container is None:
			raise BaseException(f"No deployment found {self.container_name}")
		health_status = None
		if container.attrs.get('State', {}).get('Health'):
			health_status = container.attrs['State']['Health'].get('Status')

		image: Image | None = container.image
		if image is None:
			raise BaseException(f"Container {self.container_name} has no image information")
		return {
			self.container_name: DockerContainerCheckResult(
				container_name=self.container_name,
				exists=True,
				status=container.status,
				image=(image.tags[0] if image.tags else image.id) or "unknown",
				version=image.tags[0].split(":")[1] if image.tags else "unknown",
				created=container.attrs['Created'],
				started=container.attrs['State'].get('StartedAt', ''),
				ports=container.ports,
				health=health_status
			)
		}


@dataclass
class DockerContainerDeployResult:
	"""Result of deploying a Docker container"""
	container_id: str
	container_name: str
	image: str
	status: str
	ports: Dict[str, Any]


class DockerContainerDeploy(AbstractStep[DockerContainerDeployResult]):
	"""Deploy a single Docker container"""

	def __init__(self,
	             image_build: DockerImageBuild,
	             container_name: str,
	             ports: Optional[Dict[str, int]] = None,
	             environment: Optional[Dict[str, str]] = None,
	             volumes: Optional[Dict[str, Dict[str, str]]] = None,
	             network: Optional[str] = None,
	             restart_policy: Optional[Dict[str, Any]] = None,
	             **kwargs: Any) -> None:
		super().__init__(**kwargs)
		self.image_build = image_build
		self.container_name = container_name
		self.ports = ports or {}
		self.environment = environment or {}
		self.volumes = volumes or {}
		self.network = network
		self.restart_policy = restart_policy or {"Name": "unless-stopped"}

	def _get_config_hash(self) -> str:
		config_str = f"{sorted(self.ports.items())}|{sorted(self.environment.items())}|{sorted(self.volumes.items())}|{self.network}|{self.restart_policy}"
		return hashlib.sha1(config_str.encode()).hexdigest()[:12]

	def _check_container_match(self, existing_container: Container, full_image: str) -> str | None:
		if existing_container.image and existing_container.image.tags and full_image not in existing_container.image.tags:
			return "Version mismatch"
		current_hash = existing_container.labels["config_hash"] if "config_hash" in existing_container.labels else None
		if self._get_config_hash() != current_hash:
			return "Config hash mismatch"
		return None

	def progress(self) -> DockerContainerDeployResult:
		"""Deploy the Docker container"""
		# First, ensure the image is built
		build_result = self.image_build.progress()
		full_image = build_result.full_image

		logger.info(f"Deploying container: {self.container_name}")
		logger.info(f"  Image: {full_image}")
		logger.info(f"  Ports: {self.ports}")
		logger.info(f"  Environment: {list(self.environment.keys())}")
		logger.info(f"  Volumes: {self.volumes}")

		if self.env.dry:
			logger.info(f"DRY RUN: Would deploy container {self.container_name}")
			return DockerContainerDeployResult(
				container_id="dry-run",
				container_name=self.container_name,
				image=full_image,
				status="dry-run",
				ports=self.ports
			)

		client = docker.DockerClient(base_url='unix://var/run/docker.sock')

		existing_container = (containers[0] if (
			containers := client.containers.list(filters={"name": self.container_name}, all=True)) else None)

		logger.info(f"Container {self.container_name} already exists (status: {existing_container})")
		if existing_container and (reason := self._check_container_match(existing_container, full_image)) is not None:
			logger.info(f"Stopping and removing existing container because {reason}...")
			if existing_container.status == "running":
				existing_container.stop(timeout=10)
			existing_container.remove()
			logger.info(f"Removed existing container")
			raise BaseException("Waiting removal of existing container, will redeploy on next run")

		if not existing_container:
			logger.info(f"Creating container {self.container_name} from image {full_image}...")
			existing_container = client.containers.run(
				image=full_image,
				detach=True,
				name=self.container_name,
				ports=self.ports,
				environment=self.environment,
				volumes=self.volumes,
				network=self.network,
				restart_policy=cast(Any, self.restart_policy),
				labels={"config_hash": self._get_config_hash()}
			)

			container_id = existing_container.id or "unknown"
			logger.info(f"Successfully deployed container: {container_id[:12]}")

		if existing_container.status != "running":
			logger.info(f"Starting existing container...")
			existing_container.start()
			raise BaseException("Container not started yet")

		# Reload to get fresh status
		existing_container.reload()

		return DockerContainerDeployResult(
			container_id=existing_container.id or "unknown",
			container_name=self.container_name,
			image=full_image,
			status=existing_container.status,
			ports=existing_container.ports
		)
