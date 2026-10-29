"""API client and response parsing for the WVV charging map.

The public WVV charging map at
https://www.wvv.de/elektromobilitaet/laden-in-wuerzburg/ embeds a third
party widget (https://map.smartandpublic.eu/map) which in turn pulls its
data from a plain, unauthenticated JSON endpoint:

    GET https://map.smartandpublic.eu/api/charging

That endpoint returns every station operated by WVV in and around
Würzburg, including live per-connector status. This module fetches that
endpoint and turns it into typed, HA-friendly station objects.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from math import asin, cos, radians, sin, sqrt
from typing import Any

import aiohttp

from .const import (
    API_URL,
    OCCUPIED_CONNECTOR_STATUSES,
    REQUEST_TIMEOUT,
    STATION_STATUS_AVAILABLE,
    STATION_STATUS_OCCUPIED,
    STATION_STATUS_OUT_OF_ORDER,
    STATION_STATUS_UNKNOWN,
    STATUS_UNAVAILABLE,
)

_LOGGER = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0


class WvvChargingApiError(Exception):
    """Raised when the WVV charging API cannot be reached or parsed."""


@dataclass(slots=True)
class Connector:
    """A single charge point (circuit) at a station."""

    connector_id: str
    plug: str | None
    power_type: str | None
    max_electric_power_w: int | None
    status: str | None
    is_charging: bool
    is_ready: bool
    evse_id: str | None

    @property
    def is_occupied(self) -> bool:
        return self.status in OCCUPIED_CONNECTOR_STATUSES

    @property
    def is_unavailable(self) -> bool:
        return self.status == STATUS_UNAVAILABLE

    @property
    def is_free(self) -> bool:
        return not self.is_occupied and not self.is_unavailable


@dataclass(slots=True)
class Station:
    """A single charging station (one or more connectors) operated by WVV."""

    station_id: str
    name: str
    description: str | None
    street: str | None
    zip_code: str | None
    city: str | None
    latitude: float | None
    longitude: float | None
    accessibility: str | None
    twentyfourseven: bool | None
    published: bool
    connectors: list[Connector] = field(default_factory=list)

    @property
    def address(self) -> str:
        parts = [p for p in (self.street, f"{self.zip_code} {self.city}".strip()) if p]
        return ", ".join(parts)

    @property
    def display_name(self) -> str:
        """A human-findable name built from the address, e.g. "Rüdigerstr. 3".

        The API's own "name" field is almost always the generic
        "WVV Energie E-Ladestation" for every station, so it's useless for
        telling stations apart. The street is what people actually look
        for when they want a specific charger.
        """
        return self.street or self.city or self.name

    @property
    def total_points(self) -> int:
        return len(self.connectors)

    @property
    def free_points(self) -> int:
        return sum(1 for c in self.connectors if c.is_free)

    @property
    def free_of_total(self) -> str:
        return f"{self.free_points}/{self.total_points}"

    @property
    def plug_types(self) -> list[str]:
        seen: list[str] = []
        for c in self.connectors:
            if c.plug and c.plug not in seen:
                seen.append(c.plug)
        return seen

    @property
    def max_power_kw(self) -> float | None:
        powers = [c.max_electric_power_w for c in self.connectors if c.max_electric_power_w]
        if not powers:
            return None
        return max(powers) / 1000

    @property
    def status(self) -> str:
        if not self.connectors:
            return STATION_STATUS_UNKNOWN
        if self.free_points > 0:
            return STATION_STATUS_AVAILABLE
        if all(c.is_unavailable for c in self.connectors):
            return STATION_STATUS_OUT_OF_ORDER
        if any(c.is_occupied for c in self.connectors):
            return STATION_STATUS_OCCUPIED
        return STATION_STATUS_UNKNOWN

    @property
    def any_free(self) -> bool:
        return self.free_points > 0

    def distance_km(self, lat: float, lon: float) -> float | None:
        if self.latitude is None or self.longitude is None:
            return None
        return _haversine_km(lat, lon, self.latitude, self.longitude)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_r, lon1_r, lat2_r, lon2_r = map(radians, (lat1, lon1, lat2, lon2))
    d_lat = lat2_r - lat1_r
    d_lon = lon2_r - lon1_r
    a = sin(d_lat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def _station_id_for(place: dict[str, Any], index: int) -> str:
    """Build a stable unique id for a station.

    The API has no explicit per-station id, but every connector's evseId
    (e.g. "DE*BDO*E594244984*1") shares a common prefix per station
    ("DE*BDO*E594244984"). That prefix is unique and stable across
    refreshes, so it's used as the station id. A handful of stations
    (depots, test entries) have no evseId at all; for those we fall back
    to a coordinate-based id, and finally to the list index as a last
    resort so a station is never dropped.
    """
    circuits = place.get("circuits") or []
    prefixes = {
        "*".join(str(c["evseId"]).split("*")[:-1])
        for c in circuits
        if c.get("evseId")
    }
    if len(prefixes) == 1:
        return next(iter(prefixes))

    lat = place.get("lat")
    lon = place.get("lon")
    if lat is not None and lon is not None:
        return f"geo:{lat}:{lon}"

    return f"index:{index}"


def _parse_connector(raw: dict[str, Any]) -> Connector:
    return Connector(
        connector_id=str(raw.get("_id")),
        plug=raw.get("plug"),
        power_type=raw.get("power_type"),
        max_electric_power_w=raw.get("max_electric_power"),
        status=raw.get("status"),
        is_charging=bool(raw.get("isCharging")),
        is_ready=bool(raw.get("isReady")),
        evse_id=raw.get("evseId"),
    )


def _parse_station(raw: dict[str, Any], index: int) -> Station:
    address = raw.get("address") or {}
    hours = raw.get("hours") or {}
    connectors = [_parse_connector(c) for c in (raw.get("circuits") or [])]

    return Station(
        station_id=_station_id_for(raw, index),
        name=raw.get("name") or "WVV Ladestation",
        description=raw.get("description"),
        street=address.get("street"),
        zip_code=address.get("zipCode"),
        city=address.get("city"),
        latitude=raw.get("lat"),
        longitude=raw.get("lon"),
        accessibility=raw.get("accessibilityType"),
        twentyfourseven=hours.get("twentyfourseven"),
        published=bool(raw.get("published", True)),
        connectors=connectors,
    )


def parse_charging_response(payload: dict[str, Any]) -> list[Station]:
    """Parse the raw /api/charging JSON payload into a list of Stations."""
    try:
        places = payload["operator"]["operatorPlaces"]
    except (KeyError, TypeError) as err:
        raise WvvChargingApiError(f"Unexpected API response shape: {err}") from err

    stations = [_parse_station(place, idx) for idx, place in enumerate(places)]
    return [s for s in stations if s.published]


class WvvChargingApiClient:
    """Thin async client for the smartandpublic charging API."""

    def __init__(self, session: aiohttp.ClientSession, url: str = API_URL) -> None:
        self._session = session
        self._url = url

    async def async_get_stations(self) -> list[Station]:
        """Fetch and parse all WVV charging stations."""
        try:
            async with self._session.get(
                self._url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                resp.raise_for_status()
                payload = await resp.json()
        except asyncio.TimeoutError as err:
            raise WvvChargingApiError("Timed out contacting the WVV charging API") from err
        except aiohttp.ClientError as err:
            raise WvvChargingApiError(f"Error contacting the WVV charging API: {err}") from err

        try:
            return parse_charging_response(payload)
        except WvvChargingApiError:
            raise
        except Exception as err:  # defensive: malformed payload shape
            raise WvvChargingApiError(f"Could not parse WVV charging API response: {err}") from err
