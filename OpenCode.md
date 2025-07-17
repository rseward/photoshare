# PhotoShare Developer Guide

## Commands
- Build: `make build` or `uv pip install -r requirements.txt`
- Run app: `make run` or `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Run indexer: `make index` or `python indexer.py index`
- Run tests: `pytest`
- Run single test: `pytest tests/test_main.py::test_function_name -v`

## Code Style
- **Imports**: System imports first, then third-party, then local. Group imports logically.
- **Type Hints**: Use typing module (e.g., `Optional[str]`, `List[int]`).
- **Naming**: snake_case for variables/functions, PascalCase for classes.
- **Error Handling**: Always catch exceptions, log errors, and raise appropriate HTTPExceptions.
- **Docstrings**: Add docstrings to functions explaining purpose and parameters.
- **Logging**: Use the logging module for errors, info, and debug messages.
- **Environment Variables**: Use PHOTOSHARE_ prefix for all environment variables.
- **Database**: Use context managers for connections and handle SQLite errors explicitly.
- **Testing**: Create fixtures for reusable test setups. Use monkeypatch for environment variables.