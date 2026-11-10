"""Worked example for statements-and-challenges.md. Prints fragments as JSON."""
import hashlib
import json
from math import gcd

from toy_curve import G, Q, add, mul, show

frag = {}
GEN = G[0]


def neg(a):
    return None if a is None else (a[0], -a[1] % 31)


def sub(a, c):
    return add(a, neg(c))


def poly_eval(c, at, m=Q):
    out = 0
    for e in reversed(c):
        out = (out * at + e) % m
    return out


def poly_mul(a, c):
    out = [0] * (len(a) + len(c) - 1)
    for i, e in enumerate(a):
        for j, f in enumerate(c):
            out[i + j] = (out[i + j] + e * f) % Q
    return out


def poly_add(a, c):
    size = max(len(a), len(c))
    return [((a[i] if i < len(a) else 0) + (c[i] if i < len(c) else 0)) % Q for i in range(size)]


def poly_str(c, var='X'):
    terms = []
    for i, e in enumerate(c):
        if e % Q == 0:
            continue
        coeff = '' if (e % Q == 1 and i) else str(e % Q)
        terms.append(coeff if i == 0 else coeff + (var if i == 1 else f'{var}^{i}'))
    return ' + '.join(terms) if terms else '0'


def divide_linear(c, root):
    """Synthetic division by (X - root). Returns the quotient and remainder."""
    out = [0] * (len(c) - 1)
    carry = 0
    for i in range(len(c) - 1, 0, -1):
        carry = (c[i] + carry * root) % Q
        out[i - 1] = carry
    return out, (c[0] + carry * root) % Q


def vec(v):
    return '(' + ', '.join(str(e % Q) for e in v) + ')'


# Section 1: relations
def circuit(x):
    return (x ** 3 + x + 5) % Q


TARGET = 35
witnesses = [x for x in range(Q) if circuit(x) == TARGET]
assert 3 in witnesses
frag['cubic-witnesses'] = (
    f'Evaluating $x^3 + x + 5$ at all 43 elements of $\\F_{{43}}$ finds that the value 35 occurs '
    + (f'only at $x = {witnesses[0]}$, so our $x = {witnesses[0]}$ is the only witness for this instance. ' if len(witnesses) == 1 else
       f'at $x \\in \\{{{", ".join(map(str, witnesses))}\\}}$. '
       f'This instance therefore has {len(witnesses)} witnesses, and the relation accepts any of them. ')
    + f'The value $x = 4$ gives ${circuit(4)}$, so the pair $(35, 4)$ falls outside the relation. '
    + f'Some instances have no witness at all, and the instance {next(t for t in range(1, Q) if t not in {circuit(x) for x in range(Q)})} is one of them.')

a = 12
P = mul(a, GEN)
assert P not in G and P is not None
frag['dlog-instance'] = (f'Take the public generator $G = {show(GEN)}$ and the secret scalar $a = {a}$, which give the instance $P = {a} \\cdot G = {show(P)}$. '
                         f'The relation holds for the pair $(P, {a})$ because recomputing ${a} \\cdot G$ yields $P$. The pair $(P, {a + 1})$ falls outside it, since ${a + 1} \\cdot G = {show(mul(a + 1, GEN))}$.')

# Section 3: Schnorr
r, c = 29, 16
R = mul(r, GEN)
s = (r + c * a) % Q
assert R is not None and s != 0
cP = mul(c, P)
assert mul(s, GEN) == add(R, cP)
frag['schnorr-run'] = '\n'.join([
    '| Step | Party | Value |', '| --- | --- | --- |',
    f'| 1 | Prover picks a mask and sends $R$ | $r = {r}$, $R = {r} \\cdot G = {show(R)}$ |',
    f'| 2 | Verifier sends a random challenge | $c = {c}$ |',
    f'| 3 | Prover sends the response | $s = {r} + {c} \\cdot {a} = {s}$ modulo 43 |',
    f'| 4 | Verifier computes the left side | $s \\cdot G = {s} \\cdot G = {show(mul(s, GEN))}$ |',
    f'| 5 | Verifier computes the right side | $R + c \\cdot P = {show(R)} + {show(cP)} = {show(add(R, cP))}$ |',
])

# Forgery with an early challenge, using only public data
fs_ = 23
fR = sub(mul(fs_, GEN), mul(c, P))
assert fR is not None and add(fR, mul(c, P)) == mul(fs_, GEN)
frag['schnorr-early'] = (f'Suppose a cheater holds only the public point $P = {show(P)}$ and learns in advance that $c = {c}$. It picks the response $s = {fs_}$ first, '
                         f'and then computes $R = {fs_} \\cdot G - {c} \\cdot P = {show(fR)}$. The check passes because $s \\cdot G = {show(mul(fs_, GEN))}$ and $R + c \\cdot P = {show(add(fR, cP))}$. '
                         f'The cheater never used $a$.')

