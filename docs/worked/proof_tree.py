"""Worked examples for proof-tree.md. Prints fragments as JSON.

One spend of chapter 20's note, traced through Tachyon's proof steps. The note,
its keys and its nullifiers are imported from notes_and_nullifiers.py, so they
carry the same stand-in values. Three kinds of number appear below:

- Hash outputs are chapter 20's stand-in, SHA-256 of a tag and inputs reduced
  modulo 65537. They are not Poseidon outputs.
- Set and sequence polynomials live over F_65539, a stand-in for F_p. It is the
  first prime above the hash range in which 2 has no cube root, which the
  indexed factor needs.
- Signing keys and value commitments are real arithmetic on the toy curve.

Set commitments are a stand-in as well, a hash of the coefficients, because a
polynomial over F_65539 does not fit the toy curve's scalars. Only their
determinism and binding matter here. Chapter 21 runs the Pedersen form.

No proof exists anywhere in this script. Each step's body is run natively, which
is also what the mock Ragu at revision 0725b52 does.
"""
import contextlib
import io
import json
from math import isqrt

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

CUBE_TEST = pow(NR, (S - 1) // 3, S)
assert len({pow(x, 3, 65537) for x in range(65537)}) == 65537  # cubing permutes F_65537
assert all(k % 3 != 1 or any(k % d == 0 for d in range(2, k)) for k in range(65538, S))  # S is the next prime that is 1 mod 3
frag['fields'] = (
    f'Modulo 65,537 every element is a cube, because $65537 \\equiv {65537 % 3} \\pmod 3$ and so cubing permutes the '
    f'field. The next prime congruent to 1 modulo 3 is {S:,}, and there $2^{{(p-1)/3}} = {CUBE_TEST} \\neq 1$, so 2 is '
    f'not a cube.')

CM, MK, PK, PSI, RCM, VAL, NK, AK, ASK = n.CM, n.MK, n.PK, n.PSI, n.RCM, n.V, n.NK, n.AK, n.ASK
nf = {e: n.nullifier(MK, e) for e in range(32)}
assert (CM, MK, nf[7], nf[8]) == (55697, 299, 55113, 61177)  # chapter 20's values


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
    f'the anchors after its three stamps, which are {trail[7][1]}, {trail[7][2]} and {trail[7][3]}. In the same way, the '
    f'anchor after epoch 3\'s first stamp, just before Bob\'s, is {trail[3][1]}, and the anchor after Bob\'s stamp is '
    f'{trail[3][2]}.')

# ------------------------------------------------------------------- NoteSeed
frag['note-seed'] = '\n'.join([
    '| Quantity | Computation | Value |', '| --- | --- | --- |',
    f'| witness | $v$, $\\psi$, $\\mathsf{{rcm}}$, $\\mathsf{{ak}}$, $\\mathsf{{nk}}$ | {VAL}, {PSI}, {RCM}, ${show(AK)}$, {NK} |',
    f'| $\\mathsf{{pk}}$ | $H_{{\\texttt{{PkDerive}}}}({AK[0]},\\ {AK[1]},\\ {NK})$ | {PK} |',
    f'| $\\mathsf{{mk}}$ | $H_{{\\texttt{{NfMaster}}}}({PSI},\\ {NK})$ | {MK} |',
    f'| $\\mathsf{{cm}}$ | $H_{{\\texttt{{CmDerive}}}}(\\mathsf{{rcm}},\\ \\mathsf{{pk}},\\ v,\\ \\psi) = '
    f'H_{{\\texttt{{CmDerive}}}}({RCM},\\ {PK},\\ {VAL},\\ {PSI})$ | {CM} |',
])
assert n.payment_key(AK, NK) == PK and H('Tachyon-NfMaster', PSI, NK) == MK and n.commit(RCM, PK, VAL, PSI) == CM

# -------------------------------------------------------------- NullifierDerive
rows = ['| Sponge input $w$ | $\\mathsf{nf}_w$ | $\\mathsf{nf}_{w+1}$ | $\\mathsf{nf}_{w+2}$ | $\\mathsf{nf}_{w+3}$ |',
        '| --- | --- | --- | --- | --- |']
for w in range(0, WIDTH, 4):
    group = n.nullifier_group(MK, w)
    assert group == [nf[w + i] for i in range(4)]
    rows.append('| ' + ' | '.join([str(w)] + [str(x) for x in group]) + ' |')
frag['batch'] = '\n'.join(rows)

