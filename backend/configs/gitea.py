from enironment import Environment
from steps.checks import SimpleLog, UrlCheck
from steps.docker import DockerSwarmCheck, DockerSwarmDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.shared_state import SharedStateHolderInMemory

clone = GitClone(url="https://github.com/rudolf1/uber_backup.git", branchNamePrefix="ansible")

dockerSwarmCheck = DockerSwarmCheck(
	stack_name="gitea",
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
		"version": "auto-" + checkoutMerged.progress().version,
	},
	stack_name="gitea",
	docker_compose_path="poc/gitea/stack-compose.yml",
)

checkPing1 = UrlCheck(
	url="http://100.70.193.97:8087/api/status",
	expected=lambda obj: obj['gateway_running'] == 'true' and obj['auth_required'] == 'true',
)
logUrls = SimpleLog(message={
	"userLinks": {
		"App": "https://gitea.rudolf.keenetic.link",
	}
})


__all__ = ["gitea"]
gitea = Environment(
	id="gitea",
	state=state,
	pipeline=[
		clone,
		state,
		checkoutMerged,
		dockerSwarmCheck,
		unmerge,
		deployDocker,
		checkPing1,
		logUrls
	]
)
