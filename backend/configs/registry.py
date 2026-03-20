from enironment import Environment
from steps.checks import SimpleLog, UrlCheck
from steps.docker import DockerSwarmCheck, DockerSwarmDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge

clone = GitClone(branchNamePrefix="ansible")
checkoutMerged = CheckoutMerged(clone,
								push=False,
								git_user_email="rudolfss13@gmail.com",
								git_user_name="brencher_bot"
								)

dockerSwarmCheck = DockerSwarmCheck(
	stack_name="registry",
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
unmerge = GitUnmerge(clone, dockerSwarmCheck)

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
