# Changelog

All notable changes to this integration are documented here. Versions
follow [Semantic Versioning](https://semver.org/) and correspond to
GitHub Releases, which is what HACS checks to offer updates.

## [1.0.0] - 2026-10-29

Initial release.

- Config flow (favourite stations, or all stations within a radius of
  home); configurable update interval.
- One device per station, named after its street address, with:
  - `sensor.<station>_free_points`
  - `sensor.<station>_status`
  - `sensor.<station>_distance` (disabled by default)
  - `binary_sensor.<station>_any_free`
- Colored (green/red) map markers reflecting free/occupied state.
- German and English translations.
