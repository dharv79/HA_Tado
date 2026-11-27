## 0.21.0

tado now limits API requests per account per day: 100 without a subscription, 20,000 with Auto-Assist or AI Assist. Running out stops all updates and blocks adding the integration until the quota refills.

- Polling is paced from tado's `ratelimit` header so the remaining requests last until the quota refills; 10 are kept back for your own actions.
- New diagnostic sensor: tado requests remaining (with the refill time when tado gives it).
- When the limit is reached, a repair says when the integration will try again, and setup or re-login says "daily request limit reached, try again after HH:MM" instead of "Unable to reach tado". Setup errors are now logged.
- Fewer requests per poll: device, weather and mobile-device data is reused for 15 minutes (refreshed straight after any change you make).
- The default polling interval is now 5 minutes (was 1 minute). A value you set in the options is kept.
