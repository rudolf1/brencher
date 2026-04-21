from enironment import Environment
from steps.checks import SimpleLog, UrlCheck
from steps.docker import DockerComposeBuild, DockerSwarmCheck, DockerSwarmDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge, ResolveInitialBranches

clone = GitClone(branchNamePrefix="immoscout")
resolveInitialBranches = ResolveInitialBranches(wd=clone, initial_branches=[("immoscout/main", "HEAD")])
checkoutMerged = CheckoutMerged(clone,
                                desired_branches=resolveInitialBranches,
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

dockerSwarmCheck = DockerSwarmCheck(
	stack_name="gmail_mcp",
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
unmerge = GitUnmerge(clone, dockerSwarmCheck)

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
	dry=False,
	repo="https://github.com/rudolf1/uber_backup.git",
	pipeline=[
		clone,
		resolveInitialBranches,
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
