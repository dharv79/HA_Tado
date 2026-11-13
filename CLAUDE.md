# HA_Tado

Home Assistant custom integration `tado_resume` (resume tado schedules; tado X and classic). Code in `custom_components/tado_resume/`, tests in `tests/` (`pytest`).

## Conventions
- Release: version lives in `custom_components/tado_resume/manifest.json`; release = push `release/<version>` branch (tag containing `bN` → prerelease), via `.github/workflows/release.yml`. Detail: `docs/RELEASING.md`.
- Roadmap: `docs/plan/PLAN.md` (index); read only the phase file being worked on. Release after each finished piece of work.

## Checks (run before committing; CI runs the same)
`ruff check .` · `ruff format .` · `mypy` · `pytest -q --cov --cov-fail-under=85`. Config in `pyproject.toml`.
