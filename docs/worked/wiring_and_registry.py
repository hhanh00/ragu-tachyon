"""Worked example for wiring-and-registry.md. Prints fragments as JSON.

Every polynomial is a real coefficient list, every commitment is computed on the
toy curve, and every count comes from running the checks. The toy field F_43 has
only the two roots of unity +1 and -1 of 2-power order, so the toy registry holds
two circuits, and the section on domains uses F_97 for arithmetic alone.
"""
import json
from functools import lru_cache

import toy_curve
from toy_curve import G, H, Q, add, curve_points, show

frag = {}


@lru_cache(maxsize=None)
def mul(k, a):
    return toy_curve.mul(k % Q, a)


# The same twelve generators as the complete proof chapter.
GENS = G + [(4, 6), (5, 2), (25, 2), (30, 23), (9, 9), (14, 22), (20, 6), (28, 21)]
assert all(a in curve_points() for a in GENS) and len(set(GENS)) == 12


def msm(scalars, points):
    out = None
    for k, a in zip(scalars, points):
        out = add(out, mul(k, a))
    return out


def commit(v):
    return msm(v, GENS)


def inv(a):
    assert a % Q
    return pow(a, Q - 2, Q)


def ev(p, at):
    out = 0
    for e in reversed(p):
        out = (out * at + e) % Q
    return out


def revdot(p, q):
    return sum(p[i] * q[len(q) - 1 - i] for i in range(len(p))) % Q


def lin(*terms):
    size = max(len(p) for _, p in terms)
    return [sum(k * (p[i] if i < len(p) else 0) for k, p in terms) % Q for i in range(size)]


def vec(v):
    return '(' + ', '.join(str(e % Q) for e in v) + ')'


def table(head, rows):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '| ' + ' | '.join(['---'] * len(head)) + ' |']
                     + ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows])


def pt(a):
    return f'${show(a)}$'


def divide(p, at):
    """Synthetic division by X - at, which ignores any claimed value."""
    out, carry = [0] * (len(p) - 1), 0
    for i in range(len(p) - 1, 0, -1):
        carry = (p[i] + at * carry) % Q
        out[i - 1] = carry
    return out + [0]


def with_roots(roots, size, point=None, value=None):
    """A polynomial with these roots, scaled to take `value` at `point`."""
    out = [1]
    for rho in roots:
        out = lin((1, [0] + out), (-rho, out + [0]))
    out = out + [0] * (size - len(out))
    if point is not None:
        scale = value * inv(ev(out, point)) % Q
        out = [e * scale % Q for e in out]
    return out


# ------------------------------------------------------------- circuits
class Circuit:
    def __init__(self, n, rows):
        self.n, self.rows = n, rows

    def pos(self, kind, i):
        n = self.n
        return {'a': 2 * n + i, 'b': 2 * n - 1 - i, 'c': 4 * n - 1 - i, 'd': i}[kind]

    def terms(self):
        return [(j, self.pos(kind, i), coeff % Q) for j, row in enumerate(self.rows)
                for (kind, i), coeff in row.items()]

    def s_y(self, y):
        """The restriction s(X, y), as coefficients of X."""
        out = [0] * (4 * self.n)
        for j, at, coeff in self.terms():
            out[at] = (out[at] + pow(y, j, Q) * coeff) % Q
        return out

    def s_x(self, x):
        """The restriction s(x, Y), as coefficients of Y."""
        out = [0] * (4 * self.n)
        for j, at, coeff in self.terms():
            out[j] = (out[j] + pow(x, at, Q) * coeff) % Q
        return out

    def sxy(self, x, y):
        return sum(pow(y, j, Q) * pow(x, at, Q) * coeff for j, at, coeff in self.terms()) % Q

    def t(self, z):
        n, out = self.n, [0] * (4 * self.n)
        for i in range(n):
            out[4 * n - 1 - i] = -(pow(z, 2 * n - 1 - i, Q) + pow(z, 2 * n + i, Q)) % Q
        return out

    def trace(self, a, b, c, d=None):
        d = d or [0] * self.n
        return [e % Q for e in list(c) + list(a)[::-1] + list(b) + list(d)[::-1]]

    def right(self, r, z, sy):
        dil = [r[i] * pow(z, i, Q) % Q for i in range(4 * self.n)]
        return lin((1, dil), (1, sy), (1, self.t(z)))


# Circuit A proves x^3 + x + 5 = 35, the running example. Circuit B proves x^4 + 2 = 40.
A = Circuit(2, [
    {('a', 0): 1, ('b', 0): -1},
    {('a', 1): 1, ('c', 0): -1},
    {('a', 0): -1, ('b', 1): 1},
    {('a', 0): 1, ('c', 1): 1},
])
B = Circuit(2, [
    {('a', 0): 1, ('b', 0): -1},
    {('a', 1): 1, ('c', 0): -1},
    {('c', 0): -1, ('b', 1): 1},
    {('c', 1): 1},
])
K_A = [0, 0, 0, 30, 0, 0, 0, 0]
K_B = [0, 0, 0, 38, 0, 0, 0, 0]
assert (3 ** 3 + 3 + 5) % Q == 35 and (3 ** 4 + 2) % Q == 40


def trace_a(x):
    w = x * x % Q
    return A.trace([x, w], [x, x], [w, w * x % Q])


def trace_b(x):
    w = x * x % Q
    return B.trace([x, w], [x, w], [w, w * w % Q])


R_A, R_B, R_FALSE = trace_a(3), trace_b(3), trace_a(4)
assert R_A == [9, 27, 9, 3, 3, 3, 0, 0] and R_FALSE == [16, 21, 16, 4, 4, 4, 0, 0]
for z_ in range(Q):
    for y_ in (1, 7, 34):
        assert revdot(R_A, A.right(R_A, z_, A.s_y(y_))) == ev(K_A, y_)
        assert revdot(R_B, B.right(R_B, z_, B.s_y(y_))) == ev(K_B, y_)

# ------------------------------------------------------------- Section 1
S7 = A.s_y(7)
assert S7 == [0, 0, 6, 42, 37, 7, 42, 36] and A.sxy(9, 7) == 23 and commit(S7) == (7, 6)
assert len(A.terms()) == 8
frag['s-terms'] = (f'Our circuit has {len(A.terms())} nonzero wiring coefficients, so computing $s(9, 7) = {A.sxy(9, 7)}$ takes {len(A.terms())} terms. '
                   f'A real circuit has at least one coefficient for each wire it uses, so at $4n = 2^{{13}}$ a full circuit needs on the order of {2 ** 13:,} terms for this one value.')

