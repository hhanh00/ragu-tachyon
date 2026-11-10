"""Worked examples for oblivious-sync.md. Prints fragments as JSON.

Poseidon does not appear. Nullifiers come from the stand-in of notes-and-nullifiers.md
(SHA-256 of tag and inputs, reduced modulo 65537), and the small examples reduce them
modulo 43 so that their polynomials fit on a page. The epoch of tachygrams is the
epoch 0 of pool-state.md. Tachyon has not activated on mainnet, and all of this
describes the Tachyon repository at commit 7e50254.
"""
import hashlib
import json
from itertools import combinations
from math import ceil, isqrt, log2

from toy_curve import G, H as H_POINT, Q, U, add, curve_points, mul, show
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    import pool_state as POOL

frag = {}


def num(x):
    return f'{x:,}'


def tnum(x):
    return num(x).replace(',', '{,}')


# ------------------------------------------------- the running note of chapter 20
F = 65537
RATE = 4


def digest(tag, *inputs):
    return hashlib.sha256('|'.join([tag] + [str(i) for i in inputs]).encode()).digest()


def H(tag, *inputs):
    return int.from_bytes(digest(tag, *inputs), 'big') % F


def sponge(tag, *inputs):
    d = digest(tag, *inputs)
    return [int.from_bytes(d[i * 8:(i + 1) * 8], 'big') % F for i in range(RATE)]


NK = H('expand', 'alice-wallet-seed-7', 0x22)
PSI = H('sender-psi', 'bob-to-alice', 1)
MK = H('Tachyon-NfMaster', PSI, NK)


def nullifier(e):
    w = e - e % RATE
    return sponge('Tachyon-NfDerive', MK, w)[e - w]


NF = {e: nullifier(e) for e in range(32)}
# The published table of chapter 20, so that a drift there cannot pass silently.
assert (NK, PSI, MK) == (40954, 625, 299)
assert [NF[e] for e in range(12)] == [19392, 15569, 21425, 14090, 2976, 63093, 59553,
                                      55113, 61177, 32258, 31053, 34200]

frag['job'] = '\n'.join(
    ['| Epoch $j$ | $\\mathsf{nf}_j$ | What happens to it | Who can do the reading |',
     '| --- | --- | --- | --- |']
    + [f'| 3 | {NF[3]} | tested for absence from epoch 3, in a bind of its own (Section 6) | the wallet or a service |']
    + [f'| {j} | {NF[j]} | tested for absence from epoch {j} | the wallet or a service |' for j in (4, 5, 6)]
    + [f'| {j} | {NF[j]} | published by the spend | consensus checks its window |' for j in (7, 8)])


# ------------------------------------------------------- polynomials over a prime
def pmul(a, b, p=Q):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] = (out[i + j] + x * y) % p
    return out


def pprod(polys, p=Q):
    out = [1]
    for a in polys:
        out = pmul(out, a, p)
    return out


def ev(a, x, p=Q):
    r = 0
    for c in reversed(a):
        r = (r * x + c) % p
    return r


def trim(a):
    a = list(a)
    while len(a) > 1 and a[-1] == 0:
        a.pop()
    return a


def pdivmod(num_, den, p=Q):
    num_, den = trim(num_), trim(den)
    inv = pow(den[-1], -1, p)
    rem = list(num_)
    if len(num_) < len(den):
        return [0], rem
    quo = [0] * (len(num_) - len(den) + 1)
    for k in range(len(quo) - 1, -1, -1):
        c = rem[k + len(den) - 1] * inv % p
        quo[k] = c
        for j, d in enumerate(den):
            rem[k + j] = (rem[k + j] - c * d) % p
    return quo, trim(rem[:len(den) - 1] or [0])


def pshow(a, var='X'):
    terms = []
    for i in range(len(a) - 1, -1, -1):
        c = a[i]
        if c == 0:
            continue
        x = '' if i == 0 else (var if i == 1 else f'{var}^{{{i}}}')
        terms.append((str(c) if (c != 1 or i == 0) else '') + x)
    return ' + '.join(terms) if terms else '0'


def roots_poly(roots, p=Q):
    return pprod([[-r % p, 1] for r in roots], p)


# ----------------------------------------------------------- cubes in the toy field
CUBES = sorted({x ** 3 % Q for x in range(1, Q)})
assert len(CUBES) == (Q - 1) // 3
C_NC = next(x for x in range(2, Q) if x not in CUBES)   # the smallest non-cube of F_43
assert 2 in CUBES and C_NC != 2
T2 = next(t for t in range(1, Q) if t ** 3 % Q == 2)    # a cube root of 2 in F_43
OMEGA = next(w for w in range(2, Q) if w ** 3 % Q == 1)
OMEGA2 = OMEGA * OMEGA % Q
assert sorted([OMEGA, OMEGA2]) == [6, 36]


def factor(i, m, c=C_NC, p=Q):
    """F_{i,m}(X) = (m + (i+1)X)^3 - c, in the code's coefficient order."""
    a = (i + 1) % p
    return [(m ** 3 - c) % p, 3 * a * m * m % p, 3 * a * a * m % p, a ** 3 % p]


def factor_at(i, m, x, c=C_NC, p=Q):
    return (pow((m + (i + 1) * x) % p, 3, p) - c) % p


# The chapter 20 nullifiers reduced into the toy field.
TOY = {e: NF[e] % Q for e in range(3, 8)}
assert all(v != 0 for v in TOY.values())
assert len({TOY[e] for e in (3, 4, 5, 6)}) == 4
frag['toy-values'] = (
    f'Our small examples use $\\F_{{43}}$, so we reduce the nullifiers above modulo 43. That gives '
    f'$\\mathsf{{nf}}_3 = {TOY[3]}$, $\\mathsf{{nf}}_4 = {TOY[4]}$, $\\mathsf{{nf}}_5 = {TOY[5]}$, and '
    f'$\\mathsf{{nf}}_6 = {TOY[6]}$.')

# ------------------------------------------------- why plain roots lose the epoch
E4 = [TOY[3], TOY[4], 17]   # epoch 4 holds the pair of the first spend, and a stranger
E5 = [33, 6, 38]
f4, f5 = roots_poly(E4), roots_poly(E5)
assert ev(f4, TOY[4]) == 0 and ev(f4, TOY[5]) != 0 and ev(f5, TOY[4]) != 0
assert len(set(E4 + E5)) == 6 and TOY[5] not in E4 + E5
honest_roots = pmul([-TOY[4] % Q, 1], [-TOY[5] % Q, 1])
assert all(ev(honest_roots, z) == (z - TOY[5]) * (z - TOY[4]) % Q for z in range(Q))
frag['root-attack'] = (
    f'Suppose an earlier spend of this note had target 3 and was accepted during epoch 4, so epoch 4 contains '
    f'$\\mathsf{{nf}}_3 = {TOY[3]}$ and $\\mathsf{{nf}}_4 = {TOY[4]}$. Say epoch 4 publishes {{{E4[0]}, {E4[1]}, {E4[2]}}} '
    f'and epoch 5 publishes {{{E5[0]}, {E5[1]}, {E5[2]}}}. Write $e_4(X)$ and $e_5(X)$ for their [epoch polynomials](./pool-state.md#_4-combining-and-dividing-sets), '
    f'whose roots are exactly the published values, so a value is absent from an epoch when that epoch\'s polynomial is nonzero there. A second spend must fail, and the honest test does fail, since '
    f'$e_4({TOY[4]}) = {ev(f4, TOY[4])}$. The cheater swaps the two values and tests {TOY[5]} against epoch 4 and '
    f'{TOY[4]} against epoch 5. Both tests pass, with $e_4({TOY[5]}) = {ev(f4, TOY[5])}$ and $e_5({TOY[4]}) = {ev(f5, TOY[4])}$. '
    f'The tested multiset is still {{{TOY[4]}, {TOY[5]}}}, and its polynomial $(X - {TOY[4]})(X - {TOY[5]}) = {pshow(honest_roots)}$ '
    f'did not change, so it divides the wallet\'s polynomial just as the honest one does.')

