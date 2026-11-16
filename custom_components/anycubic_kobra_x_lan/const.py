DOMAIN = "anycubic_kobra_x_lan"

CONF_HOST = "host"
CONF_PC_DEVICE_ID = "pc_device_id"
CONF_POLLING_INTERVAL = "polling_interval"

DEFAULT_NAME = "Anycubic Kobra X LAN"
DEFAULT_POLLING_INTERVAL = 30
MIN_POLLING_INTERVAL = 10
MAX_POLLING_INTERVAL = 3600

PLATFORMS = [
    "sensor",
    "binary_sensor",
    "button",
    "camera",
    "light",
    "number",
    "select",
    "switch",
    "event",
    "image",
]

# The printer serves its camera as HTTP-FLV on this port once it has been
# told to startCapture over MQTT.
CAMERA_STREAM_PORT = 18088
CAMERA_START_DEBOUNCE_SECONDS = 10
# How long an unconfirmed startCapture is trusted before it is sent again.
CAMERA_CONFIRM_SECONDS = 30
# Restart the stream after a reconnect if it was viewed this recently.
CAMERA_RESUME_WINDOW_SECONDS = 600

QUERY_TYPES = [
    "status",
    "info",
    "tempature",
    "fan",
    "light",
    "peripherie",
    "multiColorBox",
]

# Queried every poll but not waited for: printers that do not support them
# simply stay silent.
OPTIONAL_QUERY_TYPES = [
    "print",
    "axis",
]

# Lovelace card bundled with the integration and served by it.
FRONTEND_URL_BASE = "/anycubic_kobra_x_lan_frontend"
CARD_FILENAME = "kobra-x-printer-card.js"

# Reason codes the printer reports with a pause/stop (print report `code`).
# 10401/10601/11518 were seen on the wire; the rest are titles of Anycubic's
# Kobra error code wiki pages (wiki.anycubic.com/en/error-codes).
REASON_PAUSED_BY_USER = 10401
REASON_STOPPED_BY_USER = 10601
USER_REASON_CODES = frozenset({REASON_PAUSED_BY_USER, REASON_STOPPED_BY_USER})
REASON_TEXT = {
    REASON_PAUSED_BY_USER: "Paused by user",
    REASON_STOPPED_BY_USER: "Stopped by user",
    10105: "File download failed",
    10106: "Insufficient memory, task cancelled",
    10107: "Filament broken",
    10115: "The device cannot parse the file",
    10116: "Abnormal slice file",
    10118: "X-axis homing failed",
    10119: "Y-axis homing failed",
    10120: "Z-axis homing failed",
    10121: "Hotbed heating abnormal",
    10122: "Extruder heating abnormal",
    10123: "Hotbed NTC abnormal",
    10124: "Extruder NTC abnormal",
    10131: "Nozzle MCU abnormal",
    10402: "Filament broken, load new filament",
    11503: "Color engine connection problem",
    11504: "Unknown feed location",
    11509: "Color engine response timeout",
    11511: "Extrusion abnormal",
    11512: "Retraction abnormal",
    11518: "Filament is stuck",
    11519: "Filament tangle detected",
    11520: "Filament abnormal in the color unit",
    11521: "Color engine motor rotation abnormal",
    11801: "Spaghetti detected, print paused",
    11900: "Nozzle diameter does not match the model",
}

# Print event entity event types.
EVENT_STARTED = "started"
EVENT_PAUSED = "paused"
EVENT_RESUMED = "resumed"
EVENT_FINISHED = "finished"
EVENT_STOPPED = "stopped"
EVENT_FAILED = "failed"
EVENT_ERROR = "error"
PRINT_EVENT_TYPES = [
    EVENT_STARTED,
    EVENT_PAUSED,
    EVENT_RESUMED,
    EVENT_FINISHED,
    EVENT_STOPPED,
    EVENT_FAILED,
    EVENT_ERROR,
]
