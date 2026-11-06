# Phase 4: Home-level actions and weather (0.6.0)

Features: F8 whole-home quick actions, F9 weather.

## Scope
- Services and buttons for boost all rooms, turn all off, resume all (resume all exists already).
- Weather sensors: outside temperature, conditions, solar intensity if provided.

## Discovery
Confirm tado X quick-action endpoints (`quickActions/*`) and the weather payload.

## Exit criteria
Each quick action verified on hardware; weather values update through the coordinator.
