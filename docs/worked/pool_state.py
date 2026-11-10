"""Worked example for pool-state.md. Prints fragments as JSON.

The real chain hashes with Poseidon over the Pallas base field. Here SHA-256
reduced modulo 43 stands in for it, so every hash value below is illustrative
and has no relation to real Tachyon values.
"""
import hashlib
import itertools
import json

from toy_curve import G, H, P, Q, U, add, curve_points, msm, mul, show

frag = {}


# Polynomial helpers: coefficient lists, lowest degree first, over F_43.
def pmul(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] = (out[i + j] + x * y) % Q
    return out


def roots_poly(roots):
    out = [1]
    for r in roots:
        out = pmul(out, [-r % Q, 1])
    return out


def ev(p, x):
    return sum(c * pow(x, i, Q) for i, c in enumerate(p)) % Q


def pdiv(num, den):
    """Long division by a monic divisor. Returns (quotient, remainder)."""
    assert den[-1] == 1
    rem = list(num)
    quo = [0] * (len(num) - len(den) + 1)
    for k in range(len(quo) - 1, -1, -1):
        c = rem[k + len(den) - 1]
        quo[k] = c
        for j, d in enumerate(den):
            rem[k + j] = (rem[k + j] - c * d) % Q
    return quo, rem[:len(den) - 1]


def pshow(p):
    terms = []
    for i in range(len(p) - 1, -1, -1):
        c = p[i] % Q
        if c == 0:
            continue
        x = '' if i == 0 else ('X' if i == 1 else f'X^{{{i}}}')
        coef = str(c) if (c != 1 or i == 0) else ''
        terms.append(coef + x)
    return ' + '.join(terms)


# Seven generators are enough for the union of two stamps. The first four are the
# shared public parameters; the rest come from the curve's point list.
_used = {a[0] for a in G} | {H[0], U[0]}
EXTRA = [a for a in curve_points() if a[0] not in _used and a[1] < 16]
GENS = list(G)
for a in EXTRA:
    if len(GENS) < 7 and a[0] not in {b[0] for b in GENS}:
        GENS.append(a)
assert len(GENS) == 7
assert len({a[0] for a in GENS}) == len(GENS)


def commit(p):
    assert len(p) <= len(GENS)
    return msm(p, GENS[:len(p)])


# The stand-in hash.
ST, EP = 'Tachyon-AnchorSt', 'Tachyon-AnchorEp'


def toy_hash(domain, *inputs):
    text = domain + '|' + ','.join(str(i) for i in inputs)
    return int.from_bytes(hashlib.sha256(text.encode()).digest(), 'big') % Q


def encode(point):
    """x in the low five bits and the parity of y in the sixth."""
    assert point is not None
    return point[0] | ((point[1] & 1) << 5)


def limbs(point):
    enc = encode(point)
    return enc & 7, enc >> 3


def h_st(anchor, epoch, point):
    lo, hi = limbs(point)
    return toy_hash(ST, anchor, epoch, lo, hi)


def h_ep(anchor, epoch):
    return toy_hash(EP, anchor, epoch)


# ---------------------------------------------------------------- stamps
STAMPS = {
    'A': [22, 24, 40],
    'B': [20, 23, 41],
    'C': [13, 19, 21],
    'D': [4, 18, 36],
    'E': [9, 12, 25],
    'F': [28, 29, 42],
}
values = [t for s in STAMPS.values() for t in s]
assert len(set(values)) == len(values) and 0 not in values and all(t < Q for t in values)
POLY = {k: roots_poly(v) for k, v in STAMPS.items()}
COMMIT = {k: commit(p) for k, p in POLY.items()}
assert len({COMMIT[k] for k in COMMIT}) == len(COMMIT)
assert all(c is not None and c not in GENS for c in COMMIT.values())

