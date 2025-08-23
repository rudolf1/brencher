# Brencher - Automated Branch Merger and CI/CD Pipeline

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

Brencher is a Python Flask web application that automatically merges Git branches, builds Docker images, and deploys to Docker Swarm. It provides a real-time web interface for monitoring branch processing pipelines and managing deployment environments.

## Working Effectively

### Environment Setup and Dependencies
- **NEVER CANCEL BUILDS OR LONG-RUNNING COMMANDS** - Set timeouts of 60+ minutes for all setup and build commands
- Install uv tool: `pip install uv` (takes ~30 seconds)
- Create virtual environment: `cd /path/to/brencher && uv venv .venv` (takes ~15 seconds)
- Activate environment: `source .venv/bin/activate`
- Install dependencies: `uv pip install -r requirements.txt` (takes ~60 seconds, NEVER CANCEL)
- Install linting/testing tools: `pip install flake8 pytest` (takes ~30 seconds)

### Running the Application
- **Basic web application**: `python backend/app.py` - starts on port 5001 with all environments
- **Specific environment**: `python backend/app.py brencher_local` - runs only the brencher_local profile
- **Dry run mode**: `python backend/app.py brencher_local dry` - prevents actual deployments
- **Headless mode**: `python backend/app.py brencher_local dry noweb` - runs without web interface
- **Exclude environments**: `python backend/app.py -brencher` - runs all except brencher environment

### Build and Deployment
- **Docker build**: `docker build -t brencher:latest .` 
  - **TIMING**: Takes 10-15 minutes when working. NEVER CANCEL. Set timeout to 30+ minutes.
  - **KNOWN ISSUE**: May fail with SSL certificate errors in some environments - document as limitation
- **Docker Swarm deployment**: Requires `docker swarm init` to be run first
  - Application will show Docker Swarm errors if swarm is not initialized (expected in development)

## Validation and Testing

### Linting
- Run critical error checks: `flake8 backend/ --count --select=E9,F63,F7,F82 --show-source --statistics`
  - **Expected**: Minor F824 warnings about unused global variables (non-critical, can be ignored)
  - **Exit code 1**: Normal when warnings exist, not a failure
- Run full linting: `flake8 backend/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics`
- **TIMING**: Linting takes 5-10 seconds

### Testing
- Run tests: `pytest`
- **Current state**: No tests exist, but pytest infrastructure is available
- **Exit code 5**: Normal when no tests are found, not a failure
- **TIMING**: Test discovery takes <5 seconds when no tests exist

### Manual Validation Scenarios
- **Always test the web interface**: Access http://localhost:5001 when running with web mode
  - **Expected**: Web interface loads with "Brencher - Branch Merger" title
  - **Note**: May show "Loading branches..." if socket.io CDN is blocked (backend still works)
- **Branch selection workflow**: 
  1. Start app: `python backend/app.py brencher_local dry`
  2. Check logs for: "Fetched brencher_local: 8 branches" (appears within 30 seconds)
  3. Verify Git cloning and branch merging activity in logs
  4. Expect Docker Swarm errors every 60 seconds (normal in development)
- **Environment processing**: Monitor logs for Git clone, branch merging, and Docker build steps
  - **Git operations**: Look for "Cloning repository", "Selected branches", "Merging commit"
  - **Docker operations**: Look for "Building image" or "Image already exists locally"

## Timing Expectations and Timeout Guidelines

- **Environment setup**: 2-3 minutes total - NEVER CANCEL
- **Application startup**: 5-10 seconds for basic startup, 30 seconds for full branch loading
- **Git operations**: 10-30 seconds per repository clone/fetch
- **Docker builds**: 10-15 minutes for full builds - **CRITICAL**: Set timeout to 30+ minutes, NEVER CANCEL
- **Processing cycles**: Application processes environments every 60 seconds
- **Branch refresh**: Automatic every 5 minutes (300 seconds)

## Key Project Structure

### Core Application Files
- `backend/app.py` - Main Flask application entry point
- `backend/configs/` - Environment configurations (brencher.py, brencher_local.py)
- `backend/steps/` - Processing pipeline steps (git.py, docker.py, gradle_build.py)
- `frontend/` - JavaScript web interface files
- `requirements.txt` - Python dependencies managed with uv
- `Dockerfile` - Container build definition
- `docker-compose.yml` - Docker Swarm deployment configuration

