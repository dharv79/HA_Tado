## 0.16.0

- New sensor **Heating run time today** for tado classic homes: seconds of heating so far today (shown in hours), with a per-zone breakdown in the `zones` attribute. Read every 15 minutes; created only when tado returns the data.
- Not included: the boiler maximum flow temperature number and the energy-savings sensors. No public, verified endpoint exists for tado X, and the classic write is an installer-app endpoint, so no boiler writes are offered.
- The run-time endpoint comes from a third-party client and is unverified against a live account.
