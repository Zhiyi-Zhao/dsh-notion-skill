# Changelog

## 1.0.0 - 2026-08-27

- Initial release: DSH Notion skill (SKILL.md + notion_api.py) reading and writing Notion workspaces through the official REST API.
- Subcommands: whoami / search / page-get / page-blocks / page-create / page-update / block-append / db-query / db-create / db-entry-create / db-entry-update.
- Zero-dependency Python helper (standard library only), cross-platform (Windows / macOS / Linux).
- Installable via `dsh plugin add` (dsh.bundle manifest) or the bundled install scripts.
- Unit tests (Python) and cordis provider tests (Node), CI on GitHub Actions.
