"""Constants for the WVV Charging integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "wvv_charging"

API_URL: Final = "https://map.smartandpublic.eu/api/charging"
EXPECTED_OPERATOR_NAME: Final = "WVV"

REQUEST_TIMEOUT: Final = 15  # seconds

CONF_MODE: Final = "mode"
CONF_STATION_IDS: Final = "station_ids"
CONF_RADIUS_KM: Final = "radius_km"
CONF_UPDATE_INTERVAL: Final = "update_interval"

MODE_FAVORITES: Final = "favorites"
MODE_RADIUS: Final = "radius"

DEFAULT_UPDATE_INTERVAL: Final = 5  # minutes
MIN_UPDATE_INTERVAL: Final = 1  # minutes
DEFAULT_RADIUS_KM: Final = 2.0

DEFAULT_SCAN_INTERVAL = timedelta(minutes=DEFAULT_UPDATE_INTERVAL)

# Connector (circuit) statuses reported by the smartandpublic API.
STATUS_AVAILABLE: Final = "OCPP_AVAILABLE"
STATUS_UNAVAILABLE: Final = "OCPP_UNAVAILABLE"
STATUS_CHARGING: Final = "OCPP16_CHARGING"
STATUS_SUSPENDED_EV: Final = "OCPP16_SUSPENDEDEV"
STATUS_PREPARING: Final = "OCPP16_PREPARING"
STATUS_FINISHING: Final = "OCPP16_FINISHING"
STATUS_IDLE: Final = "IDLE"

OCCUPIED_CONNECTOR_STATUSES: Final = {
    STATUS_CHARGING,
    STATUS_SUSPENDED_EV,
    STATUS_PREPARING,
    STATUS_FINISHING,
}

# Station-level status exposed by the integration's "status" sensor.
STATION_STATUS_AVAILABLE: Final = "available"
STATION_STATUS_OCCUPIED: Final = "occupied"
STATION_STATUS_OUT_OF_ORDER: Final = "out_of_order"
STATION_STATUS_UNKNOWN: Final = "unknown"

STATION_STATUS_OPTIONS: Final = [
    STATION_STATUS_AVAILABLE,
    STATION_STATUS_OCCUPIED,
    STATION_STATUS_OUT_OF_ORDER,
    STATION_STATUS_UNKNOWN,
]

ATTR_ADDRESS: Final = "address"
ATTR_MAX_POWER_KW: Final = "max_power_kw"
ATTR_PLUG_TYPES: Final = "plug_types"
ATTR_CONNECTORS: Final = "connectors"
ATTR_TOTAL_POINTS: Final = "total_points"
ATTR_FREE_OF_TOTAL: Final = "free_of_total"
ATTR_ACCESSIBILITY: Final = "accessibility"
ATTR_TWENTYFOURSEVEN: Final = "twentyfourseven"
ATTR_PRICE_INFO_URL: Final = "price_info_url"

PRICE_INFO_URL: Final = "https://www.wvv.de/elektromobilitaet/ladepreis/"

MANUFACTURER: Final = "WVV Energie"
