# REST API Specifications



## WebSocket Endpoints
- /ws/branches: Backend to UI socket. Send all branches on new connection and un each update
- /ws/environment: Bidirectional socket of EnvironmentDto. Backend should send all environment dtos for new connections and for each update.
- /ws/errors: Receives errors to display


## DTOs
- Branches in format Dict[envName, List[branchName]]

- EnvironmentDto: (stored in file environment.py)
    id: str
    branches: List[Tuple[str, str]]
    state: str  # 'Active' or 'Pause'
    pipeline: Dict[str, Any]

