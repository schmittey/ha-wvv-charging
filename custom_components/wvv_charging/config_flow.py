"""Config flow for the WVV Charging integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import Station, WvvChargingApiClient, WvvChargingApiError
from .const import (
    CONF_MODE,
    CONF_RADIUS_KM,
    CONF_STATION_IDS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_RADIUS_KM,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MIN_UPDATE_INTERVAL,
    MODE_FAVORITES,
    MODE_RADIUS,
)

_LOGGER = logging.getLogger(__name__)


async def _async_fetch_stations(hass: Any) -> list[Station]:
    client = WvvChargingApiClient(async_get_clientsession(hass))
    return await client.async_get_stations()


def _station_options(stations: list[Station]) -> list[selector.SelectOptionDict]:
    ordered = sorted(stations, key=lambda s: (s.city or "", s.street or "", s.name))
    labels: list[selector.SelectOptionDict] = []
    for station in ordered:
        label = station.address or station.name
        description = (station.description or "").strip().rstrip(".")
        if description and len(description) <= 40:
            label = f"{label} ({description})"
        labels.append(selector.SelectOptionDict(value=station.station_id, label=label))
    return labels


def _common_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_MODE, default=defaults.get(CONF_MODE, MODE_FAVORITES)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[MODE_FAVORITES, MODE_RADIUS],
                    translation_key=CONF_MODE,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=defaults.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_UPDATE_INTERVAL,
                    max=1440,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            ),
        }
    )


class WvvChargingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._stations: list[Station] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            try:
                self._stations = await _async_fetch_stations(self.hass)
            except WvvChargingApiError:
                errors["base"] = "cannot_connect"
            else:
                if user_input[CONF_MODE] == MODE_FAVORITES:
                    return await self.async_step_favorites()
                return await self.async_step_radius()

        return self.async_show_form(
            step_id="user",
            data_schema=_common_schema(self._data),
            errors=errors,
        )

    async def async_step_favorites(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_STATION_IDS):
                errors["base"] = "no_stations_selected"
            else:
                self._data.update(user_input)
                return self.async_create_entry(title="WVV Ladestationen", data=self._data)

        return self.async_show_form(
            step_id="favorites",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_IDS): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=_station_options(self._stations),
                            multiple=True,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_radius(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="WVV Ladestationen", data=self._data)

        return self.async_show_form(
            step_id="radius",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RADIUS_KM, default=DEFAULT_RADIUS_KM): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.1,
                            max=100,
                            step=0.1,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="km",
                        )
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return WvvChargingOptionsFlow(config_entry)


class WvvChargingOptionsFlow(OptionsFlow):
    """Allow changing station selection / radius / update interval after setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        self._data: dict[str, Any] = dict(config_entry.data)
        self._stations: list[Station] = []

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            try:
                self._stations = await _async_fetch_stations(self.hass)
            except WvvChargingApiError:
                errors["base"] = "cannot_connect"
            else:
                if user_input[CONF_MODE] == MODE_FAVORITES:
                    return await self.async_step_favorites()
                return await self.async_step_radius()

        return self.async_show_form(
            step_id="init",
            data_schema=_common_schema(self._data),
            errors=errors,
        )

    async def async_step_favorites(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_STATION_IDS):
                errors["base"] = "no_stations_selected"
            else:
                self._data.update(user_input)
                self.hass.config_entries.async_update_entry(self._config_entry, data=self._data)
                return self.async_create_entry(title="", data={})

        current = self._data.get(CONF_STATION_IDS, [])
        return self.async_show_form(
            step_id="favorites",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_IDS, default=current): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=_station_options(self._stations),
                            multiple=True,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_radius(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            self.hass.config_entries.async_update_entry(self._config_entry, data=self._data)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="radius",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_RADIUS_KM, default=self._data.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM)
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.1,
                            max=100,
                            step=0.1,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="km",
                        )
                    ),
                }
            ),
        )
