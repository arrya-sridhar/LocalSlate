# Changelog 📋

All notable changes to the LocalSlate project will be documented in this file.

## [0.2.0] - 2026-06-28 (Phase 2 MVP)
### Added
- Completed **CLI Dashboard** built on `rich` rendering live queue sizes, active processes, system resources, and database entries.
- Created `queue_manager` managing lock files, hashes, file movement, and 120s timeouts for audio files.
- Built Local SLM wrapper with `llama-cpp-python` and validation parser using Pydantic schemas.
- Built faster-whisper local int8 transcription wrapper with OMP thread limit constraints.
- Generated `requirements.txt` with absolute hashes pinned for Python 3.11.
- Initialized local SQLite schema with database indexes for fast query lookup.

## [0.1.0] - 2026-06-28 (Phase 1 Specification)
### Added
- Initial specifications for pipeline flow, SQLite DDL database schemas, and model sizing criteria.
- GPL-2.0 copyleft `LICENSE` configuration.
- Comprehensive `README.md` defining setup, constraints, and architecture.
