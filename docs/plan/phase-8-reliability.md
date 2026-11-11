# Phase 8: Reauth, repairs and API health (0.10.0)

Reauthentication flow and Repairs issues.

## Scope
- Reauth config-flow step reusing the device-code login, so an expired or revoked refresh token no longer requires removing the entry.
- Repair issue when the API has failed for a set period; diagnostic sensor for last successful update.

## Discovery
Confirm what tado returns for an expired refresh token (`invalid_grant`) and how rotation failures present.

## Exit criteria
Expired token triggers a reauth prompt; entry recovers without losing entities.