# A fixed response passes for exactly one challenge
G_multiples = [mul(k, GEN) for k in range(Q)]
P_multiples = [mul(k, P) for k in range(Q)]
all_points = list(G_multiples)
counts = {}
for pt in all_points:
    for k in range(Q):
        passing = sum(1 for e in range(Q) if add(pt, P_multiples[e]) == G_multiples[k])
        counts[passing] = counts.get(passing, 0) + 1
assert counts == {1: Q * Q}
frag['schnorr-count'] = (f'We can test this on all ${Q} \\times {Q} = {Q * Q}$ pairs $(R, s)$, trying every one of the {Q} challenges against each pair. '
                         f'Every pair passes for exactly one challenge. A cheater who fixes $R$ and prepares one response therefore succeeds with probability $1/{Q}$.')

c1, c2 = c, 31
s1 = s
s2 = (r + c2 * a) % Q
assert mul(s2, GEN) == add(R, mul(c2, P)) and s1 != s2
recovered = (s1 - s2) * pow(c1 - c2, -1, Q) % Q
assert recovered == a
frag['schnorr-extract'] = (f'Keep $R = {show(R)}$. The prover answers $c = {c1}$ with $s = {s1}$ and answers $c\' = {c2}$ with $s\' = {s2}$. '
                           f'The difference gives $s - s\' = {(s1 - s2) % Q}$ and $c - c\' = {(c1 - c2) % Q}$ modulo 43, and dividing gives ${(s1 - s2) % Q} / {(c1 - c2) % Q} = {recovered}$, which is the secret $a$.')

real = {(mul(u, GEN), (u + c * a) % Q) for u in range(Q)}
sim = {(sub(mul(v, GEN), cP), v) for v in range(Q)}
assert real == sim and {pair[1] for pair in real} == set(range(Q))
r_alt = 8
s_alt = (r_alt + c * a) % Q
frag['schnorr-mask'] = (f'Fix $c = {c}$ and let the mask $r$ range over $\\F_{{43}}$. The response $s = r + {c} \\cdot {a}$ takes each of the 43 values exactly once, with $r = {r}$ giving ${s}$ and $r = {r_alt}$ giving ${s_alt}$, for example. '
                        f'We also listed the 43 pairs $(R, s)$ an honest prover can produce for this challenge, and the 43 pairs a simulator produces by picking $s$ first and computing $R = s \\cdot G - c \\cdot P$. The two lists contain the same pairs.')

# Section 4: factor theorem
pc = [7, 2, 5, 3]
qc = [3, 1, 8, 4]
at = 9
y = poly_eval(pc, at)
shifted = [(pc[0] - y) % Q] + pc[1:]
quot, rem = divide_linear(shifted, at)
assert rem == 0 and poly_mul([-at % Q, 1], quot) == shifted
frag['factor'] = (f'Take $p(X) = {poly_str(pc)}$ over $\\F_{{43}}$. Its value at ${at}$ is $p({at}) = {y}$, so subtracting gives $f(X) = p(X) - {y} = {poly_str(shifted)}$, which has a root at ${at}$. '
                  f'Dividing $f$ by $X - {at}$ leaves no remainder, so $f(X) = (X - {at})({poly_str(quot)})$, and the second factor has degree {len(quot) - 1}, one less than $f$.')

peel = [2]
for t in (1, 2, 3):
    peel = poly_mul(peel, [-t % Q, 1])
peel_rows = ['| Step | Polynomial | Degree | Root removed |', '| --- | --- | --- | --- |']
cur = peel
peel_rows.append(f'| Start | ${poly_str(cur)}$ | 3 | |')
for idx, t in enumerate((1, 2, 3)):
    cur, rem = divide_linear(cur, t)
    assert rem == 0
    peel_rows.append(f'| {idx + 1} | ${poly_str(cur)}$ | {len(cur) - 1} | {t} |')
assert cur == [2]
assert [t for t in range(Q) if poly_eval(peel, t) == 0] == [1, 2, 3]
frag['peel'] = '\n'.join(peel_rows) + (f'\n\nThe constant 2 has no roots, so the process stops after three steps. Evaluating the starting polynomial at all 43 points confirms that its roots are exactly 1, 2 and 3.')

roots8 = [t for t in range(8) if (t * t - 1) % 8 == 0]
assert roots8 == [1, 3, 5, 7]
frag['ring'] = (f'Work modulo 8, which is not a prime. The degree-2 polynomial $X^2 - 1$ has the {len(roots8)} roots ${", ".join(map(str, roots8))}$, more than its degree allows over a field.')
assert (3 - 1) * (3 + 1) % 8 == 0 and (3 + 1) % 8 != 0
frag['ring-detail'] = (f'Peeling the root 1 gives $X^2 - 1 = (X - 1)(X + 1)$. At $X = 3$ the product is $(3 - 1)(3 + 1) = 2 \\cdot 4 = 0$ modulo 8, although neither factor is zero. '
                       f'So 3 is a root of $X^2 - 1$ without being a root of the remaining factor $X + 1$, and the step that carries every other root into $g$ fails.')

