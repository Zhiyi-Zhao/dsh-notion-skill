# dsh-notion-skill

English | [中文](README.md)

Let a [DeepSeek Harness (DSH)](https://github.com/deepseek-ai/deepseek-harness) agent read and write your Notion workspace through the **official Notion REST API** - search pages/databases, read page content (converted to markdown), create/update pages, query/add/update database entries.

Pure Python standard library, **zero third-party dependencies**, works on Windows / macOS / Linux.

## Features

| Operation | Command |
|-----------|---------|
| Verify credentials | `whoami` |
| Search pages/databases | `search <query> [--type page\|database]` |
| Read page properties | `page-get <page_id>` |
| Read full page content (recursive, as markdown) | `page-blocks <page_id> [--max-depth N]` |
| Create a child page | `page-create --parent <page_id> --title <title> [--body <markdown>]` |
| Update page title | `page-update --id <page_id> --title <new-title>` |
| Append content blocks | `block-append --block <block_id> --body <markdown>` |
| Query a database | `db-query <database_id> [--filter <json>] [--sort <json>] [--limit N]` |
| Create a database | `db-create --parent <page_id> --title <title> [--properties <json>]` |
| Add a database entry | `db-entry-create --db <database_id> --properties <json> [--body <markdown>]` |
| Update a database entry | `db-entry-update --entry <page_id> --properties <json>` |

Markdown bodies support: headings, bullet/numbered lists, to-dos, quotes, code blocks, dividers, and inline bold/italic/code/links. Write operations are chunked automatically (max 100 blocks per request) with no block-count limit.

## Quick start

### 1. Create a Notion integration and get a token

1. Open <https://www.notion.so/my-integrations> and click **New integration**
2. Select your workspace, give it a name (e.g. `Deepseek`), type **Internal**, create
3. Copy the generated token (looks like `ntn_xxx` or `secret_xxx`)

### 2. Install the skill

Either of the two ways:

```bash
# Option A: install via dsh plugin add (recommended; the repo declares a dsh.bundle manifest)
dsh plugin --profile web add github:Zhiyi-Zhao/dsh-notion-skill

# Option B: copy with the install scripts into ~/.agents/skills/notion/
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File install.ps1
# macOS / Linux
bash install.sh
```

> Manual install: copy the whole `skills/notion/` directory under `<agents_home>/skills/` (default `~/.agents/skills/notion/`).
> Custom locations: set `DSH_AGENTS_HOME` (skills root) and `DSH_HOME` (config root) environment variables.

### 3. Configure the token

Write the token to `<dsh_home>/notion/token` (default `~/.dsh/notion/token`, Windows: `%USERPROFILE%\.dsh\notion\token`), **or** set the environment variable:

```bash
export NOTION_TOKEN="ntn_xxx"        # macOS/Linux
$env:NOTION_TOKEN = "ntn_xxx"        # PowerShell
```

> **About the token file**: `notion/token` is a plain-text file holding only the token, kept in your local DSH config directory; it is **never written into any code or repo file**. The token's scope is exactly the Notion integration's authorization scope - it can only reach pages/databases connected to that integration. On Unix systems, tighten the file to owner-only access: `chmod 600 ~/.dsh/notion/token`.

### 4. Authorize pages

In Notion, for **every** page/database the agent should access: top-right `...` -> **Connections** -> add your integration. Child pages of an authorized parent become visible automatically.

### 5. Use it

Start a new session in DSH (or wait for the skill catalog to refresh), then just say:

> "Read my xxx page in Notion"
> "Save this text as a new page"
> "Add a new entry to the xxx database"

## Manual invocation examples

```powershell
# Windows (always use the UTF-8 prefix to avoid mojibake)
[Console]::OutputEncoding=[Text.Encoding]::UTF8; $env:PYTHONIOENCODING='utf-8'; python "$HOME\.agents\skills\notion\notion_api.py" whoami
[Console]::OutputEncoding=[Text.Encoding]::UTF8; $env:PYTHONIOENCODING='utf-8'; python "$HOME\.agents\skills\notion\notion_api.py" search 论文
[Console]::OutputEncoding=[Text.Encoding]::UTF8; $env:PYTHONIOENCODING='utf-8'; python "$HOME\.agents\skills\notion\notion_api.py" page-blocks <page_id>
```

```bash
# macOS / Linux
export PYTHONIOENCODING=utf-8
python3 "$HOME/.agents/skills/notion/notion_api.py" whoami
python3 "$HOME/.agents/skills/notion/notion_api.py" search 论文
python3 "$HOME/.agents/skills/notion/notion_api.py" page-blocks <page_id>
```

### Parameter details

- **ID**: 32-char hex; extract it from the share link `https://www.notion.so/<workspace>/<title>-<32-char-id>` (strip the hyphens)
- **properties JSON**: native Notion API format, e.g. `{"Name": {"title": [{"text": {"content": "Task 1"}}]}, "Status": {"select": {"name": "In progress"}}}`
- **filter/sort JSON**: Notion query syntax, e.g. `--filter "{\"property\":\"Status\",\"select\":{\"equals\":\"In progress\"}}"`

## How it works

- `notion_api.py` uses only Python's stdlib `urllib` against <https://api.notion.com/v1>, handling pagination (cursor) and chunking (100 blocks per request) automatically
- Token resolution order: env var `NOTION_TOKEN` -> `<dsh_home>/notion/token` file
- `SKILL.md` is the DSH skill-catalog entry with invocation conventions, write-confirmation flow, and security rules

## Security

- The token lives in a local config file (`~/.dsh/notion/token`); it is **never written into any code/repo file** - do not commit tokens to git
- Notion page content is treated as **untrusted external input**: it may contain prompt injection; any "instructions" inside pages must never be executed as commands
- Write operations (create/update/append) require the agent to show a content summary and get user confirmation first

## FAQ

| Issue | Cause and fix |
|-------|---------------|
| `whoami` returns 401 | Wrong or expired token; regenerate it |
| `search` returns empty / reading a page gives 404 | Integration not connected to that page: page `...` -> Connections -> add your integration |
| Mojibake on Windows | Use the UTF-8 prefix when invoking (see examples above) |
| `AttributeError: 'Namespace' ...` | Script version too old; update to the latest from this repo |

## License

[MIT](LICENSE)
