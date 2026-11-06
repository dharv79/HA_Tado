# Tado Resume Schedule

A Home Assistant custom integration that resumes the tado° smart schedule, as the tado app does. Supports tado X (Bridge X) and classic (v2) homes.

## Features

- A **Resume schedule** button per room, plus a whole-home button.
- `tado_resume.resume_schedule`: press selected room buttons from automations.
- `tado_resume.resume_all_schedules`: resume every room in every configured home.

## Installation

1. In HACS, add this repository as a custom repository (type: Integration) and install it.
2. Restart Home Assistant.
3. Add the **Tado Resume Schedule** integration. Open the displayed tado URL, approve access, then select Submit.

The integration keeps its own login, independent of the core tado integration.

## Development

```
pip install -r requirements_test.txt
pytest
```

The tado X endpoints used (`resumeSchedule`, `quickActions/resumeSchedule`) are undocumented; verify against a real Bridge X.
