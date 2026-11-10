"""Worked examples for notes-and-nullifiers.md. Prints fragments as JSON.

The toy curve E plays the part of Pallas, so signing keys are real toy-curve
arithmetic. Poseidon does not appear. Every hash below is a labelled stand-in:
SHA-256 of the domain tag and inputs, reduced modulo 65537. That prime is far
too small to be secure and large enough that unrelated values rarely collide,
which is what the examples need to show. Tachyon has not activated on mainnet,
and all of this describes the Tachyon repository at commit 7e50254.
"""
import hashlib
import json
from itertools import combinations

from toy_curve import G, Q, P, add, curve_points, mul, show

frag = {}
F = 65537   # the stand-in hash range
RATE = 4    # Poseidon's rate in Tachyon, and so our stand-in sponge's output count
GEN = G[0]  # plays the part of the spend authorization generator


def digest(tag, *inputs):
    return hashlib.sha256('|'.join([tag] + [str(i) for i in inputs]).encode()).digest()


def H(tag, *inputs):
    """Stand-in for a tagged one-output Poseidon hash."""
    return int.from_bytes(digest(tag, *inputs), 'big') % F


def sponge(tag, *inputs):
    """Stand-in for one permutation squeezed RATE times."""
    d = digest(tag, *inputs)
    return [int.from_bytes(d[i * 8:(i + 1) * 8], 'big') % F for i in range(RATE)]


def num(x):
    return f'{x:,}'


# ------------------------------------------------------------------ the keys
SK = 'alice-wallet-seed-7'
ASK_RAW = int.from_bytes(digest('expand', SK, 0x21), 'big') % Q
NK = H('expand', SK, 0x22)
AK_RAW = mul(ASK_RAW, GEN)
assert AK_RAW is not None and AK_RAW[1] % 2 == 1  # this seed needs normalizing
ASK = (-ASK_RAW) % Q
AK = mul(ASK, GEN)
assert AK == (AK_RAW[0], (-AK_RAW[1]) % P) and AK[1] % 2 == 0
assert AK != GEN and ASK not in (0, 1)


def payment_key(ak, nk):
    return H('Tachyon-PkDerive', ak[0], ak[1], nk)


PK = payment_key(AK, NK)
# A fresh index above sk gives an unrelated address for a second sender.
SK2 = 'alice-wallet-seed-8'
ASK2_RAW = int.from_bytes(digest('expand', SK2, 0x21), 'big') % Q
AK2_RAW = mul(ASK2_RAW, GEN)
AK2 = AK2_RAW if AK2_RAW[1] % 2 == 0 else (AK2_RAW[0], (-AK2_RAW[1]) % P)
NK2 = H('expand', SK2, 0x22)
PK2 = payment_key(AK2, NK2)
assert PK2 != PK and NK2 != NK

frag['keys'] = '\n'.join([
    '| Key | Derivation | Stand-in value |', '| --- | --- | --- |',
    f'| $\\mathsf{{ask}}$, before normalizing | expand with `0x21`, in $\\F_{{{Q}}}$ | {ASK_RAW} |',
    f'| its public point | $[{ASK_RAW}]\\mathcal{{G}}$ | ${show(AK_RAW)}$, with $y$ odd |',
    f'| $\\mathsf{{ask}}$, normalized | negated, since $y$ was odd | {ASK} |',
    f'| $\\mathsf{{ak}}$ | $[{ASK}]\\mathcal{{G}}$ | ${show(AK)}$, with $y$ even |',
    f'| $\\mathsf{{nk}}$ | expand with `0x22` | {NK} |',
])
frag['generator'] = (
    f'Our generator $\\mathcal{{G}}$ is the toy point ${show(GEN)}$, and the wallet\'s $\\mathsf{{sk}}$ is the text '
    f'`{SK}`, which stands in for 32 random bytes.')

# -------------------------------------------------------------- payment keys
frag['payment-key'] = (
    f'$$\\mathsf{{pk}} = H_{{\\texttt{{PkDerive}}}}({AK[0]},\\ {AK[1]},\\ {NK}) = {PK}.$$\n\n'
    f'For a second sender, Alice\'s wallet moves to the next index. We stand in for that index\'s $\\mathsf{{sk}}$ with the '
    f'text `{SK2}`, and the same derivations give $\\mathsf{{ak}} = {show(AK2)}$ and $\\mathsf{{nk}} = {NK2}$, so '
    f'$\\mathsf{{pk}} = {PK2}$. Nothing in the two payment keys {PK} and {PK2} shows that they belong to one wallet.')

