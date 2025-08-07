# UI Requirements

## Branch List
- Display list of branches in all git repositories
- Each branch has a checkbox (selected or unselected)
- Branch checkbox should be checked if this branch present in EnvironmentDto

## Branch Refresh
- Branches are fetched from server on startup and refreshed every 5 minutes


## Environment Editing
- EnvironmentDto properties editable by user:
    branches
    state

## Environment State
- On each update for EnvironmentDto render pipeline on right conlumn on UI

## Communication and errors
- UI communicates with backend using websocket with class-based mapping
- UI receives environment updates via websocket
- UI receives errors via websocket to display
- UI should handle websocket events for environment updates and errors
- UI should provide feedback for failed requests and backend errors
- If request fails, show error message in bar
- If backend response is not 2xx, display error with message from response
