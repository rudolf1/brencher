import os
import json
import time
import threading
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from steps.step import AbstractStep
from dotenv import load_dotenv
import enironment
from steps.git import GitClone
import logging
from dataclasses import asdict
from typing import List, Dict, Any, Optional, Tuple, Set
import traceback
from typing import TypeVar
import websockets
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv("local.env")
load_dotenv('/run/secrets/brencher-secrets')


class DataclassJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if hasattr(o, '__dataclass_fields__'):
            return asdict(o)
        if isinstance(o, BaseException):
            return str(o)
        try:
            return super().default(o)
        except TypeError:
            return str(o)


def custom_json_dumps(obj: Any) -> str:
    return json.dumps(obj, cls=DataclassJSONEncoder)


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '../frontend')

# In-memory state
environments: Dict[str, Tuple[enironment.Environment, List[AbstractStep]]] = {}
environments_slaves: Dict[str, Tuple[enironment.Environment, List[AbstractStep]]] = {}
branches: Dict[str, Dict[str, Any]] = {}
branches_slaves: Dict[str, Dict[str, Any]] = {}
state_lock = threading.Lock()

# WebSocket connection managers
branches_connections: Set[WebSocket] = set()
environment_connections: Set[WebSocket] = set()
error_connections: Set[WebSocket] = set()


# Static file serving
@app.get("/")
async def serve_index() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, 'index.html'))


@app.get("/state")
async def serve_state() -> Response:
    return Response(content=custom_json_dumps(get_global_envs_to_emit()), media_type="application/json")


@app.get("/{path:path}")
async def serve_static(path: str) -> FileResponse:
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(FRONTEND_DIR, 'index.html'))


# --- Utility Functions ---
T = TypeVar('T')


def merge_dicts(a: Dict[str, T], b: Dict[str, T]) -> Dict[str, T]:
    result: Dict[str, T] = {}
    for k in (a.keys() | b.keys()):
        if k not in a or k not in b:
            result[k] = a.get(k, b.get(k))  # type: ignore[assignment]
            continue
        if (
            isinstance(a[k], dict)
            and isinstance(b[k], dict)
        ):
            result[k] = merge_dicts(a[k], b[k])  # type: ignore[arg-type,assignment]
        else:
            result[k] = b[k]
    return result