# ---------------------------------------------------------------- the note
V = 25
PSI = H('sender-psi', 'bob-to-alice', 1)
RCM = H('sender-rcm', 'bob-to-alice', 1)


def commit(rcm, pk, v, psi):
    return H('Tachyon-CmDerive', rcm, pk, v, psi)


def pad_of(rcm, pk, v, psi):
    return H('Tachyon-CmOutPad', rcm, pk, v, psi)


CM = commit(RCM, PK, V, PSI)
PAD = pad_of(RCM, PK, V, PSI)
assert 0 not in (CM, PAD, PSI, RCM) and CM != PAD

frag['note'] = '\n'.join([
    '| Field | Value | Who knows it |', '| --- | --- | --- |',
    f'| $\\mathsf{{pk}}$ | {PK} | Alice gave it to Bob |',
    f'| $v$ | {V} | Bob and Alice |',
    f'| $\\psi$ | {PSI} | Bob and Alice |',
    f'| $\\mathsf{{rcm}}$ | {RCM} | Bob and Alice |',
])
frag['commitment'] = f'$$\\mathsf{{cm}} = H_{{\\texttt{{CmDerive}}}}({RCM},\\ {PK},\\ {V},\\ {PSI}) = {CM}.$$'
RCM_B = H('sender-rcm', 'bob-to-alice', 2)
assert commit(RCM_B, PK, V, PSI) != CM
frag['hiding'] = (
    f'Changing only $\\mathsf{{rcm}}$ to {RCM_B} gives the commitment {commit(RCM_B, PK, V, PSI)}, which looks '
    f'unrelated to {CM} although the note has the same owner, value, and $\\psi$.')

# ---------------------------------------------------- per-action randomizers
THETA = H('alice-theta', 1)
ALPHA_RAW = H('Tachyon-Spend', THETA, CM)
ALPHA = ALPHA_RAW % Q
assert ALPHA not in (0, 1)
RSK = (ASK + ALPHA) % Q
RK = add(AK, mul(ALPHA, GEN))
assert RK is not None and mul(RSK, GEN) == RK
# A Schnorr signature in the RedDSA shape, with made-up message and nonce.
NONCE = 1 + H('nonce', 1) % (Q - 1)
R = mul(NONCE, GEN)
C = H('challenge', R, RK, 'sighash') % Q
S = (NONCE + C * RSK) % Q
assert mul(S, GEN) == add(R, mul(C, RK))
THETA2 = H('alice-theta', 2)
ALPHA2 = H('Tachyon-Spend', THETA2, CM) % Q
RK2 = add(AK, mul(ALPHA2, GEN))
assert RK2 != RK and RK2 is not None

frag['rk'] = '\n'.join([
    '| Quantity | Computation | Value |', '| --- | --- | --- |',
    f'| $\\theta$ | chosen by the signer | {THETA} |',
    f'| $\\alpha$ | $H_{{\\texttt{{Spend}}}}({THETA},\\ {CM}) = {ALPHA_RAW}$, reduced mod {Q} | {ALPHA} |',
    f'| $\\mathsf{{rsk}}$ | ${ASK} + {ALPHA}$ mod {Q} | {RSK} |',
    f'| $\\mathsf{{rk}}$ | ${show(AK)} + [{ALPHA}]\\mathcal{{G}}$ | ${show(RK)}$ |',
    f'| check | $[{RSK}]\\mathcal{{G}}$ | ${show(mul(RSK, GEN))}$ |',
])
frag['signature'] = (
    f'A signature follows the Schnorr pattern. With nonce {NONCE}, the signer computes $R = [{NONCE}]\\mathcal{{G}} = '
    f'{show(R)}$, derives a challenge $c = {C}$ from a hash of $R$, $\\mathsf{{rk}}$, and the message, and returns '
    f'$s = {NONCE} + {C} \\cdot {RSK} = {S}$ modulo {Q}. The verifier checks $[s]\\mathcal{{G}} = R + [c]\\mathsf{{rk}}$, '
    f'and both sides equal ${show(mul(S, GEN))}$. The verifier never used $\\mathsf{{ak}}$.')

