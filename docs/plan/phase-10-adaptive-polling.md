# Phase 10: Adaptive polling and rate limits (0.12.0)

Fewer API calls.

## Scope
- Slow polling when the home is away or idle, fast after a write; honour `Retry-After`/429.
- Skip optional endpoints (weather, mobile devices) that returned errors until a longer back-off passes.

## Discovery
Observe tado rate-limit headers and responses on hardware.

## Exit criteria
Request count per hour measurably lower; no stale state after writes.
