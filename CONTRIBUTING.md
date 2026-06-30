# Contributing to LocalSlate

Thank you for contributing! Please review the guidelines below to ensure a smooth workflow.

---

## Development Setup

1. **Prerequisites**: Ensure you have Python 3.11 installed.
2. **Environment Ingestion**:
   ```bash
   pip install uv
   uv venv -p 3.11
   # Activate:
   # Windows:
   .venv\Scripts\activate
   # Mac/Linux:
   source .venv/bin/activate
   ```
3. **Install Dependencies**:
   ```bash
   uv pip install -r backend/requirements.txt
   ```

---

## Folder Architecture

All modifications should target:
- `backend/src/` for API endpoints, queue manager daemons, and database layers.
- `frontend/` for HTML templates, CSS grids, and vanilla JS controllers.

---

## Coding Standards

- **Formatter**: Code must be formatted using `black` and checked using `ruff`.
- **Typing**: All Python signatures should have type annotations validated by `mypy`.
- **Naming**: Use standard snake_case for functions and variables, and PascalCase for classes.

---

## Testing Workflows

Before proposing pull requests, run all verification suites:
1. **Ruff Lints**:
   ```bash
   ruff check backend/
   ```
2. **Format Check**:
   ```bash
   black --check backend/
   ```
3. **Type Check**:
   ```bash
   mypy backend/src/
   ```
4. **Pytest Suite**:
   ```bash
   .venv\Scripts\pytest
   ```
