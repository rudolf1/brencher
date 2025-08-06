from steps.git import GitClone
from steps.git import CheckoutMerged
from steps.docker import DockerComposeBuild
from steps.docker import DockerComposeDeploy
from enironment import Environment
from typing import List, Dict, Any, Optional, Tuple
from steps.step import AbstractStep

env = Environment(
    id="brencher",
    branches=["main"],
    state="Active",
    repo="https://github.com/rudolf1/brencher.git",
)


def create_pipeline(env: Environment) -> List[AbstractStep]:
    clone = GitClone(env)
    checkoutMerged = CheckoutMerged(clone, env.branches)
    buildDocker = DockerComposeBuild() #wd=lambda: clone.path, version=lambda: checkoutMerged.version)
    deployDocker = DockerComposeDeploy() #version=lambda: checkoutMerged.version)
    return [
        clone,
        checkoutMerged,
        buildDocker,
        deployDocker
    ]

brencher: Tuple[Environment, List[AbstractStep]] = (env, create_pipeline(env))

