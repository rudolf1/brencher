# Load environments from files in folder `configs`

# Backend Processing Logic

Hold environment in local.
Each job processes each EnvironmentDto event in flow.
As input it takes field <input>.
Result saved to field of EnvironmentDto and declared in <output> section.
After processing new EnvironmentDto save it to state via compareAndSet.

# Steps stored in folder `steps`

All steps must inherit from BaseStep and implement idempotent behavior. This means that:
- Each step should be able to safely run multiple times without changing the outcome beyond the first run
- Steps should check if their work has already been done and skip redundant operations
- All steps must handle edge cases and errors gracefully

## GitClone
### Input
    git url
### Logic
    - Inherits from BaseStep
    - Checks if repository is already cloned at the target location
    - If already cloned, performs a fetch to update the local repository
    - If not cloned, clones the repository to a temporary folder
    - Ensures the operation is idempotent by validating repository state

## CheckoutMerged
### Input
    `clone` object of type GitClone
    branches - list of branches to merge
### Logic    
    - Inherits from BaseStep
    - Find any branch `auto/<hash>`:
      - It is merged state of commits pointed by <environment.branches>
      - If found, verify the branch is up-to-date by comparing commit hashes of source branches
      - If branch exists but is outdated, update it with fresh merges
      - If valid and up-to-date, set branch name and commit to <output>, and finish
    - If no matching branch exists:
      - Creates a new temporary branch for merging
      - All selected branches are merged into this temporary branch. If merge conflicts occur, the backend should handle them according to predefined rules (e.g., fail the operation and notify the user, or attempt an automatic merge if possible)
      - After a successful merge, the backend creates a branch named `auto/<hash>`, where `<hash>` is a deterministic hash generated from the commit names of the branches (e.g., using SHA-1 or MD5 on the sorted branch names)
      - The merged result in the `auto/<hash>` branch is pushed to the remote git repository
    - Ensures idempotency by verifying the current state of branches and only performing necessary operations
    - If failed, save result to <output>

## GradleBuild
### Input
    checkout object of type CheckoutMerged
    task name - name of gradle task to execute
### Logic
    - Inherits from BaseStep
    - Checkout <environment.mergedBranch> to temporary folder, verifying if already checked out
    - Use <environment.merged> name to calculate <environment.buildVersion>. Use first 5 characters
    - Set version to gradle project to <environment.buildVersion>
    - Extract docker image names from gradle modules. It will be <environment.artifactUrls>
    - Check images with versions exists in registry
    - If images already exist with matching version and content, skip build step
    - If images do not exist or need updating, execute `gradle jib`
    - Ensures idempotency by verifying existing docker images before building
    - If failed, save result to <output>

## DockerBuild
### Input
    docker_compose_path - path to docker-compose file
    docker_repo_url - docker repository url
    docker_repo_username - username for docker repository
    docker_repo_password - password for docker repository
### Logic
    - Inherits from BaseStep
    - Reads the docker-compose file and parses all defined services with build contexts
    - For each service, builds the Docker image using the specified context and tags it with the appropriate version/tag
    - Authenticates to the docker repository using provided credentials
    - Pushes the built images to the docker repository
    - Ensures idempotency by checking if the image with the same tag already exists in the repository before building/pushing
    - If all images exist and match, skips build and push
    - If failed, save result to <output>

## DockerSwarmDeploy
### Logic
    Deploys to swarm service described in specified docker-compose.yaml

# TODOs
    - pipeline: add reverse flow. We need to understand what is deployed

    - pipeline: add health check.
    - pipeline: add teamcity support
    - pipeline: add udploy support
    - pipeline: fetch more frequently
    - pipeline: fetch Git steps, not in separate method
    - pipeline: Trigger next step only if result of previous changed.

    - version: leave only root commits. It will prevent redeploy in case already merged branch selected
    + git: No sense to generate branch name from hash. Used concatenation of root commits.

    - docker: skip if correct stack already deployed. Only image tags compared. Need more.
    - docker: I guess label for container should be added.
    - docker: Or find keys for docker swarm to skip deploy if no changes.

    - Write test to cover usecases.
    - Blocker!!! Not able to push in docker.
    - Blocker!!! Not able to push in git. Do not lookup local branches.
