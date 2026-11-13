"""Constants for Home Assistant for Tado Thermostat."""

DOMAIN = "tado_resume"

CONF_HOME_ID = "home_id"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_GENERATION = "generation"

# Options (defaults match the behaviour before options existed)
CONF_POLL_INTERVAL = "poll_interval"
CONF_BOOST_TEMPERATURE = "boost_temperature"
CONF_BOOST_MINUTES = "boost_minutes"
CONF_DEFAULT_TERMINATION = "default_termination"
DEFAULT_POLL_INTERVAL = 60  # seconds
DEFAULT_BOOST_TEMPERATURE = 25.0
DEFAULT_BOOST_MINUTES = 30
DEFAULT_TERMINATION = "next_schedule_block"

SERVICE_RESUME_SCHEDULE = "resume_schedule"
SERVICE_RESUME_ALL = "resume_all_schedules"

SERVICE_SET_ROOM_TEMPERATURE = "set_room_temperature"
SERVICE_BOOST_ALL = "boost_all_rooms"
SERVICE_TURN_OFF_ALL = "turn_off_all_rooms"
SERVICE_SET_AWAY_UNTIL = "set_away_until"
