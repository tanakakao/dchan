# Python environment

dchan uses uv for reproducible Python environments.

## Files under version control

- `pyproject.toml`: direct dependency requirements and optional dependency groups.
- `uv.lock`: exact resolved dependency graph. Commit this file together with dependency changes.
- `.python-version`: default Python version for the project (`3.12`).

The generated `.venv/` directory is local to each checkout and is not committed.

## Application environment

Install uv, then from the repository root run:

```bash
uv sync --locked
```

This creates or updates `.venv` from the committed lockfile. `--locked` fails instead of silently changing `uv.lock` when `pyproject.toml` and the lockfile do not agree.

Run commands in the same locked environment with, for example:

```bash
uv run --locked python -m uvicorn application.main:app
```

Development and test tools:

```bash
uv sync --locked --extra dev
```

## Updating dependencies

When dependencies intentionally change:

1. Edit `pyproject.toml`.
2. Run `uv lock`.
3. Review the `uv.lock` diff.
4. Run `uv sync --locked` and relevant tests.
5. Commit `pyproject.toml` and `uv.lock` together.

Do not hand-edit `uv.lock`.

The React frontend is managed separately with pnpm and `frontend/pnpm-lock.yaml`.
