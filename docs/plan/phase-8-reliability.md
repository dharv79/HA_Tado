# Phase 8: Reauth, repairs and API health (0.10.0)

Reauthentication flow and Repairs issues.

## Scope
- Reauth config-flow step reusing the device-code login, so an expired or revoked refresh token no longer requires removing the entry.
- Repair issue when the API has failed for a set period; diagnostic sensor for last successful update.

## Discovery
Confirm what tado returns for an expired refresh token (`invalid_grant`) and how rotation failures present.

## Exit criteria
Expired token triggers a reauth prompt; entry recovers without losing entities.

## Outcome (0.10.0)
- Token endpoint 400/401/403 raise `TadoAuthError` (including `invalid_grant`), which raises `ConfigEntryAuthFailed` in setup and the coordinator, starting the reauth flow. Not verified against a live expired token.
- `reauth_confirm` repeats the device login, checks the configured home is still visible to the account (`wrong_account` otherwise), updates the stored token and reloads, keeping entities.
- Repair issue `api_unreachable_<home>` after one hour of continuous non-auth failures; cleared on success or unload.
- Diagnostic sensor "Last successful update" on the home device; stays available while the API fails.