# ------------------------------------------------- linear factors can be rescaled
a4, a5, b4, b5 = 5, 6, TOY[4], TOY[5]
r = a5 * pow(a4, -1, Q) % Q
b5_new = b4 * r % Q                      # the value now labelled epoch 5
b4_new = b5 * pow(r, -1, Q) % Q          # the value now labelled epoch 4
lin_honest = pmul([b4, a4], [b5, a5])
lin_forged = pmul([b4_new, a4], [b5_new, a5])
assert lin_honest == lin_forged and b4_new != b4 and b5_new != b5
frag['linear-attack'] = (
    f'For epochs 4 and 5 the linear factors are ${a4}X + {b4}$ and ${a5}X + {b5}$, and their product is ${pshow(lin_honest)}$. '
    f'Move the unit $r = {a5}/{a4} = {r}$ from one factor to the other:\n\n'
    f'$$({a4}X + {b4})({a5}X + {b5}) = \\big({r}({a4}X + {b4})\\big)\\big({r}^{{-1}}({a5}X + {b5})\\big) = ({a5}X + {b5_new})({a4}X + {b4_new}).$$\n\n'
    f'The right side reads as value {b4_new} at epoch 4 and value {b5_new} at epoch 5. Neither is the genuine nullifier, '
    f'and the product is the same polynomial, so it passes every challenge.')

