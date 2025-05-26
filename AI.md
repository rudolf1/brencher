Use language kotlin multiplatform.
Backend server ktor

Project connecting to git repository and fetching all branches.
Git repository configured on backend side.
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

Usecases:
1. User can add or remove branches to Release.
When user clicks on "Create Release" button, this DTO should be sent to server.
2. User can select branches and click "Remove Release" button.
When user clicks on "Remove Release" button, this DTO should be sent to server.
3. User can change branches of Release.
When user clicks checkbox next to branch name, this DTO should be sent to server.
4. User can change state of Release.
When user clicks on "Change State" button, this DTO should be sent to server.
5. User can change environment of Release.
When user clicks on "Change Environment" button, this DTO should be sent to server.

