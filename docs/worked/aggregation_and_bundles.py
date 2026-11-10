"""Worked example for aggregation-and-bundles.md. Prints fragments as JSON.

The bundles here follow the shapes in pcd-intro.md Section 11: an innocent
aggregate A and autonomes X, Y and Z. Everything Tachyon computes with Poseidon
uses a stand-in, SHA-256 reduced modulo 43, so that digests and tachygrams can be
roots of polynomials over F_43 as in pool-state.md. BLAKE2b digests use real
BLAKE2b-256 with the real personalizations, over toy byte encodings. The proof is
not modelled: a "proof" records the header it was made for, and verifying compares
headers. SALT was chosen so that the stand-in hash has no accidental collisions
among the values the chapter uses. The action and fee digests hash value
commitments, so they take a second salt, DIGEST_SALT, chosen the same way for the
value commitment generators V and R that proof-tree.md fixes.
"""
import hashlib
import itertools
import json

from toy_curve import G, H, P, Q, U, add, curve_points, msm, mul, show

SALT = 13726025
DIGEST_SALT = 478
frag = {}
ZERO = None


# ---- stand-in hash and small helpers ------------------------------------------
def h(tag, *inputs):
    salt = DIGEST_SALT if tag in ('ActionDg', 'FeeDg') else SALT
    data = f'{salt}|{tag}|' + '|'.join(str(i) for i in inputs)
    return int.from_bytes(hashlib.sha256(data.encode()).digest(), 'big') % Q


def neg(a):
    return None if a is None else (a[0], -a[1] % P)


def sub(a, c):
    return add(a, neg(c))


def blake(person, *parts):
    state = hashlib.blake2b(digest_size=32, person=person)
    for part in parts:
        state.update(part)
    return state.digest()


def short(b):
    return f'`{b.hex()[:8]}`'


def pt32(a):
    assert a is not None
    return bytes([a[0], a[1]]).ljust(32, b'\0')


def fe32(x):
    return bytes([x % Q]).ljust(32, b'\0')


def le64(x):
    return x.to_bytes(8, 'little')


def i64(x):
    return x.to_bytes(8, 'little', signed=True)


# ---- polynomials over F_43, lowest degree first --------------------------------
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


def peval(a, x):
    out = 0
    for c in reversed(a):
        out = (out * x + c) % Q
    return out


def pdivmod(a, b):
    a = list(a)
    quotient = [0] * max(len(a) - len(b) + 1, 1)
    inv = pow(b[-1], -1, Q)
    for i in range(len(a) - len(b), -1, -1):
        c = a[i + len(b) - 1] * inv % Q
        quotient[i] = c
        for j, y in enumerate(b):
            a[i + j] = (a[i + j] - c * y) % Q
    remainder = a[:len(b) - 1]
    while remainder and remainder[-1] == 0:
        remainder.pop()
    return quotient, remainder


_used = {a[0] for a in G} | {H[0], U[0]}
EXTRA = [a for a in curve_points() if a[0] not in _used and a[1] < 16]
GENS = list(G)
for a in EXTRA:
    if a[0] not in {g[0] for g in GENS}:
        GENS.append(a)
assert len(GENS) >= 13


def commit(poly):
    assert len(poly) <= len(GENS)
    return msm(poly, GENS[:len(poly)])


# ---- value commitments ---------------------------------------------------------
VV, RR = G[1], G[2]   # the shared value commitment pair from proof-tree.md
SIG_G = (1, 2)   # the spend authorization generator from notes-and-nullifiers.md
assert SIG_G in curve_points() and VV != RR and VV[0] != RR[0]
frag['generators'] = (
    f'We use the toy value commitment generators $\\mathcal{{V}} = {show(VV)}$ and $\\mathcal{{R}} = {show(RR)}$ '
    f'that [chapter 23](./proof-tree.md#_6-spending) fixed, and values and blinds are scalars in $\\F_{{{Q}}}$.'
)


def cv_of(v, blind):
    return add(mul(v % Q, VV), mul(blind, RR))


def schnorr(sk, gen, msg):
    pub = mul(sk, gen)
    k = h('nonce', sk, msg.hex()) or 1
    big_r = mul(k, gen)
    c = h('chal', big_r, pub, msg.hex())
    return big_r, (k + c * sk) % Q, c


def schnorr_ok(sig, pub, gen, msg):
    big_r, s, _ = sig
    c = h('chal', big_r, pub, msg.hex())
    return mul(s, gen) == add(big_r, mul(c, pub))


def sig_bytes(sig):
    return pt32(sig[0]) + fe32(sig[1])


