# Contributing to LocalSlate 🤝

We operate under a structured, offline-first collaborative framework. Please follow these guidelines:

## 🌿 Branching Strategy
* Never commit directly to `main`.
* Create a developer branch (e.g., `sreeshanth` or `dev-1`) for all feature development.
* Merge changes into `main` using GitLab Merge Requests.

## ⚙️ Coding Standards
* We strictly follow the **10 pre-commit checks** configured in `.pre-commit-config.yaml` including `black` formatting, `ruff` linting, and `mypy` static type checking.
* Install pre-commit locally:
  ```bash
  pre-commit install
  ```

## 📝 Commit Guidelines
We use semantic commit messages to automatically build changesets:
* `feat:` New features (e.g. new UI panel)
* `fix:` Bug fixes (e.g. handling file locks)
* `docs:` Documentation edits (e.g. README or specs)
* `style:` Formatting edits (black, white spaces)
* `refactor:` Code changes that neither fix a bug nor add a feature

Thank you for keeping our codebase clean!