Z_R, Y_R, X_R = 5, 7, 9
gap = (ev(K_A, Y_R) - revdot(R_FALSE, A.right(R_FALSE, Z_R, S7))) % Q
assert ev(K_A, Y_R) == 13 and gap == 38
delta = gap * inv(R_FALSE[3]) % Q
S_WRONG = list(S7)
S_WRONG[4] = (S_WRONG[4] + delta) % Q
B_WRONG = A.right(R_FALSE, Z_R, S_WRONG)
assert revdot(R_FALSE, B_WRONG) == 13
tie_all = [x_ for x_ in range(Q)
           if ev(B_WRONG, x_) == (ev(R_FALSE, x_ * Z_R) + ev(S_WRONG, x_) + ev(A.t(Z_R), x_)) % Q]
assert len(tie_all) == Q
assert commit(S_WRONG) != commit(S7) and commit(S_WRONG) is not None
frag['wrong-wiring'] = (f'Take the false trace with $x = 4$, $\\v{{r}}\' = {vec(R_FALSE)}$, at $z = {Z_R}$ and $y = {Y_R}$. With the true wiring the revdot product is {revdot(R_FALSE, A.right(R_FALSE, Z_R, S7))}, and the target is $k({Y_R}) = {ev(K_A, Y_R)}$. '
                        f'The prover adds ${delta}X^4$ to its wiring polynomial, which moves the revdot product by $r\'_3 \\cdot {delta} = {gap}$ and reaches the target. It commits to the altered polynomial $(0, 0, 6, 42, {S_WRONG[4]}, 7, 42, 36)$, which gives $S^* = {show(commit(S_WRONG))}$ in place of the true ${show(commit(S7))}$. '
                        f'The right factor is built from this polynomial, so the check $b(x) = a(xz) + s(x, y) + t(x, z)$ holds at all {len(tie_all)} values of $x$, and every evaluation claim is true of the committed polynomials. The only thing wrong with this proof is that $S^*$ does not commit to $s(X, {Y_R})$.')

# ------------------------------------------------------------- Section 2
rows = []
for j, row in enumerate(A.rows):
    cells = {A.pos(kind, i): coeff % Q for (kind, i), coeff in row.items()}
    rows.append([f'$Y^{j}$'] + [cells.get(i, '') for i in range(8)])
frag['matrix'] = table(['', '$X^0$', '$X^1$', '$X^2$', '$X^3$', '$X^4$', '$X^5$', '$X^6$', '$X^7$'], rows)
X9 = A.s_x(9)
assert ev(X9, 7) == ev(S7, 9) == A.sxy(9, 7)
frag['restrictions'] = (f'Fixing $Y = 7$ collapses the rows into $s(X, 7)$, with coefficients ${vec(S7)}$. Fixing $X = 9$ collapses the columns into $s(9, Y)$, with coefficients ${vec(X9)}$ on $Y^0, \\ldots, Y^7$. '
                        f'These are different polynomials, and they meet at one number, since evaluating the first at $X = 9$ and the second at $Y = 7$ both give ${A.sxy(9, 7)}$.')


# ------------------------------------------------------------- batching, as in chapter 08
def accumulate(polys, claims, alpha, u, beta):
    """Prover and verifier sides of chapter 08's reduction, with no blinding."""
    names = list(polys)
    m, ell = len(claims), len(names)
    f = [0] * max(len(p) for p in polys.values())
    for i, (name, at, _) in enumerate(claims):
        f = lin((1, f), (pow(alpha, m - 1 - i, Q), divide(polys[name], at)))
    F = commit(f)
    values = {name: ev(polys[name], u) for name in names}
    # Verifier side: it sees only commitments, claims, F and the values at u.
    fu = sum(pow(alpha, m - 1 - i, Q) * (values[name] - y) * inv(u - at)
             for i, (name, at, y) in enumerate(claims)) % Q
    P = mul(pow(beta, ell, Q), F)
    v = pow(beta, ell, Q) * fu % Q
    for j, name in enumerate(names):
        weight = pow(beta, ell - 1 - j, Q)
        P = add(P, mul(weight, commit(polys[name])))
        v = (v + weight * values[name]) % Q
    # Prover side.
    p = [pow(beta, ell, Q) * e % Q for e in f]
    for j, name in enumerate(names):
        p = lin((1, p), (pow(beta, ell - 1 - j, Q), polys[name]))
    return dict(f=f, F=F, values=values, fu=fu, P=P, v=v, p=p)


def decide(res):
    return commit(res['p']) == res['P'] and ev(res['p'], ALPHA_U) == res['v']


ALPHA, ALPHA_U, BETA = 11, 17, 23

# ------------------------------------------------------------- Section 3
Y0, Y1, XC, YNEW = 7, 34, 21, 12
s0, s1 = A.s_y(Y0), A.s_y(Y1)
assert s1 == [0, 0, 38, 42, 8, 34, 2, 9] and commit(s1) == (4, 25)
sp = A.s_x(XC)
snew = A.s_y(YNEW)
polys_single = {'S_0': s0, 'S_1': s1, "S'": sp, 'S_{\\text{new}}': snew}
v0, v1, v2 = A.sxy(XC, Y0), A.sxy(XC, Y1), A.sxy(XC, YNEW)
assert ev(s0, XC) == ev(sp, Y0) == v0 and ev(s1, XC) == ev(sp, Y1) == v1 and ev(snew, XC) == ev(sp, YNEW) == v2
assert len({v0, v1, v2}) == 3 and 0 not in (v0, v1, v2)
assert None not in [commit(p_) for p_ in polys_single.values()]
assert not {commit(p_) for p_ in polys_single.values()} & set(GENS[:8])
frag['single-run'] = table(['Step', 'Party', 'Value'], [
    [1, 'Both hold', f'$(S_0, y_0) = ({show(commit(s0))},\\ {Y0})$ and $(S_1, y_1) = ({show(commit(s1))},\\ {Y1})$'],
    [2, 'Verifier sends', f'$x = {XC}$'],
    [3, 'Prover sends', f'$S\' = {show(commit(sp))}$, the commitment to $s({XC}, Y) = {vec(sp)}$'],
    [4, 'Verifier sends', f'$y_{{\\text{{new}}}} = {YNEW}$'],
    [5, 'Prover sends', f'$S_{{\\text{{new}}}} = {show(commit(snew))}$, the commitment to $s(X, {YNEW}) = {vec(snew)}$'],
])
single_claims = [('S_0', XC, v0), ("S'", Y0, v0), ('S_1', XC, v1), ("S'", Y1, v1), ('S_{\\text{new}}', XC, v2), ("S'", YNEW, v2)]
frag['single-claims'] = table(['Claim', 'Commitment', 'Point', 'Value', 'Which value is shared'], [
    [i, f'${c}$', at, val, ['$s(21, 7)$', '$s(21, 7)$', '$s(21, 34)$', '$s(21, 34)$', '$s(21, 12)$', '$s(21, 12)$'][i]]
    for i, (c, at, val) in enumerate(single_claims)])
