from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.docker import DockerComposeBuild
from steps.docker import DockerSwarmDeploy, DockerSwarmCheck
from enironment import Environment
from typing import List, Dict, Any, Optional, Tuple
from steps.step import AbstractStep

env_local = Environment(
    id="brencher_local1",
    branches=[],
    dry=False,
    repo="https://github.com/rudolf1/brencher.git",
)


def create_pipeline(env: Environment) -> List[AbstractStep]:
    clone = GitClone(env)
    checkoutMerged = CheckoutMerged(clone, env=env,
                        push = False,
                        git_user_email="rudolfss13@gmail.com",
                        git_user_name="brencher_bot"
            )
    

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
    dockerSwarmCheck = DockerSwarmCheck(
        stack_name = "brencher_local1",
        env=env, 
    )
    deployDocker = DockerSwarmDeploy(
        wd=clone,
        buildDocker=buildDocker,
        stackChecker=dockerSwarmCheck,
        envs = lambda: { 
                "version": "auto-" + checkoutMerged.result.version,
                "services": {
                    "brencher-backend" :{
                        "user" : "1000:998",
                        "ports": [{
                            "published": 5003
                        }],
                        "environment": {
                            "PROFILES" : "brencher_local"
                        }
                    }
                }
        },
        stack_name = "brencher_local1",
        docker_compose_path = "docker-compose.yml", 
        env=env,
    )
    unmerge = GitUnmerge(clone, dockerSwarmCheck, env=env)
    return [
        clone,
        checkoutMerged,
        buildDocker,
        dockerSwarmCheck,
        deployDocker,
        unmerge
    ]

brencher_local: Tuple[Environment, List[AbstractStep]] = (env_local, create_pipeline(env_local))

