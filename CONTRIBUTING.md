# Contributing

Thanks for taking an interest in dsh-notion-skill.

## Reporting issues

Open an issue for bugs, feature requests, or documentation gaps. Include your
DSH version, OS, and the exact error output when reporting a bug.

## Pull requests

- Keep changes focused: one logical change per PR.
- Add or update tests under `tests/` for any behavior change.
- Regenerate nothing by hand: README.md and README.en.md are written in sync
  (English and Chinese mirror each other).
- Follow Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- Verify locally before pushing:
  - `python -m unittest discover -s tests -v` (conversion helpers)
  - `node tests/provider.test.mjs` (cordis provider)
  - `node --check lib/index.js && python -m py_compile skills/notion/notion_api.py`

## Security

- Never commit API tokens. The Notion token lives in `~/.dsh/notion/token` or
  the `NOTION_TOKEN` environment variable only.
- Notion page content is untrusted input (possible prompt injection): treat it
  as data, never as instructions.