# The factor, its irreducibility, and why a linear factor would not do.
F3 = factor(3, nf[3])
assert all(pev(F3, x) != 0 for x in range(S))
frag['factor'] = (
    f'For epoch 3 the member is $\\mathsf{{nf}}_3 = {nf[3]}$ and $i + 1 = 4$, so working modulo {S:,},\n\n'
    f'$$F_{{3,\\,{nf[3]}}}(X) = ({nf[3]} + 4X)^3 - 2 = {poly_tex(F3)}.$$\n\n'
    f'Trying all {S:,} field elements finds no root, so this cubic has no linear factor, and a cubic with no linear '
    f'factor is irreducible.')
BOUND = isqrt(S // 3)
assert BOUND * BOUND <= S / 3 < (BOUND + 1) ** 2 and 2 * WIDTH < BOUND
frag['factor-bound'] = (
    f'On our field that bound is $\\lfloor\\sqrt{{{S}/3}}\\rfloor = {BOUND}$, so $i + 1$ must stay below {BOUND}. The '
    f'epochs in this chapter run from 0 to {2 * WIDTH - 1}, well inside it.')

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
    f'The batch polynomial has degree $3 \\cdot {WIDTH} = {3 * WIDTH}$, and its stand-in commitment is {COM_G0}. The challenge '
    f'derived from that commitment is $z = {z}$. The opening gives $N({z}) = {pev(G0, z)}$, and the step gets the same '
    f'value by evaluating the {WIDTH} factors directly from the sponge outputs. Suppose a prover commits instead to a '
    f'polynomial with the member at epoch 5 replaced by {wrong[5][1]}. Testing every challenge shows that this false '
    f'polynomial agrees with the true product at {len(passing)} of the {S:,} points, which is within the degree bound of '
    f'{3 * WIDTH}.')

# NullifierFuse
W2 = [(e, nf[e]) for e in range(WIDTH, 2 * WIDTH)]
G1 = seq(W2)
GM = pmul(G0, G1)
zf = chal(com(G0), com(G1), com(GM))
assert pev(GM, zf) == pev(G0, zf) * pev(G1, zf) % S
LAST0 = WIDTH - 1                 # NoteNullifiers stores an inclusive last epoch
OVERLAP = WIDTH - 4               # the next group-aligned start that overlaps
assert OVERLAP % 4 == 0 and OVERLAP != LAST0 + 1
frag['nullifier-fuse'] = (
    f'The first batch covers epochs 0 to {LAST0}, both included. A second batch starting at epoch {WIDTH} passes the '
    f'contiguity check, since ${WIDTH} = {LAST0} + 1$. At the challenge $z = {zf}$ the product check reads '
    f'${pev(GM, zf)} = {pev(G0, zf)} \\cdot {pev(G1, zf)}$ modulo {S:,}. A batch starting at epoch {OVERLAP} would also be '
    f'group-aligned, but it would repeat four epochs, and the check rejects it because ${OVERLAP} \\neq {LAST0} + 1$.')

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
    f'that the joined $\\Delta$ is the product of the two inputs\' polynomials at $z = {zu}$, where it reads ${pev(L, zu)} = {pev(elapsed[4], zu)} \\cdot '
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
COMP_EPOCHS = [e for e in range(WIDTH) if e not in (4, 5, 6)]
assert comp456 == seq([(e, nf[e]) for e in COMP_EPOCHS])
frag['unspent-bind'] = (
    f'For the segment covering epochs 4 to 6, the batch polynomial $N$ has degree {len(G0) - 1} and the segment\'s '
    f'$\\Delta$ has degree {len(E456) - 1}. Dividing leaves remainder 0 and a complement $C$ of degree '
    f'{len(comp456) - 1}, which is the product of the {len(COMP_EPOCHS)} factors for epochs 0 to 3 and 7 to 15. The step '
    f'checks $N = C \\cdot \\Delta$ at a challenge $z = {zb}$, where it reads ${pev(G0, zb)} = {pev(comp456, zb)} \\cdot '
    f'{pev(E456, zb)}$, and outputs {tup(un456)}, whose first entry is $\\mathsf{{cm}}$. The segment for epoch 3 binds '
    f'the same way, with a complement of degree {len(comp3) - 1}, and gives {tup(un3)}.')

