"""Worked examples for pcd-intro.md. Prints fragments as JSON.

This chapter uses no cryptography, so nothing here touches the toy curve. The
proof is treated as a black box, and the script models only the checks a step
performs. Importing this module (the Manim figure does) prints nothing.
"""
import json
import random
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
        f'Joining the entry with value {repeat} to itself produces a node that claims {repeat + repeat}, and nothing in that '
        f'header reveals the repeat. A tree with {N} leaves has {joins} joins, and a prover can choose any entry for each leaf. '
        f'Enumerating those choices gives {len(multisets)} multisets of entries, which reach {len(totals)} different root '
        f'totals from {min(totals)} to {max(totals)}. Only {TRUE_SUM} is the true sum, yet every one of these trees passes a join rule that '
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

    partial = tally(0, N - 1)
    assert partial in derived and partial[2] != TRUE_SUM
    frag['partial'] = (
        f'The header ${show(partial)}$ is also true and has a valid proof, because it is one of the derived headers. A verifier who wants the sum of the '
        f'whole list must still confirm that the range runs from 0 to {N}, and a verifier who accepted this header without looking would conclude that the total is {partial[2]}.'
    )

    # Distinguishing header types with a fee.
    fee = 2
    charged = (0, N, TRUE_SUM + fee)
    frag['charge'] = (
        f'Suppose a final step `Charge` adds a flat fee of {fee}. It consumes ${show(root[3])}$ and outputs ${show(charged)}$. If `Charge` accepted its own output, a prover could '
        f'apply it again to reach ${show((0, N, charged[2] + fee))}$, even though the fee is meant to apply once. The input and output contain three numbers of the same form, so the numbers cannot tell the '
        'two states apart. Giving the input and output different type labels, say `Tally` and `Charged`, solves this, because `Charge` accepts only a `Tally`.'
    )

    # Cost of keeping one proof per node versus one proof overall.
    rows = ['| Entries $n$ | Nodes $2n - 1$ | Proofs checked if every node\'s proof is kept | Proofs checked with PCD | Layers in a balanced tree |', '| --- | --- | --- | --- | --- |']
    for k in (3, 10, 20):
        n = 2 ** k
        rows.append(f'| {n:,} | {2 * n - 1:,} | {2 * n - 1:,} | 1 | {k + 1} |')
    frag['cost'] = '\n'.join(rows)

    # The toy aggregate. Labels stand in for field elements and commitments.
    rng = random.Random(7)
    plan = [('A', 0, 15), ('X', 1, 12), ('Y', 2, 14), ('Z', 1, 15)]
    total_actions = sum(p[1] for p in plan)
    total_tachygrams = 2 * total_actions + len(plan)
    labels = rng.sample(range(100, 1000), total_tachygrams)
    bundles = {}
    action_no = 1
    for name, n_actions, anchor in plan:
        count = 2 * n_actions + 1
        tgs, labels = sorted(labels[:count]), labels[count:]
        acts = [f'a_{{{action_no + i}}}' for i in range(n_actions)]
        action_no += n_actions
        bundles[name] = {'actions': acts + [f'f_{{{name}}}'], 'tachygrams': tgs, 'anchor': anchor, 'n': n_actions}
    assert not labels

    def cell(items):
        return '$\\{' + ',\\ '.join(str(i) for i in items) + '\\}$' if items else 'none'

    rows = ['| Bundle | Actions | Action set, with fee digest | Tachygrams | Anchor |', '| --- | --- | --- | --- | --- |']
    for name, b in bundles.items():
        assert len(b['tachygrams']) == 2 * b['n'] + 1
        rows.append(f"| {name} | {b['n']} | {cell(b['actions'])} | {cell(b['tachygrams'])} | $\\alpha_{{{b['anchor']}}}$ |")
    frag['stamp-bundles'] = '\n'.join(rows)

    span = {'start': 12, 'end': 15, 'members': {13, 14, 15}}

    def lift(stamp):
        assert stamp['anchor'] == span['start'] or stamp['anchor'] in span['members']
        return {**stamp, 'anchor': span['end']}

    def can_merge(a, c):
        return a['anchor'] == c['anchor']

    def merge(a, c):
        assert can_merge(a, c)
        assert not set(a['tachygrams']) & set(c['tachygrams'])
        return {'actions': a['actions'] + c['actions'], 'tachygrams': sorted(a['tachygrams'] + c['tachygrams']), 'anchor': a['anchor']}

    assert not can_merge(bundles['A'], bundles['X'])
    x2, y2 = lift(bundles['X']), lift(bundles['Y'])
    m1 = merge(bundles['A'], x2)
    m2 = merge(m1, y2)
    m3 = merge(m2, bundles['Z'])
    assert len(m3['tachygrams']) == total_tachygrams == 2 * total_actions + len(plan)
    assert len(m3['actions']) == total_actions + len(plan)

    def row(step, left, right, check, out):
        return f"| {step} | {left} | {right} | {check} | $\\alpha_{{{out['anchor']}}}$ | {len(out['actions'])} | {len(out['tachygrams'])} |"

    rows = ['| Step | Left | Right | What the step checks | Output anchor | Action digests | Tachygrams |', '| --- | --- | --- | --- | --- | --- | --- |',
            row('`StampLift`', 'X', 'span', '$\\alpha_{12}$ is the span\'s start', x2),
            row('`StampLift`', 'Y', 'span', '$\\alpha_{14}$ is a member', y2),
            row('`StampMerge`', 'A', 'lifted X', 'anchors match', m1),
            row('`StampMerge`', 'previous', 'lifted Y', 'anchors match', m2),
            row('`StampMerge`', 'previous', 'Z', 'anchors match', m3)]
    frag['stamp-run'] = '\n'.join(rows) + (
        f'\n\nThe span runs from $\\alpha_{{{span["start"]}}}$ to $\\alpha_{{{span["end"]}}}$, with members '
        '$\\{' + ',\\ '.join(f'\\alpha_{{{m}}}' for m in sorted(span['members'])) + '\\}$. '
        f'Merging A with the unlifted X would fail, because ${bundles["A"]["anchor"]} \\neq {bundles["X"]["anchor"]}$.'
    )

    # What the block holds and what a validator rebuilds.
    published_actions = [d for name in bundles for d in bundles[name]['actions']]
    assert sorted(published_actions) == sorted(m3['actions'])
    omit_z = [d for d in published_actions if d not in bundles['Z']['actions']]
    assert sorted(omit_z) != sorted(m3['actions'])
    proofs_before, proofs_after = len(bundles), 1
    frag['stamp-block'] = '\n'.join([
        '| Transaction | Name | Keeps its action and fee descriptors | Carries tachygrams and a proof |',
        '| --- | --- | --- | --- |',
        '| A | aggregate | yes | yes, the merged stamp |',
        '| X | adjunct | yes | no, it points to A |',
        '| Y | adjunct | yes | no, it points to A |',
        '| Z | adjunct | yes | no, it points to A |',
        '',
        f'The block carries {proofs_after} proof where the four separate transactions carried {proofs_before}. It still carries all {total_tachygrams} tachygrams and all '
        f'{len(published_actions)} action and fee digests, because the verifier needs them. A validator collects the digests from the four transactions, takes the tachygrams and anchor from A\'s stamp, '
        f'and checks the one proof against the header those values produce. If a miner leaves Z out of the block, the rebuilt action set has {len(omit_z)} digests instead of {len(m3["actions"])}. '
        'The header no longer matches the one the proof was made for, so the proof fails.',
    ])

    # Removing a contributor.
    q_tgs = sorted(set(m3['tachygrams']) - set(x2['tachygrams']))
    q_actions = [d for d in m3['actions'] if d not in x2['actions']]
    assert sorted(q_tgs) == sorted(bundles['A']['tachygrams'] + bundles['Y']['tachygrams'] + bundles['Z']['tachygrams'])
    frag['stamp-unmerge'] = (
        f'Suppose a block includes X on its own while the aggregator is still working. The merged stamp holds {len(m3["tachygrams"])} tachygrams, and publishing it now would repeat those of X. '
        f'`StampUnmerge` takes the merged stamp and a stamp of X lifted to the same anchor, and it produces a stamp with {len(q_tgs)} tachygrams and {len(q_actions)} action digests, which covers A, Y and Z. Its header states less than its input did, which '
        'is permitted, because a step only has to establish the relation it declares between its inputs and its output.'
    )

    return frag


if __name__ == '__main__':
    print(json.dumps(fragments()))
