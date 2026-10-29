# Contributing / releasing

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
