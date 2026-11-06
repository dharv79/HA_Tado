# Roadmap

Goal: extend the integration beyond resume schedule to cover what tado thermostats can do. Each phase is one or more PRs, ends with a release (see `../RELEASING.md`), and has its own file. Read only the phase being worked on.

| Phase | File | Features | Release |
|---|---|---|---|
| 0 | [phase-0-foundation.md](phase-0-foundation.md) | Coordinator, state API, capability detection | 0.2.0 |
| 1 | [phase-1-climate.md](phase-1-climate.md) | Climate entity, timed override, boost, off | 0.3.0 |
| 2 | [phase-2-sensors.md](phase-2-sensors.md) | Heating power, battery, connection, firmware, early start | 0.4.0 |
| 3 | [phase-3-presence-windows.md](phase-3-presence-windows.md) | Home/Away, device trackers, open window | 0.5.0 |
| 4 | [phase-4-home-actions.md](phase-4-home-actions.md) | Whole-home actions, weather | 0.6.0 |
| 5 | [phase-5-device-settings.md](phase-5-device-settings.md) | Offset, child lock, display | 0.7.0 |
| 6 | [phase-6-schedules.md](phase-6-schedules.md) | Schedule sensor, schedule editing | 0.8.0 |
| 7 | [phase-7-energy-boiler.md](phase-7-energy-boiler.md) | Boiler flow temperature, energy and run time | 0.9.0 |

Feature numbers (F1 to F20) refer to the agreed 20-feature list; each is assigned to exactly one phase.

## Invariants
- Domain `tado_resume` and existing entity unique IDs must not change.
- Every phase starts by verifying its endpoints against the real tado X (and classic where relevant) API; unverified endpoints are not shipped. Record findings in the phase file.
- Features unsupported on a given home generation are not created for it (detect via `generation`).
- Write requests send a JSON `Content-Type` (tado X rejects body-less writes without it).
- Refresh tokens rotate; any new API client must persist the new token through the existing callback.
- Each phase adds tests; all existing tests keep passing.
