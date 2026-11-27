# Phase 18: tado daily request quota (0.21.0)

Since 01/01/2026 tado limits API requests per account per day: 100 without a subscription, 20,000 with Auto-Assist or AI Assist ([tado support article 12165739](https://support.tado.com/en/articles/12165739-limitation-for-rest-api-usage)). The Home Assistant core docs give 12:00 CET as the reset time; tado's article does not state one.

## Scope
1. Read tado's `ratelimit` header (`"perday";r=<left>[;t=<seconds to refill>]`), expose requests left as a diagnostic sensor, and pace polling so the remaining quota (less a reserve of 10 for user actions) lasts until the refill.
2. A 429 waits for `t` (else `Retry-After`, else 1 hour), raises a `rate_limited` repair naming the retry time, and the config and reauth flows abort with `rate_limited` instead of `cannot_connect`. Setup errors are logged.
3. Fewer requests: devices, weather and mobile devices are reused for 15 minutes (cleared by any write); default poll interval 300 s.

## Outcome (27/11/2026)
Shipped in 0.21.0. Unverified against the live API: whether `hops.tado.com` and `my.tado.com` both send the `ratelimit` header on successful responses (pacing is skipped when absent); whether refused (429) requests and `login.tado.com` token refreshes count towards the quota; the reset time.
