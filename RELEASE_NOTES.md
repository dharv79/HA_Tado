## 0.12.0

Fewer API calls.

- Polling slows to three times the configured interval while the home is set to Away.
- A 429 response is honoured: polling waits for `Retry-After` (capped at one hour) before the next request.
- Optional endpoints (weather, mobile devices, device list, home state) that fail are left alone for 30 minutes; the last good data is kept meanwhile.
- Writes still trigger an immediate refresh, so state stays current after a change.
