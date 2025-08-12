from steps.git import GitClone
from steps.git import CheckoutMerged
from steps.docker import DockerComposeBuild
from steps.docker import DockerSwarmDeploy
from enironment import Environment
from typing import List, Dict, Any, Optional, Tuple
from steps.step import AbstractStep

env_local = Environment(
    id="brencher_local",
    branches=["main", "main_local"],
    state="Active",
    repo="https://github.com/rudolf1/brencher.git",
)


def create_pipeline(env: Environment) -> List[AbstractStep]:
    clone = GitClone(env)
    checkoutMerged = CheckoutMerged(clone, env=env,
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
                        envs = lambda: { 
                            "version": "auto-" + checkoutMerged.result.version,
                            "user_group" : "1000:998" 
                        },
                        env=env
                    )
    deployDocker = DockerSwarmDeploy(
        wd=clone,
        buildDocker=buildDocker,
        envs = lambda: { 
                "version": "auto-" + checkoutMerged.result.version,
                "user_group" : "1000:998" 
                },
        stack_name = "brencher_local",
        docker_compose_path = "docker-compose.yml", 
        env=env, 
    )
    return [
        clone,
        checkoutMerged,
        buildDocker,
        # deployDocker,
        # TODO add health check.
        # TODO add reverse flow. We need to understand what is deployed
        # TODO add teamcity support
        # TODO add udploy support

    ]

brencher_local: Tuple[Environment, List[AbstractStep]] = (env_local, create_pipeline(env_local))

