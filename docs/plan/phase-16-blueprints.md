# Phase 16: Automation blueprints (0.20.0)

Ready-made automations.

## Scope
- Blueprints: window open → heating off, everyone away → away mode, arrival → resume schedule.
- Documented in the README with import buttons.

## Discovery
None; built on existing entities.

## Exit criteria
Blueprints import and run against the test fixtures.

## Outcome (13/11/2026)
Shipped in 0.20.0 (the 0.19.0 release attempt failed because tag 0.19.0 already held Phase 17): three blueprints in `blueprints/automation/tado_resume/`, README import buttons, and `tests/test_blueprints.py` (schema validation plus a run of each against mocked services). No new endpoints.
