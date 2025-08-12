# UI Requirements

## Branch List
- Display list of branches in all git repositories
- Each branch has a checkbox

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

## Use Cases

- As a user, I want 
    to see a list of all branches in all git repositories, 
    so I can select which ones to include in my environment.
- As a user, I want 
    to check or uncheck branches, so I can control which branches are present in my environment.
- As a user, I want 
    the branch list to refresh automatically every 5 minutes, so I always see the latest branches.
- As a user, I want 
    the pipeline to update in the UI whenever the environment changes, 
    so I can track progress and status.
- As a user, I want 
    to receive real-time updates and errors from the backend via websockets, 
    so I am always informed of the current state and any issues.
- As a user, I want 
    to see clear error messages in the UI if a request fails or the backend returns an error, 
    so I can quickly address problems.

### Updated state of environment should be sent to server via websocket in cases
- When I check or uncheck a branch