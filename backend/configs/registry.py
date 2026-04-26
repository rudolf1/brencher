from enironment import Environment
from steps.checks import SimpleLog, UrlCheck
from steps.docker import DockerSwarmCheck, DockerSwarmDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.shared_state import SharedStateHolderInMemory

clone = GitClone(branchNamePrefix="ansible")

dockerSwarmCheck = DockerSwarmCheck(
	stack_name="registry",
)
unmerge = GitUnmerge(clone, dockerSwarmCheck)

state = SharedStateHolderInMemory(unmerge=unmerge)

checkoutMerged = CheckoutMerged(clone,
                                desired_branches=state,
                                push=False,
                                git_user_email="rudolfss13@gmail.com",
                                git_user_name="brencher_bot"
                                )

deployDocker = DockerSwarmDeploy(
	wd=clone,
	buildDocker=None,
	stackChecker=dockerSwarmCheck,
	envs=lambda: {
		"version": "auto-" + checkoutMerged.progress().version
	},
	stack_name="registry",
	docker_compose_path="docker-compose-registry.yaml",
)

checkPing = UrlCheck(
	url="https://registry.rudolf.keenetic.link/v2/",
	expected={},
)
logUrls = SimpleLog(message={
	"userLinks": {
		"App": "https://registry.rudolf.keenetic.link",
	}
})

__all__ = ["registry"]
registry = Environment(
	id="registry",
	state=state,
	repo="https://github.com/rudolf1/uber_backup.git",
	pipeline=[
		clone,
		state,
		checkoutMerged,
		dockerSwarmCheck,
		unmerge,
		deployDocker,
		checkPing,
		logUrls
	]
)
