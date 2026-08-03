from enironment import Environment
from steps.checks import SimpleLog, UrlCheck
from steps.docker import DockerSwarmCheck, DockerSwarmDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.shared_state import SharedStateHolderInMemory

clone = GitClone(url="https://github.com/rudolf1/uber_backup.git", branchNamePrefix="ansible")

dockerSwarmCheck = DockerSwarmCheck(
	stack_name="hermes_infra",
)
unmerge = GitUnmerge(clone, dockerSwarmCheck)

state = SharedStateHolderInMemory(unmerge=None)

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
	stack_name="hermes_infra",
	docker_compose_path="hermes_squid/stack-compose.yml",
)

checkPing1 = UrlCheck(
	url="http://100.70.193.97:8088/api/status",
	expected=lambda obj: obj['gateway_running'] == 'true' and obj['auth_required'] == 'true',
)
logUrls = SimpleLog(message={
	"userLinks": {
		"App": "https://hermes.rudolf.keenetic.link",
	}
})


__all__ = ["hermes_infra"]
hermes_infra = Environment(
	id="hermes_infra",
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