def get_local_envs_to_emit() -> Dict[str, Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    env_dtos: Dict[str, Tuple[Dict[str, Any], List[Dict[str, Any]]]] = {}
    for e, p in environments.values():
        env = asdict(e)
        res: List[Dict[str, Any]] = []
        for r in p:
            if isinstance(r.result_obj, BaseException):
                stack = traceback.format_exception(type(r.result_obj), r.result_obj, r.result_obj.__traceback__)
                res.append({
                    "name": r.name,
                    "status": [str(r.result_obj), stack],
                })
            else:
                res.append({
                    "name": r.name,
                    "status": r.result_obj
                })
        env_dtos[env['id']] = (env, res)
    return env_dtos


def get_global_envs_to_emit() -> Any:
    global environments, environments_slaves
    local_envs = get_local_envs_to_emit()
    merge_result = merge_dicts(local_envs, environments_slaves)  # type: ignore[misc]
    common_keys = set(local_envs.keys()) & set(environments_slaves.keys())
    if len(common_keys) > 0:
        # Schedule broadcast in event loop
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(broadcast_error({'message': f"Conflict: both master and slave have environment with id {common_keys}"}))
        except:
            pass
    return merge_result


environment_update_event = threading.Event()


# --- WebSocket Broadcasting Functions ---
async def broadcast_to_connections(connections: Set[WebSocket], event: str, data: Any) -> None:
    """Broadcast message to all connected clients"""
    disconnected = set()
    message = custom_json_dumps({"event": event, "data": data})
    
    for websocket in list(connections):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending to websocket: {e}")
            disconnected.add(websocket)
    
    # Remove disconnected clients
    for ws in disconnected:
        connections.discard(ws)


async def broadcast_branches(data: Any) -> None:
    await broadcast_to_connections(branches_connections, "branches", data)


async def broadcast_environments(data: Any) -> None:
    await broadcast_to_connections(environment_connections, "environments", data)


async def broadcast_error(data: Any) -> None:
    await broadcast_to_connections(error_connections, "error", data)


# --- WebSocket Endpoints ---
@app.websocket("/ws/branches")
async def websocket_branches(websocket: WebSocket) -> None:
    await websocket.accept()
    branches_connections.add(websocket)
    
    try:
        # Send initial data
        await websocket.send_text(custom_json_dumps({
            "event": "branches",
            "data": merge_dicts(branches, branches_slaves)
        }))
        
        # Listen for updates
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("event") == "update":
                # Handle update request
                await broadcast_branches(merge_dicts(branches, branches_slaves))
    except WebSocketDisconnect:
        branches_connections.discard(websocket)
    except Exception as e:
        logger.error(f"WebSocket error in /ws/branches: {e}")
        branches_connections.discard(websocket)


@app.websocket("/ws/environment")
async def websocket_environment(websocket: WebSocket) -> None:
    await websocket.accept()
    environment_connections.add(websocket)
    
    try:
        # Send initial data
        await websocket.send_text(custom_json_dumps({
            "event": "environments",
            "data": get_global_envs_to_emit()
        }))
        
        # Listen for updates
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("event") == "update":
                update_data = message.get("data", {})
                
                logger.info(f"Received environment update: {update_data}")
                
                for e, _ in environments.values():
                    if e.id == update_data.get('id'):
                        e.branches = update_data.get('branches', e.branches)
                        logger.info(f"Updated environment {e.id} branches to {e.branches}")
                
                environment_update_event.set()
                
                # Forward to slave if connected
                if slave_ws_task is not None:
                    await slave_send_queue.put({"event": "update", "data": update_data})
                
                # Broadcast to all clients
                await broadcast_environments(get_global_envs_to_emit())
    except WebSocketDisconnect:
        environment_connections.discard(websocket)
    except Exception as e:
        logger.error(f"WebSocket error in /ws/environment: {e}")
        environment_connections.discard(websocket)


@app.websocket("/ws/errors")
async def websocket_errors(websocket: WebSocket) -> None:
    await websocket.accept()
    error_connections.add(websocket)
    
    try:
        # Listen for errors (mostly just broadcasts)
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("event") == "error":
                await broadcast_error(message.get("data"))
    except WebSocketDisconnect:
        error_connections.discard(websocket)
    except Exception as e:
        logger.error(f"WebSocket error in /ws/errors: {e}")
        error_connections.discard(websocket)


# --- Slave Connection ---
slave_ws_task: Optional[asyncio.Task] = None
slave_send_queue: asyncio.Queue = asyncio.Queue()
slave_url = os.getenv('SLAVE_BRENCHER')


async def connect_to_slave() -> None:
    """Connect to slave brencher instance via WebSocket"""
    global branches_slaves, environments_slaves
    
    if not slave_url:
        return
    
    logger.info(f"SLAVE_BRENCHER set, will connect to master at {slave_url}")
    
    while True:
        try:
            # Convert HTTP URL to WebSocket URL
            ws_url_branches = slave_url.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/branches'
            ws_url_env = slave_url.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/environment'
            ws_url_errors = slave_url.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/errors'
            
            # Connect to all endpoints
            async with websockets.connect(ws_url_branches) as ws_branches, \
                       websockets.connect(ws_url_env) as ws_env, \
                       websockets.connect(ws_url_errors) as ws_errors:
                
                logger.info("Connected to slave WebSockets")
                
                # Handle messages from slave
                async def handle_branches() -> None:
                    async for message in ws_branches:
                        data = json.loads(message)
                        if data.get("event") == "branches":
                            branches_slaves = data.get("data", {})
                            await broadcast_branches(merge_dicts(branches, branches_slaves))
                
                async def handle_env() -> None:
                    async for message in ws_env:
                        data = json.loads(message)
                        if data.get("event") == "environments":
                            environments_slaves = data.get("data", {})
                            await broadcast_environments(get_global_envs_to_emit())
                
                async def handle_errors() -> None:
                    async for message in ws_errors:
                        data = json.loads(message)
                        if data.get("event") == "error":
                            await broadcast_error(data.get("data"))
                
                async def handle_sends() -> None:
                    while True:
                        msg = await slave_send_queue.get()
                        await ws_env.send(json.dumps(msg))
                
                # Run all handlers concurrently
                await asyncio.gather(
                    handle_branches(),
                    handle_env(),
                    handle_errors(),
                    handle_sends(),
                    return_exceptions=True
                )
                        
        except Exception as e:
            logger.error(f"Could not connect to SLAVE_BRENCHER {slave_url}: {e}")
            await asyncio.sleep(60)


# --- Background Tasks ---
def emit_fresh_branches_sync() -> None:
    """Refresh branches from git repositories (sync version for thread)"""
    global branches, branches_slaves, environments
    for k, e in environments.items():
        env, pipe = e
        branches[k] = {}
        for step in pipe:
            try:
                if not isinstance(step, GitClone):
                    continue
                branches[k] = {**step.get_branches()}
                env.branches = [x for x in env.branches if x[0] in branches[env.id].keys()]
            except BaseException as e:
                # Schedule async broadcast
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(broadcast_error({'message': str(e)}))
                except:
                    pass
        logger.info(f"Fetched {env.id}: {len(branches[env.id])} branches")
    
    # Schedule async broadcast
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(broadcast_branches(merge_dicts(branches, branches_slaves)))
    except:
        pass


def processing_thread_func() -> None:
    """Background thread for processing jobs"""
    while True:
        import processing
        
        def emit_envs() -> None:
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(broadcast_environments(get_global_envs_to_emit()))
            except Exception as e:
                logger.error(f"Error emitting environments: {str(e)}")
        
        with state_lock:
            logger.error(f"Processing")
            processing.process_all_jobs(list(environments.values()), lambda: emit_envs())
            emit_fresh_branches_sync()
        
        environment_update_event.wait(timeout=1*60)
        environment_update_event.clear()


# --- Startup and Shutdown Events ---
@app.on_event("startup")
async def startup_event() -> None:
    """Initialize application on startup"""
    global environments, slave_ws_task
    
    import signal
    
    def sigchld_handler(signum, frame):  # type: ignore[no-untyped-def]
        """Reap zombie processes"""
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break
            except ChildProcessError:
                break
    
    # Register the handler
    signal.signal(signal.SIGCHLD, sigchld_handler)
    
    import configs.brencher
    import configs.brencher2
    import configs.brencher_local2
    import configs.brencher_local1
    import configs.torrserv_proxy
    import configs.immich
    
    environments_l = [
        configs.brencher.brencher,
        configs.brencher2.brencher,
        configs.brencher_local2.brencher_local,
        configs.brencher_local1.brencher_local,
        configs.torrserv_proxy.config,
        configs.immich.config,
    ]
    environments = {e[0].id: e for e in environments_l}
    
    cli_env_ids_list = sys.argv[1:]
    cli_env_ids_str: str
    if len(cli_env_ids_list) == 0:
        cli_env_ids_str = os.getenv('PROFILES', '')
    else:
        cli_env_ids_str = cli_env_ids_list[0]
    
    logger.info(f"cli_env_ids {cli_env_ids_str}")
    if len(cli_env_ids_str) > 0 and cli_env_ids_str[0] == '-':
        cli_env_ids = cli_env_ids_str[1:].split(',')
        cli_env_ids = [x for x in cli_env_ids if len(x) > 0]
        logger.info(f"cli_env_ids (minus) {cli_env_ids}")
        if cli_env_ids and len(cli_env_ids) > 0:
            environments = {k: e for k, e in environments.items() if k not in cli_env_ids}
    else:
        cli_env_ids = cli_env_ids_str.split(',')
        cli_env_ids = [x for x in cli_env_ids if len(x) > 0]
        logger.info(f"cli_env_ids {cli_env_ids}")
        if cli_env_ids and len(cli_env_ids) > 0:
            environments = {k: e for k, e in environments.items() if k in cli_env_ids}
    
    if 'dry' in sys.argv[1:]:
        for id, e in environments.items():
            e[0].dry = True
    
    logger.info(f"Resulting profiles {environments.keys()}")
    
    # Start processing thread
    processing = threading.Thread(target=processing_thread_func, daemon=True)
    processing.start()
    
    # Start slave connection if configured
    if slave_url:
        slave_ws_task = asyncio.create_task(connect_to_slave())


if __name__ == '__main__':
    import uvicorn
    
    port = 5000 if 'noweb' in sys.argv[1:] else 5001
    uvicorn.run(app, host='0.0.0.0', port=port, log_level='info')
