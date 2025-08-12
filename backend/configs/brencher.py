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
    checkoutMerged = CheckoutMerged(clone, env.branches, env=env,
                        push = False,
                        git_user_email="rudolfss13@gmail.com",
                        git_user_name="brencher_bot"
            )
    
# git config --global user.email "rudolfss13@gmail.com"
# git config --global user.name "brencher_bot"


    buildDocker = DockerComposeBuild(clone,
                        docker_repo_username = "", 
                        docker_repo_password = "", 
                        docker_compose_path = "docker-compose.yml", 
                        docker_repo_url="https://registry.rudolf.keenetic.link", 
                        publish=False,
                        envs = lambda: { "version": "auto-" + checkoutMerged.result.version },
                        env=env
                    )
    deployDocker = DockerSwarmDeploy(
        wd=clone,
        buildDocker=buildDocker,
        envs = lambda: { "version": "auto-" + checkoutMerged.result.version },
        stack_name = "brencher",
        docker_compose_path = "docker-compose.yml", 
        env=env, 
    )
    return [
        clone,
        checkoutMerged,
        buildDocker,
        deployDocker,
        # TODO add health check.
        # TODO add reverse flow. We need to understand what is deployed
        # TODO add teamcity support
        # TODO add udploy support

    ]

brencher: Tuple[Environment, List[AbstractStep]] = (env, create_pipeline(env))

