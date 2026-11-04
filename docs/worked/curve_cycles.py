"""Worked examples for curve-cycles.md. Prints fragments as JSON.

The chapter's central object is a small tracer, Wires, tied to one field. It
refuses a point whose coordinates live in any other field, so a successful run
is evidence that a circuit stayed native. Every gate count in the chapter comes
from running these gates. Importing this module (the Manim figure may) prints
nothing unless it runs as a script.
"""
import contextlib
import io
import json

from toy_curve import B, B_DUAL, G, P, Q, add, curve_points, mul, msm, show

with contextlib.redirect_stdout(io.StringIO()):
    from statements_and_challenges import Sponge

INV2 = pow(2, -1, Q)
CURVES = {P: B, Q: B_DUAL}          # coordinate field -> b
ORDER = {P: Q, Q: P}                # coordinate field -> group order


def on_curve(a, f):
    return (a[1] * a[1] - a[0] ** 3 - CURVES[f]) % f == 0


def neg(a, f):
    return (a[0], -a[1] % f)


def smul(k, a, f):
    """Scalar multiplication on the curve whose coordinates lie in F_f."""
    return mul(k % ORDER[f], a, f) if f == Q else mul(k, a)


def mmsm(scalars, points, f):
    out = None
    for k, a in zip(scalars, points):
        out = add(out, smul(k, a, f), f)
    return out


# Generators on E'. As on E, take points at distinct x, spaced across the curve.
_dual = []
for _p in curve_points(Q, B_DUAL):
    if _p[0] not in [a[0] for a in _dual]:
        _dual.append(_p)
