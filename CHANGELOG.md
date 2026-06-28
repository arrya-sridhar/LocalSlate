# Changelog

All notable changes to the LocalSlate project will be documented in this file.

## [2.0.0] - 2026-06-28

### Added
- **Full-Stack REST Architecture**: Created a proper FastAPI backend with clean routing, dependency injection, and centralized exception handling.
- **Vanilla SPA Frontend**: Designed a responsive, offline-friendly frontend UI dashboard with automatic dark-mode support using Vanilla HTML, CSS, and JS.
- **Write-Ahead Logging (WAL)**: Added WAL mode tuning and connection timeouts for the SQLite Database Service to support reliable concurrent operations.
- **Enhanced Status Monitoring**: Updated the `/status` API endpoint to return active CPU utilization, RAM usage, and database records count telemetry.
- **`pytest.ini` Configuration**: Integrated pytests pythonpaths to prevent `ModuleNotFoundError` during test collection.

### Changed
- **Directory Restructuring**: Refactored the code into a modular structure:
  - `backend/` for server logic and requirements.
  - `frontend/` for client-side assets.
  - `specs/` for architectural and operational specifications.
  - `tools/` and `tests/` for pipeline tools and test suites.
- **Render Deployment Support**: Separated lightweight dependencies into `backend/requirements-render.txt` to guarantee clean compilation on Render without local AI binaries.