# Every monic cubic over F_43
powers = [[pow(x, i, Q) for i in range(4)] for x in range(Q)]
tally = {}
for c0 in range(Q):
    for c1_ in range(Q):
        for c2_ in range(Q):
            n_roots = sum(1 for x in range(Q) if (c0 + c1_ * x + c2_ * powers[x][2] + powers[x][3]) % Q == 0)
            tally[n_roots] = tally.get(n_roots, 0) + 1
assert sum(tally.values()) == Q ** 3 and max(tally) == 3 and set(tally) == {0, 1, 2, 3}
frag['root-tally'] = '\n'.join(
    ['| Distinct roots | Monic cubics over $\\F_{43}$ | Share |', '| --- | --- | --- |']
    + [f'| {k} | {tally[k]} | {tally[k] / Q ** 3:.3f} |' for k in sorted(tally)]
) + (f'\n\nThe counts add up to $43^3 = {Q ** 3}$, and no polynomial reaches 4 roots.')

# Section 4: testing a product
honest = poly_mul(pc, qc)


def roots_prod(*factors):
    out = [1]
    for t in factors:
        out = poly_mul(out, [-t % Q, 1])
    return out


errors = [
    ('$5$', [5]),
    ('$X - 4$', roots_prod(4)),
    ('$X^2 + 1$', [1, 0, 1]),
    ('$(X-1)(X-2)(X-3)$', roots_prod(1, 2, 3)),
    ('$(X-1)(X-2)(X-3)(X-4)(X-5)(X-6)$', roots_prod(1, 2, 3, 4, 5, 6)),
]
test_rows = ['| Error $e = r\' - p \\cdot q$ | Points where the test passes | Pass rate | Bound $6/43$ |', '| --- | --- | --- | --- |']
for name, e in errors:
    forged = poly_add(honest, e)
    assert len(forged) == 7
    agree = [x for x in range(Q) if poly_eval(pc, x) * poly_eval(qc, x) % Q == poly_eval(forged, x)]
    assert len(agree) <= 6 and agree == [x for x in range(Q) if poly_eval(e, x) == 0]
    test_rows.append(f'| {name} | {len(agree)} | {len(agree) / Q:.3f} | {6 / Q:.3f} |')
at_test = 9
assert poly_eval(pc, at_test) * poly_eval(qc, at_test) % Q == poly_eval(honest, at_test)
school = len(pc) * len(qc)
horner = [len(pc) - 1, len(qc) - 1, len(honest) - 1]
frag['product-honest'] = (f'Let $p(X) = {poly_str(pc)}$ and $q(X) = {poly_str(qc)}$. Their product is $r(X) = {poly_str(honest)}$, and writing it out by the schoolbook method takes {school} multiplications of coefficients. At the point ${at_test}$, '
                          f'$p({at_test}) = {poly_eval(pc, at_test)}$ and $q({at_test}) = {poly_eval(qc, at_test)}$, whose product is ${poly_eval(honest, at_test)}$ modulo 43, and $r({at_test}) = {poly_eval(honest, at_test)}$ as well, so the claim passes. '
                          f'Horner\'s rule evaluates $p$, $q$ and $r$ with {horner[0]}, {horner[1]} and {horner[2]} multiplications, and one more multiplies $p({at_test})$ by $q({at_test})$.')
frag['product-cheats'] = '\n'.join(test_rows)

known = 9
late = poly_add(honest, [-known % Q, 1])
assert poly_eval(late, known) == poly_eval(honest, known) and late != honest
frag['product-early'] = (f'If the prover knows the point ${known}$ in advance, it can send $r\'(X) = r(X) + (X - {known}) = {poly_str(late)}$. '
                         f'This polynomial differs from $r$, yet $r\'({known}) = {poly_eval(late, known)}$, so the test at ${known}$ passes.')

# Section 4: scale
d_exp, f_exp = 13, 254
p_pallas = 0x40000000000000000000000000000000224698fc094cf91b992d30ed00000001
q_pallas = 0x40000000000000000000000000000000224698fc0994a8dd8c46eb2100000001
assert p_pallas > 2 ** f_exp and q_pallas > 2 ** f_exp
frag['sz-scale'] = (f'With degree $d = 2^{{{d_exp}}}$ over a field with more than $2^{{{f_exp}}}$ elements, such as either Pasta field, the probability is below $2^{{{d_exp - f_exp}}}$.')