GD = [_dual[(i * len(_dual) // 12 + 8) % len(_dual)] for i in range(12)]
assert len(set(GD)) == 12
GENS = {P: G, Q: GD[:4]}


def fv(c, m):
    return '(' + ', '.join(str(a % m) for a in c) + ')'


def rows(header, body):
    out = ['| ' + ' | '.join(header) + ' |', '| ' + ' | '.join(['---'] * len(header)) + ' |']
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in body]
    return '\n'.join(out)


class Wires:
    """A circuit over F_mod. One entry per multiplication gate."""

    def __init__(self, mod):
        self.mod = mod
        self.gates = []

    def mul(self, a, b):
        c = a * b % self.mod
        self.gates.append((a % self.mod, b % self.mod, c))
        return c

    def inv(self, a):
        ai = pow(a, -1, self.mod)
        assert self.mul(a, ai) == 1
        return ai

    def bit(self, s):
        assert s in (0, 1)
        self.mul(s, (s - 1) % self.mod)
        return s

    def check_point(self, a):
        # A point can enter these gates only if its coordinates are wires here.
        assert on_curve(a, self.mod), f'{a} is not native to F_{self.mod}'

    def add_points(self, a, c):
        f = self.mod
        self.check_point(a)
        self.check_point(c)
        assert a[0] != c[0]
        s = (c[1] - a[1]) * pow(c[0] - a[0], -1, f) % f
        assert self.mul(s, c[0] - a[0]) == (c[1] - a[1]) % f
        x = self.mul(s, s)
        x = (x - a[0] - c[0]) % f
        y = (self.mul(s, a[0] - x) - a[1]) % f
        assert (x, y) == add(a, c, f)
        return x, y

    def double(self, a):
        f = self.mod
        self.check_point(a)
        sq = self.mul(a[0], a[0])
        s = 3 * sq * pow(2 * a[1], -1, f) % f
        assert self.mul(s, 2 * a[1]) == 3 * sq % f
        x = (self.mul(s, s) - 2 * a[0]) % f
        y = (self.mul(s, a[0] - x) - a[1]) % f
        assert (x, y) == add(a, a, f)
        return x, y

    def select(self, s, a, c):
        """s ? c : a, one gate per coordinate."""
        f = self.mod
        x = (a[0] + self.mul(s, c[0] - a[0])) % f
        y = (a[1] + self.mul(s, c[1] - a[1])) % f
        return x, y

    def scalar_mul(self, k, a):
        """The plain double-and-add of the recursive proofs chapter, top bit set."""
        bits = [int(b) for b in bin(k)[2:]]
        for b in bits:
            self.bit(b)
        out = a
        for b in bits[1:]:
            d = self.double(out)
            out = self.select(b, d, self.add_points(d, a))
        assert out == smul(k, a, self.mod)
        return out


def plain_scalar_gates(bits):
    return 10 * bits - 9


# ---- Polynomials and one fold, in whichever field a side uses ----
def ev(c, at, m):
    return sum(a * pow(at, i, m) for i, a in enumerate(c)) % m


def divide(c, x, m):
    running, out = 0, []
    for a in reversed(c):
        running = (a + x * running) % m
        out.append(running)
    out.pop()
    return out[::-1]


def lin(pairs, m, n=4):
    out = [0] * n
    for w, c in pairs:
        for i, a in enumerate(c):
            out[i] = (out[i] + w * a) % m
    return out


class Side:
    """One accumulator: polynomials over F_scalar, commitments on the curve with
    that scalar field, whose coordinates lie in the other field."""

    def __init__(self, scalar):
        self.m = scalar
        self.coord = P if scalar == Q else Q

    def commit(self, c):
        return mmsm(c, GENS[self.coord], self.coord)

    def claim(self, c, x):
        return dict(poly=[a % self.m for a in c], x=x, y=ev(c, x, self.m), C=self.commit(c))


def fold(side, claims, alpha, u, beta, value_wires, group_wires):
    """Chapter 08's batching, with the value in one circuit and the point in the other."""
    m_ = len(claims)
    assert value_wires.mod == side.m and group_wires.mod == side.coord
    qs = [divide(c['poly'], c['x'], side.m) for c in claims]
    fc = lin([(pow(alpha, m_ - 1 - i, side.m), q) for i, q in enumerate(qs)], side.m)
    Fp = side.commit(fc)
    vals = [ev(c['poly'], u, side.m) for c in claims]
    # The value: native field arithmetic.
    w = value_wires
    start = len(w.gates)
    fu = 0
    for c, val in zip(claims, vals):
        d = w.inv((u - c['x']) % side.m)
        fu = (w.mul(fu, alpha) + w.mul((val - c['y']) % side.m, d)) % side.m
    assert fu == ev(fc, u, side.m)
    v = fu
    for val in vals:
        v = (w.mul(v, beta) + val) % side.m
    value_gates = len(w.gates) - start
    # The point: native group arithmetic, on the other circuit's wires.
    g = group_wires
    start = len(g.gates)
    acc = Fp
    for c in claims:
        acc = g.add_points(g.scalar_mul(beta, acc), c['C'])
    group_gates = len(g.gates) - start
    pc = lin([(pow(beta, m_, side.m), fc)] + [(pow(beta, m_ - 1 - i, side.m), c['poly']) for i, c in enumerate(claims)], side.m)
    assert side.commit(pc) == acc and ev(pc, u, side.m) == v
    return dict(P=acc, u=u, v=v, poly=pc, F=Fp, f=fc, vals=vals, value_gates=value_gates, group_gates=group_gates)


# ---- Emulating F_31 multiplication inside F_43 wires, with bit limbs ----
LIMBS = 5
assert P == 2 ** LIMBS - 1


def bits_of(a):
    return [(a >> i) & 1 for i in range(LIMBS)]


def signed(a):
    a %= Q
    return a - Q if a > Q // 2 else a


def columns(a, b, r, t):
    """Column k of ab - r - 31 t, using 31 t = 32 t - t. Returns the integer columns."""
    ab, rb, tb = bits_of(a), bits_of(b), bits_of(t)
    rv = bits_of(r)
    out = []
    for k in range(2 * LIMBS):
        col = sum(ab[i] * bb for i in range(LIMBS) for j, bb in enumerate(rb) if i + j == k)
        col -= rv[k] if k < LIMBS else 0
        col += tb[k] if k < LIMBS else 0
        col -= tb[k - LIMBS] if k >= LIMBS else 0
        out.append(col)
    return out


def carries(cols):
    """Solve 2 c_k = col_k + c_(k-1) in F_43. Returns the carries, signed."""
    c, out = 0, []
    for col in cols:
        c = signed((col + c) * INV2)
        out.append(c)
    return out


CARRY_LOW, CARRY_HIGH = 0, 0
for _a in range(P):
    for _b in range(P):
        _cs = carries(columns(_a, _b, _a * _b % P, _a * _b // P))
        assert _cs[-1] == 0
        CARRY_LOW, CARRY_HIGH = min(CARRY_LOW, *_cs), max(CARRY_HIGH, *_cs)
CARRY_BITS = len(bin(CARRY_HIGH - CARRY_LOW)) - 2
EMUL_MUL = LIMBS * LIMBS + 2 * LIMBS + (2 * LIMBS - 1) * CARRY_BITS


def emul_exhaustive():
    """All inputs. Every column stays far below 43, so each equation mod 43 is an integer equation."""
    products = [[[sum(((a >> i) & 1) * ((b >> (k - i)) & 1) for i in range(LIMBS) if 0 <= k - i < LIMBS)
                  for k in range(2 * LIMBS)] for b in range(P)] for a in range(P)]
    deltas = [[[(-((r >> k) & 1) + ((t >> k) & 1)) if k < LIMBS else -((t >> (k - LIMBS)) & 1)
                for k in range(2 * LIMBS)] for t in range(2 ** LIMBS)] for r in range(2 ** LIMBS)]
    half = [signed(v * INV2) for v in range(Q)]
    accepted = 0
    for a in range(P):
        for b in range(P):
            pr = products[a][b]
            for r in range(2 ** LIMBS):
                for t in range(2 ** LIMBS):
                    de = deltas[r][t]
                    c = 0
                    for k in range(2 * LIMBS):
                        c = half[(pr[k] + de[k] + c) % Q]
                        if not CARRY_LOW <= c <= CARRY_HIGH:
                            break
                    else:
                        if c == 0:
                            assert r + 31 * t == a * b and r % P == a * b % P
                            accepted += 1
    assert accepted == P * P
    return accepted


def main():
    frag = {}
    cq = [7, 2, 5, 3], [3, 1, 8, 4]
    C0, C1 = msm(cq[0], G), msm(cq[1], G)
    assert (C0, C1) == ((27, 30), (6, 23))

    # ---- Section 1: the same formula in the wrong field ----
    lam = (C1[1] - C0[1]) * pow(C1[0] - C0[0], -1, P) % P
    true_sum = add(C0, C1)
    lam_w = (C1[1] - C0[1]) * pow(C1[0] - C0[0], -1, Q) % Q
    x_w = (lam_w * lam_w - C0[0] - C1[0]) % Q
    y_w = (lam_w * (C0[0] - x_w) - C0[1]) % Q
    assert not on_curve((x_w, y_w), P) and not on_curve((x_w, y_w), Q)
    assert (x_w, y_w) != true_sum
    frag['wrong-field'] = (
        f'Take the commitments ${show(C0)}$ and ${show(C1)}$ from [chapter 08](./batched-openings.md#_8-the-complete-protocol). '
        f'Modulo 31 the slope is ${lam}$ and the sum is ${show(true_sum)}$, a point on $E$. Run the same three formulas on wires that reduce modulo 43 and the slope becomes ${lam_w}$, '
        f'and the result is $({x_w},\\,{y_w})$, which lies on neither curve of the toy cycle.')

    dx, dy = (C1[0] - C0[0]) % P, (C1[1] - C0[1]) % P
    n_int = lam * dx
    assert n_int % P == dy and n_int % Q != dy
    frag['wrap'] = (
        f'The first gate of that addition checks $\\lambda \\cdot (x_2 - x_1) = y_2 - y_1$, which here reads ${lam} \\cdot {dx} = {dy}$ modulo 31. '
        f'As integers, ${lam} \\cdot {dx} = {n_int}$, and ${n_int}$ leaves remainder ${n_int % P}$ modulo 31. A wire in $\\F_{{43}}$ holds ${n_int % Q}$, because that is the remainder modulo 43, and the remainder modulo 43 says nothing about the remainder modulo 31.')

    # ---- Section 2: emulation ----
    r_true, t_true = n_int % P, n_int // P
    assert r_true + 31 * t_true == n_int
    passing = [(r, t) for r in range(P) for t in range(2 ** LIMBS) if (r + 31 * t - n_int) % Q == 0]
    false_pairs = [(r, t) for r, t in passing if r != r_true]
    assert (r_true, t_true) in passing and false_pairs
    fr, ft = false_pairs[0]
    frag['one-equation'] = (
        f'The honest witness for ${n_int}$ is $r = {r_true}$ and $t = {t_true}$, since ${r_true} + 31 \\cdot {t_true} = {n_int}$. A single gate can only check this equation modulo 43. '
        f'Of the ${P * 2 ** LIMBS:,}$ pairs with $r$ below 31 and $t$ below {2 ** LIMBS}, ${len(passing)}$ satisfy it, and ${len(false_pairs)}$ of those have the wrong remainder. '
        f'One of them is $r = {fr}$ and $t = {ft}$, because ${fr} + 31 \\cdot {ft} = {fr + 31 * ft}$, which equals ${n_int}$ modulo 43.')

    cols = columns(lam, dx, r_true, t_true)
    cs = carries(cols)
    assert cs[-1] == 0 and all(CARRY_LOW <= c <= CARRY_HIGH for c in cs)
    ab, bb, rb, tb = bits_of(lam), bits_of(dx), bits_of(r_true), bits_of(t_true)
    body = []
    prev = 0
    for k, (col, c) in enumerate(zip(cols, cs)):
        prod = sum(ab[i] * bb[k - i] for i in range(LIMBS) if 0 <= k - i < LIMBS)
        rk = rb[k] if k < LIMBS else 0
        tk = tb[k] if k < LIMBS else 0
        tk5 = tb[k - LIMBS] if k >= LIMBS else 0
        assert prod - rk + tk - tk5 == col and col + prev == 2 * c
        body.append([k, prod, rk, tk, tk5, prev, c])
        prev = c
    frag['columns'] = rows(['Column $k$', 'Sum of $a_i b_j$', '$r_k$', '$t_k$', '$t_{k-5}$', 'Carry in', 'Carry out'], body)

    accepted = emul_exhaustive()
    frag['emul-count'] = (
        f'Here $a = {lam}$ and $b = {dx}$. Each row satisfies its equation and the last carry is 0. The gates are ${LIMBS * LIMBS}$ for the products $a_i b_j$, ${2 * LIMBS}$ to show that the bits of $r$ and $t$ are bits, and ${(2 * LIMBS - 1) * CARRY_BITS}$ for the ${2 * LIMBS - 1}$ carries at ${CARRY_BITS}$ bits each, '
        f'since an honest carry always lies between ${CARRY_LOW}$ and ${CARRY_HIGH}$. That is ${EMUL_MUL}$ gates for one multiplication in $\\F_{{31}}$. '
        f'We ran the check on all ${P}^2$ pairs $(a, b)$ against all ${2 ** LIMBS}^2$ pairs $(r, t)$. It accepted ${accepted}$ inputs, one for each pair $(a, b)$, and each of them had the true remainder.')

    # A double-and-add step per lower bit: 4 + 3 emulated multiplications, 2 selects over limbs.
    b6 = 6
    mults = (b6 - 1) * 7
    emul6 = mults * EMUL_MUL + (b6 - 1) * 2 * LIMBS + b6
    assert plain_scalar_gates(b6) == 51
    frag['emul-toy-scalar'] = (
        f'A 6-bit scalar multiplication on $E$ does {b6 - 1} doublings and {b6 - 1} additions, or ${mults}$ multiplications in $\\F_{{31}}$ at ${EMUL_MUL}$ gates each. '
        f'With its selections and scalar bits, it costs ${emul6:,}$ gates, where the same operation on $E\'$ costs ${plain_scalar_gates(b6)}$ gates in the [recursive proofs chapter](./recursive-proofs.md#point-operations). That leaves out the extra work to reduce the sums and differences in each formula back into range.')

    w_limb, n_limb = 64, 4
    assert w_limb * n_limb >= 255
    carry_bits = w_limb + 3
    real_mul = n_limb * n_limb + 2 * 255 + (2 * n_limb - 1) * carry_bits
    scal_mults = 254 * 7
    real_scalar = scal_mults * real_mul
    native_scalar = plain_scalar_gates(255)
    verifier_scalars = 2 * 13 + 6
    assert verifier_scalars * native_scalar == 81312
    budget = 2 ** 11
    assert 3 * real_mul > budget
    frag['emul-real'] = (
        f'Take the same plain design with {n_limb} limbs of {w_limb} bits. One multiplication then uses ${n_limb * n_limb}$ limb products, ${2 * 255}$ bits for $r$ and $t$, and ${2 * n_limb - 1}$ carries of about ${carry_bits}$ bits, for about ${real_mul:,}$ gates. '
        f'A point addition needs three of these, or about ${3 * real_mul:,}$ gates, which already exceeds the ${budget:,}$ gates that Ragu allows in one circuit. A 255-bit scalar multiplication needs ${scal_mults:,}$ multiplications, or about ${real_scalar:,}$ gates, where the native version costs ${native_scalar:,}$. '
        f'The verifier of Chapter 09 has ${verifier_scalars}$ such multiplications, which comes to about ${verifier_scalars * real_scalar:,}$ gates.')

    # ---- Section 3: the partner curve, and how rare cycles are ----
    A2, B2 = GD[1], GD[4]
    wp = Wires(Q)
    S2 = wp.add_points(A2, B2)
    native_add = len(wp.gates)
    frag['native-add'] = (
        f'Take the points ${show(A2)}$ and ${show(B2)}$ on $E\'$. Their slope and sum are computed modulo 43, so every gate works in the circuit\'s own field. The addition takes ${native_add}$ gates and gives ${show(S2)}$, which we confirmed lies on $E\'$.')

    frag['cycle-table'] = rows(
        ['Curve', 'Coordinates in', 'Scalars in', 'Polynomials it commits to', 'Circuit that can do its point arithmetic'],
        [['$E$', '$\\F_{31}$', '$\\F_{43}$', 'Over $\\F_{43}$', 'Wires in $\\F_{31}$'],
         ["$E'$", '$\\F_{43}$', '$\\F_{31}$', 'Over $\\F_{31}$', 'Wires in $\\F_{43}$']])

    t1, t2 = P + 1 - Q, Q + 1 - P
    assert t1 + t2 == 2 and t1 * t1 <= 4 * P and t2 * t2 <= 4 * Q
    frag['hasse'] = (
        f'For $E$ we have $31 + 1 - 43 = {t1}$, and $2\\sqrt{{31}}$ is about ${2 * P ** 0.5:.1f}$. For $E\'$ we have $43 + 1 - 31 = {t2}$, and $2\\sqrt{{43}}$ is about ${2 * Q ** 0.5:.1f}$. Both differences fit within the bound.')

    def is_prime(n):
        return n > 1 and all(n % d for d in range(2, int(n ** 0.5) + 1))

    def orders_of(p):
        roots = [0] * p
        for y in range(p):
            roots[y * y % p] += 1
        return {1 + sum(roots[(x * x * x + b) % p] for x in range(p)) for b in range(1, p)}

    primes = [p for p in range(5, 200) if is_prime(p) and p % 3 == 1]
    orders = {p: orders_of(p) for p in primes}
    pairs = [(p, q) for p in primes for q in primes if p < q and q in orders[p] and p in orders[q]]
    anomalous = [p for p in primes if p in orders[p]]
    assert (31, 43) in pairs and anomalous
    frag['cycle-search'] = (
        f'We counted the points on every curve $y^2 = x^3 + b$ over each of the ${len(primes)}$ primes below 200 that are congruent to 1 modulo 3. Among the ${len(primes) * (len(primes) - 1) // 2}$ pairs of these primes, ${len(pairs)}$ form a cycle, and the pair $(31, 43)$ is one of them. '
        f'The same count finds ${len(anomalous)}$ primes with a curve whose number of points equals its field size, starting with ${anomalous[0]}$.')

    # ---- Section 4: Pasta ----
    pp = 0x40000000000000000000000000000000224698fc094cf91b992d30ed00000001
    pq = 0x40000000000000000000000000000000224698fc0994a8dd8c46eb2100000001

    def miller_rabin(n):
        d, s = n - 1, 0
        while d % 2 == 0:
            d, s = d // 2, s + 1
        for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
            x = pow(a, d, n)
            if x in (1, n - 1):
                continue
            for _ in range(s - 1):
                x = x * x % n
                if x == n - 1:
                    break
            else:
                return False
        return True

    def sqrt_mod(a, p):
        if pow(a, (p - 1) // 2, p) != 1:
            return None
        s, d = 0, p - 1
        while d % 2 == 0:
            s, d = s + 1, d // 2
        z = 2
        while pow(z, (p - 1) // 2, p) != p - 1:
            z += 1
        m, c, t, r = s, pow(z, d, p), pow(a, d, p), pow(a, (d + 1) // 2, p)
        while t != 1:
            i, t2i = 0, t
            while t2i != 1:
                t2i, i = t2i * t2i % p, i + 1
            b = pow(c, 2 ** (m - i - 1), p)
            m, c, t, r = i, b * b % p, t * b * b % p, r * b % p
        return r

    def order_is(field, n):
        x = 1
        while True:
            y = sqrt_mod((x ** 3 + 5) % field, field)
            if y:
                break
            x += 1
        pt = (x, y)
        assert (y * y - x ** 3 - 5) % field == 0
        # add() from toy_curve is generic in its modulus.
        out, base, k = None, pt, n
        while k:
            if k & 1:
                out = add(out, base, field)
            base = add(base, base, field)
            k >>= 1
        return out is None

    assert miller_rabin(pp) and miller_rabin(pq) and pp < pq
    assert order_is(pp, pq) and order_is(pq, pp)
    tt = pp + 1 - pq
    assert tt * tt <= 4 * pp and (pq + 1 - pp) * (pq + 1 - pp) <= 4 * pq
    assert pp % 3 == 1 and pq % 3 == 1
    assert pow(5, (pp - 1) // 2, pp) == pp - 1 and pow(5, (pq - 1) // 2, pq) == pq - 1
    gap_bits = (pq - pp).bit_length()
    assert pp.bit_length() == 255 and pq.bit_length() == 255
    frag['pasta-numbers'] = (
        f'$$\n\\begin{{aligned}}\np &= \\texttt{{{hex(pp)}}}, \\\\\nq &= \\texttt{{{hex(pq)}}}.\n\\end{{aligned}}\n$$\n\n'
        f'Both are primes of {pp.bit_length()} bits, and $q - p$ has only {gap_bits} bits, which is below the size that $2\\sqrt{{p}}$ allows. '
        f'We tested the cycle property directly. A point found on $y^2 = x^3 + 5$ over $\\F_p$ goes to the identity when multiplied by $q$, a point over $\\F_q$ goes to the identity when multiplied by $p$, and only one multiple of each prime lies within the Hasse range, so the two orders must be $q$ and $p$.')

    toy_miss = Q - P
    frag['fit'] = (
        f'In the toy cycle, ${toy_miss}$ of the 43 values of $\\F_{{43}}$ are 31 or larger, so more than a quarter of them have no equal in $\\F_{{31}}$. In the Pasta cycle the fraction is near $2^{{{gap_bits - 254}}}$, so a random value of $\\F_q$ almost always fits in $\\F_p$. A protocol still cannot rely on that for values a prover can choose.')

    frag['names'] = rows(
        ['Role', 'Toy cycle', 'Pasta', 'Book', 'Code at `3219e08`'],
        [['Field of the main circuit\'s wires', '$\\F_{43}$', '$\\F_p$', '$\\F^{(1)}$, $CS^{(1)}$', '`CircuitField`'],
         ['Curve for that circuit\'s polynomials', '$E$', 'Vesta', '$\\G^{(1)}$, $\\G_{host}$', '`HostCurve`'],
         ['Field of the other circuit\'s wires', '$\\F_{31}$', '$\\F_q$', '$\\F^{(2)}$, $CS^{(2)}$', '`ScalarField`'],
         ['Curve for that circuit\'s polynomials', "$E'$", 'Pallas', '$\\G^{(2)}$, $\\G_{nested}$', '`NestedCurve`']])

    # ---- Section 6: one fold on both curves ----
    s1, s2 = Side(Q), Side(P)
    alpha, u, beta = 11, 13, 15
    assert beta >> 3 == 1 and all(c < 16 for c in (alpha, u, beta))
    cl1 = [s1.claim(cq[0], 9), s1.claim(cq[1], 5)]
    cl2 = [s2.claim([4, 9, 2, 6], 5), s2.claim([8, 3, 7, 5], 3)]
    assert [c['y'] for c in cl1] == [37, 20]
    assert all(c['y'] for c in cl1 + cl2) and all(c['x'] != u for c in cl1 + cl2)
    primary, secondary = Wires(Q), Wires(P)
    a1 = fold(s1, cl1, alpha, u, beta, primary, secondary)
    a2 = fold(s2, cl2, alpha, u, beta, secondary, primary)
    assert all(a1['vals']) and all(a2['vals'])

    def claim_row(name, c, m):
        return [name, fv(c['poly'], m).join('$$'), f"${c['x']}$", f"${c['y']}$", f"${show(c['C'])}$"]

    frag['fold-inputs'] = rows(
        ['Claim', 'Coefficients', 'Point', 'Value', 'Commitment'],
        [claim_row('$p_0$ over $\\F_{43}$, on $E$', cl1[0], Q),
         claim_row('$p_1$ over $\\F_{43}$, on $E$', cl1[1], Q),
         claim_row("$p'_0$ over $\\F_{31}$, on $E'$", cl2[0], P),
         claim_row("$p'_1$ over $\\F_{31}$, on $E'$", cl2[1], P)])

    frag['fold-f'] = (
        f'The challenges are $\\alpha = {alpha}$, $u = {u}$ and $\\beta = {beta}$, each picked by hand and each below 16, for a reason that Section 9 gives. '
        f'On the first side, the prover\'s quotient combination is $f = {fv(a1["f"], Q)}$ with commitment $F = {show(a1["F"])}$, and the values at $u$ are ${a1["vals"][0]}$ and ${a1["vals"][1]}$. '
        f'On the second side, it is $f\' = {fv(a2["f"], P)}$ with commitment $F\' = {show(a2["F"])}$, and the values at $u$ are ${a2["vals"][0]}$ and ${a2["vals"][1]}$.')

    frag['fold-split'] = rows(
        ['Output', 'Computed in', 'Operations', 'Result', 'Gates'],
        [['$v$ over $\\F_{43}$', 'Circuit over $\\F_{43}$', 'Field arithmetic', f"${a1['v']}$", a1['value_gates']],
         ["$P'$ on $E'$", 'Circuit over $\\F_{43}$', 'Point arithmetic', f"${show(a2['P'])}$", a2['group_gates']],
         ["$v'$ over $\\F_{31}$", 'Circuit over $\\F_{31}$', 'Field arithmetic', f"${a2['v']}$", a2['value_gates']],
         ['$P$ on $E$', 'Circuit over $\\F_{31}$', 'Point arithmetic', f"${show(a1['P'])}$", a1['group_gates']]])

    assert len(primary.gates) == a1['value_gates'] + a2['group_gates']
    assert len(secondary.gates) == a2['value_gates'] + a1['group_gates']
    assert s1.commit(a1['poly']) == a1['P'] and ev(a1['poly'], u, Q) == a1['v']
    assert s2.commit(a2['poly']) == a2['P'] and ev(a2['poly'], u, P) == a2['v']
    frag['fold-decide'] = (
        f'The prover also holds the combined polynomials $p = {fv(a1["poly"], Q)}$ and $p\' = {fv(a2["poly"], P)}$. A decider commits to them and gets ${show(a1["P"])}$ on $E$ and ${show(a2["P"])}$ on $E\'$. Evaluating at $u = {u}$ gives ${a1["v"]}$ in $\\F_{{43}}$ and ${a2["v"]}$ in $\\F_{{31}}$. All four numbers match the table.')

    b4 = plain_scalar_gates(4)
    mults4 = 3 * 7
    # One Horner step per claim: a 4-bit scalar multiplication and one addition.
    steps = len(cl1)
    native_p = steps * (b4 + 3)
    assert native_p == a1['group_gates']
    emul_p = steps * (mults4 * EMUL_MUL + 3 * 2 * LIMBS + 4 + 3 * EMUL_MUL)
    frag['fold-compare'] = (
        f'The tracer that runs these gates refuses any point whose coordinates are not in its own field, and every run above passed that test. The point $P$ took ${native_p}$ gates on wires in $\\F_{{31}}$. If the circuit over $\\F_{{43}}$ had computed it by the method of Section 2, the same steps would have cost at least ${emul_p:,}$ gates.')

    # ---- Section 7: nested commitment ----
    A, B_ = C0, C1
    coords = [A[0], A[1], B_[0], B_[1]]
    assert all(0 < c < P for c in coords)
    nested = mmsm(coords, GD[:4], Q)
    assert on_curve(nested, Q)

    def absorb_challenge(point):
        sp = Sponge()
        sp.absorb(point[0])
        sp.absorb(point[1])
        return sp.squeeze()

    s_full = absorb_challenge(nested)
    assert s_full != 0
    frag['nested-run'] = (
        f'Take $A = {show(A)}$ and $B = {show(B_)}$. Their coordinates form the vector ${fv(coords, P)}$ in $\\F_{{31}}^4$. Each entry is a valid scalar on $E\'$, so we commit with four generators of $E\'$, namely ${", ".join(show(g) for g in GD[:4])}$:\n\n'
        f'$$\\mathring{{A}} = {coords[0]} \\cdot G\'_0 + {coords[1]} \\cdot G\'_1 + {coords[2]} \\cdot G\'_2 + {coords[3]} \\cdot G\'_3 = {show(nested)}.$$\n\n'
        f'The coordinates of $\\mathring{{A}}$ lie in $\\F_{{43}}$, so the circuit over $\\F_{{43}}$ can hold them as wires and absorb them. The [toy sponge](./statements-and-challenges.md#a-toy-poseidon) over $\\F_{{43}}$ takes those two values and squeezes the output ${s_full}$.')

    changes_point = changes_output = 0
    for alt in range(P):
        if alt == coords[0]:
            continue
        p2 = mmsm([alt] + coords[1:], GD[:4], Q)
        if p2 != nested:
            changes_point += 1
        if p2 is not None and absorb_challenge(p2) != s_full:
            changes_output += 1
    assert changes_point == P - 1
    d1 = next(d for d in range(1, P) if add(smul(1, GD[0], Q), smul(d, GD[1], Q), Q) is None)
    other = [(coords[0] + 1) % P, (coords[1] + d1) % P] + coords[2:]
    assert other != coords and mmsm(other, GD[:4], Q) == nested
    frag['nested-binding'] = (
        f'Changing the first coordinate to each of the other ${P - 1}$ values gives ${changes_point}$ different points, and ${changes_output}$ of those change the sponge\'s output as well. '
        f'A vector of four entries from $\\F_{{31}}$ has ${P ** 4:,}$ possible values and $E\'$ has only 31 points, so collisions must exist. Here is one found by solving a discrete log: since $G\'_0 + {d1} \\cdot G\'_1 = \\mathcal{{O}}$, the vector ${fv(other, P)}$ gives the same point.')

    # ---- Section 8: deferred operations and stages ----
    # A small trace on the F_31 side: the stage holds the coordinates of A and B,
    # and the final part holds wires from the gate that adds them.
    w = Wires(P)
    S_ab = w.add_points(A, B_)
    gate0 = w.gates[0]
    final_part = [gate0[0], gate0[1], S_ab[0], S_ab[1]]
    assert all(final_part)
    stage = coords + [0, 0, 0, 0]
    final = [0, 0, 0, 0] + final_part
    trace = [(a + b) % P for a, b in zip(stage, final)]
    GS = GD[:8]
    stage_c = mmsm(stage, GS, Q)
    final_c = mmsm(final, GS, Q)
    full_c = mmsm(trace, GS, Q)
    assert stage_c == nested
    pw = Wires(Q)
    sum_c = pw.add_points(stage_c, final_c)
    sum_gates = len(pw.gates)
    assert sum_c == full_c
    frag['stage-run'] = (
        f'The circuit over $\\F_{{31}}$ adds $A$ and $B$. Its stage holds ${fv(coords, P)}$ and its later wires hold the slope, the difference of $x$-coordinates and the output, ${fv(final_part, P)}$, so the full vector is ${fv(trace, P)}$. '
        f'With eight generators of $E\'$, the stage commits to $\\mathring{{A}} = {show(stage_c)}$, the later part to $R\' = {show(final_c)}$, and the whole vector to $R = {show(full_c)}$. '
        f'The next step\'s circuit over $\\F_{{43}}$ adds $\\mathring{{A}}$ and $R\'$ in ${sum_gates}$ gates, gets ${show(sum_c)}$, and compares it with $R$.')

    caught = 0
    for alt in range(P):
        if alt == coords[0]:
            continue
        cheat = [alt] + trace[1:]
        if mmsm(cheat, GS, Q) != full_c:
            caught += 1
    assert caught == P - 1
    frag['stage-sum'] = (
        f'Suppose the prover traces the circuit with a different $x$-coordinate for $A$ while it leaves $\\mathring{{A}}$ alone. We tried each of the ${P - 1}$ other values. Each one changes $R$, and all ${caught}$ fail the comparison.')

    zeta = next(z for z in range(2, P) if pow(z, 3, P) == 1)
    A_star = (A[0] * zeta % P, A[1])
    assert on_curve(A_star, P) and A_star != A
    d = (A_star[0] - A[0]) % P
    bad_final = [d, 0, 0, 0] + final_part
    bad_trace = [(a + b) % P for a, b in zip(stage, bad_final)]
    assert bad_trace[0] == A_star[0]
    bad_c = mmsm(bad_final, GS, Q)
    bad_full = mmsm(bad_trace, GS, Q)
    assert add(stage_c, bad_c, Q) == bad_full
    all_d = 0
    for dd in range(1, P):
        f2 = [dd, 0, 0, 0] + final_part
        t2_ = [(a + b) % P for a, b in zip(stage, f2)]
        if add(stage_c, mmsm(f2, GS, Q), Q) == mmsm(t2_, GS, Q):
            all_d += 1
    assert all_d == P - 1
    frag['stage-overlap'] = (
        f'Let the prover put ${d}$ in slot 0 of the later part, which is reserved for the stage. The stage still says $x = {A[0]}$, but the sum holds ${A_star[0]}$ in that slot, so the circuit runs on ${show(A_star)}$ in place of $A$. That is a genuine point of $E$, because ${zeta}^3 = 1$ modulo 31 and the equation of $E$ only sees $x^3$. '
        f'The commitment check still passes, since $\\mathring{{A}} + R\'$ equals the commitment to the sum. It passes for all ${all_d}$ nonzero values in that slot, because a commitment to a sum equals the sum of the commitments however the entries overlap.')

    z_pass_one = sum(1 for z in range(P) if d * pow(z, 0, P) % P == 0)
    assert z_pass_one == 0
    worst = 0
    for d0 in range(1, P):
        for d1_ in range(1, P):
            worst = max(worst, sum(1 for z in range(P) if (d0 + d1_ * z) % P == 0))
    assert worst == 1
    frag['stage-mask'] = (
        f'For the entry above, the combination equals ${d}$ at every $z$, so all 31 values of $z$ catch it. A prover that uses two reserved slots can cancel at one $z$, and over all ${(P - 1) ** 2}$ pairs of nonzero entries, no pair passes at more than ${worst}$ value of $z$.')

    # ---- Section 9: crossing with a challenge ----
    big = 38
    assert big >= P
    wrong = smul(big % P, A, P)
    right = smul(big, A, P)
    assert wrong != right
    frag['big-challenge'] = (
        f'Suppose the challenge is ${big}$. On $E$, the scalar is a value modulo 43, and ${big} \\cdot A = {show(right)}$. A circuit over $\\F_{{31}}$ that holds the number as one wire holds ${big % P}$, and ${big % P} \\cdot A = {show(wrong)}$.')

    ch = [alpha, u, beta]
    gens_ch = GD[9:12]
    stage_ch = mmsm(ch, gens_ch, Q)
    pc = Wires(Q)
    acc_ch = None
    for k, g in zip(ch, gens_ch):
        term = pc.scalar_mul(k, g)
        acc_ch = term if acc_ch is None else pc.add_points(acc_ch, term)
    assert acc_ch == stage_ch
    wrong_ch = 0
    for alt in range(P):
        if alt == beta:
            continue
        if mmsm([alpha, u, alt], gens_ch, Q) != acc_ch:
            wrong_ch += 1
    assert wrong_ch == P - 1
    frag['challenge-bind'] = (
        f'The stage holds the vector ${fv(ch, P)}$ in $\\F_{{31}}$, with no blinding, on the generators ${", ".join(show(g) for g in gens_ch)}$, and its commitment is $C_s = {show(stage_ch)}$. '
        f'The circuit over $\\F_{{43}}$ knows the three challenges as wires, so it can break each into bits and compute $\\alpha \\cdot G\'_9 + u \\cdot G\'_{{10}} + \\beta \\cdot G\'_{{11}}$ on $E\'$ itself. This takes ${len(pc.gates)}$ gates and gives ${show(acc_ch)}$. '
        f'If the prover hands the other circuit any of the ${wrong_ch}$ other values of $\\beta$, the stage commits to a different point, and the comparison fails.')

    # Short challenges against false values. The cheater shifts its claims and its
    # values at u alike, so f(u) still matches, and aims the error at one beta.
    target = beta
    shifts = [1, -target % Q]
    false_ys = [(c['y'] + e) % Q for c, e in zip(cl1, shifts)]
    pass_full, pass_short = 0, 0
    for b in range(Q):
        vals = [(val + e) % Q for val, e in zip(a1['vals'], shifts)]
        fu = 0
        for c, val, y in zip(cl1, vals, false_ys):
            fu = (fu * alpha + (val - y) * pow((u - c['x']) % Q, -1, Q)) % Q
        assert fu == ev(a1['f'], u, Q)
        v = fu
        for val in vals:
            v = (v * b + val) % Q
        pc_ = lin([(b * b % Q, a1['f']), (b, cl1[0]['poly']), (1, cl1[1]['poly'])], Q)
        ok = ev(pc_, u, Q) == v
        pass_full += ok
        pass_short += ok and b < 16
    assert pass_full == 1 and pass_short == 1
    frag['short-count'] = (
        f'Take a cheater who claims $p_0(9) = {false_ys[0]}$ and $p_1(5) = {false_ys[1]}$ and shifts its values at $u$ by the same amounts, as in [chapter 08](./batched-openings.md#the-cheater-lies-about-a-value-at-u). The error in $v$ is $\\beta - {target}$, so one value of $\\beta$ out of the 43 passes, namely ${target}$. Since the cheater aimed at a short value, that same one passes among the 16 short challenges, which moves its chance from ${pass_full}$ in 43 to ${pass_short}$ in 16.')

    # ---- Section 10: two steps ----
    p1w, s1w = Wires(Q), Wires(P)
    b1 = fold(s1, cl1, alpha, u, beta, p1w, s1w)
    b2 = fold(s2, cl2, alpha, u, beta, s1w, p1w)
    trace1 = [g[0] for g in p1w.gates if g[0] > 1][:4]
    trace2 = [g[2] for g in s1w.gates if g[2] > 1][:4]
    assert all(trace1) and all(trace2)
    x1, x2 = 7, 12
    n1 = s1.claim(trace1, x1)
    n2 = s2.claim(trace2, x2)
    alpha2, u2, beta2 = 6, 10, 9
    assert beta2 >> 3 == 1
    acc1 = dict(poly=b1['poly'], x=b1['u'], y=b1['v'], C=b1['P'])
    acc2 = dict(poly=b2['poly'], x=b2['u'], y=b2['v'], C=b2['P'])
    assert u2 not in (acc1['x'], n1['x'], acc2['x'], n2['x'])
    p2w, s2w = Wires(Q), Wires(P)
    c1 = fold(s1, [acc1, n1], alpha2, u2, beta2, p2w, s2w)
    c2 = fold(s2, [acc2, n2], alpha2, u2, beta2, s2w, p2w)

    frag['two-steps'] = rows(
        ['', 'Step 1', 'Step 2'],
        [['Accumulator on $E$ on entry', 'Claims $p_0$, $p_1$ above', f"$({show(acc1['C'])},\\ {acc1['x']},\\ {acc1['y']})$"],
         ["Accumulator on $E'$ on entry", "Claims $p'_0$, $p'_1$ above", f"$({show(acc2['C'])},\\ {acc2['x']},\\ {acc2['y']})$"],
         ['New claim on $E$ on entry', 'None', f"$({show(n1['C'])},\\ {n1['x']},\\ {n1['y']})$, from step 1's circuit over $\\F_{{43}}$"],
         ["New claim on $E'$ on entry", 'None', f"$({show(n2['C'])},\\ {n2['x']},\\ {n2['y']})$, from step 1's circuit over $\\F_{{31}}$"],
         ['Challenges $\\alpha, u, \\beta$', f'${alpha}, {u}, {beta}$', f'${alpha2}, {u2}, {beta2}$'],
         ['Circuit over $\\F_{43}$ outputs', f"$v = {b1['v']}$, $P' = {show(b2['P'])}$", f"$v = {c1['v']}$, $P' = {show(c2['P'])}$"],
         ['Circuit over $\\F_{31}$ outputs', f"$v' = {b2['v']}$, $P = {show(b1['P'])}$", f"$v' = {c2['v']}$, $P = {show(c1['P'])}$"],
         ['Gates over $\\F_{43}$ / $\\F_{31}$', f'{len(p1w.gates)} / {len(s1w.gates)}', f'{len(p2w.gates)} / {len(s2w.gates)}']])

    assert s1.commit(c1['poly']) == c1['P'] and ev(c1['poly'], u2, Q) == c1['v']
    assert s2.commit(c2['poly']) == c2['P'] and ev(c2['poly'], u2, P) == c2['v']
    # A false value in step 1's first-side claim reaches the final decider.
    bad_v = (b1['v'] + 1) % Q
    bad_acc = dict(acc1, y=bad_v)
    d1f = fold_false(s1, [bad_acc, n1], alpha2, u2, beta2)
    assert d1f != c1['v']
    frag['two-steps-decide'] = (
        f'The decider commits to the two final polynomials $p = {fv(c1["poly"], Q)}$ and $p\' = {fv(c2["poly"], P)}$, which gives ${show(c1["P"])}$ on $E$ and ${show(c2["P"])}$ on $E\'$, and it evaluates them at $u = {u2}$ to get ${c1["v"]}$ and ${c2["v"]}$. '
        f'That single decision on each curve covers the two claims of step 1 and the two traces it produced. If the value in the accumulator on $E$ had been ${bad_v}$ at the start of step 2, the circuit would have derived $v = {d1f}$, and the decider would have rejected, since the polynomial still evaluates to ${c1["v"]}$.')

    # ---- Section 11: a wrong output cannot satisfy the gates ----
    a, c = A, B_
    honest = add(a, c)
    tried = passed = 0
    for out in curve_points():
        if out == honest:
            continue
        for s in range(P):
            tried += 1
            g1 = s * (c[0] - a[0]) % P == (c[1] - a[1]) % P
            g2 = s * s % P == (out[0] + a[0] + c[0]) % P
            g3 = s * (a[0] - out[0]) % P == (out[1] + a[1]) % P
            if g1 and g2 and g3:
                passed += 1
    assert passed == 0
    frag['gates-exact'] = (
        f'We tried every wrong output for the addition of $A$ and $B$ with every possible slope witness, which makes ${tried:,}$ attempts on the circuit over $\\F_{{31}}$, and none satisfied the three gates. The transcript and the commitments did not enter into that count.')

    assert 143 == 2 + 3 * 47
    return frag


def fold_false(side, claims, alpha, u, beta):
    """The verifier's value for the fold when one input y is false."""
    m_ = len(claims)
    vals = [ev(c['poly'], u, side.m) for c in claims]
    fu = 0
    for c, val in zip(claims, vals):
        fu = (fu * alpha + (val - c['y']) * pow((u - c['x']) % side.m, -1, side.m)) % side.m
    v = fu
    for val in vals:
        v = (v * beta + val) % side.m
    return v


if __name__ == '__main__':
    print(json.dumps(main()))