# ---- bundles -------------------------------------------------------------------
class Bundle:
    def __init__(self, name, spends, outputs, maxfee, memo=b''):
        self.name, self.spends, self.outputs, self.maxfee, self.memo = name, spends, outputs, maxfee, memo
        self.pk = h('Pk', name)
        self.psi = h('Psi', name) or 1
        self.rcm = h('Rcm', name) or 1
        self.r = h('FeeBlind', self.pk, self.psi, self.rcm)
        assert self.r != 0
        self.cvmax = cv_of(-maxfee, self.r)
        assert self.cvmax is not None
        self.actions = []
        self.spend_tgs = []
        for i, v in enumerate(spends):
            rcv = h('Rcv', name, 's', i)
            assert rcv != 0
            rk = mul(h('Rsk', name, 's', i) or 1, SIG_G)
            self.actions.append(dict(kind='spend', v=v, rcv=rcv, cv=cv_of(v, rcv), rk=rk))
        for i, v in enumerate(outputs):
            rcv = h('Rcv', name, 'o', i)
            assert rcv != 0
            rk = mul(h('Rsk', name, 'o', i) or 1, SIG_G)
            self.actions.append(dict(kind='output', v=-v, rcv=rcv, cv=cv_of(-v, rcv), rk=rk))
        self.balance = sum(spends) - sum(outputs) - maxfee
        self.bsk = (sum(a['rcv'] for a in self.actions) + self.r) % Q

    def bvk(self, balance=None):
        balance = self.balance if balance is None else balance
        out = self.cvmax
        for a in self.actions:
            out = add(out, a['cv'])
        return sub(out, mul(balance % Q, VV))

    def desc_bytes(self):
        return [pt32(a['cv']) + pt32(a['rk']) for a in self.actions]

    def digests(self):
        return [h('ActionDg', *a['cv'], *a['rk']) for a in self.actions]

    def fee_entry(self, fee):
        return pt32(self.cvmax) + le64(fee)

    def fee_digest(self, fee):
        return h('FeeDg', *self.cvmax, fee)

    def change_cm(self, fee):
        return h('CmDerive', self.rcm, self.pk, self.maxfee - fee, self.psi)

    def action_tgs(self, spend_key=None):
        out = []
        for i, a in enumerate(self.actions):
            if a['kind'] == 'spend':
                mk = h('NfMaster', spend_key or self.name, i)
                out += [h('NfDerive', mk, 7), h('NfDerive', mk, 8)]
            else:
                out += [h('CmDerive', self.name, 'cm', i), h('CmOutPad', self.name, 'pad', i)]
        return out

    def commitment(self, memo=None):
        memo = self.memo if memo is None else memo
        return blake(b'ZTxIdTachyonHash',
                     blake(b'Tachyon-Actions', *self.desc_bytes()),
                     i64(self.balance),
                     pt32(self.cvmax),
                     blake(b'Tachyon-Memo', memo))

    def sign_all(self):
        msg = self.commitment()
        self.action_sigs = [schnorr(h('Rsk', self.name, a['kind'][0], i) or 1, SIG_G, msg)
                            for a, i in zip(self.actions, list(range(len(self.spends))) + list(range(len(self.outputs))))]
        self.binding_sig = schnorr(self.bsk, RR, msg)


class Stamp:
    """A stamp, with the sets it covers written out and the header its proof is for."""
    counter = 0

    def __init__(self, digests, tgs, descs, fees, fee, anchor=17):
        self.digests, self.tgs = list(digests), list(tgs)
        self.descs, self.fees = sorted(descs), sorted(fees)
        self.fee, self.anchor = fee, anchor
        self.apoly, self.tpoly = roots_poly(self.digests), roots_poly(self.tgs)
        self.header = (commit(self.apoly), commit(self.tpoly), anchor)
        Stamp.counter += 1
        self.proof = blake(b'toy-proof', repr(self.header).encode(), bytes([Stamp.counter]))

    def coverage(self):
        return coverage(self.descs, self.fees)

    def data_digest(self):
        return blake(b'Tachyon-Stamp', blake(b'Tachyon-Proof', self.proof), fe32(self.anchor),
                     pt32(self.header[1]), *[fe32(t) for t in sorted(self.tgs)])


def coverage(descs, fees):
    return blake(b'Tachyon-Coverage',
                 blake(b'Tachyon-Actions', *sorted(descs)),
                 blake(b'Tachyon-Fees', *sorted(fees)))


def stamp_of(b, fee):
    assert 0 <= fee <= b.maxfee
    return Stamp(b.digests() + [b.fee_digest(fee)], b.action_tgs() + [b.change_cm(fee)],
                 b.desc_bytes(), [b.fee_entry(fee)], fee)


def merge(left, right):
    assert left.anchor == right.anchor
    assert not set(left.tgs) & set(right.tgs)
    out = Stamp(left.digests + right.digests, left.tgs + right.tgs,
                left.descs + right.descs, left.fees + right.fees, left.fee, left.anchor)
    assert out.apoly == pmul(left.apoly, right.apoly)
    assert out.tpoly == pmul(left.tpoly, right.tpoly)
    return out


def unmerge(dividend, divisor):
    aq, ar = pdivmod(dividend.apoly, divisor.apoly)
    tq, tr = pdivmod(dividend.tpoly, divisor.tpoly)
    assert not ar and not tr
    digests = list(dividend.digests)
    for d in divisor.digests:
        digests.remove(d)
    tgs = list(dividend.tgs)
    for t in divisor.tgs:
        tgs.remove(t)
    descs = [d for d in dividend.descs if d not in divisor.descs]
    fees = [f for f in dividend.fees if f not in divisor.fees]
    out = Stamp(digests, tgs, descs, fees, dividend.fee, dividend.anchor)
    assert out.apoly == aq and out.tpoly == tq
    return out


