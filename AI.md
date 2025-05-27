Use language kotlin multiplatform.
Backend server ktor.
All backend configuration stored in ktor config.


Project connecting to git repository and fetching all branches.
Git repository configured on backend side:
- url
- Authentication username (optional)
- Authentication password (optional)


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


Create kotlin channel which subscribes to Release state.

Create separate job, which subscribes to this channel. 
For each update to a Release and its corresponding environment, the backend performs the following steps:

- If `auto/<hash>` branch reflects the latest merged state of the selected branches for that Release, do nothing
- **Receive DTO**: The backend receives a DTO representing the updated Release, including the list of selected branches and the target environment.

- **Merge Branches**:
    - The backend checks out the latest versions of the selected branches from the configured git repository.
    - It creates a new temporary branch for merging.
    - All selected branches are merged into this temporary branch. If merge conflicts occur, the backend should handle them according to predefined rules (e.g., fail the operation and notify the user, or attempt an automatic merge if possible).

- **Create Auto Branch**:
    - After a successful merge, the backend creates or updates a branch named `auto/<hash>`, where `<hash>` is a deterministic hash generated from the commit names of the branches (e.g., using SHA-1 or MD5 on the sorted branch names).

- **Push to Repository**:
    - The merged result in the `auto/<hash>` branch is pushed to the remote git repository.

- **Notify UI**:
    - The backend sends a response or notification to the UI via websockets indicating the operation's success or failure, including any relevant details (e.g., new branch name, errors).

