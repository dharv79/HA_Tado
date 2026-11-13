# Phase 7: Energy and boiler (0.9.0)

Features: F19 boiler max flow temperature, F20 energy and run time.

## Scope
- `number` entity for max flow temperature where the Bridge X exposes it. Validate bounds; wrong values can affect the boiler.
- Daily heating run-time and energy-savings sensors suitable for the Energy dashboard.

## Discovery
Confirm availability of both on tado X; they may require a subscription or be absent. Omit entities when unavailable.

## Exit criteria
Values verified against the tado app; boiler writes are bounded and documented in the README.

## Outcome (0.16.0)
Shipped: classic-only `Heating run time today` sensor (home device).
- Endpoint: `GET https://minder.tado.com/v1/homes/{id}/runningTimes?from=YYYY-MM-DD` (from a third-party Go client; unverified live). Response `{"runningTimes": [{runningTimeInSeconds, startTime, endTime, zones: [{id, runningTimeInSeconds}]}]}`. Cached 15 minutes; auth and rate-limit errors propagate; other failures keep the last value; sensor omitted when absent. Device class duration, `total_increasing`, seconds, suggested unit hours.
- F19 boiler max flow: not built. Only known endpoint is classic `PUT /homeByBridge/{bridge}/boilerMaxOutputTemperature` (installer app, bridge ID plus authKey, not public); nothing known for tado X / Bridge X. Needs a traffic capture and bounds from the tado app.
- F20 energy savings (`energy-bob.tado.com`) and tado X run time: not built; shapes unverified, tado X endpoint unknown.
- Unverified: run-time endpoint on live data, subscription gating, home-timezone date boundary (server date used).
