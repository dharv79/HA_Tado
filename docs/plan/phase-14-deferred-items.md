# Phase 14: Early start and update-available (not scheduled)

Deferred Phase 2 items.

## Scope
- Early-start switch (where the room reports it) and an update-available indicator per device from firmware data.

## Discovery
Confirm the early-start read/write fields and a firmware-update flag.

## Exit criteria
Entities exist only where the payload supports them.

## Outcome (13/11/2026)
Discovery only; no code shipped and no release.

- Early start: PyTado 1.0.3 has no early-start read or write. The classic path `zones/{id}/earlyStart` with `{"enabled": bool}` is recalled but unverified. Nothing is known for tado X.
- Update-available: no field is known in either payload. Only `firmwareVersion` / `currentFwVersion` are read (already exposed as the firmware sensor).
- Per the exit criteria, no entities were added.
- To unblock: capture tado app traffic for both features, record the endpoints and fields here, then implement.
