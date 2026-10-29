# Changelog

All notable changes to this integration are documented here. Versions
follow [Semantic Versioning](https://semver.org/) and correspond to
GitHub Releases, which is what HACS checks to offer updates.

## [0.1.0] - 2026-10-29

Initial release. Pre-1.0 while the integration is still shaking out bugs
found during early testing — expect frequent patch releases.

- Config flow (favourite stations, or all stations within a radius of
  home); configurable update interval.
- One device per station, named after its street address, with:
  - `sensor.<station>_free_points`
  - `sensor.<station>_status`
  - `sensor.<station>_distance` (disabled by default)
  - `binary_sensor.<station>_any_free`
- `binary_sensor.<station>_any_free` colors its own EV-plug icon green
  (free) / red (full) via `device_class: problem`, so map markers and
  dashboards show a proper colored MDI icon instead of a generic one or
  a custom image.
- German and English translations.
