from enironment import Environment
from steps.checks import SimpleLog, UrlCheck
from steps.docker import DockerSwarmCheck, DockerSwarmDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge, ResolveInitialBranches

clone = GitClone(branchNamePrefix="ansible")
resolveInitialBranches = ResolveInitialBranches(wd=clone, initial_branches=[("ansible/master", "HEAD")])
checkoutMerged = CheckoutMerged(clone,
                                desired_branches=resolveInitialBranches,
                                push=False,
                                git_user_email="rudolfss13@gmail.com",
                                git_user_name="brencher_bot"
                                )

dockerSwarmCheck = DockerSwarmCheck(
	stack_name="immich",
)

deployDocker = DockerSwarmDeploy(
	wd=clone,
	buildDocker=None,
	stackChecker=dockerSwarmCheck,
	envs=lambda: {
		"version": "auto-" + checkoutMerged.progress().version
	},
	stack_name="immich",
	docker_compose_path="poc/immich/stack-compose.yml",
)
unmerge = GitUnmerge(clone, dockerSwarmCheck)

checkPing = UrlCheck(
	url="https://immich.rudolf.keenetic.link/api/server/ping",
	expected={"res": "pong"},
)
logUrls = SimpleLog(message={
	"userLinks": {
		"App": "https://immich.rudolf.keenetic.link",
	}
})

__all__ = ["immich"]
immich = Environment(
	id="immich",
	dry=False,
	repo="https://github.com/rudolf1/uber_backup.git",
	pipeline=[
		clone,
		resolveInitialBranches,
		checkoutMerged,
		dockerSwarmCheck,
		unmerge,
		deployDocker,
		checkPing,
		logUrls
	]
)
