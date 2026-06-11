import logging
import os
import re
import subprocess
from dataclasses import dataclass
from typing import List, Dict, Callable, Any, Mapping, Protocol, Union, runtime_checkable

import docker
import yaml
from docker import errors as docker_errors
from dotenv import dotenv_values
from enironment import AbstractStep
from steps.git import GitClone, HasVersion

logger = logging.getLogger(__name__)


class DockerComposeBuild(AbstractStep[Dict[str, str]]):
	def __init__(self,
	             wd: GitClone,  # TODO should be CheckoutMerged
	             docker_repo_username: str,
	             docker_repo_password: str,
	             docker_compose_path: str,
	             docker_repo_url: str,
	             publish: bool,
	             envs: Callable[[], Dict[str, Any]], 
				 build_cache: bool = False,
				 **kwargs: Any) -> None:
		super().__init__(**kwargs)
		self.wd = wd
		self.envs = envs
		self.docker_repo_username = docker_repo_username
		self.docker_repo_password = docker_repo_password
		self.docker_compose_path = docker_compose_path
		self.docker_repo_url = docker_repo_url
		self.publish = publish
		self.build_cache = build_cache

	def progress(self) -> Dict[str, str]:
		"""
		Build and push Docker images defined in a docker-compose file.
		Returns a dict mapping image name to its SHA digest.
		"""
		image_shas: Dict[str, str] = {}
		try:
			# Authenticate to docker repo
			client = docker.DockerClient(base_url='unix://var/run/docker.sock')
			if self.publish:
				client.login(
					username=self.docker_repo_username,
					password=self.docker_repo_password,
					registry=self.docker_repo_url
				)
			env = self.envs()
			# Parse docker-compose file
			docker_compose_absolute_path = os.path.join(self.wd.progress(), self.docker_compose_path)
			with open(docker_compose_absolute_path, 'r') as f:
				content = f.read()
				content = re.sub(r'\$\{([^}]+)\}', lambda m: env[m.group(1)], content)
				compose = yaml.safe_load(content)
			services = compose.get('services', {})

			for name, svc in services.items():
				build_section = svc.get('build')
				if build_section is None:
					continue
				if isinstance(build_section, dict):
					build_ctx = build_section.get('context', '.')
					build_dockerfile = build_section.get('dockerfile', 'Dockerfile')
				else:
					build_ctx = build_section
					build_dockerfile = 'Dockerfile'

				build_ctx = os.path.join(os.path.dirname(docker_compose_absolute_path), build_ctx) 
				build_dockerfile = os.path.join(os.path.dirname(docker_compose_absolute_path), build_dockerfile) 

				image = svc.get('image')
				if not build_ctx or not image:
					continue
				if self.publish:
					# Check if image exists in remote repo
					try:
						img = client.images.pull(image)
						logger.info(f"Image {image} already exists in repo, skipping build.")
						if img.id is not None:
							image_shas[image] = img.id
						continue
					except Exception:
						pass
				else:
					# Check if image exists locally
					try:
						img = client.images.get(image)
						logger.info(f"Image {image} already exists locally, skipping build.")
						if img.id is not None:
							image_shas[image] = img.id
						continue
					except docker_errors.ImageNotFound:
						pass

				logger.info(f"Building image {image} from {build_ctx}, {build_dockerfile}")
				img, _ = client.images.build(path=build_ctx, dockerfile=build_dockerfile, tag=image, nocache=not self.build_cache, rm=not self.build_cache)

				if self.publish:
					logger.info(f"Pushing image {image}")
					for line in client.images.push(image, stream=True, decode=True):
						logger.debug(line)
				if img.id is not None:
					image_shas[image] = img.id
			return image_shas
		except Exception as e:
			raise e


@dataclass
class DockerSwarmCheckResult:
	name: str
	image: str
	stack: str
	version: str


class DockerSwarmCheck(AbstractStep[Dict[str, DockerSwarmCheckResult]]):

	def __init__(self,
	             stack_name: str,
	             **kwargs: Any) -> None:
		super().__init__(**kwargs)
		self.stack_name = stack_name

	def progress(self) -> Dict[str, DockerSwarmCheckResult]:

		client = docker.DockerClient(base_url='unix://var/run/docker.sock')
		current_services: Dict[str, DockerSwarmCheckResult] = {}
		for svc in client.services.list():
			attrs = client.services.get(svc.id).attrs
			name = attrs["Spec"]["Name"].replace(self.stack_name + "_", "")
			if attrs["Spec"]["Labels"].get("com.docker.stack.namespace", "") == self.stack_name:
				# logger.info(f"Service {svc.name} is running with image {attrs}")
				current_services[name] = DockerSwarmCheckResult(
					name=name,
					image=attrs["Spec"]["Labels"].get("com.docker.stack.image", ""),
					stack=attrs["Spec"]["Labels"].get("com.docker.stack.namespace", ""),
					version=attrs["Spec"]["TaskTemplate"]["ContainerSpec"]["Labels"].get("org.brencher.version", ""),
				)

		logger.info(f"Current services in stack '{self.stack_name}': {current_services}")
		return current_services


@runtime_checkable
class HasImage(Protocol):
	image: str


