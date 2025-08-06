import os
import subprocess
import logging
import docker
import yaml
from typing import List, Optional
from dataclasses import dataclass
from steps.step import AbstractStep

logger = logging.getLogger(__name__)

@dataclass
class DockerBuildResult:
    images_built: List[str]
    success: bool
    error_message: Optional[str] = None

class DockerComposeBuild(AbstractStep):
    def progress(self) -> None:    
    # def process(self, docker_compose_path: str, docker_repo_url: str, docker_repo_username: str, docker_repo_password: str) -> DockerBuildResult:
        """
        Build and push Docker images defined in a docker-compose file.
        """
        images_built = []
        try:
            # Authenticate to docker repo
            client = docker.from_env()
            client.login(username=docker_repo_username, password=docker_repo_password, registry=docker_repo_url)

            # Parse docker-compose file
            with open(docker_compose_path, 'r') as f:
                compose = yaml.safe_load(f)
            services = compose.get('services', {})

            for name, svc in services.items():
                build_ctx = svc.get('build')
                image = svc.get('image')
                if not build_ctx or not image:
                    continue
                # Check if image exists in remote repo
                try:
                    client.images.pull(image)
                    logger.info(f"Image {image} already exists in repo, skipping build.")
                    continue
                except Exception:
                    pass
                # Build image
                logger.info(f"Building image {image} from {build_ctx}")
                client.images.build(path=build_ctx, tag=image)
                # Push image
                logger.info(f"Pushing image {image}")
                for line in client.images.push(image, stream=True, decode=True):
                    logger.debug(line)
                images_built.append(image)
            return DockerBuildResult(images_built=images_built, success=True)
        except Exception as e:
            logger.error(f"DockerBuild failed: {e}")
            return DockerBuildResult(images_built=images_built, success=False, error_message=str(e))

class DockerComposeDeploy(AbstractStep):
    def progress(self) -> None:    
    # def process(self, docker_compose_path: str, docker_repo_url: str, docker_repo_username: str, docker_repo_password: str) -> DockerBuildResult:
        """
        Build and push Docker images defined in a docker-compose file.
        """
        images_built = []
        try:
            # Authenticate to docker repo
            client = docker.from_env()
            client.login(username=docker_repo_username, password=docker_repo_password, registry=docker_repo_url)

            # Parse docker-compose file
            with open(docker_compose_path, 'r') as f:
                compose = yaml.safe_load(f)
            services = compose.get('services', {})

            for name, svc in services.items():
                build_ctx = svc.get('build')
                image = svc.get('image')
                if not build_ctx or not image:
                    continue
                # Check if image exists in remote repo
                try:
                    client.images.pull(image)
                    logger.info(f"Image {image} already exists in repo, skipping build.")
                    continue
                except Exception:
                    pass
                # Build image
                logger.info(f"Building image {image} from {build_ctx}")
                client.images.build(path=build_ctx, tag=image)
                # Push image
                logger.info(f"Pushing image {image}")
                for line in client.images.push(image, stream=True, decode=True):
                    logger.debug(line)
                images_built.append(image)
            return DockerBuildResult(images_built=images_built, success=True)
        except Exception as e:
            logger.error(f"DockerBuild failed: {e}")
            return DockerBuildResult(images_built=images_built, success=False, error_message=str(e))