# ---------------------------------------------------------------- the set polynomial
ta, tb, tc = STAMPS['A']
f1 = roots_poly([ta])
f2 = roots_poly([ta, tb])
f3 = POLY['A']
assert f3 == pmul(f2, roots_poly([tc]))
frag['set-poly'] = '\n'.join([
    f'Take a stamp A with the three tachygrams ${ta}$, ${tb}$, ${tc}$. Multiplying the factors one at a time, with coefficients reduced modulo {Q}, gives',
    '',
    f'$$\\begin{{aligned}}',
    f'(X - {ta})(X - {tb}) &= X^2 - {ta + tb}X + {ta * tb} = {pshow(f2)},\\\\',
    f'({pshow(f2)})(X - {tc}) &= X^3 + ({f2[1]} - {tc})X^2 + ({f2[0]} - {f2[1]} \\cdot {tc})X - {f2[0]} \\cdot {tc}\\\\',
    f'&= X^3 + {f2[1] - tc} \\cdot X^2 {"-" if f2[0] - f2[1] * tc < 0 else "+"} {abs(f2[0] - f2[1] * tc)}X - {f2[0] * tc} = {pshow(f3)}.',
    f'\\end{{aligned}}$$',
])
for perm in itertools.permutations(STAMPS['A']):
    assert roots_poly(list(perm)) == f3

nonmember = STAMPS['B'][0]
frag['set-eval'] = '\n'.join([
    '| Value $x$ | In the set | $\\mathsf{tachygram\\_acc}(x)$ |', '| --- | --- | --- |',
] + [f'| {x} | {"yes" if x in STAMPS["A"] else "no"} | {ev(f3, x)} |'
     for x in [ta, tb, tc, nonmember, 6]])
zeros = [x for x in range(Q) if ev(f3, x) == 0]
assert zeros == sorted(STAMPS['A'])
assert ev(f3, nonmember) != 0 and ev(f3, 6) != 0
frag['set-count'] = (
    f'Running through all {Q} field elements, the polynomial is zero at exactly {len(zeros)} of them, '
    f'which are the three tachygrams. All {len(list(itertools.permutations(STAMPS["A"])))} orderings of the three factors expand to the same coefficients, '
    'so the polynomial records the set and no order.')
dup = roots_poly([ta, ta, tb])
assert ev(dup, ta) == 0 and dup != f3
frag['set-multi'] = (
    f'For example, the multiset $\\{{{ta}, {ta}, {tb}\\}}$ gives ${pshow(dup)}$. It has a double root at ${ta}$, '
    f'and evaluating it there still gives ${ev(dup, ta)}$, the same answer as a single occurrence.')

# ---------------------------------------------------------------- commitment
rows = ['| Coefficient of | Value | Generator | Term | Running sum |', '| --- | --- | --- | --- | --- |']
run = None
names = ['X^0', 'X^1', 'X^2', 'X^3']
for i, c in enumerate(f3):
    term = mul(c, G[i])
    run = add(run, term)
    rows.append(f'| ${names[i]}$ | {c} | $G_{i}$ | ${show(term)}$ | ${show(run)}$ |')
assert run == COMMIT['A'] and f3[3] == 1
frag['commit'] = '\n'.join(rows + ['', f'The commitment is $C_A = {show(COMMIT["A"])}$. Coefficients live in $\\F_{{{Q}}}$, like the tachygrams, and the coordinates of $C_A$ live in $\\F_{{{P}}}$.'])
assert commit([1]) == G[0]
frag['empty'] = (
    f'On the toy curve, the empty set has the constant polynomial $1$, so its commitment is $1 \\cdot G_0 = {show(G[0])}$. '
    f'That point is a valid curve point, and it differs from $\\mathcal{{O}}$, so the code needs a separate check for it.')

# ---------------------------------------------------------------- union and difference
fa, fb = POLY['A'], POLY['B']
pab = pmul(fa, fb)
assert pab == roots_poly(STAMPS['A'] + STAMPS['B'])
cab = commit(pab)
r = 11
assert all(ev(pab, x) == ev(fa, x) * ev(fb, x) % Q for x in range(Q))
frag['union'] = '\n'.join([
    f'Stamp B has the tachygrams ${STAMPS["B"][0]}$, ${STAMPS["B"][1]}$, ${STAMPS["B"][2]}$, so $f_B(X) = {pshow(fb)}$. Writing $f_A$ for the polynomial of stamp A above, the union is',
    '',
    f'$$p(X) = f_A(X)\\,f_B(X) = {pshow(pab)}.$$',
    '',
    f'A product of degree 6 has 7 coefficients, which needs more than our four generators, so this example adds three more curve points, $G_4 = {show(GENS[4])}$, $G_5 = {show(GENS[5])}$ and $G_6 = {show(GENS[6])}$. The commitment to the union is $C_{{AB}} = {show(cab)}$.',
    '',
    f'At the challenge $r = {r}$, the check reads $p({r}) = {ev(pab, r)}$ against $f_A({r}) \\cdot f_B({r}) = {ev(fa, r)} \\cdot {ev(fb, r)} = {ev(fa, r) * ev(fb, r) % Q}$, and the two sides agree.',
])
assert add(COMMIT['A'], COMMIT['B']) != cab