trivial = [x for x in range(Q) if (pow(x, Q, Q) - x) % Q == 0]
assert len(trivial) == Q
frag['degree-limit'] = (f'The polynomial $X^{{{Q}}} - X$ has degree {Q} and is not the zero polynomial, yet it evaluates to 0 at all {len(trivial)} points of $\\F_{{{Q}}}$. Its bound is ${Q}/{Q} = 1$, which promises nothing.')


# Section 5: several variables
def zeros(fn):
    return sum(1 for u in range(Q) for v in range(Q) if fn(u, v) % Q == 0)


rows2 = [
    ('$XY - 1$', 2, lambda u, v: u * v - 1),
    ('$(X - 1)(Y - 2)$', 2, lambda u, v: (u - 1) * (v - 2)),
    ('$(X - 1)(X - 2)$', 2, lambda u, v: (u - 1) * (u - 2)),
    ('$X^3 + X^2 + Y^3 - 5$', 3, lambda u, v: u ** 3 + u ** 2 + v ** 3 - 5),
    ('$(Y - 5)(X^2 - Y)$', 3, lambda u, v: (v - 5) * (u ** 2 - v)),
]
table = ['| Polynomial | Total degree $d$ | Zeros among $(x, y)$ | Limit $d \\cdot 43$ |', '| --- | --- | --- | --- |']
biv_counts = []
for name, deg, fn in rows2:
    count = zeros(fn)
    biv_counts.append(count)
    assert count <= deg * Q
    table.append(f'| {name} | {deg} | {count} | {deg * Q} |')
assert biv_counts[2] == 2 * Q
frag['biv-table'] = '\n'.join(table) + (f'\n\nThe third row reaches the limit exactly. It ignores $Y$ and vanishes on two whole columns of the grid, so the bound cannot be improved in general.')

bad_row = [u for u in range(Q) if (5 - 5) * (u * u - 5) % Q == 0]
other = {v: [u for u in range(Q) if (v - 5) * (u * u - v) % Q == 0] for v in range(Q) if v != 5}
assert len(bad_row) == Q and max(len(z) for z in other.values()) == 2
other_total = sum(len(z) for z in other.values())
assert other_total + len(bad_row) == biv_counts[4]
frag['biv-rows'] = (f'For $f(X, Y) = (Y - 5)(X^2 - Y)$ we have $k = 2$ and $f_2(Y) = Y - 5$, so the only bad row is $y = 5$, and it contains all {len(bad_row)} points as zeros. '
                    f'The other {len(other)} rows hold at most 2 zeros each, because each is a nonzero degree-2 polynomial in $X$. They contribute {other_total} zeros in total, and the sum ${len(bad_row)} + {other_total} = {biv_counts[4]}$ stays below the limit of ${3 * Q}$.')

F5 = 5
grid = [(u, v, (1, u, v, u * u % F5, u * v % F5, v * v % F5)) for u in range(F5) for v in range(F5)]
checked = 0
best = 0
reach = 0
for k0 in range(F5):
    for k1 in range(F5):
        for k2 in range(F5):
            for k3 in range(F5):
                for k4 in range(F5):
                    for k5 in range(F5):
                        if not (k0 or k1 or k2 or k3 or k4 or k5):
                            continue
                        count = sum(1 for _, _, m in grid if (k0 * m[0] + k1 * m[1] + k2 * m[2] + k3 * m[3] + k4 * m[4] + k5 * m[5]) % F5 == 0)
                        checked += 1
                        reach += count == 2 * F5
                        best = max(best, count)
assert checked == F5 ** 6 - 1 and best == 2 * F5
frag['biv-exhaustive'] = (f'To test every case rather than selected ones, we move to the smaller field $\\F_{{{F5}}}$, whose bivariate polynomials of total degree at most 2 have six coefficients. There are {checked} nonzero choices. '
                          f'None has more than {best} zeros among the {F5 * F5} points of the grid, which matches the limit $2 \\cdot {F5}$, and {reach} of them reach it.')

# Section 6: random linear combinations
e_cancel = [1, 42]
assert sum(e_cancel) % Q == 0
weights = [1, 2]
e_public = [2, 42]
assert sum(w * e for w, e in zip(weights, e_public)) % Q == 0
frag['rlc-cancel'] = (f'The errors $(1, 42)$ are both nonzero, but they add to 0 modulo 43. Fixed weights known in advance do no better. With the weights $(1, 2)$, a cheater picks the errors $(2, 42)$, and $1 \\cdot 2 + 2 \\cdot 42 = 0$ modulo 43.')

