"""Worked examples for staging.md. Prints fragments as JSON.

Every trace lives in the real four-block layout, with a system gate at index 0,
as at Ragu commit 3219e08. The circuits themselves are small ones of our own.
Masks are built twice, once from the list of forbidden wires and once from the
closed form in crates/ragu_circuits/src/staging/mask.rs, and asserted equal.
"""
import contextlib
import io
import json
from itertools import product

from toy_curve import B, B_DUAL, G, H, P, Q, U, add, curve_points, mul, show

with contextlib.redirect_stdout(io.StringIO()):
    from statements_and_challenges import FULL, PARTIAL, RATE, T, Sponge

frag = {}


def vec(v, m=Q):
    return '(' + ', '.join(str(e % m) for e in v) + ')'


def table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '| ' + ' | '.join('---' for _ in head) + ' |']
    out += ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows]
    return '\n'.join(out)


# ---- The layout: r = c || rev(a) || b || rev(d), and partners for wiring ----
def pos(kind, i, n):
    return {'c': i, 'a': 2 * n - 1 - i, 'b': 2 * n + i, 'd': 4 * n - 1 - i}[kind]


def partner(kind, i, n):
    return 4 * n - 1 - pos(kind, i, n)


def poly(n, wires, m=Q):
    out = [0] * (4 * n)
    for (kind, i), v in wires.items():
        out[pos(kind, i, n)] = v % m
    return out


def plus(*vs, m=Q):
    return [sum(c) % m for c in zip(*vs)]


def scale(k, v, m=Q):
    return [k * e % m for e in v]


def ev(p, at, m=Q):
    out = 0
    for e in reversed(p):
        out = (out * at + e) % m
    return out


def revdot(p, q, m=Q):
    assert len(p) == len(q)
    return sum(p[i] * q[len(q) - 1 - i] for i in range(len(p))) % m


class Circuit:
    def __init__(self, n, rows, k, m=Q):
        self.n, self.rows, self.k, self.m = n, rows, list(k) + [0] * (4 * n - len(k)), m

    def s(self, y):
        out = [0] * (4 * self.n)
        for j, row in enumerate(self.rows):
            weight = pow(y, j, self.m)
            for (kind, i), coeff in row.items():
                at = partner(kind, i, self.n)
                out[at] = (out[at] + weight * coeff) % self.m
        return out

    def t(self, z):
        n, out = self.n, [0] * (4 * self.n)
        for i in range(n):
            out[4 * n - 1 - i] = -(pow(z, 2 * n - 1 - i, self.m) + pow(z, 2 * n + i, self.m)) % self.m
        return out

    def right(self, r, z, y):
        dil = [r[i] * pow(z, i, self.m) % self.m for i in range(4 * self.n)]
        return plus(dil, self.s(y), self.t(z), m=self.m)

    def holds(self, r, z, y):
        return revdot(r, self.right(r, z, y), self.m) == ev(self.k, y, self.m)

    def holds_everywhere(self, r):
        return all(self.holds(r, z, y) for z in range(self.m) for y in range(self.m))


def wires_at(p, n, m=Q):
    """Read gates back from a vector, for the assertions on gate equations."""
    return [{kind: p[pos(kind, i, n)] % m for kind in 'abcd'} for i in range(n)]


def gates_hold(p, n, m=Q):
    return all((g['a'] * g['b'] - g['c']) % m == 0 and g['c'] * g['d'] % m == 0 for g in wires_at(p, n, m))


# ---- Masks ----
def active(g, count):
    """Gates a polynomial may use: the system gate and g, ..., g + count - 1."""
    return {0} | set(range(g, g + count))


def forbidden_degrees(n, g, count):
    keep = active(g, count)
    return sorted(partner(kind, i, n) for kind in 'abcd' for i in range(n) if i not in keep)


def mask(n, g, count, y, m=Q):
    out = [0] * (4 * n)
    for k in forbidden_degrees(n, g, count):
        out[k] = pow(y, k, m)
    return out


def geo(t, count, m):
    return sum(pow(t, i, m) for i in range(count)) % m


def mask_closed(n, g, count, t, m=Q):
    """global - notch, as in global_mask and StageMask::sxy at commit 3219e08."""
    two_n = pow(t, 2 * n, m)
    glob = geo(t, 4 * n, m) - (two_n + 1) * (pow(t, 2 * n - 1, m) + 1)
    notch = (1 + two_n) * (pow(t, g, m) + pow(t, 2 * n - g - count, m)) * geo(t, count, m)
    return (glob - notch) % m


# ---- Generators. As in chapters 09 and 13, distinct x-coordinates ----
EXTRA = [(4, 6), (5, 2), (25, 2), (30, 23), (9, 9), (14, 22), (20, 6), (28, 21)]
_seen = {a[0] for a in G + EXTRA + [H, U]}
_more = []
for _p in curve_points():
    if _p[0] not in _seen and len(_more) < 4:
        _seen.add(_p[0])
        _more.append(_p)
GENS = G + EXTRA + _more
assert len(GENS) == 16 and len({a[0] for a in GENS}) == 16

_dual = []
for _p in curve_points(Q, B_DUAL):
    if _p[0] not in [a[0] for a in _dual]:
        _dual.append(_p)
