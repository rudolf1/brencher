from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.docker import DockerSwarmCheck, DockerSwarmDeploy
from enironment import Environment
from typing import List, Tuple
from steps.checks import SimpleLog, UrlCheck

clone = GitClone(branchNamePrefix="ansible")
checkoutMerged = CheckoutMerged(clone,
                    push = False,
                    
                    git_user_email="rudolfss13@gmail.com",
                    git_user_name="brencher_bot"
        )


dockerSwarmCheck = DockerSwarmCheck(
    stack_name = "immich",
)
deployDocker = DockerSwarmDeploy(
    wd=clone,
    buildDocker=None,
    stackChecker=dockerSwarmCheck,
    envs = lambda: { 
        "version": "auto-" + checkoutMerged.progress().version
    },
    stack_name = "immich",
    docker_compose_path = "poc/immich/stack-compose.yml", 
)
unmerge = GitUnmerge(clone, dockerSwarmCheck)

checkPing = UrlCheck(
    url="https://immich.rudolf.keenetic.link/api/server/ping",
    expected = {"res":"pong"},
)
logUrls = SimpleLog(message = {
    "userLinks": {
        "App": "https://immich.rudolf.keenetic.link",
    }
})


config = Environment(
    id="immich",
    branches=[("ansible/master", "HEAD")],
    dry=False,
    repo="https://github.com/rudolf1/uber_backup.git",
    pipeline=[
        clone,
        checkoutMerged,
        dockerSwarmCheck, 
        unmerge,       
        deployDocker,
        checkPing,
        logUrls
    ]
)


