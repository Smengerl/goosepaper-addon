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
   every time - there is no prebuilt image yet, see the Roadmap section in `DEVELOPMENT.md`). Any
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

## Release & versioning policy

Version format: `major.minor.bugfix` (`config.yaml`'s `version` field).
This is the policy for *which* number to bump and whether to ask first -
same policy as the sibling project `ha-tibber-vehicle`'s `CLAUDE.md`, kept
consistent across both:

- **Bugfix** (the third number): a single, small fix. No `CHANGELOG.md`
  entry is required for what a bugfix bump actually contains (this repo's
  existing `CHANGELOG.md` entries mostly *do* describe patch-level fixes
  in detail - that's fine to keep doing when it's genuinely useful, just
  no longer a requirement). **Always ask the user before bumping** -
  confirm per change whether it should increment the bugfix number, even
  mid-iteration while testing a deploy (see "Deploying a change to the
  real add-on" above - don't fold a bugfix bump into that loop unasked
  just because Supervisor needs a version increase to offer an update).
- **Minor** (the second number): used whenever a new feature is
  introduced. Gets a brief `CHANGELOG.md` entry under the new version
  heading - concise, not full commit-level detail (see "Documentation to
  keep current with every change" below for the existing writing-style
  guidance, which still applies). If it's unclear whether a change is
  substantial enough to warrant a minor bump versus staying at
  bugfix-level, **ask the user for confirmation** rather than deciding
  unilaterally.
- **Major** (the first number): comprehensive changes, a thorough
  `CHANGELOG.md` entry. **Only the user bumps major, at their own
  explicit request.** Don't propose, suggest, or perform a major version
  bump on your own initiative under any circumstance - surface that a
  change seems major-sized if genuinely relevant, but the decision to
  actually bump stays with the user.

### Git tags

`config.yaml`'s `version` and the repo's git tags track two different things - Supervisor's
update mechanism (see "Deploying a change" above) only cares about the former, but a git tag is
what makes a version discoverable as a real release (GitHub's Releases page, anyone pinning a
specific commit, etc.). Keep them in sync at the **major.minor** level, but not on every single
bump:

- **Major/minor bump** (`1.4.0` → `1.5.0`, or `1.4.0` → `2.0.0`): push a matching git tag
  (`v1.5.0`) once the bump lands and is confirmed running - see "Deploying a change" above. This
  is what a git tag is *for* here: marking an actual release.
- **Bugfix-only bump** (`1.4.0` → `1.4.1`): bump `config.yaml` so
  Supervisor offers the update, but don't cut a new git tag for it - the existing `v1.4.0` tag
  stays the reference point for that minor line until the next major/minor bump.

This keeps tags meaningful (one per real release, not one per tiny fix) while Supervisor still
sees every change meant to reach the add-on, bugfix-level ones included.

## Config files: local working copy vs. live Home Assistant

`config/` (`addon_config.json` and each `*.goosepaper.json`) is gitignored - it's a user's
personal live configuration, not repo-tracked example data. Whether a local checkout of this repo
is also the live location the add-on actually reads from varies per user and per session - don't
assume either way. The condition that matters:

- The user has *some* way to reach their real Home Assistant instance directly - an MCP server,
  a mounted Samba share, SSH, Studio Code Server, the File editor add-on, etc. (see DOCS.md's
  "Editing your configuration" section for the options this add-on documents), **and**
- a `config/` file gets created or changed in a local working copy that is *not itself* that live
  location (e.g. a plain git checkout on the user's own machine, separate from wherever Home
  Assistant actually reads `/config`/`/addon_configs/<slug>` from).

When both hold, treat the local copy and the live instance as two separate things that can drift
silently - a change on one side has no effect on the running add-on until it reaches the other.
Don't assume they're already in sync, and don't push a change to the live side without asking:

1. After making (or discovering) a config change locally, tell the user plainly that it isn't live
   yet.
2. If you have a way to reach the live location, offer to check it - diff the live file against
   the one that was just changed, rather than assuming "no news is good news."
3. Ask whether the change should be synced/uploaded to Home Assistant now. Only do it once they
   say yes.
4. This runs in the opposite direction too: if a live-side edit turns up that isn't reflected
   locally (e.g. an earlier out-of-band edit made directly on the live instance), surface that
   drift and offer to reconcile it - don't silently overwrite one side with the other.

None of this applies if the "local checkout" already *is* the live config location (working
directly over a Samba mount, or via an MCP tool that reads/writes the real instance) - in that
case there's only one copy, nothing to synchronize.

## Known nits (not blocking, but worth fixing opportunistically)

- No prebuilt image, `aarch64`-only (see `DEVELOPMENT.md`'s Roadmap section: a GitHub Actions
  workflow using `home-assistant/builder`, pushing multi-arch images to a registry, is the
  intended fix for both the slow-build pain described above and the amd64/armv7 install gap).
  Deliberately deferred past v1 - real CI/build-pipeline work, and the on-device build works
  correctly today for the one arch the maintainer actually runs.

- `deliver.py`'s `_patched_get_root_state` monkeypatches `remarkapy.client.Client.get_root_state`
  at import time to force `schemaVersion` 4 (this account is reported as schema 3, and gets
  rejected by the reMarkable cloud on every write, even though it accepts schema-4 writes fine -
  see the function's own docstring). This patches a third-party library directly, not goosepaper -
  unlike every other fork-side fix in this project, there's no `goosepaper-logicpuzzles`-style
  staging fork for `remarkapy` to carry it as a real PR instead of a permanent runtime patch.
  Found during the scope-creep review (finding 5) - reported as
  [remarkapy#24](https://github.com/j6k4m8/remarkapy/issues/24), not a PR: research (see that
  issue - a closely analogous case in `erikbrinkman/rmapi-js#25`/`#29`) suggests schema 4 is a
  gradual, per-account server-side rollout, so forcing it unconditionally isn't verified safe for
  every account, only this one. Revisit `_patched_get_root_state` once that issue is resolved -
  it may no longer be needed, or need a narrower condition than "always 4".

## Supervisor terminology: "addon" vs. "app"

Home Assistant renamed add-ons to "apps" in the 2026.2 release, and Supervisor's internals
already reflect it (`supervisor.apps.app`, `supervisor.apps.manager`, `supervisor.apps.validate`,
paths like `/data/app_configs/<slug>` and `/data/apps/data/<slug>` - all confirmed via real logs
on the user's instance) even though the HA UI still says "Add-ons" everywhere a human sees it.

Concretely, `config.yaml`'s `map:` key should be `app_config:rw`, not the older `addon_config:rw`
- confirmed as a deliberate, in-progress migration via
[Supervisor issue #6905](https://github.com/home-assistant/supervisor/issues/6905) ("introduce
new mapping options, and with them mount to the new location... clear migration path"), which is
why Supervisor logs a "legacy map type" warning for `addon_config` rather than rejecting it
outright - both work today, `app_config` is the forward-looking one.

**The official docs are behind the actual software here** -
[developers.home-assistant.io/docs/apps/configuration](https://developers.home-assistant.io/docs/apps/configuration/)
still lists only `addon_config` as a valid `map` value as of this writing, with no mention of
`app_config` at all. Don't take that page as gospel for anything rename-adjacent; if something
HA-facing behaves unexpectedly and a doc or example you're going by says "addon", try
the "app" equivalent first before assuming it's actually broken.

## Documentation to keep current with every change

This split is confirmed against official guidance in
[Presenting your app](https://developers.home-assistant.io/docs/apps/presentation/) - README.md
is "a short description of what the app can do" shown in the store, DOCS.md "helps the consumer
of your app to understand its usage, explains configuration options", and CHANGELOG.md should
follow the [Keep a Changelog](https://keepachangelog.com/) format (that page's own explicit
recommendation) and is what users see as an upgrade notice. Update the ones a change actually
touches, every time - not as a separate cleanup pass later:

- **`CHANGELOG.md`** - every feature or user-visible change gets an entry under the version it
  shipped in, written at the same time as the `config.yaml` version bump (same commit, or the
  same small group of commits). If there's no entry for the version you just bumped to, the bump
  isn't finished yet. **Write for the add-on's users, not for a developer reading the code** - a
  couple of sentences on what changed and why it matters to someone running this add-on (does
  their generated PDF look different, does a log line change, do they need to do anything), not a
  walkthrough of the fork's internal commits, function names, or code paths. For anyone who wants
  that level of detail, link the actual commit(s)/PR(s) instead of writing the detail out inline -
  `goosepaper-logicpuzzles`@`<short-sha>` or a GitHub commit/PR URL - the repo history already has
  the full story, the changelog doesn't need to duplicate it.
- **`README.md`** - user-facing, not developer-facing. Home Assistant shows this file **verbatim**
  as the add-on's `long_description` in the Add-on Store (confirmed via `ha_get_addon`'s API
  response) - anyone browsing the store sees exactly what's in this file, not just GitHub
  visitors. It must read as "what does this add-on do and why would I install it", in plain
  language a Home Assistant user (not necessarily a developer) can follow.
- **`DOCS.md`** - the detailed reference, shown under the add-on's own "Documentation" tab in HA.
  Should cover the full feature set (not just the config file format) and walk through
  installation, configuration, and day-to-day usage in enough depth that a user never needs to
  read the source to answer "can this do X" or "how do I configure Y".
- **`DEVELOPMENT.md`** - build-from-source instructions, `uv`/Docker internals, and roadmap/TODO
  planning. Not shown anywhere in HA's UI - this is the one file in the set actually aimed at
  developers/contributors, kept separate specifically so it never leaks into what an end user
  sees.

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
