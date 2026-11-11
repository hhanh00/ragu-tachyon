"""Check relative .md#anchor links in docs/ against VuePress-style heading slugs."""
import re, sys, pathlib, unicodedata

DOCS = pathlib.Path(__file__).resolve().parent.parent / 'docs'

def slug(text):
    # approximate @vuepress/shared slugify
    text = re.sub(r'\$[^$]*\$', lambda m: m.group(0), text)
    s = unicodedata.normalize('NFKD', text)
    s = re.sub(r'[̀-ͯ\u0000-\u001f]', '', s)
    s = re.sub(r'[\s~`!@#$%^&*()\-_+=[\]{}|\\;:"\'“”‘’<>,.?/]+', '-', s)
    s = re.sub(r'-{2,}', '-', s)
    s = re.sub(r'^-+|-+$', '', s)
    s = re.sub(r'^(\d)', r'_\1', s)
    return s.lower()

def anchors(path):
    out = set()
    in_code = False
    for line in path.read_text().splitlines():
        if line.startswith('```'):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r'^(#{1,6})\s+(.*?)\s*$', line)
        if m:
            h = re.sub(r'`', '', m.group(2))
            h = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', h)
            out.add(slug(h))
    return out

cache = {}
bad = []
files = list(DOCS.glob('*.md')) + list((DOCS / 'worked').glob('*.py'))
for f in files:
    text = f.read_text()
    for m in re.finditer(r'\]\(\.?/?([a-z0-9\-]+\.md)?#([^)\s]+)\)|\(\./([a-z0-9\-]+\.md)#([^)\s]+)\)', text):
        target = m.group(1) or m.group(3)
        anchor = m.group(2) or m.group(4)
        if target is None:
            target = f.name if f.suffix == '.md' else None
            if target is None:
                continue
        tp = DOCS / target
        if not tp.exists():
            bad.append((f.name, target, anchor, 'missing file'))
            continue
        if target not in cache:
            cache[target] = anchors(tp)
        if anchor not in cache[target]:
            line = text[:m.start()].count('\n') + 1
            bad.append((f'{f.name}:{line}', target, anchor, ''))
for b in bad:
    print(*b)
print(len(bad), 'bad links', file=sys.stderr)
