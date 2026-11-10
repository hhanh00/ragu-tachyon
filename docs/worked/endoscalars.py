"""Worked examples for endoscalars.md. Prints fragments as JSON.

The toy endoscalar has the layout of Ragu's with one digit in place of 47, which
gives 5 bits. Every walk runs through a tracer with one entry per multiplication
gate, so the gate counts come from running the gates, including the 480 and 433
of the real width on the Pasta curves. Importing this module (the Manim figure
may) prints nothing unless it runs as a script.
"""
import contextlib
import io
import json
import math
from fractions import Fraction

from toy_curve import B, B_DUAL, G, P, Q, add, curve_points, mul, show

with contextlib.redirect_stdout(io.StringIO()):
    from curve_cycles import GD, Side, Wires, ev, fv, lin, mmsm, on_curve, plain_scalar_gates, rows, smul

# Each field's one cube root constant. It acts on coordinates of the curve over
# that field, and it is the eigenvalue of the partner curve's endomorphism.
ZETA = {P: 5, Q: 6}
ORDER = {P: Q, Q: P}
PASTA_P = 0x40000000000000000000000000000000224698fc094cf91b992d30ed00000001
PASTA_Q = 0x40000000000000000000000000000000224698fc0994a8dd8c46eb2100000001
# From the pasta_curves crate. Section 3 checks them against both curves.
PASTA_ZP = 0x12ccca834acdba712caad5dc57aab1b01d1f8bd237ad31491dad5ebdfdfe4ab9
PASTA_ZQ = 0x06819a58283e528e511db4d81cf70f5a0fed467d47c033af2aa9d2e050aa0e4f
ZETA[PASTA_P] = PASTA_ZP
ZETA[PASTA_Q] = PASTA_ZQ
ORDER[PASTA_P] = PASTA_Q
ORDER[PASTA_Q] = PASTA_P
assert PASTA_ZP != 1 and pow(PASTA_ZP, 3, PASTA_P) == 1
assert PASTA_ZQ != 1 and pow(PASTA_ZQ, 3, PASTA_Q) == 1


def fmul(k, a, f):
    """Double-and-add, for scalars too large for toy_curve.mul."""
    out = None
    while k:
        if k & 1:
            out = add(out, a, f)
        a = add(a, a, f)
        k >>= 1
    return out


def phi(a, f, z=None):
    if a is None:
        return None
    return (a[0] * (ZETA[f] if z is None else z) % f, a[1])


def neg(a, f):
    return None if a is None else (a[0], -a[1] % f)


# ---- The ring Z[lambda], with lambda^2 = -1 - lambda. (a, b) means a + b lambda ----
ONE, LAM, LAM2, TWIST = (1, 0), (0, 1), (-1, -1), (1, -1)


def e_add(x, y):
    return (x[0] + y[0], x[1] + y[1])


def e_scale(c, x):
    return (c * x[0], c * x[1])


def e_mul(x, y):
    a, b = x
    c, d = y
    return (a * c - b * d, a * d + b * c - b * d)


def norm(x):
    return x[0] * x[0] - x[0] * x[1] + x[1] * x[1]


def image(x, m):
    return (x[0] + x[1] * ZETA[m]) % m


def e_show(x):
    a, b = x
    if b == 0:
        return f'{a}'
    lam = r'\lambda' if abs(b) == 1 else f'{abs(b)}\\lambda'
    if a == 0:
        return ('-' if b < 0 else '') + lam
    return f'{a} {"-" if b < 0 else "+"} {lam}'


assert e_mul(LAM, LAM) == LAM2 and e_mul(LAM, LAM2) == ONE
assert norm(TWIST) == 3 and all(norm(u) == 1 for u in (ONE, LAM, LAM2))


def bits_of(s, width):
    assert 0 <= s < 2 ** width
    return [(s >> i) & 1 for i in range(width)]


def bstr(bits):
    return ''.join(str(b) for b in bits)


def unit(s0, e0):
    return e_scale(-1 if s0 else 1, LAM if e0 else ONE)


def digit(s, e1, e2):
    return e_scale(-1 if s else 1, {(0, 0): ONE, (1, 0): LAM, (0, 1): LAM2, (1, 1): TWIST}[(e1, e2)])


