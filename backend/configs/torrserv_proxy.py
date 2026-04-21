from enironment import Environment
from steps.docker import DockerComposeBuild, DockerSwarmCheck, DockerSwarmDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge, ResolveInitialBranches

clone = GitClone()
resolveInitialBranches = ResolveInitialBranches(wd=clone, initial_branches=[])
checkoutMerged = CheckoutMerged(clone,
                                desired_branches=resolveInitialBranches,
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

dockerSwarmCheck = DockerSwarmCheck(
	stack_name="torrserv_proxy",
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
unmerge = GitUnmerge(clone, dockerSwarmCheck)

__all__ = ["torrserv_proxy"]
torrserv_proxy = Environment(
	id="torrserv_proxy",
	dry=False,
	repo="https://github.com/rudolf1/reverseproxy.git",
	pipeline=[
		clone,
		resolveInitialBranches,
		checkoutMerged,
		buildDocker,
		dockerSwarmCheck,
		unmerge,
		deployDocker,
	]
)