def auth_digest(state_byte, b, stamp_state):
    return blake(b'ZTxAuthTachyHash', bytes([state_byte]),
                 *[sig_bytes(s) for s in b.action_sigs], sig_bytes(b.binding_sig), stamp_state)


def stamped_auth(b, stamp):
    assert len(le64(stamp.fee) + stamp.coverage() + stamp.data_digest()) == 72
    return auth_digest(1, b, le64(stamp.fee) + stamp.coverage() + stamp.data_digest())


def stripped_auth(b, fee, aggregate_id):
    assert len(le64(fee) + aggregate_id) == 72
    return auth_digest(2, b, le64(fee) + aggregate_id)


def wtxid(b, auth):
    return b.commitment() + auth


X = Bundle('X', [25], [], 5)
Y = Bundle('Y', [30], [21], 6, memo=b'first contact')
Z = Bundle('Z', [], [9], 3)
A = Bundle('A', [], [], 0)
XC = Bundle('Xc', [25], [], 5)      # a conflicting spend of X's note
T = Bundle('T', [], [14], 2)        # a receiver outside the working stamp
Z2 = Bundle('Z2', [], [11], 3)      # same shape as Z, different content
B_NEW = Bundle('B', [], [8], 2)     # a new bundle of the aggregator's own
FEE = {'X': 5, 'Y': 4, 'Z': 2, 'A': 0, 'T': 1, 'Z2': 2, 'B': 1, 'Xc': 5}
for _b in (X, Y, Z, A, XC, T, Z2, B_NEW):
    _b.sign_all()

# Every value the chapter compares has to be distinct under the stand-in hash.
_main_tgs = (A.action_tgs() + [A.change_cm(0)] + X.action_tgs() + [X.change_cm(5)]
             + Y.action_tgs() + [Y.change_cm(4)] + Z.action_tgs() + [Z.change_cm(2)])
assert len(set(_main_tgs)) == len(_main_tgs) == 12 and 0 not in _main_tgs
_variant_tgs = [Y.change_cm(f) for f in (0, 3, 5, 6)] + [X.change_cm(4)]
assert len(set(_variant_tgs)) == 5 and not set(_variant_tgs) & set(_main_tgs)
for _o in (T, B_NEW):
    _o_tgs = _o.action_tgs() + [_o.change_cm(FEE[_o.name])]
    assert len(set(_o_tgs)) == 3 and not set(_o_tgs) & set(_main_tgs) and 0 not in _o_tgs
_main_digests = (A.digests() + [A.fee_digest(0)] + X.digests() + [X.fee_digest(5)]
                 + Y.digests() + [Y.fee_digest(4)] + Z.digests() + [Z.fee_digest(2)])
assert len(set(_main_digests)) == len(_main_digests) == 8 and 0 not in _main_digests
_variant_digests = [Y.fee_digest(f) for f in (0, 3, 5, 6)] + [X.fee_digest(4)]
assert len(set(_variant_digests)) == 5 and not set(_variant_digests) & set(_main_digests)
for _o in (T, Z2, B_NEW):
    _o_digests = _o.digests() + [_o.fee_digest(FEE[_o.name])]
    assert len(set(_o_digests)) == 2 and not set(_o_digests) & set(_main_digests) and 0 not in _o_digests

# Conflicting spend: same nullifier pair as X, different descriptor and fee note.
_xc_tgs = X.action_tgs() + [XC.change_cm(5)]
assert XC.change_cm(5) not in _main_tgs
assert XC.digests()[0] not in _main_digests and XC.fee_digest(5) not in _main_digests


# ---- sizes ---------------------------------------------------------------------
PROOF = 23_000   # the mock's PROOF_SIZE_COMPRESSED at Ragu 0725b52


def compactsize(n):
    return 1 if n < 253 else 3 if n < 2**16 else 5


def body_size(n, memo=0):
    return 8 + compactsize(n) + 64 * n + 32 + 64 * n + 64 + compactsize(memo) + memo


def stamped_size(n, tgs, memo=0):
    return 1 + body_size(n, memo) + 8 + 32 + 32 + 32 + compactsize(tgs) + 32 * tgs + PROOF


def stripped_size(n, memo=0):
    return 1 + body_size(n, memo) + 8 + 64