assert all(ev(polys_single[c], at) == val for c, at, val in single_claims)
ok_all = all(ev(A.s_y(y_), x_) == ev(A.s_x(x_), y_) for x_ in range(Q) for y_ in range(Q))
assert ok_all
BETA_S = 15
res_single = accumulate(polys_single, single_claims, ALPHA, ALPHA_U, BETA_S)
assert decide(res_single) and None not in (res_single['F'], res_single['P'])
assert res_single['P'] not in GENS[:8] and res_single['F'] not in GENS[:8]
assert res_single['P'] not in [commit(p_) for p_ in polys_single.values()]
frag['single-batch'] = (f'With $\\alpha = {ALPHA}$, $u = {ALPHA_U}$ and $\\beta = {BETA_S}$, the prover sends $F = {show(res_single["F"])}$ and the values at $u$, one for each of the four polynomials: ${", ".join(str(e) for e in res_single["values"].values())}$. '
                        f'The verifier derives $f({ALPHA_U}) = {res_single["fu"]}$, then $P = {show(res_single["P"])}$ and $v = {res_single["v"]}$. A decider holding $\\v{{p}} = {vec(res_single["p"])}$ commits to it and evaluates it, and both results match. Checking the crossing identity at all {Q * Q} pairs $(x, y)$ confirms that an honest prover passes at every challenge.')
wiring_ok = commit(A.s_y(YNEW)) == commit(snew)
assert wiring_ok
frag['single-decide'] = (f'The accumulator that leaves this fold is $(S_{{\\text{{new}}}}, y_{{\\text{{new}}}}) = ({show(commit(snew))},\\ {YNEW})$. If the chain stops here, the decider computes $s(X, {YNEW})$ from the circuit, which takes {len(A.terms())} terms, commits to it and gets ${show(commit(snew))}$. That one linear computation stands in for computing $s$ at each of the three points.')

# ------------------------------------------------------------- Section 4
D = with_roots([1, 2, 3, 4, 5, 6, 7], 8)
scale = revdot(R_FALSE, D)
D = [e * gap * inv(scale) % Q for e in D]
assert revdot(R_FALSE, lin((1, A.right(R_FALSE, Z_R, S7)), (1, D))) == 13
s0_false = lin((1, S7), (1, D))
assert commit(s0_false) != commit(S7)
pass_x = [x_ for x_ in range(Q) if ev(s0_false, x_) == ev(A.s_x(x_), Y0)]
assert pass_x == [1, 2, 3, 4, 5, 6, 7] and XC not in pass_x
frag['false-honest-bridge'] = (f'The most favourable false polynomial differs from $s(X, 7)$ by a multiple of $(X-1)(X-2)\\cdots(X-7)$, the difference that [chapter 09](./nark.md#the-prover-changes-b) found best for its cheater. Against an honest $S\'$, the pair of claims about $s(x, 7)$ can hold only where this difference vanishes. Trying all 43 values of $x$ finds {len(pass_x)} that pass, $x \\in \\{{1, \\ldots, 7\\}}$. No polynomial with 8 coefficients has more roots.')

err = ev(D, XC)
assert err
others = [34, 1, 2, 3, 4, 5, 6]
assert Y0 not in others
DY = with_roots(others, 8, Y0, err)
sp_false = lin((1, sp), (1, DY))
assert ev(sp_false, Y0) == ev(s0_false, XC) and ev(sp_false, Y1) == ev(s1, XC)
pass_y = [y_ for y_ in range(Q) if ev(sp_false, y_) == ev(A.s_y(y_), XC)]
assert sorted(pass_y) == sorted(others)
assert YNEW not in pass_y
frag['false-bridge'] = (f'At $x = {XC}$ the false $S_0$ opens to ${ev(s0_false, XC)}$, while the true $s({XC}, 7)$ is ${v0}$. The prover can absorb this error ${err}$ by committing to $s({XC}, Y) + D(Y)$ with $D(7) = {err}$ and $D(34) = 0$, so that both old pairs now hold. The polynomial $D$ can have at most 7 roots, and one of them has to be $34$. Taking the other six at $1, \\ldots, 6$, we tried all 43 values of $y_{{\\text{{new}}}}$ against an honest $S_{{\\text{{new}}}}$, and {len(pass_y)} pass.')

c_new = ev(DY, YNEW)
assert c_new
snew_false = list(snew)
snew_false[0] = (snew_false[0] + c_new) % Q
polys_false = {'S_0': s0_false, 'S_1': s1, "S'": sp_false, 'S_{\\text{new}}': snew_false}
false_claims = [('S_0', XC, ev(s0_false, XC)), ("S'", Y0, ev(s0_false, XC)), ('S_1', XC, v1), ("S'", Y1, v1),
                ('S_{\\text{new}}', XC, ev(snew_false, XC)), ("S'", YNEW, ev(snew_false, XC))]
assert all(ev(polys_false[c], at) == val for c, at, val in false_claims)
res_false = accumulate(polys_false, false_claims, ALPHA, ALPHA_U, BETA_S)
assert decide(res_false)
assert commit(snew_false) != commit(A.s_y(YNEW))
frag['false-new'] = (f'At $y_{{\\text{{new}}}} = {YNEW}$ the difference is $D({YNEW}) = {c_new}$, so the prover has one option left. It commits to $s(X, {YNEW}) + {c_new}$, which opens at $x = {XC}$ to the value that $S\'$ now requires. All six claims are true of the committed polynomials, and the batched check of the previous section accepts. The prover has moved its error into the new accumulator, whose commitment is ${show(commit(snew_false))}$. The decider computes $s(X, {YNEW})$ itself, gets ${show(commit(A.s_y(YNEW)))}$, and rejects.')

e_early = lin((1, [0, 0, 0, 0, 1, 0, 0, 0]), (-XC, [0, 0, 0, 1, 0, 0, 0, 0]))
assert ev(e_early, XC) == 0
sc = revdot(R_FALSE, e_early)
e_early = [e * gap * inv(sc) % Q for e in e_early]
s0_early = lin((1, S7), (1, e_early))
assert ev(s0_early, XC) == ev(sp, Y0) and revdot(R_FALSE, A.right(R_FALSE, Z_R, s0_early)) == 13
frag['false-early'] = (f'Suppose the prover knows $x = {XC}$ before it fixes the old accumulator. The difference $(X - {XC}) X^3$, scaled by ${e_early[4]}$, vanishes at that point and gives the revdot shift of Section 1, so the false polynomial $(0, 0, 6, {s0_early[3]}, {s0_early[4]}, 7, 42, 36)$ passes with an honest $S\'$ and an honest $S_{{\\text{{new}}}}$, and the decider accepts the accumulator that leaves the fold.')

