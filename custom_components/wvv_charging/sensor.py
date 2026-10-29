"""Sensor platform for the WVV Charging integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Station
from .const import (
    ATTR_ACCESSIBILITY,
    ATTR_ADDRESS,
    ATTR_CONNECTORS,
    ATTR_FREE_OF_TOTAL,
    ATTR_MAX_POWER_KW,
    ATTR_PLUG_TYPES,
    ATTR_PRICE_INFO_URL,
    ATTR_TOTAL_POINTS,
    ATTR_TWENTYFOURSEVEN,
    DOMAIN,
    MANUFACTURER,
    PRICE_INFO_URL,
    STATION_STATUS_OPTIONS,
)
from .coordinator import WvvChargingCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up WVV Charging sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: WvvChargingCoordinator = data["coordinator"]
    station_ids: set[str] = data["station_ids"]

    entities: list[SensorEntity] = []
    for station_id in station_ids:
        entities.append(WvvFreePointsSensor(coordinator, station_id))
        entities.append(WvvStatusSensor(coordinator, station_id))
        entities.append(WvvDistanceSensor(coordinator, station_id, hass))

    async_add_entities(entities)


class WvvStationEntity(CoordinatorEntity[WvvChargingCoordinator]):
    """Common base for all entities tied to a single WVV station."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WvvChargingCoordinator, station_id: str) -> None:
        super().__init__(coordinator)
        self._station_id = station_id

    @property
    def _station(self) -> Station | None:
        return self.coordinator.data.get(self._station_id) if self.coordinator.data else None

    @property
    def available(self) -> bool:
        return super().available and self._station is not None

    @property
    def device_info(self) -> DeviceInfo:
        station = self._station
        name = station.name if station else self._station_id
        model = ", ".join(station.plug_types) if station and station.plug_types else None
        return DeviceInfo(
            identifiers={(DOMAIN, self._station_id)},
            name=name,
            manufacturer=MANUFACTURER,
            model=model,
            configuration_url="https://www.wvv.de/elektromobilitaet/laden-in-wuerzburg/",
        )

    def _location_attrs(self, station: Station) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if station.latitude is not None and station.longitude is not None:
            attrs["latitude"] = station.latitude
            attrs["longitude"] = station.longitude
        return attrs


class WvvFreePointsSensor(WvvStationEntity, SensorEntity):
    """Number of currently free charge points at a station."""

    _attr_translation_key = "free_points"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "points"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator: WvvChargingCoordinator, station_id: str) -> None:
        super().__init__(coordinator, station_id)
        self._attr_unique_id = f"{station_id}_free_points"

    @property
    def native_value(self) -> int | None:
        station = self._station
        return station.free_points if station else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        station = self._station
        if station is None:
            return None

        attrs: dict[str, Any] = {
            ATTR_ADDRESS: station.address,
            ATTR_MAX_POWER_KW: station.max_power_kw,
            ATTR_PLUG_TYPES: station.plug_types,
            ATTR_TOTAL_POINTS: station.total_points,
            ATTR_FREE_OF_TOTAL: station.free_of_total,
            ATTR_ACCESSIBILITY: station.accessibility,
            ATTR_TWENTYFOURSEVEN: station.twentyfourseven,
            ATTR_PRICE_INFO_URL: PRICE_INFO_URL,
            ATTR_CONNECTORS: [
                {
                    "id": c.connector_id,
                    "plug": c.plug,
                    "power_type": c.power_type,
                    "max_power_kw": c.max_electric_power_w / 1000 if c.max_electric_power_w else None,
                    "status": c.status,
                    "free": c.is_free,
                }
                for c in station.connectors
            ],
        }
        attrs.update(self._location_attrs(station))
        return attrs


class WvvStatusSensor(WvvStationEntity, SensorEntity):
    """Overall status of a station: available / occupied / out_of_order / unknown."""

    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATION_STATUS_OPTIONS
    _attr_icon = "mdi:flash"

    def __init__(self, coordinator: WvvChargingCoordinator, station_id: str) -> None:
        super().__init__(coordinator, station_id)
        self._attr_unique_id = f"{station_id}_status"

    @property
    def native_value(self) -> str | None:
        station = self._station
        return station.status if station else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        station = self._station
        if station is None:
            return None
        return self._location_attrs(station) or None


class WvvDistanceSensor(WvvStationEntity, SensorEntity):
    """Distance from the Home Assistant home zone to this station."""

    _attr_translation_key = "distance"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:map-marker-distance"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: WvvChargingCoordinator, station_id: str, hass: HomeAssistant) -> None:
        super().__init__(coordinator, station_id)
        self._attr_unique_id = f"{station_id}_distance"
        self._hass = hass

    @property
    def native_value(self) -> float | None:
        station = self._station
        home_lat = self._hass.config.latitude
        home_lon = self._hass.config.longitude
        if station is None or home_lat is None or home_lon is None:
            return None
        distance = station.distance_km(home_lat, home_lon)
        return round(distance, 2) if distance is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        station = self._station
        if station is None:
            return None
        return self._location_attrs(station) or None