e3 = [6, 5, 1]
ind = sum(1 for u in range(Q) for v in range(Q) for w_ in range(Q) if (e3[0] * u + e3[1] * v + e3[2] * w_) % Q == 0)
assert ind == Q ** 2
frag['rlc-independent'] = (f'Take the errors ${vec(e3)}$. Trying all $43^3 = {Q ** 3}$ choices of $(r_0, r_1, r_2)$ finds {ind} that give a zero combination, which is a share of exactly $1/43$.')

power_tally = {}
for e0 in range(Q):
    for e1 in range(Q):
        for e2 in range(Q):
            if not (e0 or e1 or e2):
                continue
            n_roots = sum(1 for x in range(Q) if (e0 + e1 * x + e2 * powers[x][2]) % Q == 0)
            power_tally[n_roots] = power_tally.get(n_roots, 0) + 1
assert max(power_tally) == 2 and sum(power_tally.values()) == Q ** 3 - 1
e3_roots = [x for x in range(Q) if (e3[0] + e3[1] * x + e3[2] * x * x) % Q == 0]
frag['rlc-powers'] = '\n'.join(
    ['| Values of $r$ that hide the errors | Nonzero error vectors of length 3 |', '| --- | --- |']
    + [f'| {k} | {power_tally[k]} |' for k in sorted(power_tally)]
) + (f'\n\nThe counts cover all ${Q ** 3 - 1}$ nonzero vectors, and no vector is hidden by more than 2 of the 43 values, which agrees with the bound $(m - 1)/|\\F| = 2/43$. '
     f'The errors ${vec(e3)}$ from the previous example are hidden by {len(e3_roots)} value{"" if len(e3_roots) == 1 else "s"} in this form'
     + (f', namely $r \\in \\{{{", ".join(map(str, e3_roots))}\\}}$.' if e3_roots else '.'))

true0, true1 = poly_eval(pc, at), poly_eval(qc, at)
false0, false1 = (true0 + 1) % Q, (true1 + 2) % Q
hidden = [u for u in range(Q) if (false0 + u * false1 - poly_eval(poly_add(pc, [u * e % Q for e in qc]), at)) % Q == 0]
assert len(hidden) == 1 and hidden[0] == (-1 * pow(2, -1, Q)) % Q
tr = 6
combo = poly_add(pc, [tr * e % Q for e in qc])
assert poly_eval(combo, at) == (true0 + tr * true1) % Q
assert (false0 + tr * false1) % Q != poly_eval(combo, at)
frag['rlc-claims'] = (f'The true values at $x = {at}$ are $p({at}) = {true0}$ and $q({at}) = {true1}$. A cheater claims ${false0}$ and ${false1}$, with errors 1 and 2. At $r = {tr}$, the combined polynomial $p + {tr}q$ evaluates to ${poly_eval(combo, at)}$, '
                      f'while the combined claim is ${false0} + {tr} \\cdot {false1} = {(false0 + tr * false1) % Q}$, so the check fails. Trying all 43 values of $r$ finds that only $r = {hidden[0]}$ hides the errors, because that is the single solution of $1 + 2r = 0$ modulo 43.')

e1_late = 2
e0_late = (-tr * e1_late) % Q
late0, late1 = (true0 + e0_late) % Q, (true1 + e1_late) % Q
assert (late0 + tr * late1) % Q == poly_eval(combo, at) and late0 != true0
frag['rlc-early'] = (f'If the cheater learns $r = {tr}$ first, it keeps the error $e_1 = {e1_late}$ and solves for $e_0 = -{tr} \\cdot {e1_late} = {e0_late}$ modulo 43. It then claims ${late0}$ and ${late1}$. '
                     f'Both claims are false, yet ${late0} + {tr} \\cdot {late1} = {(late0 + tr * late1) % Q}$ equals the value of $p + {tr}q$ at ${at}$.')

# Toy Poseidon over F_43. Same structure as Ragu's, with far smaller parameters.
T, RATE, FULL, PARTIAL = 3, 2, 8, 8
assert gcd(5, Q - 1) == 1
assert len({pow(x, 5, Q) for x in range(Q)}) == Q
RC = [[int.from_bytes(hashlib.sha256(f'toy-poseidon-{rd}-{i}'.encode()).digest(), 'big') % Q for i in range(T)] for rd in range(FULL + PARTIAL)]
MDS = [[pow(x + y_, -1, Q) for y_ in (3, 4, 5)] for x in (0, 1, 2)]
det = (MDS[0][0] * (MDS[1][1] * MDS[2][2] - MDS[1][2] * MDS[2][1])
       - MDS[0][1] * (MDS[1][0] * MDS[2][2] - MDS[1][2] * MDS[2][0])
       + MDS[0][2] * (MDS[1][0] * MDS[2][1] - MDS[1][1] * MDS[2][0])) % Q
assert det != 0


