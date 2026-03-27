from enironment import Environment
from steps.checks import SimpleLog, UrlCheck
from steps.docker import DockerComposeBuild, DockerSwarmCheck, DockerSwarmDeploy
from steps.git import GitClone, CheckoutMerged, GitUnmerge

clone = GitClone(branchNamePrefix="immoscout")
checkoutMerged = CheckoutMerged(clone,
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

checkPing = UrlCheck(
	url="https://gmail_mcp.rudolf.keenetic.link",
	expected={},
)
logUrls = SimpleLog(message={
	"userLinks": {
		"App": "https://gmail_mcp.rudolf.keenetic.link",
	}
})

__all__ = ["gmail_mcp"]
gmail_mcp = Environment(
	id="gmail_mcp",
	branches=[("immoscout/main", "HEAD")],
	dry=False,
	repo="https://github.com/rudolf1/uber_backup.git",
	pipeline=[
		clone,
		checkoutMerged,
		buildDocker,
		dockerSwarmCheck,
		unmerge,
		deployDocker,
		checkPing,
		logUrls
	]
)
