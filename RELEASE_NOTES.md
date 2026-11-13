## 0.18.0

- New service `tado_resume.set_away_until`: sets every home to away now and returns it to automatic (geofencing) at the chosen date and time.
- The end time is stored, so it survives a Home Assistant restart. If the time passes while Home Assistant is stopped, presence returns to automatic at the next start. A failed return is retried every 5 minutes.
- Choosing a presence manually (the Presence select) cancels the timer.
