Use language kotlin multiplatform.
Backend server ktor.
All backend configuration stored in ktor config.


Project connecting to git repository and fetching all branches.
Git repository configured on backend side:
- url
- Authentication username (optional, stored in local.conf)
- Authentication password (optional, stored in local.conf)


Branches fetched on server side on start and refreshing each 5 minutes.

On UI user should see entites:
    Branches - all branches present in git repository

    Release
    - Name of release
    - Desired state. Available values: Pause, Active
    - Desired environment. 
    - list of all branches with checkboxes

    Environment
    - Name of environment
    - Configuration of environment. Editable json object

UI Communicates with server using ktor http client with class based mapping.
If request failed, show error message in bar. If response to backend is not 2xx status code, raise error with message from response.
UI receiving Releases updates by websockets.
UI receiving errors by websockets to display.


Usecases:
1. User can add or remove branches to Release.
When user clicks on "Create Release" button, this DTO should be sent to server.
2. User can select branches and click "Remove Release" button.
When user clicks on "Remove Release" button, this DTO should be sent to server.
3. User can change branches of each specific Release.
When user changes checkbox next to branch name, Release DTO should be sent to server.
4. User can change state of Release.
When user clicks on "Change State" button, this DTO should be sent to server.
5. User can change environment of Release.
When user clicks on "Change Environment" button, this DTO should be sent to server.

# Backend processing:

Hold releases state in kotlin flow.
Each job process each ReleaseDto event in flow.
As input it takes field <input>.
Result saved to field of ReleaseDto and decalred in <Output> section. 
After processing new ReleaseDto save it to state via compareAndSet.


## CreateOrGetBranchJob
### Kotlin class 
    CreateOrGetBranchJob
### Input
    release.branches
### Output
    release.mergedBranch
    Result type: <branch name> and <commit name>
### Logic

    Find any branch `auto/<hash>`:
    - It is merged state of commits pointed by <release.branches>
    - If found, set branch name and commit to <output>, and finish.
    - Creates a new temporary branch for merging.
    - All selected branches are merged into this temporary branch. If merge conflicts occur, the backend should handle them according to predefined rules (e.g., fail the operation and notify the user, or attempt an automatic merge if possible).
    - After a successful merge, the backend creates or updates a branch named `auto/<hash>`, where `<hash>` is a deterministic hash generated from the commit names of the branches (e.g., using SHA-1 or MD5 on the sorted branch names).
    - The merged result in the `auto/<hash>` branch is pushed to the remote git repository.
    - If failed, save result to <output>

## GradleJobBuild
### Kotlin class 
    GradleBuild
### Input
    release.mergedBranch
### Output
    release.buildVersion, release.artifactUrls
### Logic

    - Checkout <release.mergedBranch> to temporary folder.
    - Use <release.merged> name to calculate <release.buildVersion>. Use first 5 characters.
    - Set version to gradle project to <release.buildVersion>.
    - Extract docker image names from gradle modules. It will be <release.artifactUrls>.
    - Check images with versions exists in registry.
    - If images not exists, execute `gradle jib`.
    - If failed, save result to <output>

