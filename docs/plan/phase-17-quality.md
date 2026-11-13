# Phase 17: Quality tooling (0.19.0)

Lint, type checks, validation.

## Scope
- Add ruff and mypy configuration, run in CI; add hassfest and HACS validation actions; coverage threshold.
- Document the commands in CLAUDE.md.

## Discovery
None.

## Exit criteria
CI fails on lint, type or manifest errors; existing tests pass.

## Outcome (0.19.0)
- `pyproject.toml`: ruff (E, F, W, I, B, UP, C4, SIM; line length 100, format) and mypy (`check_untyped_defs`, integration only); coverage over the integration.
- CI (`tests.yml`): separate `lint` (ruff check, ruff format --check, mypy), `test` (pytest with coverage floor 85%; baseline 93%), `hassfest` and `hacs` jobs.
- Code fixes required by the new checks: explicit `strict=False` on two `zip` calls, a `None` guard on the coordinator's update interval, and a typing ignore for the tracker's `_attr_device_info`. Whole repo reformatted by ruff.
- Behaviour unchanged; 58 tests pass.
- HACS validation ignores `brands`, `topics` and `description`: the repository has no description or topics (GitHub settings) and no `custom_components/tado_resume/brand/icon.png`. To re-enable: set the description and topics, add the icon, then remove the `ignore:` line in `tests.yml`.
