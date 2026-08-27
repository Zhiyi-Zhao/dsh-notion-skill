#!/usr/bin/env bash
# dsh-notion-skill — macOS/Linux installer
# Installs the notion skill for DeepSeek Harness into ~/.agents/skills/notion/
set -euo pipefail

AGENTS_HOME="${DSH_AGENTS_HOME:-$HOME/.agents}"
DEST="$AGENTS_HOME/skills/notion"

mkdir -p "$DEST"
cp -f "$(dirname "$0")/skills/notion/SKILL.md"      "$DEST/SKILL.md"
cp -f "$(dirname "$0")/skills/notion/notion_api.py" "$DEST/notion_api.py"

echo ""
echo "[OK] notion skill installed to: $DEST"
echo ""
echo "Next steps:"
echo "  1. Create a Notion integration at https://www.notion.so/my-integrations and copy its token"
echo "  2. Save the token to: $HOME/.dsh/notion/token   (or set env var NOTION_TOKEN)"
echo "  3. In Notion, connect the integration to each page/database you want the agent to access:"
echo "     page ... -> Connections -> add your integration"
echo "  4. Restart / open a new session in DeepSeek Harness so the skill is loaded"
