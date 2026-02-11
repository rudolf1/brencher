from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.docker import DockerSwarmCheck, DockerSwarmDeploy
from enironment import Environment
from typing import List, Tuple
from steps.step import AbstractStep
from steps.checks import SimpleLog, UrlCheck

env = Environment(
    id="immich",
    branches=[("photosHelper/master", "HEAD")],
    dry=False,
    repo="https://github.com/rudolf1/uber_backup.git",
)


def create_pipeline(env: Environment) -> List[AbstractStep]:
    clone = GitClone(env, branchNamePrefix="photosHelper")
    checkoutMerged = CheckoutMerged(clone, env=env,
                        push = False,
                        git_user_email="rudolfss13@gmail.com",
                        git_user_name="brencher_bot"
            )
    

    dockerSwarmCheck = DockerSwarmCheck(
        stack_name = "photosHelper",
        env=env, 
    )
    deployDocker = DockerSwarmDeploy(
        wd=clone,
        buildDocker=None,
        stackChecker=dockerSwarmCheck,
        envs = lambda: { 
            "version": "auto-" + checkoutMerged.result.version
       },
        stack_name = "photosHelper",
        docker_compose_path = "docker-compose.yml", 
        env=env, 
    )
    unmerge = GitUnmerge(clone, dockerSwarmCheck, env=env)

    checkPing = UrlCheck(
        url="https://backuper.rudolf.keenetic.link/api/server/ping",
        expected = {"res":"pong"},
        env=env
    )
    logUrls = SimpleLog(env=env,message = {
        "userLinks": {
            "App": "https://backuper.rudolf.keenetic.link",
        }
    })
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

