# Python Type Checking and Linting Guide

This project enforces type annotations for all Python code to maintain code quality, readability, and catch potential bugs early.

## Tools Used

### mypy
We use [mypy](https://mypy.readthedocs.io/) as our primary type checker. It ensures that all functions have type annotations for parameters and return values.

### flake8
We use [flake8](https://flake8.pycqa.org/) for code style checking.

## Running Linters Locally

### Prerequisites
Ensure you have all dependencies installed:

```bash
# Using pip
pip install -r requirements.txt

# Or using uv (recommended for this project)
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

### Running mypy

To check type annotations in the backend code:

```bash
mypy backend --config-file mypy.ini
```

To check a specific file:

```bash
mypy backend/app.py --config-file mypy.ini
```

### Running flake8

To check code style:

```bash
# Check for critical errors
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Full check with warnings
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
```

### Running All Checks

You can run all linting checks at once:

```bash
# Type checking
mypy backend --config-file mypy.ini

# Code style
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

## VSCode Integration

### Recommended Extensions

Install the following VSCode extensions for the best development experience:
- **ms-python.python** - Python language support
- **ms-python.vscode-pylance** - Advanced Python IntelliSense
- **ms-python.mypy-type-checker** - mypy integration for real-time type checking

These are already configured in `.vscode/extensions.json`. VSCode will prompt you to install them when you open the project.

### VSCode Settings

The project includes pre-configured VSCode settings in `.vscode/settings.json` that:
- Enable mypy linting
- Configure mypy to use the project's `mypy.ini` configuration
- Set up Pylance for type checking assistance
- Enable workspace-wide diagnostics

### Real-time Type Checking in VSCode

With the recommended extensions installed:
1. Open any Python file
2. Type errors will be highlighted in real-time
3. Hover over any type error to see the mypy message
4. Use "Problems" panel (View → Problems) to see all type errors

## Type Annotation Requirements

All functions must have type annotations:

### ✅ Good Examples

```python
def process_data(name: str, count: int) -> dict[str, int]:
    return {"name": name, "count": count}

def fetch_user(user_id: int) -> Optional[User]:
    # Implementation
    pass

class MyClass:
    def __init__(self, value: str) -> None:
        self.value = value
    
    def get_value(self) -> str:
        return self.value
```

### ❌ Bad Examples (Will Fail mypy)

```python
# Missing return type annotation
def process_data(name: str, count: int):
    return {"name": name, "count": count}

# Missing parameter type annotations
def fetch_user(user_id) -> Optional[User]:
    pass

# No type annotations at all
def calculate(x, y):
    return x + y
```

## Configuration

### mypy.ini

The project's mypy configuration is in `mypy.ini` at the root. Key settings:

- `disallow_untyped_defs = True` - Requires type annotations on all functions
- `disallow_incomplete_defs = True` - All parameters and return values must be typed
- `check_untyped_defs = True` - Type-check functions even if they lack annotations
- `warn_return_any = False` - Allows returning Any types (less strict)

### Per-module Configuration

Third-party libraries without type stubs are configured to ignore missing imports:
- git
- docker
- flask_socketio
- dotenv
- yaml

## Continuous Integration

Type checking runs automatically on every push and pull request via GitHub Actions. The CI workflow:

1. Installs dependencies (including mypy)
2. Runs flake8 for syntax and style checks
3. **Runs mypy for type checking**
4. Runs pytest for unit tests

The build will fail if:
- There are syntax errors (flake8)
- Type annotations are missing or incorrect (mypy)
- Tests fail (pytest)

## Common Type Checking Issues

### Issue: "Function is missing a type annotation"
**Solution:** Add type annotations to all parameters and return value:
```python
# Before
def my_func(x, y):
    return x + y

# After
def my_func(x: int, y: int) -> int:
    return x + y
```

### Issue: "Missing return statement"
**Solution:** Add explicit return or use `-> None`:
```python
# Before
def process():
    print("Processing")

# After
def process() -> None:
    print("Processing")
```

### Issue: "Incompatible return value type"
**Solution:** Ensure return type matches the annotation:
```python
# Before
def get_count() -> int:
    return "5"  # Wrong type!

# After
def get_count() -> int:
    return 5
```

### Issue: "Library has no type stubs"
**Solution:** Add to mypy.ini:
```ini
[mypy-library_name.*]
ignore_missing_imports = True
```

## Best Practices

1. **Always annotate function signatures** - Include types for all parameters and return values
2. **Use Optional for nullable values** - `Optional[str]` instead of `str | None` for clarity
3. **Import types from typing** - Use `from typing import List, Dict, Optional, Any`
4. **Use specific types** - Prefer `list[str]` over `list` or `Any`
5. **Document complex types** - Add comments for complex type annotations
6. **Run mypy before committing** - Catch type errors early
7. **Fix type errors, don't ignore them** - Use `# type: ignore` sparingly and with good reason

## Additional Resources

- [mypy documentation](https://mypy.readthedocs.io/)
- [Python typing module](https://docs.python.org/3/library/typing.html)
- [PEP 484 - Type Hints](https://www.python.org/dev/peps/pep-0484/)
- [Real Python - Python Type Checking Guide](https://realpython.com/python-type-checking/)
