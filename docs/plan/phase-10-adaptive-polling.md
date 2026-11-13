# Phase 10: Adaptive polling and rate limits (0.12.0)

Fewer API calls.

## Scope
- Slow polling when the home is away or idle, fast after a write; honour `Retry-After`/429.
- Skip optional endpoints (weather, mobile devices) that returned errors until a longer back-off passes.

## Discovery
Observe tado rate-limit headers and responses on hardware.

## Exit criteria
Request count per hour measurably lower; no stale state after writes.

## Outcome (0.12.0)
- `TadoRateLimitError` raised on 429 with parsed `Retry-After`; the coordinator waits at least that long.
- Optional endpoints back off for 30 minutes after an error and serve the last good payload.
- Away polling interval is 3x the base interval; restored on the next non-away poll.
- Not verified on hardware: tado's real rate-limit headers and whether `Retry-After` is sent. Idle detection (beyond Away) was not implemented.
