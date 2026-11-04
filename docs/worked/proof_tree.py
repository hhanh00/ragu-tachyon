"""Worked examples for proof-tree.md. Prints fragments as JSON.

One spend of chapter 19's note, traced through Tachyon's proof steps. The note,
its keys and its nullifiers are imported from notes_and_nullifiers.py, so they
carry the same stand-in values. Three kinds of number appear below:

- Hash outputs are chapter 19's stand-in, SHA-256 of a tag and inputs reduced
  modulo 65537. They are not Poseidon outputs.
- Set and sequence polynomials live over F_65539, a stand-in for F_p. It is the
  first prime above the hash range in which 2 has no cube root, which the
  indexed factor needs.
- Signing keys and value commitments are real arithmetic on the toy curve.

Set commitments are a stand-in as well, a hash of the coefficients, because a
polynomial over F_65539 does not fit the toy curve's scalars. Only their
determinism and binding matter here. Chapter 20 runs the Pedersen form.

No proof exists anywhere in this script. Each step's body is run natively, which
is also what the mock Ragu at revision 0725b52 does.
"""
import contextlib
import io
import json

with contextlib.redirect_stdout(io.StringIO()):
    import notes_and_nullifiers as n
from toy_curve import G, Q, add, log, mul, show

frag = {}
H = n.H
S = 65539            # the stand-in polynomial field
NR = 2               # the cubic non-residue, as in the code
WIDTH = 16           # NF_DERIVATION_WIDTH
GEN, V, R = G[0], G[1], G[2]
assert all(S % k for k in range(2, 300)) and S % 3 == 1 and pow(NR, (S - 1) // 3, S) != 1
assert 65537 % 3 == 2  # every element has a cube root modulo 65537, so that field cannot host the factor
assert len({GEN, V, R}) == 3

CM, MK, PK, PSI, RCM, VAL, NK, AK, ASK = n.CM, n.MK, n.PK, n.PSI, n.RCM, n.V, n.NK, n.AK, n.ASK
nf = {e: n.nullifier(MK, e) for e in range(32)}
assert (CM, MK, nf[7], nf[8]) == (55697, 299, 55113, 61177)  # chapter 19's values


# ------------------------------------------------------------ polynomial tools
def pmul(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] = (out[i + j] + x * y) % S
    return out


def pdivmod(a, b):
    a, q = a[:], [0] * (len(a) - len(b) + 1)
    inv = pow(b[-1], -1, S)
    for i in range(len(q) - 1, -1, -1):
        q[i] = a[i + len(b) - 1] * inv % S
        for j, y in enumerate(b):
            a[i + j] = (a[i + j] - q[i] * y) % S
    while len(a) > 1 and a[-1] == 0:
        a.pop()
    rem = a[:len(b) - 1] if len(b) > 1 else [0]
    return q, rem


def pev(a, x):
    out = 0
    for c in reversed(a):
        out = (out * x + c) % S
    return out


def product(polys):
    out = [1]
    for p in polys:
        out = pmul(out, p)
    return out


def roots(values):
    return product([[(-v) % S, 1] for v in values])


def factor(i, m):
    """The indexed factor F_{i,m}(X) = (m + (i+1)X)^3 - 2."""
    a = (i + 1) % S
    return [(m ** 3 - NR) % S, 3 * a * m * m % S, 3 * a * a * m % S, a ** 3 % S]


def seq(pairs):
    return product([factor(i, m) for i, m in pairs])


def com(poly):
    """Stand-in for a deterministic commitment to a polynomial."""
    return H('Commit', *poly)


def chal(*coms):
    z = H('Challenge', *coms)
    assert z not in (0, 1)
    return z


def poly_tex(p):
    terms = []
    for i in range(len(p) - 1, -1, -1):
        c = p[i]
        if c == 0:
            continue
        x = '' if i == 0 else ('X' if i == 1 else f'X^{{{i}}}')
        terms.append(f'{c}{x}' if (c != 1 or i == 0) else x)
    return ' + '.join(terms)


def st(a, e, c):
    return H('Tachyon-AnchorSt', a, e, c)


def ep(a, e):
    return H('Tachyon-AnchorEp', a, e)


def tex(names):
    return ',\\ '.join(str(x) for x in names)


# ----------------------------------------------------------------- pool history
bob_nf = [H('bob-spend', i) for i in range(2)]
bob_chg = H('bob-change', 1)
CREATION = sorted([CM, n.PAD] + bob_nf + [bob_chg])
stamps = {
    3: [[H('tg', 3, 0, j) for j in range(3)], CREATION, [H('tg', 3, 2, j) for j in range(3)]],
    4: [[H('tg', 4, 0, j) for j in range(3)], [H('tg', 4, 1, j) for j in range(3)]],
    5: [[H('tg', 5, 0, j) for j in range(3)]],
    6: [],
    7: [[H('tg', 7, i, j) for j in range(3)] for i in range(3)],
}
FINAL2 = H('history-before-epoch-3')
entry, final, trail = {}, {}, {}
state = FINAL2
for e in sorted(stamps):
    state = ep(state, e)
    entry[e] = state
    trail[e] = [state]
    for tgs in stamps[e]:
        state = st(state, e, com(roots(tgs)))
        trail[e].append(state)
    final[e] = state
entry[8] = None
ACCEPTED = {a for e in trail for a in trail[e]}
assert len(ACCEPTED) == sum(len(t) for t in trail.values())  # no collisions in this run
next_entry = {e: ep(final[e], e + 1) for e in stamps}
for e in (3, 4, 5, 6):
    assert next_entry[e] == entry[e + 1]

contents = {e: roots([t for s in stamps[e] for t in s]) if stamps[e] else [1] for e in stamps}
for e in range(3, 8):
    assert pev(contents[e], nf[e]) != 0
assert pev(contents[3], CM) == 0
ALL_TG = [t for e in stamps for s in stamps[e] for t in s]
assert len(set(ALL_TG)) == len(ALL_TG) and not set(ALL_TG) & set(nf.values())

rows = ['| Epoch | Stamps | Tachygrams | Entry anchor | Final anchor |', '| --- | --- | --- | --- | --- |']
for e in sorted(stamps):
    rows.append(f'| {e} | {len(stamps[e])} | {sum(len(s) for s in stamps[e])} | {entry[e]} | {final[e]} |')
frag['pool'] = '\n'.join(rows)
frag['pool-note'] = (
    f'The second stamp of epoch 3 is Bob\'s, and its 5 tachygrams include Alice\'s commitment {CM}. Epoch 6 published '
    f'nothing, so its entry and final anchors are both {entry[6]}. Epoch 7 is still open. We write $a_1, a_2, a_3$ for '
    f'the anchors after its three stamps, which are {trail[7][1]}, {trail[7][2]} and {trail[7][3]}.')

# ------------------------------------------------------------------- NoteSeed
frag['note-seed'] = '\n'.join([
    '| Quantity | Computation | Value |', '| --- | --- | --- |',
    f'| witness | $v$, $\\psi$, $\\mathsf{{rcm}}$, $\\mathsf{{ak}}$, $\\mathsf{{nk}}$ | {VAL}, {PSI}, {RCM}, ${show(AK)}$, {NK} |',
    f'| $\\mathsf{{pk}}$ | $H_{{\\texttt{{PkDerive}}}}({AK[0]},\\ {AK[1]},\\ {NK})$ | {PK} |',
    f'| $\\mathsf{{mk}}$ | $H_{{\\texttt{{NfMaster}}}}({PSI},\\ {NK})$ | {MK} |',
    f'| $\\mathsf{{cm}}$ | $H_{{\\texttt{{CmDerive}}}}({RCM},\\ {PK},\\ {VAL},\\ {PSI})$ | {CM} |',
])
assert n.payment_key(AK, NK) == PK and H('Tachyon-NfMaster', PSI, NK) == MK and n.commit(RCM, PK, VAL, PSI) == CM

# -------------------------------------------------------------- NullifierDerive
rows = ['| Sponge input $w$ | $\\mathsf{nf}_w$ | $\\mathsf{nf}_{w+1}$ | $\\mathsf{nf}_{w+2}$ | $\\mathsf{nf}_{w+3}$ |',
        '| --- | --- | --- | --- | --- |']
for w in range(0, WIDTH, 4):
    group = n.nullifier_group(MK, w)
    assert group == [nf[w + i] for i in range(4)]
    rows.append('| ' + ' | '.join([str(w)] + [str(x) for x in group]) + ' |')
frag['window'] = '\n'.join(rows)

# The factor, its irreducibility, and why a linear factor would not do.
F3 = factor(3, nf[3])
assert all(pev(F3, x) != 0 for x in range(S))
frag['factor'] = (
    f'For epoch 3 the member is $\\mathsf{{nf}}_3 = {nf[3]}$ and $i + 1 = 4$, so working modulo {S:,},\n\n'
    f'$$F_{{3,\\,{nf[3]}}}(X) = ({nf[3]} + 4X)^3 - 2 = {poly_tex(F3)}.$$\n\n'
    f'Trying all {S:,} field elements finds no root, so this cubic has no linear factor, and a cubic with no linear '
    f'factor is irreducible.')

m2 = 8 * nf[3] * pow(4, -1, S) % S       # the member at epoch 7 whose linear factor has the same root
lin = lambda i, m: [m % S, (i + 1) % S]
root = lambda p: (-p[0]) * pow(p[1], -1, S) % S
assert root(lin(3, nf[3])) == root(lin(7, m2)) and m2 != nf[3]
assert factor(3, nf[3]) != factor(7, m2)
frag['linear-collision'] = (
    f'The linear factor $m + (i+1)X$ has the root $-m/(i+1)$, so the pair (epoch 3, member {nf[3]}) and the pair '
    f'(epoch 7, member {m2}) share a root, and the two factors differ only by a constant multiple. Divisibility cannot '
    f'tell them apart. Their cubic factors have different coefficients, and the leading terms alone already differ, at '
    f'{factor(3, nf[3])[3]} against {factor(7, m2)[3]}.')

zeta = next(pow(x, (S - 1) // 3, S) for x in range(2, 50) if pow(x, (S - 1) // 3, S) != 1)
assert pow(zeta, 3, S) == 1 and zeta != 1
collide = [(i, j) for i in range(WIDTH) for j in range(WIDTH) if i != j
           and (j + 1) % S in ((i + 1) * zeta % S, (i + 1) * zeta * zeta % S)]
assert not collide
PALLAS_P = 0x40000000000000000000000000000000224698fc094cf91b992d30ed00000001
from math import isqrt  # noqa: E402
bound_toy, bound_real = isqrt(S // 3), isqrt(PALLAS_P // 3)
assert 1048576 < bound_real
assert 2 ** 125 < bound_real < 2 ** 127
frag['cube-root'] = (
    f'Two cubic factors can still coincide when the ratio of their linear terms is a cube root of unity. Modulo {S:,} '
    f'such a root is $\\zeta = {zeta}$, so a collision needs $j + 1 = \\zeta(i + 1)$ or $j + 1 = \\zeta^2(i + 1)$ for two '
    f'epoch indices. None of the {WIDTH * (WIDTH - 1)} ordered pairs in our window satisfies this. The code\'s comment gives '
    f'$i + 1$ below $\\sqrt{{p/3}}$ as enough to rule out every such pair. That bound is {bound_toy} for our stand-in field, '
    f'and it exceeds $2^{{125}}$ for the real $p$, while epoch indices stay below $2^{{20}}$.')

WINDOW = [(e, nf[e]) for e in range(WIDTH)]
G0 = seq(WINDOW)
assert len(G0) - 1 == 3 * WIDTH
COM_G0 = com(G0)
z = chal(COM_G0)
direct = 1
for e, m in WINDOW:
    direct = direct * (((e + 1) * z + m) ** 3 - NR) % S
assert pev(G0, z) == direct
wrong = list(WINDOW)
wrong[5] = (5, H('wrong-member', 5))
G_wrong = seq(wrong)
passing = [x for x in range(S) if pev(G_wrong, x) == pev(G0, x)]
assert 0 < len(passing) <= 3 * WIDTH
frag['derive-open'] = (
    f'The sequence has degree $3 \\cdot {WIDTH} = {3 * WIDTH}$, and its stand-in commitment is {COM_G0}. The challenge '
    f'derived from that commitment is $z = {z}$. The opening gives $g({z}) = {pev(G0, z)}$, and the step gets the same '
    f'value by evaluating the {WIDTH} factors directly from the sponge outputs. Suppose a prover commits instead to a '
    f'sequence with the member at epoch 5 replaced by {wrong[5][1]}. Testing every challenge shows that this false '
    f'sequence agrees with the true product at {len(passing)} of the {S:,} points, which is within the degree bound of '
    f'{3 * WIDTH}.')

# NullifierFuse
W2 = [(e, nf[e]) for e in range(WIDTH, 2 * WIDTH)]
G1 = seq(W2)
GM = pmul(G0, G1)
zf = chal(com(G0), com(G1), com(GM))
assert pev(GM, zf) == pev(G0, zf) * pev(G1, zf) % S
frag['nullifier-fuse'] = (
    f'A second window starting at epoch {WIDTH} passes the contiguity check, since ${WIDTH} = 15 + 1$. At the challenge '
    f'$z = {zf}$ the product check reads ${pev(GM, zf)} = {pev(G0, zf)} \\cdot {pev(G1, zf)}$ modulo {S:,}. A window '
    f'starting at epoch 12 would also be group-aligned, but it would repeat four epochs, and the check rejects it '
    f'because $12 \\neq 16$.')

# ---------------------------------------------------------------- SpendableInit
PREV = trail[3][1]
COM_CREATE = com(roots(CREATION))
A_AFTER = st(PREV, 3, COM_CREATE)
assert A_AFTER == trail[3][2] and A_AFTER in ACCEPTED
WRONG_PREV = (PREV + 1) % n.F
WRONG_A = st(WRONG_PREV, 3, COM_CREATE)
WRONG_E = st(PREV, 4, COM_CREATE)
assert WRONG_A not in ACCEPTED and WRONG_E not in ACCEPTED
frag['spendable-init'] = (
    f'The creation polynomial gives {pev(roots(CREATION), CM)} at $\\mathsf{{cm}} = {CM}$, so the membership check passes. Its '
    f'commitment stands in as {COM_CREATE}, and the witnessed predecessor is {PREV}, so the step computes '
    f'$H_\\mathsf{{st}}({PREV},\\ 3,\\ {COM_CREATE}) = {A_AFTER}$ and emits $(\\mathsf{{cm}}, e, \\text{{anchor}}) = '
    f'({CM},\\ 3,\\ {A_AFTER})$.')
frag['spendable-init-wrong'] = (
    f'A wrong predecessor {WRONG_PREV} gives {WRONG_A}, and a wrong epoch 4 gives {WRONG_E}. The step accepts both, since '
    f'nothing in it can tell, but neither value appears in the chain.')

# -------------------------------------------------------- exclusion, as a black box
rows = ['| Epoch $e$ | Tested value $\\mathsf{nf}_e$ | Bucket opened at that value | Absent |', '| --- | --- | --- | --- |']
for e in (3, 4, 5, 6):
    rows.append(f'| {e} | {nf[e]} | {pev(contents[e], nf[e])} | yes |')
frag['exclusion'] = '\n'.join(rows)

# Segments. Each one is (anchor_start, epoch_start, elapsed, epoch_next, anchor_next).
elapsed = {e: seq([(e, nf[e])]) for e in (3, 4, 5, 6)}
seg3 = (entry[3], 3, com(elapsed[3]), 4, entry[4])
seg4 = (entry[4], 4, com(elapsed[4]), 5, entry[5])
seg5 = (entry[5], 5, com(elapsed[5]), 6, entry[6])
L = pmul(elapsed[4], elapsed[5])
seg45 = (seg4[0], 4, com(L), 6, seg5[4])
assert seg4[3] == seg5[1] and seg4[4] == seg5[0]
zu = chal(com(elapsed[4]), com(elapsed[5]), com(L))
assert pev(L, zu) == pev(elapsed[4], zu) * pev(elapsed[5], zu) % S
E456 = pmul(L, elapsed[6])
seg456 = (seg45[0], 4, com(E456), 7, entry[7])
seg6_bucket = (6, entry[6], entry[7])
assert seg45[4] == seg6_bucket[1] and seg45[3] == seg6_bucket[0]
zl = chal(com(L), com(E456))
assert pev(E456, zl) == pev(L, zl) * pev(elapsed[6], zl) % S

rows = ['| Step | Runs on | Output: anchor start, epoch start, elapsed, epoch next, anchor next |', '| --- | --- | --- |']
tup = lambda t: '$(' + ',\\ '.join(str(x) for x in t) + ')$'
rows += [f'| `QrUnspentInit` | bucket of epoch 3, $\\mathsf{{nf}}_3$ | {tup(seg3)} |',
         f'| `QrUnspentInit` | bucket of epoch 4, $\\mathsf{{nf}}_4$ | {tup(seg4)} |',
         f'| `QrUnspentInit` | bucket of epoch 5, $\\mathsf{{nf}}_5$ | {tup(seg5)} |',
         f'| `UnspentFuse` | the two segments above | {tup(seg45)} |',
         f'| `UnspentLift` | that segment, bucket of epoch 6, $\\mathsf{{nf}}_6$ | {tup(seg456)} |']
frag['segments'] = '\n'.join(rows)
frag['segments-note'] = (
    f'The fuse checks that the anchors meet at {seg4[4]} and the epochs meet at 5, and then checks '
    f'$C(z) = L(z) \\cdot R(z)$ at $z = {zu}$, where it reads ${pev(L, zu)} = {pev(elapsed[4], zu)} \\cdot '
    f'{pev(elapsed[5], zu)}$. The lift\'s product check at $z = {zl}$ reads ${pev(E456, zl)} = {pev(L, zl)} \\cdot '
    f'{pev(elapsed[6], zl)}$. Each segment holds plain numbers, so nothing in the table mentions a note.')

# ----------------------------------------------------------------- UnspentBind
comp3, rem3 = pdivmod(G0, elapsed[3])
comp456, rem456 = pdivmod(G0, E456)
assert not any(rem3) and not any(rem456)
assert len(comp3) - 1 == 45 and len(comp456) - 1 == 39
zb = chal(com(E456), com(comp456), com(G0))
assert pev(G0, zb) == pev(E456, zb) * pev(comp456, zb) % S
un3 = (CM, entry[3], 3, 4, entry[4])
un456 = (CM, entry[4], 4, 7, entry[7])
frag['unspent-bind'] = (
    f'Dividing the window polynomial, which has degree {len(G0) - 1}, by the composed `elapsed` of degree '
    f'{len(E456) - 1} leaves remainder 0 and a complement of degree {len(comp456) - 1}, namely the 13 factors for epochs '
    f'0 to 3 and 7 to 15. At the challenge $z = {zb}$ the check reads ${pev(G0, zb)} = {pev(E456, zb)} \\cdot '
    f'{pev(comp456, zb)}$. The step outputs {tup(un456)}, whose first entry is $\\mathsf{{cm}}$. The segment for epoch 3 '
    f'binds the same way, with a complement of degree {len(comp3) - 1}, and gives {tup(un3)}.')

# The attack that the epoch index stops.
FAKE = 9
epoch5_spent = roots([t for s in stamps[5] for t in s] + [nf[5], nf[6]])
assert pev(epoch5_spent, nf[5]) == 0 and pev(epoch5_spent, nf[6]) == 0
assert pev(epoch5_spent, nf[FAKE]) != 0
g_plain = roots([nf[e] for e in range(WIDTH)])
el_plain = roots([nf[3], nf[4], nf[FAKE], nf[6]])
_, rem_plain = pdivmod(g_plain, el_plain)
assert not any(rem_plain)
el_cheat = seq([(3, nf[3]), (4, nf[4]), (5, nf[FAKE]), (6, nf[6])])
_, rem_cheat = pdivmod(G0, el_cheat)
assert any(rem_cheat)
honest = seq([(3, nf[3]), (4, nf[4]), (5, nf[5]), (6, nf[6])])
comp_honest, r0 = pdivmod(G0, honest)
assert not any(r0)
hits = [x for x in range(S) if pev(G0, x) == pev(el_cheat, x) * pev(comp_honest, x) % S]
assert len(hits) == 2
frag['epoch-attack'] = (
    f'Suppose Alice already spent the note with target 5, so epoch 5 now holds $\\mathsf{{nf}}_5$ and '
    f'$\\mathsf{{nf}}_6$. An honest test at epoch 5 gives ${pev(epoch5_spent, nf[5])}$, and the segment cannot be built. '
    f'She now tries a second spend with target 7 and tests a different one of her nullifiers at epoch 5, namely '
    f'$\\mathsf{{nf}}_{FAKE} = {nf[FAKE]}$, which gives {pev(epoch5_spent, nf[FAKE])}, so the bucket reports absence.\n\n'
    f'With plain factors $X - \\mathsf{{nf}}_e$ the tested values $\\{{\\mathsf{{nf}}_3, \\mathsf{{nf}}_4, '
    f'\\mathsf{{nf}}_{FAKE}, \\mathsf{{nf}}_6\\}}$ all come from the window, the division leaves remainder 0, and the '
    f'double spend goes through. With indexed factors, $F_{{5,\\,{nf[FAKE]}}}$ does not divide the window polynomial, '
    f'because the window holds $F_{{5,\\,{nf[5]}}}$ and $F_{{{FAKE},\\,{nf[FAKE]}}}$. The division now leaves a nonzero '
    f'remainder. If she commits to the honest complement anyway and hopes for a lucky challenge, then testing all '
    f'{S:,} challenges shows that the check passes at exactly {len(hits)} of them.')

# --------------------------------------------------------------- SpendableLift
sp0 = (CM, 4, entry[4])
assert un3[3] == 4 and un3[4] == entry[4] and pev(contents[3], CM) == 0
sp1 = (CM, un456[3], un456[4])
assert un456[0] == sp0[0] and un456[2] == sp0[1] and un456[1] == sp0[2]
frag['qr-spendable-init'] = (
    f'For our note, the opening of epoch 3\'s bucket at {CM} gives 0, and the bound segment from the last section has '
    f'the same extent as the bucket, running from {entry[3]} to {entry[4]}. So the step emits '
    f'$({sp0[0]},\\ {sp0[1]},\\ {sp0[2]})$, which rests on the entry anchor of epoch 4.')
OTHER_CM = n.commit(H('sender-rcm', 'bob-to-alice', 3), PK, 9, PSI)
assert OTHER_CM != CM
frag['lift-checks'] = '\n'.join([
    '| Check | Spendable | Segment | Result |', '| --- | --- | --- | --- |',
    f'| same note | $\\mathsf{{cm}} = {sp0[0]}$ | $\\mathsf{{cm}} = {un456[0]}$ | equal |',
    f'| same epoch | $e = {sp0[1]}$ | epoch start ${un456[2]}$ | equal |',
    f'| same position | anchor {sp0[2]} | anchor start {un456[1]} | equal |',
    f'| output | | | $({sp1[0]},\\ {sp1[1]},\\ {sp1[2]})$ |',
])
frag['lift-rejects'] = (
    f'A spendable from `SpendableInit` cannot take this route. Its anchor {A_AFTER} is the state after the creation stamp '
    f'and the segment for epoch 3 starts at {entry[3]}, while the segment for epoch 4 starts at {entry[4]}. Neither '
    f'matches, so the third check fails.')
assert A_AFTER not in (entry[3], entry[4])
frag['value-drift'] = (
    f'Recall the second note from [chapter 19](./notes-and-nullifiers.md#_9-reusing-a-trapdoor) with the same $\\psi$. '
    f'It has the same $\\mathsf{{mk}}$ and so the same nullifiers, which means a segment bound through its derivation '
    f'tests identical values. The `cm` check still separates them. With a new $\\mathsf{{rcm}}$ and value 9, its '
    f'commitment is {OTHER_CM}, and {OTHER_CM} $\\neq$ {CM} stops the lift, so a spender cannot move absence evidence '
    f'from a note worth 9 to a note worth {VAL}, or the reverse.')

# ------------------------------------------------------------------- SpendBind
THETA, ALPHA, RK = n.THETA, n.ALPHA, n.RK
RSK = (ASK + ALPHA) % Q


def cv_of(v, rcv):
    return add(mul(v % Q, V), mul(rcv % Q, R))


# Keep every published point visibly distinct, so no value looks like a key or a generator.
USED_X = {pt[0] for pt in (GEN, V, R, AK, RK)}


def fresh_blind(v, label):
    for i in range(100):
        blind = H('rcv', label, i) % Q
        point = cv_of(v, blind)
        if blind and point is not None and point[0] not in USED_X:
            USED_X.add(point[0])
            return blind, point
    raise AssertionError('no blind found')


RCV_S, CV_S = fresh_blind(VAL, 'spend')
EPOCH = 7
NF_CUR, NF_NEXT = nf[EPOCH], nf[EPOCH + 1]
assert NF_CUR != 0 and NF_NEXT != 0
SPEND_HEADER = (CM, NF_CUR, NF_NEXT, entry[7], PK)
frag['spend-bind'] = '\n'.join([
    '| Output field | Source | Value |', '| --- | --- | --- |',
    f'| $\\mathsf{{cm}}$ | spendable, checked equal to the secret\'s | {CM} |',
    f'| $\\mathsf{{nf}}_\\text{{current}}$ | $\\mathsf{{mk}} = {MK}$ at epoch 7 | {NF_CUR} |',
    f'| $\\mathsf{{nf}}_\\text{{next}}$ | $\\mathsf{{mk}} = {MK}$ at epoch 8 | {NF_NEXT} |',
    f'| anchor | spendable | {entry[7]} |',
    f'| $\\mathsf{{pk}}$ | the secret\'s note | {PK} |',
    f'| $\\mathsf{{cv}}$ | $[{VAL}]\\mathcal{{V}} + [{RCV_S}]\\mathcal{{R}}$ | ${show(CV_S)}$ |',
])
frag['value-gens'] = (
    f'On the toy curve we take $\\mathcal{{V}} = {show(V)}$ and $\\mathcal{{R}} = {show(R)}$.')


def digest_of(cv, rk):
    return H('Tachyon-ActionDg', cv[0], cv[1], rk[0], rk[1])


D_S = digest_of(CV_S, RK)
assert mul(RSK, GEN) == RK and add(AK, mul(ALPHA, GEN)) == RK
A_SPEND = roots([D_S])
T_SPEND = roots([NF_CUR, NF_NEXT])
NK_WRONG = H('expand', 'mallory', 0x22)
PK_WRONG = n.payment_key(AK, NK_WRONG)
assert PK_WRONG != PK
ASK_M = 11
AK_M = mul(ASK_M, GEN)
PK_M = n.payment_key(AK_M, NK)
assert PK_M != PK
frag['spend-action'] = '\n'.join([
    '| Quantity | Computation | Value |', '| --- | --- | --- |',
    f'| check on $\\mathsf{{pak}}$ | $H_{{\\texttt{{PkDerive}}}}({AK[0]},\\ {AK[1]},\\ {NK})$ against the header | {PK} matches |',
    f'| $\\alpha$ | $H_{{\\texttt{{Spend}}}}({THETA},\\ {CM})$, reduced mod {Q} | {ALPHA} |',
    f'| $\\mathsf{{rk}}$ | $\\mathsf{{ak}} + [{ALPHA}]\\mathcal{{G}}$ | ${show(RK)}$ |',
    f'| action digest $d$ | $H_{{\\texttt{{ActionDg}}}}(\\mathsf{{cv}},\\ \\mathsf{{rk}})$ | {D_S} |',
    f'| action set | $X - {D_S}$, as ${poly_tex(A_SPEND)}$ | committed as {com(A_SPEND)} |',
    f'| tachygram set | $(X - {NF_CUR})(X - {NF_NEXT})$, as ${poly_tex(T_SPEND)}$ | committed as {com(T_SPEND)} |',
])
frag['pak-reject'] = (
    f'A prover who holds a different spend validating key ${show(AK_M)}$, together with the right $\\mathsf{{nk}}$, computes '
    f'{PK_M} in place of {PK}, and the first row fails.')

# ---------------------------------------------------------------------- outputs
OUT_V = 18
PK_C = H('carol-address', 1)
PSI_O, RCM_O = H('alice-psi', 'to-carol'), H('alice-rcm', 'to-carol')
CM_O, PAD_O = n.commit(RCM_O, PK_C, OUT_V, PSI_O), n.pad_of(RCM_O, PK_C, OUT_V, PSI_O)
RCV_O, CV_O = fresh_blind(-OUT_V, 'output')
THETA_O = H('alice-theta', 'output')
ALPHA_O = H('Tachyon-Output', THETA_O, CM_O) % Q
assert ALPHA_O not in (0, 1) and 0 not in (CM_O, PAD_O)
RK_O = mul(ALPHA_O, GEN)
D_O = digest_of(CV_O, RK_O)
A_OUT = roots([D_O])
T_OUT = roots([CM_O, PAD_O])
frag['output'] = '\n'.join([
    '| Step | Quantity | Computation | Value |', '| --- | --- | --- | --- |',
    f'| `OutputBind` | $\\mathsf{{cm}}$ | $H_{{\\texttt{{CmDerive}}}}({RCM_O},\\ {PK_C},\\ {OUT_V},\\ {PSI_O})$ | {CM_O} |',
    f'| `OutputBind` | pad | $H_{{\\texttt{{CmOutPad}}}}({RCM_O},\\ {PK_C},\\ {OUT_V},\\ {PSI_O})$ | {PAD_O} |',
    f'| `OutputBind` | $\\mathsf{{cv}}$ | $[-{OUT_V}]\\mathcal{{V}} + [{RCV_O}]\\mathcal{{R}}$ | ${show(CV_O)}$ |',
    f'| `OutputAction` | $\\alpha$ | $H_{{\\texttt{{Output}}}}({THETA_O},\\ {CM_O})$, reduced mod {Q} | {ALPHA_O} |',
    f'| `OutputAction` | $\\mathsf{{rk}}$ | $[{ALPHA_O}]\\mathcal{{G}}$ | ${show(RK_O)}$ |',
    f'| `OutputAction` | digest $d$ | $H_{{\\texttt{{ActionDg}}}}(\\mathsf{{cv}},\\ \\mathsf{{rk}})$ | {D_O} |',
])

# ----------------------------------------------------------- spans and ActionLift
A1, A2, A3 = trail[7][1], trail[7][2], trail[7][3]
M1 = roots([A1])
assert pev(M1, entry[7]) * (entry[7] - entry[7]) % S == 0
span_good = pev(M1, A1) * (A1 - entry[7]) % S
assert span_good == 0
stale = entry[6]
stale_value = pev(M1, stale) * (stale - entry[7]) % S
assert stale_value != 0
frag['action-lift'] = (
    f'Here the spend\'s actions rest on $\\mathsf{{entry}}(7) = {entry[7]}$, and the wallet plans to anchor its bundle at '
    f'$a_1 = {A1}$. The span from {entry[7]} to {A1} has the members polynomial $M(X) = X - {A1}$. The check '
    f'$M(a) \\cdot (a - \\text{{start}})$ evaluates to $({entry[7]} - {A1}) \\cdot 0 = 0$, so the lift outputs the same '
    f'sets at anchor {A1}. An anchor from before the span, such as {stale}, gives {stale_value}, and the step rejects it.')

# ----------------------------------------------------------------- ActionMerge
A_ACT = pmul(A_SPEND, A_OUT)
T_ACT = pmul(T_SPEND, T_OUT)
zm = chal(com(A_SPEND), com(A_OUT), com(A_ACT))
zt = chal(com(T_SPEND), com(T_OUT), com(T_ACT))
assert pev(A_ACT, zm) == pev(A_SPEND, zm) * pev(A_OUT, zm) % S
assert pev(T_ACT, zt) == pev(T_SPEND, zt) * pev(T_OUT, zt) % S
frag['merge'] = (
    f'Both inputs now sit at anchor {A1}, so the anchor check passes. The merged action set has the roots {D_S} and '
    f'{D_O}, and at $z = {zm}$ its check reads ${pev(A_ACT, zm)} = {pev(A_SPEND, zm)} \\cdot {pev(A_OUT, zm)}$. The merged '
    f'tachygram set has the roots {NF_CUR}, {NF_NEXT}, {CM_O} and {PAD_O}, and at $z = {zt}$ its check reads '
    f'${pev(T_ACT, zt)} = {pev(T_SPEND, zt)} \\cdot {pev(T_OUT, zt)}$. The output header is '
    f'$({com(A_ACT)},\\ {com(T_ACT)},\\ {A1})$.')

# ----------------------------------------------------------------- the fee
MAXFEE, FEE = 5, 3
BAL = VAL - OUT_V - MAXFEE
assert BAL == 2 and 0 < FEE < MAXFEE
for seed in range(100):  # a fresh opening whose commitment does not repeat an earlier point
    PSI_F, RCM_F = H('alice-psi', 'max-fee', seed), H('alice-rcm', 'max-fee', seed)
    BLIND_RAW = H('Tachyon-FeeBlind', PK, PSI_F, RCM_F)
    BLIND = BLIND_RAW % Q
    CV_MAX = cv_of(-MAXFEE, BLIND)
    if BLIND and CV_MAX is not None and CV_MAX[0] not in USED_X:
        break
assert CV_MAX[0] not in USED_X


def fee_digest(fee):
    return H('Tachyon-FeeDg', CV_MAX[0], CV_MAX[1], fee)


def change_cm(fee):
    return n.commit(RCM_F, PK, MAXFEE - fee, PSI_F)


D_F, CM_CHG = fee_digest(FEE), change_cm(FEE)
assert CM_CHG != 0
S_A, S_T = roots([D_F]), roots([CM_CHG])
A_ST, T_ST = pmul(A_ACT, S_A), pmul(T_ACT, S_T)
PUBLISHED_TG = sorted([NF_CUR, NF_NEXT, CM_O, PAD_O, CM_CHG])
assert len(set(PUBLISHED_TG)) == 2 * 2 + 1
assert roots(PUBLISHED_TG) == T_ST
frag['fee-setup'] = (
    f'Alice\'s bundle spends {VAL} and creates an output of {OUT_V}. She reserves a maximum fee of {MAXFEE}, which leaves '
    f'a value balance of ${VAL} - {OUT_V} - {MAXFEE} = {BAL}$.')
frag['fee-fuse'] = '\n'.join([
    '| Quantity | Computation | Value |', '| --- | --- | --- |',
    f'| $r$ | $H_{{\\texttt{{FeeBlind}}}}({PK},\\ {PSI_F},\\ {RCM_F}) = {BLIND_RAW}$, reduced mod {Q} | {BLIND} |',
    f'| $\\mathsf{{cv}}_\\text{{maxfee}}$ | $[-{MAXFEE}]\\mathcal{{V}} + [{BLIND}]\\mathcal{{R}}$ | ${show(CV_MAX)}$ |',
    f'| fee | chosen by the wallet, at most {MAXFEE} | {FEE} |',
    f'| fee digest | $H_{{\\texttt{{FeeDg}}}}({CV_MAX[0]},\\ {CV_MAX[1]},\\ {FEE})$ | {D_F} |',
    f'| change note value | ${MAXFEE} - {FEE}$ | {MAXFEE - FEE} |',
    f'| change commitment | $H_{{\\texttt{{CmDerive}}}}({RCM_F},\\ {PK},\\ {MAXFEE - FEE},\\ {PSI_F})$ | {CM_CHG} |',
    f'| output action set | three roots: {D_S}, {D_O}, {D_F} | committed as {com(A_ST)} |',
    f'| output tachygram set | five roots, $2N + B = 2 \\cdot 2 + 1$ | committed as {com(T_ST)} |',
])

# ------------------------------------------------------------ the binding signature
BSK = (RCV_S + RCV_O + BLIND) % Q
CV_SUM = add(add(CV_S, CV_O), CV_MAX)
BVK = add(CV_SUM, mul((-BAL) % Q, V))
assert BVK == mul(BSK, R) and BVK is not None
assert VAL - OUT_V - MAXFEE - BAL == 0


def bundle_commitment(bal, cvmax):
    actions = H('Tachyon-Actions', CV_S, RK, CV_O, RK_O)
    return H('ZTxIdTachyonHash', actions, bal, cvmax, H('Tachyon-Memo', 'memo'))


SIGHASH = H('sighash', bundle_commitment(BAL, CV_MAX))


def schnorr(sk, base, nonce_seed):
    k = 1 + H('nonce', nonce_seed) % (Q - 1)
    point = mul(k, base)
    pub = mul(sk, base)
    c = H('challenge', point, pub, SIGHASH) % Q
    return point, (k + c * sk) % Q, c


for seed in range(100):  # avoid a challenge of 0 or 1, which would hide the structure of the check
    NONCE_POINT, SIG_S, SIG_C = schnorr(BSK, R, f'binding-{seed}')
    if SIG_C > 1 and SIG_S != 0:
        break
assert SIG_C > 1
assert mul(SIG_S, R) == add(NONCE_POINT, mul(SIG_C, BVK))
for sk, pub, seed_name in ((RSK, RK, 'spend-action'), (ALPHA_O, RK_O, 'output-action')):
    point, s_val, c_val = schnorr(sk, GEN, seed_name)
    assert mul(s_val, GEN) == add(point, mul(c_val, pub))
frag['binding'] = '\n'.join([
    '| Quantity | Computation | Value |', '| --- | --- | --- |',
    f'| $\\mathsf{{bsk}}$ | ${RCV_S} + {RCV_O} + {BLIND}$ mod {Q} | {BSK} |',
    f'| $\\sum \\mathsf{{cv}}$ | ${show(CV_S)} + {show(CV_O)} + {show(CV_MAX)}$ | ${show(CV_SUM)}$ |',
    f'| $\\mathsf{{bvk}}$ | ${show(CV_SUM)} - [{BAL}]\\mathcal{{V}}$ | ${show(BVK)}$ |',
    f'| check | $[{BSK}]\\mathcal{{R}}$ | ${show(mul(BSK, R))}$ |',
])
frag['binding-sig'] = (
    f'With the stand-in sighash {SIGHASH} and nonce point ${show(NONCE_POINT)}$, the challenge is {SIG_C} and the response '
    f'is {SIG_S}, and both sides of $[s]\\mathcal{{R}} = R + [c]\\mathsf{{bvk}}$ equal ${show(mul(SIG_S, R))}$.')

wrong_bvks = {}
for claim in range(Q):
    delta = (BAL - claim) % Q
    point = add(BVK, mul(delta, V))
    if delta:
        assert point != mul(BSK, R)
    wrong_bvks[claim] = point
assert sum(1 for c, p in wrong_bvks.items() if p == mul(BSK, R)) == 1
K_LOG = log(V, R)
CHEAT_CLAIM = (BAL + 10) % Q
CHEAT_KEY = (BSK + (BAL - CHEAT_CLAIM) * K_LOG) % Q
assert mul(CHEAT_KEY, R) == wrong_bvks[CHEAT_CLAIM]
frag['binding-cheat'] = (
    f'Now suppose Alice claims a value balance of {CHEAT_CLAIM} in place of {BAL}, taking 10 more from the pool. The '
    f'validator computes $\\mathsf{{bvk}}\' = {show(wrong_bvks[CHEAT_CLAIM])}$, and the surviving term is '
    f'$[{(BAL - CHEAT_CLAIM) % Q}]\\mathcal{{V}}$. Of the {Q} possible claims in the toy field, only the true one makes '
    f'$\\mathsf{{bvk}}$ equal $[\\mathsf{{bsk}}]\\mathcal{{R}}$. The signature fails unless Alice can find the discrete '
    f'log of $\\mathsf{{bvk}}\'$ to base $\\mathcal{{R}}$. On the toy curve she can, by counting, because $\\mathcal{{V}} = '
    f'[{K_LOG}]\\mathcal{{R}}$ gives her the key {CHEAT_KEY} for the false balance. So this protection rests on the '
    f'hardness of discrete log.')

# Changing the fee.
FEE2 = 4
D_F2, CM_CHG2 = fee_digest(FEE2), change_cm(FEE2)
assert D_F2 != D_F and CM_CHG2 != CM_CHG
assert add(CV_SUM, mul((-BAL) % Q, V)) == BVK  # no fee term in either key
assert bundle_commitment(BAL, cv_of(-MAXFEE - 1, BLIND)) != bundle_commitment(BAL, CV_MAX)  # the maximum is signed
A_ST2, T_ST2 = pmul(A_ACT, roots([D_F2])), pmul(T_ACT, roots([CM_CHG2]))
assert com(A_ST2) != com(A_ST) and com(T_ST2) != com(T_ST)
frag['fee-change'] = (
    f'If the wallet raises the fee to {FEE2}, the fee digest becomes {D_F2} and the change note, now worth '
    f'{MAXFEE - FEE2}, has the commitment {CM_CHG2}. So both set commitments change, to {com(A_ST2)} and {com(T_ST2)}, and '
    f'`FeeFuse` has to run again. The sighash stays {SIGHASH}, and $\\mathsf{{bvk}}$ stays ${show(BVK)}$, so no signature '
    f'has to be made again.')
assert CHEAT_CLAIM != BAL

# The balance sheet.
assert VAL - OUT_V - (MAXFEE - FEE) == BAL + FEE
frag['balance'] = (
    f'For our bundle this gives ${VAL} - {OUT_V} - ({MAXFEE} - {FEE}) = {BAL} + {FEE} = {BAL + FEE}$, so {BAL + FEE} '
    f'zatoshi leave the pool, and the fee change note keeps {MAXFEE - FEE} inside it.')

# ---------------------------------------------------------- StampLift and consensus
M2_L, M2_R = roots([A2]), roots([A3])
M2 = pmul(M2_L, M2_R)
zs = chal(com(M2_L), com(M2_R), com(M2))
assert pev(M2, zs) == pev(M2_L, zs) * pev(M2_R, zs) % S
assert pev(M2, A1) * (A1 - A1) % S == 0
assert pev(M2, A2) == 0 and pev(M2, A3) == 0 and pev(M2, A1) != 0
frag['stamp-lift'] = (
    f'Stamps have landed since the wallet chose $a_1$, so it lifts along a span from $a_1 = {A1}$ to $a_3 = {A3}$. Two '
    f'`AnchorSpanSeed` steps and one `AnchorSpanFuse` build the span, whose members polynomial has roots {A2} and {A3}. '
    f'The stamp\'s anchor {A1} is the span\'s start, so the product $M({A1}) \\cdot 0$ vanishes although '
    f'$M({A1}) = {pev(M2, A1)}$, and the output anchor is {A3}.')

rebuilt_a = roots([digest_of(CV_S, RK), digest_of(CV_O, RK_O), H('Tachyon-FeeDg', CV_MAX[0], CV_MAX[1], FEE)])
rebuilt_t = roots(PUBLISHED_TG)
assert com(rebuilt_a) == com(A_ST) and com(rebuilt_t) == com(T_ST)
assert A3 in ACCEPTED
missing = roots([digest_of(CV_S, RK), H('Tachyon-FeeDg', CV_MAX[0], CV_MAX[1], FEE)])
assert com(missing) != com(A_ST)
frag['validate'] = '\n'.join([
    '| Validator step | Computation | Result |', '| --- | --- | --- |',
    f'| signatures | action signatures under each $\\mathsf{{rk}}$, binding under $\\mathsf{{bvk}}$ | accepted |',
    f'| arity | ${len(PUBLISHED_TG)} = 2 \\cdot 2 + 1$ | accepted |',
    f'| tachygram set | rebuild from the 5 published values | {com(rebuilt_t)}, matches the stamp |',
    f'| action set | rebuild from 2 action and 1 fee descriptors | {com(rebuilt_a)} |',
    f'| proof | verify against $({com(rebuilt_a)},\\ {com(rebuilt_t)},\\ {A3})$ | accepted, in the design |',
    f'| anchor | look up {A3} in the chain | found, in epoch 7 |',
])
frag['validate-note'] = (
    f'If a miner dropped the output\'s descriptor, the validator would rebuild the action commitment as {com(missing)} '
    f'instead of {com(A_ST)}. The header would then differ from the one the proof covers, so the proof would fail.')

# ------------------------------------------------------- the aggregator's two steps
DAVE_D = [H('dave-digest', i) for i in range(2)]
DAVE_T = [H('dave-tg', i) for i in range(3)]
A_D, T_D = roots(DAVE_D), roots(DAVE_T)
A_MERGED, T_MERGED = pmul(A_ST, A_D), pmul(T_ST, T_D)
q_a, r_a = pdivmod(A_MERGED, A_D)
q_t, r_t = pdivmod(T_MERGED, T_D)
assert q_a == A_ST and q_t == T_ST and not any(r_a) and not any(r_t)
_, r_x = pdivmod(T_MERGED, roots([H('not-in-stamp', 1)]))
assert any(r_x)
frag['aggregate'] = (
    f'Suppose an aggregator holds Dave\'s stamp with one action, which has 2 action and fee digests and 3 tachygrams, at '
    f'the same anchor {A3}. `StampMerge` multiplies the sets, which gives degrees {len(A_MERGED) - 1} and '
    f'{len(T_MERGED) - 1}, and the merged tachygram set has the commitment {com(T_MERGED)}. If a block then includes '
    f'Dave\'s transaction alone, `StampUnmerge` divides by his stamp. The quotient has remainder 0 and commitment '
    f'{com(q_t)}, which is exactly Alice\'s tachygram commitment again. Dividing by a value that was never in the stamp '
    f'leaves a nonzero remainder.')

# -------------------------------------------------------------------- step budget
from fractions import Fraction as Fr  # noqa: E402
PERM, SM = Fr(1, 7), Fr(1, 4)
work = {'OutputBind': (2, 2), 'OutputAction': (2, 1), 'SpendBind': (2, 2), 'SpendAction': (3, 1)}
rows = ['| Step | Permutations | Scalar multiplications | Share of one step |', '| --- | --- | --- | --- |']
for name, (p, s) in work.items():
    share = p * PERM + s * SM
    assert share <= 1
    rows.append(f'| `{name}` | {p} | {s} | {float(share):.2f} |')
frag['budget'] = '\n'.join(rows)
out_all = (work['OutputBind'][0] + work['OutputAction'][0], work['OutputBind'][1] + work['OutputAction'][1])
sp_all = (work['SpendBind'][0] + work['SpendAction'][0], work['SpendBind'][1] + work['SpendAction'][1])
out_share, sp_share = out_all[0] * PERM + out_all[1] * SM, sp_all[0] * PERM + sp_all[1] * SM
assert out_share > 1 and sp_share > 1
frag['budget-note'] = (
    f'Doing a spend in one step would need {sp_all[0]} permutations and {sp_all[1]} scalar multiplications, which comes to '
    f'{float(sp_share):.2f} of a step before any polynomial opening. An output would need {float(out_share):.2f}. Splitting '
    f'each action in two brings every part under 1.')

# ---------------------------------------------------------------- the whole roster
# (name, left, right, output, family, wallet, sync, aggregator), from proof-tree.md, checked against the code.
y, p_, x = 'yes', 'possible', 'no'
ROSTER = [
    ('NoteSeed', 'derive', y, x, x), ('NullifierDerive', 'derive', y, x, x), ('NullifierFuse', 'derive', y, x, x),
    ('SpendableInit', 'spendable', y, x, x), ('QrSpendableInit', 'spendable', y, x, x),
    ('UnspentBind', 'spendable', y, x, x), ('SpendableLift', 'spendable', y, x, x),
    ('SpendBind', 'action', y, x, x), ('SpendAction', 'action', y, x, x), ('OutputBind', 'action', y, x, x),
    ('OutputAction', 'action', y, x, x), ('ActionMerge', 'action', y, x, x), ('ActionLift', 'action', y, x, x),
    ('FeeFuse', 'fee', y, x, x), ('FeeSeed', 'fee', y, x, y),
    ('StampMerge', 'stamp', y, x, y), ('StampLift', 'stamp', y, p_, y), ('StampUnmerge', 'stamp', x, x, y),
    ('AnchorSpanSeed', 'span', p_, y, y), ('AnchorSpanFuse', 'span', p_, y, y),
    ('SummarySeed', 'summary', p_, y, x), ('SummaryAdvance', 'summary', p_, y, x),
    ('QrSummaryIntake', 'qr', p_, y, x), ('QrStampIntakeSeed', 'qr', p_, y, x), ('QrEmptyIntakeSeed', 'qr', p_, y, x),
    ('QrIntakeMerge', 'qr', p_, y, x), ('QrIntakeSplit', 'qr', p_, y, x), ('QrSideDescend', 'qr', p_, y, x),
    ('QrBucketSeal', 'qr', p_, y, x),
    ('EvidenceTreeLeafPair', 'tree', p_, y, x), ('EvidenceTreePairFuse', 'tree', p_, y, x),
    ('EvidenceTreeFuse', 'tree', p_, y, x), ('EvidenceTreeCap', 'tree', p_, y, x),
    ('EvidenceTreeDescend', 'tree', p_, y, x), ('EvidenceTreeOpen', 'tree', p_, y, x),
    ('QrUnspentInit', 'unspent', p_, y, x), ('UnspentFuse', 'unspent', p_, y, x), ('UnspentLift', 'unspent', p_, y, x),
]
assert len(ROSTER) == 38 and len({r[0] for r in ROSTER}) == 38
FAMILY = [
    ('derive', 'Deriving nullifiers', 'wallet', 'Section 3'),
    ('spendable', 'Holding a spendable', 'wallet', 'Sections 4 and 5'),
    ('action', 'Spends, outputs, merging', 'wallet', 'Sections 6 to 8'),
    ('fee', 'Applying the fee', 'wallet; `FeeSeed` also aggregator', 'Section 9'),
    ('stamp', 'Moving and combining stamps', 'wallet and aggregator; `StampUnmerge` aggregator only', 'Sections 11 and 12'),
    ('span', 'Anchor spans', 'sync service, aggregator; wallet possible', 'Section 8'),
    ('unspent', 'Absence segments', 'sync service; wallet possible', 'Section 5'),
    ('summary', 'Stamp summaries', 'sync service; wallet possible', '[chapter 21](./oblivious-sync.md)'),
    ('qr', 'Routing into buckets', 'sync service; wallet possible', '[chapter 21](./oblivious-sync.md)'),
    ('tree', 'Evidence trees', 'sync service; wallet possible', '[chapter 21](./oblivious-sync.md)'),
]
assert {f[0] for f in FAMILY} == {r[1] for r in ROSTER}
rows = ['| Family | Steps | Who runs them | Covered in |', '| --- | --- | --- | --- |']
for key, title, who, where in FAMILY:
    names = [r[0] for r in ROSTER if r[1] == key]
    rows.append(f'| {title} ({len(names)}) | ' + ', '.join(f'`{a}`' for a in names) + f' | {who} | {where} |')
frag['roster'] = '\n'.join(rows)
wallet_only = sum(1 for r in ROSTER if r[2] == y and r[3] == x and r[4] == x)
sync_side = sum(1 for r in ROSTER if r[3] == y)
frag['roster-count'] = (
    f'Tachyon registers 38 steps at this commit. The book\'s table gives {wallet_only} of them to a wallet alone, and it '
    f'assigns {sync_side} to the sync service, none of which reads a note, although a wallet may run those itself.')

# ------------------------------------------------------------- nodes in this one run
NODES = [
    ('NoteSeed', 'wallet'), ('NullifierDerive', 'wallet'),
    ('QrUnspentInit', 'sync service'), ('QrUnspentInit', 'sync service'), ('QrUnspentInit', 'sync service'),
    ('UnspentFuse', 'sync service'), ('UnspentLift', 'sync service'),
    ('UnspentBind', 'wallet'), ('UnspentBind', 'wallet'), ('QrSpendableInit', 'wallet'), ('SpendableLift', 'wallet'),
    ('SpendBind', 'wallet'), ('SpendAction', 'wallet'),
    ('AnchorSpanSeed', 'sync service'), ('ActionLift', 'wallet'),
    ('OutputBind', 'wallet'), ('OutputAction', 'wallet'), ('ActionMerge', 'wallet'), ('FeeFuse', 'wallet'),
    ('AnchorSpanSeed', 'sync service'), ('AnchorSpanSeed', 'sync service'), ('AnchorSpanFuse', 'sync service'),
    ('StampLift', 'wallet'),
]
wallet_nodes = sum(1 for _, w in NODES if w == 'wallet')
sync_nodes = sum(1 for _, w in NODES if w == 'sync service')
assert wallet_nodes + sync_nodes == len(NODES)
assert all(a in {r[0] for r in ROSTER} for a, _ in NODES)
frag['node-count'] = (
    f'Counting only what the graph shows, this one spend and one output take {len(NODES)} nodes, of which the wallet runs '
    f'{wallet_nodes} and the sync service {sync_nodes}. The buckets add more, on the service side, and chapter 21 '
    f'counts those. The published result is one proof, whose header a validator can rebuild.')

# ------------------------------------------------------------- the threaded fields
frag['thread'] = '\n'.join([
    '| Node | Header type | $\\mathsf{cm}$ | Epoch | Anchor |', '| --- | --- | --- | --- | --- |',
    f'| `NoteSeed` | `NoteSecret` | {CM} | | |',
    f'| `NullifierDerive` | `NoteNullifiers` | {CM} | 0 to 15 | |',
    f'| `UnspentBind` | `NoteUnspent` | {CM} | 3 to 4 | {entry[3]} to {entry[4]} |',
    f'| `QrSpendableInit` | `NoteSpendable` | {CM} | 4 | {entry[4]} |',
    f'| `UnspentBind` | `NoteUnspent` | {CM} | 4 to 7 | {entry[4]} to {entry[7]} |',
    f'| `SpendableLift` | `NoteSpendable` | {CM} | 7 | {entry[7]} |',
    f'| `SpendBind` | `SpendHeader` | {CM} | | {entry[7]} |',
    f'| `SpendAction` | `Actions` | gone | | {entry[7]} |',
    f'| `ActionLift` | `Actions` | gone | | {A1} |',
    f'| `ActionMerge` | `Actions` | gone | | {A1} |',
    f'| `FeeFuse` | `Stamp` | gone | | {A1} |',
    f'| `StampLift` | `Stamp` | gone | | {A3} |',
])

print(json.dumps(frag))
