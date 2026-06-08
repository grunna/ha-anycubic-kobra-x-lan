DOMAIN = "anycubic_kobra_x_lan"

CONF_HOST = "host"
CONF_PC_DEVICE_ID = "pc_device_id"
CONF_POLLING_INTERVAL = "polling_interval"

DEFAULT_NAME = "Anycubic Kobra X LAN"
DEFAULT_POLLING_INTERVAL = 30
MIN_POLLING_INTERVAL = 10
MAX_POLLING_INTERVAL = 3600

PLATFORMS = ["sensor", "binary_sensor", "camera", "button", "light", "switch", "number"]

QUERY_TYPES = [
    "status",
    "info",
    "tempature",
    "fan",
    "light",
    "peripherie",
    "multiColorBox",
]