# A prover swaps a genuine root for a value of its choosing.
fake_root = 31
assert fake_root not in values
pfake = roots_poly([t for t in STAMPS['A'] if t != tc] + [fake_root] + STAMPS['B'])
assert commit(pfake) != cab
passing = [x for x in range(Q) if ev(pfake, x) == ev(fa, x) * ev(fb, x) % Q]
assert len(passing) <= 5 and r not in passing and ev(pfake, tc) != 0 and ev(pfake, fake_root) == 0
# Both products are monic of degree 6 and share every factor except one.
kept = [t for t in STAMPS['A'] if t != tc]
diff = [(x - y) % Q for x, y in zip(pfake, pab)]
shared = pmul(roots_poly(kept), fb)
lead = (tc - fake_root) % Q
assert diff[-1] == 0 and diff == pmul(shared, [lead]) + [0]
assert sorted(passing) == sorted(kept + STAMPS['B'])
frag['union-cheat'] = '\n'.join([
    f'Suppose a prover claims a union $p\'$ with the root ${tc}$ replaced by ${fake_root}$. Then $p\'({tc}) = {ev(pfake, tc)}$, '
    f'so ${tc}$ would look absent from the merged set, and $p\'({fake_root}) = 0$, so ${fake_root}$ would look present. '
    f'Trying every challenge in $\\F_{{{Q}}}$, the false product passes at exactly {len(passing)} of the {Q} values, namely {", ".join(str(x) for x in passing)}.',
    '',
    f'The bound explains this count. Both $p\'$ and $f_A f_B$ are monic of degree 6, so their leading terms cancel and the difference has degree at most 5. '
    f'Here the two products share every factor except one, so the difference factors as',
    '',
    f'$$p\'(X) - f_A(X)f_B(X) = (X - {kept[0]})(X - {kept[1]})\\,f_B(X)\\,\\big((X - {fake_root}) - (X - {tc})\\big) = {lead}\\,(X - {kept[0]})(X - {kept[1]})\\,f_B(X).$$',
    '',
    f'Its roots are the five values that the two products share, and those are exactly the passing challenges, so this example meets the bound of 5. '
    f'The chance {len(passing)}/{Q} is large here only because the field is tiny. On a field of about $2^{{254}}$ elements, the same bound is negligible.',
])

q_ok, rem_ok = pdiv(pab, fb)
assert q_ok == fa and all(c == 0 for c in rem_ok)
absent = STAMPS['C'][0]
q_bad, rem_bad = pdiv(pab, [-absent % Q, 1])
assert rem_bad == [ev(pab, absent)] and rem_bad[0] != 0
frag['quotient'] = (
    f'Dividing $p$ by $f_B$ returns $f_A$ with remainder zero, which removes stamp B from the union. '
    f'Dividing $p$ by $X - {absent}$ leaves the nonzero remainder ${rem_bad[0]}$, because ${absent}$ is not in the set.')

e0 = pmul(pmul(POLY['A'], POLY['B']), POLY['C'])
member0, absent0 = STAMPS['B'][2], STAMPS['D'][0]
assert len(e0) == 10 and ev(e0, member0) == 0 and ev(e0, absent0) != 0
frag['epoch-product'] = (
    f'Section 7 builds a chain whose epoch 0 holds stamps A, B and C, where stamp C has the tachygrams ${STAMPS["C"][0]}$, ${STAMPS["C"][1]}$ and ${STAMPS["C"][2]}$. '
    f'Their product $e_0(X)$ has degree {len(e0) - 1}. It gives $e_0({member0}) = {ev(e0, member0)}$ for a value published in stamp B, and $e_0({absent0}) = {ev(e0, absent0)}$ for a value that does not appear in the epoch.')

# ---------------------------------------------------------------- recomputing the commitment
list_good = STAMPS['A']
c_tampered = commit(roots_poly([ta, tb, fake_root]))
assert c_tampered != COMMIT['A']
y = 1
for t in list_good:
    y = y * (r - t) % Q
