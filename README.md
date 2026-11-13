# Home Assistant for Tado Thermostat

A Home Assistant custom integration that resumes the tado° smart schedule, as the tado app does. Supports tado X (Bridge X) and classic (v2) homes.

## Features

- A **Resume schedule** button per room, plus a whole-home button.
- `tado_resume.resume_schedule`: press selected room buttons from automations.
- `tado_resume.resume_all_schedules`: resume every room in every configured home.

## Blueprints

| Blueprint | Behaviour | Import |
|---|---|---|
| Window open, heating off | Turns a room off when its window is open for a set time; resumes the schedule when closed. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fdharv79%2FHA_Tado%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Ftado_resume%2Fwindow_open_heating_off.yaml) |
| Everyone away, away mode | Sets the home to away once all selected people are away for a set time. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fdharv79%2FHA_Tado%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Ftado_resume%2Feveryone_away.yaml) |
| Arrival, resume schedule | On arrival, sets presence to automatic and resumes every room's schedule. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fdharv79%2FHA_Tado%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Ftado_resume%2Farrival_resume_schedule.yaml) |

## Installation

1. In HACS, add this repository as a custom repository (type: Integration) and install it.
2. Restart Home Assistant.
3. Add the **Home Assistant for Tado Thermostat** integration. Open the displayed tado URL, approve access, then select Submit.

The integration keeps its own login, independent of the core tado integration.

## Development

```
pip install -r requirements_test.txt
pytest
```

The tado X endpoints used (`resumeSchedule`, `quickActions/resumeSchedule`) are undocumented; verify against a real Bridge X.
