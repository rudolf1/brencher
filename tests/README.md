# Integration Tests for git.py

This directory contains integration tests for the `CheckoutMerged` and `GitUnmerge` classes from `backend/steps/git.py`.

## Overview

The integration tests simulate real git operations in isolated temporary directories to ensure the git merge and unmerge functionality works correctly in various scenarios without affecting the host environment.

## Test Coverage

### CheckoutMerged Class Tests

1. **test_checkout_merged_two_branches** - Tests merging two branches successfully
2. **test_checkout_merged_three_branches** - Tests merging three branches successfully
3. **test_checkout_merged_fast_forward** - Tests merging with fast-forward (linear history)
4. **test_checkout_merged_conflicting_branches** - Tests that conflicting branches fail gracefully
5. **test_checkout_merged_existing_auto_branch** - Tests that existing auto branches are reused
6. **test_checkout_merged_empty_branches** - Tests that empty branch lists are rejected

### GitUnmerge Class Tests

1. **test_git_unmerge_valid_version** - Tests extracting branch information from valid version strings
2. **test_git_unmerge_invalid_version** - Tests handling of invalid version formats

## Running the Tests

### Option 1: Run in Docker (Recommended - Isolated Environment)

The tests can be run inside a Docker container to ensure complete isolation from the host system:

```bash
./run_integration_tests.sh
```

This script will:
1. Build a Docker image with all necessary dependencies
2. Run the integration tests inside a container
3. Clean up after completion

### Option 2: Run Locally

If you prefer to run tests locally (requires Python 3.11+ and git):

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/test_git_integration.py -v
```

### Option 3: Run Specific Tests

To run a specific test:

```bash
python -m pytest tests/test_git_integration.py::TestGitIntegration::test_checkout_merged_two_branches -v
```

## Test Scenarios Simulated

### Merge Scenarios

- **2 branches merge**: Creates two divergent branches from a common ancestor and merges them
- **3 branches merge**: Creates three divergent branches from a common ancestor and merges them
- **Fast-forward merge**: Tests merging when one branch is directly ahead of another
- **Conflicting branches**: Creates branches that modify the same file differently, expecting merge conflicts

### Repository Simulation

Each test:
1. Creates a temporary "remote" repository
2. Creates a temporary "local" clone
3. Simulates various branch scenarios
4. Executes the merge/unmerge operations
5. Verifies the results
6. Cleans up all temporary files

## CI Integration

These tests are integrated into the CI pipeline through the `python-package.yml` workflow, which runs pytest on every push and pull request.

## Dependencies

- Python 3.11+
- pytest
- gitpython
- git (system package)

All Python dependencies are specified in `requirements.txt`.
