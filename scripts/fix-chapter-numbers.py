"""Fix bare-number link labels like [20](./pool-state.md) to the chapter's sidebar number."""
import re, sys, pathlib
DOCS = pathlib.Path(__file__).resolve().parent.parent / 'docs'
cfg = (DOCS / '.vuepress/config.js').read_text()
order = []
for s in re.findall(r"link: '/([a-z-]+)\.html'", cfg):
    if s not in order:
        order.append(s)
num = {s: i + 1 for i, s in enumerate(order[:25])}
skip = set(sys.argv[1:])
pat = re.compile(r'\[(\d{1,2})\]\(\./([a-z-]+)\.md(#[^)]*)?\)')
for p in sorted(DOCS.glob('*.md')):
    if p.stem in skip:
        continue
    s = p.read_text()
    changes = []
    def rep(m):
        n, slug = int(m.group(1)), m.group(2)
        if slug in num and num[slug] != n:
            changes.append((n, num[slug], slug))
            return f'[{num[slug]}](./{slug}.md{m.group(3) or ""})'
        return m.group(0)
    s2 = pat.sub(rep, s)
    if s2 != s:
        p.write_text(s2)
        print(p.name, changes)
