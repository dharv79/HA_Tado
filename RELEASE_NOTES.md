## 0.13.0

Device settings.

- New temperature offset control (number, configuration category) for each tado X device that reports an offset.
- New child lock switch (configuration category) for each device that reports a child lock, on tado X and classic.
- Entities are only created where tado reports the value; devices without it get nothing.
- Display and LED controls are not included: no write endpoint has been identified.
