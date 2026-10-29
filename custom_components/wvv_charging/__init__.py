"""The WVV Charging integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import Station
from .const import (
    CONF_MODE,
    CONF_RADIUS_KM,
    CONF_STATION_IDS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MODE_FAVORITES,
)
from .coordinator import WvvChargingCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


def _select_station_ids(hass: HomeAssistant, entry: ConfigEntry, stations: dict[str, Station]) -> set[str]:
    """Resolve the set of station ids this config entry should expose."""
    if entry.data.get(CONF_MODE) == MODE_FAVORITES:
        return set(entry.data.get(CONF_STATION_IDS, []))

    radius_km = entry.data.get(CONF_RADIUS_KM)
    home_lat = hass.config.latitude
    home_lon = hass.config.longitude
    if radius_km is None or home_lat is None or home_lon is None:
        return set()

    return {
        station_id
        for station_id, station in stations.items()
        if (distance := station.distance_km(home_lat, home_lon)) is not None and distance <= radius_km
    }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the WVV Charging config entry."""
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    coordinator = WvvChargingCoordinator(hass, entry, update_interval)

    await coordinator.async_config_entry_first_refresh()

    if coordinator.data is None:
        raise ConfigEntryNotReady("No data received from the WVV charging API yet")

    station_ids = _select_station_ids(hass, entry, coordinator.data)
    if not station_ids:
        _LOGGER.warning(
            "No WVV charging stations matched this entry's configuration "
            "(check your favourite stations or radius setting)"
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "station_ids": station_ids,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a WVV Charging config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
