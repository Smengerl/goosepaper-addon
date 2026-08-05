# Contributing

Thanks for your interest in contributing to Goosepaper! Contributions are welcome and
appreciated. To make collaboration smooth, please follow these guidelines.

## How to Contribute

1. **Fork the repository** and create a feature branch
2. **Make your changes** in a clearly named branch (e.g., `fix/rss-encoding` or
   `feat/add-mastodon-example`)
3. **Write clear commit messages** following [Conventional Commits](https://www.conventionalcommits.org/)
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `chore:` for dependency bumps, version bumps, and similar housekeeping
   - `refactor:` for code refactoring
4. **Keep the docs in sync** — see AGENTS.md's "Documentation to keep current with every change"
   for exactly which of README.md/DOCS.md/DEVELOPMENT.md/CHANGELOG.md a given change touches;
   they have distinct audiences (end user vs. developer) and Home Assistant shows some of them
   verbatim in its own UI, so it's not just "update everything"
5. **Open a Pull Request** with a clear description of what you changed and why

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/goosepaper-addon.git
cd goosepaper-addon
```

From there, see DEVELOPMENT.md's "Running locally" section for the actual `uv sync`/
`preview.sh`/`run.sh` workflow — not repeated here to avoid the two drifting out of sync.

There's no automated test suite in this repo yet (see AGENTS.md's "Known nits") — verify a
change by actually generating a newspaper via `./preview.sh` and checking the resulting PDF.
Tests around `config_schema.py`'s Pydantic models would be a genuinely useful contribution if
you're looking for a good first PR.

## Project-Specific Notes

This add-on is a thin wrapper: scheduling (`scheduler.py`), the two-layer JSON config
(`config_schema.py`), delivery orchestration (`deliver.py`), and the Home Assistant add-on
manifest (`config.yaml`/`repository.yaml`/`Dockerfile`). Most *content* features — new story
providers, RSS filtering behavior, puzzle types, paper styles — actually belong in
[goosepaper-logicpuzzles](https://github.com/Smengerl/goosepaper-logicpuzzles), the fork this
add-on depends on (pinned via `uv.lock`, see AGENTS.md's "Dependency on the fork"). If what
you're adding isn't specific to Home Assistant/Supervisor packaging or this add-on's own config
schema, it's very likely a better fit as a PR against that repo instead.

## Code Style

- Follow the conventions already in the file you're editing over generic PEP 8 — this codebase
  favors explanatory docstrings/comments that capture *why* a piece of code exists (a specific
  upstream quirk it works around, a constraint it satisfies), not just *what* it does
- Add type hints for new function parameters and return values
- Keep functions small and focused; prefer Pydantic validation (`config_schema.py`) over ad-hoc
  checks for anything config-shaped

## Reporting Issues

- **Search existing issues** before opening a new one
- **Provide clear reproduction steps** with expected vs. actual behavior
- **Include your environment**: Home Assistant/Supervisor version, add-on version, and
  architecture (this add-on currently only supports `aarch64`)
- **Attach relevant logs** (`Honk!`-prefixed lines are this add-on's own; see DOCS.md's "Logs"
  section for how to get more detail out of the underlying generation libraries)

## Questions?

Check [README.md](README.md) and [DOCS.md](DOCS.md) first — installation, configuration, and
day-to-day usage are documented there. For anything else, open an issue.

## License

By contributing, you agree that your contributions will be licensed under the
[Apache License 2.0](LICENSE).
