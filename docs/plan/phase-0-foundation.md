# Phase 0: Foundation (0.2.0)

Enables every later phase. No new user-facing entities.

## Scope
- `DataUpdateCoordinator` polling home state (rooms, devices, presence, weather) with a sensible interval and back-off on errors.
- API layer: read methods for tado X (`hops.tado.com`) and classic, behind one interface selected by `generation`.
- Capability map per home and room (what can be read or written), used by later phases to create only supported entities.
- Diagnostics support with credentials and tokens redacted.

## Discovery (do first)
Probe real responses for: rooms and state, devices, mobile devices, weather, home state. Save redacted example payloads under `tests/fixtures/`.

## Exit criteria
Coordinator populates from fixtures in tests; existing button and services use it without behaviour change; diagnostics output contains no secrets.