assert y == ev(f3, r)
ftamp = roots_poly([ta, tb, fake_root])
tamper_pass = [x for x in range(Q) if ev(ftamp, x) == ev(f3, x)]
assert len(tamper_pass) <= 3 and r not in tamper_pass
frag['recompute'] = '\n'.join([
    f'Suppose stamp A publishes the list ${ta}$, ${tb}$, ${tc}$ but carries a commitment to the polynomial with roots ${ta}$, ${tb}$, ${fake_root}$. That commitment is ${show(c_tampered)}$.',
    '',
    f'- **Recomputation.** The validator builds $f_A$ from the list and commits to it, which gives ${show(COMMIT["A"])}$. The two points differ, so it rejects the stamp.',
    f'- **Evaluation at a random point.** The validator picks a point $r = {r}$ after it sees the commitment, so the prover cannot choose the commitment to suit $r$. It computes $({r} - {ta})({r} - {tb})({r} - {tc}) = {y}$ from the list. The polynomial behind the carried commitment gives ${ev(ftamp, r)}$ at $r = {r}$, so an opening to the value {y} fails. The two polynomials agree at {len(tamper_pass)} of the {Q} challenges, which is the prover\'s chance of getting past this test.',
])

# ---------------------------------------------------------------- limbs
encs = {encode(a): a for a in curve_points()}
assert len(encs) == len(curve_points()) == 42
assert all(limbs(a)[0] < 8 and limbs(a)[1] < 8 for a in curve_points())
ca = COMMIT['A']
lo, hi = limbs(ca)
assert encode(ca) == lo + 8 * hi
frag['limbs'] = (
    f'For $C_A = {show(ca)}$, the coordinate ${ca[0]}$ fits in five bits, and we place the parity of $y = {ca[1]}$ in a sixth bit. '
    f'The encoding is ${ca[0]} + 32 \\cdot {ca[1] & 1} = {encode(ca)}$. Splitting it into a low and a high part of three bits each gives '
    f'$\\mathsf{{tg}}_\\mathsf{{lo}} = {lo}$ and $\\mathsf{{tg}}_\\mathsf{{hi}} = {hi}$, since ${encode(ca)} = {lo} + 8 \\cdot {hi}$. '
    f'Checking all {len(encs)} affine points of the toy curve shows that each one gets a different encoding, so the pair of limbs determines the point.')

# ---------------------------------------------------------------- the chain
EPOCH_SIZE = 4
BLOCKS = {0: ['A'], 2: ['B', 'C'], 8: ['D'], 11: ['E'], 12: ['F']}
LAST_HEIGHT = 12
genesis = h_ep(0, 0)
state = None
seq = []          # every state: (name, epoch, fold description, value)
end_code = {}     # end-of-block anchor at each height, crossing at the start of an epoch's first block
end_deep = {}     # same, with the crossing at the end of the old epoch's last block
entry, final = {}, {}
after = {}
state = genesis
entry[0] = genesis
seq.append(('entry', 0, None, genesis))
rows = ['| Block | Epoch | Fold | Input | New anchor |', '| --- | --- | --- | --- | --- |']
rows.append(f'| (start) | 0 | $H_\\mathsf{{ep}}$ | $(0,\\ 0)$ | {genesis} |')
for height in range(LAST_HEIGHT + 1):
    epoch = height // EPOCH_SIZE
    if height % EPOCH_SIZE == 0 and height > 0:
        final[epoch - 1] = state
        state_new = h_ep(state, epoch)
        rows.append(f'| {height} | {epoch} | $H_\\mathsf{{ep}}$ | $({state},\\ {epoch})$ | {state_new} |')
        end_deep[height - 1] = state_new
        state = state_new
        entry[epoch] = state
        seq.append(('entry', epoch, None, state))
    for name in BLOCKS.get(height, []):
        lo_, hi_ = limbs(COMMIT[name])
        new = h_st(state, epoch, COMMIT[name])
        rows.append(f'| {height} | {epoch} | $H_\\mathsf{{st}}$, stamp {name} | $({state},\\ {epoch},\\ {lo_},\\ {hi_})$ | {new} |')
        after[name] = (height, epoch, state, new)
        state = new
        seq.append((name, epoch, None, state))
    end_code[height] = state
    end_deep.setdefault(height, state)
