from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.docker import DockerComposeBuild, DockerSwarmCheck, DockerSwarmDeploy
from enironment import Environment
from typing import List, Dict, Any, Optional, Tuple
from steps.step import AbstractStep
from steps.checks import SimpleLog, UrlCheck

env = Environment(
    id="immich",
    branches=[("ansible/master", "HEAD")],
    dry=False,
    repo="https://github.com/rudolf1/uber_backup.git",
)


def create_pipeline(env: Environment) -> List[AbstractStep]:
    clone = GitClone(env, branchNamePrefix="ansible")
    checkoutMerged = CheckoutMerged(clone, env=env,
                        push = False,
                        
                        git_user_email="rudolfss13@gmail.com",
                        git_user_name="brencher_bot"
            )
    

    dockerSwarmCheck = DockerSwarmCheck(
        stack_name = "immich",
        env=env, 
    )
    deployDocker = DockerSwarmDeploy(
        wd=clone,
        buildDocker=None,
        stackChecker=dockerSwarmCheck,
        envs = lambda: { 
            "version": "auto-" + checkoutMerged.result.version
       },
        stack_name = "immich",
        docker_compose_path = "poc/immich/stack-compose.yml", 
        env=env, 
    )
    unmerge = GitUnmerge(clone, dockerSwarmCheck, env=env)

    checkPing = UrlCheck(
        url="https://immich.rudolf.keenetic.link/api/server/ping",
        expected = {"res":"pongX"},
        env=env
    )
    logUrls = SimpleLog(env=env,message = {
            "Immich": "https://immich.rudolf.keenetic.link",
        }
    )
    return [
        clone,
        checkoutMerged,
        dockerSwarmCheck, 
        unmerge,       
        deployDocker,
        checkPing,
        logUrls
    ]

config: Tuple[Environment, List[AbstractStep]] = (env, create_pipeline(env))

