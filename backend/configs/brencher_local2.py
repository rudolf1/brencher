from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.docker import DockerComposeBuild
from steps.docker import DockerSwarmDeploy, DockerSwarmCheck
from enironment import Environment


clone = GitClone()
checkoutMerged = CheckoutMerged(clone,
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
                        "version": "auto-" + checkoutMerged.progress().version,
                        "user_group" : "1000:998" 
                    },
                    
                )
dockerSwarmCheck = DockerSwarmCheck(
    stack_name = "brencher_local2",
)
deployDocker = DockerSwarmDeploy(
    wd=clone,
    buildDocker=buildDocker,
    stackChecker=dockerSwarmCheck,
    envs = lambda: { 
            "version": "auto-" + checkoutMerged.progress().version,
            "services": {
                "brencher-backend" :{
                    "user" : "1000:998",
                    "environment": {
                        "PROFILES" : "brencher_local1"
                    },
                    "ports": [
                        "5002:5001"
                    ]
                }
            }
    },
    stack_name = "brencher_local2",
    docker_compose_path = "docker-compose.yml", 
)
unmerge = GitUnmerge(clone, dockerSwarmCheck)



__all__ = ["brencher_local2"]
brencher_local2 = Environment(
    id="brencher_local2",
    branches=[],
    dry=False,
    repo="https://github.com/rudolf1/brencher.git",
    pipeline = [
        clone,
        checkoutMerged,
        buildDocker,
        dockerSwarmCheck,
        deployDocker,
        unmerge
    ]
)

