# Phase 12: Computed comfort sensors (0.17.0)

Dew point and mould risk.

## Scope
- Dew point and mould-risk level computed from room temperature and humidity; no new endpoints.

## Discovery
None (derived data).

## Exit criteria
Values match a reference dew-point formula in tests.

## Outcome (0.17.0)
- Added per-room `dew_point` (°C) and `mould_risk` (enum low/medium/high) sensors, created only where a room reports both temperature and humidity. No new endpoints.
- Dew point uses the Magnus formula (a=17.62, b=243.12); tests check against reference values. Invalid input (humidity outside 0–100, missing values) gives unknown.
- Mould risk: high at RH ≥ 70 % or air/dew-point margin < 3 K; medium at RH ≥ 60 % or margin < 5 K; otherwise low. Thresholds are heuristic, not a standard; adjust if the user prefers different limits.
- Handles tado X (`value`) and classic (`celsius`) temperature shapes.