# ------------------------------------------------------------- Section 5
sB7 = B.s_y(7)
frag['two-circuits'] = table(['Circuit', 'Statement', 'Constraints that differ from A', '$s(X, 7)$', 'Commitment'], [
    ['A', '$x^3 + x + 5 = 35$', 'None', f'${vec(S7)}$', pt(commit(S7))],
    ['B', '$x^4 + 2 = 40$', '$b_1 - c_0 = 0$ and $c_1 = 38$', f'${vec(sB7)}$', pt(commit(sB7))],
])
merge_a = [x_ for x_ in range(Q) if A.sxy(x_, Y1) == B.sxy(x_, Y1)]
assert merge_a == [0]
frag['cannot-merge'] = (f'Let the first accumulator hold circuit A at $y_0 = 7$ and the second hold circuit B at $y_1 = 34$, so that $S_1 = {show(commit(B.s_y(34)))}$. If $S\'$ commits to $s_A({XC}, Y)$, the first pair of claims holds, and the second compares $s_B({XC}, 34) = {B.sxy(XC, 34)}$ with $s_A({XC}, 34) = {A.sxy(XC, 34)}$. Over all 43 values of $x$ these agree only at $x = {merge_a[0]}$, so an honest prover with two different circuits fails almost everywhere.')


# The registry: circuit 0 sits at +1 and circuit 1 at -1.
OMEGA = [1, Q - 1]
HALF = inv(2)


def ell(i, w):
    return (1 + w) * HALF % Q if i == 0 else (1 - w) * HALF % Q


CIRCUITS = [A, B]


def m(w, x, y):
    return sum(ell(i, w) * c.sxy(x, y) for i, c in enumerate(CIRCUITS)) % Q


def m_xy(x, y):
    """m(W, x, y), as coefficients of W."""
    a, b = A.sxy(x, y), B.sxy(x, y)
    return [(a + b) * HALF % Q, (a - b) * HALF % Q] + [0] * 6


def m_wy(w, y):
    """m(w, X, y), as coefficients of X."""
    return lin((ell(0, w), A.s_y(y)), (ell(1, w), B.s_y(y)))


def m_wx(w, x):
    """m(w, x, Y), as coefficients of Y."""
    return lin((ell(0, w), A.s_x(x)), (ell(1, w), B.s_x(x)))


W_R = 14
assert all((ell(0, w_) + ell(1, w_)) % Q == 1 for w_ in range(Q))
assert all(ell(0, 1) == 1 and ell(1, 1) == 0 and ell(0, Q - 1) == 0 and ell(1, Q - 1) == 1 for _ in [0])
assert all(m(1, x_, y_) == A.sxy(x_, y_) and m(Q - 1, x_, y_) == B.sxy(x_, y_) for x_ in range(Q) for y_ in range(Q))
mix7 = m_wy(W_R, 7)
assert mix7 not in (S7, sB7)
frag['lagrange'] = table(['$W$', '$\\ell_0(W)$', '$\\ell_1(W)$', '$m(W, X, 7)$'], [
    ['$\\omega^0 = 1$', ell(0, 1), ell(1, 1), f'${vec(m_wy(1, 7))}$, which is $s_A(X, 7)$'],
    ['$\\omega^1 = 42$', ell(0, 42), ell(1, 42), f'${vec(m_wy(42, 7))}$, which is $s_B(X, 7)$'],
    [f'${W_R}$', ell(0, W_R), ell(1, W_R), f'${vec(mix7)}$, which is neither'],
])
frag['registry-check'] = f'The script compares $m(1, x, y)$ with $s_A(x, y)$ and $m(42, x, y)$ with $s_B(x, y)$ at all {Q * Q} pairs, and they agree at every pair. Since $\\ell_0 + \\ell_1 = 1$ at every $W$, the two weights at $W = {W_R}$ also add up to 1, and we return to this fact in Section 10.'

# ------------------------------------------------------------- Section 6
X0, X1, W, Y, X = 9, 37, W_R, YNEW, XC
s_acc0, s_acc1 = m_xy(X0, Y0), m_xy(X1, Y1)
s_w0, s_w1 = m_wx(W, X0), m_wx(W, X1)
s_wy = m_wy(W, Y)
s_new = m_xy(X, Y)
names = ['S_0', 'S_1', "S'_0", "S'_1", "S''", 'S_{\\text{new}}']
polys_reg = dict(zip(names, [s_acc0, s_acc1, s_w0, s_w1, s_wy, s_new]))
assert None not in [commit(p_) for p_ in polys_reg.values()]
assert not {commit(p_) for p_ in polys_reg.values()} & set(GENS[:8])
assert len({commit(p_) for p_ in polys_reg.values()}) == 6
frag['reg-run'] = table(['Step', 'Party', 'Value'], [
    [1, 'Both hold', f'$(S_0, x_0, y_0) = ({show(commit(s_acc0))},\\ {X0},\\ {Y0})$ and $(S_1, x_1, y_1) = ({show(commit(s_acc1))},\\ {X1},\\ {Y1})$'],
    [2, 'Verifier sends', f'$w = {W}$'],
    [3, 'Prover sends', f"$S'_0 = {show(commit(s_w0))}$ for $m({W}, {X0}, Y) = {vec(s_w0)}$"],
    ['', 'Prover sends', f"$S'_1 = {show(commit(s_w1))}$ for $m({W}, {X1}, Y) = {vec(s_w1)}$"],
    [4, 'Verifier sends', f'$y = {Y}$'],
    [5, 'Prover sends', f"$S'' = {show(commit(s_wy))}$ for $m({W}, X, {Y}) = {vec(s_wy)}$"],
    [6, 'Verifier sends', f'$x = {X}$'],
    [7, 'Prover sends', f'$S_{{\\text{{new}}}} = {show(commit(s_new))}$ for $m(W, {X}, {Y}) = {vec(s_new)}$'],
])
vs = [m(W, X0, Y0), m(W, X1, Y1), m(W, X0, Y), m(W, X1, Y), m(W, X, Y)]
assert len(set(vs)) == 5 and 0 not in vs
reg_claims = [('S_0', W, vs[0]), ("S'_0", Y0, vs[0]), ('S_1', W, vs[1]), ("S'_1", Y1, vs[1]),
              ("S'_0", Y, vs[2]), ("S''", X0, vs[2]), ("S'_1", Y, vs[3]), ("S''", X1, vs[3]),
              ("S''", X, vs[4]), ('S_{\\text{new}}', W, vs[4])]
