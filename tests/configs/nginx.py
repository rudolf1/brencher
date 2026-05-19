import subprocess
from pathlib import Path

from enironment import Environment
from steps.docker_plain import DockerImageBuild, DockerContainerCheck, DockerContainerDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.shared_state import SharedStateHolderInMemory

REPO_ROOT = Path(__file__).resolve().parents[2]
CURRENT_BRANCH = subprocess.check_output(
	["git", "-C", str(REPO_ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
	text=True,
).strip()
CURRENT_COMMIT = subprocess.check_output(
	["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
	text=True,
).strip()

clone = GitClone(url="https://github.com/rudolf1/brencher.git")

container_check = DockerContainerCheck(
	container_name="test_plain-container"
)

unmerge = GitUnmerge(wd=clone, check=container_check)

state = SharedStateHolderInMemory(unmerge=unmerge)

checkoutMerged = CheckoutMerged(clone,
                                desired_branches=state,
                                push=False,
                                git_user_email="rudolfss13@gmail.com",
                                git_user_name="test_bot"
                                )

# Step 1: Build the image
image_build = DockerImageBuild(
	wd=checkoutMerged,
	dockerfile_path="Dockerfile_test_app",
	image_name="test_plain",
	image_tag=lambda: "auto-" + checkoutMerged.progress().version,
	nocache=False,
)

# Step 3: Deploy the container
container_deploy = DockerContainerDeploy(
	image_build=image_build,
	container_name="test_plain-container",
	ports={"5001/tcp": 5002},
	environment={"PROFILES": "no_profiles"},
	restart_policy={"Name": "unless-stopped"},
)

__all__ = ["test_local1"]
test_local1 = Environment(
	id="test_local1",
	state=state,
	pipeline=[
		clone,
		state,
		checkoutMerged,
		image_build,
		container_deploy,
		container_deploy,
		unmerge
	]
)
