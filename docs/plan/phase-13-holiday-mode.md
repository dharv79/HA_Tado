# Phase 13: Holiday and away-until (0.15.0)

Timed away.

## Scope
- Service `set_away_until` (datetime) that sets away presence and returns to automatic at the end, surviving restarts.
- Optionally a minimum-temperature setting while away.

## Discovery
Check whether tado X supports a native holiday/away timer; otherwise schedule inside HA.

## Exit criteria
Away is cleared at the chosen time, including after a Home Assistant restart.
