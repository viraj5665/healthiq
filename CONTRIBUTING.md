# Contributing to HealthIQ

Thank you for your interest in contributing!

## Getting started

1. Fork the repository and clone your fork
2. Follow the [Quickstart](README.md#quickstart) to get the stack running locally
3. Create a feature branch: `git checkout -b feat/your-feature`

## Development workflow

### Backend (Python)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload          # runs on :8000
pytest tests/ -v                       # run all tests
```

### Frontend (TypeScript)

```bash
cd dashboard
npm install
npm run dev                            # runs on :5173
```

The Vite dev server proxies `/api/*` to `http://localhost:8000` automatically.

## Code style

- **Python**: PEP 8, 4-space indent. Run `ruff check .` before committing.
- **TypeScript**: ESLint config in `dashboard/eslint.config.js`. Run `npm run lint`.
- Keep functions short and single-purpose. No inline comments unless the *why* is non-obvious.

## Adding a new agent

1. Create `agents/<name>/agent.py` with a class that has a `run(db) -> Result` method
2. Add a `@dataclass` result type
3. Mount a new router in `api/routers/<name>.py` and register it in `api/main.py`
4. Add unit tests in `tests/unit/test_<name>_agent.py`

## Adding a migration

Create `infra/migrations/00N_description.sql` (next number in sequence). Use `IF NOT EXISTS` and `IF EXISTS` guards so migrations are idempotent.

## Pull requests

- Keep PRs focused: one feature or fix per PR
- All tests must pass: `pytest tests/ -v`
- Include a short description of *what* and *why* in the PR body
- Screenshots for UI changes

## Reporting issues

Open a GitHub Issue with:
- Steps to reproduce
- Expected vs actual behaviour
- Python/Node versions and OS

## License

By contributing, you agree your contributions will be licensed under the [MIT License](LICENSE).
