import json
from typing import Any

from enironment import Environment
from steps.checks import SimpleLog, UrlCheck
from steps.docker import DockerComposeBuild, DockerSwarmCheck, DockerSwarmDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.shared_state import SharedStateHolderInMemory


def checkPingF(obj: Any) -> None:
	if not isinstance(obj, dict):
		raise TypeError(f"Expected dict, got {type(obj).__name__}")
	if "brencher" not in obj or "brencher2" not in obj:
		raise ValueError("Dictionary must contain both 'brencher' and 'brencher2' keys")
	for v in obj['brencher']['pipeline']:
		if ('name' not in v or v['name'] != "UrlCheck") and "Exception" in json.dumps(v):
			raise Exception(f"brencher check failed for: {v}")
	for v in obj['brencher2']['pipeline']:
		if ('name' not in v or v['name'] != "UrlCheck") and "Exception" in json.dumps(v):
			raise Exception(f"brencher2 check failed for: {v}")


clone = GitClone()

dockerSwarmCheck = DockerSwarmCheck(
	stack_name="brencher2",
)

unmerge = GitUnmerge(clone, dockerSwarmCheck)

state = SharedStateHolderInMemory(unmerge)

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
		"services": {
			"brencher-backend": {
				"environment": {
					"PROFILES": "brencher"
				},
				"ports": [
					"5002:5001"
				]
			}
		}
	},
	stack_name="brencher2",
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
		"App100": "http://100.70.193.97:5002/",
		"Status100": "http://100.70.193.97:5002/state",
	}
})

__all__ = ["brencher2"]

brencher2 = Environment(
	id="brencher2",
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