GD = [_dual[(i * len(_dual) // 12 + 8) % len(_dual)] for i in range(12)]
assert len(set(GD)) == 12


def commit(v):
    out = None
    for k, a in zip(v, GENS):
        out = add(out, mul(k % Q, a))
    return out


def dual_mul(k, a):
    out = None
    for _ in range(k % P):
        out = add(out, a, Q)
    return out


def dual_commit(v):
    out = None
    for k, a in zip(v, GD):
        out = add(out, dual_mul(k, a), Q)
    return out


# ---- The running circuits, n = 4 over F_43 ----
N = 4
ALPHA_A, ALPHA_SQ, ALPHA_CU, ALPHA_BAD, ALPHA_B, ALPHA_CO = 10, 25, 14, 12, 3, 32
X, V = 3, 9


def stage_a(x=X, v=V, alpha=ALPHA_A):
    return poly(N, {('a', 0): alpha, ('a', 1): x, ('d', 1): v})


def square_circuit(target):
    return Circuit(N, [
        {('d', 0): 1},
        {('c', 2): 1, ('d', 0): 1},
        {('a', 2): 1, ('a', 1): -1},
        {('b', 2): 1, ('a', 1): -1},
    ], [1, target])


def square_final(x=X, alpha=ALPHA_SQ):
    return poly(N, {('a', 0): alpha, ('d', 0): 1, ('a', 2): x, ('b', 2): x, ('c', 2): x * x})


CUBE = Circuit(N, [
    {('d', 0): 1},
    {('c', 3): 1, ('a', 1): 1, ('d', 0): 5},
    {('a', 2): 1, ('a', 1): -1},
    {('b', 2): 1, ('a', 1): -1},
    {('c', 2): 1, ('d', 1): -1},
    {('a', 3): 1, ('d', 1): -1},
    {('b', 3): 1, ('a', 1): -1},
], [1, 35])


def cube_final(x=X, alpha=ALPHA_CU):
    w = x * x % Q
    return poly(N, {('a', 0): alpha, ('d', 0): 1, ('a', 2): x, ('b', 2): x, ('c', 2): w,
                    ('a', 3): w, ('b', 3): x, ('c', 3): w * x})


A_POLY = stage_a()
SQUARE = square_circuit(10)
F_SQ = square_final()
F_CU = cube_final()
A_PT, F_SQ_PT, F_CU_PT = commit(A_POLY), commit(F_SQ), commit(F_CU)
R_SQ = plus(A_POLY, F_SQ)
R_CU = plus(A_POLY, F_CU)
SPECIAL = set(GENS + [H, U, None])
assert not {A_PT, F_SQ_PT, F_CU_PT, commit(R_SQ), commit(R_CU)} & SPECIAL
assert len({A_PT, F_SQ_PT, F_CU_PT, commit(R_SQ), commit(R_CU)}) == 5
assert add(A_PT, F_SQ_PT) == commit(R_SQ) and add(A_PT, F_CU_PT) == commit(R_CU)
assert A_POLY[6] == X and A_POLY[14] == V and A_POLY[7] == ALPHA_A

# ---- Section 1: the two costs ----
sbox_mults = 3                           # x^5 takes three multiplications
per_perm = (FULL * T + PARTIAL) * sbox_mults
def perms(values):
    return -(-values // RATE)
sample = 8
assert perms(2) == 1 and perms(sample) == 4
frag['hash-cost'] = (
    f'The toy sponge from [chapter 03](./statements-and-challenges.md#a-toy-poseidon) has rate {RATE}, and one permutation applies ${FULL} \\cdot {T} + {PARTIAL} = {FULL * T + PARTIAL}$ S-boxes of ${sbox_mults}$ multiplications each, or ${per_perm}$ gates before counting anything else. '
    f'Hashing ${sample}$ wires takes ${perms(sample)}$ permutations and ${perms(sample) * per_perm}$ gates. Hashing the two coordinates of a commitment to those same ${sample}$ wires takes ${perms(2)}$ permutation and ${per_perm}$ gates, and that cost stays the same however many wires the commitment covers.')

# ---- Section 2: the split ----
frag['split'] = table(
    ['Polynomial', 'Coefficients of $X^0, \\ldots, X^{15}$', 'Commitment'],
    [['Stage $a(X)$', f'${vec(A_POLY)}$', f'$\\bar{{A}} = {show(A_PT)}$'],
     ["Final trace $r'(X)$", f'${vec(F_SQ)}$', f"$\\bar{{R}}' = {show(F_SQ_PT)}$"],
     ['Sum $r(X)$', f'${vec(R_SQ)}$', f'$\\bar{{R}} = {show(commit(R_SQ))}$']])

gate_rows = []
wa, wf = wires_at(A_POLY, N), wires_at(F_SQ, N)
owner = ['System gate', 'Stage', 'Final trace', 'Final trace (unused)']
for i in range(N):
    gate_rows.append([i, owner[i]] + [f'{wa[i][k]} + {wf[i][k]}' for k in 'abcd'])
frag['gate-table'] = table(['Gate $i$', 'Reserved for', '$a_i$', '$b_i$', '$c_i$', '$d_i$'], gate_rows)

frag['gens'] = (
    f'A vector of $4n = 16$ entries needs 16 generators. We use the twelve from [chapter 09](./nark.md#_14-the-constant-wire), followed by ${", ".join(show(a) for a in _more)}$. '
    'This chapter never uses the blinding generator $H$, for a reason Section 3 gives.')

# ---- Section 3: gates and the consolidated equation ----
free = 0
for a_, d_ in product(range(Q), repeat=2):
    assert gates_hold(poly(N, {('a', 1): a_, ('d', 1): d_}), N)
    free += 1
assert SQUARE.holds_everywhere(R_SQ)
assert gates_hold(R_SQ, N)
assert not SQUARE.holds_everywhere(F_SQ)            # the final trace alone is not a witness
fail_alone = sum(1 for z in range(Q) for y in range(Q) if not SQUARE.holds(F_SQ, z, y))
frag['free-gate'] = (f'We tried all ${free:,}$ pairs of values for $(a_1, d_1)$, with $b_1 = c_1 = 0$. Every pair satisfies both equations of gate 1.')
frag['sum-holds'] = (
    f'The right vector at $z = 5$ and $y = 7$ gives $\\langle\\!\\langle \\v{{r}}, \\v{{r}} \\circ \\v{{z^{{16}}}} + \\v{{t}} + \\v{{s}} \\rangle\\!\\rangle = {revdot(R_SQ, SQUARE.right(R_SQ, 5, 7))}$, and $k(7) = 1 + 10 \\cdot 7 = {ev(SQUARE.k, 7)}$. '
    f'The two sides agree at all ${Q ** 2:,}$ pairs $(z, y)$. The final trace alone fails at ${fail_alone:,}$ of those pairs, which shows that the circuit reads its input from the stage polynomial, not from $r\'(X)$.')

# ---- Section 4: the overlap attack ----
SQ17 = square_circuit(17)
roots_sq17 = [x for x in range(Q) if (x * x + 1 - 17) % Q == 0]
roots_cube = [x for x in range(Q) if (x ** 3 + x + 5 - 35) % Q == 0]
roots_sq10 = [x for x in range(Q) if (x * x + 1 - 10) % Q == 0]
assert roots_cube == [X] and X in roots_sq10
assert not set(roots_sq17) & set(roots_cube)
DELTA = 1
F_BAD = plus(square_final(4, ALPHA_BAD), poly(N, {('a', 1): DELTA}))
R_BAD = plus(A_POLY, F_BAD)
assert wires_at(R_BAD, N)[1]['a'] == 4
assert SQ17.holds_everywhere(R_BAD) and not SQ17.holds_everywhere(R_SQ)
assert commit(R_BAD) == add(A_PT, commit(F_BAD))
assert not {commit(F_BAD), commit(R_BAD)} & SPECIAL and commit(F_BAD) != A_PT
assert CUBE.holds_everywhere(R_CU)
frag['roots'] = (
    f'Over $\\F_{{43}}$, the equation $x^3 + x + 5 = 35$ has the single solution ${roots_cube[0]}$. The equation $x^2 + 1 = 10$ has the solutions ${", ".join(map(str, roots_sq10))}$, and they share $x = {X}$. '
    f'The equation $x^2 + 1 = 17$ has the solutions ${", ".join(map(str, roots_sq17))}$, neither of which solves the first equation.')
frag['overlap'] = (
    f'Let the prover leave $\\bar{{A}} = {show(A_PT)}$ alone, so the stage still says $x = {X}$, and put ${DELTA}$ in slot $a_1$ of the final trace, whose gate 2 now holds $4 \\cdot 4 = 16$. The sum then holds $a_1 = {wires_at(R_BAD, N)[1]["a"]}$, and the circuit for $x^2 + 1 = 17$ accepts it at all ${Q ** 2:,}$ challenge pairs, while the commitments still add up: $\\bar{{A}} + {show(commit(F_BAD))} = {show(commit(R_BAD))}$. '
    f'The commitment says one input and the circuit ran on another.')

# ---- Section 5: the mask ----
FB_A = forbidden_degrees(N, 1, 1)
FB_FA = forbidden_degrees(N, 2, 2)
FB_B = forbidden_degrees(N, 2, 1)
FB_FB = forbidden_degrees(N, 3, 1)
assert FB_FA == sorted([partner(k, 1, N) for k in 'abcd'])
Y_RUN = 7
ms = mask(N, 1, 1, Y_RUN)
assert revdot(A_POLY, ms) == 0
frag['mask-degrees'] = table(
    ['Gate', 'Wire', 'Position $p$ in the trace', 'Degree $4n - 1 - p$ in the mask'],
    [[i, f'${k}_{i}$', pos(k, i, N), partner(k, i, N)] for i in (2, 3) for k in 'abcd'])
assert sorted(partner(k, i, N) for i in (2, 3) for k in 'abcd') == FB_A
for y in range(Q):
    assert revdot(A_POLY, mask(N, 1, 1, y)) == 0 and revdot(F_SQ, mask(N, 2, 2, y)) == 0
    assert revdot(F_CU, mask(N, 2, 2, y)) == 0
frag['mask-run'] = (
    f'At $y = {Y_RUN}$ the mask for stage $a(X)$ has coefficients ${vec(ms)}$. The stage has nonzero entries only at positions 6, 7 and 14, whose partners are 9, 8 and 1, and those are the positions where the mask has zeros. '
    f'So the product is ${revdot(A_POLY, ms)}$. The result is 0 at all 43 values of $y$.')
badv = [revdot(F_BAD, mask(N, 2, 2, y)) for y in range(Q)]
expected = [DELTA * pow(y, partner('a', 1, N), Q) % Q for y in range(Q)]
assert badv == expected
assert partner('a', 1, N) == 9
passes = [y for y in range(Q) if badv[y] == 0]
assert passes == [0]
frag['mask-catch'] = (
    f'The final trace from Section 4 has the stray entry at position 6, the partner of degree 9. Its product with the final mask is therefore ${DELTA} \\cdot y^9$, which equals ${badv[Y_RUN]}$ at $y = {Y_RUN}$. It is zero only at $y = 0$, so 42 of the 43 values of $y$ catch it.')

# A cheater may also fill the other three wires of gate 1 to build roots.
best_free = best_gates = 0
gate_examples = None
count_free = count_gates = 0
for e_, f_, g_ in product(range(Q), repeat=3):
    wrong = poly(N, {('a', 1): DELTA, ('d', 1): e_, ('b', 1): f_, ('c', 1): g_})
    # sum of powers, computed directly from the entries
    hits = sum(1 for y in range(1, Q)
               if (DELTA * pow(y, 9, Q) + e_ * y + f_ * pow(y, 6, Q) + g_ * pow(y, 14, Q)) % Q == 0)
    count_free += 1
    best_free = max(best_free, hits)
    total_a, total_d = 4, (V + e_) % Q
    if (total_a * f_ - g_) % Q == 0 and g_ * total_d % Q == 0:
        count_gates += 1
        if hits > best_gates:
            best_gates, gate_examples = hits, (e_, f_, g_)
assert best_free <= 13 and best_gates <= best_free
wrong = poly(N, {('a', 1): DELTA, ('d', 1): gate_examples[0], ('b', 1): gate_examples[1], ('c', 1): gate_examples[2]})
wrong_final = plus(square_final(4, ALPHA_BAD), wrong)
assert sum(1 for y in range(1, Q) if revdot(wrong_final, mask(N, 2, 2, y)) == 0) == best_gates
assert SQ17.holds_everywhere(plus(A_POLY, wrong_final))
frag['mask-best'] = (
    f'The cheater has more freedom than this, because the other three wires of gate 1 are also forbidden entries, and it can fill them in the hope of building roots. The product becomes $y^9 + e\\,y + f\\,y^6 + g\\,y^{{14}}$, where $e$, $f$ and $g$ are the entries it adds to $d_1$, $b_1$ and $c_1$. '
    f'Trying all ${count_free:,}$ choices, the best one has ${best_free}$ nonzero roots, out of the 42 nonzero values of $y$. Only ${count_gates:,}$ of the choices also leave gate 1 satisfied, as the circuit needs, and the best of those has ${best_gates}$ nonzero roots, at $(e, f, g) = {gate_examples}$.')
assert (4 * N - 1) == 15
frag['mask-bound'] = (f'For $n = 4$ the mask has degree at most $4n - 1 = 15$ in $y$, so the bound is $15/43 \\approx {15 / 43:.3f}$ and the best rate we found is ${best_gates + 1}/43 \\approx {(best_gates + 1) / 43:.3f}$, which counts the ${best_gates}$ nonzero roots of the best gate-satisfying choice plus $y = 0$. On a field of about $2^{{254}}$ elements with $4n = 2^{{13}}$, the same bound falls below $2^{{-240}}$.')

# ---- Section 6: closed form ----
for (g_, c_) in [(1, 1), (2, 2), (2, 1), (3, 1)]:
    for t in range(1, Q):
        assert mask_closed(N, g_, c_, t) == sum(pow(t, k, Q) for k in forbidden_degrees(N, g_, c_)) % Q
    for x_ in range(Q):
        for y_ in range(Q):
            full = sum(mask(N, g_, c_, y_)[k] * pow(x_, k, Q) for k in range(16)) % Q
            assert full == sum(pow(x_ * y_ % Q, k, Q) for k in forbidden_degrees(N, g_, c_)) % Q
t_run = 9 * 7 % Q
direct = sum(pow(t_run, k, Q) for k in FB_A) % Q
g_part = geo(t_run, 16, Q)
two_n = pow(t_run, 8, Q)
glob_part = (g_part - (two_n + 1) * (pow(t_run, 7, Q) + 1)) % Q
notch_part = (1 + two_n) * (pow(t_run, 1, Q) + pow(t_run, 6, Q)) * geo(t_run, 1, Q) % Q
assert (glob_part - notch_part) % Q == direct == mask_closed(N, 1, 1, t_run)
frag['closed-run'] = (
    f'Take $x = 9$ and $y = 7$, so $t = xy = {t_run}$, and the mask of stage $a(X)$, for which $g = 1$ and $m = 1$. The global term is ${glob_part}$ and the notch is ${notch_part}$, so the formula gives ${direct}$. Adding $t^k$ over the eight forbidden degrees gives the same value. '
    f'We checked the formula against the direct sum for every mask of this chapter at all 42 nonzero values of $t$.')
BIG_N, BIG_M = 2 ** 11, 100
terms = 4 * (BIG_N - 1 - BIG_M)
frag['closed-size'] = (f'For a circuit with $n = 2^{{{11}}}$ gates and a stage of ${BIG_M}$ gates, the mask has $4(n - 1 - m) = {terms:,}$ nonzero coefficients. The closed form needs only a few powers of $t$ and two geometric sums.')

# ---- Section 7: masks table ----
RESERVE = {'$a(X)$': (1, 1), '$b(X)$': (2, 1), 'Final trace after $a(X)$': (2, 2), 'Final trace after $b(X)$': (3, 1)}
rows = []
for name, (g_, c_) in RESERVE.items():
    keep = sorted(active(g_, c_) - {0})
    drop = [i for i in range(1, N) if i not in keep]
    rows.append([name, g_, c_, ', '.join(map(str, keep)), ', '.join(map(str, drop)) or 'None'])
frag['mask-table'] = table(['Polynomial', '$g$', '$m$', 'Gates it may use', 'Gates it must leave zero'], rows)

# ---- Section 8: folding ----
LEFT = stage_a()
RIGHT = stage_a(5, 25, 8)
assert all(revdot(plus(scale(z_, LEFT), RIGHT), mask(N, 1, 1, y)) == 0 for z_ in range(Q) for y in range(Q))
Z_RUN, Y2 = 5, 7
fold = plus(scale(Z_RUN, LEFT), RIGHT)
frag['fold-run'] = (
    f'Take the stage above as the left child\'s, and a right child\'s stage holding $(x, v) = (5, 25)$ with $a_0 = 8$. At $z = {Z_RUN}$ the fold $z \\cdot a_L(X) + a_R(X)$ has coefficients ${vec(fold)}$, and its product with the mask is 0, as it is at all ${Q ** 2:,}$ pairs $(z, y)$. One claim did the work of two.')
stray = 11
bad_r = plus(RIGHT, poly(N, {('a', 3): stray}))
hits_fold = sum(1 for z_ in range(Q) for y in range(Q) if revdot(plus(scale(z_, LEFT), bad_r), mask(N, 1, 1, y)) == 0)
assert hits_fold == Q
best_cancel, best_pair = 0, None
for dl, dr in product(range(1, Q), repeat=2):
    cnt = sum(1 for z_ in range(1, Q) if (z_ * dl + dr) % Q == 0)
    if cnt > best_cancel:
        best_cancel, best_pair = cnt, (dl, dr)
assert best_cancel == 1
frag['fold-catch'] = (
    f'Put a stray ${stray}$ in gate 3 of the right stage. Among all ${Q ** 2:,}$ pairs $(z, y)$, the folded claim passes at ${hits_fold}$, which are the 43 pairs with $y = 0$. '
    f'Two stray entries at one position, one per child, can cancel each other at a single $z$, since $z\\,\\delta_L + \\delta_R$ is a degree-1 polynomial in $z$. Over all ${42 ** 2:,}$ pairs of nonzero entries, no pair cancels at more than ${best_cancel}$ value of $z$.')

SQ26 = square_circuit(26)
r1, r2 = R_SQ, plus(stage_a(5, 25, 8), square_final(5, 12))
assert SQUARE.holds_everywhere(r1) and SQ26.holds_everywhere(r2)
# Folding two gate-carrying claims naively: the same circuit shape, the target adds up.
Z3, Y3 = 5, 7
assert SQUARE.s(7) == SQ26.s(7)
def fold_passes(rho):
    r = plus(scale(rho, r1), r2)
    target = (rho * ev(SQUARE.k, Y3) + ev(SQ26.k, Y3)) % Q
    return revdot(r, SQUARE.right(r, Z3, Y3)) == target
pass_rho = [rho for rho in range(Q) if fold_passes(rho)]
r_run = plus(scale(2, r1), r2)
lhs = revdot(r_run, SQUARE.right(r_run, Z3, Y3))
target_run = (2 * ev(SQUARE.k, Y3) + ev(SQ26.k, Y3)) % Q
assert lhs != target_run
assert len(pass_rho) <= 2
frag['fold-quadratic'] = (
    f'Fold two honest traces of the squaring circuit, with $x = 3$ and with $x = 5$, in the same way at $\\rho = 2$, $z = {Z3}$ and $y = {Y3}$. The two claims are both true, but the folded product is ${lhs}$ while the folded target is ${target_run}$. The terms with $\\rho^2$ and $\\rho$ do not match the target, and the two sides agree at only ${len(pass_rho)}$ of the 43 values of $\\rho$.')

# ---- Section 9: two circuits on one stage ----
assert F_SQ[6] == 0 and F_CU[6] == 0
LAMBDA_1, LAMBDA_2 = 5, 8
frag['two-circuits'] = table(
    ['Circuit', 'Statement', 'Trace', 'Commitment to its final trace', 'Consolidated equation'],
    [['Squaring', '$x^2 + 1 = 10$', "$a(X) + r'_1(X)$", f'${show(F_SQ_PT)}$', f'Holds at all ${Q ** 2:,}$ pairs'],
     ['Cubing', '$x^3 + x + 5 = 35$', "$a(X) + r'_2(X)$", f'${show(F_CU_PT)}$', f'Holds at all ${Q ** 2:,}$ pairs']])
# Separately traced, a prover can show both false claims.
sep_sq = plus(stage_a(4, 16, ALPHA_A), square_final(4))
assert SQ17.holds_everywhere(sep_sq) and CUBE.holds_everywhere(R_CU)
assert commit(stage_a(4, 16, ALPHA_A)) != A_PT
sep_pt = commit(stage_a(4, 16, ALPHA_A))
frag['two-statements'] = (
    f'With separate traces, the prover can use $x = 3$ for the cubing circuit and $x = 4$ for the circuit of $x^2 + 1 = 17$, and each trace passes its own consolidated equation at every challenge pair. The verifier has no way to see that the inputs differ. '
    f'With one shared stage the prover has to pick one $x$, and the lists above show that no single value satisfies both equations.')

# ---- Section 10: bonding, linking two stages ----
def bridge_for(point, alpha):
    return poly(3, {('a', 0): alpha, ('a', 1): point[0], ('d', 1): point[1]}, P)


ALPHA_BR, ALPHA_BF = 8, 6
BRIDGE = bridge_for(A_PT, ALPHA_BR)
NESTED = dual_commit(BRIDGE)
assert NESTED is not None and NESTED not in GD
assert A_PT[0] < P and A_PT[1] < P


def hash_point(pt):
    sp = Sponge()
    sp.absorb(pt[0])
    sp.absorb(pt[1])
    return sp.squeeze()


W = hash_point(NESTED)
assert W not in (0, 1)
E_VAL = (X + W * V) % Q


def stage_b(e, v, alpha=ALPHA_B):
    return poly(N, {('a', 0): alpha, ('a', 2): e, ('d', 2): v})


B_POLY = stage_b(E_VAL, V)
B_PT = commit(B_POLY)
assert B_PT not in SPECIAL and all(revdot(B_POLY, mask(N, 2, 1, y)) == 0 for y in range(Q))

LOAD = [{}, {('d', 1): 1, ('d', 2): -1}]


def load_s(y):
    c = Circuit(N, LOAD, [0])
    return c.s(y)


assert load_s(0) == [0] * 16
sum_ab = plus(A_POLY, B_POLY)
assert all(revdot(sum_ab, load_s(y)) == 0 for y in range(Q))
Y4 = 7
bad_v = 20
bad_sum = plus(A_POLY, stage_b(E_VAL, bad_v))
expect_bad = (V - bad_v) * Y4 % Q
assert revdot(bad_sum, load_s(Y4)) == expect_bad
hits_load = [y for y in range(Q) if revdot(bad_sum, load_s(y)) == 0]
assert hits_load == [0]
frag['bond-run'] = (
    f'The two stages hold $v = {V}$ in $d_1$ and $d_2$. The only row of the polynomial is $d_1 - d_2 = 0$, placed at $Y^1$, because the $Y^0$ position is empty in a polynomial of this kind. Then $\\langle\\!\\langle \\v{{a}} + \\v{{b}}, \\v{{s}} \\rangle\\!\\rangle = y\\,(d_1 - d_2)$, which is 0 at all 43 values of $y$. '
    f'If stage $b(X)$ holds ${bad_v}$ in $d_2$, the product at $y = {Y4}$ is ${expect_bad}$, and only $y = 0$ hides the difference.')

# ---- Section 11: stages do not check their contents ----
pairs = list(product(range(P), repeat=2))
on_e = [p_ for p_ in pairs if (p_[1] * p_[1] - p_[0] ** 3 - B) % P == 0]
mask_ok = [p_ for p_ in pairs if all(revdot(bridge_for(p_, ALPHA_BR), mask(3, 1, 1, y, P), P) == 0 for y in (1, 2, 3))]
assert len(on_e) == 42 and len(mask_ok) == P ** 2
frag['content'] = (
    f'A stage over $\\F_{{31}}$ that is supposed to hold a point of $E$ passes its mask for all ${len(mask_ok)}$ pairs of coordinates, and only ${len(on_e)}$ of those pairs lie on $E$.')

# ---- Section 12: nested staged commitment and the challenge ----
B_FIX = G[2]
assert B_FIX != A_PT and B_FIX[0] != A_PT[0]
LAM = (B_FIX[1] - A_PT[1]) * pow(B_FIX[0] - A_PT[0], -1, P) % P
assert LAM not in (0, 1)
DEFER = Circuit(3, [
    {('d', 0): 1},
    {('a', 2): 1},
    {('b', 2): 1, ('a', 1): 1, ('d', 0): -B_FIX[0]},
    {('c', 2): 1, ('d', 1): 1, ('d', 0): -B_FIX[1]},
], [1, LAM], P)
F_BR = poly(3, {('a', 0): ALPHA_BF, ('d', 0): 1, ('a', 2): LAM,
                ('b', 2): B_FIX[0] - A_PT[0], ('c', 2): B_FIX[1] - A_PT[1]}, P)
R_BR = plus(BRIDGE, F_BR, m=P)
assert gates_hold(R_BR, 3, P) and DEFER.holds_everywhere(R_BR)
assert all(revdot(BRIDGE, mask(3, 1, 1, y, P), P) == 0 and revdot(F_BR, mask(3, 2, 1, y, P), P) == 0 for y in range(P))
F_BR_PT = dual_commit(F_BR)
R_BR_PT = dual_commit(R_BR)
assert add(NESTED, F_BR_PT, Q) == R_BR_PT and not {F_BR_PT, R_BR_PT} & set(GD + [None]) and F_BR_PT != NESTED
frag['nested-run'] = table(
    ['Step', 'Field', 'Result'],
    [['Commit to stage $a(X)$ on $E$', '$\\F_{43}$ scalars', f'$\\bar{{A}} = {show(A_PT)}$'],
     ['Place its coordinates in a stage of the other circuit, gate 1', '$\\F_{31}$ wires', f'$a_1 = {A_PT[0]}$, $d_1 = {A_PT[1]}$, with $a_0 = {ALPHA_BR}$'],
     ['Commit to that stage on $E\'$', '$\\F_{31}$ scalars', f'$\\mathring{{A}} = {show(NESTED)}$'],
     ['Absorb the coordinates of $\\mathring{A}$ and squeeze', '$\\F_{43}$ wires', f'$w = {W}$']])
frag['deferred-run'] = (
    f'The circuit over $\\F_{{31}}$ has $n = 3$ gates, so it uses the twelve generators of $E\'$ from [chapter 13](./curve-cycles.md#_8-deferred-operations). Its gate 2 is the first gate of adding $\\bar{{A}}$ to the fixed point ${show(B_FIX)}$. Holding $\\lambda = {LAM}$, it checks ${LAM} \\cdot {(B_FIX[0] - A_PT[0]) % P} = {(B_FIX[1] - A_PT[1]) % P}$ modulo 31, with both differences written as linear rows over the stage wires. '
    f'Its consolidated equation holds at all ${P ** 2}$ pairs $(z, y)$, and both of its masks return 0 at all 31 values of $y$. The toy curve has too few points for the two remaining gates of the addition, so we stop there.')
BAD_DELTA = 7
F_BR_BAD = plus(F_BR, poly(3, {('a', 1): BAD_DELTA}, P), m=P)
stray_vals = [revdot(F_BR_BAD, mask(3, 2, 1, y, P), P) for y in range(P)]
assert [y for y in range(P) if stray_vals[y] == 0] == [0]
all_d = all(any(revdot(plus(F_BR, poly(3, {('a', 1): d_}, P), m=P), mask(3, 2, 1, y, P), P) for y in range(1, P)) for d_ in range(1, P))
assert all_d
frag['nested-catch'] = (
    f'Suppose the prover adds ${BAD_DELTA}$ to slot $a_1$ in the final trace of this circuit, so that its gates run on the $x$-coordinate ${(A_PT[0] + BAD_DELTA) % P}$ while $\\mathring{{A}}$ still holds ${A_PT[0]}$. The final mask returns ${stray_vals[5]}$ at $y = 5$, and only $y = 0$ hides the entry. The same holds for all 30 nonzero amounts.')

# stage b and the combining circuit
COMBINE = Circuit(N, [
    {('d', 0): 1},
    {('a', 3): 1},
    {('a', 2): 1},
    {('b', 3): 1, ('d', 2): -1},
    {('c', 3): 1, ('a', 1): 1, ('a', 2): -1},
], [1, W, E_VAL])
F_CO = poly(N, {('a', 0): ALPHA_CO, ('d', 0): 1, ('a', 3): W, ('b', 3): V, ('c', 3): W * V})
R_CO = plus(A_POLY, B_POLY, F_CO)
assert COMBINE.holds_everywhere(R_CO) and gates_hold(R_CO, N)
assert all(revdot(F_CO, mask(N, 3, 1, y)) == 0 for y in range(Q))
frag['combine-run'] = (
    f'With $w = {W}$, the prover computes $e = x + w\\,v = {X} + {W} \\cdot {V} = {E_VAL}$ and commits to stage $b(X)$, which holds $(e, v) = ({E_VAL}, {V})$ at gate 2, giving $\\bar{{B}} = {show(B_PT)}$. The final trace holds one gate, $a_3 = {W}$, $b_3 = {V}$ and $c_3 = {W * V % Q}$. '
    f'Rows of the wiring make $a_3$ and $a_2$ public, tie $b_3$ to $d_2$, and require $c_3 + a_1 - a_2 = 0$. The trace $a(X) + b(X) + r\'(X)$ satisfies the consolidated equation at all ${Q ** 2:,}$ pairs, with $k(Y) = 1 + {W}Y + {E_VAL}Y^2$.')

chain = {}
for v_ in range(Q):
    pt = commit(stage_a(X, v_))
    nest = None if pt is None else dual_commit(bridge_for(pt, ALPHA_BR))
    if nest is not None:
        chain[v_] = (X + hash_point(nest) * v_) % Q
assert chain[V] == E_VAL
def only_hit(target):
    return [v_ for v_, e_ in chain.items() if e_ == target]


TARGET = min(e_ for e_ in set(chain.values())
             if e_ not in (E_VAL, X) and len(only_hit(e_)) == 1 and only_hit(e_)[0] not in (0, V))
hit = only_hit(TARGET)
sol = [w_ for w_ in range(Q) if (X + w_ * V) % Q == TARGET]
assert len(sol) == 1 and len(hit) == 1 and W not in sol
early_v = (TARGET - X) * pow(W, -1, Q) % Q
assert (X + W * early_v) % Q == TARGET
frag['grind'] = (
    f'Suppose the prover wants $e = {TARGET}$. With the stage fixed at $(x, v) = ({X}, {V})$, only one of the 43 values of $w$ gives that result, namely $w = {sol[0]}$. If the prover could see $w = {W}$ before fixing the stage, it would set $v = {early_v}$ and reach the target for certain. '
    f'Instead, every new $v$ changes $\\bar{{A}}$, then $\\mathring{{A}}$, then $w$. We ran that whole chain for the ${len(chain)}$ values of $v$ that give a usable commitment, and one of them, $v = {hit[0]}$, reaches the target. A search of about 43 tries succeeds on a field of 43 elements, which is the [repeated-trials problem from chapter 03](./statements-and-challenges.md#_10-repeated-trials), and the same search has no realistic chance on a 255-bit field.')

# ---- Section 13: adding the stage commitments ----
frag['book-sum'] = (
    f'In the circuit above, $\\mathring{{A}} = {show(NESTED)}$ and the final trace commits to $\\bar{{R}}\' = {show(F_BR_PT)}$. The whole trace commits to $\\bar{{R}} = {show(R_BR_PT)}$. These are points on $E\'$, so the next circuit over $\\F_{{43}}$ can add them with the $3$ gates of [chapter 13](./curve-cycles.md#_3-a-curve-for-each-field), and the sum matches.')
A_FOLD = plus(scale(LAMBDA_1, R_SQ), scale(LAMBDA_2, R_CU))
msm_terms = [((LAMBDA_1 + LAMBDA_2) % Q, A_PT), (LAMBDA_1, F_SQ_PT), (LAMBDA_2, F_CU_PT)]
A_FOLD_PT = None
for k_, pt_ in msm_terms:
    A_FOLD_PT = add(A_FOLD_PT, mul(k_, pt_))
assert A_FOLD_PT == commit(A_FOLD) and A_FOLD_PT is not None
XZ = 2
a_at, f1_at, f2_at = ev(A_POLY, XZ), ev(F_SQ, XZ), ev(F_CU, XZ)
assert len({a_at, f1_at, f2_at, (LAMBDA_1 * (a_at + f1_at) + LAMBDA_2 * (a_at + f2_at)) % Q}) == 4 and 0 not in (a_at, f1_at, f2_at)
assert A_FOLD_PT not in SPECIAL
computed = (LAMBDA_1 * (a_at + f1_at) + LAMBDA_2 * (a_at + f2_at)) % Q
assert computed == ev(A_FOLD, XZ)
frag['code-sum-intro'] = (f'That gives the following run for our two circuits, with $\\lambda_1 = {LAMBDA_1}$, $\\lambda_2 = {LAMBDA_2}$ and the opening point $xz = {XZ}$ from $x = 9$ and $z = 5$:')
assert 9 * 5 % Q == XZ
frag['code-sum'] = table(
    ['Polynomial', 'Commitment', 'Value at the opening point $2$', 'Weight in $A(X)$'],
    [['$a(X)$', f'${show(A_PT)}$', a_at, f'$\\lambda_1 + \\lambda_2 = {(LAMBDA_1 + LAMBDA_2) % Q}$'],
     ["$r'_1(X)$", f'${show(F_SQ_PT)}$', f1_at, f'$\\lambda_1 = {LAMBDA_1}$'],
     ["$r'_2(X)$", f'${show(F_CU_PT)}$', f2_at, f'$\\lambda_2 = {LAMBDA_2}$'],
     ['$A(X)$', f'${show(A_FOLD_PT)}$', computed, 'Derived from the three rows above']])
frag['code-sum-text'] = (
    f'The prover gets the commitment to $A(X)$ from three scalar multiplications, ${(LAMBDA_1 + LAMBDA_2) % Q} \\cdot \\bar{{A}} + {LAMBDA_1} \\cdot \\bar{{R}}\'_1 + {LAMBDA_2} \\cdot \\bar{{R}}\'_2$, and a commitment to the full polynomial gives the same point. The verifying circuit computes the expected value ${LAMBDA_1} \\cdot ({a_at} + {f1_at}) + {LAMBDA_2} \\cdot ({a_at} + {f2_at}) = {computed}$ with field arithmetic and compares it with the opening of $A(X)$ at that point.')
# The cheat: A* folds a trace with another stage.
ST_STAR = stage_a(4, 16, ALPHA_A)
A_STAR = plus(scale(LAMBDA_1, plus(ST_STAR, square_final(4))), scale(LAMBDA_2, R_CU))
diff = [(p_ - q_) % Q for p_, q_ in zip(A_STAR, A_FOLD)]
agree = [p_ for p_ in range(Q) if ev(diff, p_) == 0]
deg = max(i for i, e_ in enumerate(diff) if e_)
assert len(agree) <= deg
frag['code-sum-catch'] = (
    f'Suppose the prover folds a squaring trace with stage input $x = 4$ into $A(X)$, while the commitment $\\bar{{A}}$ in the proof still holds $x = 3$. The polynomial it commits to as $A(X)$ then differs from the expected combination by a nonzero polynomial of degree ${deg}$. Of the 43 opening points, ${len(agree)}$ hide the difference.')

# ---- Section 14: the wrong mask ----
wrong_mask_vals = [revdot(A_POLY, mask(N, 2, 1, y)) for y in range(Q)]
assert wrong_mask_vals[7] == (X * pow(7, partner('a', 1, N), Q) + V * pow(7, partner('d', 1, N), Q)) % Q
wm_roots = [y for y in range(Q) if wrong_mask_vals[y] == 0]
frag['wrong-mask'] = (
    f'Check stage $a(X)$ against the mask of $b(X)$, which forbids gate 1. The product is ${X}\\,y^{{{partner("a", 1, N)}}} + {V}\\,y^{{{partner("d", 1, N)}}}$, or ${wrong_mask_vals[7]}$ at $y = 7$, and it vanishes at only ${len(wm_roots)}$ of the 43 values of $y$.')

# ---- Section 15: numbers from the code ----
BINDERS, STEPS = 8 // 2, 23
circuits = 4 + BINDERS + 2 + STEPS
stage_masks, final_masks = 11, 5
bondings = stage_masks + final_masks
claims = 2 + 2 + 2 * circuits + bondings
assert claims == 86 and claims <= 14 * 7
frag['code-count'] = (
    f'In the standard profile, the native side has ${circuits}$ internal circuits, of which ${STEPS}$ are endoscaling steps, along with ${stage_masks}$ stage masks and ${final_masks}$ final masks. The [count of revdot claims per fuse](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/mod.rs#L151-L166) is $2 + 2 + 2 \\cdot {circuits} + {bondings} = {claims}$. Each internal circuit counts once per child, and each mask counts once across both children, which saves ${bondings}$ claims.')
frag['code-preamble'] = (
    f'The native preamble stage reserves [$2(3h + 1 + 37)$ values](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/preamble.rs#L358-L362) for a header of $h$ elements, which is at least ${2 * (1 + 37)}$ even for an empty header.')

print(json.dumps(frag))
