# UI Requirements

# UI Requirements

## Branch List Display
- Display list of branches in all git repositories as a table format
- Each branch has a checkbox for deployment selection
- Branch name with environment context (production, development, staging)
- Desired commit selection with dropdown and custom input
- Current deployed commit ID display from GitUnmerge results

### Filter Functionality
- Filter textbox at the top of the branch table (empty by default)
- Branches are displayed based on:
  - Checked for deploy (always shown)
  - Unchecked but currently deployed (returned by GitUnmerge)
  - Filter text matches branch name, commit ID, or commit message

### Commit Selection
- Dropdown shows:
  - HEAD option with commit details (hash, author, message)
  - Individual commits in the branch
- Text input for custom commit IDs when "Custom Commit" is selected

## Data Structure
- Environment branch list format: Array of [branch_name, desired_commit] pairs
- desired_commit can be:
  - "HEAD" for latest commit
  - Full commit hash for specific commits
  - Custom commit ID entered by user

## Table Layout
- Borderless table with columns:
  1. Deploy (checkbox)
  2. Branch Name (with environment label)
  3. Desired Commit (dropdown + optional text input)
  4. Current Deployed (commit hash from GitUnmerge)

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

### Apply Changes Pattern
- Changes are tracked locally and "Apply Changes" button appears when modifications are detected
- Button submits all pending changes at once via websocket
- Server state tracking prevents unnecessary updates

