import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.join(__dirname, '..')
const manimDir = path.join(root, 'docs', 'manim')
const venvManim = path.join(root, '.manim-venv', 'bin', 'manim')

// docs/manim/foo-bar.diagrams.json lists the scenes for docs/foo-bar.md as
// [{ source, scene, output, resolution? }].
const diagrams = fs.readdirSync(manimDir)
  .filter((file) => file.endsWith('.diagrams.json'))
  .flatMap((file) => JSON.parse(fs.readFileSync(path.join(manimDir, file), 'utf8'))
    .map((entry) => ({ ...entry, page: file.replace('.diagrams.json', '') })))

const args = process.argv.slice(2)
if (args.length && (args.length !== 2 || args[0] !== '--page')) {
  console.error('Usage: pnpm docs:manim [--page <chapter-slug>]')
  process.exit(1)
}
const selected = args.length ? diagrams.filter((d) => d.page === args[1]) : diagrams
if (!selected.length) {
  console.error(`No diagrams registered for page: ${args[1]}`)
  process.exit(1)
}

if (!fs.existsSync(venvManim)) {
  console.error(`manim not found at ${venvManim}`)
  console.error('Create it with: uv venv .manim-venv --python 3.14 && uv pip install --python .manim-venv/bin/python manim')
  process.exit(1)
}

const missing = ['latex', 'dvisvgm'].filter((cmd) => spawnSync('which', [cmd]).status !== 0)
if (missing.length > 0) {
  console.error(`missing on PATH: ${missing.join(', ')}`)
  console.error('Install TeX Live with: brew install dvisvgm')
  process.exit(1)
}

// Render into an isolated directory; never remove a user's existing media.
const mediaDir = fs.mkdtempSync(path.join(os.tmpdir(), 'site-manim-'))
let ok = 0
let failed = 0
for (const { source, scene, output, resolution = '2400,1350' } of selected) {
  const result = spawnSync(
    venvManim,
    ['render', '-s', '--tex_template', path.join(manimDir, 'template.tex'), '--media_dir', mediaDir, '-r', resolution, '-q', 'm', path.join('docs', 'manim', source), scene],
    { cwd: root, stdio: 'pipe', encoding: 'utf8' },
  )
  if (result.status !== 0) {
    failed++
    console.error(`FAIL ${source}\n${result.stderr || result.stdout}`)
    continue
  }
  const imagesDir = path.join(mediaDir, 'images', path.basename(source, '.py'))
  const rendered = fs
    .readdirSync(imagesDir)
    .find((f) => f.startsWith(`${scene}_ManimCE_v`) && f.endsWith('.png'))
  if (!rendered) {
    failed++
    console.error(`FAIL ${source}: no rendered PNG found in ${imagesDir}`)
    continue
  }
  fs.copyFileSync(path.join(imagesDir, rendered), path.join(manimDir, output))
  ok++
  console.log(`ok   ${source} -> docs/manim/${output}`)
}

fs.rmSync(mediaDir, { recursive: true, force: true })

console.log(`\n${ok} diagram(s) rendered, ${failed} failed.`)
if (failed > 0) process.exitCode = 1