# --------------------------------------------------------------- SpendableLift
sp0 = (CM, 4, entry[4])
assert un3[3] == 4 and un3[4] == entry[4] and pev(contents[3], CM) == 0
sp1 = (CM, un456[3], un456[4])
assert un456[0] == sp0[0] and un456[2] == sp0[1] and un456[1] == sp0[2]
frag['qr-spendable-init'] = (
    f'For our note, the opening of epoch 3\'s bucket at {CM} gives 0, and the bound segment for epoch 3 from Section 4 has '
    f'the same extent as the bucket, running from {entry[3]} to {entry[4]}. So the step emits '
    f'$({sp0[0]},\\ {sp0[1]},\\ {sp0[2]})$, which rests on the entry anchor of epoch 4.')
# What QrSpendableInit's epoch-3 test catches that no later segment does.
EARLY = roots([t for s_ in stamps[3] for t in s_] + [nf[3], nf[4]])   # epoch 3 with an earlier spend of the note
assert pev(EARLY, nf[3]) == 0 and pev(contents[4], nf[4]) != 0
assert not {nf[3], nf[4]} & {nf[7], nf[8]}
frag['missed-spend'] = (
    f'Suppose Alice had already spent the note in a later stamp of epoch 3. That spend would have published '
    f'$\\mathsf{{nf}}_3 = {nf[3]}$ and $\\mathsf{{nf}}_4 = {nf[4]}$, and both values would sit in epoch 3\'s data. Now '
    f'follow a second spend at epoch 7. The segment for epoch 4 tests {nf[4]} against epoch 4\'s bucket only, where the '
    f'opening is {pev(contents[4], nf[4])}, so it reports the value absent, and it is right, because the value went into '
    f'epoch 3. The segments for epochs 5 and 6 test values that nobody published. The second spend publishes {nf[7]} and '
    f'{nf[8]}, which match neither earlier value, and the consensus window at epoch 7 holds only epochs 6 and 7 anyway. '
    f'Every one of these checks passes. The only test that finds the first spend is {nf[3]} against epoch 3 itself, where the opening '
    f'of epoch 3\'s data, with that spend included, gives {pev(EARLY, nf[3])}.')
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
    f'Recall the second note from [chapter 20](./notes-and-nullifiers.md#_9-reusing-a-trapdoor) with the same $\\psi$. '
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
        if blind and blind not in (v % Q, -v % Q) and point is not None and point[0] not in USED_X:
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
    f'| $\\mathsf{{cv}}$ | $[v]\\mathcal{{V}} + [\\mathsf{{rcv}}]\\mathcal{{R}}$ with $v = {VAL}$ and a fresh '
    f'$\\mathsf{{rcv}} = {RCV_S}$, so $[{VAL}]\\mathcal{{V}} + [{RCV_S}]\\mathcal{{R}}$ | ${show(CV_S)}$ |',
])
frag['value-gens'] = (
    f'On the toy curve we take $\\mathcal{{V}} = {show(V)}$ and $\\mathcal{{R}} = {show(R)}$. This chapter is the first '
    f'to commit a value, so this pair is the shared toy pair for value commitments, and later chapters reuse it.')


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
    f'| $\\alpha$ | $H_{{\\texttt{{Spend}}}}(\\theta,\\ \\mathsf{{cm}}) = H_{{\\texttt{{Spend}}}}({THETA},\\ {CM})$, reduced mod {Q} | {ALPHA} |',
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
    f'| `OutputBind` | witness | $\\mathsf{{pk}}_\\text{{Carol}}$, $v$, $\\psi$, $\\mathsf{{rcm}}$, $\\mathsf{{rcv}}$ | '
    f'{PK_C}, {OUT_V}, {PSI_O}, {RCM_O}, {RCV_O} |',
    f'| `OutputBind` | $\\mathsf{{cm}}$ | $H_{{\\texttt{{CmDerive}}}}(\\mathsf{{rcm}},\\ \\mathsf{{pk}}_\\text{{Carol}},\\ v,\\ \\psi) = '
    f'H_{{\\texttt{{CmDerive}}}}({RCM_O},\\ {PK_C},\\ {OUT_V},\\ {PSI_O})$ | {CM_O} |',
    f'| `OutputBind` | pad | $H_{{\\texttt{{CmOutPad}}}}$ on the same four inputs in the same order | {PAD_O} |',
    f'| `OutputBind` | $\\mathsf{{cv}}$ | $[-v]\\mathcal{{V}} + [\\mathsf{{rcv}}]\\mathcal{{R}} = [-{OUT_V}]\\mathcal{{V}} + [{RCV_O}]\\mathcal{{R}}$ | ${show(CV_O)}$ |',
    f'| `OutputAction` | witness | $\\theta$ | {THETA_O} |',
    f'| `OutputAction` | $\\alpha$ | $H_{{\\texttt{{Output}}}}(\\theta,\\ \\mathsf{{cm}}) = H_{{\\texttt{{Output}}}}({THETA_O},\\ {CM_O})$, reduced mod {Q} | {ALPHA_O} |',
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
    f'Here the spend\'s actions rest on the entry anchor of epoch 7, {entry[7]}, and the wallet plans to anchor its bundle at '
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
    # Keep the sum and bvk distinct from every earlier point, and the blind distinct from the values.
    BVK_TRY = mul((RCV_S + RCV_O + BLIND) % Q, R)
    SUM_TRY = add(add(CV_S, CV_O), CV_MAX) if CV_MAX is not None else None
    if BLIND and BLIND not in (VAL % Q, OUT_V, MAXFEE) and CV_MAX is not None and CV_MAX[0] not in USED_X \
            and BVK_TRY is not None and SUM_TRY is not None \
            and len({BVK_TRY[0], SUM_TRY[0], CV_MAX[0]}) == 3 and not {BVK_TRY[0], SUM_TRY[0]} & USED_X:
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
    f'a value balance of $v^{{\\mathsf{{bal}}}} = {VAL} - {OUT_V} - {MAXFEE} = {BAL}$. We let those {BAL} zatoshi leave the '
    f'shielded pool, for example to a transparent output in the same transaction. That is a choice made for the '
    f'example, and a balance of zero would work the same way. The max fee note has the opening '
    f'$(\\mathsf{{pk}}, \\mathsf{{maxfee}}, \\psi, \\mathsf{{rcm}}) = ({PK},\\ {MAXFEE},\\ {PSI_F},\\ {RCM_F})$. Its '
    f'$\\mathsf{{pk}}$ is Alice\'s own payment key, so the change note that inherits it returns the unused fee to her.')
