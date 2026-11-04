import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const docsDir = path.join(__dirname, '..', 'docs')
const workedDir = path.join(docsDir, 'worked')

// docs/worked/foo_bar.py belongs to docs/foo-bar.md. Each script prints a JSON
// map of fragment names to Markdown, and the page holds each fragment between
// <!-- worked:name --> and <!-- /worked:name --> markers.
const args = process.argv.slice(2)
const check = args.includes('--check')
const pageIndex = args.indexOf('--page')
const only = pageIndex >= 0 ? args[pageIndex + 1] : null

const examples = fs.readdirSync(workedDir)
  .filter((file) => file.endsWith('.py') && file !== 'toy_curve.py')
  .map((source) => ({ source, page: `${source.slice(0, -3).replace(/_/g, '-')}.md` }))
  .filter(({ page }) => !only || page === `${only}.md`)
if (only && !examples.length) {
  console.error(`No worked example for page: ${only}`)
  process.exit(1)
}

let stale = 0
for (const { source, page } of examples) {
  const result = spawnSync('python3', [path.join(workedDir, source)], {
    encoding: 'utf8',
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
  })
  if (result.status !== 0) {
    console.error(`FAIL ${source}\n${result.stderr}`)
    process.exit(1)
  }
  const pagePath = path.join(docsDir, page)
  const before = fs.readFileSync(pagePath, 'utf8')
  let after = before
  for (const [name, body] of Object.entries(JSON.parse(result.stdout))) {
    const open = `<!-- worked:${name} -->`
    const close = `<!-- /worked:${name} -->`
    const start = after.indexOf(open)
    const end = after.indexOf(close)
    if (start < 0 || end < 0) {
      console.error(`${page} has no markers for fragment ${name}`)
      process.exit(1)
    }
    after = `${after.slice(0, start + open.length)}\n\n${body}\n\n${after.slice(end)}`
  }
  if (after !== before) {
    stale++
    if (!check) fs.writeFileSync(pagePath, after)
    console.log(`${check ? 'stale' : 'ok  '} ${page}`)
  }
}
if (check && stale) {
  console.error('Worked examples are out of date. Run pnpm docs:worked.')
  process.exit(1)
}
