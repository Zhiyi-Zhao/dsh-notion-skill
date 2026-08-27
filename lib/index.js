// dsh-notion-skill: Notion integration skill for the DeepSeek Harness.
//
// A Cordis plugin that registers one skill provider into the HOST layer of the
// `ctx.skills` registry, so every agent preset's scope chain merges this
// skill. The skill body lives at `../skills/notion/SKILL.md` inside this
// package; the provider locates it from `import.meta.url` (an assembly fact of
// this package, never user config) and loads the body on demand. The
// `notion_api.py` helper sits in the same directory and is exposed through the
// candidate's directory resource base.
//
// The provider protocol mirrors @deepseek-ai/dsh-skill-filesystem:
//   - list()  discovers the directory-bundle candidate (name/description from
//     YAML frontmatter, body left unread until requested)
//   - get()   parses the candidate's SKILL.md and returns the full definition
//     with a directory resource base for relative references
//
// @module dsh-notion-skill
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const name = 'dsh-notion-skill'
const inject = ['skills']

/** Registry precedence for packaged skill providers: ranks below the local bundled root. */
const PACKAGED_SKILL_RANK = 550

/** The source bucket this skill advertises under (prompt-visible metadata). */
const SOURCE = 'custom'

/**
 * Parse the YAML frontmatter block of a SKILL.md into metadata plus body.
 * Handles only the scalar fields DSH skill discovery consumes (name,
 * description, whenToUse); richer metadata passes through verbatim.
 * @param text - the raw skill file contents.
 * @returns parsed metadata object and the markdown body after the block, or
 *   null when the file has no frontmatter block at all.
 */
function parseFrontmatter(text) {
  if (!text.startsWith('---')) return null
  const end = text.indexOf('\n---', 3)
  if (end === -1) return null
  const block = text.slice(3, end)
  const body = text.slice(end + 4).replace(/^\n+/, '')
  const metadata = {}
  for (const line of block.split('\n')) {
    const match = /^([A-Za-z][\w-]*):\s*(.*)$/.exec(line.trim())
    if (!match) continue
    let value = match[2].trim()
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1)
    }
    metadata[match[1]] = value
  }
  return { metadata, body }
}

/**
 * Read and parse one skill directory's SKILL.md.
 * @param skillFile - absolute path to the SKILL.md file.
 * @param signal - optional cancellation; aborts the read.
 * @returns the parsed skill record, or undefined when the file vanished.
 */
async function parseSkillFile(skillFile, signal) {
  let text
  try {
    text = await readFile(skillFile, 'utf8')
  } catch {
    return undefined
  }
  if (signal?.aborted) return undefined
  const parsed = parseFrontmatter(text)
  if (parsed === null) return undefined
  return {
    name: parsed.metadata.name ?? '',
    description: parsed.metadata.description ?? '',
    whenToUse: parsed.metadata.whenToUse,
    metadata: parsed.metadata,
    content: parsed.body
  }
}

/** Register the packaged notion provider on `ctx.skills`. */
function apply(ctx) {
  const skillsRoot = join(dirname(fileURLToPath(import.meta.url)), '..', 'skills')
  const skillDir = join(skillsRoot, 'notion')
  const skillFile = join(skillDir, 'SKILL.md')
  ctx.skills.registerProvider((control) => ({
    name,
    async list(options) {
      const parsed = await parseSkillFile(skillFile, options.signal)
      if (parsed === undefined) return []
      return [{
        name: parsed.name,
        description: parsed.description,
        ...(parsed.whenToUse !== undefined ? { whenToUse: parsed.whenToUse } : {}),
        invocation: { modelInvocable: true, userInvocable: true },
        source: SOURCE,
        provider: name,
        rank: PACKAGED_SKILL_RANK,
        locator: skillDir,
        path: skillFile,
        ...(Object.keys(parsed.metadata).length > 0 ? { metadata: parsed.metadata } : {})
      }]
    },
    async get(candidate, options) {
      const parsed = await parseSkillFile(candidate.path, options.signal)
      if (parsed === undefined) return undefined
      return {
        name: parsed.name,
        description: parsed.description,
        ...(parsed.whenToUse !== undefined ? { whenToUse: parsed.whenToUse } : {}),
        invocation: { modelInvocable: true, userInvocable: true },
        source: SOURCE,
        provider: name,
        resourceBase: { kind: 'directory', path: candidate.locator },
        path: candidate.path,
        ...(Object.keys(parsed.metadata).length > 0 ? { metadata: parsed.metadata } : {}),
        content: parsed.content
      }
    }
  }))
}

export { apply, name, inject, parseFrontmatter }
export default { apply, name, inject, parseFrontmatter }
