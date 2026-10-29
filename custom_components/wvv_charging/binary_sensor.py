"""Binary sensor platform for the WVV Charging integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import WvvChargingCoordinator
from .sensor import WvvStationEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up WVV Charging binary sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: WvvChargingCoordinator = data["coordinator"]
    station_ids: set[str] = data["station_ids"]
    station_names: dict[str, str] = data["station_names"]

    async_add_entities(
        WvvAnyFreeBinarySensor(coordinator, station_id, station_names.get(station_id, station_id))
        for station_id in station_ids
    )


class WvvAnyFreeBinarySensor(WvvStationEntity, BinarySensorEntity):
    """On when at least one charge point at the station is free."""

    _attr_translation_key = "any_free"
    _attr_icon = "mdi:ev-plug-type2"

    def __init__(self, coordinator: WvvChargingCoordinator, station_id: str, device_name: str) -> None:
        super().__init__(coordinator, station_id, device_name)
        self._attr_unique_id = f"{station_id}_any_free"

    @property
    def is_on(self) -> bool | None:
        station = self._station
        if station is None:
            return None
        return station.any_free

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        station = self._station
        if station is None:
            return None
        return self._location_attrs(station) or None
