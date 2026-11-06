# Phase 7: Energy and boiler (0.9.0)

Features: F19 boiler max flow temperature, F20 energy and run time.

## Scope
- `number` entity for max flow temperature where the Bridge X exposes it. Validate bounds; wrong values can affect the boiler.
- Daily heating run-time and energy-savings sensors suitable for the Energy dashboard.

## Discovery
Confirm availability of both on tado X; they may require a subscription or be absent. Omit entities when unavailable.

## Exit criteria
Values verified against the tado app; boiler writes are bounded and documented in the README.
