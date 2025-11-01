from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.docker import DockerComposeBuild, DockerSwarmCheck, DockerSwarmDeploy
from enironment import Environment
from typing import List, Dict, Any, Optional, Tuple
from steps.step import AbstractStep

env = Environment(
    id="brencher",
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
                            "user_group" : "1000:137" 
                        },
                        env=env
                    )
    

    dockerSwarmCheck = DockerSwarmCheck(
        stack_name = "brencher",
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
                    "environment": {
                        "SLAVE_BRENCHER" : "http://host.docker.internal:5002",
                        "PYTHONUNBUFFERED": "1",
                        "VIRTUAL_HOST": "brencher.rudolf.keenetic.link",
                        "LETSENCRYPT_HOST": "brencher.rudolf.keenetic.link",
                        "PROFILES": "brencher,brencher2,torrserv_proxy,immich",
                    },
                }
            }
            #  SLAVE_BRENCHER='http://100.70.193.97:5002' .venv/bin/python3 backend/app.py brencher_localX
       },
        stack_name = "brencher",
        docker_compose_path = "docker-compose.yml", 
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

brencher: Tuple[Environment, List[AbstractStep]] = (env, create_pipeline(env))

