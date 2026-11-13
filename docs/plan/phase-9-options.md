# Phase 9: Options flow (0.11.0)

User-configurable behaviour.

## Scope
- Options flow: poll interval, boost temperature and duration, default override termination.
- Replace the constants `BOOST_TEMPERATURE`, `BOOST_SECONDS` and `BASE_INTERVAL` with options.

## Discovery
None beyond verifying tado X accepts non-default boost values.

## Exit criteria
Options change behaviour without a restart; defaults unchanged.

## Outcome (0.11.0)
- Options flow (`TadoResumeOptionsFlow`): update interval (30–3600 s, default 60), boost temperature (5–25 °C, default 25), boost duration (5–720 min, default 30), default override end (`next_schedule_block` or `indefinite`).
- `BOOST_TEMPERATURE`, `BOOST_SECONDS` and `BASE_INTERVAL` removed; defaults live in `const.py`. `async_boost_room` takes temperature and seconds (defaults unchanged).
- Options apply to the climate Boost preset, `set_temperature` and heat mode. The whole-home boost uses tado's own quick action and ignores them.
- Saving options reloads the entry (no restart). Failure backoff doubles from the configured interval, capped at 15 min or the interval if larger.
- Not verified on hardware: that tado X accepts non-default boost temperatures and durations (unit-tested request body only).
