from steps.git import GitClone
from steps.git import CheckoutMerged
from steps.docker import DockerComposeBuild
from steps.docker import DockerSwarmDeploy
from enironment import Environment
from typing import List, Dict, Any, Optional, Tuple
from steps.step import AbstractStep

env = Environment(
    id="brencher",
    branches=["main"],
    state="Active",
    repo="https://github.com/rudolf1/brencher.git",
)


def create_pipeline(env: Environment) -> List[AbstractStep]:
    clone = GitClone(env)
    checkoutMerged = CheckoutMerged(clone, env.branches, env=env)
    buildDocker = DockerComposeBuild(clone,
                        docker_repo_username = "", 
                        docker_repo_password = "", 
                        docker_compose_path = "docker-compose.yml", 
                        docker_repo_url="https://registry.rudolf.keenetic.link", 
                        envs = lambda: { "version": "auto-" + checkoutMerged.result[1][0:5] },
                        env=env
                    )
    deployDocker = DockerSwarmDeploy(
        wd=clone,
        envs = lambda: { "version": "auto-" + checkoutMerged.result[1][0:5] },
        stack_name = "brencher",
        docker_compose_path = "docker-compose.yml", 
        env=env, 
    )
    return [
        clone,
        checkoutMerged,
        buildDocker,
        deployDocker
    ]

brencher: Tuple[Environment, List[AbstractStep]] = (env, create_pipeline(env))

