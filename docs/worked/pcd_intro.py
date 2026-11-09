"""Worked examples for pcd-intro.md. Prints fragments as JSON.

This chapter uses no cryptography, so nothing here touches the toy curve. The
proof is treated as a black box, and the script models only the checks a step
performs. Importing this module (the Manim figure does) prints nothing.
"""
import json
from itertools import combinations_with_replacement

L = [4, 11, 3, 7, 6, 2, 9, 5]
N = len(L)
TRUE_SUM = sum(L)


def tally(lo, hi):
    return (lo, hi, sum(L[lo:hi]))


def show(h):
    return f'({h[0]}, {h[1]}, {h[2]})'


def check_entry(pos, value):
    return L[pos] == value


def check_join(left, right, claimed):
    return left[1] == right[0] and left[2] + right[2] == claimed


def join(left, right):
    claimed = left[2] + right[2]
    assert check_join(left, right, claimed)
    return (left[0], right[1], claimed)


def balanced_nodes():
    """The nodes of the balanced tree, leaves first, as (name, step, inputs, header)."""
    nodes = []
    layer = []
    for i, v in enumerate(L):
        assert check_entry(i, v)
        name = f'E{i}'
        h = (i, i + 1, v)
        nodes.append((name, 'Entry', None, h))
        layer.append((name, h))
    count = 0
    while len(layer) > 1:
        next_layer = []
        for k in range(0, len(layer), 2):
            (ln, lh), (rn, rh) = layer[k], layer[k + 1]
            name = f'J{count}'
            count += 1
            h = join(lh, rh)
            nodes.append((name, 'Join', (ln, lh, rn, rh), h))
            next_layer.append((name, h))
        layer = next_layer
    return nodes


def all_roots(lo, hi):
    """The root header of every binary tree over positions lo..hi."""
    if hi - lo == 1:
        return [(lo, hi, L[lo])]
    roots = []
    for mid in range(lo + 1, hi):
        for left in all_roots(lo, mid):
            for right in all_roots(mid, hi):
                roots.append(join(left, right))
    return roots


def partial_header():
    return tally(0, N - 1)


