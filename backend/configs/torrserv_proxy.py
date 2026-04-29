from enironment import Environment
from steps.docker import DockerComposeBuild, DockerSwarmCheck, DockerSwarmDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.shared_state import SharedStateHolderInMemory

clone = GitClone(url="https://github.com/rudolf1/reverseproxy.git")

dockerSwarmCheck = DockerSwarmCheck(
	stack_name="torrserv_proxy",
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
                                 envs=lambda: {
									 "version": "auto-" + checkoutMerged.progress().version,
								 },
                                 )

deployDocker = DockerSwarmDeploy(
	wd=clone,
	buildDocker=buildDocker,
	stackChecker=dockerSwarmCheck,
	envs=lambda: {
		"version": "auto-" + checkoutMerged.progress().version
	},
	stack_name="torrserv_proxy",
	docker_compose_path="docker-compose.yml",
)

__all__ = ["torrserv_proxy"]
torrserv_proxy = Environment(
	id="torrserv_proxy",
	state=state,
	pipeline=[
		clone,
		state,
		checkoutMerged,
		buildDocker,
		dockerSwarmCheck,
		unmerge,
		deployDocker,
	]
)