final[LAST_HEIGHT // EPOCH_SIZE] = state
all_values = [s[3] for s in seq]
assert len(set(all_values)) == len(all_values), all_values
assert 0 not in all_values
frag['chain'] = '\n'.join(rows)

frag['entry-final'] = '\n'.join(
    ['| Epoch | Stamps | Entry anchor | Final anchor |', '| --- | --- | --- | --- |']
    + [f'| {e} | {s} | {entry[e]} | {final[e]} |' for e, s in [(0, 'A, B, C'), (1, 'none'), (2, 'D, E')]])
assert entry[1] == final[1] and entry[0] != final[0] and entry[2] != final[2]
assert final[0] == after['C'][3] and final[2] == after['E'][3]
assert entry[2] == h_ep(entry[1], 2)

# The anchor a stamp carries versus the state its absorption produces.
assert end_code[0] == after['A'][3] and after['B'][2] == after['A'][3]
frag['carried'] = (
    f'Stamp B lands in block 2. Suppose its wallet built its proofs while the state after block 0, {end_code[0]}, was the latest, so that B carries the anchor {end_code[0]}. '
    f'When the validator absorbs B, the chain moves from {after["B"][2]} to {after["B"][3]}. The carried value {end_code[0]} names a state that existed before B, and the value {after["B"][3]} is a new state that B\'s absorption creates. '
    f'Stamp C in the same block could carry {end_code[0]} as well, even though its absorption starts from {after["C"][2]}.')

# Effects of order, epoch, and domain on one fold.
a0 = genesis
swap_ab = h_st(h_st(a0, 0, COMMIT['B']), 0, COMMIT['A'])
fwd_ab = h_st(h_st(a0, 0, COMMIT['A']), 0, COMMIT['B'])
assert swap_ab != fwd_ab and fwd_ab == after['B'][3]
wrong_epoch = h_st(a0, 1, COMMIT['A'])
assert wrong_epoch != after['A'][3] and wrong_epoch not in all_values
frag['absorb'] = (
    f'The chain starts from the genesis state {a0}, which is the entry anchor of epoch 0 that Section 7 derives as $H_\\mathsf{{ep}}(0,\\ 0)$. Stamp A lands in epoch 0, so the new anchor is $H_\\mathsf{{st}}({a0},\\ 0,\\ {lo},\\ {hi}) = {after["A"][3]}$. '
    f'Absorbing B after A gives {fwd_ab}, while absorbing A after B gives {swap_ab}, so the anchor records the order of stamps even though each stamp\'s own polynomial does not. '
    f'Claiming epoch 1 for stamp A would give {wrong_epoch} instead of {after["A"][3]}, and that value does not appear anywhere in the chain below.')

# Which states consensus acknowledges under each placement of the crossing.
seq_values_code = []
rows = ['| Block | Epoch | End-of-block state, crossing at the start of the new epoch (code, `anchor.md`) | End-of-block state, crossing at the end of the old epoch (deep dive) |', '| --- | --- | --- | --- |']
differ = [h for h in range(LAST_HEIGHT + 1) if end_code[h] != end_deep[h]]
assert differ == [3, 7, 11]
for h in differ:
    rows.append(f'| {h} | {h // EPOCH_SIZE} | {end_code[h]} | {end_deep[h]} |')
frag['placement'] = '\n'.join(rows)
assert end_code[3] == final[0] and end_deep[3] == entry[1]
assert end_code[8] != entry[2] and end_deep[7] == entry[2]
assert end_code[4] == entry[1]
assert entry[2] not in set(end_code.values())
assert final[2] == end_code[11] and final[2] not in set(end_deep.values())
assert after['B'][3] not in set(end_code.values())
assert end_code[3] == final[0] and end_deep[3] == entry[1] and end_code[7] == final[1] and end_deep[7] == entry[2]
assert end_deep[11] == entry[3]
frag['placement-note'] = (
    f'The table lists only the blocks where the two placements disagree, and each of them is the last block of an epoch. '
    f'With the code\'s placement, that block ends on its own epoch\'s final anchor, such as {final[0]} for epoch 0. '
    f'With the deep dive\'s placement, it ends on the next epoch\'s entry anchor, such as {entry[1]} for epoch 1. '
    f'So under the code\'s placement the entry anchor of epoch 2, {entry[2]}, is never an end-of-block value, because block 8 carries a stamp, and under the deep dive\'s placement the final anchor of epoch 2, {final[2]}, never is. '
    f'Under both placements, the state {after["B"][3]} just after stamp B is never an end-of-block value, because stamp C follows it in the same block.')

assert end_code[8] == after['D'][3] and after['D'][2] == entry[2]
frag['placement-short'] = (
    f'With the crossing at the start of the new epoch, which this site follows, block 8 opens epoch 2 by crossing to the entry anchor {entry[2]} and then absorbs stamp D, so it ends on {end_code[8]}. '
    f'The entry anchor {entry[2]} is therefore never an end-of-block value. '
    f'Section 10 shows what this means for proofs that end on an entry anchor, and it compares the other placement there.')

# ---------------------------------------------------------------- walking an epoch
probe = STAMPS['B'][2]
rows = ['| Step | Anchor | Running product | Product at $' + str(probe) + '$ |', '| --- | --- | --- | --- |']
rows.append(f'| start at $\\mathsf{{entry}}(0)$ | {entry[0]} | $1$ | 1 |')
prod = [1]
for name in ['A', 'B', 'C']:
    prod = pmul(prod, POLY[name])
    label = {'A': 'f_A', 'B': 'f_A f_B', 'C': 'f_A f_B f_C = e_0'}[name]
    rows.append(f'| absorb stamp {name} | {after[name][3]} | ${label}$ | {ev(prod, probe)} |')
assert prod == e0
rows.append(f'| crossing into epoch 1 | {entry[1]} | $e_0$ | {ev(e0, probe)} |')
frag['epoch-walk'] = '\n'.join([f'Here is the walk for epoch 0 of the run, testing the value {probe} from stamp B.', ''] + rows)
assert ev(POLY['A'], probe) != 0 and ev(e0, probe) == 0

# ---------------------------------------------------------------- stopping short
stop = after['A'][3]
assert stop in set(end_code.values()) and stop != final[0]
short = h_ep(stop, 1)
assert short != entry[1] and short not in all_values
col = [x for x in range(Q) if h_ep(x, 1) == entry[1]]
assert final[0] in col
others = [x for x in col if x != final[0]]
assert not set(others) & set(all_values)
frag['short-seal'] = (
    f'Suppose a prover runs this walk for epoch 0 and stops after stamp A, at anchor {stop}, leaving out B and C. '
    f'Its product is then only $f_A$, and $f_A({probe}) = {ev(POLY["A"], probe)}$ is nonzero, so the value {probe} from stamp B would look absent from epoch 0. '
    f'The anchor {stop} is a real end-of-block value from block 0, so a consensus check on it would pass. Now perform the crossing from it. '
    f'The result is $H_\\mathsf{{ep}}({stop},\\ 1) = {short}$, while the true entry anchor of epoch 1 is {entry[1]} = $H_\\mathsf{{ep}}({final[0]},\\ 1)$. '
    f'The value {short} appears nowhere in the chain, so nothing built on it can reach a published anchor.')
frag['short-count'] = (
    f'Our stand-in hash has only {Q} outputs, so we can count the inputs that would rescue the short run. '
    f'Of the {Q} possible states $x$, the crossing $H_\\mathsf{{ep}}(x,\\ 1)$ lands on {entry[1]} for {len(col)} of them. They are '
    + (f'the true final anchor {final[0]} and the colliding value{"s" if len(others) > 1 else ""} {" and ".join(map(str, others))}. ' if others else f'only the true final anchor {final[0]}. ')
    + 'A collision like this is what a cheater would need, and on the real field finding one means breaking Poseidon.')

# Starting the walk late, at a genuine state inside the epoch.
late = after['A'][3]
w = late
for name in ['B', 'C']:
    w = h_st(w, 0, COMMIT[name])
assert w == final[0] and h_ep(w, 1) == entry[1]
late_prod = pmul(POLY['B'], POLY['C'])
late_probe = STAMPS['A'][1]
assert ev(late_prod, late_probe) != 0 and ev(e0, late_probe) == 0
frag['late-start'] = (
    f'Suppose instead that a prover starts the walk for epoch 0 at the state {late}, just after stamp A, and folds only B and C. '
    f'Its product is $f_B f_C$, and $f_B({late_probe}) f_C({late_probe}) = {ev(late_prod, late_probe)}$ is nonzero, so the value {late_probe} from stamp A would look absent. '
    f'The walk passes through {after["B"][3]} and ends at {w}, which is the true final anchor, and the crossing gives $H_\\mathsf{{ep}}({w},\\ 1) = {entry[1]}$, the true entry anchor of epoch 1. '
    f'The check at the end of the walk passes, so the defense has to come from the start.')
pre_late = [x for x in range(Q) if h_ep(x, 0) == late]
pre_true = [x for x in range(Q) if h_ep(x, 0) == entry[0]]
assert pre_true == [0] and not set(pre_late) & set(all_values)
frag['late-count'] = (
    f'The seal asks the prover for a state $x$ with $H_\\mathsf{{ep}}(x,\\ 0) = {late}$. In the chain, {late} is the output $H_\\mathsf{{st}}({entry[0]},\\ 0,\\ {lo},\\ {hi})$ of a stamp fold, so any such $x$ is a collision between the two domains. '
    + (f'Our stand-in has only {Q} outputs, and {len(pre_late)} such inputs exist, namely {" and ".join(map(str, pre_late))}. ' if pre_late else f'Our stand-in has none. ')
    + f'For the genuine start {entry[0]}, the only input is $x = {pre_true[0]}$, as Section 7 defined. On the real field, finding any $x$ for a stamp-fold output means breaking Poseidon across domains.')

# A free-witnessed predecessor.
bad_prev = (after['A'][3] + 1) % Q
assert bad_prev not in all_values
bad_after = h_st(bad_prev, 0, COMMIT['B'])
assert bad_after not in all_values and bad_after != after['B'][3]
frag['free-witness'] = (
    f'For instance, a wallet could witness the predecessor {bad_prev} in place of {after["A"][3]} for stamp B. The fold then gives {bad_after}, '
    f'which is not in the chain, so the proof runs without complaint and the error surfaces only when consensus looks up the anchor.')

# An invented boundary digest at the start of the walk.
def walk_from(x, names):
    states = [h_ep(x, 0)]
    for name in names:
        states.append(h_st(states[-1], 0, COMMIT[name]))
    states.append(h_ep(states[-1], 1))
    return states
inv_x = next(x for x in range(1, Q)
             if not set(walk_from(x, ['A', 'B', 'C']) + walk_from(x, ['A', 'C'])) & set(all_values))
full = walk_from(inv_x, ['A', 'B', 'C'])
skip = walk_from(inv_x, ['A', 'C'])
assert full[0] == skip[0] and full[1] == skip[1]
assert full[-1] != entry[1] and skip[-1] != entry[1]
skip_hits = [x for x in range(1, Q) if walk_from(x, ['A', 'C'])[-1] == entry[1]]
frag['invented-start'] = '\n'.join([
    f'Take epoch 0 of the run and suppose a prover witnesses $x = {inv_x}$ in place of the true $x = 0$. '
    f'The seal accepts a walk that starts at $H_\\mathsf{{ep}}({inv_x},\\ 0) = {full[0]}$. '
    f'The table follows two such walks, one that folds the genuine stamps A, B and C, and one that leaves out stamp B so that the value {probe} would look absent.',
    '',
    '| Step | Folding A, B, C | Folding A and C only |',
    '| --- | --- | --- |',
    f'| start at $H_\\mathsf{{ep}}({inv_x},\\ 0)$ | {full[0]} | {skip[0]} |',
    f'| absorb stamp A | {full[1]} | {skip[1]} |',
    f'| absorb stamp B | {full[2]} | (skipped) |',
    f'| absorb stamp C | {full[3]} | {skip[2]} |',
    f'| crossing into epoch 1 | {full[4]} | {skip[3]} |',
    '',
    f'None of these values appears in the chain table of Section 7, whose states are {", ".join(map(str, all_values[:-1]))} and {all_values[-1]}. '
    f'The crossings {full[4]} and {skip[3]} both miss the published entry anchor {entry[1]}. '
    + (f'We tried all {Q - 1} invented values of $x$, and none of them makes the walk that skips B end at {entry[1]}.' if not skip_hits
       else f'Of the {Q - 1} invented values of $x$, {len(skip_hits)} make the walk that skips B end at {entry[1]}, and each of them is a collision.'),
])

# ---------------------------------------------------------------- spans
start = entry[2]
m1, m2 = after['D'][3], after['E'][3]
M = roots_poly([m1, m2])
one = [-m1 % Q, 1]
assert commit(one) == add(GENS[1], mul(-m1 % Q, GENS[0]))
assert commit(M) is not None
outsider = final[0]
assert outsider not in (start, m1, m2)
check = lambda a: ev(M, a) * (a - start) % Q
assert check(start) == check(m1) == check(m2) == 0 and check(outsider) != 0
count_pass = [a for a in range(Q) if check(a) == 0]
assert sorted(count_pass) == sorted([start, m1, m2])
frag['span'] = '\n'.join([
    f'Take epoch 2 from the run above. A span starts at the entry anchor {start} and folds stamps D and E, producing the members {m1} and {m2}. Its members polynomial is',
    '',
    f'$$M(X) = (X - {m1})(X - {m2}) = {pshow(M)}.$$',
    '',
    '| Stamp anchor $a$ | Position | $M(a)$ | $a - $ start | Product | Result |',
    '| --- | --- | --- | --- | --- | --- |',
    f'| {start} | span start | {ev(M, start)} | {(start - start) % Q} | {check(start)} | lifts to {m2} |',
    f'| {m1} | member | {ev(M, m1)} | {(m1 - start) % Q} | {check(m1)} | lifts to {m2} |',
    f'| {m2} | member, span end | {ev(M, m2)} | {(m2 - start) % Q} | {check(m2)} | stays at {m2} |',
    f'| {outsider} | final anchor of epoch 0 | {ev(M, outsider)} | {(outsider - start) % Q} | {check(outsider)} | rejected |',
    '',
    f'Among all {Q} field elements, exactly {len(count_pass)} pass this check.',
])
frag['span-cross'] = (
    f'In our run, a span over epoch 2 ends at {final[2]}, and a span over the stamp in epoch 3 starts at {entry[3]}. '
    f'The fuse requires those two values to match, and they do not, because the crossing sits between them.')
assert final[2] != entry[3]

# ---------------------------------------------------------------- the window
def in_window(epoch):
    keep = []
    for name, (height, e, _, _) in after.items():
        if e in (epoch, epoch - 1):
            keep.append(name)
    return keep


rows = ['| Current epoch | Window | Stamps retained | Tachygrams retained |', '| --- | --- | --- | --- |']
for e in [0, 1, 2, 3]:
    keep = in_window(e)
    n = sum(len(STAMPS[k]) for k in keep)
    win = f'$\\{{{e}\\}}$' if e == 0 else f'$\\{{{e - 1},\\ {e}\\}}$'
    rows.append(f'| {e} | {win} | {", ".join(keep) if keep else "none"} | {n} |')
frag['retained'] = '\n'.join(rows)
assert in_window(1) == ['A', 'B', 'C'] and in_window(2) == ['D', 'E'] and in_window(3) == ['D', 'E', 'F']
val = STAMPS['C'][1]
frag['retained-note'] = (
    f'The value ${val}$ from stamp C is therefore rejected if a stamp republishes it in epoch 1, and it passes this check in epoch 2, because epoch 0 has left the window. '
    'Forgetting epoch 0 at that point is safe for spends. A spend accepted in epoch 2 targets epoch 1 or 2, so its exclusion proof already covers epoch 0.')

# ---------------------------------------------------------------- what the chain costs
BLOCK_SECONDS = 75
YEAR = 365 * 24 * 3600
blocks_year = YEAR // BLOCK_SECONDS
TPS = 100
per_block = TPS * BLOCK_SECONDS
mb = blocks_year * 32 / 1e6
stamps_year = TPS * YEAR
gb = stamps_year * 32 / 1e9
frag['chain-cost'] = '\n'.join([
    f'At the 75-second block target there are {blocks_year:,} blocks per year. Take the hypothetical {TPS} transactions per second from [chapter 1](./scaling-zcash.md), which is {per_block:,} transactions per block. These inputs are illustrative.',
    '',
    '| Case | Folds per block | Anchors per year, if validators keep every inner state | Size at 32 bytes each, if validators keep every inner state |',
    '| --- | --- | --- | --- |',
    f'| Every transaction is an autonome | {per_block:,} | {stamps_year:,} | {gb:,.1f} GB |',
    f'| One aggregate per block | 1 | {blocks_year:,} | {mb:,.1f} MB |',
])

print(json.dumps(frag))