# Every normalized key is consistent with the published rk, under exactly one alpha.
normalized = [pt for pt in curve_points() if pt[1] % 2 == 0]
assert len(curve_points()) == 42 and len(normalized) == 21
alphas_per_key = [sum(1 for a in range(Q) if add(k, mul(a, GEN)) == RK) for k in normalized]
assert all(n == 1 for n in alphas_per_key)
# An output's rk = [alpha]G can also be any point.
assert {mul(a, GEN) for a in range(1, Q)} == set(curve_points())
frag['unlinkable'] = (
    f'We can test this exhaustively on the toy curve. Of the {len(curve_points())} points other than the identity, '
    f'{len(normalized)} have even $y$ and could be a normalized $\\mathsf{{ak}}$. For each of those {len(normalized)} '
    f'candidates, exactly one $\\alpha$ in $\\F_{{{Q}}}$ turns it into ${show(RK)}$. The published key is therefore equally '
    f'consistent with every owner, and a second action by Alice with $\\alpha = {ALPHA2}$ publishes the unrelated-looking '
    f'${show(RK2)}$.')

# --------------------------------------------------------- epoch nullifiers
MK = H('Tachyon-NfMaster', PSI, NK)
assert MK != 0


def nullifier_group(mk, w):
    assert w % RATE == 0
    return sponge('Tachyon-NfDerive', mk, w)


def nullifier(mk, e):
    w = e - e % RATE
    return nullifier_group(mk, w)[e - w]


