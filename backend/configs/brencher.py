from configs.brencher2 import checkPingF
from enironment import Environment
from steps.checks import SimpleLog, UrlCheck
from steps.docker import DockerComposeBuild, DockerSwarmCheck, DockerSwarmDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.shared_state import SharedStateHolderInMemory

clone = GitClone()

dockerSwarmCheck = DockerSwarmCheck(
	stack_name="brencher",
)
unmerge = GitUnmerge(clone, dockerSwarmCheck)

state = SharedStateHolderInMemory(unmerge=unmerge)

checkoutMerged = CheckoutMerged(clone,
                                desired_branches=state,
                                push=False,
                                git_user_email="rudolfss13@gmail.com",
                                git_user_name="brencher_bot"
                                )

buildDocker = DockerComposeBuild(clone,
                                 docker_repo_username="",
                                 docker_repo_password="",
                                 docker_compose_path="docker-compose.yml",
                                 docker_repo_url="https://registry.rudolf.keenetic.link",
                                 publish=False,
                                 build_cache = True,
                                 envs=lambda: {
									 "version": "auto-" + checkoutMerged.progress().version,
									 "user_group": "1000:137"
								 },
                                 )

deployDocker = DockerSwarmDeploy(
	wd=clone,
	buildDocker=buildDocker,
	stackChecker=dockerSwarmCheck,
	envs=lambda: {
		"version": "auto-" + checkoutMerged.progress().version,
	},
	stack_name="brencher",
	docker_compose_path="docker-compose.yml",
)

checkPing = UrlCheck(
	url="https://brencher.rudolf.keenetic.link/state",
	expected=checkPingF,
)
logUrls = SimpleLog(message={
	"userLinks": {
		"App": "https://brencher.rudolf.keenetic.link/",
		"Status": "https://brencher.rudolf.keenetic.link/state",
	}
})

__all__ = ["brencher"]
brencher = Environment(
	id="brencher",
	state=state,
	repo="https://github.com/rudolf1/brencher.git",
	pipeline=[
		clone,
		state,
		checkoutMerged,
		buildDocker,
		dockerSwarmCheck,
		unmerge,
		deployDocker,
		checkPing,
		logUrls
	]
)
