from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.docker import DockerSwarmCheck, DockerSwarmDeploy
from enironment import Environment
from steps.checks import SimpleLog, UrlCheck
from steps.shared_state import SharedStateHolderInMemory



clone = GitClone(url="https://github.com/rudolf1/uber_backup.git", branchNamePrefix="photosHelper")

sharedState = SharedStateHolderInMemory(unmerge=None)

checkoutMerged = CheckoutMerged(clone,
                    desired_branches=sharedState,
                    push = False,
                    git_user_email="rudolfss13@gmail.com",
                    git_user_name="brencher_bot"
        )

sharedState.set_branches([("photosHelper/master", "HEAD")])
dockerSwarmCheck = DockerSwarmCheck(
    stack_name = "photosHelper",
)
deployDocker = DockerSwarmDeploy(
    wd=clone,
    buildDocker=None,
    stackChecker=dockerSwarmCheck,
    envs = lambda: {
        "version": "auto-" + checkoutMerged.progress().version
   },
    stack_name = "photosHelper",
    docker_compose_path = "docker-compose.yml",
)
unmerge = GitUnmerge(clone, dockerSwarmCheck)

checkPing = UrlCheck(
    url="https://backuper.rudolf.keenetic.link/api/server/ping",
    expected = {"res":"pong"},
)
logUrls = SimpleLog(message = {
    "userLinks": {
        "App": "https://backuper.rudolf.keenetic.link",
    }
})

backups_helper = Environment(
    id="backupsHelper",
    state=sharedState,
    pipeline=[
        clone,
        sharedState,
        checkoutMerged,
        dockerSwarmCheck,
        unmerge,
        deployDocker,
        checkPing,
        logUrls
    ]
)


