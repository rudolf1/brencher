import json
from steps.checks import SimpleLog, UrlCheck
from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.docker import DockerComposeBuild, DockerSwarmCheck, DockerSwarmDeploy
from enironment import Environment
from typing import List, Dict, Any, Optional, Tuple
from steps.step import AbstractStep

env = Environment(
    id="brencher2",
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
        stack_name = "brencher2",
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
                        "PROFILES" : "brencher"
                    },
                    "ports": [
                        "5002:5001"
                    ]
                }
            }
       },
        stack_name = "brencher2",
        docker_compose_path = "docker-compose.yml", 
        env=env, 
    )
    unmerge = GitUnmerge(clone, dockerSwarmCheck, env=env)

    def checkPingF(obj: Any):
        if not isinstance(obj, dict):
            raise TypeError(f"Expected dict, got {type(obj).__name__}")
        if "brencher" not in obj or "brencher2" not in obj:
            raise ValueError("Dictionary must contain both 'brencher' and 'brencher2' keys")
        for v in obj['brencher'][1]:
            if "Exception" in json.dumps(v):
                raise Exception(f"Brencher check failed for: {v}")

    checkPing = UrlCheck(
        url="https://brencher.rudolf.keenetic.link/state",
        expected = checkPingF,
        env=env
    )
    logUrls = SimpleLog(env=env,message = {
        "userLinks": {
            "App": "https://brencher.rudolf.keenetic.link/",
            "Status": "https://brencher.rudolf.keenetic.link/state",
        }
    })

    return [
        clone,
        checkoutMerged,
        buildDocker,
        dockerSwarmCheck, 
        unmerge,       
        deployDocker,
        checkPing,
        logUrls
    ]

brencher: Tuple[Environment, List[AbstractStep]] = (env, create_pipeline(env))