### Configuration Files
- `backend/configs/brencher.py` - Production environment configuration  
- `backend/configs/brencher_local.py` - Local development environment configuration
- Each config defines Git repositories, branches to merge, and deployment pipelines

### Important Directories Always Check
- When modifying pipeline steps, always check `backend/steps/` directory
- When updating environment configs, check `backend/configs/` directory  
- When changing web interface, check `frontend/` directory
- Always check `docker-compose.yml` when modifying deployment settings

## Common Development Tasks

### Adding New Environment
1. Create new file in `backend/configs/[env_name].py`
2. Follow pattern from existing configs (brencher.py, brencher_local.py)
3. Import in `backend/app.py` and add to environments list
4. Test with: `python backend/app.py [env_name] dry noweb`

### Modifying Pipeline Steps  
1. Edit files in `backend/steps/` directory
2. All steps inherit from BaseStep and must be idempotent
3. Test changes with dry run: `python backend/app.py [env] dry noweb`
4. Always verify Docker builds still work: `docker build -t test .`

### Frontend Changes
1. Edit files in `frontend/` directory (index.html, app.js, styles.css)
2. No build step required - files served directly by Flask
3. Test by running: `python backend/app.py brencher_local dry` and accessing http://localhost:5001
4. Verify WebSocket communication works for real-time updates

## Known Issues and Limitations

### Expected Failures in Development
- **Socket.io CDN blocking**: Web interface may show "Loading branches..." if socket.io CDN is blocked
  - Error: "Failed to load resource: net::ERR_BLOCKED_BY_CLIENT" or "io is not defined"
  - Application backend still functions correctly, only real-time UI updates are affected
- **Docker Swarm errors**: Normal when Docker Swarm is not initialized
  - Error: "This node is not a swarm manager. Use docker swarm init or docker swarm join"
  - **Frequency**: Appears every 60 seconds in logs during processing cycles
  - Solution: Either run `docker swarm init` or use dry mode to disable deployments
- **SSL Certificate errors in Docker builds**: May occur in some network environments
  - These are network/environment specific and not code issues
- **Minor linting warnings**: F824 unused global variable warnings exist but don't affect functionality
  - Exit code 1 from flake8 is normal when warnings exist

### Performance Notes
- Application uses background threads for processing - expect continuous log output
- Memory usage grows over time due to Git repository caching in /tmp
- Docker images are cached locally to speed up subsequent builds

## CI/CD Integration

### GitHub Actions Workflow
- Workflow file: `.github/workflows/python-package.yml`
- Tests Python 3.9, 3.10, 3.11 compatibility
- Runs flake8 linting and pytest (currently no tests)
- **Always run linting before commits**: `flake8 backend/` 

### Pre-commit Validation
- Always run: `flake8 backend/ --count --select=E9,F63,F7,F82 --show-source --statistics`
- Fix any critical errors before committing
- Verify application starts: `timeout 30 python backend/app.py brencher_local dry noweb`

## Common Command Reference

```bash
# Environment setup (run once)
pip install uv
cd /path/to/brencher
uv venv .venv
source .venv/bin/activate  
uv pip install -r requirements.txt
pip install flake8 pytest

# Development workflow
source .venv/bin/activate
python backend/app.py brencher_local dry  # Web interface
python backend/app.py brencher_local dry noweb  # Headless

# Validation
flake8 backend/ --count --select=E9,F63,F7,F82 --show-source --statistics
pytest
docker build -t brencher:test . # TAKES 10-15 MINUTES, SET 30+ MINUTE TIMEOUT

# Access web interface
# http://localhost:5001 (when running without noweb flag)
```

**CRITICAL REMINDERS**: 
- NEVER CANCEL long-running operations (builds, installs)
- Always set appropriate timeouts (30+ minutes for builds, 60+ minutes for complex operations)
- Always test both headless and web interface modes when making changes
- Expect Docker Swarm deployment errors in development environments without swarm initialization