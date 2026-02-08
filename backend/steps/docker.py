import os
import subprocess
import logging
import docker
from docker import errors as docker_errors
import yaml
from dotenv import dotenv_values
from typing import List, Dict, Callable, Any
from dataclasses import dataclass
from steps.step import AbstractStep
from steps.git import GitClone
import re

logger = logging.getLogger(__name__)

class DockerComposeBuild(AbstractStep[List[str]]):
    def __init__(self, 
                wd: GitClone, 
                docker_repo_username: str, 
                docker_repo_password: str, 
                docker_compose_path: str, 
                docker_repo_url: str,
                publish: bool,
                envs: Callable[[], Dict[str, Any]], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.wd = wd
        self.envs = envs
        self.docker_repo_username = docker_repo_username
        self.docker_repo_password = docker_repo_password
        self.docker_compose_path = docker_compose_path
        self.docker_repo_url = docker_repo_url
        self.publish = publish

    def progress(self) -> List[str]:    
        """
        Build and push Docker images defined in a docker-compose file.
        """
        images_built = []
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
            docker_compose_absolute_path = os.path.join(self.wd.result, self.docker_compose_path)
            with open(docker_compose_absolute_path, 'r') as f:
                content = f.read()
                content = re.sub(r'\$\{([^}]+)\}', lambda m: env[m.group(1)], content)
                compose = yaml.safe_load(content)
            services = compose.get('services', {})

            for name, svc in services.items():
                if svc.get('build') is None:
                    continue
                build_ctx = os.path.join(os.path.dirname(docker_compose_absolute_path), svc.get('build'))
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
                    except docker_errors.ImageNotFound:
                        pass

                logger.info(f"Building image {image} from {build_ctx}")
                client.images.build(path=build_ctx, tag=image, nocache=True)

                if self.publish:
                    logger.info(f"Pushing image {image}")
                    for line in client.images.push(image, stream=True, decode=True):
                        logger.debug(line)
                images_built.append(image)
            return images_built
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
        current_services = {}
        for svc in client.services.list():
            attrs = client.services.get(svc.id).attrs
            name = attrs["Spec"]["Name"].replace(self.stack_name + "_", "")
            if attrs["Spec"]["Labels"].get("com.docker.stack.namespace", "") == self.stack_name:
                # logger.info(f"Service {svc.name} is running with image {attrs}")
                current_services[name] = DockerSwarmCheckResult(
                    name = name,
                    image   = attrs["Spec"]["Labels"].get("com.docker.stack.image", ""),
                    stack   = attrs["Spec"]["Labels"].get("com.docker.stack.namespace", ""),
                    version = attrs["Spec"]["TaskTemplate"]["ContainerSpec"]["Labels"].get("org.brencher.version", ""),
                )

        logger.info(f"Current services in stack '{self.stack_name}': {current_services}")    
        return current_services

class DockerSwarmDeploy(AbstractStep[str]):
    def __init__(self, 
                 wd: GitClone, 
                 buildDocker: DockerComposeBuild | None,
                 stackChecker: DockerSwarmCheck,
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
        if isinstance(self.wd.result, BaseException):
            raise self.wd.result
        if self.buildDocker is not None and isinstance(self.buildDocker.result, BaseException):
            raise self.buildDocker.result
        if isinstance(self.stackChecker.result, BaseException):
            raise self.stackChecker.result


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
        docker_compose_absolute_path = os.path.join(self.wd.result, self.docker_compose_path)
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

        current_services = self.stackChecker.result
        expected_services = compose.get("services", {})
        diffs = []
        ok = []
        for svc_name, svc in expected_services.items():
            expected_image = svc.get("image")
            running_service = current_services.get(svc_name)
            running_image = running_service.image if running_service is not None else None
            l = {
                "service": svc_name,
                "expected_image": expected_image,
                "actual_image": running_image,
                "stack": self.stack_name,
            }
            logger.info(l)
            if running_image and expected_image and running_image == expected_image:
                ok.append(l)
            else:
                diffs.append(l)

        if len(diffs) == 0:
            logger.info(f"No diff found, stack is already up-to-date.")
            return ok
        logger.info(f"Diff {diffs}")
        if self.env.dry:
            logger.info(f"Stack is not active, skipping deploy.")
            return {
                "diffs": diffs,
            }
        
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
        logger.info(f"Deploying stack '{self.stack_name}' using {tmp_compose_path} in cwd {os.path.dirname(tmp_compose_path)}")
        swarmEnv: dict[str, str] = {}
        if os.path.exists(os.path.join(os.path.dirname(tmp_compose_path), ".env")):
            swarmEnv = { k:v for k,v in dotenv_values(os.path.join(os.path.dirname(tmp_compose_path), ".env")).items() if v is not None }
        # merge_dicts(swarmEnv, env)
        result = subprocess.run(cmd, capture_output=True, text=True)
        #, cwd=os.path.dirname(tmp_compose_path), env=swarmEnv)
        if result.returncode != 0:
            logger.error(f"Stack deploy failed: {result.stderr}")
            raise RuntimeError(f"Stack deploy failed: {result.stderr}")
        logger.info(f"Stack deployed successfully: {result.stdout}")
        return f"Stack deployed successfully: {result.stdout}"
