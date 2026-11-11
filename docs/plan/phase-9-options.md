# Phase 9: Options flow (0.11.0)

User-configurable behaviour.

## Scope
- Options flow: poll interval, boost temperature and duration, default override termination.
- Replace the constants `BOOST_TEMPERATURE`, `BOOST_SECONDS` and `BASE_INTERVAL` with options.

## Discovery
None beyond verifying tado X accepts non-default boost values.

## Exit criteria
Options change behaviour without a restart; defaults unchanged.
