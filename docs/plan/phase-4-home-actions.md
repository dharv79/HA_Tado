# Phase 4: Home-level actions and weather (0.6.0)

Features: F8 whole-home quick actions, F9 weather.

## Scope
- Services and buttons for boost all rooms, turn all off, resume all (resume all exists already).
- Weather sensors: outside temperature, conditions, solar intensity if provided.

## Discovery
Confirm tado X quick-action endpoints (`quickActions/*`) and the weather payload.

## Exit criteria
Each quick action verified on hardware; weather values update through the coordinator.

## Status (0.6.0)
Implemented from desk research; requests are NOT verified on hardware.
- tado X: `POST /homes/{id}/quickActions/boost` and `.../turnOffAll` (no body).
- Classic: turn off all = per-zone indefinite-style overlay with power OFF; boost unsupported (button not created).
- Surfaces: home buttons "Boost all rooms" (X only), "Turn off all rooms"; services `tado_resume.boost_all_rooms`, `tado_resume.turn_off_all_rooms` (alongside `resume_all_schedules`).
- Weather: `GET /api/v2/homes/{id}/weather` read through the coordinator; sensors outside temperature, solar intensity, weather state, created only for keys present.
- Unverified: the weather endpoint on tado X homes, the field names, and the quick-action paths.
