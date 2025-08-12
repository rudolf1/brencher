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
            client = docker.DockerClient(base_url='unix://var/run/docker.sock')
            if self.publish:
                client.login(username=self.docker_repo_username, password=self.docker_repo_password, registry=self.docker_repo_url)
            env = self.envs()
            # Parse docker-compose file
            docker_compose_absolute_path = os.path.join(self.wd.result, self.docker_compose_path)
            with open(docker_compose_absolute_path, 'r') as f:
                content = f.read()
                content = re.sub(r'\$\{([^}]+)\}', lambda m: env[m.group(1)], content)
                compose = yaml.safe_load(content)
            services = compose.get('services', {})

            for name, svc in services.items():
                build_ctx = os.path.join(self.wd.result, svc.get('build'))
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

class DockerSwarmDeploy(AbstractStep[str]):
    def __init__(self, 
                 wd: GitClone, 
                 buildDocker: DockerComposeBuild,
                 docker_compose_path: str, 
                 envs: Callable[[], Dict[str, str]], 
                 stack_name: str, 
                 **kwargs):
        super().__init__(**kwargs)
        self.wd = wd
        self.buildDocker = buildDocker
        self.envs = envs
        self.docker_compose_path = docker_compose_path
        self.stack_name = stack_name

    def _get_stack_state(self, stack_name):
        current_services = {}
        cmd_ps = [
            "docker", "service", "ls", "--format", "{{.Name}}"
        ]
        ps_result = subprocess.run(cmd_ps, capture_output=True, text=True, check=True)
        stack_svc_names = ps_result.stdout.strip().splitlines()
        for svc_name in stack_svc_names:
            if not svc_name.startswith(stack_name + "_"):
                continue
            cmd_inspect = [
                "docker", "service", "inspect", svc_name, "--format", "{{.Spec.TaskTemplate.ContainerSpec.Image}}"
            ]
            inspect_result = subprocess.run(cmd_inspect, capture_output=True, text=True, check=True)
            image_tag = inspect_result.stdout.strip()
            service_name = svc_name.removeprefix(self.stack_name + "_")
            current_services[service_name] = image_tag
        logger.info(f"Current services {current_services}")
        return current_services

    def progress(self) -> str:
        """
        Deploys to Docker Swarm using the specified docker-compose.yaml.
        """
        if isinstance(self.wd.result, BaseException):
            raise self.wd.result
        if isinstance(self.buildDocker.result, BaseException):
            raise self.buildDocker.result

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

        current_services = self._get_stack_state(self.stack_name)
        expected_services = compose.get("services", {})
        diffs = []
        ok = []
        for svc_name, svc in expected_services.items():
            expected_image = svc.get("image")
            running_image = current_services.get(svc_name)
            l = f"Service '{svc_name}' (expected image: '{expected_image}', actual image: '{running_image}')"
            logger.info(l)
            if running_image and expected_image and running_image == expected_image:
                ok.append(l)
            else:
                diffs.append(l)

        if len(diffs) == 0:
            return '\\n'.join(ok)
        logger.info(f"Diff {diffs}")
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
        return f"Stack deployed successfully: {result.stdout}"