def window(mk, start):
    assert start % RATE == 0
    out = []
    for k in range(16 // RATE):
        out += nullifier_group(mk, start + k * RATE)
    return out


CREATED, TARGET = 3, 7
nfs = {e: nullifier(MK, e) for e in range(0, 24)}
assert len(set(nfs.values())) == len(nfs) and 0 not in nfs.values()
assert window(MK, 0) == [nfs[e] for e in range(16)]
assert window(MK, 4)[:12] == [nfs[e] for e in range(4, 16)]  # overlapping windows agree


def role(e):
    if e < CREATED:
        return 'before the note existed'
    if e < TARGET:
        return 'tested for absence'
    if e <= TARGET + 1:
        return 'published by the spend'
    return 'never revealed'


frag['master-key'] = f'$$\\mathsf{{mk}} = H_{{\\texttt{{NfMaster}}}}({PSI},\\ {NK}) = {MK}.$$'
frag['nullifier-table'] = '\n'.join(
    ['| Epoch $e$ | Group start $w$ | Position $e - w$ | $\\mathsf{nf}_e$ | Role for this spend |',
     '| --- | --- | --- | --- | --- |']
    + [f'| {e} | {e - e % RATE} | {e % RATE} | {nfs[e]} | {role(e)} |' for e in range(12)])

ONE_E = TARGET
ONE_W = ONE_E - ONE_E % RATE
frag['group-example'] = (
    f'For $e = {ONE_E}$ we get $w = {ONE_E} - ({ONE_E} \\bmod {RATE}) = {ONE_W}$, so $\\mathsf{{nf}}_{ONE_E}$ is the entry at '
    f'position {ONE_E - ONE_W} of the group that starts at {ONE_W}.')
assert (TARGET + 1) % RATE == 0  # the running pair crosses a group boundary
frag['pair-crossing'] = (
    f'Our note\'s pair shows why. The value $\\mathsf{{nf}}_{TARGET}$ comes from the group at $w = {TARGET - TARGET % RATE}$, '
    f'while $\\mathsf{{nf}}_{TARGET + 1}$ comes from the group at $w = {TARGET + 1}$, so this pair needs two sponges. A spend '
    f'with target 5 would find both $\\mathsf{{nf}}_5$ and $\\mathsf{{nf}}_6$ in the group at $w = 4$.')

PSI_2 = H('sender-psi', 'carol-to-alice', 1)
MK_2 = H('Tachyon-NfMaster', PSI_2, NK)
NK_BOB = H('expand', 'bob-wallet-seed', 0x22)
MK_BOB = H('Tachyon-NfMaster', PSI, NK_BOB)
assert PSI_2 != PSI and MK_2 != MK and MK_BOB != MK and NK_BOB != NK
assert nullifier(MK_2, 7) != nfs[7] and nullifier(MK_BOB, 7) != nfs[7]
frag['two-inputs'] = (
    f'Both inputs matter. A second note to Alice with $\\psi = {PSI_2}$ has $\\mathsf{{mk}} = {MK_2}$ and '
    f'$\\mathsf{{nf}}_7 = {nullifier(MK_2, 7)}$, so her two notes do not share nullifiers. Bob knows the first note\'s $\\psi$, '
    f'but his own key {NK_BOB} gives $\\mathsf{{mk}} = {MK_BOB}$ and $\\mathsf{{nf}}_7 = {nullifier(MK_BOB, 7)}$, where the true '
    f'value is {nfs[7]}. So the sender of a note cannot watch for its spend.')

SPLIT_E = 6
floor_input = SPLIT_E // RATE
aligned_input = SPLIT_E - SPLIT_E % RATE
assert nullifier_group(MK, aligned_input)[SPLIT_E % RATE] != sponge('Tachyon-NfDerive', MK, floor_input)[SPLIT_E % RATE]
frag['group-input'] = (
    f'For $e = {SPLIT_E}$ the deep dive absorbs $\\lfloor {SPLIT_E}/{RATE} \\rfloor = {floor_input}$, while the code absorbs '
    f'$w = {aligned_input}$. In our stand-in the two choices give '
    f'{sponge("Tachyon-NfDerive", MK, floor_input)[SPLIT_E % RATE]} and {nullifier_group(MK, aligned_input)[SPLIT_E % RATE]}, '
    f'so they are different functions, although each gives every epoch one fixed value.')

# ---------------------------------------------- the epoch space and step cost
EPOCH_SIZE = 4096
EPOCH_MAX = (2 ** 32 - 1) // EPOCH_SIZE
assert EPOCH_MAX == 2 ** 20 - 1
BLOCK_SECONDS = 75
YEAR = 365.25 * 86400
frag['epoch-space'] = (
    f'The code [allows epoch indices](https://github.com/tachyon-zcash/tachyon/blob/7e502548db33845dbaacdc0efe905d1a3c45e626/'
    f'crates/tachyon/src/constants.rs#L9-L23) up to {num(EPOCH_MAX)}, since a block height has 32 bits and an epoch has '
    f'{num(EPOCH_SIZE)} blocks. At 75 seconds per block that range lasts about '
    f'{num(round((EPOCH_MAX + 1) * EPOCH_SIZE * BLOCK_SECONDS / YEAR))} years.')

# ---------------------------------------------------------------- GGM tree
def ggm_step(node, bit):
    return H('ggm-G', bit, node)


def ggm_walk(node, bits):
    for b in bits:
        node = ggm_step(node, int(b))
    return node


SEED = H('ggm-seed', NK, PSI)
leaves = {e: ggm_walk(SEED, format(e, '03b')) for e in range(8)}
assert len(set(leaves.values())) == 8
K01 = ggm_walk(SEED, '01')
assert ggm_walk(K01, '0') == leaves[2] and ggm_walk(K01, '1') == leaves[3]


def prefixes(lo, hi, bits=3):
    """The maximal subtrees covering the range [lo, hi)."""
    out, e = [], lo
    while e < hi:
        size = 1
        while e % (size * 2) == 0 and e + size * 2 <= hi and size * 2 <= 2 ** bits:
            size *= 2
        depth = bits - {1: 0, 2: 1, 4: 2, 8: 3}[size]
        out.append(format(e, f'0{bits}b')[:depth])
        e += size
    return out


assert prefixes(2, 4) == ['01']
cover = prefixes(0, 7)
assert cover == ['0', '10', '110']
worst = max(len(prefixes(a, b)) for a in range(8) for b in range(a + 1, 9))
worst_range = next((a, b) for a in range(8) for b in range(a + 1, 9) if len(prefixes(a, b)) == worst)
frag['ggm-run'] = (
    f'Take a 3-bit epoch space and the seed {SEED}, with a stand-in hash for each $G_b$. To delegate epochs 2 and 3, a wallet '
    f'hands over only the node at prefix `01`, which is $k_{{01}} = G_1(G_0({SEED})) = {K01}$. Walking one more level gives '
    f'$G_0({K01}) = {leaves[2]}$ and $G_1({K01}) = {leaves[3]}$, which are exactly the nullifiers for those epochs, and '
    f'one-way hashing keeps the holder away from all the others. The range of epochs 0 to 6 needs {len(cover)} prefixes '
    f'(`{cover[0]}`, `{cover[1]}`, `{cover[2]}`). Over all ranges in this small space the worst case needs {worst}, reached by '
    f'epochs {worst_range[0]} to {worst_range[1] - 1}, so the amount of delegated key material depends on the range.')

GATES, PERM = 2 ** 11, 288
BUDGET = GATES // PERM
assert BUDGET == 7 and BUDGET * PERM <= GATES
DEPTH = 14
DAYS_YEARS = 2 ** DEPTH / 365.25
assert 44 < DAYS_YEARS < 46
assert RATE ** BUDGET == 2 ** DEPTH
frag['step-budget'] = (
    f'A step has $2^{{11}} = {num(GATES)}$ multiplication gates, and one Poseidon permutation costs {PERM} of them, so a step fits '
    f'$\\lfloor {num(GATES)} / {PERM} \\rfloor = {BUDGET}$ permutations.')
frag['nf-cost'] = '\n'.join([
    '| Design | Permutations for one nullifier | Nullifiers per step of 7 permutations |', '| --- | --- | --- |',
    f'| GGM, binary tree of depth {DEPTH} | {DEPTH} | none, since one walk overflows a step |',
    f'| GGM, higher arity, depth {BUDGET} | {BUDGET} | 1 |',
    f'| One hash per nullifier (Attempt 3 before batching) | 1 | {BUDGET} |',
    f'| Rate-{RATE} squeeze (Attempt 3) | $1/{RATE}$ of a permutation | ${BUDGET} \\cdot {RATE} = {BUDGET * RATE}$ |',
])
frag['ggm-space'] = (
    f'A binary tree over an epoch space of $2^{{{DEPTH}}}$ days, about {DAYS_YEARS:.0f} years, has depth {DEPTH}, so one walk takes '
    f'{DEPTH} permutations and overflows a step. The analysis counts epochs as days here, unlike the code\'s {num(EPOCH_SIZE)}-block '
    f'epochs, but only the depth matters for cost. A node with four children costs one permutation, the same as a node with two, '
    f'because one rate-{RATE} permutation emits {RATE} outputs. So raising the arity shortens the walk at no extra cost per level, and '
    f'{BUDGET} levels of arity {RATE} already cover ${RATE}^{{{BUDGET}}} = {num(RATE ** BUDGET)} = 2^{{{DEPTH}}}$ leaves. '
    f'A walk of depth {BUDGET} just fits a step.')

# ------------------------------------------- what the commitment pins down
hits = {
    'nk': [x for x in range(F) if x != NK and commit(RCM, payment_key(AK, x), V, PSI) == CM],
    'psi': [x for x in range(F) if x != PSI and commit(RCM, PK, V, x) == CM],
    'v': [x for x in range(F) if x != V and commit(RCM, PK, x, PSI) == CM],
    'rcm': [x for x in range(F) if x != RCM and commit(x, PK, V, PSI) == CM],
}
TRIES = F - 1
for x in hits['nk']:
    assert nullifier(H('Tachyon-NfMaster', PSI, x), 7) != nfs[7]  # fresh nullifiers for the same cm
for x in hits['psi']:
    assert nullifier(H('Tachyon-NfMaster', x, NK), 7) != nfs[7]
assert hits['nk'], 'the running example shows a toy collision on nk'
TOTAL_HITS = sum(len(h) for h in hits.values())
ex_nk = hits['nk'][0]
ex_mk = H('Tachyon-NfMaster', PSI, ex_nk)
ex_pk = payment_key(AK, ex_nk)
assert ex_pk == PK  # this toy collision is already in the payment key
frag['cheat-table'] = '\n'.join([
    '| Field changed | Wrong values tried | Values that keep $\\mathsf{cm}$ the same | What a match would give the cheater |',
    '| --- | --- | --- | --- |',
    f'| $\\mathsf{{nk}}$ (through $\\mathsf{{pk}}$) | {num(TRIES)} | {len(hits["nk"])} | a second nullifier sequence |',
    f'| $\\psi$ | {num(TRIES)} | {len(hits["psi"])} | a second nullifier sequence |',
    f'| $v$ | {num(TRIES)} | {len(hits["v"])} | a different value for the same note |',
    f'| $\\mathsf{{rcm}}$ | {num(TRIES)} | {len(hits["rcm"])} | nothing useful, since the note is otherwise the same |',
])
frag['cheat-reading'] = (
    f'A random function into {num(F)} values should produce about one match per row. The table shows {TOTAL_HITS} matches '
    f'in total, and each of them is a real collision. With $\\mathsf{{nk}} = {ex_nk}$, for example, the payment key still comes out '
    f'as {ex_pk}, so the commitment stays {CM}, while the master key {ex_mk} yields $\\mathsf{{nf}}_7 = {nullifier(ex_mk, 7)}$ in place of '
    f'{nfs[7]}. On this toy scale a cheater could double spend.')

# ----------------------------------------------------- reusing a trapdoor
V_B = 9
RCM_2 = H('sender-rcm', 'bob-to-alice', 3)
CM_B = commit(RCM_2, PK, V_B, PSI)
assert CM_B != CM and H('Tachyon-NfMaster', PSI, NK) == MK
REF_E = 0
frag['faerie'] = (
    f'Suppose Bob sends Alice a second note with value {V_B}, a new $\\mathsf{{rcm}} = {RCM_2}$, and the same $\\psi = {PSI}$. Its '
    f'commitment {CM_B} differs from {CM}, so it looks like a separate note. Since $\\mathsf{{pk}}$ fixes the same '
    f'$\\mathsf{{nk}}$, both notes have $\\mathsf{{mk}} = {MK}$ and the same $\\mathsf{{nf}}_7 = {nfs[7]}$ at every epoch. '
    f'Once Alice spends one of them, the other can never be spent, because its nullifiers have already been published. A wallet detects '
    f'this on receipt by computing one nullifier at a fixed reference epoch for each incoming note. With reference epoch '
    f'{REF_E}, both notes give {nfs[REF_E]}, and the wallet rejects the second.')

# ----------------------------------------------------- the two-nullifier rule
def published(t, pair=True):
    return [nfs[t], nfs[t + 1]] if pair else [nfs[t]]


def judge(t1, a1, t2, a2, pair=True, window=2):
    """Which check stops the second spend, given the first was accepted in epoch a1?"""
    history = {a1: set(published(t1, pair))}
    # The exclusion proof tests each nf_j only against its own closed epoch j.
    failed_test = [j for j in range(CREATED, t2) if nfs[j] in history.get(j, set())]
    retained = set()
    for epoch in range(a2 - window + 1, a2 + 1):
        retained |= history.get(epoch, set())
    shared = [c for c in published(t2, pair) if c in retained]
    return failed_test, shared


cases = []
for t1 in range(CREATED, 10):
    for a1 in (t1, t1 + 1):
        for t2 in range(CREATED, 10):
            for a2 in (t2, t2 + 1):
                if a2 >= a1:
                    cases.append((t1, a1, t2, a2))
n_exclusion = n_window = n_both = 0
for t1, a1, t2, a2 in cases:
    # The invariant: the epoch of acceptance always holds its own nullifier.
    assert nfs[a1] in published(t1)
    failed_test, shared = judge(t1, a1, t2, a2)
    if t2 > a1:
        assert failed_test == [a1]
        n_exclusion += 1
        n_both += bool(shared)
    else:
        assert not failed_test and nfs[a1] in shared
        n_window += 1
assert all((c[2] == c[1] + 1 and c[1] == c[0] and c[3] == c[2]) == bool(c[2] > c[1] and judge(*c)[1]) for c in cases)
assert n_exclusion + n_window == len(cases) and n_exclusion and n_window and n_both

single_escapes = [c for c in cases if not any(judge(*c, pair=False))]
frag['case-count'] = (
    f'The script checks this on every pair of spends of our note, with targets from epoch {CREATED} to epoch 9 and each spend '
    f'accepted in its target epoch or the next. There are {len(cases)} such scenarios. In {n_exclusion} of them $t_2 > a_1$ and the '
    f'second proof cannot be built, and in the other {n_window} we have $t_2 \\le a_1$ and consensus finds a shared value in its '
    f'window. No scenario escapes. The two checks also overlap in {n_both} scenarios, where the first spend was accepted on time and the second '
    f'targets and lands in the very next epoch, so the window would have caught it too. Rerunning the same {len(cases)} '
    f'scenarios with a single published nullifier per spend lets {len(single_escapes)} of them through, as in the example above.')


def case_row(t1, a1, t2, a2):
    failed_test, shared = judge(t1, a1, t2, a2)
    if failed_test:
        j = failed_test[0]
        return (f'| {t1}, accepted in {a1} | {t2}, accepted in {a2} | exclusion proof | '
                f'$\\mathsf{{nf}}_{j} = {nfs[j]}$ is present in epoch {j} |')
    v = shared[0]
    e = next(k for k in nfs if nfs[k] == v)
    return (f'| {t1}, accepted in {a1} | {t2}, accepted in {a2} | window | '
            f'both publish $\\mathsf{{nf}}_{e} = {v}$ |')


rows = [c for c in cases if c[0] == TARGET and 6 <= c[2] <= 9]
frag['case-table'] = '\n'.join(
    ['| First spend: target | Second spend: target | Caught by | Reason |', '| --- | --- | --- | --- |']
    + [case_row(*c) for c in rows])

# Remove the second nullifier and walk through the failure.
fail_case = (7, 8, 8, 8)
failed_test, shared = judge(*fail_case, pair=False)
assert not failed_test and not shared
assert fail_case in single_escapes
frag['single-fail'] = (
    f'Suppose instead that a spend published only $\\mathsf{{nf}}_e$. A first spend with target 7 waits in the mempool and gets '
    f'accepted in epoch 8, so {nfs[7]} lands in epoch 8. A second spend with target 8 now tests $\\mathsf{{nf}}_7$ against epoch 7, '
    f'where it is absent, and it publishes $\\mathsf{{nf}}_8 = {nfs[8]}$, which nobody has published. Both checks pass and the note '
    f'is spent twice.')

# The window: why two epochs and not one.
assert not any(judge(7, 7, 7, 8, window=1)) and judge(7, 7, 7, 8, window=2)[1] == [nfs[7], nfs[8]]
frag['window-fail'] = (
    f'Take two spends with target 7, the first accepted in epoch 7 and the second in epoch 8. The colliding values {nfs[7]} and '
    f'{nfs[8]} entered the pool during epoch 7, so a validator that kept only the current epoch would miss them when the second '
    f'spend arrives.')

# ----------------------------------------------------------- uniform arity
N = 4
arity_rows = []
for s in range(N + 1):
    o = N - s
    bare = 2 * s + o
    assert bare - N == s and 2 * N - bare == o
    arity_rows.append(f'| {s} | {o} | {bare} | ${bare} - {N} = {s}$ | {2 * N} |')
frag['arity'] = '\n'.join(
    [f'| Spends $s$ | Outputs $o$ | Tachygrams without padding | Observer computes $s = t - n$ | Tachygrams with padding |',
     '| --- | --- | --- | --- | --- |'] + arity_rows)

# ------------------------------------------------------ one bundle's tachygrams
PSI_S2 = H('sender-psi', 'dave-to-alice', 1)
MK_S2 = H('Tachyon-NfMaster', PSI_S2, NK)
out1 = (H('sender-rcm', 'alice-to-erin'), H('erin-pk'), 30, H('sender-psi', 'alice-to-erin'))
out2 = (H('sender-rcm', 'alice-change'), PK2, 12, H('sender-psi', 'alice-change'))
chg = (H('sender-rcm', 'alice-fee'), PK2, 3, H('sender-psi', 'alice-fee'))
entries = [
    (nfs[TARGET], 'spend 1, $\\mathsf{nf}_7$'),
    (nfs[TARGET + 1], 'spend 1, $\\mathsf{nf}_8$'),
    (nullifier(MK_S2, TARGET), 'spend 2, $\\mathsf{nf}_7$'),
    (nullifier(MK_S2, TARGET + 1), 'spend 2, $\\mathsf{nf}_8$'),
    (commit(*out1), 'output 1, $\\mathsf{cm}$'),
    (pad_of(*out1), 'output 1, pad'),
    (commit(*out2), 'output 2, $\\mathsf{cm}$'),
    (pad_of(*out2), 'output 2, pad'),
    (commit(*chg), 'fee change note, $\\mathsf{cm}$'),
]
B = 1
assert len(entries) == 2 * N + B and len({e[0] for e in entries}) == len(entries)
assert all(e[0] != 0 for e in entries)
entries_sorted = sorted(entries)
frag['bundle-size'] = (
    f'Take one bundle ($B = {B}$) with $N = {N}$ actions, two of each kind. It publishes '
    f'$2 \\cdot {N} + {B} = {2 * N + B}$ tachygrams, and the stamp lists them in sorted order.')
# The pair-testing attack on the rejected design, and the same test on the real one.
bad_pad = lambda cm: H('Tachyon-CmOutPad', cm)
bad_of = {pad_of(*out1): bad_pad(commit(*out1)), pad_of(*out2): bad_pad(commit(*out2))}
frag['bundle'] = '\n'.join(
    ['| Published tachygram | If the pad were $H(\\mathsf{cm})$ | Known only to the parties involved |',
     '| --- | --- | --- |']
    + [f'| {v} | {bad_of.get(v, "same")} | {what} |' for v, what in entries_sorted])

values = [e[0] for e in entries]
pairs = [(a, b) for a in values for b in values if a != b]
assert len(pairs) == (2 * N + B) * (2 * N + B - 1)
assert not [1 for a, b in pairs if b == H('Tachyon-CmOutPad', a)]
bad_values = [bad_of.get(v, v) for v in values]
assert len(set(bad_values)) == len(bad_values)
bad_hits = [(a, b) for a in bad_values for b in bad_values if a != b and b == bad_pad(a)]
assert len(bad_hits) == 2
assert sorted(bad_hits) == sorted([(commit(*out1), bad_pad(commit(*out1))), (commit(*out2), bad_pad(commit(*out2)))])
bad_hits = [(commit(*out1), bad_pad(commit(*out1))), (commit(*out2), bad_pad(commit(*out2)))]
frag['pad-test'] = (
    f'Start with the middle column, a hypothetical design in which each output derives its pad as $H(\\mathsf{{cm}})$. '
    f'Only the two pads change, to {bad_hits[0][1]} and {bad_hits[1][1]}. An observer holding those {2 * N + B} values hashes '
    f'each one and looks for the result among the others, which takes {len(pairs)} ordered comparisons. The test finds exactly '
    f'{len(bad_hits)} matches, because $H({bad_hits[0][0]}) = {bad_hits[0][1]}$ and $H({bad_hits[1][0]}) = {bad_hits[1][1]}$, '
    f'and so the observer learns which values are commitments and how many outputs the bundle has. Now run the same '
    f'{len(pairs)} comparisons on the first column, where each pad comes from the note opening. They find no matches. To test '
    f'the real relation, the observer would need the note\'s $\\mathsf{{rcm}}$, $\\mathsf{{pk}}$, $v$, and $\\psi$.')


def f_eval(x):
    result = 1
    for v in values:
        result = result * (x - v) % F
    return result


probe = nfs[TARGET + 2]
assert f_eval(CM) != 0 and f_eval(nfs[TARGET]) == 0 and f_eval(commit(*out1)) == 0 and f_eval(probe) != 0
frag['poly-test'] = (
    f'For our bundle, working modulo {num(F)}, $f(X) = \\prod_i (X - \\mathsf{{tg}}_i)$ gives $f({commit(*out1)}) = 0$ for output '
    f'1\'s commitment and $f({nfs[TARGET]}) = 0$ for spend 1\'s $\\mathsf{{nf}}_7$. The test has no need to know which kind each '
    f'root is. The value $\\mathsf{{nf}}_9 = {probe}$ was not published, and $f({probe}) = {f_eval(probe)}$.')

print(json.dumps(frag))
