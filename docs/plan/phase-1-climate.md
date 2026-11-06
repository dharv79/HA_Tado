# Phase 1: Climate control (0.3.0)

Features: F1 climate entity per room, F2 timed manual override, F3 boost, F4 heating off / frost protection.

## Scope
- `climate` platform: current temperature, humidity, target temperature, HVAC action (heating/idle/off), preset modes (schedule, boost).
- Manual set with termination options: until next schedule block, duration, indefinite. Expose as a service and via the entity.
- Boost and off per room. Resume schedule remains available via the existing button.

## Discovery
Confirm tado X endpoints and payloads for manual control, termination types, boost and off; confirm classic zone overlay equivalents.

## Exit criteria
Set, boost, off and resume work on real hardware; unit tests cover each termination type and error path.
