# HA_Tado

Home Assistant custom integration `tado_resume` (resume tado schedules; tado X and classic). Code in `custom_components/tado_resume/`, tests in `tests/` (`pytest`).

## Conventions
- Release: version lives in `custom_components/tado_resume/manifest.json`; release = push `release/<version>` branch (tag containing `bN` → prerelease), via `.github/workflows/release.yml`. Detail: `docs/RELEASING.md`.
