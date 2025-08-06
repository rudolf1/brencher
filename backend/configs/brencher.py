from steps.git import GitClone
from steps.git import CheckoutMerged
from steps.docker import DockerComposeBuild
from steps.docker import DockerComposeDeploy
from enironment import Environment
from typing import List, Dict, Any, Optional
from steps.step import AbstractStep

brencher = Environment(
    id="brencher",
    branches=[],
    state="Pause",
    repo="https://github.com/rudolf1/brencher.git",
    pipeline=lambda e: pipeline(e)
)

def pipeline(env: Environment) -> List[AbstractStep]:
    clone = GitClone()
    checkoutMerged = CheckoutMerged() #wd=lambda: clone.repo, env.branches)
    buildDocker = DockerComposeBuild() #wd=lambda: clone.path, version=lambda: checkoutMerged.version)
    deployDocker = DockerComposeDeploy() #version=lambda: checkoutMerged.version)
    return [
        clone,
        checkoutMerged,
        buildDocker,
        deployDocker
    ]


