// Unit tests for the dsh-notion-skill cordis provider (lib/index.js).
// Uses only node:test and node:assert — no framework, no network.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseFrontmatter, apply, name } from '../lib/index.js'

function loadProvider() {
  const providers = []
  const ctx = { skills: { registerProvider: (fn) => providers.push(fn({})) } }
  apply(ctx)
  assert.equal(providers.length, 1, 'provider must be registered')
  return providers[0]
}

test('plugin identity', () => {
  assert.equal(name, 'dsh-notion-skill')
})

test('parseFrontmatter extracts scalar metadata and body', () => {
  const text = '---\nname: notion\ndescription: 测试描述\nversion: 1.0.0\n---\n\n# Body\n\n内容'
  const parsed = parseFrontmatter(text)
  assert.ok(parsed)
  assert.equal(parsed.metadata.name, 'notion')
  assert.equal(parsed.metadata.description, '测试描述')
  assert.match(parsed.body, /^# Body/)
})

test('parseFrontmatter handles quoted values', () => {
  const parsed = parseFrontmatter('---\nname: "notion"\ndescription: \'带 空格 的 描述\'\n---\n\nbody')
  assert.equal(parsed.metadata.name, 'notion')
  assert.equal(parsed.metadata.description, '带 空格 的 描述')
})

test('parseFrontmatter returns null without a frontmatter block', () => {
  assert.equal(parseFrontmatter('no frontmatter'), null)
})

test('list() discovers exactly the notion skill', async () => {
  const provider = loadProvider()
  const candidates = await provider.list({ signal: undefined })
  assert.equal(candidates.length, 1)
  assert.equal(candidates[0].name, 'notion')
  assert.equal(candidates[0].provider, 'dsh-notion-skill')
  assert.equal(candidates[0].invocation.modelInvocable, true)
  assert.equal(candidates[0].invocation.userInvocable, true)
  assert.equal(candidates[0].path.split(/[\\/]/).slice(-3).join('/'), 'skills/notion/SKILL.md')
})

test('get() returns the full definition with a directory resource base', async () => {
  const provider = loadProvider()
  const [candidate] = await provider.list({ signal: undefined })
  const skill = await provider.get(candidate, { signal: undefined })
  assert.equal(skill.name, 'notion')
  assert.ok(skill.description.length > 0)
  assert.match(skill.content, /Notion Integration/)
  assert.equal(skill.resourceBase.kind, 'directory')
  assert.equal(skill.resourceBase.path.split(/[\\/]/).slice(-2).join('/'), 'skills/notion')
})
