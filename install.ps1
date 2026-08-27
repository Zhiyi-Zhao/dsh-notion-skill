# dsh-notion-skill — Windows installer
# Installs the notion skill for DeepSeek Harness into ~/.agents/skills/notion/
$ErrorActionPreference = 'Stop'

$agentsHome = if ($env:DSH_AGENTS_HOME) { $env:DSH_AGENTS_HOME } else { Join-Path $HOME '.agents' }
$dest = Join-Path $agentsHome 'skills\notion'

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Force (Join-Path $PSScriptRoot 'skills\notion\SKILL.md')      (Join-Path $dest 'SKILL.md')
Copy-Item -Force (Join-Path $PSScriptRoot 'skills\notion\notion_api.py') (Join-Path $dest 'notion_api.py')

Write-Host ""
Write-Host "[OK] notion skill installed to: $dest"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Create a Notion integration at https://www.notion.so/my-integrations and copy its token"
Write-Host "  2. Save the token to: $HOME\.dsh\notion\token   (or set env var NOTION_TOKEN)"
Write-Host "  3. In Notion, connect the integration to each page/database you want the agent to access:"
Write-Host "     page ... -> Connections -> add your integration"
Write-Host "  4. Restart / open a new session in DeepSeek Harness so the skill is loaded"