frag['fee-fuse'] = '\n'.join([
    '| Quantity | Computation | Value |', '| --- | --- | --- |',
    f'| $r$ | $H_{{\\texttt{{FeeBlind}}}}({PK},\\ {PSI_F},\\ {RCM_F}) = {BLIND_RAW}$, reduced mod {Q} | {BLIND} |',
    f'| $\\mathsf{{cv}}_\\text{{maxfee}}$ | $[-{MAXFEE}]\\mathcal{{V}} + [{BLIND}]\\mathcal{{R}}$ | ${show(CV_MAX)}$ |',
    f'| fee | chosen by the wallet, at most {MAXFEE} | {FEE} |',
    f'| fee digest | $H_{{\\texttt{{FeeDg}}}}({CV_MAX[0]},\\ {CV_MAX[1]},\\ {FEE})$ | {D_F} |',
    f'| change note value | ${MAXFEE} - {FEE}$ | {MAXFEE - FEE} |',
    f'| change commitment | $H_{{\\texttt{{CmDerive}}}}({RCM_F},\\ {PK},\\ {MAXFEE - FEE},\\ {PSI_F})$ | {CM_CHG} |',
    f'| output action set | three roots: {D_S}, {D_O}, {D_F} | committed as {com(A_ST)} |',
    f'| output tachygram set | five roots, two per action and the change commitment | committed as {com(T_ST)} |',
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
COEF_V = [VAL, -OUT_V, -MAXFEE, -BAL]
assert sum(COEF_V) == 0
frag['binding-cancel'] = (
    f'In Alice\'s bundle the $\\mathcal{{V}}$ coefficients are {VAL} from the spend, $-{OUT_V}$ from the output, '
    f'$-{MAXFEE}$ from $\\mathsf{{cv}}_\\text{{maxfee}}$, and $-{BAL}$ from subtracting the value balance, and '
    f'${VAL} - {OUT_V} - {MAXFEE} - {BAL} = {sum(COEF_V)}$. The $\\mathcal{{R}}$ coefficients are the three blinds, so '
    f'collecting terms gives $\\mathsf{{bvk}} = [{sum(COEF_V)}]\\mathcal{{V}} + [{RCV_S} + {RCV_O} + {BLIND}]\\mathcal{{R}}$.')
frag['binding'] = (
    f'For Alice\'s bundle the validator adds $\\mathsf{{cv}}$ of the spend, $\\mathsf{{cv}}$ of the output, and '
    f'$\\mathsf{{cv}}_\\text{{maxfee}}$, which gives ${show(CV_SUM)}$, and subtracts $[{BAL}]\\mathcal{{V}}$ to reach '
    f'$\\mathsf{{bvk}} = {show(BVK)}$. The planner\'s key is $\\mathsf{{bsk}} = {RCV_S} + {RCV_O} + {BLIND} = {BSK}$ '
    f'modulo {Q}, and $[{BSK}]\\mathcal{{R}} = {show(mul(BSK, R))}$, so the two agree.')

# The cheat on the balance is chapter 24's example; here we only check that it fails.
for claim in range(Q):
    if (BAL - claim) % Q:
        assert add(BVK, mul((BAL - claim) % Q, V)) != mul(BSK, R)

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
    f'`FeeFuse` has to run again.')
assert VAL - OUT_V - (MAXFEE - FEE) == BAL + FEE

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
    f'| tachygram count | ${len(PUBLISHED_TG)} = 2 \\cdot 2 + 1$ for 2 actions | accepted |',
    f'| tachygram set | rebuild from the 5 published values | {com(rebuilt_t)}, matches the stamp |',
    f'| action set | hash the 2 action descriptors and the fee descriptor, rebuild | {com(rebuilt_a)}, matches the stamp |',
    f'| proof | verify against $({com(rebuilt_a)},\\ {com(rebuilt_t)},\\ {A3})$ | accepted, in the design |',
    f'| anchor | look up {A3} in the chain | found, in epoch 7 |',
])
frag['validate-note'] = (
    f'If a miner dropped the output\'s descriptor, the validator would rebuild the action commitment as {com(missing)} '
    f'instead of {com(A_ST)}. The header would then differ from the one the proof covers, so the proof would fail.')

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
ob = work['OutputBind']
frag['budget-note'] = (
    f'Each share adds a seventh per permutation and a quarter per scalar multiplication, so for `OutputBind` it is '
    f'${ob[0]} \\cdot \\tfrac{{1}}{{7}} + {ob[1]} \\cdot \\tfrac{{1}}{{4}} \\approx {float(ob[0] * PERM + ob[1] * SM):.2f}$. '
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
    ('stamp', 'Moving and combining stamps', 'wallet and aggregator; `StampLift` also possible for the sync service; `StampUnmerge` aggregator only', 'Sections 11 and 12'),
    ('span', 'Anchor spans', 'sync service, aggregator; wallet possible', 'Section 8'),
    ('unspent', 'Absence segments', 'sync service; wallet possible', 'Section 4'),
    ('summary', 'Stamp summaries', 'sync service; wallet possible', 'named only here; [chapter 22](./oblivious-sync.md) treats a run of stamps as one intake'),
    ('qr', 'Routing into buckets', 'sync service; wallet possible', '[chapter 22](./oblivious-sync.md)'),
    ('tree', 'Evidence trees', 'sync service; wallet possible', '[chapter 22](./oblivious-sync.md)'),
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
    f'{wallet_nodes} and the sync service {sync_nodes}. The buckets add more, on the service side, and chapter 22 '
    f'describes the steps that build them. The published result is one proof, whose header a validator can rebuild.')

