# Phase 6: Schedules (0.8.0)

Features: F17 schedule viewer, F18 schedule editing.

## Scope
- Sensor per room: next scheduled change time and target temperature.
- Service to change time blocks. Highest risk: it modifies stored configuration.

## Discovery
Confirm tado X schedule read and write endpoints. If write support is absent or unsafe, ship F17 only and record F18 as blocked here.

## Exit criteria
Next-change sensor matches the tado app; any edit service validates input and was tested on a single room first.
