## 0.15.0

- New per-room sensors for classic (pre-tado X) systems: next schedule change (timestamp, with the new power state as an attribute) and next scheduled temperature.
- The active timetable is read once an hour, so the extra requests are negligible.
- tado X and schedule editing are not included: no schedule endpoint for tado X could be confirmed.
- Endpoints and block fields follow tado's classic API and have not yet been confirmed against hardware.