def split_bits(bits):
    assert (len(bits) - 2) % 3 == 0
    return bits[0], bits[1], [tuple(bits[2 + 3 * i:5 + 3 * i]) for i in range((len(bits) - 2) // 3)]


def element(bits):
    """The effective scalar as an element of Z[lambda], by Horner in radix 3."""
    s0, e0, digits = split_bits(bits)
    acc = e_scale(2, unit(s0, e0))
    for dg in digits:
        acc = e_add(e_scale(3, acc), digit(*dg))
    return acc


def lift(bits, m):
    """lift_endoscalar: the same Horner walk with lambda the field's cube root."""
    s0, e0, digits = split_bits(bits)
    z = ZETA[m]
    acc = (z if e0 else 1)
    acc = (-acc if s0 else acc) * 2 % m
    for s, e1, e2 in digits:
        d = {(0, 0): 1, (1, 0): z, (0, 1): z * z, (1, 1): 1 - z}[(e1, e2)]
        acc = (3 * acc + (-d if s else d)) % m
    assert acc == image(element(bits), m)
    return acc


class Exceptional(Exception):
    """An incomplete addition met equal x-coordinates."""


def divide_gate(w, n, d):
    if d % w.mod == 0:
        raise Exceptional()
    q = n * pow(d, -1, w.mod) % w.mod
    assert w.mul(q, d) == n % w.mod
    return q


def select_plain(w, r, s, u, v):
    """The three-gate selector of Endoscalar::group_scale."""
    f, z = w.mod, ZETA[w.mod]
    third = pow(3, -1, f)
    zm1, z2m1 = z - 1, z * z - 1
    h = w.mul((r + zm1 * third * third * 4 * u) % f, (zm1 * u + z2m1 * v) % f)
    j = w.mul((u + v - 1) % f, h)
    xd = (r + h + zm1 * third * j + z * third * 4 * u) % f
    yd = w.mul((1 - 2 * s) % f, (r - 2 * z * third * j) % f)
    return xd, yd


def select_hoisted(w, r, s, u, v):
    """The two-gate selector of HoistedEndoscalar::group_scale. The products p
    and q are wires of a shared stage, so they cost no gates here."""
    f, z = w.mod, ZETA[w.mod]
    third = pow(3, -1, f)
    p_ = u * v
    q_ = p_ * s
    lx = (1 + (z - 1) * u + (z * z - 1) * v + (1 - z) * p_) % f
    xd = (w.mul(r, lx) - z * z * third * 4 * p_) % f
    c1 = 1 + 2 * z
    pm2q = p_ - 2 * q_
    ly = (1 - 2 * s + (c1 - 1) * pm2q) % f
    yd = (w.mul(r, ly) - c1 * third * third * 8 * pm2q) % f
    return xd, yd


def triple_plus(w, x, y, xd, yd, log=None):
    """[3]A + D = ((A + D) + A) + A, seven gates."""
    f = w.mod
    neg2y = -2 * y % f
    t1 = divide_gate(w, (yd - y) % f, (xd - x) % f)
    x1 = (w.mul(t1, t1) - x - xd) % f
    t2 = (divide_gate(w, neg2y, (x1 - x) % f) - t1) % f
    x2 = (w.mul(t2, t2) - x1 - x) % f
    t3 = (divide_gate(w, neg2y, (x2 - x) % f) - t2) % f
    x3 = (w.mul(t3, t3) - x2 - x) % f
    y3 = (w.mul(t3, (x - x3) % f) - y) % f
    if log is not None:
        log.update(t1=t1, x1=x1, t2=t2, x2=x2, t3=t3, x3=x3, y3=y3)
    return x3, y3


def walk(w, bits, pt, select=select_plain, trace=None):
    """The radix-3 walk: normalize, double, one tripling per digit, move back."""
    f, z = w.mod, ZETA[w.mod]
    x, y = pt
    assert x % f and y % f
    # Normalize to (r, r) in three gates.
    c = divide_gate(w, x, y)
    c2 = w.mul(c, c)
    r = w.mul(c2, x)
    # The initial doubling in four gates. The tangent at (r, r) has slope 3r/2.
    s0, e0, digits = split_bits(bits)
    t = 3 * r * pow(2, -1, f) % f
    x2 = (w.mul(t, t) - 2 * r) % f
    y2 = (w.mul(t, (r - x2) % f) - r) % f
    ax = w.mul(x2, (1 + e0 * (z - 1)) % f)
    ay = w.mul(y2, (1 - 2 * s0) % f)
    if trace is not None:
        trace.update(c=c, r=r, A0=(ax, ay), digits=[])
    for s, u, v in digits:
        xd, yd = select(w, r, s, u, v)
        log = {} if trace is not None else None
        ax, ay = triple_plus(w, ax, ay, xd, yd, log)
        if trace is not None:
            log.update(D=(xd, yd), out=(ax, ay))
            trace['digits'].append(log)
    # Move back in three gates.
    c3 = w.mul(c2, c)
    out = (divide_gate(w, ax, c2), divide_gate(w, ay, c3))
    assert out == fmul(lift(bits, ORDER[f]), pt, f)
    return out


def walk_gates(n, select=select_plain):
    """Run the walk on the real curves and count the gates."""
    w = Wires(PASTA_Q)
    walk(w, bits_of(2 ** (2 + 3 * n) // 3, 2 + 3 * n), (PASTA_Q - 1, 2), select)
    return len(w.gates)


def main():
    frag = {}
    G0, G1, G2, G3 = G
    GP = GD[0]
    A, B_ = (27, 30), (6, 23)
    assert on_curve(A, P) and on_curve(B_, P) and on_curve(GP, Q)

    # ---- Section 2: the map, and the addition law ----
    roots = sorted(z for z in range(1, P) if pow(z, 3, P) == 1)
    assert roots == [1, 5, 25]
    im = phi(G0, P)
    assert on_curve(im, P)
    frag['endo-map'] = (
        f'The cube roots of 1 in $\\F_{{31}}$ are ${roots[0]}$, ${roots[1]}$ and ${roots[2]}$, since $5^3 = 125 = 4 \\cdot 31 + 1$ and $25 = 5^2$. '
        f'We take $\\zeta = {ZETA[P]}$. The generator $G_0 = {show(G0)}$ maps to $\\phi(G_0) = {show(im)}$, and this image is on $E$, because $2^2 = 4$ and ${im[0]}^3 + {B} = {im[0] ** 3 + B}$, which equals $4$ modulo 31.')

    sm = add(A, B_)
    assert phi(sm, P) == add(phi(A, P), phi(B_, P))
    assert all(phi(add(a, c), P) == add(phi(a, P), phi(c, P)) for a in curve_points() for c in curve_points())
    assert all(on_curve(phi(a, P), P) for a in curve_points())
    n_pairs = len(curve_points()) ** 2
    frag['endo-hom'] = (
        f'Take $A = {show(A)}$ and $B = {show(B_)}$ from [Chapter 8](./batched-openings.md#_8-the-complete-protocol). Their sum is ${show(sm)}$, which maps to ${show(phi(sm, P))}$. '
        f'Mapping first gives $\\phi(A) = {show(phi(A, P))}$ and $\\phi(B) = {show(phi(B_, P))}$, and these add to ${show(add(phi(A, P), phi(B_, P)))}$. We confirmed the identity on all ${n_pairs:,}$ ordered pairs of affine points of $E$.')

    # ---- Section 2: the eigenvalue ----
    lam43 = ZETA[Q]
    assert all(phi(a, P) == mul(lam43, a) for a in curve_points())
    frag['endo-eigen'] = rows(
        ['Point $T$', '$\\phi(T)$', 'Multiple of $T$ that equals $\\phi(T)$'],
        [[f'$G_{i} = {show(a)}$', f'${show(phi(a, P))}$', f'${next(k for k in range(1, Q) if mul(k, a) == phi(a, P))}$'] for i, a in enumerate(G)])
    frag['endo-eigen-check'] = (
        f'Every row gives the same multiple, and the same holds for all {len(curve_points())} affine points. So on $E$ with $\\zeta = {ZETA[P]}$ we have $\\lambda = {lam43}$, and indeed ${lam43}^2 + {lam43} + 1 = {lam43 ** 2 + lam43 + 1} = {(lam43 ** 2 + lam43 + 1) // Q} \\cdot 43$.')

    gates3 = plain_scalar_gates(3)
    frag['endo-cost'] = (
        f'Computing $6 \\cdot G_0$ by the double-and-add of the [recursive proofs chapter](./recursive-proofs.md#point-operations) would take ${gates3}$ gates for a 3-bit scalar, while $\\phi(G_0)$ takes no gates, because multiplying a wire by the constant ${ZETA[P]}$ is part of a linear combination. '
        f'The contrast is sharper on Pasta, where $\\lambda$ is a scalar of about {PASTA_ZQ.bit_length()} bits, and a multiplication by it would cost about ${plain_scalar_gates(PASTA_ZQ.bit_length()):,}$ gates with the same method.')

    # ---- Section 3: the pairing ----
    pair_rows = []
    for f, curve, lams in [(P, '$E$', (6, 36)), (Q, "$E'$", (5, 25))]:
        pts = curve_points(f, B if f == P else B_DUAL)
        roots_f = sorted(z for z in range(2, f) if pow(z, 3, f) == 1)
        for z in roots_f:
            found = [l for l in lams if all(phi(a, f, z) == mul(l, a, f) for a in pts)]
            assert len(found) == 1
            pair_rows.append([curve, f'$\\F_{{{f}}}$', f'${z}$', f'$\\F_{{{ORDER[f]}}}$', f'${found[0]}$'])
    assert [r[2] for r in pair_rows] == ['$5$', '$25$', '$6$', '$36$']
    assert [r[4] for r in pair_rows] == ['$6$', '$36$', '$5$', '$25$']
    frag['pairing'] = rows(['Curve', 'Coordinate field', '$\\zeta$', 'Scalar field', '$\\lambda$'], pair_rows)

    lam_of = {(r[0], int(r[2].strip('$'))): int(r[4].strip('$')) for r in pair_rows}
    c31, c43, bad43 = ZETA[P], ZETA[Q], 36
    assert lam_of[('$E$', c31)] == c43 and lam_of[("$E'$", c43)] == c31
    assert lam_of[('$E$', c31)] != bad43
    sq31, sq43 = c31 * c31 % P, c43 * c43 % Q
    assert lam_of[('$E$', sq31)] == sq43 and lam_of[("$E'$", sq43)] == sq31
    frag['pairing-choice'] = (
        f'Take the pair $c_{{31}} = {c31}$ and $c_{{43}} = {c43}$. In row 1, $\\zeta = {c31}$ on $E$ gives $\\lambda = {lam_of[("$E$", c31)]}$, which equals $c_{{43}}$, so the first equation holds. In row 3, $\\zeta = {c43}$ on $E\'$ gives $\\lambda = {lam_of[("$E\'$", c43)]}$, which equals $c_{{31}}$, so the second holds too. '
        f'The pair $c_{{31}} = {c31}$ and $c_{{43}} = {bad43}$ fails the first equation, because row 1 still gives $\\lambda = {lam_of[("$E$", c31)]}$ on $E$, and that disagreement is the mismatch of the example above. '
        f'The squares, $c_{{31}} = {sq31}$ and $c_{{43}} = {sq43}$, form the other consistent pair, through rows 2 and 4.')
    # What breaks when the constants do not line up: 3 + 2 lambda on E, with F_43's
    # constant 36 in place of 6.
    mm = (3, 2)
    walked = add(mul(3, G0), mul(2, phi(G0, P)))
    good = (mm[0] + mm[1] * ZETA[Q]) % Q
    badc = 36
    badv = (mm[0] + mm[1] * badc) % Q
    assert walked == mul(good, G0) and walked != mul(badv, G0) and pow(badc, 3, Q) == 1
    frag['pairing-mismatch'] = (
        f'Take the combination $3 \\cdot G_0 + 2 \\cdot \\phi(G_0)$ on $E$, where $\\phi$ uses $\\zeta = {ZETA[P]}$. The secondary circuit, over $\\F_{{31}}$, computes it with point additions and gets ${show(walked)}$, which is ${good} \\cdot G_0$ because $\\phi$ acts as multiplication by ${ZETA[Q]}$. '
        f'The primary circuit, over $\\F_{{43}}$, has to produce the matching number $3 + 2\\lambda$ from its own constant. With the constant ${ZETA[Q]}$ it gets $3 + 2 \\cdot {ZETA[Q]} = {good}$, which agrees. With the other cube root, ${badc}$, it gets $3 + 2 \\cdot {badc} = {3 + 2 * badc}$, which is ${badv}$ modulo 43, and ${badv} \\cdot G_0 = {show(mul(badv, G0))}$ is a different point. The number and the point would then describe different scalars.')
    pal, ves = (PASTA_P - 1, 2), (PASTA_Q - 1, 2)
    assert on_curve_pasta(pal, PASTA_P) and on_curve_pasta(ves, PASTA_Q)
    assert fmul(PASTA_ZQ, pal, PASTA_P) == phi(pal, PASTA_P)
    assert fmul(PASTA_ZP, ves, PASTA_Q) == phi(ves, PASTA_Q)
    assert fmul(PASTA_ZQ ** 2 % PASTA_Q, pal, PASTA_P) == phi(pal, PASTA_P, PASTA_ZP ** 2 % PASTA_P)
    assert fmul(PASTA_ZP ** 2 % PASTA_P, ves, PASTA_Q) == phi(ves, PASTA_Q, PASTA_ZQ ** 2 % PASTA_Q)
    assert fmul(PASTA_ZQ, pal, PASTA_P) != phi(pal, PASTA_P, PASTA_ZP ** 2 % PASTA_P)
    frag['pasta-pair'] = (
        '$$\n\\begin{aligned}\n'
        f'\\zeta_p &= \\texttt{{{PASTA_ZP:#066x}}}, \\\\\n'
        f'\\zeta_q &= \\texttt{{{PASTA_ZQ:#066x}}}.\n'
        '\\end{aligned}\n$$\n\n'
        'We multiplied the point $(-1,\\,2)$ of Pallas by $\\zeta_q$ and got $(-\\zeta_p,\\,2)$, and we multiplied the point $(-1,\\,2)$ of Vesta by $\\zeta_p$ and got $(-\\zeta_q,\\,2)$. '
        'Replacing $\\zeta_p$ with its square while $\\zeta_q$ stays the same makes the first test fail.')

    # ---- Section 4: the ring ----
    ex = (3, 2)
    frag['ring-map'] = (
        f'Take ${e_show(ex)}$. With $\\lambda = {ZETA[Q]}$ it maps to $3 + 2 \\cdot {ZETA[Q]} = {image(ex, Q)}$ in $\\F_{{43}}$, and with $\\lambda = {ZETA[P]}$ it maps to $3 + 2 \\cdot {ZETA[P]} = {image(ex, P)}$ in $\\F_{{31}}$. '
        f'Applied to $G_0$ on $E$, the element means $3 \\cdot G_0 + 2 \\cdot \\phi(G_0) = {show(add(mul(3, G0), mul(2, phi(G0, P))))}$, and ${image(ex, Q)} \\cdot G_0$ is the same point. '
        f'Applied to $G\' = {show(GP)}$ on $E\'$, it means $3 \\cdot G\' + 2 \\cdot \\phi(G\') = {show(add(smul(3, GP, Q), smul(2, phi(GP, Q), Q), Q))}$, and ${image(ex, P)} \\cdot G\'$ is the same point.')
    assert add(mul(3, G0), mul(2, phi(G0, P))) == mul(image(ex, Q), G0)
    assert add(smul(3, GP, Q), smul(2, phi(GP, Q), Q), Q) == smul(image(ex, P), GP, Q)

    rng = range(-8, 9)
    elems = [(a, b) for a in rng for b in rng]
    assert all(image(e_mul(x, y), m) == image(x, m) * image(y, m) % m
               for x in elems[::7] for y in elems[::11] for m in (P, Q))
    assert all(norm(e_mul(x, y)) == norm(x) * norm(y) for x in elems[::7] for y in elems[::11])

    k31, k43 = (5, -1), (1, 7)
    assert norm(k31) == 31 and image(k31, P) == 0 and image(k31, Q) != 0
    assert norm(k43) == 43 and image(k43, Q) == 0 and image(k43, P) != 0
    big = range(-40, 41)
    zero31 = [(a, b) for a in big for b in big if (a, b) != (0, 0) and image((a, b), P) == 0]
    zero43 = [(a, b) for a in big for b in big if (a, b) != (0, 0) and image((a, b), Q) == 0]
    assert all(norm(x) % 31 == 0 for x in zero31) and all(norm(x) % 43 == 0 for x in zero43)
    assert min(norm(x) for x in zero31) == 31 and min(norm(x) for x in zero43) == 43
    frag['ring-zero'] = (
        f'The element ${e_show(k31)}$ has norm $25 + 5 + 1 = {norm(k31)}$. With $\\lambda = {ZETA[P]}$ it maps to $0$ in $\\F_{{31}}$, while in $\\F_{{43}}$ it maps to ${image(k31, Q)}$. '
        f'The element ${e_show(k43)}$ has norm $1 - 7 + 49 = {norm(k43)}$, and it maps to $0$ in $\\F_{{43}}$ and to ${image(k43, P)}$ in $\\F_{{31}}$. '
        f'We searched all coefficients from $-40$ to $40$. Each of the ${len(zero31)}$ nonzero elements that map to $0$ in $\\F_{{31}}$ has a norm divisible by 31, and each of the ${len(zero43)}$ that map to $0$ in $\\F_{{43}}$ has a norm divisible by 43.')

    # ---- Section 5: digits and decoding ----
    names = [('(0, 0)', ONE, '1'), ('(1, 0)', LAM, '\\lambda'), ('(0, 1)', LAM2, '\\lambda^2'), ('(1, 1)', TWIST, '1 - \\lambda')]
    res_rows, residues = [], set()
    for pair, val, name in names:
        n_ = norm(val)
        for s, sign, v in [(0, '', val), (1, '-', e_scale(-1, val))]:
            r_ = (v[0] % 3, v[1] % 3)
            assert r_ != (0, 0)
            residues.add(r_)
            label = f'${sign}({name})$' if sign and ' ' in name else f'${sign}{name}$'
            res_rows.append([f'$({s}, {pair[1]}, {pair[4]})$', label, f'$({v[0]},\\ {v[1]})$', f'$({r_[0]},\\ {r_[1]})$', f'${n_}$'])
    assert len(residues) == 8
    frag['digits'] = rows(['$(s, e_1, e_2)$', 'Digit', 'As $(a, b)$', 'Modulo 3', 'Norm'], res_rows)

    # The radix-2 clash from the book.
    left = e_add(e_scale(2, ONE), LAM)
    right = e_add(e_scale(2, e_scale(-1, LAM2)), e_scale(-1, LAM))
    assert left == right == (2, 1)
    frag['radix2-clash'] = (
        f'For instance, $2 \\cdot 1 + \\lambda$ and $2 \\cdot (-\\lambda^2) + (-\\lambda)$ are both ${e_show(left)}$, because $-\\lambda^2 = 1 + \\lambda$.')

    # A longer string, decoded digit by digit.
    n3 = 3
    width3 = 2 + 3 * n3
    s3 = 0b01100111010
    bits3 = bits_of(s3, width3)
    k3 = element(bits3)
    s0, e0, digs = split_bits(bits3)
    assert len(set(digit(*d) for d in digs)) == 3 and k3[1] != 0
    dec_rows, cur = [], k3
    decoded = []
    table = {}
    for dg in [(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]:
        v = digit(*dg)
        table[(v[0] % 3, v[1] % 3)] = dg
    for i in range(n3 - 1, -1, -1):
        dg = table[(cur[0] % 3, cur[1] % 3)]
        v = digit(*dg)
        nxt = e_add(cur, e_scale(-1, v))
        assert nxt[0] % 3 == 0 and nxt[1] % 3 == 0
        if not dec_rows:
            dec_first = (cur, v, nxt, (nxt[0] // 3, nxt[1] // 3))
        nxt = (nxt[0] // 3, nxt[1] // 3)
        dec_rows.append([f'${e_show(cur)}$', f'$({cur[0] % 3},\\ {cur[1] % 3})$', f'${e_show(v)}$', f'${e_show(nxt)}$'])
        decoded.insert(0, dg)
        cur = nxt
    assert decoded == digs and cur == e_scale(2, unit(s0, e0))
    frag['decode-setup'] = (
        f'Take the 11-bit string `{bstr(bits3)}`, which has three digits. Its first two bits say $s_0 = {s0}$ and $e_0 = {e0}$, its digits are ${e_show(digit(*digs[0]))}$, ${e_show(digit(*digs[1]))}$ and ${e_show(digit(*digs[2]))}$, and Horner gives $k = {e_show(k3)}$. Starting from $k$ alone, we read the last digit from its residue modulo 3, subtract it, and divide by 3:')
    frag['decode'] = rows(['Current value', 'Modulo 3', 'Digit it must end in', 'After subtracting and dividing by 3'], dec_rows)
    frag['decode-end'] = (
        'In the first row, for instance, subtracting the digit gives $' + e_show(dec_first[0]) + ' - (' + e_show(dec_first[1]) + ') = ' + e_show(dec_first[2]) + ' = 3(' + e_show(dec_first[3]) + ')$, so the division by 3 is exact. '
        f'The value that remains after the last row is ${e_show(cur)}$, which is $2 \\cdot ({e_show(unit(s0, e0))})$, so the first two bits are $s_0 = {s0}$ and $e_0 = {e0}$. The string comes back in full.')

    for n_ in range(0, 5):
        width = 2 + 3 * n_
        seen = {}
        for s in range(2 ** width):
            seen.setdefault(element(bits_of(s, width)), s)
        assert len(seen) == 2 ** width
    n_small = 4
    enc_small = [element(bits_of(s, 2 + 3 * n_small)) for s in range(2 ** (2 + 3 * n_small))]
    frag['ring-injective'] = (
        f'We enumerated every string for $n$ from 0 to {n_small}, which at $n = {n_small}$ means ${2 ** (2 + 3 * n_small):,}$ strings, and no two gave the same element of $\\mathbb{{Z}}[\\lambda]$.')

    # ---- Section 6: one string, two scalars, and the walk ----
    beta_val = 31
    bits = bits_of(beta_val, 5)
    k = element(bits)
    beta, beta_n = lift(bits, Q), lift(bits, P)
    assert beta and beta_n and beta != beta_n and beta != beta_val and beta_n != beta_val
    s0, e0, ((s_, e1, e2),) = split_bits(bits)
    d0 = digit(s_, e1, e2)
    u0 = unit(s0, e0)
    frag['lift-run'] = (
        f'Take the string `{bstr(bits)}`. Its first two bits are $s_0 = {s0}$ and $e_0 = {e0}$, so the initial unit is ${e_show(u0)}$. The remaining three bits are $(s, e_1, e_2) = ({s_}, {e1}, {e2})$, so the digit is $-(1 - \\lambda)$. The element is\n\n'
        f'$$k = 2 \\cdot 3 \\cdot (-\\lambda) - (1 - \\lambda) = -6\\lambda - 1 + \\lambda = {e_show(k)}.$$\n\n'
        f'With $\\lambda = {ZETA[Q]}$ this is ${beta}$ in $\\F_{{43}}$, and with $\\lambda = {ZETA[P]}$ it is ${beta_n}$ in $\\F_{{31}}$. As an integer, the string is ${beta_val}$, and neither scalar has any simple relation to that number.')
    assert k == (-1, -5) and (s0, e0, s_, e1, e2) == (1, 1, 1, 1, 1)

    show_list = [3, 11, 13, 20, 26, 31]
    lt_rows = []
    for s in show_list:
        b = bits_of(s, 5)
        lt_rows.append([f'`{bstr(b)}`', f'${s}$', f'${e_show(element(b))}$', f'${lift(b, Q)}$', f'${lift(b, P)}$'])
    frag['lift-table'] = rows(['String', 'As an integer', 'Element', 'Scalar in $\\F_{43}$', 'Scalar in $\\F_{31}$'], lt_rows)

    # The walk on each curve, in plain point arithmetic first.
    def plain_walk(b, pt, f):
        s0_, e0_, dgs = split_bits(b)
        a0 = phi(pt, f) if e0_ else pt
        a0 = neg(a0, f) if s0_ else a0
        a0 = add(a0, a0, f)
        out = [a0]
        acc = a0
        for dg in dgs:
            dv = digit(*dg)
            d_ = add(smul(dv[0], pt, f), smul(dv[1], phi(pt, f), f), f)
            tr = add(add(acc, acc, f), acc, f)
            acc = add(tr, d_, f)
            out += [tr, d_, acc]
        return out

    w_rows = []
    for f, pt, curve, scal, nm in [(P, G0, '$E$', beta, '$G_0$'), (Q, GP, "$E'$", beta_n, "$G'$")]:
        a0, tr, d_, end = plain_walk(bits, pt, f)
        assert end == smul(scal, pt, f)
        w_rows.append([curve, f'${nm.strip("$")} = {show(pt)}$', f'${show(a0)}$', f'${show(tr)}$', f'${show(d_)}$', f'${show(end)}$', f'${scal}$'])
    frag['walk-note'] = (
        f'Both rows end at the multiple the lift predicts. On $E\'$ the tripled point returns to $G\'$ itself, because $A_0$ has index $-2\\lambda$ and $3 \\cdot (-2 \\cdot {ZETA[P]}) = {3 * -2 * ZETA[P]}$, which is $1$ modulo 31.')
    assert 3 * -2 * ZETA[P] % P == 1
    frag['walk-two-curves'] = rows(['Curve', 'Base point', '$A_0$', '$3 \\cdot A_0$', 'Digit point', '$A_1$', 'Direct multiple that equals $A_1$'], w_rows)

    # Section 7: the gates on the isomorphic curve.
    w = Wires(P)
    tr = {}
    out = walk(w, bits, G0, select_plain, tr)
    assert out == mul(beta, G0)
    gates_toy = len(w.gates)
    assert gates_toy == 3 + 4 + 10 + 3
    c, r = tr['c'], tr['r']
    bprime = (r * r - r ** 3) % P
    assert bprime == pow(c, 6, P) * B % P
    frag['normalize'] = (
        f'For $G_0 = {show(G0)}$ on $E$, we get $c = 1/2 = {c}$ and $r = c^2 x = {r}$. The new curve has constant $c^6 \\cdot {B} = {bprime}$, and $(r, r) = ({r},\\,{r})$ lies on it because ${r}^2 = {r * r % P}$ and ${r}^3 + {bprime} = {(r ** 3 + bprime) % P}$ modulo 31.')

    z = ZETA[P]
    third = pow(3, -1, P)
    tw_x = z * z * (r - 4 * third) % P
    tw_y = (1 + 2 * z) * (r - 8 * third * third) % P
    base = (r, r)
    assert add(base, neg(phi(base, P), P)) == (tw_x, tw_y)
    sel_rows = []
    for pair, val, name, form_x, form_y in [
        ((0, 0), ONE, '1', 'r', 'r'),
        ((1, 0), LAM, '\\lambda', '\\zeta r', 'r'),
        ((0, 1), LAM2, '\\lambda^2', '\\zeta^2 r', 'r'),
        ((1, 1), TWIST, '1 - \\lambda', '\\zeta^2 (r - 4/3)', '(1 + 2\\zeta)(r - 8/9)'),
    ]:
        direct = add(smul(val[0], base, P), smul(val[1], phi(base, P), P))
        probe = Wires(P)
        got = select_plain(probe, r, 0, pair[0], pair[1])
        assert got == direct and len(probe.gates) == 3
        probe = Wires(P)
        assert select_hoisted(probe, r, 0, pair[0], pair[1]) == direct and len(probe.gates) == 2
        sel_rows.append([f'$({pair[0]}, {pair[1]})$', f'${name}$', f'${form_x}$', f'${form_y}$', f'${show(direct)}$'])
    frag['digit-coords'] = rows(['$(e_1, e_2)$', 'Digit', '$x$', '$y$', 'At $r = ' + str(r) + '$'], sel_rows)

    # Every selector combination on both fields, against point arithmetic.
    checked = 0
    for f in (P, Q):
        pts = curve_points(f, B if f == P else B_DUAL)
        for pt in pts:
            cc = pt[0] * pow(pt[1], -1, f) % f
            rr = cc * cc * pt[0] % f
            bb = (rr, rr)
            assert (rr * rr - rr ** 3) % f == pow(cc, 6, f) * (B if f == P else B_DUAL) % f
            for s in (0, 1):
                for u in (0, 1):
                    for v in (0, 1):
                        val = digit(s, u, v)
                        want = add(mul_any(val[0], bb, f), mul_any(val[1], phi(bb, f), f), f)
                        assert select_plain(Wires(f), rr, s, u, v) == want
                        assert select_hoisted(Wires(f), rr, s, u, v) == want
                        checked += 1
    frag['selector-check'] = (
        f'We compared both selectors with direct point arithmetic for all eight digits at every affine point of both curves, which makes ${checked:,}$ comparisons, and they all agreed.')

    # The three-gate selector on our string's digit, at r = 8.
    sw = Wires(P)
    s_d, u_d, v_d = split_bits(bits)[2][0]
    third = pow(3, -1, P)
    left_f = (r + (z - 1) * 4 * third * third * u_d) % P
    right_f = ((z - 1) * u_d + (z * z - 1) * v_d) % P
    h_ = left_f * right_f % P
    j_ = (u_d + v_d - 1) * h_ % P
    xd_ = (r + h_ + (z - 1) * third * j_ + z * third * 4 * u_d) % P
    yd_ = (1 - 2 * s_d) * (r - 2 * z * third * j_) % P
    assert select_plain(sw, r, s_d, u_d, v_d) == (xd_, yd_) == tr['digits'][0]['D'] and len(sw.gates) == 3
    assert (xd_, yd_) == (tw_x, (-tw_y) % P)
    frag['selector-run'] = (
        f'For our string `{bstr(bits)}` the digit bits are $(s, e_1, e_2) = ({s_d}, {u_d}, {v_d})$. On $\\F_{{31}}$ we have $r = {r}$, $\\zeta = {z}$ and $1/3 = {third}$:\n\n'
        + rows(['Gate', 'Equation', 'Value'],
               [[1, '$h = \\big(r + \\tfrac{4}{9}(\\zeta - 1) e_1\\big)\\big((\\zeta - 1) e_1 + (\\zeta^2 - 1) e_2\\big)$', f'$h = {left_f} \\cdot {right_f} = {h_}$'],
                [2, '$j = (e_1 + e_2 - 1)\\, h$', f'$j = {j_}$'],
                [3, '$y_D = (1 - 2s)\\big(r - \\tfrac{2\\zeta}{3} j\\big)$', f'$y_D = {yd_}$'],
                ['none', '$x_D = r + h + \\tfrac{\\zeta - 1}{3} j + \\tfrac{4\\zeta}{3} e_1$', f'$x_D = {xd_}$']])
        + f'\n\nThe point $D = ({xd_},\\,{yd_})$ is the negation of the $1 - \\lambda$ row of the table, $({tw_x},\\,{tw_y})$, as the sign bit $s = 1$ requires.')

    d0_log = tr['digits'][0]
    a0x, a0y = tr['A0']
    frag['triple-run'] = rows(
        ['Gate', 'Equation', 'Value'],
        [[1, '$t_1 (x_D - x) = y_D - y$', f"$t_1 = {d0_log['t1']}$"],
         [2, '$x_1 = t_1^2 - x - x_D$', f"$x_1 = {d0_log['x1']}$"],
         [3, '$(t_1 + t_2)(x_1 - x) = -2y$', f"$t_2 = {d0_log['t2']}$"],
         [4, '$x_2 = t_2^2 - x_1 - x$', f"$x_2 = {d0_log['x2']}$"],
         [5, '$(t_2 + t_3)(x_2 - x) = -2y$', f"$t_3 = {d0_log['t3']}$"],
         [6, '$x_3 = t_3^2 - x_2 - x$', f"$x_3 = {d0_log['x3']}$"],
         [7, '$y_3 = t_3 (x - x_3) - y$', f"$y_3 = {d0_log['y3']}$"]])
    # The same tripling through ordinary point addition, on the isomorphic curve.
    a0 = (a0x, a0y)
    dd = d0_log['D']
    assert add(add(add(a0, dd), a0), a0) == d0_log['out'] == (d0_log['x3'], d0_log['y3'])
    frag['triple-setup'] = (
        f'Here is the digit step for our string `{bstr(bits)}` on $G_0$. Its first two bits make the initial unit $-\\lambda$, so the 4-gate doubling turns the normalized base point $({r},\\,{r})$ into $A_0 = -2\\lambda \\cdot ({r},\\,{r}) = {show(a0)}$. The digit point is the $D = {show(dd)}$ that the selector produced above.')
    c3 = c * c * c % P
    frag['triple-end'] = (
        f'So the result on the normalized curve is ${show(d0_log["out"])}$, which three additions outside the circuit confirm. Dividing by $c^2 = {c * c % P}$ and $c^3 = {c3}$ gives ${show(out)}$, and that is ${beta} \\cdot G_0$. The tracer counted ${gates_toy}$ gates, namely 3 to normalize, 4 for the doubling, 10 for the digit and 3 to move back.')

    w = Wires(P)
    assert walk(w, bits, G0, select_hoisted) == out
    assert len(w.gates) == 19

    # Real widths, counted by running the gates on Pallas and Vesta.
    plain_real = walk_gates(47)
    hoist_real = walk_gates(47, select_hoisted)
    assert plain_real == 480 and hoist_real == 433
    dbl143, dbl255 = plain_scalar_gates(143), plain_scalar_gates(255)
    frag['walk-costs'] = rows(
        ['Method', 'Bits', 'Gates', 'Gates per bit'],
        [['Double-and-add from Chapter 10', 255, f'{dbl255:,}', f'{dbl255 / 255:.2f}'],
         ['Double-and-add from Chapter 10', 143, f'{dbl143:,}', f'{dbl143 / 143:.2f}'],
         ['Radix 2 with the endomorphism, the book\'s figure', 128, 455, f'{455 / 128:.2f}'],
         ['Radix 3, plain selector', 143, plain_real, f'{plain_real / 143:.2f}'],
         ['Radix 3, hoisted selector', 143, hoist_real, f'{hoist_real / 143:.2f}']])
    frag['walk-costs-check'] = (
        f'The last two rows come from running our tracer on the point $(-1,\\,2)$ of Vesta with a 143-bit string, where it counted ${plain_real}$ and ${hoist_real}$ gates and the result matched a direct multiplication by the lifted scalar. '
        f'A circuit has $2^{{11}} = {2 ** 11:,}$ gates, so it holds ${2 ** 11 // dbl143}$ double-and-add multiplication or ${2 ** 11 // hoist_real}$ hoisted walks.')
    assert 2 ** 11 // dbl143 == 1 and 2 ** 11 // hoist_real == 4

    # Test vector from the code's consistency test, on both curves.
    tv = 206786806484900909362154774549736492353
    tv_bits = bits_of(tv, 143)
    w1, w2 = Wires(PASTA_P), Wires(PASTA_Q)
    kq, kp = lift(tv_bits, PASTA_Q), lift(tv_bits, PASTA_P)
    assert walk(w1, tv_bits, pal) == fmul(kq, pal, PASTA_P)
    assert walk(w2, tv_bits, ves) == fmul(kp, ves, PASTA_Q)
    assert kq != kp and kq != tv and kp != tv
    assert len(w1.gates) == len(w2.gates) == 480
    lift_pasta = traced_lift(Wires(PASTA_P), tv_bits)
    assert lift_pasta == 1 + 2 * 47 and 0.18 < lift_pasta / len(w1.gates) < 0.2
    lift_toy = traced_lift(Wires(Q), bits)
    frag['lift-cost'] = (
        f'Inside a circuit the lift is a Horner loop over the digits. Our traced version spends one gate on the product $s_0 e_0$ of the first two bits, and then two gates per digit, one for the product $e_1 e_2$ and one to apply the sign. For our 5-bit string that is ${lift_toy}$ gates. On Pasta, with 47 digits, it is ${lift_pasta}$ gates, just under a fifth of the ${len(w1.gates)}$ gates of one walk.')
    frag['pasta-run'] = (
        f'The code\'s [consistency test](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_primitives/src/endoscalar.rs#L1126-L1149) uses the endoscalar ${tv}$. Our Python lift sends it to a scalar beginning `{f"{kq:#066x}"[:18]}...` in $\\F_q$ and a scalar beginning `{f"{kp:#066x}"[:18]}...` in $\\F_p$. The walk on $(-1,\\,2)$ on Pallas, in gates over $\\F_p$, gives the same point as a direct multiplication by the first, and the walk on $(-1,\\,2)$ on Vesta, in gates over $\\F_q$, gives the same point as a direct multiplication by the second. Each walk took ${len(w1.gates)}$ gates.')

    # ---- Section 8: collisions and exceptions ----
    def bound(n):
        return 3 * (5 * 3 ** n - 1) ** 2

    for n_ in range(0, 5):
        width = 2 + 3 * n_
        enc = [element(bits_of(s, width)) for s in range(2 ** width)]
        sample = enc if width <= 8 else enc[:: max(1, len(enc) // 200)]
        worst = max(norm((x[0] - y[0], x[1] - y[1])) for x in sample for y in sample)
        assert worst <= bound(n_)

    toy_enc = {s: element(bits_of(s, 5)) for s in range(32)}
    worst_toy = max(norm((x[0] - y[0], x[1] - y[1])) for x in toy_enc.values() for y in toy_enc.values())
    im43 = {}
    im31 = {}
    for s in range(32):
        im43.setdefault(lift(bits_of(s, 5), Q), []).append(s)
        im31.setdefault(lift(bits_of(s, 5), P), []).append(s)
    frag['toy-bound'] = (
        f'With one digit the bound is $3 (5 \\cdot 3 - 1)^2 = {bound(1)}$, and the largest norm that actually occurs among differences of our 32 strings is ${worst_toy}$. Both exceed 31 and 43, so the argument does not apply on the toy curves.')
    # A concrete clash in each field.
    clash31 = next(v for v in im31.values() if len(v) > 1)
    a31, b31 = clash31[0], clash31[1]
    df31 = (toy_enc[a31][0] - toy_enc[b31][0], toy_enc[a31][1] - toy_enc[b31][1])
    assert norm(df31) % 31 == 0
    frag['toy-collisions'] = (
        f'The 32 strings reach ${len(im43)}$ different scalars in $\\F_{{43}}$ and ${len(im31)}$ in $\\F_{{31}}$. For one clash, the strings `{bstr(bits_of(a31, 5))}` and `{bstr(bits_of(b31, 5))}` give the elements ${e_show(toy_enc[a31])}$ and ${e_show(toy_enc[b31])}$, whose difference ${e_show(df31)}$ has norm ${norm(df31)}$, a multiple of 31. Both map to ${lift(bits_of(a31, 5), P)}$ in $\\F_{{31}}$.')

    log_bound = math.log2(bound(47))
    assert 155.1 < log_bound < 155.3 and bound(47) < 75 * 9 ** 47 < PASTA_P < PASTA_Q
    frag['real-bound'] = (
        f'With 47 digits the bound is $3 (5 \\cdot 3^{{47}} - 1)^2$, which is about $2^{{{log_bound:.1f}}}$, and the Pasta group orders are about $2^{{254}}$. A nonzero difference therefore cannot have a norm divisible by either order, and the 143-bit strings stay distinct in both fields.')

    # Exceptions in the walk.
    exc = {P: set(), Q: set()}
    runs = 0
    for f, pts in [(P, curve_points()), (Q, curve_points(Q, B_DUAL))]:
        for pt in pts:
            for s in range(32):
                runs += 1
                try:
                    walk(Wires(f), bits_of(s, 5), pt)
                except Exceptional:
                    exc[f].add(s)
    assert beta_val not in exc[P] and beta_val not in exc[Q]
    # The string with a = 2 and d = 1 - lambda hits 2a + d = 5 - lambda, of norm 31.
    bad = 0b11000
    assert bad in exc[Q] and element(bits_of(bad, 5)) == (7, -1)
    frag['exceptional'] = (
        f'We ran all 32 strings on every affine point of both curves, which makes ${runs:,}$ walks. Every walk that finished gave the point the lift predicts. On $E$, ${len(exc[P])}$ strings failed with equal $x$-coordinates in an addition, and on $E\'$, ${len(exc[Q])}$ failed. '
        f'One failure on $E\'$ is the string `{bstr(bits_of(bad, 5))}`, with $A_0 = 2 \\cdot T$ and digit $1 - \\lambda$. After the first addition the running point is $A_0 + D$, and adding $A_0$ again would give the index $2 \\cdot 2 + (1 - \\lambda) = 5 - \\lambda$, the norm-31 element from Section 4, which is the identity on $E\'$.')

    # ---- Section 9: extraction ----
    cap = 5
    assert 2 ** cap <= Q < 2 ** (cap + 1)
    reject = Q - 2 ** cap
    two_ways = [v for v in range(Q) if v + Q < 2 ** (cap + 1)]
    v_ = 5
    assert v_ in two_ways and v_ + Q == 48
    b_a, b_b = bits_of(v_, 6), bits_of(v_ + Q, 6)
    frag['extract-toy'] = (
        f'In $\\F_{{43}}$ a 6-bit string can name values up to 63, so ${len(two_ways)}$ field elements have two spellings, one of them the value plus 43. The element ${v_}$ can be written as `{bstr(b_a)}` or as `{bstr(b_b)}`, which is $48 = 5 + 43$. These spellings have different low bits, `{bstr(b_a[:5])}` and `{bstr(b_b[:5])}`, so they would name two different endoscalars. '
        f'If we require the top bit to be 0, each of the 32 elements below $2^5$ has one spelling, and the ${reject}$ elements from 32 to 42 have none and are rejected.')
    assert (PASTA_P >> 254) == 1 and (PASTA_Q >> 254) == 1
    lp = math.log2(PASTA_P - 2 ** 254) - 254
    lq = math.log2(PASTA_Q - 2 ** 254) - 254
    assert -130 < lp < -128.5 and -130 < lq < -128.5
    frag['extract-real'] = (
        f'Both Pasta primes lie just above $2^{{254}}$, so the capacity is 254 bits. The rejected values make up about $2^{{{lp:.1f}}}$ of $\\F_p$ and about $2^{{{lq:.1f}}}$ of $\\F_q$, which is the figure of about $2^{{-129}}$ in the source. Each 143-bit string is the low 143 bits of exactly $2^{{{254 - 143}}}$ in-range values, so a uniform in-range value gives a uniform string.')

    # ---- Section 10: the fold, with lifted challenges ----
    s1, s2 = Side(Q), Side(P)
    alpha, u = 11, 13
    assert alpha < 32 and u < 32 and beta_val < 32
    alpha_n, u_n = lift(bits_of(alpha, 5), P), lift(bits_of(u, 5), P)
    assert alpha_n and u_n
    frag['fold-challenges'] = (
        f'Let the transcript give $\\alpha = {alpha}$, $u = {u}$ and `pre_beta` $= {beta_val}$ in $\\F_{{43}}$, all below 32. The primary circuit uses $\\alpha$ and $u$ as they are, and it lifts `pre_beta` to $\\beta = {beta}$. The secondary circuit uses only lifts of the same bit strings, which are $\\alpha\' = {alpha_n}$, $u\' = {u_n}$ and $\\beta\' = {beta_n}$.')

    c0, c1 = s1.claim((7, 2, 5, 3), 9), s1.claim((3, 1, 8, 4), 5)
    d0_, d1_ = s2.claim((4, 9, 2, 6), 5), s2.claim((8, 3, 7, 5), 3)
    assert (c0['y'], c1['y'], d0_['y'], d1_['y']) == (37, 20, 12, 29)
    primary, secondary = Wires(Q), Wires(P)
    a1 = endo_fold(s1, [c0, c1], alpha, u, beta, bits, primary, secondary)
    a2 = endo_fold(s2, [d0_, d1_], alpha_n, u_n, beta_n, bits, secondary, primary)
    assert s1.commit(a1['poly']) == a1['P'] and ev(a1['poly'], u, Q) == a1['v']
    assert s2.commit(a2['poly']) == a2['P'] and ev(a2['poly'], u_n, P) == a2['v']
    frag['fold-commit'] = (
        f'On the first side $\\alpha$ is still ${alpha}$, so the quotient combination $f$ and its commitment $F = {show(a1["F"])}$ on $E$ are those of Chapter 13. On the second side the batching uses $\\alpha\' = {alpha_n}$, which gives a new combination $f\'$ with commitment $F\' = {show(a2["F"])}$ on $E\'$.')
    frag['fold-table'] = rows(
        ['Output', 'Computed in', 'Scalar used', 'Operation', 'Result', 'Gates'],
        [['$v$ over $\\F_{43}$', 'Primary, over $\\F_{43}$', f'$\\beta = {beta}$', 'Field arithmetic', f"${a1['v']}$", a1['value_gates']],
         ["$P'$ on $E'$", 'Primary, over $\\F_{43}$', f"Bits, acting as $\\beta' = {beta_n}$", 'Walk', f"${show(a2['P'])}$", a2['group_gates']],
         ["$v'$ over $\\F_{31}$", 'Secondary, over $\\F_{31}$', f"$\\beta' = {beta_n}$", 'Field arithmetic', f"${a2['v']}$", a2['value_gates']],
         ['$P$ on $E$', 'Secondary, over $\\F_{31}$', f'Bits, acting as $\\beta = {beta}$', 'Walk', f"${show(a1['P'])}$", a1['group_gates']]])
    assert a1['group_gates'] == 2 * (20 + 3) == 46
    frag['fold-decide'] = (
        f'The decider commits to the combined polynomials $p = {fv(a1["poly"], Q)}$ and $p\' = {fv(a2["poly"], P)}$, and gets ${show(a1["P"])}$ on $E$ and ${show(a2["P"])}$ on $E\'$. It evaluates them at $u = {u}$ and at $u\' = {u_n}$, and gets ${a1["v"]}$ in $\\F_{{43}}$ and ${a2["v"]}$ in $\\F_{{31}}$. All four numbers match the table, although neither circuit ever computed in the other\'s field.')
    frag['fold-compare'] = (
        f'Each point now takes ${a1["group_gates"]}$ gates, two walks of $20$ and two additions of $3$, where the 4-bit double-and-add of [Chapter 13](./curve-cycles.md#_6-a-fold-split-across-two-circuits) took $68$ gates for a shorter challenge. Each circuit also pays ${5}$ gates to show that the bits are bits and $3$ gates to lift them.')
    lift_w = Wires(Q)
    gates_lift = traced_lift(lift_w, bits)
    assert gates_lift == 3

    # What happens with the integer instead of the lift.
    wrong = smul(beta_val, a1['F'], P)
    right_pt = smul(beta, a1['F'], P)
    assert wrong != right_pt
    frag['integer-fail'] = (
        f'Suppose the primary circuit used the integer ${beta_val}$ as $\\beta$ in its field arithmetic. The walk on $E$ does not act as ${beta_val}$. It takes the commitment $F = {show(a1["F"])}$ to ${beta} \\cdot F = {show(right_pt)}$, while ${beta_val} \\cdot F = {show(wrong)}$. The value and the point would then describe different polynomials, and the decider would reject.')

    # ---- Section 11: the challenge stage ----
    stage = [alpha_n, u_n, beta_n]
    gens = GD[9:12]
    cs = mmsm(stage, gens, Q)
    pw = Wires(Q)
    terms = [walk(pw, bits_of(ch, 5), g) for ch, g in zip((alpha, u, beta_val), gens)]
    acc_ = pw.add_points(pw.add_points(terms[0], terms[1]), terms[2])
    assert acc_ == cs
    bind_gates = len(pw.gates)
    assert bind_gates == 3 * 20 + 2 * 3
    bad_count = sum(1 for b in range(P) if b != beta_n and mmsm([alpha_n, u_n, b], gens, Q) == cs)
    assert bad_count == 0
    frag['stage-bind'] = (
        f'The stage holds $(\\alpha\', u\', \\beta\') = {fv(stage, P)}$ with no blinding, on the generators ${show(gens[0])}, {show(gens[1])}, {show(gens[2])}$ of $E\'$ from [Chapter 13](./curve-cycles.md#_9-sharing-one-set-of-challenges), and its commitment is $C_s = {show(cs)}$. '
        f'The primary circuit holds the three transcript values as wires in its own field, breaks each into bits, and walks each generator by those bits. The walks give ${show(terms[0])}$, ${show(terms[1])}$ and ${show(terms[2])}$, which add to ${show(acc_)}$ in ${bind_gates}$ gates. '
        f'That circuit never computed ${alpha_n}$, ${u_n}$ or ${beta_n}$, because it has no wires modulo 31, and it still confirmed a commitment to exactly those values. If the prover puts any of the ${P - 1}$ other values in the place of $\\beta\'$, the stage commits to a different point and the comparison fails.')

    # The lift check on the secondary side, and why it needs injectivity.
    same31 = [s for s in range(32) if s != beta_val and lift(bits_of(s, 5), P) == beta_n]
    assert same31
    other = same31[0]
    other_bits = bits_of(other, 5)
    beta_other = lift(other_bits, Q)
    assert beta_other != beta and other not in exc[P]
    cheat_w = Wires(P)
    cheat_P = cheat_fold(s1, [c0, c1], a1['F'], other_bits, cheat_w)
    assert cheat_P != a1['P']
    frag['bits-cheat'] = (
        f'The string `{bstr(other_bits)}` also lifts to ${beta_n}$ in $\\F_{{31}}$, so a prover could load it into the secondary circuit and pass the comparison with $\\beta\'$. '
        f'In $\\F_{{43}}$ that string lifts to ${beta_other}$ and not ${beta}$, so the walk on $E$ now acts as ${beta_other}$ and produces $P = {show(cheat_P)}$ in place of ${show(a1["P"])}$. The false accumulator has a value computed with $\\beta = {beta}$ and a point computed with ${beta_other}$.')
    n_pairs_c = sum(1 for s in range(32) for t in range(s + 1, 32)
                    if lift(bits_of(s, 5), P) == lift(bits_of(t, 5), P)
                    and lift(bits_of(s, 5), Q) != lift(bits_of(t, 5), Q))
    frag['bits-cheat-count'] = (
        f'Among the 32 toy strings, ${n_pairs_c}$ pairs agree in $\\F_{{31}}$ and disagree in $\\F_{{43}}$. On Pasta no such pair exists, by the norm bound of Section 8.')

    # ---- Section 12: soundness counts ----
    # A cheater whose error in v is beta - c, for the c it aims at.
    worst_c = max(im43, key=lambda v: len(im43[v]))
    frag['root-count'] = (
        f'Take a cheater whose error in $v$ is the polynomial $\\beta - c$, as in [Chapter 13](./curve-cycles.md#_9-sharing-one-set-of-challenges). It passes when the string lifts to $c$. With an injective lift, one string out of the 32 would pass. On the toy cycle the lift is not injective, and the cheater does best with $c = {worst_c}$, which ${len(im43[worst_c])}$ strings reach, for a chance of ${len(im43[worst_c])}$ in 32. So a collision in the lift directly raises a cheater\'s chance.')

    ledger = [126, 24573, 8191, 168 + 140, 26 + 18, 24573, 137, 8329, 92 + 104]
    assert sum(ledger) == 66477
    bits_left = 143 - math.log2(sum(ledger))
    assert 126.9 < bits_left < 127.0
    frag['ledger'] = (
        f'For each of the nine challenges of one fuse step, the book [lists how many roots a false identity tested by that challenge can have](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/extensions/endoscalar.md?plain=1#L216-L233). The nine counts add up to ${sum(ledger):,}$, so the chance that some false identity passes is at most\n\n'
        f'$$\\frac{{{sum(ledger):,}}}{{2^{{143}}}} = 2^{{{math.log2(sum(ledger)):.2f} - 143}} = 2^{{-{bits_left:.2f}}}.$$\n\n'
        f'We recomputed both the sum and the exponent.')

    # A meet-in-the-middle search for a secret encoding.
    secret = 28
    sb = bits_of(secret, 5)
    assert secret not in exc[P]
    target = mul(lift(sb, Q), G0)
    assert lift(sb, Q) not in (0, 1)
    table_ = {}
    for dg in [(a, b, c_) for a in (0, 1) for b in (0, 1) for c_ in (0, 1)]:
        table_[mul(image(digit(*dg), Q), G0)] = dg
    hits = []
    for s0_ in (0, 1):
        for e0_ in (0, 1):
            head = mul(6 * image(unit(s0_, e0_), Q), G0)
            rest = add(target, neg(head, P)) if head else target
            if rest in table_:
                hits.append((s0_, e0_) + table_[rest])
    assert tuple(sb) in hits
    assert all(lift(list(h), Q) == lift(sb, Q) for h in hits)
    half = 143 / 2
    frag['mitm'] = (
        f'Suppose the secret string is `{bstr(sb)}`, and an attacker sees $Q = {lift(sb, Q)} \\cdot G_0 = {show(target)}$. The attacker tabulates the 8 possible digit points, tries the 4 possible values of the head $2 \\cdot 3 \\cdot u$, and looks up $Q$ minus each head in the table. That is 12 operations against 32 for trying every string, and the search finds the string. '
        f'The same split works at any digit, so the saving grows with the width. At 143 bits the same idea takes roughly $2^{{{half}}}$ work.')

    # ---- Section 13: the fixed point of the walks ----
    def points(rx):
        return 1 + 2 * (rx + 4) + 6

    def steps(pts, k=4):
        return max(1, -((pts - 1) // -k))

    native_fixed, nested_fixed = 18 + 4, 2 + 11
    sn, sm_ = 0, 0
    conv_rows = []
    round_ = 0
    while True:
        nested_pts = points(native_fixed + sn)
        native_pts = points(nested_fixed + sm_)
        nn, nm = steps(native_pts), steps(nested_pts)
        round_ += 1
        conv_rows.append([round_, native_pts, nn, nested_pts, nm, sn, sm_])
        if (nn, nm) == (sn, sm_):
            break
        sn, sm_ = nn, nm
    assert (sn, sm_) == (23, 26) and (native_pts, nested_pts) == (93, 105)
    frag['fold-points'] = (
        f'Its trouble is the price. In Ragu\'s code a fuse folds ${native_pts}$ points of Pallas and ${nested_pts}$ points of Vesta with one challenge, counts that Section 13 derives. A Horner fold of ${native_pts}$ points makes ${native_pts - 1}$ multiplications by the challenge, one for each point after the first, and the other fold makes ${nested_pts - 1}$. '
        'A Ragu circuit holds only $2^{11}$ gates, and the double-and-add from the [recursive proofs chapter](./recursive-proofs.md#point-operations) spends about ten gates on every bit, so one multiplication by a challenge of 143 bits would fill most of a circuit.')
    frag['code-fixed-setup'] = (
        f'The trace polynomials on the other side are a fixed set plus one per step circuit, and at commit `3219e08` the fixed sets have [${native_fixed}$ polynomials on the primary side](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/mod.rs#L135-L137) and [${nested_fixed}$ on the secondary side](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/mod.rs#L165-L168). A Horner fold makes one multiplication by the challenge for each point after the first, and a step circuit does four of these endoscalings, so a walk needs $(\\text{{points}} - 1)/4$ step circuits, rounded up.')
    frag['code-fixed'] = (
        rows(['Round', 'Primary step circuits going in', 'Secondary step circuits going in', 'Points on Pallas', 'Points on Vesta', 'Primary step circuits needed', 'Secondary step circuits needed'],
             [[r_[0], r_[5], r_[6], r_[1], r_[3], r_[2], r_[4]] for r_ in conv_rows]))
    frag['code-fixed-end'] = (
        f'In round {round_} the step circuits needed equal the step circuits going in, so the counts have stopped changing after ${round_}$ rounds. '
        f'The primary circuits fold ${native_pts}$ points of Pallas in ${sn}$ step circuits, and the secondary circuits fold ${nested_pts}$ points of Vesta in ${sm_}$. '
        f'Each step circuit does $4$ endoscalings, and ${sn} \\cdot 4 = {sn * 4} = {native_pts} - 1$ and ${sm_} \\cdot 4 = {sm_ * 4} = {nested_pts} - 1$.')
    # The iteration reproduces the code's pinned step counts, which the chapter on
    # recursion in Ragu cites. This chapter states only the series below.
    fr = Fraction(1, 3) / Fraction(1, 4)
    assert fr == Fraction(4, 3)
    assert Fraction(1, 7) / Fraction(1, 8) == Fraction(8, 7)
    frag['book-series'] = (
        f'With $k = 4$ each series sums to $1/(1 - 1/16) = 16/15$, so for $M = N$ the total is $\\tfrac{{16}}{{15}}\\big(\\tfrac{{M}}{{4}} + \\tfrac{{M}}{{16}}\\big) = \\tfrac{{M}}{{3}}$, against a first round of $M/4$. The feedback raises the count by a factor of ${float(fr):.2f}$.')
    kk = 4
    ratio = Fraction(2, kk) ** 2
    ssum = 1 / (1 - ratio)
    total = ssum * (Fraction(1, kk) + Fraction(2, kk * kk))
    limit = total / Fraction(1, kk)
    assert ratio == Fraction(1, 4) and ssum == Fraction(4, 3) and total == Fraction(1, 2) and limit == 2
    frag['code-series'] = (
        f'With $k = {kk}$ the ratio is $(2/{kk})^2 = {ratio.numerator}/{ratio.denominator}$, and each series sums to $1/(1 - {ratio.numerator}/{ratio.denominator}) = {ssum.numerator}/{ssum.denominator}$. For $M = N$ the total is '
        f'$\\tfrac{{{ssum.numerator}}}{{{ssum.denominator}}}\\big(\\tfrac{{M}}{{{kk}}} + \\tfrac{{2M}}{{{kk * kk}}}\\big) = \\tfrac{{{ssum.numerator}}}{{{ssum.denominator}}} \\cdot \\tfrac{{3M}}{{8}} = \\tfrac{{M}}{{{total.denominator}}}$, against the same first round of $M/{kk}$. '
        f'The feedback now raises the count by a factor of ${int(limit)}$, where the book\'s model gave ${float(fr):.2f}$.')

    return frag


def on_curve_pasta(a, f):
    return (a[1] * a[1] - a[0] ** 3 - 5) % f == 0


def mul_any(k, a, f):
    """k may be negative, and the point need not lie on one of the toy curves."""
    k %= ORDER[f]
    return fmul(k, a, f)


def traced_lift(w, bits):
    """The plain lift: one gate for s0 e0, then two per digit."""
    f, z = w.mod, ZETA[w.mod]
    s0, e0, digits = split_bits(bits)
    s0e0 = w.mul(s0, e0)
    acc = (2 + 2 * (z - 1) * e0 - 4 * s0 - 4 * (z - 1) * s0e0) % f
    for s, e1, e2 in digits:
        e1e2 = w.mul(e1, e2)
        v = (1 + (z - 1) * e1 + (z * z - 1) * e2 + (3 - z) * e1e2) % f
        d = w.mul((1 - 2 * s) % f, v)
        acc = (3 * acc + d) % f
    assert acc == lift(bits, f)
    return len(w.gates)


def endo_fold(side, claims, alpha, u, beta, bits, value_wires, group_wires):
    """Chapter 13's fold, with the point walked by bits instead of an integer."""
    m_ = len(claims)
    m = side.m
    assert value_wires.mod == m and group_wires.mod == side.coord
    assert lift(bits, m) == beta
    qs = []
    for c in claims:
        running, out = 0, []
        for a in reversed(c['poly']):
            running = (a + c['x'] * running) % m
            out.append(running)
        out.pop()
        qs.append(out[::-1])
    fc = lin([(pow(alpha, m_ - 1 - i, m), q) for i, q in enumerate(qs)], m)
    Fp = side.commit(fc)
    vals = [ev(c['poly'], u, m) for c in claims]
    w = value_wires
    start = len(w.gates)
    fu = 0
    for c, val in zip(claims, vals):
        d = w.inv((u - c['x']) % m)
        fu = (w.mul(fu, alpha) + w.mul((val - c['y']) % m, d)) % m
    assert fu == ev(fc, u, m)
    v = fu
    for val in vals:
        v = (w.mul(v, beta) + val) % m
    value_gates = len(w.gates) - start
    g = group_wires
    start = len(g.gates)
    acc = Fp
    for c in claims:
        acc = g.add_points(walk(g, bits, acc), c['C'])
    group_gates = len(g.gates) - start
    pc = lin([(pow(beta, m_, m), fc)] + [(pow(beta, m_ - 1 - i, m), c['poly']) for i, c in enumerate(claims)], m)
    return dict(P=acc, v=v, poly=pc, F=Fp, f=fc, vals=vals, value_gates=value_gates, group_gates=group_gates)


def cheat_fold(side, claims, F, bits, g):
    acc = F
    for c in claims:
        acc = g.add_points(walk(g, bits, acc), c['C'])
    return acc


if __name__ == '__main__':
    print(json.dumps(main()))
