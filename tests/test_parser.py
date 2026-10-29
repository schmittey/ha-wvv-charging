"""Standalone test for the WVV charging API parser.

Runs the parser against a saved sample response (a trimmed excerpt of the
real https://map.smartandpublic.eu/api/charging payload) and checks the
derived fields the Home Assistant integration relies on.

Usage:
    python3 tests/test_parser.py
"""
from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

# Import api.py (and its sibling const.py) directly, without executing
# custom_components/wvv_charging/__init__.py, which pulls in the real
# Home Assistant package that isn't installed in this test environment.
_PKG_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "wvv_charging"
_pkg = types.ModuleType("wvv_charging")
_pkg.__path__ = [str(_PKG_DIR)]
sys.modules["wvv_charging"] = _pkg
api = importlib.import_module("wvv_charging.api")

SAMPLE_PATH = Path(__file__).resolve().parent / "sample_response.json"


def _load_sample() -> dict:
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def test_unpublished_stations_are_filtered() -> None:
    payload = _load_sample()
    stations = api.parse_charging_response(payload)
    # The sample contains 5 raw places, 2 of which are published=false.
    assert len(stations) == 3, f"expected 3 published stations, got {len(stations)}"
    assert all(s.published for s in stations)


def test_fully_available_station() -> None:
    stations = api.parse_charging_response(_load_sample())
    station = next(s for s in stations if s.street == "Rüdigerstr. 3")

    assert station.total_points == 2
    assert station.free_points == 2
    assert station.free_of_total == "2/2"
    assert station.status == api.STATION_STATUS_AVAILABLE
    assert station.any_free is True
    assert station.plug_types == ["TYP2"]
    assert station.max_power_kw == 22.0
    assert station.city == "Würzburg"
    assert station.zip_code == "97070"


def test_partially_occupied_dc_station() -> None:
    stations = api.parse_charging_response(_load_sample())
    station = next(s for s in stations if s.street == "Salvatorstraße 26")

    assert station.total_points == 2
    assert station.free_points == 0  # one unavailable, one charging: none free
    assert station.free_of_total == "0/2"
    assert station.any_free is False
    assert station.status == api.STATION_STATUS_OCCUPIED
    assert station.max_power_kw == 300.0
    assert "CCS" in station.plug_types


def test_fully_unavailable_station_is_out_of_order() -> None:
    stations = api.parse_charging_response(_load_sample())
    station = next(s for s in stations if s.street == "Bismarckstraße 13")

    assert station.free_points == 0
    assert station.status == "out_of_order"
    assert station.any_free is False


def test_station_id_is_stable_and_unique() -> None:
    stations = api.parse_charging_response(_load_sample())
    ids = [s.station_id for s in stations]
    assert len(ids) == len(set(ids)), "station ids must be unique"
    for station_id in ids:
        assert station_id, "station id must not be empty"


def test_station_id_fallback_without_evse_id() -> None:
    # A station with no circuits/evseId at all must still get a stable id,
    # derived from its coordinates rather than crashing or being dropped.
    raw_place = {
        "name": "No EVSE station",
        "circuits": [],
        "lat": 49.775997,
        "lon": 9.938008,
        "published": True,
        "address": {},
        "hours": {},
    }
    station_id = api._station_id_for(raw_place, index=0)
    assert station_id == "geo:49.775997:9.938008"


def test_distance_km_is_reasonable() -> None:
    stations = api.parse_charging_response(_load_sample())
    station = next(s for s in stations if s.street == "Rüdigerstr. 3")
    # Würzburg city centre (Residenz) is roughly 1-3 km from this station.
    distance = station.distance_km(49.7913, 9.9534)
    assert distance is not None
    assert 0.5 < distance < 5.0


def run_all() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as err:
            failures += 1
            print(f"FAIL {test.__name__}: {err}")
        else:
            print(f"PASS {test.__name__}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests passed")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