# ------------------------------------------------------------- the threaded fields
frag['thread'] = '\n'.join([
    '| Node | Header type | $\\mathsf{cm}$ | Epoch | Anchor |', '| --- | --- | --- | --- | --- |',
    f'| `NoteSeed` | `NoteSecret` | {CM} | | |',
    f'| `NullifierDerive` | `NoteNullifiers` | {CM} | $[0, {LAST0}]$ | |',
    f'| `UnspentBind` | `NoteUnspent` | {CM} | $[3, 4)$ | {entry[3]} to {entry[4]} |',
    f'| `QrSpendableInit` | `NoteSpendable` | {CM} | 4 | {entry[4]} |',
    f'| `UnspentBind` | `NoteUnspent` | {CM} | $[4, 7)$ | {entry[4]} to {entry[7]} |',
    f'| `SpendableLift` | `NoteSpendable` | {CM} | 7 | {entry[7]} |',
    f'| `SpendBind` | `SpendHeader` | {CM} | | {entry[7]} |',
    f'| `SpendAction` | `Actions` | gone | | {entry[7]} |',
    f'| `ActionLift` | `Actions` | gone | | {A1} |',
    f'| `ActionMerge` | `Actions` | gone | | {A1} |',
    f'| `FeeFuse` | `Stamp` | gone | | {A1} |',
    f'| `StampLift` | `Stamp` | gone | | {A3} |',
])

print(json.dumps(frag))
