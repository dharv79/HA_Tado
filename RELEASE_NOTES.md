## 0.20.0

Corrects the 0.19.0 release. Tag 0.19.0 points to an older commit (quality tooling only) that lacks everything from 0.11.0 to 0.18.0, so HACS users on 0.19.0 lost those features, including rate-limit handling. Update to 0.20.0.

- Includes all changes from 0.11.0 to 0.18.0: options flow, adaptive polling and 429 back-off, device offset and child lock, override end time sensors, classic schedule and run-time sensors, dew point and mould risk, timed away.
- Three automation blueprints: window open turns a room off and resumes it on close; everyone away sets away mode; arrival sets presence to automatic and resumes all schedules. Import buttons are in the README.