def one_round(state, rd, elems):
    added = [(v + RC[rd][i]) % Q for i, v in enumerate(state)]
    boxed = [pow(v, 5, Q) if i < elems else v for i, v in enumerate(added)]
    mixed = [sum(MDS[i][j] * boxed[j] for j in range(T)) % Q for i in range(T)]
    return added, boxed, mixed


SCHEDULE = [T] * (FULL // 2) + [1] * PARTIAL + [T] * (FULL // 2)


def permutation(state):
    for rd, elems in enumerate(SCHEDULE):
        state = one_round(state, rd, elems)[2]
    return state


class Sponge:
    def __init__(self):
        self.state = [0] * T
        self.pending = []
        self.squeezing = False
        self.values = []
        self.trace = []

    def permute(self):
        taken = list(self.pending)
        for i, v in enumerate(self.pending):
            self.state[i] = (self.state[i] + v) % Q
        self.pending = []
        self.state = permutation(self.state)
        self.trace.append((taken, list(self.state)))

    def absorb(self, v):
        assert 0 <= v < Q
        if self.squeezing:
            self.squeezing = False
            self.values = []
        if len(self.pending) == RATE:
            self.permute()
        self.pending.append(v)

    def squeeze(self):
        if not self.squeezing:
            assert self.pending
            self.permute()
            self.squeezing = True
            self.values = self.state[:RATE][::-1]
        if not self.values:
            self.permute()
            self.values = self.state[:RATE][::-1]
        return self.values.pop()


TAG_A = [11, 22]
TAG_B = [11, 24]


def transcript(tag):
    sp = Sponge()
    sp.absorb(len(tag))
    for e in tag:
        sp.absorb(e)
    return sp


def absorb_point(sp, pt):
    # A coordinate is below 31, so it embeds in F_43 with no collisions.
    assert pt is not None
    sp.absorb(pt[0])
    sp.absorb(pt[1])


def challenge(tag, *points):
    sp = transcript(tag)
    for pt in points:
        absorb_point(sp, pt)
    return sp.squeeze()


def verify_strong(pub, com, resp, tag=TAG_A):
    return mul(resp, GEN) == add(com, mul(challenge(tag, pub, com), pub))


# Section 7: Fiat-Shamir run
fs_r = 29
fs_R = mul(fs_r, GEN)
fs_c = challenge(TAG_A, P, fs_R)
fs_s = (fs_r + fs_c * a) % Q
assert fs_c != 0 and fs_s != 0 and verify_strong(P, fs_R, fs_s)
frag['fs-run'] = '\n'.join([
    '| Step | Party | Value |', '| --- | --- | --- |',
    f'| 1 | Prover starts the transcript with the tag and instance | tag ${vec(TAG_A)}$, $P = {show(P)}$ |',
    f'| 2 | Prover computes the commitment and absorbs it | $R = {fs_r} \\cdot G = {show(fs_R)}$ |',
    f'| 3 | Prover squeezes the challenge | $c = {fs_c}$ |',
    f'| 4 | Prover computes the response | $s = {fs_r} + {fs_c} \\cdot {a} = {fs_s}$ modulo 43 |',
    f'| 5 | Prover publishes the proof | $(R, s) = ({show(fs_R)},\\ {fs_s})$ |',
    f'| 6 | Verifier replays steps 1 to 3 | $c = {fs_c}$ |',
    f'| 7 | Verifier checks the equation | $s \\cdot G = {show(mul(fs_s, GEN))}$ and $R + c \\cdot P = {show(add(fs_R, mul(fs_c, P)))}$ |',
])

alt_R = mul(fs_r + 1, GEN)
alt_c = challenge(TAG_A, P, alt_R)
assert alt_c != fs_c and not verify_strong(P, alt_R, fs_s)
second = transcript(TAG_A)
absorb_point(second, P)
absorb_point(second, fs_R)
c_first = second.squeeze()
second.absorb(fs_s)
d_first = second.squeeze()
second_alt = transcript(TAG_A)
absorb_point(second_alt, P)
absorb_point(second_alt, alt_R)
second_alt.squeeze()
second_alt.absorb(fs_s)
d_alt = second_alt.squeeze()
assert c_first == fs_c and d_first != d_alt
frag['fs-tamper'] = (f'Changing the commitment to $R\' = {show(alt_R)}$ changes the challenge from ${fs_c}$ to ${alt_c}$, and the old response ${fs_s}$ no longer satisfies the check. '
                     f'The effect also carries forward. If the protocol had a later round, which absorbed $s$ and squeezed a second challenge, that challenge would be ${d_first}$ after $R$ and ${d_alt}$ after $R\'$, with the same $s$ in both runs.')

# Section 8: omitted data. None of these attacks reads the variable a,
# except the mauling attack's input proof, which an honest party made.
weak_c = challenge(TAG_A, P)
atk_s = 31
atk_R = sub(mul(atk_s, GEN), mul(weak_c, P))
assert weak_c != 0 and atk_R is not None and atk_R not in G
assert mul(atk_s, GEN) == add(atk_R, mul(weak_c, P))
assert challenge(TAG_A, P) == weak_c
assert not verify_strong(P, atk_R, atk_s)
frag['omit-commitment'] = '\n'.join([
    '| Step | Value |', '| --- | --- |',
    f'| Compute the challenge from the tag and $P$ alone | $c = {weak_c}$ |',
    f'| Pick any response | $s = {atk_s}$ |',
    f'| Solve for the commitment | $R = {atk_s} \\cdot G - {weak_c} \\cdot P = {show(atk_R)}$ |',
    f'| Verifier\'s left side | $s \\cdot G = {show(mul(atk_s, GEN))}$ |',
    f'| Verifier\'s right side | $R + c \\cdot P = {show(add(atk_R, mul(weak_c, P)))}$ |',
]) + (f'\n\nThe flawed verifier accepts. A verifier that also absorbs $R$ derives the challenge ${challenge(TAG_A, P, atk_R)}$ instead of ${weak_c}$ and rejects the same proof.')

chosen_R = G[3]
weak2_c = challenge(TAG_A, chosen_R)
atk2_s = 19
assert weak2_c != 0
atk2_P = mul(pow(weak2_c, -1, Q), sub(mul(atk2_s, GEN), chosen_R))
assert atk2_P is not None and atk2_P != P
assert mul(atk2_s, GEN) == add(chosen_R, mul(weak2_c, atk2_P))
assert not verify_strong(atk2_P, chosen_R, atk2_s)
frag['omit-instance'] = (f'Start from the public point $R = G_3 = {show(chosen_R)}$, one of the fixed public points described above, whose discrete log relative to $G$ the cheater is assumed not to know. The flawed transcript gives $c = {weak2_c}$ without looking at any instance. '
                         f'Picking $s = {atk2_s}$ and solving gives $P\' = c^{{-1}} \\cdot (s \\cdot G - R) = {show(atk2_P)}$. The check holds, since $s \\cdot G = {show(mul(atk2_s, GEN))}$ and $R + c \\cdot P\' = {show(add(chosen_R, mul(weak2_c, atk2_P)))}$.')

honest_weak_c = challenge(TAG_A, fs_R)
honest_weak_s = (fs_r + honest_weak_c * a) % Q
assert mul(honest_weak_s, GEN) == add(fs_R, mul(honest_weak_c, P))
shift = 7
mauled_P = add(P, mul(shift, GEN))
mauled_s = (honest_weak_s + honest_weak_c * shift) % Q
assert mauled_P is not None
assert mul(mauled_s, GEN) == add(fs_R, mul(honest_weak_c, mauled_P))
assert not verify_strong(mauled_P, fs_R, mauled_s)
frag['omit-maul'] = (f'An honest prover publishes $(R, s) = ({show(fs_R)},\\ {honest_weak_s})$ for $P = {show(P)}$ under the flawed transcript, whose challenge is $c = {honest_weak_c}$. An observer takes $t = {shift}$ and computes $P\' = P + {shift} \\cdot G = {show(mauled_P)}$ and '
                     f'$s\' = s + c \\cdot t = {honest_weak_s} + {honest_weak_c} \\cdot {shift} = {mauled_s}$ modulo 43. The pair $(R, s\')$ passes for $P\'$, because $s\' \\cdot G = {show(mul(mauled_s, GEN))}$ and $R + c \\cdot P\' = {show(add(fs_R, mul(honest_weak_c, mauled_P)))}$.')

tag_c = challenge(TAG_B, P, fs_R)
assert tag_c != fs_c and not verify_strong(P, fs_R, fs_s, TAG_B)
frag['omit-tag'] = (f'With the tag ${vec(TAG_A)}$, the instance and commitment above give the challenge ${fs_c}$. With the tag ${vec(TAG_B)}$, the same two points give ${tag_c}$, and the response ${fs_s}$ fails the check.')

# Section 9: repeated trials. The search uses only public data.
attempts = 0
first = None
successes = 0
tried = 0
for guess in reversed(range(Q)):
    for resp in reversed(range(Q)):
        candidate = sub(G_multiples[resp], P_multiples[guess])
        if candidate is None:
            continue
        tried += 1
        if challenge(TAG_A, P, candidate) == guess:
            successes += 1
            assert verify_strong(P, candidate, resp)
            if first is None:
                first = (tried, guess, resp, candidate)
assert tried == Q * Q - Q and successes == Q - 1
assert first[3] not in G and first[1] and first[2]
frag['grinding'] = (f'A cheater repeats the early-challenge trick. It guesses a challenge, picks a response, computes $R = s \\cdot G - c \\cdot P$, and tests whether the hash of the transcript returns its guess. With $P = {show(P)}$, it tries guesses $c$ from {Q - 1} downward and, for each guess, responses $s$ from {Q - 1} downward, skipping any pair that gives the identity as $R$. The identity has no affine coordinates for the transcript to absorb, so a proof with that $R$ cannot be written down. Attempt {first[0]} succeeds with the guess $c = {first[1]}$, the response $s = {first[2]}$ and $R = {show(first[3])}$. '
                    f'The honest verifier accepts this proof, and the search never touched $a$. Across all {tried} pairs that give a nonidentity $R$, exactly {successes} succeed, which is one attempt in {tried // successes}.')

trials_exp = 128
frag['grinding-scale'] = (f'Suppose a cheater can compute $2^{{{trials_exp}}}$ hashes, and each attempt faces the soundness error $d/|\\F|$ with $d = 2^{{{d_exp}}}$ and a field above $2^{{{f_exp}}}$. Each attempt succeeds with probability below $2^{{{d_exp - f_exp}}}$, and all attempts together succeed with probability below $2^{{{trials_exp + d_exp - f_exp}}}$.')

# Section 10: Poseidon
squares = len({x * x % Q for x in range(Q)})
cubes = len({pow(x, 3, Q) for x in range(Q)})
fifths = len({pow(x, 5, Q) for x in range(Q)})
assert squares < Q and cubes < Q and fifths == Q
assert gcd(5, p_pallas - 1) == 1 and gcd(5, q_pallas - 1) == 1
assert gcd(3, p_pallas - 1) == 3 and gcd(3, q_pallas - 1) == 3 and gcd(2, p_pallas - 1) == 2
assert gcd(5, 31 - 1) == 5
frag['sbox'] = (f'Over $\\F_{{43}}$, the map $x \\mapsto x^2$ takes only {squares} distinct values and $x \\mapsto x^3$ takes {cubes}, whereas $x \\mapsto x^5$ takes all {fifths}, because 5 shares no factor with $43 - 1 = 42$. '
                f'The same reasoning rules out smaller exponents on both Pasta fields, because each field size minus 1 is divisible by 2 and 3 but not by 5.')

start_state = [len(TAG_A), TAG_A[0], 0]
added, boxed, mixed = one_round(start_state, 0, T)
part_in = list(mixed)
for rd in range(1, FULL // 2):
    part_in = one_round(part_in, rd, T)[2]
padded, pboxed, pmixed = one_round(part_in, FULL // 2, 1)
frag['round-trace'] = '\n'.join([
    '| Step | Full round | Partial round |', '| --- | --- | --- |',
    f'| Input state | ${vec(start_state)}$ | ${vec(part_in)}$ |',
    f'| After adding constants | ${vec(added)}$ | ${vec(padded)}$ |',
    f'| After the S-box | ${vec(boxed)}$ | ${vec(pboxed)}$ |',
    f'| After the mixing matrix | ${vec(mixed)}$ | ${vec(pmixed)}$ |',
])
assert pboxed[1:] == padded[1:] and pboxed[0] != padded[0]

run = transcript(TAG_A)
absorb_point(run, P)
absorb_point(run, fs_R)
assert run.squeeze() == fs_c
assert len(run.trace) == 4
sponge_rows = ['| Permutation | Elements added to the state | State afterward |', '| --- | --- | --- |']
for idx, (taken, st) in enumerate(run.trace):
    sponge_rows.append(f'| {idx + 1} | ${vec(taken)}$ | ${vec(st)}$ |')
assert run.trace[-1][1][0] == fs_c
frag['sponge-trace'] = (f'The transcript of Section 7 absorbs seven elements in order: the tag length 2, the tag ${vec(TAG_A)}$, the coordinates of $P = {show(P)}$, and the coordinates of $R = {show(fs_R)}$.\n\n'
                        + '\n'.join(sponge_rows)
                        + f'\n\nThe last permutation runs when the prover squeezes. The first entry of the resulting state is the challenge $c = {fs_c}$ from Section 7.')

zero_a = transcript(TAG_A)
absorb_point(zero_a, P)
absorb_point(zero_a, fs_R)
zero_b = transcript(TAG_A)
absorb_point(zero_b, P)
absorb_point(zero_b, fs_R)
zero_b.absorb(0)
v_a, v_b = zero_a.squeeze(), zero_b.squeeze()
assert v_a == v_b == fs_c
frag['zero-absorb'] = (f'Absorb the seven elements from the sponge trace in Section 10. The seventh waits in the buffer alone, so absorbing a zero after it leaves the sum unchanged. Both runs squeeze the challenge ${v_a}$.')

print(json.dumps(frag))
