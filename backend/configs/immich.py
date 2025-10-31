from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.docker import DockerComposeBuild, DockerSwarmCheck, DockerSwarmDeploy
from enironment import Environment
from typing import List, Dict, Any, Optional, Tuple
from steps.step import AbstractStep

env = Environment(
    id="immich",
    branches=[("ansible/master", "HEAD")],
    dry=False,
    repo="https://git@github.com/rudolf1/uber_backup.git",
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

    return [
        clone,
        checkoutMerged,
        dockerSwarmCheck, 
        unmerge,       
        deployDocker,
    ]

config: Tuple[Environment, List[AbstractStep]] = (env, create_pipeline(env))