assert all(ev(polys_reg[c], at) == val for c, at, val in reg_claims)
crossing = [f'$m({W}, {X0}, {Y0})$', f'$m({W}, {X1}, {Y1})$', f'$m({W}, {X0}, {Y})$', f'$m({W}, {X1}, {Y})$', f'$m({W}, {X}, {Y})$']
frag['reg-claims'] = table(['Shared value', 'Number', 'First claim', 'Second claim'], [
    [crossing[i], vs[i], f'${reg_claims[2 * i][0]}$ at {reg_claims[2 * i][1]}', f'${reg_claims[2 * i + 1][0]}$ at {reg_claims[2 * i + 1][1]}'] for i in range(5)])

# All challenges: the honest walk holds at every (w, x, y).
acc0, acc1 = s_acc0, s_acc1
count = 0
for w_ in range(Q):
    p0, p1 = m_wx(w_, X0), m_wx(w_, X1)
    for y_ in range(Q):
        pp = m_wy(w_, y_)
        for x_ in range(Q):
            assert ev(acc0, w_) == ev(p0, Y0) and ev(acc1, w_) == ev(p1, Y1)
            assert ev(p0, y_) == ev(pp, X0) and ev(p1, y_) == ev(pp, X1)
            count += 1
    for x_ in (X, 1, 2):
        for y_ in (Y, 1, 2):
            assert ev(m_wy(w_, y_), x_) == ev(m_xy(x_, y_), w_)
assert count == Q ** 3
frag['reg-honest'] = f'The script repeats these comparisons at all {count:,} triples $(w, x, y)$, and an honest prover passes every one.'

# ------------------------------------------------------------- Section 7
Z = 16
sel = []
for name, c, r, k, i in (('Left, circuit A', A, R_A, K_A, 0), ('Right, circuit B', B, R_B, K_B, 1)):
    val = ev(s_new, OMEGA[i])
    assert val == c.sxy(X, Y)
    rx = ev(r, X * Z)
    tx = ev(c.t(Z), X)
    bx = ev(c.right(r, Z, c.s_y(Y)), X)
    assert bx == (rx + val + tx) % Q
    assert revdot(r, c.right(r, Z, c.s_y(Y))) == ev(k, Y)
    sel.append([name, f'${OMEGA[i]}$', val, rx, tx, bx])
xz = X * Z % Q
frag['select'] = (f'The new accumulator is $m(W, {X}, {Y}) = {s_new[0]} + {s_new[1]}W$. Take $z = {Z}$, so that $xz = {xz}$. For each child the circuit reads the wiring value by opening $S_{{\\text{{new}}}}$ at the child\'s domain point, and it adds the trace value and the gate value:\n\n'
                  + table(['Child', '$\\omega^i$', '$s_i(x, y) = m(\\omega^i, x, y)$', f'$r({xz})$', f't({X}, {Z})'.replace('t(', '$t(').replace(')', ')$'), 'Sum, $b(x)$'], sel)
                  + f'\n\nThe script also confirms that each child\'s revdot product at $z = {Z}$ and $y = {Y}$ equals its own $k(y)$, with different wiring and different public inputs on the two sides.')
all_claims = reg_claims + [('S_{\\text{new}}', 1, ev(s_new, 1)), ('S_{\\text{new}}', 42, ev(s_new, 42))]
assert all(ev(polys_reg[c], at) == val for c, at, val in all_claims)
res_reg = accumulate(polys_reg, all_claims, ALPHA, ALPHA_U, BETA)
assert decide(res_reg)
assert ALPHA_U not in [at for _, at, _ in all_claims]
assert res_reg['P'] not in GENS[:8] and res_reg['F'] not in GENS[:8]
frag['reg-batch'] = (f'With $\\alpha = {ALPHA}$, $u = {ALPHA_U}$ and $\\beta = {BETA}$, the prover sends $F = {show(res_reg["F"])}$ and six values at $u$: ${", ".join(str(e) for e in res_reg["values"].values())}$. The verifier derives $f({ALPHA_U}) = {res_reg["fu"]}$, then $P = {show(res_reg["P"])}$ and $v = {res_reg["v"]}$, and a decider holding $\\v{{p}} = {vec(res_reg["p"])}$ accepts. '
                     f'The wiring decider then evaluates the accumulator at a fresh point. At $W = 30$ the polynomial gives ${ev(s_new, 30)}$, and the two circuits give $\\ell_0(30) s_A({X}, {Y}) + \\ell_1(30) s_B({X}, {Y}) = {m(30, X, Y)}$.')
assert ev(s_new, 30) == m(30, X, Y)

# ------------------------------------------------------------- Section 8
GATES = 2 ** 11
NUM_C = 256
frag['costs'] = table(['Approach', 'What one step puts in its circuit', 'Size for this example'], [
    ['Compute $s_i(x, y)$ directly', 'One term per wiring coefficient of each child\'s circuit', f'At least {2 * 2 ** 13:,} multiplications for two full circuits'],
    ['One merged circuit with selectors', 'The gates of every circuit, on every step', f'{NUM_C * GATES:,} gates'],
    ['Registry, as in this chapter', 'Field arithmetic on claims, 6 commitments in the fold, and a domain check on 2 indices', f'{len(all_claims)} claims and {2 * 8} squarings'],
])