# ---------------------------------------------------------- the cubic factor, expanded
A, M = 5, TOY[4]
fac44 = factor(4, TOY[4])
assert fac44 == [(M ** 3 - C_NC) % Q, 3 * A * M * M % Q, 3 * A * A * M % Q, A ** 3 % Q]
assert pmul(pmul([M, A], [M, A]), [M, A])[1:] == fac44[1:]
PALLAS_P = 0x40000000000000000000000000000000224698fc094cf91b992d30ed00000001
assert PALLAS_P % 3 == 1 and pow(2, (PALLAS_P - 1) // 3, PALLAS_P) != 1
frag['noncube'] = (
    f'In $\\F_{{43}}$ the nonzero cubes are {", ".join(str(x) for x in CUBES)}, which is {len(CUBES)} of the 42 nonzero elements. '
    f'The value 2 is one of them, since ${T2}^3 = 2$ here, so the toy field cannot use the code\'s constant. '
    f'Its smallest non-cube is $c = {C_NC}$, and we use that. '
    f'The real field does have $2$ as a non-cube, which we checked by computing $2^{{(p-1)/3}} \\neq 1$ for the Pallas base field.')
frag['factor-expand'] = (
    f'With $i = 4$, $m = {M}$, and $c = {C_NC}$ we have $a = i + 1 = {A}$, and expanding the cube gives\n\n'
    f'$$\\begin{{aligned}}F_{{4,{M}}}(X) &= ({M} + {A}X)^3 - {C_NC} \\\\\n'
    f'&= {A}^3 X^3 + 3 \\cdot {A}^2 \\cdot {M}\\, X^2 + 3 \\cdot {A} \\cdot {M}^2\\, X + {M}^3 - {C_NC} \\\\\n'
    f'&= {pshow(fac44)}.\\end{{aligned}}$$')

# --- exhaustive: distinct pairs in a window give distinct factors and products
WINDOW = [3, 4, 5, 6]
pairs = [(i, m) for i in WINDOW for m in range(Q)]
assert len({tuple(factor(i, m)) for i, m in pairs}) == len(pairs)
prods = {}
n_prods = 0
for x, y in combinations(pairs, 2):
    key = tuple(pmul(factor(*x), factor(*y)))
    assert key not in prods, (x, y, prods.get(key))
    prods[key] = (x, y)
    n_prods += 1
for x in pairs:
    key = tuple(pmul(factor(*x), factor(*x)))
    assert key not in prods
    prods[key] = (x, x)
    n_prods += 1
frag['unique'] = (
    f'We can test this on the toy field. Epochs 3 to 6 and all 43 values give {len(pairs)} pairs, and they produce {len(pairs)} different factors. '
    f'Multiplying any two of them, repeats allowed, gives {num(n_prods)} products, and no two of those products are equal. So rescaling cannot produce a second set of pairs here.')

# --- a cube for c breaks containment
N_SET = {i: TOY[i] for i in WINDOW}
Npoly_of = lambda c: pprod([factor(i, N_SET[i], c) for i in WINDOW])  # noqa: E731


def forged_divisors(c):
    N_ = Npoly_of(c)
    out = []
    for i in range(0, 16):
        for m in range(Q):
            if N_SET.get(i) == m:
                continue
            if pdivmod(N_, factor(i, m, c))[1] == [0]:
                out.append((i, m))
    return out


forged_cube = forged_divisors(2)
forged_good = forged_divisors(C_NC)
# Scale-equivalent reps of genuine factors are the injectivity issue; separate them.
same_as_member = lambda c, p: any(  # noqa: E731
    factor(p[0], p[1], c) == factor(i, N_SET[i], c) for i in WINDOW)
assert all(same_as_member(C_NC, p) for p in forged_good)
true_forgeries = [p for p in forged_cube if not same_as_member(2, p)]
assert true_forgeries
pair0 = true_forgeries[0]
roots_of = lambda poly: [x for x in range(Q) if ev(poly, x) == 0]  # noqa: E731
frag['cube-fail'] = (
    f'Here is the failure on the toy field. Take the four pairs above and rebuild their product $N(X)$ twice, once with the cube $c = 2$ and once with our non-cube $c = {C_NC}$. '
    f'Then try every candidate pair $(i, m)$ with $i$ from 0 to 15, which are the 16 epochs of one derivation batch in the code, a batch that Section 7 introduces, and all 43 values of $m$. '
    f'With $c = 2$, $N(X)$ has the {len(roots_of(Npoly_of(2)))} distinct roots {", ".join(map(str, roots_of(Npoly_of(2))))}, '
    f'and {len(true_forgeries)} false pairs have all of their three roots among them. The pair $({pair0[0]},\\ {pair0[1]})$ is one, whose roots '
    f'are {", ".join(map(str, roots_of(factor(pair0[0], pair0[1], 2))))}, and its factor divides $N$ although it is no member of $N$.\n\n'
    f'With $c = {C_NC}$, $N(X)$ has no roots in the field at all, and the only other pairs whose factors divide it turn out to give exactly the same polynomial as a member, for a reason that Section 5 explains.')

# ---------------------------------------------------------- the cube root collision
m0 = TOY[4]
assert factor(0, m0) == factor(5, OMEGA * m0 % Q)
BOUND_T = isqrt(Q // 3)
assert 1 + OMEGA + OMEGA * OMEGA == Q
assert max(a * a + a * b + b * b for a in range(1, BOUND_T + 1) for b in range(1, BOUND_T + 1)) < Q
BOUND_P = isqrt(PALLAS_P // 3)
EPOCH_COUNT = 2 ** 32 // 4096
assert EPOCH_COUNT == 2 ** 20 and BOUND_P > 2 ** 125
frag['omega'] = (
    f'In $\\F_{{43}}$ the cube roots of unity are 1, {OMEGA}, and {OMEGA2}. Since ${OMEGA} \\cdot 1 = {OMEGA}$, the epoch numbers $a = 1$ and $a = {OMEGA}$ '
    f'are one scaling apart, and the factors for $(0,\\ {m0})$ and $(5,\\ {OMEGA * m0 % Q})$ are the same polynomial, namely ${pshow(factor(0, m0))}$.')
frag['omega-bound'] = (
    f'On the toy field the bound is $\\lfloor\\sqrt{{43/3}}\\rfloor = {BOUND_T}$, which is small, and the collision above has $1 + {OMEGA} + {OMEGA}^2 = {1 + OMEGA + OMEGA * OMEGA}$, '
    f'exactly the field size. For the Pallas base field the bound is about $2^{{{int(log2(BOUND_P))}}}$, while the code has only $2^{{20}}$ epochs. '
    f'Our batch of epochs 3 to 6 lies above the toy bound, so we checked it directly, and Section 4 found no collision among those epochs.')

# ------------------------------------------------ the full run on the toy curve
_used = {a[0] for a in G} | {H_POINT[0], U[0]}
EXTRA = [a for a in curve_points() if a[0] not in _used and a[1] < 16]
GENS = list(G)
for a in EXTRA:
    if len(GENS) < 13 and a[0] not in {b[0] for b in GENS}:
        GENS.append(a)
assert GENS[4:7] == [(4, 6), (5, 2), (7, 6)]  # the extra generators of pool-state.md
if len(GENS) < 13:  # the rule above runs out of low points; continue with the high ones
    for a in curve_points():
        if len(GENS) < 13 and a[0] not in _used and a[0] not in {b[0] for b in GENS}:
            GENS.append(a)
assert len(GENS) == 13 and len({a[0] for a in GENS}) == 13


def commit(p):
    assert len(p) <= len(GENS)
    out = None
    for k, g in zip(p, GENS):
        out = add(out, mul(k, g))
    return out


DELTA_E = [4, 5, 6]
COMP_E = [3]
Delta = pprod([factor(i, TOY[i]) for i in DELTA_E])
Comp = pprod([factor(i, TOY[i]) for i in COMP_E])
Npoly = pprod([factor(i, TOY[i]) for i in WINDOW])
assert pmul(Delta, Comp) == Npoly
quo, rem = pdivmod(Npoly, Delta)
assert trim(quo) == trim(Comp) and rem == [0]
assert len(Npoly) == 13 and len(Delta) == 10 and len(Comp) == 4
cD, cC, cN = commit(Delta), commit(Comp), commit(Npoly)
assert None not in (cD, cC, cN) and len({cD, cC, cN}) == 3
# Com(Delta) can coincide with one of the unnamed high generators in a group this small;
# keep it distinct from the generators that earlier chapters name.
assert not ({cD, cC, cN} & set(GENS[:7]))


def challenge(*items):
    return int.from_bytes(digest('Tachyon-toy-challenge', *items), 'big') % Q


# The stand-in hash retries with a counter until no value in the example is 0 or 1,
# so that the check below shows real multiplications.
Z = next(z for z in (challenge(cD, cC, cN, k) for k in range(100))
         if z not in (0, 1) and all(v not in (0, 1) for v in
                                    [ev(Delta, z), ev(Comp, z)] + [factor_at(i, TOY[i], z) for i in DELTA_E]))
dz, cz, nz = ev(Delta, Z), ev(Comp, Z), ev(Npoly, Z)
assert 0 not in (dz, cz, nz) and dz * cz % Q == nz
DZ_PARTS = [factor_at(i, TOY[i], Z) for i in DELTA_E]
assert dz == DZ_PARTS[0] * DZ_PARTS[1] * DZ_PARTS[2] % Q
frag['run-polys'] = '\n'.join([
    '| Polynomial | Epochs | Built by | Coefficients, highest degree first |',
    '| --- | --- | --- | --- |',
    f'| $\\Delta(X)$ | 4, 5, 6 | the service | ${pshow(Delta)}$ |',
    f'| $N(X)$ | 3, 4, 5, 6 | the wallet | ${pshow(Npoly)}$ |',
    f'| $C(X)$ | 3 | the wallet | ${pshow(Comp)}$ |',
])
frag['run-degrees'] = (
    f'Each factor is a cubic, so $\\Delta$ has degree {len(Delta) - 1}, $C$ has degree {len(Comp) - 1}, and $N$ has degree {len(Npoly) - 1}. '
    f'The box lists their coefficients.')
frag['run-commit'] = (
    f'Each polynomial commits on the toy curve as in [chapter 6](./polynomial-commitments.md), with the extra generators of [chapter 21](./pool-state.md#_4-combining-and-dividing-sets) '
    f'and more of the same kind, since $N$ needs 13: $\\mathsf{{Com}}(\\Delta) = {show(cD)}$, $\\mathsf{{Com}}(C) = {show(cC)}$, and $\\mathsf{{Com}}(N) = {show(cN)}$. '
    f'A stand-in hash of those three points gives the challenge $z = {Z}$.')
frag['run-check'] = (
    f'At $z = {Z}$ the service\'s side evaluates factor by factor as '
    f'$\\Delta({Z}) = F_{{4,{TOY[4]}}}({Z}) \\cdot F_{{5,{TOY[5]}}}({Z}) \\cdot F_{{6,{TOY[6]}}}({Z}) = {DZ_PARTS[0]} \\cdot {DZ_PARTS[1]} \\cdot {DZ_PARTS[2]} = {dz}$. '
    f'The wallet also has $C({Z}) = {cz}$ and $N({Z}) = {nz}$, and the identity holds, since ${dz} \\cdot {cz} = {nz}$ in $\\F_{{43}}$.')

# --- counting cheaters at every challenge
def passes(delta_poly, comp_poly):
    return [z for z in range(Q) if ev(Npoly, z) == ev(delta_poly, z) * ev(comp_poly, z) % Q]


rows = []
# (a) a wrong value at epoch 5, with the honest complement committed in advance
wrong = [m for m in range(Q) if m != TOY[5]]
w_counts = []
for m in wrong:
    dp = pprod([factor(4, TOY[4]), factor(5, m), factor(6, TOY[6])])
    assert pdivmod(Npoly, dp)[1] != [0]
    w_counts.append(len(passes(dp, Comp)))
assert set(w_counts) == {2}
rows.append(('A wrong value at epoch 5, for each of the 42 wrong values', 0, '2 in every case'))
all_counts = [2]
# (b) swap the two values across their epochs
dp = pprod([factor(4, TOY[5]), factor(5, TOY[4]), factor(6, TOY[6])])
assert pdivmod(Npoly, dp)[1] != [0]
k = len(passes(dp, Comp))
assert k <= 12
all_counts.append(k)
rows.append((f'The swap of Section 3, with {TOY[5]} at epoch 4 and {TOY[4]} at epoch 5', 0, str(k)))
# (c) one epoch tested twice with the genuine value
dp = pprod([factor(4, TOY[4]), factor(4, TOY[4]), factor(6, TOY[6])])
assert pdivmod(Npoly, dp)[1] != [0]
k = len(passes(dp, Comp))
all_counts.append(k)
rows.append((f'Epoch 4 tested twice, standing in for epoch 5', 0, str(k)))
# (d) an epoch outside the window, with its genuine value
assert 7 not in WINDOW
dp = pprod([factor(4, TOY[4]), factor(7, TOY[7]), factor(6, TOY[6])])
assert pdivmod(Npoly, dp)[1] != [0]
k = len(passes(dp, Comp))
all_counts.append(k)
rows.append(('A genuine nullifier of epoch 7, which the batch does not hold, in place of epoch 5', 0, str(k)))
frag['run-cheat'] = '\n'.join(
    ['| The segment\'s polynomial $\\Delta\'$ uses | Cases where any $C$ makes $N = \\Delta\' C$ | Challenges that pass with the honest $C$, of 43 |', '| --- | --- | --- |']
    + [f'| {a} | {b} | {c} |' for a, b, c in rows])
deg_N = len(Npoly) - 1
frag['run-cheat-bound'] = (
    f'The difference $N - \\Delta\' C$ has degree at most {deg_N}, so no attempt can pass more than {deg_N} challenges, and the worst one here passes {max(all_counts)}. '
    f'The box explains why a single wrong value passes so few.')
frag['run-cheat-note'] = (
    f'A wrong value passes so few because $N - \\Delta\' C$ factors as $C$, $F_{{4,{TOY[4]}}}$ and $F_{{6,{TOY[6]}}}$, which have no roots in the field, times $F_{{5,{TOY[5]}}} - F_{{5,m}}$. The constants $c$ cancel in that difference, which leaves $A^3 - B^3$ with $A = {TOY[5]} + {5 + 1}X$ and $B = m + {5 + 1}X$. '
    f'Because $\\F_{{43}}$ contains the cube root of unity $\\omega$, this factors as $(A - B)(A - \\omega B)(A - \\omega^2 B)$. The first factor $A - B = {TOY[5]} - m$ is a nonzero constant, and each of the other two is linear in $X$ with one root. So the difference has at most two roots, and the count of 2 in every case shows that the two roots never coincide here. '
    f'The proportion looks large only because the field has 43 elements.')

# --- the twin value, if the tested value were not absorbed
tw_i, tw_m = 5, TOY[5]
tw_a = tw_i + 1
tw_w = OMEGA2                     # the cube root of unity that differs from a = 6


def _twin_of(z):
    return (tw_w * ((tw_m + tw_a * z) % Q) - tw_a * z) % Q


# A challenge for which a, omega, z, m, az, m + az and the twin are seven different numbers,
# so that no symbol in the example can be mistaken for another.
tw_z = next(z for z in [Z] + list(range(2, Q))
            if len({tw_a, tw_w, z, tw_m, _twin_of(z), tw_a * z % Q, (tw_m + tw_a * z) % Q}) == 7
            and _twin_of(z) not in (0, 1))
tw_inner = (tw_m + tw_a * tw_z) % Q
tw = (tw_w * tw_inner - tw_a * tw_z) % Q
assert tw != tw_m and factor_at(tw_i, tw, tw_z) == factor_at(tw_i, tw_m, tw_z)
assert (tw + tw_a * tw_z) % Q == tw_w * tw_inner % Q
tw_count = [z for z in range(Q) if factor_at(tw_i, tw, z) == factor_at(tw_i, tw_m, z)]
assert tw_z in tw_count and len(tw_count) <= 3
frag['twin'] = (
    f'Take the one-factor `elapsed` polynomial for the value $m = {tw_m}$ at epoch 5, so $a = {tw_a}$, and let the challenge be $z = {tw_z}$. '
    f'Suppose $z$ did not depend on the value. A cheater could pick the cube root of unity $\\omega = {tw_w}$ and set\n\n'
    f'$$m\' = \\omega(m + az) - az = {tw_w}({tw_m} + {tw_a} \\cdot {tw_z}) - {tw_a} \\cdot {tw_z} = {tw_w} \\cdot {tw_inner} - {tw_a * tw_z % Q} = {tw}.$$\n\n'
    f'Then $m\' + az = \\omega(m + az)$, the two inner terms differ by the factor $\\omega$, and their cubes agree, so $F_{{5,{tw}}}({tw_z}) = F_{{5,{tw_m}}}({tw_z}) = {factor_at(tw_i, tw, tw_z)}$. '
    f'The step would open the bucket at {tw}, while `elapsed` records the factor for {tw_m}. '
    f'That direction is the harmful one, because the bucket can report {tw} absent while the segment vouches for {tw_m}, which might be a published nullifier.')

# ------------------------------------------------------ the 16-epoch window at scale
P2 = 65539
assert all(P2 % d for d in range(2, isqrt(P2) + 1)) and P2 % 3 == 1
assert (F - 1) % 3 != 0 and all(pow(x, 3, F) != pow(y, 3, F) for x, y in [(2, 3), (5, 7)])
assert len({pow(x, 3, F) for x in range(1, F)}) == F - 1
C2 = next(x for x in range(2, P2) if pow(x, (P2 - 1) // 3, P2) != 1)
assert all(NF[e] != 0 and NF[e] < P2 for e in range(16))
W16 = list(range(16))
D16 = [4, 5, 6]
C16 = [e for e in W16 if e not in D16]
assert len(C16) == 13


def seq_at(epochs, vals, z):
    out = 1
    for e in epochs:
        out = out * (pow((vals[e] + (e + 1) * z) % P2, 3, P2) - C2) % P2
    return out


Z2 = int.from_bytes(digest('Tachyon-toy-challenge', 'window', *[NF[e] for e in W16]), 'big') % P2
d2, c2, n2 = seq_at(D16, NF, Z2), seq_at(C16, NF, Z2), seq_at(W16, NF, Z2)
assert d2 * c2 % P2 == n2 and 0 not in (d2, c2, n2)
FORGE2 = dict(NF)
FORGE2[5] = (NF[5] + 1) % P2
pass2 = 0
for z in range(P2):
    if seq_at(D16, FORGE2, z) * seq_at(C16, NF, z) % P2 == seq_at(W16, NF, z):
        pass2 += 1
assert pass2 <= 48
BOUND2 = isqrt(P2 // 3)
assert BOUND2 > 16
frag['window16'] = '\n'.join([
    f'| Polynomial | Epochs | Factors | Degree | Value at $z = {Z2}$ |',
    '| --- | --- | --- | --- | --- |',
    f'| $\\Delta(X)$ | 4, 5, 6 | {len(D16)} | {3 * len(D16)} | {d2} |',
    f'| $C(X)$ | 0 to 3 and 7 to 15 | {len(C16)} | {3 * len(C16)} | {c2} |',
    f'| $N(X)$ | 0 to 15 | {len(W16)} | {3 * len(W16)} | {n2} |',
])
frag['window16-field'] = (
    f'The stand-in range of chapter 20 is the prime 65,537, and it cannot host this encoding. Since $65{{,}}536$ is not divisible by 3, cubing permutes that field and every element is a cube. '
    f'So this section works modulo the next prime with the right shape, {num(P2)}, which is 1 modulo 3 and whose smallest non-cube is $c = {C2}$. The nullifier values carry over unchanged.')
frag['window16-check'] = (
    f'The identity holds: ${d2} \\cdot {c2} \\equiv {n2} \\pmod{{65{{,}}539}}$. If the service instead tests {FORGE2[5]} at epoch 5, one more than the genuine {NF[5]}, '
    f'then trying all {num(P2)} challenges finds {pass2} that pass, against the degree bound of 48. The batch is well inside the injectivity bound here, which is $\\lfloor\\sqrt{{65{{,}}539/3}}\\rfloor = {BOUND2}$.')

# ----------------------------------------------------------------- sizes of an epoch
EPOCH_SECONDS = 4096 * 75
TWO_WEEKS = 14 * 86400
assert EPOCH_SECONDS == 307200
TG_PER_TX = 2 * 4 + 1  # four actions of two tachygrams each, plus the fee change note (chapter 1)
assert TG_PER_TX == 9
tg_code = 100 * EPOCH_SECONDS * TG_PER_TX
tg_book4 = 100 * TWO_WEEKS * 4
assert tg_book4 > 480_000_000 and tg_book4 < 490_000_000
_seal_start = POOL.h_ep(0, 0)
_seal_end = POOL.h_ep(POOL.final[0], 1)
assert _seal_start == POOL.entry[0] and _seal_end == POOL.entry[1]
frag['seal'] = (
    f'For our epoch, the step takes $\\mathsf{{anchor\\_final\\_prev}} = 0$ for epoch zero and checks the start against '
    f'$H_\\mathsf{{ep}}(0,\\ 0) = {_seal_start}$. The last intake ended on the final anchor {POOL.final[0]}, '
    f'so the step computes $H_\\mathsf{{ep}}({POOL.final[0]},\\ 1) = {_seal_end}$. The bucket covers the half-open range '
    f'from {_seal_start} to {_seal_end}, using the stand-in values of chapter 21.'
)

frag['scale'] = (
    f'Take chapter 1\'s hypothetical load of 100 two-input, two-output transactions per second, with {TG_PER_TX} tachygrams each. An epoch of the code\'s 4,096 blocks lasts {num(EPOCH_SECONDS)} seconds at 75 seconds per block, '
    f'so it holds {num(tg_code)} tachygrams, and $e(X)$ has that degree.')
TG_MAX = 50_000 * 8 * TWO_WEEKS
ROOTS_MAX = TG_MAX // 8000
DEPTH8 = ceil(log2(ROOTS_MAX))
assert TG_MAX < 4.84e11 and ROOTS_MAX < 6.1e7
assert 2 ** (DEPTH8 - 1) < ROOTS_MAX <= 2 ** DEPTH8 and DEPTH8 == 26
TG_MAX9 = 50_000 * TG_PER_TX * TWO_WEEKS
ROOTS_MAX9 = TG_MAX9 // 8000
DEPTH9 = ceil(log2(ROOTS_MAX9))
assert 2 ** (DEPTH9 - 1) < ROOTS_MAX9 <= 2 ** DEPTH9 and DEPTH9 == 27
frag['depth-budget'] = (
    f'The deep dive [sizes this](https://github.com/tachyon-zcash/tachyon/blob/7e502548db33845dbaacdc0efe905d1a3c45e626/book/src/revisit.md?plain=1#L1172-L1177) for 50,000 two-input, two-output transactions per second over a two-week epoch, at 8 tachygrams per transaction, which gives {num(TG_MAX)} tachygrams. '
    f'At 8,000 tachygrams per bucket that is {num(ROOTS_MAX)} buckets. A tree of profiles with that many leaves needs depth at least {DEPTH8}, '
    f'because $2^{{{DEPTH8 - 1}}} = {tnum(2 ** (DEPTH8 - 1))}$ is fewer than the bucket count and $2^{{{DEPTH8}}} = {tnum(2 ** DEPTH8)}$ is not. A balanced network reaches exactly that depth, well inside the 32 positions the header allows.')
frag['counts-box'] = (
    f'**Deep dive:** its figure of more than 480,000,000 tachygrams per epoch matches {num(tg_book4)}, which is 100 transactions per second over two weeks at 4 tachygrams per transaction, one per input and output. Its depth estimate uses 8 per transaction, two for each of the 4 actions.\n\n'
    f'**This site:** we follow chapter 1 and count {TG_PER_TX}, which adds the fee change note, and we use the code\'s epoch of 4,096 blocks. At {TG_PER_TX} per transaction the deep dive\'s sizing gives {num(ROOTS_MAX9)} buckets and a depth of at least {DEPTH9}, which also fits in 32 positions.')

# ------------------------------------------------------------- quadratic residues
SQUARES = sorted({x * x % Q for x in range(1, Q)})
assert len(SQUARES) == 21
NQR = next(x for x in range(2, Q) if x not in SQUARES)
assert NQR == 2
assert pow(5, (PALLAS_P - 1) // 2, PALLAS_P) == PALLAS_P - 1
assert all(pow(x, (PALLAS_P - 1) // 2, PALLAS_P) == 1 for x in (2, 3, 4))
assert all((NQR * s % Q) not in SQUARES for s in SQUARES)
assert all((NQR * s % Q) in SQUARES for s in range(1, Q) if s not in SQUARES)
frag['squares'] = (
    f'In $\\F_{{43}}$ the nonzero squares are {", ".join(map(str, SQUARES))}, which is half of the 42 nonzero elements. The smallest non-residue is $n = {NQR}$, and multiplying by it swaps the two halves. '
    f'For example, $9$ is a square, and ${NQR} \\cdot 9 = {NQR * 9 % Q}$ is not. The value $3$ is not a square, and ${NQR} \\cdot 3 = {NQR * 3 % Q}$ is. So every nonzero $s$ has a root $y$ with either $y^2 = s$ or $y^2 = {NQR}s$, and never both. '
    f'The code uses $n = 5$, which is the [smallest non-residue of the real field](https://github.com/tachyon-zcash/tachyon/blob/7e502548db33845dbaacdc0efe905d1a3c45e626/crates/tachyon/src/collections/qr.rs#L33-L37).')


def is_sq(s):
    return s % Q in SQUARES


def side(x, R):
    s = (x + R) % Q
    return 1 if s == 0 or is_sq(s) else 0


def kappa(b):
    return 1 if b else NQR


def root_of(x, R, b=None):
    s = (x + R) % Q
    b = side(x, R) if b is None else b
    t = kappa(b) * s % Q
    return min(y for y in range(Q) if y * y % Q == t)


# ---------------------------------------------------- the epoch of chapter 21
STAMPS = {'A': [22, 24, 40], 'B': [20, 23, 41], 'C': [13, 19, 21]}
EPOCH = [x for s in STAMPS.values() for x in s]
e0 = roots_poly(EPOCH)
assert ev(e0, 41) == 0 and ev(e0, 4) == 37  # the published values of pool-state.md
ANCHOR = {'entry0': 29, 'final0': 26, 'entry1': 40, 'entry2': 18}
ABSENT, PRESENT = 4, 41
CAP = 4


def interp(points):
    out = [0]
    for i, (xi, yi) in enumerate(points):
        term = [yi]
        for j, (xj, _) in enumerate(points):
            if i != j:
                inv = pow(xi - xj, -1, Q)
                term = pmul(term, [(-xj * inv) % Q, inv])
        out = [(a + b) % Q for a, b in zip(out + [0] * (len(term) - len(out)), term + [0] * (len(out) - len(term)))]
    return trim(out)


def sub(a, b):
    n_ = max(len(a), len(b))
    return trim([((a[i] if i < len(a) else 0) - (b[i] if i < len(b) else 0)) % Q for i in range(n_)])


def route(R0, cap=CAP):
    """One network: split every unresolved intake, then merge same-profile neighbours."""
    layer = [{'profile': '', 'members': list(v), 'span': (i, i + 1), 'names': k}
             for i, (k, v) in enumerate(STAMPS.items())]
    history = [[dict(x) for x in layer]]
    final = []
    depth = 0
    while layer and depth < 12:
        groups = {}
        for it in layer:
            groups.setdefault(it['profile'], []).append(it)
        todo = []
        for p, its in groups.items():
            if len(its) == 1 and its[0]['span'] == (0, 3):
                final.append(its[0])
            else:
                todo.extend(its)
        if not todo:
            break
        out = []
        for it in todo:
            for b in (0, 1):
                out.append({'profile': it['profile'] + str(b),
                            'members': [x for x in it['members'] if side(x, R0 + len(it['profile'])) == b],
                            'span': it['span'], 'names': it['names']})
        out.sort(key=lambda it: (it['profile'], it['span']))
        merged = []
        for it in out:
            if merged and merged[-1]['profile'] == it['profile'] and merged[-1]['span'][1] == it['span'][0] \
                    and len(merged[-1]['members']) + len(it['members']) <= cap:
                merged[-1] = {'profile': it['profile'], 'members': merged[-1]['members'] + it['members'],
                              'span': (merged[-1]['span'][0], it['span'][1]), 'names': merged[-1]['names'] + it['names']}
            else:
                merged.append(it)
        layer = merged
        history.append([dict(x) for x in layer])
        depth += 1
    return final, history


def split_parts(v, r0):
    sib = [x for x in v if side(x, r0) == 0]
    s_ = roots_poly(sib)
    u_ = interp([(x, root_of(x, r0)) for x in sib])
    h_ = pdivmod(sub(pmul(u_, u_), [NQR * r0 % Q, NQR]), s_)[0]
    return [commit(s_), commit(u_), commit(h_)]


def good(R0):
    if any((x + R0 + j) % Q == 0 for x in EPOCH + [ABSENT] for j in range(2)):
        return False
    final, hist = route(R0)
    if sorted(len(b['profile']) for b in final) != [1, 2, 2]:
        return False
    if not all(b['members'] for b in final):
        return False
    pa = bucket_for(ABSENT, final, R0)
    pp = bucket_for(PRESENT, final, R0)
    if pa is pp or PRESENT not in pp['members'] or len(pa['members']) < 2 or len(pa['profile']) != 2 or pa['profile'] == '00':
        return False
    coms = [commit(roots_poly(b['members'])) for b in final]
    if len(set(coms)) != 3 or None in coms:
        return False
    # One stamp has at least two non-residue members and a residue member, and
    # the commitments of its split are distinct and differ from the four base generators.
    for v in STAMPS.values():
        sib = [x for x in v if side(x, R0) == 0]
        if 2 <= len(sib) < len(v):
            parts = split_parts(v, R0)
            if None not in parts and len(set(parts)) == 3 and not set(parts) & set(G):
                return True
    return False


def bucket_for(x, final, R0):
    for b in final:
        if all(side(x, R0 + j) == int(c) for j, c in enumerate(b['profile'])):
            return b
    raise AssertionError


R0 = next(r for r in range(2, Q) if good(r))
FINAL, HIST = route(R0)
FINAL.sort(key=lambda b: (len(b['profile']), b['profile']))
assert sorted(x for b in FINAL for x in b['members']) == sorted(EPOCH)
assert all(len(b['members']) <= CAP for b in FINAL)
assert all(b['span'] == (0, 3) for b in FINAL)
# A product of the buckets is the epoch polynomial.
assert pprod([roots_poly(b['members']) for b in FINAL]) == e0

frag['classify'] = '\n'.join(
    [f'| Tachygram $x$ | Stamp | $x + R_0$ | Side at $R_0 = {R0}$ | Root | $x + R_1$ | Side at $R_1 = {R0 + 1}$ |',
     '| --- | --- | --- | --- | --- | --- | --- |']
    + [f'| {x} | {k} | {(x + R0) % Q} | {side(x, R0)} | {root_of(x, R0)} | {(x + R0 + 1) % Q} | {side(x, R0 + 1)} |'
       for k, v in STAMPS.items() for x in v])
exc = (-R0) % Q
assert all(root_of(exc, R0, b) == 0 for b in (0, 1)) and exc not in EPOCH
frag['exceptional'] = (
    f'The exceptional value at our discriminant is $x = -R_0 = {exc}$. Its shifted value is 0, so $y = 0$ satisfies $y^2 = 1 \\cdot 0$ and also $y^2 = {NQR} \\cdot 0$, which means a root alone would let it sit on either side.')

# -------------------------------------------------------------- proving one split
STAMP_NAME = next(k for k, v in STAMPS.items()
                  if 2 <= len([x for x in v if side(x, R0) == 0]) < len(v)
                  and None not in split_parts(v, R0) and len(set(split_parts(v, R0))) == 3
                  and not set(split_parts(v, R0)) & set(G))
PARENT = STAMPS[STAMP_NAME]
SIB = [x for x in PARENT if side(x, R0) == 0]
CHILD = [x for x in PARENT if side(x, R0) == 1]
pts = [(x, root_of(x, R0)) for x in SIB]


s_poly = roots_poly(SIB)
child_poly = roots_poly(CHILD)
u_poly = interp(pts)
assert all(ev(u_poly, x) == y for x, y in pts)
target = sub(pmul(u_poly, u_poly), [NQR * R0 % Q, NQR])
h_poly, rem_h = pdivmod(target, s_poly)
assert rem_h == [0]
assert pmul(s_poly, child_poly) == roots_poly(PARENT)
cs, cu, ch = commit(s_poly), commit(u_poly), commit(h_poly)
Z3 = challenge(cs, cu, ch, R0)
assert Z3 not in SIB and Z3 != 0
lhs = (ev(u_poly, Z3) ** 2 - NQR * (Z3 + R0)) % Q
rhs = ev(s_poly, Z3) * ev(h_poly, Z3) % Q
assert lhs == rhs
pts_txt = ', '.join(f'$u({x}) = {y}$' for x, y in pts)
frag['split-run'] = (
    f'Take stamp {STAMP_NAME} as an intake, with members {", ".join(map(str, PARENT))}. At $R_0 = {R0}$ its non-residue side is $s(X) = {pshow(s_poly)}$, with roots {", ".join(map(str, SIB))}, '
    f'and its residue side is ${pshow(child_poly)}$. To descend into the residue side, the prover attests the sibling $s$ at $\\kappa = n = {NQR}$. The roots from the table give {pts_txt}, so $u(X) = {pshow(u_poly)}$. Then\n\n'
    f'$$\\begin{{aligned}}u(X)^2 - {NQR}(X + {R0}) &= {pshow(target)} \\\\\n&= ({pshow(s_poly)}) \\cdot ({pshow(h_poly)}),\\end{{aligned}}$$\n\n'
    f'so $h(X) = {pshow(h_poly)}$, a constant here because $s$ has degree 2. The commitments are $\\mathsf{{Com}}(s) = {show(cs)}$, $\\mathsf{{Com}}(u) = {show(cu)}$, and $\\mathsf{{Com}}(h) = {show(ch)}$. A stand-in hash of those and $R_0$ gives $z = {Z3}$, where both sides equal {lhs}.')

# --- hiding a member from its own bucket
HIDE = CHILD[0]
s_bad = roots_poly(SIB + [HIDE])
need = NQR * (HIDE + R0) % Q
assert need not in SQUARES and need != 0
max_pass, exact = 0, 0
for y in range(Q):
    u2 = interp(pts + [(HIDE, y)])
    t2 = sub(pmul(u2, u2), [NQR * R0 % Q, NQR])
    h2, r2 = pdivmod(t2, s_bad)
    if r2 == [0]:
        exact += 1
    count = sum(1 for z in range(Q) if (ev(u2, z) ** 2 - NQR * (z + R0) - ev(s_bad, z) * ev(h2, z)) % Q == 0)
    max_pass = max(max_pass, count)
assert exact == 0 and max_pass <= 2
frag['split-cheat'] = (
    f'Suppose a cheater wants {HIDE} missing from the residue child, because later it will claim that {HIDE} is absent. It moves {HIDE} into the sibling, so the sibling polynomial gains the root {HIDE}. '
    f'The identity then needs $u({HIDE})^2 = {NQR}({HIDE} + {R0}) = {need}$, and {need} is not a square, so no $u$ exists. Trying all 43 values for $u({HIDE})$ and taking the quotient by long division, {exact} of them divide exactly, and the best attempt passes {max_pass} of the 43 challenges.')

# ------------------------------------------------------------------- routing
rows = ['| Round | Discriminant | Intakes, as profile: members (stamps covered) |', '| --- | --- | --- |']
for d, layer in enumerate(HIST):
    cells = '; '.join(f"`{it['profile'] or 'root'}`: {', '.join(map(str, it['members'])) or 'empty'} ({it['names']})" for it in layer)
    label = 'start' if d == 0 else str(d)
    disc = '' if d == 0 else f'$R_{{{d - 1}}} = {R0 + d - 1}$'
    rows.append(f'| {label} | {disc} | {cells} |')
frag['routing'] = '\n'.join(rows)
A_sides = {x: side(x, R0) for x in STAMPS['A']}
B_sides = {x: side(x, R0) for x in STAMPS['B']}
C_sides = {x: side(x, R0) for x in STAMPS['C']}
def _by(sd, b):
    return ', '.join(str(x) for x, v in sd.items() if v == b)
n0 = [len([x for x in STAMPS[k] if side(x, R0) == 0]) for k in 'ABC']
n1 = [len([x for x in STAMPS[k] if side(x, R0) == 1]) for k in 'ABC']
assert n0[0] + n0[1] <= CAP < n0[0] + n0[1] + n0[2] and sum(n1) <= CAP
frag['routing-walk'] = (
    f'Round 1 uses $R_0 = {R0}$. The classification table puts stamp A\'s values {_by(A_sides, 0)} on side 0 and {_by(A_sides, 1)} on side 1, '
    f'so the split step turns intake A into a `0` intake holding {_by(A_sides, 0)} and a `1` intake holding {_by(A_sides, 1)}. '
    f'Stamp B gives `0`: {_by(B_sides, 0)} and `1`: {_by(B_sides, 1)}, and stamp C gives `0`: {_by(C_sides, 0)} and `1`: {_by(C_sides, 1)}. '
    f'The merge step then works through each profile from left to right. Among the `0` intakes, A and B meet and hold {n0[0] + n0[1]} values together, so they merge. '
    f'Adding C would make {n0[0] + n0[1] + n0[2]}, which is over the capacity of {CAP}, so C stays apart. '
    f'The three `1` intakes hold {sum(n1)} values in all, so they merge into one intake covering A, B and C.')
assert len(HIST) == 3
_r1 = HIST[1]
_fin1 = next(it['profile'] for it in _r1 if it['span'] == (0, 3))
_open1 = next(it['profile'] for it in _r1 if it['span'] != (0, 3))
assert [it['profile'] for it in _r1].count(_open1) == 2 and all(it['span'] != (0, 3) for it in _r1 if it['profile'] == _open1)
assert sorted(it['profile'] for it in HIST[2]) == [_open1 + '0', _open1 + '1'] and all(it['span'] == (0, 3) for it in HIST[2])
frag['routing-result'] = (
    f'With a capacity of {CAP} per intake the network ends with {len(FINAL)} buckets: '
    + ', '.join(f"`{b['profile']}` holding {', '.join(map(str, b['members']))}" for b in FINAL)
    + f'. Multiplying the three bucket polynomials gives back the epoch polynomial $e_0(X)$ of chapter 21, and no bucket has degree above {CAP}, where $e_0$ has degree {len(EPOCH)}.\n\n'
    + f'The buckets have different depths. After round 1 the `{_fin1}` intake spans all three stamps, so step 3 makes it final, and it does not appear in the round 2 row. '
    + f'Profile `{_open1}` still had two intakes after round 1, neither spanning the epoch, so only that branch went through another round. '
    + f'In round 2 both `{_open1}` intakes split at $R_1$, the two `{_open1}0` pieces merge, the two `{_open1}1` pieces merge, and each result spans the epoch, which ends the network.')

# Balance over the choice of R0, and what a grinder could do with R0 in hand.
loads = []
for r in range(Q):
    counts = {}
    for x in EPOCH:
        key = (side(x, r), side(x, r + 1))
        counts[key] = counts.get(key, 0) + 1
    loads.append(max(counts.values()))
best_prof = (1, 1)
same = [x for x in range(1, Q) if (side(x, R0), side(x, R0 + 1)) == best_prof]
assert len(same) >= 9
frag['grind'] = (
    f'Across all 43 choices of $R_0$, the fullest of the four depth-2 classes holds on average {sum(loads) / len(loads):.1f} of our 9 tachygrams. With $R_0 = {R0}$ known in advance, a user could publish 9 of the {len(same)} field elements with profile `11` and fill that class alone.')

# ------------------------------------------------------------- testing a value
bA = bucket_for(ABSENT, FINAL, R0)
bP = bucket_for(PRESENT, FINAL, R0)
polyA, polyP = roots_poly(bA['members']), roots_poly(bP['members'])
assert ev(polyA, ABSENT) != 0 and ev(polyP, PRESENT) == 0 and ev(e0, ABSENT) != 0
sides_abs = [side(ABSENT, R0 + j) for j in range(len(bA['profile']))]
assert ''.join(map(str, sides_abs)) == bA['profile']
frag['open-absent'] = (
    f'Test the value {ABSENT}, which chapter 21 found absent from this epoch. Its shifted values are ${ABSENT} + {R0} = {(ABSENT + R0) % Q}$ and ${ABSENT} + {R0 + 1} = {(ABSENT + R0 + 1) % Q}$, and these give it the sides '
    f'{", ".join(map(str, [side(ABSENT, R0), side(ABSENT, R0 + 1)]))}. So its bucket is `{bA["profile"]}`, whose polynomial is $q(X) = {pshow(polyA)}$, and $q({ABSENT}) = {ev(polyA, ABSENT)}$ is nonzero. '
    f'One opening of a polynomial of degree {len(bA["members"])} has replaced an opening of degree {len(EPOCH)}.')
others = [b for b in FINAL if b is not bP]
open_other = [(b['profile'], ev(roots_poly(b['members']), PRESENT)) for b in others]
assert all(v != 0 for _, v in open_other)
frag['open-present'] = (
    f'Now test {PRESENT}, which stamp B published. Its sides lead to bucket `{bP["profile"]}`, where $q({PRESENT}) = {ev(polyP, PRESENT)}$, so the nonzero check fails and no proof exists. '
    f'This is why the step must force the profile to match. Opened against the other buckets, {PRESENT} gives '
    + ' and '.join(f'{v} in `{p}`' for p, v in open_other)
    + ', both nonzero, so without the profile check a cheater could prove absence of a value that was published.')
# The mask and the fold.
d = 2
masks = [m for m in combinations(range(32), d)]
ok = [m for m in masks if 2 * sum(m) == d * (d - 1)]
assert ok == [(0, 1)] and len(masks) == 496


def fold(bits, mask):
    a = 0
    steps = []
    for j, b in enumerate(bits):
        a = a + mask[j] * (a + b)
        steps.append(a)
    return steps


value_sides = [side(ABSENT, R0 + j) for j in range(4)]
steps = fold(value_sides, [1, 1, 0, 0])
assert steps[-1] == int(bA['profile'], 2) and len(bA['profile']) == 2
frag['mask'] = (
    f'For depth 2 there are {len(masks)} ways to set two mask bits among 32 positions. The index sum must equal $d(d-1)/2 = 1$, and only the prefix $\\{{0, 1\\}}$ does. '
    f'For the value {ABSENT}, the first four sides are {", ".join(map(str, value_sides))}, and the fold starts from $t_0 = 0$. Under the mask it gives $t_1, \\ldots, t_4 = {", ".join(map(str, steps))}$, because the first two steps append a side and the last two leave $t$ unchanged. It ends at {steps[-1]}, the integer that encodes `{bA["profile"]}`. The sides past the depth are computed and ignored.')

# ------------------------------------------------------- a segment across two epochs
V1 = 33
assert V1 != ABSENT
seg0 = factor(0, ABSENT)
seg1 = pmul(seg0, factor(1, V1))
assert factor_at(0, ABSENT, 3) == ev(seg0, 3)
frag['segment'] = '\n'.join([
    '| Step | Value tested | Epochs covered | Anchors covered | `elapsed` |',
    '| --- | --- | --- | --- | --- |',
    f'| `QrUnspentInit` on bucket `{bA["profile"]}` of epoch 0 | {ABSENT} | $[0, 1)$ | $[{ANCHOR["entry0"]}, {ANCHOR["entry1"]})$ | ${pshow(seg0)}$ |',
    f'| `UnspentLift` on the empty bucket of epoch 1 | {V1} | $[0, 2)$ | $[{ANCHOR["entry0"]}, {ANCHOR["entry2"]})$ | ${pshow(seg1)}$ |',
])

# -------------------------------------------------------------- the evidence tree
def leaf(b, label=None):
    prof = b['profile'] if label is None else label
    c = commit(roots_poly(b['members']))
    return H('Tachyon-QrBucket', 0, ANCHOR['entry0'], ANCHOR['entry1'], R0, len(prof), int(prof, 2), c)


leaves = [leaf(b) for b in FINAL]
slots = leaves + [leaves[-1]]
assert len(slots) == 4 and len(set(leaves)) == 3
root = H('Tachyon-EvidNode', *slots)
bad_label = leaf(others[0], label=bP['profile'])
assert bad_label not in slots
assert ev(roots_poly(others[0]['members']), PRESENT) != 0
frag['tree'] = '\n'.join(
    ['| Slot | Bucket | Commitment | Leaf digest (stand-in) |', '| --- | --- | --- | --- |']
    + [f"| {i} | `{b['profile']}` | ${show(commit(roots_poly(b['members'])))}$ | {slots[i]} |"
       for i, b in enumerate(FINAL + [FINAL[-1]])])
frag['tree-root'] = (
    f'The node over these four slots hashes to the root {root}, and this one value stands for all the buckets. To serve a query for bucket `{bA["profile"]}`, a proof step takes the four children as witnesses, rehashes them to {root}, '
    f'and then checks the bucket\'s fields against slot {slots.index(leaf(bA))}\'s digest.')
frag['tree-cheat'] = (
    f'Suppose the leaf did not bind the profile, and a builder wanted to prove the published value {PRESENT} absent. It could offer the contents of bucket `{others[0]["profile"]}` under the label `{bP["profile"]}`. The profile check would pass, because the label is {PRESENT}\'s true profile, '
    f'and the opening would give {ev(roots_poly(others[0]["members"]), PRESENT)}, which is nonzero. With the profile in the leaf, that combination digests to {bad_label}, which matches none of the slots, so the path check rejects it.')

# ------------------------------------------------------------------ what the service sees
LIST = [NF[e] for e in (4, 5, 6)]
PUB = [13229, 24937, 30698, 31831, 40944, 46656, 55113, 55356, 61177]  # the bundle of chapter 20
assert NF[7] in PUB and NF[8] in PUB and not set(LIST) & set(PUB)
LIST2 = LIST + [NF[7]]
assert set(LIST2) & set(PUB) == {NF[7]}
frag['service-scan'] = (
    f'Alice\'s spend sits in the bundle of [chapter 20](./notes-and-nullifiers.md#_11-tachygrams-and-output-padding), which publishes {", ".join(map(str, PUB))}. A service holding the list {", ".join(map(str, LIST))} for epochs 4 to 6 compares that list with the bundle and finds no match. '
    f'If Alice had also delegated epoch 7, the service would hold {NF[7]} and would see it published, which would tie her request to this bundle.')

print(json.dumps(frag))
