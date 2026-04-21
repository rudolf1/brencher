from enironment import Environment
from steps.docker_plain import DockerImageBuild, DockerContainerCheck, DockerContainerDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge, ResolveInitialBranches

clone = GitClone()
resolveInitialBranches = ResolveInitialBranches(wd=clone, initial_branches=[("main", "HEAD")])
checkoutMerged = CheckoutMerged(clone,
                                desired_branches=resolveInitialBranches,
                                push=False,
                                git_user_email="rudolfss13@gmail.com",
                                git_user_name="brencher_bot"
                                )

# Step 1: Build the image
image_build = DockerImageBuild(
	wd=checkoutMerged,
	dockerfile_path="Dockerfile",
	image_name="brencher_plain",
	image_tag=lambda: "auto-" + checkoutMerged.progress().version,
	nocache=False,
)

# Step 2: Check if container already exists
container_check = DockerContainerCheck(
	container_name="brencher_plain-container"
)

# Step 3: Deploy the container
container_deploy = DockerContainerDeploy(
	image_build=image_build,
	container_name="brencher_plain-container",
	ports={"5001/tcp": 5002},
	environment={"PROFILES": "no_profiles"},
	restart_policy={"Name": "unless-stopped"},
)

unmerge = GitUnmerge(wd=clone, check=container_check)

__all__ = ["brencher_local1"]
brencher_local1 = Environment(
	id="brencher_local1",
	dry=False,
	repo="https://github.com/rudolf1/brencher.git",
	pipeline=[
		clone,
		resolveInitialBranches,
		checkoutMerged,
		image_build,
		container_deploy,
		container_deploy,
		unmerge
	]
)

#
#
# buildDocker = DockerComposeBuild(clone,
#                     docker_repo_username = "",
#                     docker_repo_password = "",
#                     docker_compose_path = "docker-compose.yml",
#                     docker_repo_url="https://registry.rudolf.keenetic.link",
#                     publish=False,
#                     envs = lambda: {
#                         "version": "auto-" + checkoutMerged.progress().version,
#                         "user_group" : "1000:998"
#                     },
#                 )
# dockerSwarmCheck = DockerSwarmCheck(
#     stack_name = "brencher_local1",
# )
# deployDocker = DockerSwarmDeploy(
#     wd=clone,
#     buildDocker=buildDocker,
#     stackChecker=dockerSwarmCheck,
#     envs = lambda: {
#             "version": "auto-" + checkoutMerged.progress().version,
#             "services": {
#                 "brencher-backend" :{
#                     "user" : "1000:998",
#                     "environment": {
#                         "PROFILES" : "brencher_local2",
#                         # "SLAVE_BRENCHER" : "192.169.1.96:5002"
#                     },
#                 }
#             }
#     },
#     stack_name = "brencher_local1",
#     docker_compose_path = "docker-compose.yml",
# )