class DockerSwarmDeploy(AbstractStep[str]):
	def __init__(self,
	             wd: GitClone,
	             buildDocker: DockerComposeBuild | None,
	             stackChecker: AbstractStep[Mapping[str, Union[HasImage, HasVersion]]],
	             docker_compose_path: str,
	             envs: Callable[[], Dict[str, Any]],
	             stack_name: str,
	             **kwargs: Any) -> None:
		super().__init__(**kwargs)
		self.wd = wd
		self.buildDocker = buildDocker
		self.envs = envs
		self.docker_compose_path = docker_compose_path
		self.stack_name = stack_name
		self.stackChecker = stackChecker

	def progress(self) -> Any:
		"""
		Deploys to Docker Swarm using the specified docker-compose.yaml.
		"""
		self.wd.progress()
		if self.buildDocker is not None:
			self.buildDocker.progress()
		current_services: Mapping[str, HasImage | HasVersion] = self.stackChecker.progress()

		def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> None:
			for k, v in b.items():
				if (
						k in a
						and isinstance(a[k], dict)
						and isinstance(v, dict)
				):
					merge_dicts(a[k], v)
				else:
					a[k] = v

		env = self.envs()
		# Prepare docker-compose file with env substitution
		docker_compose_absolute_path = os.path.join(self.wd.progress(), self.docker_compose_path)
		with open(docker_compose_absolute_path, 'r') as f:
			content = f.read()
			content = re.sub(r'\$\{([^}]+)\}', lambda m: env.get(m.group(1), ""), content)
			compose = yaml.safe_load(content)
			if "services" in compose:
				for svc in compose["services"].values():
					if "build" in svc:
						del svc["build"]
					svc["labels"] = {"org.brencher.version": env["version"]}
			del env["version"]
			merge_dicts(compose, env)
			# logger.info(f"Final compose: {compose}")
			content = yaml.safe_dump(compose)

		expected_services = compose.get("services", {})
		diffs = []
		ok = []
		for svc_name, svc in expected_services.items():
			running_service = current_services.get(svc_name)
			if isinstance(running_service, HasVersion):
				expected_version = svc.get("labels", {}).get("org.brencher.version")
				running_version = running_service.version if running_service is not None else None
				l = {
					"service": svc_name,
					"expected_version": expected_version,
					"actual_version": running_version,
					"stack": self.stack_name,
				}
				logger.info(l)
				if not running_version or not expected_version:
					diffs.append(l)
				elif running_version != expected_version:
					diffs.append(l)
				else:
					ok.append(l)
			elif isinstance(running_service, HasImage):
				expected_image = svc.get("image")
				running_image = running_service.image if running_service is not None else None
				l = {
					"service": svc_name,
					"expected_image": expected_image,
					"actual_image": running_image,
					"stack": self.stack_name,
				}
				logger.info(l)
				if not running_image or not expected_image:
					diffs.append(l)
				elif running_image != expected_image:
					diffs.append(l)
				else:
					ok.append(l)
			else:
				diffs.append({
					"service": svc_name,
					"stack": self.stack_name,
				})
		if len(diffs) == 0:
			logger.info(f"No diff found, stack is already up-to-date.")
			return ok
		logger.info(f"Diff {diffs}")
		if self.env.dry:
			logger.info(f"Stack is not active, skipping deploy.")
			return {
				"diffs": diffs,
			}

		# tmp_compose_path = os.path.join(tempfile.gettempdir(), f"{hashlib.sha1(content.encode()).hexdigest()[:5]}")
		tmp_compose_path = docker_compose_absolute_path + ".tmp"
		with open(tmp_compose_path, 'w') as f:
			f.write(content)
		logger.info(f"Deploying stack '{self.stack_name}' using {tmp_compose_path}")

		# Deploy stack to Docker Swarm
		cmd = [
			"docker", "stack", "deploy",
			"--prune",
			"-c", tmp_compose_path,
			self.stack_name
		]
		logger.info(
			f"Deploying stack '{self.stack_name}' using {tmp_compose_path} in cwd {os.path.dirname(tmp_compose_path)}")
		swarmEnv: dict[str, str] = {}
		if os.path.exists(os.path.join(os.path.dirname(tmp_compose_path), ".env")):
			swarmEnv = {k: v for k, v in dotenv_values(os.path.join(os.path.dirname(tmp_compose_path), ".env")).items()
			            if v is not None}
		# merge_dicts(swarmEnv, env)
		result = subprocess.run(cmd, capture_output=True, text=True)
		# , cwd=os.path.dirname(tmp_compose_path), env=swarmEnv)
		os.remove(tmp_compose_path)
		if result.returncode != 0:
			logger.error(f"Stack deploy failed: {result.stderr}")
			raise RuntimeError(f"Stack deploy failed: {result.stderr}")
		logger.info(f"Stack deployed successfully: {result.stdout}")

		# Check health of all deployed services
		client = docker.DockerClient(base_url='unix://var/run/docker.sock')
		not_running = []
		for svc_name in expected_services:
			full_svc_name = f"{self.stack_name}_{svc_name}"
			services_list = client.services.list(filters={"name": full_svc_name})
			if not services_list:
				not_running.append(f"{full_svc_name} (not found)")
				continue
			svc = services_list[0]
			spec_mode = svc.attrs.get("Spec", {}).get("Mode", {})
			desired_replicas = spec_mode.get("Replicated", {}).get("Replicas", 1)
			running_tasks = [
				t for t in svc.tasks()
				if t.get("Status", {}).get("State") == "running" and t.get("DesiredState") == "running"
			]
			if len(running_tasks) < desired_replicas:
				not_running.append(f"{full_svc_name} ({len(running_tasks)}/{desired_replicas} replicas running)")
		if not_running:
			raise BaseException(f"Services not started yet: {', '.join(not_running)}")

		return f"Stack deployed successfully: {result.stdout}"
