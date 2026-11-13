# Phase 13: Holiday and away-until (0.18.0)

Timed away.

## Scope
- Service `set_away_until` (datetime) that sets away presence and returns to automatic at the end, surviving restarts.
- Optionally a minimum-temperature setting while away.

## Discovery
Check whether tado X supports a native holiday/away timer; otherwise schedule inside HA.

## Exit criteria
Away is cleared at the chosen time, including after a Home Assistant restart.

## Outcome (0.18.0)
- No native timed-away endpoint is known for tado X or classic (presence is only HOME/AWAY/auto, plus the classic `presenceLock`), so the timer runs inside Home Assistant (`away.py`).
- `set_away_until` sets presence to away through the existing presence call, stores the end time with `helpers.storage.Store` (one file per config entry) and schedules a UTC point-in-time callback that sets presence to auto.
- On setup the stored time is restored: future → rescheduled; elapsed → presence set to auto immediately. A failed return retries after 5 minutes. Selecting a presence manually cancels the timer.
- Rejected: past end times (service validation error).
- Not done: the optional minimum temperature while away. The away-temperature endpoints are unverified and need a tado app traffic capture.
- Phases 14–16 version labels are stale; the next release must be 0.19.0 or later.
