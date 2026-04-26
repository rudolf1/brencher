from enironment import Environment
from steps.docker import DockerComposeBuild
from steps.docker import DockerSwarmDeploy, DockerSwarmCheck
from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.shared_state import SharedStateHolderInMemory

clone = GitClone()
dockerSwarmCheck = DockerSwarmCheck(
	stack_name="brencher_local2",
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
									 "user_group": "1000:998"
								 },

                                 )
deployDocker = DockerSwarmDeploy(
	wd=clone,
	buildDocker=buildDocker,
	stackChecker=dockerSwarmCheck,
	envs=lambda: {
		"version": "auto-" + checkoutMerged.progress().version,
		"services": {
			"brencher-backend": {
				"user": "1000:998",
				"environment": {
					"PROFILES": "brencher_local1"
				},
				"ports": [
					"5002:5001"
				]
			}
		}
	},
	stack_name="brencher_local2",
	docker_compose_path="docker-compose.yml",
)

__all__ = ["brencher_local2"]
brencher_local2 = Environment(
	id="brencher_local2",
	state=state,
	repo="https://github.com/rudolf1/brencher.git",
	pipeline=[
		clone,
		state,
		checkoutMerged,
		buildDocker,
		dockerSwarmCheck,
		deployDocker,
		unmerge
	]
)
