from enironment import Environment
from steps.checks import SimpleLog, UrlCheck
from steps.docker import DockerComposeBuild, DockerSwarmCheck, DockerSwarmDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge
from steps.shared_state import SharedStateHolderInMemory

clone = GitClone(branchNamePrefix="immoscout")

dockerSwarmCheck = DockerSwarmCheck(
	stack_name="gmail_mcp",
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
                                 docker_compose_path="gmail-mcp-server/docker-compose.yml",
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
		"version": "auto-" + checkoutMerged.progress().version,
	},
	stack_name="gmail_mcp",
	docker_compose_path="gmail-mcp-server/docker-compose.yml",
)

checkPing1 = UrlCheck(
	url="http://100.70.193.97:3000/health",
	expected={ "ok": True, "service": "gmail-mcp-server" },
)
checkPing2 = UrlCheck(
	url="http://100.70.193.97:3001/health",
	expected={ "ok": True, "service": "telegram-mcp-server" },
)

logUrls = SimpleLog(message={
	"userLinks": {
		"AppGm": "http://100.70.193.97:3000/health",
		"AppTg": "http://100.70.193.97:3001/health",
	}
})

__all__ = ["gmail_mcp"]
gmail_mcp = Environment(
	id="gmail_mcp",
	state=state,
	repo="https://github.com/rudolf1/uber_backup.git",
	pipeline=[
		clone,
		state,
		checkoutMerged,
		buildDocker,
		dockerSwarmCheck,
		unmerge,
		deployDocker,
		checkPing1,
		checkPing2,
		logUrls
	]
)
