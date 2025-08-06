# UI Requirements

## Branch List
- Display list of branches in all git repositories
- Each branch has a checkbox (selected or unselected)

## Branch Refresh
- Branches are fetched from server on startup and refreshed every 5 minutes

## Communication
- UI communicates with backend using websocket with class-based mapping
- UI receives environment updates via websocket
- UI receives errors via websocket to display

## Error Handling
- If request fails, show error message in bar
- If backend response is not 2xx, display error with message from response

## Environment Editing
- Environment is editable by user
- EnvironmentDto contains list of branches

## Environment State
- Display list of jobs from EnvironmentState

## DTOs
- EnvironmentDto: { branches: [string] }
- EnvironmentStateDto: { jobs: [JobDto] }

## Notes
- UI should handle websocket events for environment updates and errors
- UI should provide feedback for failed requests and backend errors
