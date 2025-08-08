import os
import subprocess
import logging
import docker
import yaml
from typing import List, Optional, Dict, Callable, Any
from dataclasses import dataclass
from steps.step import AbstractStep
from steps.git import GitClone
import re

logger = logging.getLogger(__name__)

class DockerComposeBuild(AbstractStep[List[str]]):
    def __init__(self, 
                 wd: GitClone, 
                 docker_repo_username:str, 
                 docker_repo_password:str, 
                 docker_compose_path:str, 
                 docker_repo_url: str,
                 publish: bool,
                 envs: Callable[[], Dict[str, str]], **kwargs):
        super().__init__(**kwargs)
        self.wd = wd
        self.envs = envs
        self.docker_repo_username = docker_repo_username
        self.docker_repo_password = docker_repo_password
        self.docker_compose_path = docker_compose_path
        self.docker_repo_url = docker_repo_url
        self.publish = publish

    def progress(self) -> List[str]:    
    # def process(self, docker_compose_path: str, docker_repo_url: str, docker_repo_username: str, docker_repo_password: str) -> DockerBuildResult:
        """
        Build and push Docker images defined in a docker-compose file.
        """
        images_built = []
        try:
            # Authenticate to docker repo
            client = docker.from_env()
            if self.publish:
                client.login(username=self.docker_repo_username, password=self.docker_repo_password, registry=self.docker_repo_url)
            env = self.envs()
            # Parse docker-compose file
            with open(self.docker_compose_path, 'r') as f:
                content = f.read()
                content = re.sub(r'\$\{([^}]+)\}', lambda m: env[m.group(1)], content)
                compose = yaml.safe_load(content)
            services = compose.get('services', {})

            for name, svc in services.items():
                build_ctx = svc.get('build')
                image = svc.get('image')
                if not build_ctx or not image:
                    continue
                if self.publish:
                # Check if image exists in remote repo
                    try:
                        client.images.pull(image)
                        logger.info(f"Image {image} already exists in repo, skipping build.")
                        continue
                    except Exception:
                        pass
                else:
                    # Check if image exists locally
                    try:
                        client.images.get(image)
                        logger.info(f"Image {image} already exists locally, skipping build.")
                        continue
                    except docker.errors.ImageNotFound:
                        pass

                logger.info(f"Building image {image} from {build_ctx}")
                client.images.build(path=build_ctx, tag=image)

                if self.publish:
                    logger.info(f"Pushing image {image}")
                    for line in client.images.push(image, stream=True, decode=True):
                        logger.debug(line)
                images_built.append(image)
            return images_built
        except Exception as e:
            raise e

class DockerSwarmDeploy(AbstractStep):
    def __init__(self, 
                 wd: GitClone, 
                 docker_compose_path: str, 
                 envs: Callable[[], Dict[str, str]], 
                 stack_name: str, 
                 **kwargs):
        super().__init__(**kwargs)
        self.wd = wd
        self.envs = envs
        self.docker_compose_path = docker_compose_path
        self.stack_name = stack_name

    def progress(self) -> None:
        """
        Deploys to Docker Swarm using the specified docker-compose.yaml.
        """
        if isinstance(self.wd.result, BaseException):
            raise self.wd.result
        try:
            env = self.envs()
            # Prepare docker-compose file with env substitution
            docker_compose_absolute_path = os.path.join(self.wd.result, self.docker_compose_path)
            with open(docker_compose_absolute_path, 'r') as f:
                content = f.read()
                content = re.sub(r'\$\{([^}]+)\}', lambda m: env.get(m.group(1), ""), content)
                compose = yaml.safe_load(content)
                if "services" in compose:
                    for svc in compose["services"].values():
                        if "build" in svc:
                            del svc["build"]
                content = yaml.safe_dump(compose)
            tmp_compose_path = docker_compose_absolute_path + ".tmp"
            with open(tmp_compose_path, 'w') as f:
                f.write(content)

            # Deploy stack to Docker Swarm
            cmd = [
                "docker", "stack", "deploy",
                "-c", tmp_compose_path,
                self.stack_name
            ]
            logger.info(f"Deploying stack '{self.stack_name}' using {tmp_compose_path}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Stack deploy failed: {result.stderr}")
                raise RuntimeError(f"Stack deploy failed: {result.stderr}")
            logger.info(f"Stack deployed successfully: {result.stdout}")
        except Exception as e:
            logger.error(f"DockerSwarmDeploy failed: {e}")
            raise
