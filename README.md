# WVV Charging (Würzburg) – Home Assistant Integration

A custom [Home Assistant](https://www.home-assistant.io/) integration that shows the
live status of public EV charging stations operated by [WVV Energie](https://www.wvv.de/)
in and around Würzburg, as listed on
[wvv.de/elektromobilitaet/laden-in-wuerzburg](https://www.wvv.de/elektromobilitaet/laden-in-wuerzburg/).

## Data source

The WVV charging map embeds a third-party widget
(`https://map.smartandpublic.eu/map`) that pulls its data from a public,
unauthenticated JSON endpoint:

```
GET https://map.smartandpublic.eu/api/charging
```

This integration polls that same endpoint directly — no scraping, no
browser automation, no API key. It currently returns roughly 240 published
WVV stations with live per-connector status, which is refreshed by WVV's
backend continuously. Pricing information is **not** part of this payload;
entities link to [wvv.de/elektromobilitaet/ladepreis](https://www.wvv.de/elektromobilitaet/ladepreis/)
instead of guessing a price.

## Features

- UI-based config flow (no YAML)
- Pick either:
  - a list of favourite stations, or
  - every published station within a radius (km) of your Home Assistant
    home location
- Configurable update interval (default 5 minutes, minimum 1 minute)
- One Home Assistant **device** per charging station, named after its
  street address (e.g. "Rüdigerstr. 3") rather than WVV's generic,
  repeated API name ("WVV Energie E-Ladestation") — addresses that occur
  more than once (large parking garages with several charge points) get
  a trailing `#2`, `#3`, ... to stay unique. Each device has:
  - `sensor.<station>_free_points` – number of free charge points right
    now (state_class `measurement`, so it works in history/statistics),
    with attributes: address, max power (kW), plug types, per-connector
    detail, total points, `free_of_total` (e.g. `"2/4"`), accessibility,
    24/7 flag, and a link to WVV's price page
  - `sensor.<station>_status` – `available` / `occupied` / `out_of_order`
    / `unknown`
  - `sensor.<station>_distance` – distance from your HA home location in
    km (disabled by default, enable it per-entity if you want it)
  - `binary_sensor.<station>_any_free` – **on** when at least one charge
    point is free (handy for automations)
  - `latitude` / `longitude` attributes on every entity, so stations can
    be plotted on a Home Assistant **Map** card — there, each station
    shows as a small green (free) or red (no free point) marker instead
    of a generic icon
- A single shared HTTP request per update cycle (not one per station)
- Graceful handling of WVV/API outages: entities become `unavailable`,
  and Home Assistant's coordinator logging avoids repeated log spam
- German and English translations

## Installation

### Via HACS (custom repository)

1. In HACS, go to **Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/schmittey/ha-wvv-charging` as an
   **Integration**.
3. Install **WVV Charging (Würzburg)** from HACS.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration**, search for
   "WVV Charging", and follow the setup wizard.

### Manual

1. Copy `custom_components/wvv_charging` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration via **Settings → Devices & Services → Add
   Integration → WVV Charging**.

## Configuration

During setup you choose:

- **Station selection**: pick favourite stations from a searchable list,
  or select every station within a radius of your HA home location.
- **Update interval**: in minutes, minimum 1.

Both can be changed later via the integration's **Configure** button.

## Example dashboard card

See [`examples/dashboard-card.yaml`](examples/dashboard-card.yaml) for a
ready-to-use entities card plus a map card showing all configured
stations.

## Example automation

See [`examples/automation-notify.yaml`](examples/automation-notify.yaml)
for an automation that notifies you as soon as a specific station has a
free charge point.

## Development / testing

A standalone parser test runs against a saved sample API response
(`tests/sample_response.json`, a trimmed excerpt of the real public
payload) without requiring a full Home Assistant install:

```bash
python3 tests/test_parser.py
```

## Versioning & releases

HACS detects updates by watching this repo's **GitHub Releases**, matched
against the `version` field in `custom_components/wvv_charging/manifest.json`.
A `release` workflow (`.github/workflows/release.yml`) automates this:
pushing a tag `vX.Y.Z` creates a matching GitHub Release automatically
(it first checks the tag matches `manifest.json`, so the two can't drift
apart). A separate `validate` workflow runs HACS's and Home Assistant's
own validation (`hacs/action`, `hassfest`) on every push and PR.

To cut a new release:

1. Bump `"version"` in `custom_components/wvv_charging/manifest.json`
   (follow [SemVer](https://semver.org/): patch for fixes, minor for new
   features, major for breaking changes).
2. Add an entry to `CHANGELOG.md`.
3. Commit, then tag and push:
   ```bash
   git tag vX.Y.Z
   git push origin main --tags
   ```
4. The `release` workflow creates the GitHub Release; HACS will then
   offer the update to anyone with this repo installed.

## Disclaimer

This is an unofficial, community-built integration. It is not affiliated
with or endorsed by WVV Energie or smartandpublic. Station data and
availability are provided by WVV's public charging map; this integration
only reads it.