# ------------------------------------------------------------- Section 9
F97, S97 = 97, 5
assert all(pow(5, 96 // q, F97) != 1 for q in (2, 3))
W5 = pow(5, 3, F97)
assert pow(W5, 32, F97) == 1 and pow(W5, 16, F97) == 96


def rev(j, bits):
    return int(format(j, f'0{bits}b')[::-1], 2) if bits else 0


def order(e):
    k = 1
    while pow(e, k, F97) != 1:
        k *= 2
    return k


def omega(k):
    return pow(W5, 2 ** (S97 - k), F97)


rows = []
for j in range(8):
    i = rev(j, S97)
    e = pow(W5, i, F97)
    rows.append([j, format(j, '05b'), format(i, '05b'), i, e, order(e)])
    for k in range(S97 + 1):
        if j < 2 ** k:
            assert pow(omega(k), rev(j, k), F97) == e
            assert i // 2 ** (S97 - k) == rev(j, k)
assert [r[5] for r in rows] == [1, 2, 4, 4, 8, 8, 8, 8]
assert all(pow(r[4], 4, F97) == 1 for r in rows[:4])
frag['bitrev'] = table(['Circuit $j$', '$j$ in 5 bits', 'Reversed', 'Exponent $i$', '$\\omega_5^i$', 'Order'], rows)
frag['bitrev-toy'] = f'On $\\F_{{43}}$ the largest available 2-power order is 2, so $S = 1$. Circuit 0 gets $\\omega_1^0 = 1$, and circuit 1 gets $\\omega_1^1 = 42$, which are the two points our registry has used all along.'
w2, w3 = omega(2), omega(3)
frag['naive'] = table(['Circuit $j$', 'Naive, 4 points: $\\omega_2^j$', 'Naive, 8 points: $\\omega_3^j$', 'Bit-reversed, any size'], [
    [j, pow(w2, j, F97), pow(w3, j, F97), pow(W5, rev(j, S97), F97)] for j in range(4)])
assert pow(w2, 1, F97) != pow(w3, 1, F97)

# ------------------------------------------------------------- Section 10: constant-wire circuits
A1 = Circuit(3, [
    {('d', 0): 1},
    {('c', 2): 1, ('a', 1): 1, ('d', 0): 5},
    {('a', 1): 1, ('b', 1): -1},
    {('a', 2): 1, ('c', 1): -1},
    {('a', 1): -1, ('b', 2): 1},
])
B1 = Circuit(3, [
    {('d', 0): 1},
    {('c', 2): 1, ('d', 0): 2},
    {('a', 1): 1, ('b', 1): -1},
    {('a', 2): 1, ('c', 1): -1},
    {('c', 1): -1, ('b', 2): 1},
])
ALPHA_WIRE = 11
K1 = [1, 35] + [0] * 10
K1B = [1, 40] + [0] * 10
assert A1.s_y(0) == [1] + [0] * 11 and B1.s_y(0) == [1] + [0] * 11


def trace_a1(x, b2=None):
    w = x * x % Q
    b2 = x if b2 is None else b2
    return A1.trace([ALPHA_WIRE, x, w], [0, x, b2], [0, w, w * b2 % Q], [1, 0, 0])


def trace_b1(x):
    w = x * x % Q
    return B1.trace([ALPHA_WIRE, x, w], [0, x, w], [0, w, w * w % Q], [1, 0, 0])


R_A1, R_B1 = trace_a1(3), trace_b1(3)
for z_ in range(Q):
    for y_ in range(Q):
        assert revdot(R_A1, A1.right(R_A1, z_, A1.s_y(y_))) == ev(K1, y_)
        assert revdot(R_B1, B1.right(R_B1, z_, B1.s_y(y_))) == ev(K1B, y_)

bonding = Circuit(3, [{}] + A1.rows[1:])
assert bonding.s_y(0) == [0] * 12
kinds = [('$s_A$, a circuit', A1.s_y(0)[0]), ('$s_B$, a circuit', B1.s_y(0)[0]), ('A bonding polynomial', bonding.s_y(0)[0]), ('Nothing registered, so the zero polynomial', 0)]
frag['kinds'] = table(['Circuit index $j$', 'Domain point in $\\F_{97}$', 'What sits there', '$s(X, 0)$'], [
    [j, pow(W5, rev(j, S97), F97), kinds[j][0], kinds[j][1]] for j in range(4)])


def gate_error(a, b, c, d, z):
    n = len(a)
    return (sum((a[i] * b[i] - c[i]) * (pow(z, 2 * n - 1 - i, Q) + pow(z, 2 * n + i, Q)) for i in range(n))
            + sum(c[i] * d[i] * (pow(z, i, Q) + pow(z, 4 * n - 1 - i, Q)) for i in range(n))) % Q


# Against the zero polynomial, only the gate terms remain.
a_, b_, c_, d_ = [1, 3, 9], [1, 3, 3], [1, 9, 27], [1, 0, 0]
r_zero = A1.trace(a_, b_, c_, d_)
Zero = Circuit(3, [])
for z_ in range(Q):
    assert revdot(r_zero, Zero.right(r_zero, z_, [0] * 12)) == gate_error(a_, b_, c_, d_, z_)
    assert gate_error(a_, b_, c_, d_, z_) == (1 + pow(z_, 11, Q)) % Q
K_ONLY = [1] + [0] * 11
zero_pass = [(z_, y_) for z_ in range(Q) for y_ in range(Q) if revdot(r_zero, Zero.right(r_zero, z_, [0] * 12)) == ev(K_ONLY, y_)]
assert {z_ for z_, _ in zero_pass} == {0} and len(zero_pass) == Q
honest_zero = [(z_, y_) for z_ in range(Q) for y_ in range(Q) if revdot(R_A1, A1.right(R_A1, z_, [0] * 12)) == ev(K1, y_)]
assert len(honest_zero) == Q
frag['zero-count'] = (f'Take the trace with $x = 3$ and the instance $k(Y) = 1 + 35Y$, and let the prover select the zero polynomial. Its gates hold, so the left side is 0, and the equation becomes $0 = 1 + 35y$, which holds for one value of $y$. Over all {Q * Q} pairs it passes at {len(honest_zero)}. '
                      f'A prover can try to manufacture the missing 1 from the $c_0 d_0$ terms by setting $c_0 = d_0 = 1$, with an instance that has no public outputs. Then the left side is $1 + z^{{11}}$, because the term at $z^0$ always comes with a partner at $z^{{4n-1}}$. It equals 1 only at $z = 0$, which is {len(zero_pass)} of the {Q * Q} pairs.')

# The mixed circuit: an out-of-domain w with a witness for neither circuit.
found = []
for w_ in range(Q):
    if w_ in (0, 1, Q - 1):
        continue
    la, lb = ell(0, w_), ell(1, w_)
    for x_ in range(1, Q):
        v_ = x_ * x_ % Q
        b2 = (la * x_ + lb * v_) % Q
        trial = trace_a1(x_, b2)
        target = (v_ * b2 + la * (x_ + 5) + lb * 2) % Q
        if target == 35:
            found.append((w_, x_, b2, trial))
found = [f_ for f_ in found if (f_[1] ** 3 + f_[1] + 5) % Q != 35 and f_[1] != 0 and f_[2] not in (0,) and f_[0] != f_[1]]
assert found
w_mix, x_mix, b2_mix, r_mix = found[0]


def mix_s(w, y):
    return lin((ell(0, w), A1.s_y(y)), (ell(1, w), B1.s_y(y)))


mix_ok = sum(revdot(r_mix, A1.right(r_mix, z_, mix_s(w_mix, y_))) == ev(K1, y_) for z_ in range(Q) for y_ in range(Q))
assert mix_ok == Q * Q
assert mix_s(w_mix, 0) == [1] + [0] * 11
a_pass = sum(revdot(r_mix, A1.right(r_mix, z_, A1.s_y(y_))) == ev(K1, y_) for z_ in range(Q) for y_ in range(Q))
b_pass = sum(revdot(r_mix, B1.right(r_mix, z_, B1.s_y(y_))) == ev(K1, y_) for z_ in range(Q) for y_ in range(Q))
assert a_pass <= 4 * Q and b_pass <= 4 * Q
assert pow(w_mix, 2, Q) != 1
frag['mix-attack'] = (f'Take the instance $k(Y) = 1 + 35Y$, whose second coefficient is the public output, and let the prover select the out-of-domain point $w = {w_mix}$. There the weights are ${ell(0, w_mix)}$ and ${ell(1, w_mix)}$, and they add up to 1, so $m({w_mix}, X, 0) = 1$ and the mixture looks like a circuit. '
                      f'The input $x = {x_mix}$ does not satisfy $x^3 + x + 5 = 35$, yet the trace with $b_2 = {b2_mix}$, which is ${vec(r_mix)}$, satisfies the consolidated equation at all {mix_ok} pairs $(z, y)$. The same trace passes against circuit A at {a_pass} pairs and against circuit B at {b_pass}. '
                      f'The domain check catches the selection, because ${w_mix}^2 = {pow(w_mix, 2, Q)}$, which is not 1.')

# Substitution among registered circuits: x^4 + 2 = 35 has no solution in F_43, while A's statement does.
assert not [x_ for x_ in range(Q) if (pow(x_, 4, Q) + 2) % Q == 35]
sub_ok = sum(revdot(R_A1, A1.right(R_A1, z_, A1.s_y(y_))) == ev(K1, y_) for z_ in range(Q) for y_ in range(Q))
assert sub_ok == Q * Q


def with_suffix(c, suffix):
    return Circuit(3, [c.rows[0], {('d', 0): suffix}] + c.rows[1:])


A2, B2 = with_suffix(A1, 2), with_suffix(B1, 3)
K2 = [1, 3, 35] + [0] * 9
K2_TRUE = [1, 3, 40] + [0] * 9
sub_passes = [(z_, y_) for z_ in range(Q) for y_ in range(Q) if revdot(R_A1, A2.right(R_A1, z_, A2.s_y(y_))) == ev(K2, y_)]
assert all(revdot(R_B1, B2.right(R_B1, z_, B2.s_y(y_))) == ev(K2_TRUE, y_) for z_ in range(Q) for y_ in range(Q))
assert {y_ for _, y_ in sub_passes} == {0} and len(sub_passes) == Q
frag['substitution'] = (f'Suppose the verifier wants a proof that some $x$ satisfies $x^4 + 2 = 35$. Trying all 43 values shows that no such $x$ exists, so this statement is false. The verifier computes $k(Y) = 1 + 35Y$, and the prover selects circuit A in place of circuit B, with $x = 3$. Every check passes at all {sub_ok} pairs, because the instance is the same as that of the true statement $3^3 + 3 + 5 = 35$. '
                        f'Now add a row to each circuit that sets the linear coefficient of $k(Y)$ to a value fixed for that circuit, 2 for A and 3 for B, and let the verifier compute $k(Y) = 1 + 3Y + 35Y^2$. Circuit B with a true output, such as $x = 3$ and the output 40, still passes everywhere. The same substitution with circuit A now passes at {len(sub_passes)} of the {Q * Q} pairs, all of them at $y = 0$.')

# ------------------------------------------------------------- Section 11
ZA, YA = 5, 7
err_row3 = (R_FALSE[1] + R_FALSE[3] - 30) % Q  # c_1 + a_0 - 30
assert err_row3 == 38
c_adapt = -err_row3 * pow(YA, 3, Q) * inv(R_FALSE[3]) % Q
A_ADAPT = Circuit(2, [{('a', 0): 1 + c_adapt, ('b', 0): -1}] + A.rows[1:])
assert revdot(R_FALSE, A_ADAPT.right(R_FALSE, ZA, A_ADAPT.s_y(YA))) == ev(K_A, YA)
adapt_pairs = sum(revdot(R_FALSE, A_ADAPT.right(R_FALSE, z_, A_ADAPT.s_y(y_))) == ev(K_A, y_) for z_ in range(Q) for y_ in range(Q))
adapt_y = sorted({y_ for z_ in range(Q) for y_ in range(Q) if revdot(R_FALSE, A_ADAPT.right(R_FALSE, z_, A_ADAPT.s_y(y_))) == ev(K_A, y_)})
assert YA in adapt_y and adapt_pairs <= 3 * Q
frag['adaptive'] = (f'Fix the false trace ${vec(R_FALSE)}$ and suppose the transcript has produced $z = {ZA}$ and $y = {YA}$ from data that does not depend on the circuit. At these values the trace misses its target, because constraint 3 is off by ${err_row3}$. An author who has seen $y$ can now publish a slightly different circuit, whose constraint 0 reads $(1 + {c_adapt})a_0 - b_0 = 0$. '
                    f'This constraint fails on the trace by ${c_adapt} \\cdot {R_FALSE[3]} = {c_adapt * R_FALSE[3] % Q}$, and with its weight $y^0$ that exactly cancels the error of constraint 3 with its weight $y^3 = {pow(YA, 3, Q)}$. Two constraints are broken, and the equation holds at $y = {YA}$. Counting over all {Q * Q} pairs, it holds at {adapt_pairs}, namely those with $y \\in \\{{{", ".join(str(e) for e in adapt_y)}\\}}$, so the verifier was misled only because the circuit came after the challenge.')

KAPPA = 19


def tagged_s_y(c, y, kappa=KAPPA):
    out = c.s_y(y)
    top = 4 * c.n - 1
    out[top] = (out[top] + kappa * pow(y, top, Q)) % Q
    return out


def tagged_s_x(c, x, kappa=KAPPA):
    out = c.s_x(x)
    top = 4 * c.n - 1
    out[top] = (out[top] + kappa * pow(x, top, Q)) % Q
    return out


assert all(ev(tagged_s_y(A1, y_), x_) == ev(tagged_s_x(A1, x_), y_) for x_ in range(Q) for y_ in range(Q))
assert all(revdot(R_A1, A1.right(R_A1, z_, tagged_s_y(A1, y_))) == ev(K1, y_) for z_ in range(Q) for y_ in range(Q))
two_gate_tag = sum(revdot(R_A, A.right(R_A, z_, tagged_s_y(A, y_))) == ev(K_A, y_) for z_ in range(Q) for y_ in range(Q))
assert two_gate_tag == Q
assert R_A[0] == 9 and R_A1[0] == 0
points = {commit(tagged_s_x(A1, XC, k_)) for k_ in range(Q)}
assert len(points) == Q
frag['tag-run'] = (f'Take $\\kappa = {KAPPA}$. On the trace of [chapter 09\'s constant-wire circuit](./nark.md#_14-the-constant-wire), $\\v{{r}} = {vec(R_A1)}$, the wire $c_0$ is 0, and the tagged wiring polynomial $s(X, Y) + {KAPPA}(XY)^{{11}}$ still satisfies the consolidated equation at all {Q * Q} pairs. The tag cannot be added to our earlier two-gate circuit, whose $c_0 = {R_A[0]}$. There the term contributes ${R_A[0]} \\cdot {KAPPA} \\cdot y^7$, and the honest trace passes at only {two_gate_tag} pairs, those with $y = 0$. '
                   f'The tag reaches every commitment a fold makes to a restriction. For $x = {XC}$ the commitment to $s_{{\\kappa}}({XC}, Y)$ is ${show(commit(tagged_s_x(A1, XC, KAPPA)))}$, and going through all 43 values of $\\kappa$ gives {len(points)} different points. So a transcript that absorbs this commitment gives challenges that the author of the circuit could not predict before $\\kappa$ was drawn.')

# ------------------------------------------------------------- Section 12
link_rows = []
# S_0 false in W: the check is at w.
e_w = with_roots([1, 2, 3, 4, 6, 8, 10], 8)
acc0_false = lin((1, s_acc0), (1, e_w))
pass_w = [w_ for w_ in range(Q) if ev(acc0_false, w_) == m(w_, X0, Y0)]
assert sorted(pass_w) == [1, 2, 3, 4, 6, 8, 10] and W not in pass_w
link_rows.append(['$S_0$', '$W$', '$w$', len(pass_w)])
# S'_0 false in Y: the check is at y, keeping its agreement at y_0.
e_y = with_roots([1, 2, 3, 4, 5, 6, 8], 8)
assert ev(e_y, Y0) != 0
sw_false = lin((1, s_w0), (1, e_y))
pass_y2 = [y_ for y_ in range(Q) if ev(sw_false, y_) == m(W, X0, y_)]
assert sorted(pass_y2) == [1, 2, 3, 4, 5, 6, 8] and Y not in pass_y2
link_rows.append(["$S'_0$", '$Y$', '$y$', len(pass_y2)])
# S'' false in X: the check is at x.
e_x = with_roots([1, 2, 3, 4, 5, 6, 7], 8)
swy_false = lin((1, s_wy), (1, e_x))
pass_x2 = [x_ for x_ in range(Q) if ev(swy_false, x_) == m(W, x_, Y)]
assert sorted(pass_x2) == [1, 2, 3, 4, 5, 6, 7] and X not in pass_x2
link_rows.append(["$S''$", '$X$', '$x$', len(pass_x2)])
# S_new false in W: the check is at the next w, or the decider's.
e_n = with_roots([1, 2, 3, 4, 6, 7, 8], 8)
new_false = lin((1, s_new), (1, e_n))
pass_d = [w_ for w_ in range(Q) if ev(new_false, w_) == m(w_, X, Y)]
assert sorted(pass_d) == [1, 2, 3, 4, 6, 7, 8]
link_rows.append(['$S_{\\text{new}}$', '$W$', 'The next $w$, or the decider\'s', len(pass_d)])
frag['links'] = table(['False commitment', 'Variable left free', 'Challenge that tests it', 'Passing values out of 43, with the best difference'], link_rows)

GAP7 = (4 * 2 ** 11 - 1) * 6
frag['links-real'] = f'At $4n = 2^{{13}}$ on a field of about $2^{{254}}$ elements, each link passes with probability at most $(4n - 1)/2^{{254}}$. Adding this over the six commitments of one fold gives ${GAP7:,}/2^{{254}}$, which is below $2^{{-238}}$.'
assert GAP7 < 2 ** 16

# The chapter's first attack, replayed against the registry.
gap_y = (ev(K_A, Y) - revdot(R_FALSE, A.right(R_FALSE, Z, A.s_y(Y)))) % Q
assert gap_y
known = {commit(p_) for p_ in polys_reg.values()} | set(GENS[:8])
new_cheat = None
for at in (5, 3, 2, 6, 7):
    d_y = gap_y * inv(R_FALSE[7 - at]) % Q
    s_cheat = list(A.s_y(Y))
    s_cheat[at] = (s_cheat[at] + d_y) % Q
    assert revdot(R_FALSE, A.right(R_FALSE, Z, s_cheat)) == ev(K_A, Y)
    want = ev(s_cheat, X)
    true_val = A.sxy(X, Y)
    shift = (want - true_val) % Q
    if not shift:
        continue
    c_w = shift * inv((1 - W) * 2) % Q
    bump = with_roots([W, Q - 1], 8)
    trial = lin((1, s_new), (c_w, bump))
    if commit(trial) not in known and commit(trial) is not None:
        new_cheat = trial
        break
assert new_cheat
assert ev(new_cheat, 1) == want and ev(new_cheat, W) == ev(s_new, W) and ev(new_cheat, 42) == ev(s_new, 42)
pass_fresh = sorted(w_ for w_ in range(Q) if ev(new_cheat, w_) == m(w_, X, Y))
assert pass_fresh == [W, 42]
polys_ch = dict(polys_reg)
polys_ch['S_{\\text{new}}'] = new_cheat
ch_claims = reg_claims + [('S_{\\text{new}}', 1, want), ('S_{\\text{new}}', 42, ev(new_cheat, 42))]
assert all(ev(polys_ch[c], at) == val for c, at, val in ch_claims)
res_ch = accumulate(polys_ch, ch_claims, ALPHA, ALPHA_U, BETA)
assert decide(res_ch)
frag['replay'] = (f'Replay Section 1 at $y = {Y}$ and $z = {Z}$. The false trace needs a wiring value of ${want}$ at $x = {X}$, while the true $s_A({X}, {Y})$ is ${true_val}$. That value comes from $S_{{\\text{{new}}}}$ at $W = 1$, so the prover has to change this polynomial, and it can do so without disturbing the claim at $w = {W}$ or the right child\'s value by adding ${c_w}(W - {W})(W + 1)$. All twelve claims are true of the committed polynomials, and the batched check accepts. '
                  f'The false accumulator commits to ${show(commit(new_cheat))}$ in place of ${show(commit(s_new))}$. The next check tests it at a fresh point. Over all 43 values, the only ones that pass are $W = {pass_fresh[0]}$ and $W = {pass_fresh[1]}$, the two points the prover built into its difference.')

print(json.dumps(frag))
