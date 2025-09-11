from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.docker import DockerComposeBuild, DockerSwarmCheck, DockerSwarmDeploy
from enironment import Environment
from typing import List, Dict, Any, Optional, Tuple
from steps.step import AbstractStep

env = Environment(
    id="torrserv_proxy",
    branches=[],
    # ("photosHelper/streams", "HEAD")
    dry=False,
    repo="https://github.com/rudolf1/TorrServer.git",
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
                        docker_compose_path = "reverseproxy/docker-compose.yml", 
                        docker_repo_url="https://registry.rudolf.keenetic.link", 
                        publish=False,
                        envs = lambda: { 
                            "version": "auto-" + checkoutMerged.result.version,
                        },
                        env=env
                    )
    

    dockerSwarmCheck = DockerSwarmCheck(
        stack_name = "torrserv_proxy",
        env=env, 
    )
    deployDocker = DockerSwarmDeploy(
        wd=clone,
        buildDocker=buildDocker,
        stackChecker=dockerSwarmCheck,
        envs = lambda: { 
            "version": "auto-" + checkoutMerged.result.version
       },
        stack_name = "torrserv_proxy",
        docker_compose_path = "reverseproxy/docker-compose.yml", 
        env=env, 
    )
    unmerge = GitUnmerge(clone, dockerSwarmCheck, env=env)

    return [
        clone,
        checkoutMerged,
        buildDocker,
        dockerSwarmCheck, 
        unmerge,       
        deployDocker,
    ]

config: Tuple[Environment, List[AbstractStep]] = (env, create_pipeline(env))

