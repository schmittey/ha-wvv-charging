"""DataUpdateCoordinator for the WVV Charging integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Station, WvvChargingApiClient, WvvChargingApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class WvvChargingCoordinator(DataUpdateCoordinator[dict[str, Station]]):
    """Fetches all WVV stations in a single shared request."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        update_interval_minutes: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self._client = WvvChargingApiClient(async_get_clientsession(hass))

    async def _async_update_data(self) -> dict[str, Station]:
        try:
            stations = await self._client.async_get_stations()
        except WvvChargingApiError as err:
            raise UpdateFailed(str(err)) from err

        return {station.station_id: station for station in stations}