assert stripped_size(0) == 1 + 8 + 1 + 32 + 64 + 1 + 72
sep = stamped_size(1, 3) + stamped_size(2, 5) + stamped_size(1, 3)
agg = stamped_size(0, 12) + stripped_size(1) + stripped_size(2) + stripped_size(1)
assert agg < sep
n_big = 1000
sep_big = n_big * stamped_size(2, 5)
agg_big = stamped_size(0, n_big * 5 + 1) + n_big * stripped_size(2)
frag['sizes'] = '\n'.join([
    '| Bundle shape | Stamped size in bytes | Stripped size in bytes |',
    '| --- | --- | --- |',
    f'| 0 actions, carrying 12 tachygrams (the merged stamp on A) | {stamped_size(0, 12):,} | {stripped_size(0):,} |',
    f'| 1 action, 3 tachygrams (X and Z) | {stamped_size(1, 3):,} | {stripped_size(1):,} |',
    f'| 2 actions, 5 tachygrams (Y) | {stamped_size(2, 5):,} | {stripped_size(2):,} |',
])
frag['size-totals'] = (
    f'Published separately, X, Y and Z take {sep:,} bytes with 3 proofs. Published as the aggregate A with three adjuncts, '
    f'the same three transactions plus A take {agg:,} bytes with 1 proof. The saving grows with the batch, which we can see on hypothetical inputs. '
    f'{n_big:,} two-action bundles take {sep_big:,} bytes separately, and {agg_big:,} bytes as one innocent aggregate and {n_big:,} adjuncts, '
    f'which is {agg_big / n_big:,.0f} bytes per bundle in place of {sep_big / n_big:,.0f}. The proof falls from {n_big:,} copies to 1, while the '
    f'{n_big * 5:,} tachygrams and {n_big * 2:,} action signatures all remain.'
)