def fragments():
    frag = {}
    assert len(set(L + [h[2] for *_, h in balanced_nodes() if h[1] - h[0] > 1])) == 2 * N - 1

    frag['values'] = '\n'.join([
        '| Position $i$ | ' + ' | '.join(str(i) for i in range(N)) + ' |',
        '| --- | ' + ' | '.join('---' for _ in L) + ' |',
        '| Value $L_i$ | ' + ' | '.join(str(v) for v in L) + ' |',
        '',
        f'The list has {N} entries, and its sum is {TRUE_SUM}.',
    ])

    # A header holding only the sum: every multiset of leaves is reachable.
    joins = N - 1
    multisets = list(combinations_with_replacement(L, N))
    totals = {sum(m) for m in multisets}
    assert len(multisets) == 6435 and TRUE_SUM in totals and len(totals) > 1
    repeat = L[1]
    frag['sum-only'] = (
        f'Combining the entry with value {repeat} to itself produces a node that claims {repeat + repeat}, and nothing in that '
        f'header reveals the repeat. A tree with {N} leaves combines subtotals at {joins} nodes, and a prover can choose any entry for each leaf. '
        f'Enumerating those choices gives {len(multisets)} multisets of entries, which reach {len(totals)} different root '
        f'totals from {min(totals)} to {max(totals)}. Only {TRUE_SUM} is the true sum, yet every one of these trees passes a rule that '
        'checks only addition.'
    )

    # With ranges, enumerate everything the two rules can ever derive.
    derived = {(i, i + 1, v) for i, v in enumerate(L)}
    while True:
        new = {join(a, b) for a in derived for b in derived if a[1] == b[0]} - derived
        if not new:
            break
        derived |= new
    expected_count = N * (N + 1) // 2
    assert len(derived) == expected_count
    assert all(s == sum(L[lo:hi]) for lo, hi, s in derived)
    pairs = len(derived) ** 2
    accepted = sum(1 for a in derived for b in derived if a[1] == b[0])
    assert accepted == 84
    full = [h for h in derived if h[0] == 0 and h[1] == N]
    assert full == [(0, N, TRUE_SUM)]
    assert all((i, i + 1, v + 1) not in derived for i, v in enumerate(L))
    frag['closure'] = (
        f'Start from the {N} entry headers and apply the join rule until nothing new appears. The process produces {len(derived)} headers, '
        f'one for each range of positions, and each one states the correct sum for its range. Of the {pairs} ordered pairs of those '
        f'headers, the rule accepts {accepted}, namely the pairs whose ranges meet. Exactly one derived header covers the whole list, '
        f'and it is ${show(full[0])}$.'
    )

    # The balanced tree.
    nodes = balanced_nodes()
    rows = ['| Node | Step | Inputs | What the step checks | Header $(\\ell, h, s)$ |', '| --- | --- | --- | --- | --- |']
    for name, step, inputs, h in nodes:
        if inputs is None:
            rows.append(f'| {name} | Entry | none | $L_{{{h[0]}}} = {h[2]}$ | ${show(h)}$ |')
        else:
            ln, lh, rn, rh = inputs
            rows.append(f'| {name} | Join | {ln}, {rn} | ${lh[1]} = {rh[0]}$ and ${lh[2]} + {rh[2]} = {h[2]}$ | ${show(h)}$ |')
    frag['tree'] = '\n'.join(rows)
    root = nodes[-1]
    assert root[3] == (0, N, TRUE_SUM)
    (left_name, left_h, right_name, right_h) = root[2]

    # Unwinding the root claim layer by layer.
    by_name = {n[0]: n for n in nodes}
    assert len(nodes) == 2 * N - 1
    a, b = by_name[left_name], by_name[right_name]
    al, ar = a[2][1], a[2][3]
    assert al == (0, 2, L[0] + L[1]) and ar == (2, 4, L[2] + L[3])
    frag['unwind'] = (
        f'The root ${show(root[3])}$ says that the `Join` rule accepted ${show(left_h)}$ and ${show(right_h)}$, and that those two headers have valid proofs. '
        f'Their own proofs in turn say that ${show(al)}$ and ${show(ar)}$ were joined into ${show(left_h)}$, and likewise on the right. '
        f'Following every branch to the bottom reaches {N} `Entry` checks, each comparing one value with the list. '
        f'The root\'s proof therefore stands for all {len(nodes)} checks in the table, of which the verifier runs none.'
    )

    # Every tree shape and a chain.
    roots = all_roots(0, N)
    assert len(roots) == 429 and set(roots) == {(0, N, TRUE_SUM)}
    frag['shapes'] = (
        f'The tree above is balanced, but the rule does not require that. A list of {N} entries has {len(roots)} binary tree shapes that '
        f'keep the entries in order. Running all of them gives the same root header ${show(root[3])}$ every time.'
    )

    chain = [(0, 1, L[0])]
    rows = ['| After appending position | Header |', '| --- | --- |', f'| 0 | ${show(chain[0])}$ |']
    for i in range(1, N):
        chain.append(join(chain[-1], (i, i + 1, L[i])))
        rows.append(f'| {i} | ${show(chain[-1])}$ |')
    assert chain[-1] == root[3]
    frag['chain'] = '\n'.join(rows)

    shared, rest_full, rest_short = tally(0, N // 2), tally(N // 2, N), tally(N // 2, N - 1)
    assert join(shared, rest_full) == root[3] and join(shared, rest_short) == partial_header()
    frag['dag'] = (
        f'For example, Alice\'s header ${show(shared)}$ can be joined with ${show(rest_full)}$ to give ${show(root[3])}$, and the same header, with the same proof, '
        f'can also be joined with ${show(rest_short)}$ to give ${show(join(shared, rest_short))}$. Nobody has to rebuild ${show(shared)}$ for the second use.'
    )

    alice, bob = tally(0, N // 2), tally(N // 2, N)
    assert join(alice, bob) == root[3] and alice == left_h and bob == right_h
    frag['parties'] = (
        f'Suppose Alice holds positions 0 to {N // 2 - 1} and Bob holds the rest. Alice runs her subtree and hands over the header ${show(alice)}$ with its proof. '
        f'Bob does the same with ${show(bob)}$. Carol, who holds neither half of the list, checks only that ${alice[1]} = {bob[0]}$ and ${alice[2]} + {bob[2]} = {TRUE_SUM}$ '
        f'before producing ${show(root[3])}$.'
    )

    # Attempted cheats. Each row must be rejected by the rule it names.
    false_entry = L[2] + 1
    assert not check_entry(2, false_entry)
    wrong = (tally(0, 1), tally(1, 2), L[0] + L[1] + 1)
    assert not check_join(*wrong)
    repeat_pair = (tally(1, 2), tally(1, 2))
    overlap = (tally(0, 3), tally(2, 4))
    gap = (tally(0, 2), tally(3, 4))
    for pair, why in ((repeat_pair, 'repeat'), (overlap, 'overlap'), (gap, 'gap')):
        assert not check_join(pair[0], pair[1], pair[0][2] + pair[1][2]), why
    frag['cheats'] = '\n'.join([
        '| Attempt | Inputs and claim | Check that fails |',
        '| --- | --- | --- |',
        f'| False entry | Claims $L_2 = {false_entry}$ | `Entry`: $L_2$ is {L[2]} |',
        f'| Wrong addition | ${show(wrong[0])}$, ${show(wrong[1])}$, claims $s = {wrong[2]}$ | `Join`: ${wrong[0][2]} + {wrong[1][2]} \\neq {wrong[2]}$ |',
        f'| Repeated entry | ${show(repeat_pair[0])}$ twice | `Join`: ${repeat_pair[0][1]} \\neq {repeat_pair[1][0]}$ |',
        f'| Overlapping ranges | ${show(overlap[0])}$, ${show(overlap[1])}$ | `Join`: ${overlap[0][1]} \\neq {overlap[1][0]}$ |',
        f'| Skipped entry | ${show(gap[0])}$, ${show(gap[1])}$ | `Join`: ${gap[0][1]} \\neq {gap[1][0]}$ |',
    ])

    partial = partial_header()
    assert partial in derived and partial[2] != TRUE_SUM
    frag['partial'] = (
        f'The header ${show(partial)}$ is also true and has a valid proof, because it is one of the derived headers. A verifier who wants the sum of the '
        f'whole list must still confirm that the range runs from 0 to {N}, and a verifier who accepted this header without looking would conclude that the total is {partial[2]}.'
    )

    # Cost of keeping one proof per node versus one proof overall.
    sizes = (3, 10, 20)
    rows = ['| Entries $n$ | Proofs checked if every node keeps its proof, $2n - 1$ | Proofs checked with PCD |', '| --- | --- | --- |']
    for k in sizes:
        n = 2 ** k
        rows.append(f'| {n:,} | {2 * n - 1:,} | 1 |')
    frag['cost'] = '\n'.join(rows)
    layers = [k + 1 for k in sizes]
    frag['layers'] = (
        f'A tree also saves time. A balanced tree over $n$ entries has $\\log_2 n + 1$ layers, which is {layers[0]}, {layers[1]} and {layers[2]} for the three sizes above. '
        'With enough workers, all the nodes of one layer can run at the same time, so the number of rounds grows with the logarithm of the number of entries.'
    )

    # The toy aggregate: three wallet bundles at one anchor. Labels stand in for
    # field elements and hashes, and each tachygram is named after its bundle so
    # that set operations read at a glance.
    plan = [('X', 1), ('Y', 2), ('Z', 1)]
    total_actions = sum(p[1] for p in plan)
    total_tachygrams = 2 * total_actions + len(plan)
    bundles = {}
    action_no = 1
    for name, n_actions in plan:
        count = 2 * n_actions + 1
        tgs = [f'{name.lower()}_{{{i + 1}}}' for i in range(count)]
        acts = [f'a_{{{action_no + i}}}' for i in range(n_actions)]
        action_no += n_actions
        bundles[name] = {'actions': acts + [f'f_{{{name}}}'], 'tachygrams': tgs, 'n': n_actions}

    def lit(items):
        return '\\{' + ',\\ '.join(str(i) for i in items) + '\\}'

    def html(label):
        # a_{1} -> a<sub>1</sub>, for Mermaid labels.
        base, sub = label.split('_')
        return f'{base}<sub>{sub.strip("{}")}</sub>'

    # Where the header of X comes from.
    x = bundles['X']
    frag['stamp-anatomy'] = '\n'.join([
        '```mermaid',
        'graph LR',
        '    subgraph BX["Bundle X"]',
        '        subgraph Body["body"]',
        '            AD["action descriptor"]',
        '            FD["fee descriptor"]',
        '        end',
        '        subgraph St["stamp"]',
        f'            TG["tachygrams {", ".join(html(t) for t in x["tachygrams"])}"]',
        '            AN["anchor α"]',
        '            PR["proof"]',
        '        end',
        '    end',
        '    subgraph H["header the proof is about, written as the sets its commitments stand for"]',
        f'        AS["action set {{{", ".join(html(a) for a in x["actions"])}}}"]',
        f'        TS["tachygram set {{{", ".join(html(t) for t in x["tachygrams"])}}}"]',
        '        HA["anchor α"]',
        '    end',
        f'    AD -->|"hash: {html(x["actions"][0])}"| AS',
        f'    FD -->|"hash: {html(x["actions"][-1])}"| AS',
        '    TG --> TS',
        '    AN --> HA',
        '    PR -.->|"proves"| H',
        '```',
    ])

    rows = ['| Bundle | Action set, with fee digest | Tachygrams | Anchor |', '| --- | --- | --- | --- |']
    for name, b in bundles.items():
        assert len(b['tachygrams']) == 2 * b['n'] + 1
        assert len(b['actions']) == b['n'] + 1
        rows.append(f"| {name} | ${lit(b['actions'])}$ | ${lit(b['tachygrams'])}$ | $\\alpha$ |")
    frag['stamp-bundles'] = '\n'.join(rows)

    def merge(a, c):
        assert not set(a['tachygrams']) & set(c['tachygrams'])
        return {'actions': a['actions'] + c['actions'], 'tachygrams': a['tachygrams'] + c['tachygrams']}

    m1 = merge(bundles['X'], bundles['Y'])
    m2 = merge(m1, bundles['Z'])
    assert len(m2['tachygrams']) == total_tachygrams == 2 * total_actions + len(plan)
    assert len(m2['actions']) == total_actions + len(plan)

    xb, yb = bundles['X'], bundles['Y']
    frag['stamp-first-merge'] = (
        'Take the first merge, of X with Y. Both stamps have the anchor $\\alpha$, so the anchor check passes and the output keeps it. '
        'The action sets combine as\n\n'
        f'$${lit(xb["actions"])} \\cup {lit(yb["actions"])} = {lit(m1["actions"])},$$\n\n'
        'and the tachygram sets combine as\n\n'
        f'$${lit(xb["tachygrams"])} \\cup {lit(yb["tachygrams"])} = {lit(m1["tachygrams"])}.$$\n\n'
        f'The output covers {len(m1["actions"])} digests and {len(m1["tachygrams"])} tachygrams.'
    )

    def row(left, right, out):
        return f"| `StampMerge` | {left} | {right} | anchors match | $\\alpha$ | {len(out['actions'])} | {len(out['tachygrams'])} |"

    frag['stamp-run'] = '\n'.join([
        '| Step | Left | Right | What the step checks | Output anchor | Action digests | Tachygrams |',
        '| --- | --- | --- | --- | --- | --- | --- |',
        row('X', 'Y', m1),
        row('previous', 'Z', m2),
    ])

    # The structure of the final block: one aggregate and its adjuncts.
    def tg_range(name):
        tgs = [html(t) for t in bundles[name]['tachygrams']]
        return f'{tgs[0]}…{tgs[-1]}'

    def body(name):
        b = bundles[name]
        acts = ', '.join(html(d) for d in b['actions'][:-1])
        n = len(b['actions']) - 1
        first = f'{"action" if n == 1 else "actions"} {acts} + {"signature" if n == 1 else "signatures"}'
        return f'{first}<br/>fee descriptor {html(b["actions"][-1])} + binding signature'

    merged_tgs = ', '.join(tg_range(n) for n in bundles)
    lines = ['```mermaid', 'graph BT',
             f'    X["<b>X: aggregate</b><br/>body: {body("X")}<br/>merged stamp: tachygrams {merged_tgs},<br/>anchor α, one proof covering X, Y, Z"]']
    for name in ('Y', 'Z'):
        lines.append(f'    {name}["<b>{name}: adjunct</b><br/>body: {body(name)}<br/>no stamp"]')
    for name in ('Y', 'Z'):
        lines.append(f'    {name} -.->|"points to"| X')
    lines.append('```')
    frag['stamp-block-structure'] = '\n'.join(lines)

    # What the block holds and what a validator rebuilds.
    published_actions = [d for name in bundles for d in bundles[name]['actions']]
    assert sorted(published_actions) == sorted(m2['actions'])
    omit_z = [d for d in published_actions if d not in bundles['Z']['actions']]
    assert sorted(omit_z) != sorted(m2['actions'])
    extra = [f'a_{{{action_no}}}', 'f_{W}']
    with_w = published_actions + extra
    assert sorted(with_w) != sorted(m2['actions'])
    proofs_before = len(bundles)
    frag['stamp-block'] = (
        f'The block carries 1 proof where the {proofs_before} separate transactions carried {proofs_before}. It still carries all {total_tachygrams} tachygrams, inside the stamp on X, '
        'and every action and fee descriptor, inside the bodies.'
    )
    frag['stamp-rebuild'] = (
        'The validator hashes the descriptors in each body. It gets $' + lit(bundles['X']['actions']) + '$ from X, $'
        + lit(bundles['Y']['actions']) + '$ from Y and $' + lit(bundles['Z']['actions']) + '$ from Z, and their union is\n\n'
        f'$${lit(published_actions)}.$$\n\n'
        f'This set has {len(published_actions)} members and equals the action set in the last row of the run, so the proof verifies. '
        f'If a miner leaves Z out of the block, the rebuilt set has {len(omit_z)} members instead of {len(m2["actions"])}. '
        f'If a miner instead adds a one-action bundle W that the stamp never covered and points it at X, the rebuilt set gains ${extra[0]}$ and ${extra[1]}$ and has {len(with_w)} members. '
        'In both cases the rebuilt header differs from the one the proof was made for, so the proof fails.'
    )

    return frag


if __name__ == '__main__':
    print(json.dumps(fragments()))
