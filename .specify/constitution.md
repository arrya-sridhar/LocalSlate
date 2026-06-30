# LocalSlate Constitution

## Principles

1. Offline-first operation is mandatory.
2. Core AI processing must run locally without external AI APIs.
3. User data must be stored safely and never exposed through logs.
4. The system must support structured incident extraction from unstructured input.
5. All changes must preserve tests, documentation, and deployment readiness.

## Technical Standards

- FastAPI backend
- Local/edge-first AI workflow
- MySQL or local database persistence
- Clear API documentation
- Secure environment variable handling
- No committed secrets

## Quality Gates

Every change should pass:

- Ruff
- MyPy
- Pytest
- Security scanning
- Dependency audit
- Coverage checks