# ---- the bundle table ----------------------------------------------------------
rows = ['| Bundle | Spends | Outputs | $\\mathsf{maxfee}$ | $\\mathsf{fee}$ | $v^{\\mathsf{bal}}$ | Change note value | Contribution $v^{\\mathsf{bal}} + \\mathsf{fee}$ |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
for b in (A, X, Y, Z):
    f = FEE[b.name]
    rows.append(f'| {b.name} | {", ".join(map(str, b.spends)) or "none"} | {", ".join(map(str, b.outputs)) or "none"} | {b.maxfee} | {f} | {b.balance} | {b.maxfee - f} | {b.balance + f} |')
    assert sum(b.spends) - sum(b.outputs) - (b.maxfee - f) == b.balance + f
frag['bundles'] = '\n'.join(rows)
assert A.balance == 0 and A.maxfee == 0

# ---- Y's balance, step by step --------------------------------------------------
s, o = Y.actions
_sum_values = (s['v'] + o['v'] - Y.maxfee)
assert _sum_values == Y.balance == 3
assert Y.bvk() == mul(Y.bsk, RR)
frag['binding-run'] = '\n'.join([
    '| Term | Formula | Point |',
    '| --- | --- | --- |',
    f"| $\\mathsf{{cv}}$ of the spend | $[{s['v']}]\\mathcal{{V}} + [{s['rcv']}]\\mathcal{{R}}$ | ${show(s['cv'])}$ |",
    f"| $\\mathsf{{cv}}$ of the output | $[{o['v']}]\\mathcal{{V}} + [{o['rcv']}]\\mathcal{{R}}$ | ${show(o['cv'])}$ |",
    f"| $\\mathsf{{cv}}_{{\\mathsf{{maxfee}}}}$ | $[-{Y.maxfee}]\\mathcal{{V}} + [{Y.r}]\\mathcal{{R}}$ | ${show(Y.cvmax)}$ |",
    f"| $\\mathsf{{bvk}}$ | sum of the three, minus $[{Y.balance}]\\mathcal{{V}}$ | ${show(Y.bvk())}$ |",
    f"| $[\\mathsf{{bsk}}]\\mathcal{{R}}$ | $\\mathsf{{bsk}} = {s['rcv']} + {o['rcv']} + {Y.r} = {Y.bsk}$ modulo {Q} | ${show(mul(Y.bsk, RR))}$ |",
])
bad_bvk = Y.bvk(Y.balance + 1)
assert bad_bvk != mul(Y.bsk, RR) and bad_bvk == sub(mul(Y.bsk, RR), VV)
bad_log = next(k for k in range(Q) if mul(k, RR) == bad_bvk)
frag['binding-cheat'] = (
    f'Suppose a bundle claims a value balance of {Y.balance + 1} while the committed values still give {Y.balance}. '
    f'The validator computes $\\mathsf{{bvk}}\' = {show(bad_bvk)}$, which is $[\\mathsf{{bsk}}]\\mathcal{{R}} - \\mathcal{{V}}$, and the true key {Y.bsk} no longer matches it. '
    f'On our toy curve the matching key is {bad_log}, found by counting. Finding it requires the discrete log of $\\mathcal{{V}}$ with respect to $\\mathcal{{R}}$, which on a real curve nobody can compute.'
)

# ---- fee levels: same signed data, different proofs -----------------------------
Y.sign_all()
_commit_before = Y.commitment()
rows = ['| $\\mathsf{fee}$ | Change note value | $\\mathsf{cm}_{\\mathsf{chg}}$ | $d_{\\mathsf{fee}}$ | Contribution | Bundle commitment | $\\mathsf{auth\\_digest}$ contribution |',
        '| --- | --- | --- | --- | --- | --- | --- |']
_auths = set()
for f in (0, 4, 6):
    st = stamp_of(Y, f)
    auth = stamped_auth(Y, st)
    _auths.add(auth)
    rows.append(f'| {f} | {Y.maxfee - f} | {Y.change_cm(f)} | {Y.fee_digest(f)} | {Y.balance + f} | {short(Y.commitment())} | {short(auth)} |')
    assert Y.commitment() == _commit_before
assert len(_auths) == 3
assert schnorr_ok(Y.binding_sig, Y.bvk(), RR, Y.commitment())
frag['fee-levels'] = '\n'.join(rows)
_pass = [f for f in range(Q) if (Y.maxfee - f) >= 0 and f >= 0]
assert _pass == list(range(7))
_wrap = (Y.maxfee - 7) % Q
frag['fee-range'] = (
    f'Our toy range check accepts {len(_pass)} of the {Q} field values of the fee for bundle Y, namely 0 to {Y.maxfee}. The check is needed because field arithmetic would otherwise wrap around. '
    f'A fee of 7 gives a change value of ${Y.maxfee} - 7 \\equiv {_wrap}$ modulo {Q}. Fee and change then still sum to ${7} + {_wrap} \\equiv {(7 + _wrap) % Q} = \\mathsf{{maxfee}}$ in the field, so the sum looks balanced, although the integers {7} and {_wrap} are worth 49 in total against a reservation of {Y.maxfee}.'
)

# ---- memo ----------------------------------------------------------------------
_no_memo = Y.commitment(b'')
assert _no_memo != Y.commitment()
assert not schnorr_ok(Y.binding_sig, Y.bvk(), RR, _no_memo)
frag['memo'] = (
    f'Bundle Y carries the memo `first contact`. Dropping it changes the bundle commitment from {short(Y.commitment())} to {short(_no_memo)}, and the binding signature made over the first value fails against the second.'
)

# ---- stamps --------------------------------------------------------------------
ST = {b.name: stamp_of(b, FEE[b.name]) for b in (A, X, Y, Z)}
rows = ['| Bundle | Action digests | Tachygrams | $\\mathsf{action\\_acc}$ | $\\mathsf{tachygram\\_acc}$ | Coverage indicator |',
        '| --- | --- | --- | --- | --- | --- |']
for name, st in ST.items():
    rows.append(f'| {name} | $\\{{{", ".join(map(str, st.digests))}\\}}$ | $\\{{{", ".join(map(str, sorted(st.tgs)))}\\}}$ | ${show(st.header[0])}$ | ${show(st.header[1])}$ | {short(st.coverage())} |')
frag['stamps'] = '\n'.join(rows)
assert len(ST['A'].tgs) == 1 and len(ST['X'].tgs) == 3 and len(ST['Y'].tgs) == 5 and len(ST['Z'].tgs) == 3
assert len(ST['A'].digests) == 1 and len(ST['X'].digests) == 2 and len(ST['Y'].digests) == 3 and len(ST['Z'].digests) == 2

W1 = merge(ST['A'], ST['X'])
W2 = merge(W1, ST['Y'])
W3 = merge(W2, ST['Z'])
assert len(W3.tgs) == 12 and len(W3.digests) == 8 and W3.fee == 0
assert len(W3.tpoly) == 13
for _i in (0, 1):
    _heads = [x.header[_i] for x in list(ST.values()) + [W1, W2, W3]]
    assert len(set(_heads)) == len(_heads) and None not in _heads
rows = ['| Merge | Output action set size | Output tachygrams | $\\mathsf{action\\_acc}$ | $\\mathsf{tachygram\\_acc}$ | Check at $r$ | Trailer fee |',
        '| --- | --- | --- | --- | --- | --- | --- |']
for (nm, l, rr, out) in (('A with X', ST['A'], ST['X'], W1), ('previous with Y', W1, ST['Y'], W2), ('previous with Z', W2, ST['Z'], W3)):
    r = h('Challenge', out.header[0], out.header[1], out.anchor)
    assert r != 0
    assert peval(out.tpoly, r) == peval(l.tpoly, r) * peval(rr.tpoly, r) % Q
    # Degenerate zero evaluations would make the check look empty.
    assert peval(out.tpoly, r) != 0
    rows.append(f'| {nm} | {len(out.digests)} | {len(out.tgs)} | ${show(out.header[0])}$ | ${show(out.header[1])}$ | $r = {r}$: ${peval(l.tpoly, r)} \\cdot {peval(rr.tpoly, r)} = {peval(out.tpoly, r)}$ | {out.fee} |')
frag['merge-run'] = '\n'.join(rows)

# ---- overlap -------------------------------------------------------------------
_shared = sorted(set(ST['X'].tgs) & set(_xc_tgs))
assert len(_shared) == 2
_a_x = ST['A'].tgs + ST['X'].tgs
_all = _a_x + _xc_tgs
_unique = sorted(set(_all))
_arity = 2 * 2 + 3
assert len(_all) == 7 == _arity and len(_unique) == 5
_product = roots_poly(_all)
_union = roots_poly(_unique)
assert len(_product) == 8 and len(_union) == 6 and commit(_product) != commit(_union)
frag['overlap'] = (
    f'Suppose a wallet publishes a second bundle X$\'$ that spends the same note as X with a fresh $\\theta$. Its descriptor and fee note differ, but it shares the nullifiers {_shared[0]} and {_shared[1]} with X. '
    f'A forger can still fuse A, X and X$\'$, because the product polynomial has degree {len(_product) - 1} with double roots at those two values, and the step checks only the product. Its header holds the commitment ${show(commit(_product))}$. '
    f'The wire format forces the published list to be unique, so the list has {len(_unique)} entries. The arity rule asks for $2 \\cdot 2 + 3 = {_arity}$, so the first check fails. Recomputing from those {len(_unique)} values gives ${show(commit(_union))}$, which also misses the header.'
)

# ---- coverage gates ------------------------------------------------------------


def candidate_row(label, members, fee_of=FEE):
    descs, fees, digests = [], [], []
    for b in members:
        f = fee_of[b.name]
        descs += b.desc_bytes()
        fees.append(b.fee_entry(f))
        digests += b.digests() + [b.fee_digest(f)]
    n, bn = len(descs), len(members)
    cov_ok = coverage(descs, fees) == W3.coverage()
    arity_ok = len(W3.tgs) == 2 * n + bn
    proof_ok = commit(roots_poly(digests)) == W3.header[0]
    mark = lambda ok: 'passes' if ok else 'fails'
    return (cov_ok, arity_ok, proof_ok,
            f'| {label} | {n} | {bn} | {2 * n + bn} | {mark(cov_ok)} | {mark(arity_ok)} | {mark(proof_ok)} |')


rows = ['| Candidate adjuncts with A | $N$ | $B$ | $2N + B$ | Indicator | Arity (12) | Proof header |',
        '| --- | --- | --- | --- | --- | --- | --- |']
_count = 0
for k in range(4):
    for sub_set in itertools.combinations((X, Y, Z), k):
        cov_ok, arity_ok, proof_ok, row = candidate_row(', '.join(b.name for b in sub_set) or 'none', (A,) + sub_set)
        rows.append(row)
        assert cov_ok == arity_ok == proof_ok
        _count += cov_ok
assert _count == 1
cov_ok, arity_ok, proof_ok, row = candidate_row('X, Y, Z$\'$ (a different one-action bundle)', (A, X, Y, Z2))
assert not cov_ok and arity_ok and not proof_ok
rows.append(row)
_fee3 = dict(FEE, Y=3)
cov_ok, arity_ok, proof_ok, row = candidate_row('X, Y at fee 3 in its trailer, Z', (A, X, Y, Z), _fee3)
assert not cov_ok and arity_ok and not proof_ok
rows.append(row)
frag['gates'] = '\n'.join(rows)

# Rewriting one adjunct's fee.
assert Y.fee_digest(3) != 0
_rewritten = commit(roots_poly([d for d in W3.digests if d != Y.fee_digest(4)] + [Y.fee_digest(3)]))
assert _rewritten != W3.header[0]
frag['fee-rewrite'] = (
    f'Suppose a miner rewrites the trailer of the adjunct Y from fee 4 to fee 3, which is still within the signed maximum of {Y.maxfee}. The bundle commitment does not change, because the fee is not effecting data, so the signatures still verify. '
    f'The fee digest changes from {Y.fee_digest(4)} to {Y.fee_digest(3)}, so the rebuilt action set has a different root, and its commitment becomes ${show(_rewritten)}$ in place of the header\'s ${show(W3.header[0])}$. The proof cannot verify against that header.'
)

# ---- identifiers ---------------------------------------------------------------
A_seed = stamped_auth(A, ST['A'])
A_merged = stamped_auth(A, W3)
W3_id = wtxid(A, A_merged)
W2_id = wtxid(A, stamped_auth(A, W2))
assert W3_id != W2_id and A_seed != A_merged and any(W3_id)
Y_auto = stamped_auth(Y, ST['Y'])
Y_fee3 = stamped_auth(Y, stamp_of(Y, 3))
Y_strip = stripped_auth(Y, 4, W3_id)
Y_strip2 = stripped_auth(Y, 4, W2_id)
T_st = merge(stamp_of(T, FEE['T']), W3)
T_id = wtxid(T, stamped_auth(T, T_st))
A_strip = stripped_auth(A, 0, T_id)
Y_strip3 = stripped_auth(Y, 4, T_id)
rows = ['| Physical form | State byte | Bundle commitment | $\\mathsf{auth\\_digest}$ contribution |',
        '| --- | --- | --- | --- |']
for label, b, sb, auth in [
    ('A with its `FeeSeed` stamp', A, '`0x01`', A_seed),
    ('A with the merged stamp over A, X, Y and Z', A, '`0x01`', A_merged),
    ('A stripped, pointing to a larger aggregate on T', A, '`0x02`', A_strip),
    ('Y as an autonome at fee 4', Y, '`0x01`', Y_auto),
    ('Y as an autonome at fee 3', Y, '`0x01`', Y_fee3),
    ('Y stripped, pointing to A with the merged stamp', Y, '`0x02`', Y_strip),
    ('Y stripped, pointing to A with a stamp that covers only A, X and Y', Y, '`0x02`', Y_strip2),
    ('Y stripped, pointing to the aggregate on T', Y, '`0x02`', Y_strip3),
]:
    rows.append(f'| {label} | {sb} | {short(b.commitment())} | {short(auth)} |')
assert len({A_seed, A_merged, A_strip}) == 3
assert len({Y_auto, Y_fee3, Y_strip, Y_strip2, Y_strip3}) == 5
frag['ids'] = '\n'.join(rows)

# ---- verification of the block --------------------------------------------------
_sigs_checked = 0
for b in (A, X, Y, Z):
    assert schnorr_ok(b.binding_sig, b.bvk(), RR, b.commitment())
    _sigs_checked += 1 + len(b.action_sigs)
    for sig, a, i in zip(b.action_sigs, b.actions, range(9)):
        assert schnorr_ok(sig, a['rk'], SIG_G, b.commitment())
assert _sigs_checked == 8
_cover_digests = sum((b.digests() + [b.fee_digest(FEE[b.name])] for b in (A, X, Y, Z)), [])
_rebuilt = commit(roots_poly(_cover_digests))
assert _rebuilt == W3.header[0]
_tg_recomputed = commit(roots_poly(sorted(W3.tgs)))
assert _tg_recomputed == W3.header[1]
assert coverage(sum((b.desc_bytes() for b in (A, X, Y, Z)), []), [b.fee_entry(FEE[b.name]) for b in (A, X, Y, Z)]) == W3.coverage()
frag['block-verify'] = '\n'.join([
    '| Check | Inputs | Result on our block |',
    '| --- | --- | --- |',
    f'| Signatures | every bundle\'s action and binding signatures | {_sigs_checked} signatures verify |',
    f'| Pointers | the 3 adjuncts\' `tachyonAggregateId` against the wtxid of A | all equal {short(W3_id[:32])}$\\ldots$ |',
    f'| Coverage | {len(W3.descs)} action descriptors and {len(W3.fees)} fee descriptors, none repeated | the digest {short(W3.coverage())} matches the trailer |',
    f'| Tachygram count | $2 \\cdot {len(W3.descs)} + {len(W3.fees)}$ | {len(W3.tgs)} published |',
    f'| Tachygram set | commit to the published list | ${show(_tg_recomputed)}$ equals `cTachygrams` |',
    f'| Proof | header $({show(_rebuilt)},\\ {show(W3.header[1])},\\ \\alpha)$ | the header matches the one the proof was made for |',
])
_total_fee = sum(FEE[n] for n in 'AXYZ')
frag['fees-in-block'] = (
    f'The merged stamp on A states a trailer fee of {W3.fee}, the adjuncts state {FEE["X"]}, {FEE["Y"]} and {FEE["Z"]}, and their fee descriptors are all covered by the one proof. The bundles therefore pay {_total_fee} in total, the same as if each had been mined alone.'
)

# ---- limits --------------------------------------------------------------------
N_COEFFS = 2 ** 13
_max_tg = N_COEFFS - 1
_max_bundles = _max_tg // 5
frag['limit'] = (
    f'At the production rank a polynomial has $2^{{13}} = {N_COEFFS:,}$ coefficients, so a stamp can hold at most {_max_tg:,} tachygrams. Bundles of two actions contribute 5 tachygrams each, so one aggregate covers at most {_max_bundles:,} of them, or {_max_bundles * 2:,} actions.'
)

# ---- ZIP 317 draft -------------------------------------------------------------
MARGINAL, GRACE = 5000, 2
rows = ['| Bundle | $\\mathsf{nActionsTachyon}$ | Logical actions, ignoring other pools | Conventional fee in zatoshi |', '| --- | --- | --- | --- |']
for name, n in (('A (innocent)', 0), ('X', 1), ('Y', 2), ('a bundle of 5 actions', 5)):
    rows.append(f'| {name} | {n} | {n} | {MARGINAL * max(GRACE, n):,} |')
frag['zip317'] = '\n'.join(rows)

# ---- unmerge -------------------------------------------------------------------
Q1 = unmerge(W3, ST['X'])
assert sorted(Q1.digests) == sorted(ST['A'].digests + ST['Y'].digests + ST['Z'].digests)
assert Q1.header[:2] == merge(merge(ST['A'], ST['Y']), ST['Z']).header[:2]
r = h('Challenge', Q1.header[0], Q1.header[1], 'unmerge')
assert r != 0
assert peval(W3.tpoly, r) == peval(ST['X'].tpoly, r) * peval(Q1.tpoly, r) % Q and peval(W3.tpoly, r) != 0
assert peval(W3.apoly, r) == peval(ST['X'].apoly, r) * peval(Q1.apoly, r) % Q
frag['unmerge-run'] = (
    f'Dividing the tachygram polynomial of the merged stamp, which has degree {len(W3.tpoly) - 1}, by that of X, which has degree {len(ST["X"].tpoly) - 1}, leaves remainder zero and a quotient of degree {len(Q1.tpoly) - 1}. '
    f'Dividing the action polynomials takes degree {len(W3.apoly) - 1} to degree {len(Q1.apoly) - 1}, also with remainder zero. The quotient stamp has the header $({show(Q1.header[0])},\\ {show(Q1.header[1])},\\ \\alpha)$, which is the same header we would get by merging A, Y and Z directly. '
    f'At the challenge $r = {r}$ the tachygram check reads ${peval(W3.tpoly, r)} = {peval(ST["X"].tpoly, r)} \\cdot {peval(Q1.tpoly, r)}$ modulo {Q}. The trailer fee stays at {Q1.fee}, which is A\'s fee.'
)

X4 = stamp_of(X, 4)
_, a_rem = pdivmod(W3.apoly, X4.apoly)
_, t_rem = pdivmod(W3.tpoly, X4.tpoly)
assert a_rem and t_rem
_common_tg = sorted(set(X4.tgs) & set(W3.tgs))
assert len(_common_tg) == 2 and X4.digests[0] == ST['X'].digests[0]
frag['unmerge-fee'] = (
    f'Suppose instead that the block carries X at fee 4, while the merged stamp holds X at fee 5. The block\'s stamp has the fee digest {X.fee_digest(4)} and the change commitment {X.change_cm(4)} where ours has {X.fee_digest(5)} and {X.change_cm(5)}. '
    f'Dividing by it leaves a nonzero remainder of degree {len(a_rem) - 1} on the action polynomial and of degree {len(t_rem) - 1} on the tachygram polynomial, so no quotient exists. The two versions of X still share the nullifiers {_common_tg[0]} and {_common_tg[1]}, so the merged stamp cannot be published either. Dividing by the cached fee 5 stamp of X removes X and gives the quotient above, and the fee in the block plays no part.'
)

D_xy = merge(ST['X'], ST['Y'])
Q2 = unmerge(W3, D_xy)
T_block = merge(merge(stamp_of(T, FEE['T']), ST['X']), ST['Y'])
_, a_rem2 = pdivmod(W3.apoly, T_block.apoly)
assert a_rem2
W_plus = merge(W3, stamp_of(T, FEE['T']))
Q3 = unmerge(W_plus, T_block)
assert Q3.header[:2] == Q2.header[:2] == merge(ST['A'], ST['Z']).header[:2]
assert Q2.fee == 0 and Q3.fee == 0
frag['unmerge-medium'] = (
    f'Suppose the block includes an aggregate on a bundle T, covering T, X and Y, and T is not in our stamp. Dividing by T\'s stamp fails, because it has the factors of T and our stamp does not, which leaves a remainder of degree {len(a_rem2) - 1} on the action polynomial. '
    f'Merging our cached stamps of X and Y gives a divisor that covers exactly what has to come out, and dividing by it leaves a stamp with {len(Q2.digests)} digests and {len(Q2.tgs)} tachygrams, covering A and Z, with header $({show(Q2.header[0])},\\ {show(Q2.header[1])},\\ \\alpha)$. '
    f'The other route merges a stamp of T into our stamp first and then divides by the block\'s stamp. It reaches the same header.'
)

Q4 = unmerge(W3, ST['A'])
assert Q4.fee == 0 and sorted(Q4.digests) == sorted(ST['X'].digests + ST['Y'].digests + ST['Z'].digests)
_q4_on_x = coverage(Q4.descs, [X.fee_entry(0)] + [Y.fee_entry(4), Z.fee_entry(2)])
assert _q4_on_x != Q4.coverage()
BS = stamp_of(B_NEW, FEE['B'])
assert not set(BS.tgs) & set(Q4.tgs)
Q5 = merge(BS, Q4)
assert Q5.fee == FEE['B']
assert len(Q5.tgs) == len(Q4.tgs) + len(BS.tgs)
assert Q5.coverage() == coverage(B_NEW.desc_bytes() + X.desc_bytes() + Y.desc_bytes() + Z.desc_bytes(),
                                 [B_NEW.fee_entry(FEE['B']), X.fee_entry(5), Y.fee_entry(4), Z.fee_entry(2)])
frag['unmerge-receiver'] = (
    f'Suppose the block included A on its own. Dividing A out leaves a stamp covering X, Y and Z, with {len(Q4.tgs)} tachygrams. Its trailer fee is still {Q4.fee}, while the fees it covers are {FEE["X"]}, {FEE["Y"]} and {FEE["Z"]}. Placed on X, the verifier would build the fee descriptor of X with fee {Q4.fee}, and the indicator check fails. '
    f'Merging the stamp into a new bundle B with its own fee of {FEE["B"]} gives a stamp whose receiver is B, with trailer fee {Q5.fee} and {len(Q5.tgs)} tachygrams, and it covers B, X, Y and Z.'
)

print(json.dumps(frag))
