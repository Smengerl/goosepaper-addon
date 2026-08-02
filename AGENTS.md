# Working on this repo

This is a Home Assistant add-on wrapping [goosepaper-logicpuzzles](https://github.com/Smengerl/goosepaper-logicpuzzles)
(a public fork of `j6k4m8/goosepaper`, pinned via git in `uv.lock`) with a two-layer JSON config,
a scheduler entrypoint, and the HA add-on manifest (`config.yaml`/`repository.yaml`/`Dockerfile`).

## Deploying a change to the real add-on

The user tests changes on a real Home Assistant Green (`arch: aarch64`, a Rockchip RK3566 -
modest hardware). Getting a change from a local commit to actually running there has several
non-obvious steps; skipping any of them leads to "I pushed but nothing changed" confusion.

1. **Bump `version` in `config.yaml` for every change meant to reach the add-on.** Supervisor
   only offers an update when the version strictly increases - it does not diff file contents.
   A code change with no version bump is invisible to Supervisor, full stop.
2. **Push to GitHub, then tell the user to manually refresh the Add-on Store**
   (Settings → Add-ons → Add-on Store → reload icon, top right) before expecting Supervisor to
   see the new version. Supervisor's store listing is driven by a *locally cached git clone*
   (`/data/apps/git/<repo-slug>`) that does **not** re-sync with GitHub on every check - only on
   its own periodic cycle (observed ~3h apart in Supervisor logs) or on that manual reload. The
   `rebuild` action (via `ha_manage_addon`) rebuilds the Docker image from whatever is already
   cloned locally - it does **not** `git pull` first, so it will happily rebuild the *old* code
   and report success. `update` (the real action to use) refuses outright with
   "No update available" until the store cache has actually refreshed.
3. **Expect the build itself to take several minutes** (WeasyPrint/Pango compiled fresh on ARM
   every time - there is no prebuilt image yet, see the Roadmap section in `README.md`). Any
   `install`/`update`/`rebuild` API call will very likely hit an MCP/HTTP client timeout well
   before the build finishes - this is *not* a failure, the job keeps running server-side
   regardless. Verify actual progress via Supervisor's own logs instead of trusting the call's
   return status:
   ```
   ha_get_logs(source="system_service", slug="supervisor", search="goosepaper")
   ```
   Look for `docker buildx build`, `successfully rebuilt` / `successfully installed`, and
   `Starting Docker app ... with version X.Y.Z` to confirm what actually landed.
4. **The whole HA instance can become briefly unreachable** (even for plain read-only API calls)
   while a build is consuming resources on the Green - don't read that as the deploy having
   failed. Wait and retry a couple of times before concluding something is actually stuck.
5. After a real update, **confirm the installed version, not just `update_available`**:
   `ha_get_addon(slug=...)` returns both `version` (currently installed/running) and
   `version_latest` (what the store has) - they should match once the update has actually
   completed and the add-on has restarted.

## Known nits (not blocking, but worth fixing opportunistically)

- Supervisor logs a validation warning on every load: `App 'Goosepaper' uses legacy map type
  'addon_config'; use 'app_config' instead.` `config.yaml`'s `map: [addon_config:rw]` should be
  updated to `app_config:rw` to match the current schema and silence this - not yet done.
- No prebuilt image (see `README.md`'s Roadmap section: a GitHub Actions workflow using
  `home-assistant/builder`, pushing to a registry, is the intended fix for the slow-build pain
  described above). Worth prioritizing given how much friction the on-device build causes for
  routine iteration.

## Dependency on the fork

`pyproject.toml` points `goosepaper` at `Smengerl/goosepaper-logicpuzzles`'s `mainline` branch;
`uv.lock` pins an exact commit. A feature landing on the fork does **not** automatically appear
here - run `uv lock --upgrade-package goosepaper && uv sync` locally, verify (`uv run python -c
"import scheduler"` at minimum, ideally a real PDF generation via `./preview.sh` or `deliver.py`
directly), then commit the updated `uv.lock` alongside any addon-side code that depends on the
new feature. If addon-side code (`deliver.py`/`config_schema.py`) references something not yet
on `mainline`, it will fail to import - check `git show origin/mainline:<path>` on the fork repo
to confirm a symbol actually exists there before assuming a local import error is a bug in this
repo.
