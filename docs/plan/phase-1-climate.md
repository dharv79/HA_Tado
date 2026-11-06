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

## Status (0.3.0)
Implemented: climate entity per room, `set_room_temperature` service (termination: next schedule block, duration, indefinite), off (frost protection), boost (tado X only, 25 °C for 30 minutes).

Discovery was desk-based, from the PyTado library source, not a real home:
- tado X: `POST /homes/{id}/rooms/{id}/manualControl` with `setting` (`power`, `isBoost`, `temperature.value`) and `termination` (`NEXT_TIME_BLOCK`, `TIMER` + `durationInSeconds`, `MANUAL`). Values are sent as strings, as PyTado does.
- Classic: `PUT /homes/{id}/zones/{id}/overlay` with `termination.typeSkillBasedApp` (`TADO_MODE`, `TIMER`, `MANUAL`).
- Boost has no classic equivalent; the preset is not offered there.

Open: confirm each call, the boost temperature and the off-state payload on real hardware.
