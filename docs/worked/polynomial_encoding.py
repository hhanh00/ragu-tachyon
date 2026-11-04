"""Worked example for polynomial-encoding.md. Prints fragments as JSON."""
import itertools
import json
from toy_curve import Q

PUBLIC = 35
frag = {}


# Polynomials are coefficient lists over F_43, lowest degree first.
def trim(p):
    p = [e % Q for e in p]
    while p and p[-1] == 0:
        p.pop()
    return p


def padd(p, q):
    size = max(len(p), len(q))
    return trim([(p[i] if i < len(p) else 0) + (q[i] if i < len(q) else 0) for i in range(size)])


def pscale(k, p):
    return trim([k * e for e in p])


def psub(p, q):
    return padd(p, pscale(-1, q))


def pmul(p, q):
    out = [0] * (len(p) + len(q) - 1) if p and q else []
    for i, e in enumerate(p):
        for j, f in enumerate(q):
            out[i + j] += e * f
    return trim(out)


def peval(p, at):
    return sum(e * pow(at, i, Q) for i, e in enumerate(p)) % Q


def inv(a):
    assert a % Q != 0
    return pow(a, Q - 2, Q)


def pdivmod(p, d):
    p, quotient = trim(p), [0] * max(len(p) - len(d) + 1, 0)
    lead = inv(d[-1])
    while len(p) >= len(d):
        coeff, shift = p[-1] * lead % Q, len(p) - len(d)
        quotient[shift] = coeff
        p = psub(p, [0] * shift + pscale(coeff, d))
    return trim(quotient), p


def term(c, i):
    if i == 0:
        return str(c)
    power = 'X' if i == 1 else f'X^{{{i}}}' if i > 9 else f'X^{i}'
    return power if c == 1 else f'{c}{power}'


def show(p):
    """Render a polynomial, skipping zero coefficients."""
    terms = [term(e % Q, i) for i, e in enumerate(p) if e % Q]
    return ' + '.join(terms) if terms else '0'


def vec(v):
    return '(' + ', '.join(str(e % Q) for e in v) + ')'


def dot(p, q):
    return sum(e * f for e, f in zip(p, q)) % Q


def table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '| ' + ' | '.join(['---'] * len(head)) + ' |']
    return '\n'.join(out + ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows])


def matrix(m):
    return '\\begin{bmatrix}' + ' \\\\ '.join(' & '.join(map(str, row)) for row in m) + '\\end{bmatrix}'


# ---------------------------------------------------------------- R1CS, as in chapter 04
A = [[0, 0, 1, 0, 0], [0, 0, 0, 1, 0], [5, 0, 1, 0, 1]]
B = [[0, 0, 1, 0, 0], [0, 0, 1, 0, 0], [1, 0, 0, 0, 0]]
C = [[0, 0, 0, 1, 0], [0, 0, 0, 0, 1], [0, 1, 0, 0, 0]]
MATRICES = {'A': A, 'B': B, 'C': C}
WIRES = 5


def wires(x):
    w1 = x * x % Q
    return [1, PUBLIC, x, w1, w1 * x % Q]


w = wires(3)
assert w == [1, 35, 3, 9, 27]
row_a, row_b, row_c = ([dot(row, w) for row in M] for M in (A, B, C))
assert all(row_a[i] * row_b[i] % Q == row_c[i] for i in range(3))
frag['r1cs-start'] = (f'$$A = {matrix(A)},\\quad B = {matrix(B)},\\quad C = {matrix(C)},$$\n\n'
                      f'with $\\v{{w}} = {vec(w)}$. The three rows give $A\\v{{w}} = {vec(row_a)}$, $B\\v{{w}} = {vec(row_b)}$ and '
                      f'$C\\v{{w}} = {vec(row_c)}$, and multiplying the first two entrywise gives the third.')


# ---------------------------------------------------------------- interpolation over a domain
def lagrange_basis(domain):
    basis = []
    for i, ri in enumerate(domain):
        num, den = [1], 1
        for j, rj in enumerate(domain):
            if j != i:
                num = pmul(num, [-rj, 1])
                den = den * (ri - rj) % Q
        basis.append(pscale(inv(den), num))
    return basis


def interpolate(values, basis):
    out = []
    for value, poly in zip(values, basis):
        out = padd(out, pscale(value, poly))
    return out


def qap_columns(domain):
    basis = lagrange_basis(domain)
    return {name: [interpolate([row[l] for row in M], basis) for l in range(WIRES)] for name, M in MATRICES.items()}


def combine(columns, assignment):
    out = []
    for coeff, poly in zip(assignment, columns):
        out = padd(out, pscale(coeff, poly))
    return out


def vanishing(domain):
    out = [1]
    for r in domain:
        out = pmul(out, [-r, 1])
    return out


D = [1, 2, 3]
basis = lagrange_basis(D)
for i in range(3):
    for j in range(3):
        assert peval(basis[i], D[j]) == (1 if i == j else 0)
frag['lagrange'] = (
    '$$\\begin{aligned}\n'
    f'L_0(X) &= \\frac{{(X-2)(X-3)}}{{(1-2)(1-3)}} = \\frac{{X^2 - 5X + 6}}{{2}} = {show(basis[0])},\\\\\n'
    f'L_1(X) &= \\frac{{(X-1)(X-3)}}{{(2-1)(2-3)}} = \\frac{{X^2 - 4X + 3}}{{-1}} = {show(basis[1])},\\\\\n'
    f'L_2(X) &= \\frac{{(X-1)(X-2)}}{{(3-1)(3-2)}} = \\frac{{X^2 - 3X + 2}}{{2}} = {show(basis[2])}.\n'
    '\\end{aligned}$$\n\n'
    f'Dividing by 2 modulo 43 means multiplying by {inv(2)}, and dividing by $-1$ means negating. As a spot check, '
    f'$L_0(1) = {peval(basis[0], 1)}$, $L_0(2) = {peval(basis[0], 2)}$ and $L_0(3) = {peval(basis[0], 3)}$.')

columns = qap_columns(D)
rows = []
for name, M in MATRICES.items():
    for l in range(WIRES):
        entries = [row[l] for row in M]
        if any(entries):
            poly = columns[name][l]
            assert [peval(poly, r) for r in D] == entries
            combo = ' + '.join(('' if e == 1 else str(e)) + f'L_{i}' for i, e in enumerate(entries) if e)
            rows.append([f'${name}_{l}$', f'${vec(entries)}$', f'${combo}$', f'${show(poly)}$'])
frag['columns'] = table(['Polynomial', 'Column entries', 'In the basis', 'Coefficients'], rows)

Ax, Bx, Cx = (combine(columns[name], w) for name in 'ABC')
assert [peval(Ax, r) for r in D] == row_a
assert [peval(Bx, r) for r in D] == row_b
assert [peval(Cx, r) for r in D] == row_c
frag['combine'] = (
    f'For $\\v{{w}} = {vec(w)}$, the sums come out as\n\n$$\\begin{{aligned}}\n'
    f'A(X) &= {show(Ax)},\\\\\nB(X) &= {show(Bx)},\\\\\nC(X) &= {show(Cx)}.\n\\end{{aligned}}$$\n\n'
    + table(['$\\rho_i$', '$A(\\rho_i)$', '$B(\\rho_i)$', '$C(\\rho_i)$', '$A(\\rho_i)B(\\rho_i) - C(\\rho_i)$'],
            [[r, peval(Ax, r), peval(Bx, r), peval(Cx, r), (peval(Ax, r) * peval(Bx, r) - peval(Cx, r)) % Q] for r in D])
    + f'\n\nThe columns for $A$, $B$ and $C$ reproduce $A\\v{{w}}$, $B\\v{{w}}$ and $C\\v{{w}}$ from Section 2.')

Px = psub(pmul(Ax, Bx), Cx)
assert len(Px) - 1 == 4 and all(peval(Px, r) == 0 for r in D)
Vx = vanishing(D)
assert Vx == [(-6) % Q, 11, (-6) % Q, 1]
frag['p-poly'] = (f'With $m = 3$ rows, the degree of $P$ is at most 4, and multiplying and subtracting gives $P(X) = {show(Px)}$. Substituting gives '
                  f'$P(1) = {peval(Px, 1)}$, $P(2) = {peval(Px, 2)}$ and $P(3) = {peval(Px, 3)}$, even though the coefficients of $P$ are not zero.')

# Long division, one step per leading term
hx, rem = pdivmod(Px, Vx)
assert rem == [] and pmul(hx, Vx) == Px and len(hx) == 2 and all(hx)
steps, working = [], Px
for shift in (1, 0):
    coeff = hx[shift]
    subtract = [0] * shift + pscale(coeff, Vx)
    working_next = psub(working, subtract)
    steps.append([f'${show(working)}$', f'${term(coeff, shift)}$', f'${show(subtract)}$', f'${show(working_next)}$'])
    working = working_next
assert working == []
frag['division'] = (
    f'Expanding the product gives $V(X) = (X-1)(X-2)(X-3) = X^3 - 6X^2 + 11X - 6$, which is ${show(Vx)}$ modulo 43. Long division removes one leading term at a time:\n\n'
    + table(['Current polynomial', 'Next term of $h$', 'Subtract', 'Result'], steps)
    + f'\n\nThe last column ends at 0, so the division is exact and $h(X) = {show(hx)}$, which has degree $m - 2 = 1$ as predicted.')

tau = 11
assert tau not in D and peval(Px, tau) != 0
ta, tb, tc, th, tv = (peval(p, tau) for p in (Ax, Bx, Cx, hx, Vx))
assert (ta * tb - tc) % Q == th * tv % Q
assert all(peval(Px, t) == peval(hx, t) * peval(Vx, t) % Q for t in range(Q))
frag['qap-test'] = (
    f'Take $\\tau = {tau}$. The prover has already fixed its polynomials, so the two sides are\n\n'
    + table(['Value', 'At $\\tau$'],
            [['$A(\\tau)$', ta], ['$B(\\tau)$', tb], ['$C(\\tau)$', tc], ['$A(\\tau)B(\\tau) - C(\\tau)$', (ta * tb - tc) % Q],
             ['$h(\\tau)$', th], ['$V(\\tau)$', tv], ['$h(\\tau)V(\\tau)$', th * tv % Q]])
    + f'\n\nThe fourth and last rows agree. Checking every one of the 43 values of $\\tau$ confirms that the honest polynomials pass at all of them, as an identity should.')

# ---------------------------------------------------------------- the false witness
w_bad = wires(4)
assert w_bad == [1, 35, 4, 16, 21]
bad_a, bad_b, bad_c = ([dot(row, w_bad) for row in M] for M in (A, B, C))
fails = [i for i in range(3) if bad_a[i] * bad_b[i] % Q != bad_c[i]]
assert fails == [2]
Ab, Bb, Cb = (combine(columns[name], w_bad) for name in 'ABC')
Pb = psub(pmul(Ab, Bb), Cb)
assert peval(Pb, 1) == 0 and peval(Pb, 2) == 0 and peval(Pb, 3) != 0
hb, rb = pdivmod(Pb, Vx)
assert rb and pmul(hb, Vx) != Pb and padd(pmul(hb, Vx), rb) == Pb
assert pdivmod(rb, [2, -3 % Q, 1])[1] == []
frag['no-quotient'] = (
    f'Keep the public value 35 and try $x = 4$, which gives $\\v{{w}} = {vec(w_bad)}$. Now $A\\v{{w}} = {vec(bad_a)}$, $B\\v{{w}} = {vec(bad_b)}$ and $C\\v{{w}} = {vec(bad_c)}$. '
    f'The first two rows hold, and the last gives ${bad_a[2]} \\cdot {bad_b[2]} = {bad_a[2] * bad_b[2] % Q}$ against {bad_c[2]}. '
    f'The polynomial built from this witness is $P\'(X) = {show(Pb)}$, with $P\'(1) = {peval(Pb, 1)}$ and $P\'(2) = {peval(Pb, 2)}$ but $P\'(3) = {peval(Pb, 3)}$. '
    f'Dividing by $V(X)$ leaves the quotient ${show(hb)}$ and the remainder ${show(rb)}$. '
    f'The remainder is not zero, so no polynomial $h$ satisfies $P\'(X) = h(X)V(X)$.')

off_domain = [t for t in range(Q) if t not in D]
counts = {}
for h0, h1 in itertools.product(range(Q), repeat=2):
    c = sum(1 for t in off_domain if peval(Pb, t) == (h0 + h1 * t) * peval(Vx, t) % Q)
    counts[c] = counts.get(c, 0) + 1
assert max(counts) == 2
assert sum(counts.values()) == Q * Q
assert sum(c * m for c, m in counts.items()) == len(off_domain) * Q
frag['guess-h'] = (
    table(['Values of $\\tau$ where the guess passes', 'Number of candidate quotients'],
          [[c, counts[c]] for c in sorted(counts)])
    + f'\n\nThe table covers all $43^2 = {Q * Q}$ candidate polynomials $h$ of degree at most 1, each tried at the {len(off_domain)} values of $\\tau$ outside the domain. '
      f'No candidate passes at more than {max(counts)} of them, which is {max(counts)}/{len(off_domain)}. Averaged over all candidates, a random guess passes at a rate of 1 in 43.')

t_known = 11
needed = peval(Pb, t_known) * inv(peval(Vx, t_known)) % Q
other = 12
assert peval(Pb, t_known) == needed * peval(Vx, t_known) % Q and needed != 0
assert peval(Pb, other) != needed * peval(Vx, other) % Q
frag['known-tau'] = (f'Suppose the prover with $x = 4$ learns $\\tau = {t_known}$ before answering. It computes $P\'({t_known}) = {peval(Pb, t_known)}$ and $V({t_known}) = {peval(Vx, t_known)}$, '
                     f'divides to get {needed}, and presents the constant polynomial $h(X) = {needed}$. The check at $\\tau = {t_known}$ passes because ${needed} \\cdot {peval(Vx, t_known)} = {peval(Pb, t_known)}$ modulo 43. '
                     f'At $\\tau = {other}$ the same $h$ gives ${needed * peval(Vx, other) % Q}$ against $P\'({other}) = {peval(Pb, other)}$, so this forgery only works at the point the prover knew in advance.')

# ---------------------------------------------------------------- roots of unity
omega = 6
assert pow(omega, 3, Q) == 1 and omega != 1
D3 = [pow(omega, i, Q) for i in range(3)]
assert D3 == [1, 6, 36] and vanishing(D3) == [Q - 1, 0, 0, 1]
assert (Q - 1) % 4 != 0
cols3 = qap_columns(D3)
A3, B3, C3 = (combine(cols3[name], w) for name in 'ABC')
P3 = psub(pmul(A3, B3), C3)
h3, r3 = pdivmod(P3, vanishing(D3))
assert r3 == [] and h3 != hx
frag['unity'] = (f'In $\\F_{{43}}$ the value $\\omega = {omega}$ satisfies ${omega}^3 = 216 = 1$ modulo 43, so its powers form the domain $\\{{{", ".join(map(str, D3))}\\}}$, and the vanishing polynomial collapses to $V(X) = X^3 - 1$. '
                 f'Repeating the construction on this domain with the same witness gives different polynomials, for example $A(X) = {show(A3)}$, and the exact quotient $h(X) = {show(h3)}$. '
                 f'The same field has no domain of size 4, because 4 does not divide $43 - 1 = {Q - 1}$. Real proof systems pick fields whose multiplicative group has a large power of two in its order for this reason.')

m_big = 2 ** 16
frag['scale'] = (f'For a circuit of $m = 2^{{16}} = {m_big:,}$ rows, $P(X)$ has degree up to $2(m-1) = {2 * (m_big - 1):,}$. Representing it requires a domain with more than {2 * (m_big - 1):,} points, and the next power of two is $2^{{17}} = {2 ** 17:,}$.')

# ---------------------------------------------------------------- Ragu's route, reusing chapter 04
n = 2
N = 4 * n
z, y, x = 5, 7, 9
rows_u = [[1, 0], [0, 1], [-1, 0], [1, 0]] + [[0, 0]] * 4
rows_v = [[-1, 0], [0, 0], [0, 1], [0, 0]] + [[0, 0]] * 4
rows_w = [[0, 0], [-1, 0], [0, 0], [0, 1]] + [[0, 0]] * 4
k_vec = [0, 0, 0, PUBLIC - 5, 0, 0, 0, 0]


def trace(a, b, c):
    return [c[0], c[1], a[1], a[0], b[0], b[1], 0, 0]


def witness(val):
    w1 = val * val % Q
    return [val, w1], [val, val], [w1, w1 * val % Q]


def s_at(at):
    s = [0] * N
    for j in range(N):
        for i in range(n):
            s[2 * n + i] += at ** j * rows_u[j][i]
            s[2 * n - 1 - i] += at ** j * rows_v[j][i]
            s[4 * n - 1 - i] += at ** j * rows_w[j][i]
    return [e % Q for e in s]


def t_at(at):
    t = [0] * N
    for i in range(n):
        t[N - 1 - i] = -(at ** (2 * n - 1 - i) + at ** (2 * n + i)) % Q
    return t


def dilate(p, at):
    return [p[i] * pow(at, i, Q) % Q for i in range(N)]


def right_factor(r, at_z, at_y):
    d, s, t = dilate(r, at_z), s_at(at_y), t_at(at_z)
    return [(d[i] + s[i] + t[i]) % Q for i in range(N)]


def k_at(at):
    return sum(k_vec[j] * pow(at, j, Q) for j in range(N)) % Q


def full_product(p, q):
    """Product with exact length, keeping trailing zeros."""
    out = [0] * (N + N - 1)
    for i, e in enumerate(p):
        for j, f in enumerate(q):
            out[i + j] = (out[i + j] + e * f) % Q
    return out


r_vec = trace(*witness(3))
assert r_vec == [9, 27, 9, 3, 3, 3, 0, 0]
dil, s_vec, t_vec = dilate(r_vec, z), s_at(y), t_at(z)
f_vec = right_factor(r_vec, z, y)
assert s_vec == [0, 0, 6, 42, 37, 7, 42, 36] and t_vec == [0, 0, 0, 0, 0, 0, 32, 24]
assert f_vec == [9, 6, 16, 30, 20, 8, 31, 17]
frag['right-factor'] = table(
    ['Polynomial', 'Coefficients of $X^0, \\ldots, X^7$'],
    [['$r(X)$', f'${vec(r_vec)}$'], ['$r(5X)$', f'${vec(dil)}$'], ['$s(X, 7)$', f'${vec(s_vec)}$'], ['$t(X, 5)$', f'${vec(t_vec)}$'], ['$f(X)$', f'${vec(f_vec)}$']]
) + '\n\nThe vector for $f(X)$ is the combined right vector from Section 12 of the arithmetization chapter, now read as coefficients.'
for at in (2, 9, 30):
    assert peval(dil, at) == peval(r_vec, at * z % Q)

target = k_at(y)
product = full_product(r_vec, f_vec)
assert product[N - 1] == target == 13 and len(product) == 15
assert sum(r_vec[i] * f_vec[N - 1 - i] for i in range(N)) % Q == target
pairs = [[i, r_vec[i], N - 1 - i, f_vec[N - 1 - i], r_vec[i] * f_vec[N - 1 - i] % Q] for i in range(N)]
frag['middle'] = (
    table(['$i$', 'Coefficient of $X^i$ in $r$', '$7 - i$', 'Coefficient of $X^{7-i}$ in $f$', 'Product'], pairs)
    + f'\n\nThe last column sums to {target} modulo 43. On the other side, $k(Y) = {PUBLIC - 5}Y^3$ because only $k_3$ is nonzero, so $k(7) = {PUBLIC - 5} \\cdot 7^3 = {target}$ modulo 43.')
frag['product'] = (
    'The full product has 15 coefficients:\n\n'
    + table(['Power of $X$'] + [str(i) for i in range(15)], [['Coefficient'] + [(f'**{e}**' if i == N - 1 else e) for i, e in enumerate(product)]])
    + f'\n\nThe entry for $X^7$ is {target}, the value the consolidated equation requires. Every other entry is a by-product of the multiplication that the check does not constrain. The two highest coefficients are zero in this example because $\\v{{d}} = \\v{{0}}$ leaves $r$ with degree {len(trim(r_vec)) - 1}.')

c_lo, c_hi = product[:N], product[N:]
c1 = c_lo[::-1]
c2 = c_hi + [0]
assert len(c_lo) == 8 and len(c_hi) == 7 and c1[0] == target
frag['split'] = (
    f'For our product, $c_{{\\mathrm{{lo}}}}$ has coefficients ${vec(c_lo)}$ and $c_{{\\mathrm{{hi}}}}$ has coefficients ${vec(c_hi)}$. '
    f'Reversing the lower half gives $c_1(X)$ with coefficients ${vec(c1)}$, so $c_1(0) = {c1[0]}$, which is the required value $k(7)$. We set $c_2 = c_{{\\mathrm{{hi}}}}$.')


def split_side(p1, p2, at):
    return (pow(at, N - 1, Q) * peval(p1, inv(at)) + pow(at, N, Q) * peval(p2, at)) % Q


xz, xinv = x * z % Q, inv(x)
assert xinv == 24 and xz == 2
vals = dict(r=peval(r_vec, x), rz=peval(r_vec, xz), s=peval(s_vec, x), t=peval(t_vec, x), c1=peval(c1, xinv), c2=peval(c2, x))
assert all(vals.values())
lhs = vals['r'] * (vals['rz'] + vals['s'] + vals['t']) % Q
assert lhs == split_side(c1, c2, x) and lhs != 0
assert peval(c_lo, x) == pow(x, N - 1, Q) * peval(c1, xinv) % Q
assert all(peval(r_vec, a) * peval(f_vec, a) % Q == split_side(c1, c2, a) for a in range(1, Q))
# The closed form of t from the Ragu Book's footnote agrees with the sum.
for a in range(1, Q):
    closed = pow(a, 3 * n, Q) * (pow(z, n, Q) * sum(pow(a * z, e, Q) for e in range(n))
                                 + pow(z, 3 * n - 1, Q) * sum(pow(a * inv(z), e, Q) for e in range(n))) % Q
    assert peval(t_vec, a) == -closed % Q
assert 8 * 2 ** 11 - 1 < 2 ** 14
frag['reversal-check'] = (f'At $x = {x}$, the inverse is $x^{{-1}} = {xinv}$, because ${x} \\cdot {xinv} = 216 = 1$ modulo 43. '
                          f'Then $c_1({xinv}) = {vals["c1"]}$, $x^7 = {pow(x, 7, Q)}$, and ${pow(x, 7, Q)} \\cdot {vals["c1"]} = {peval(c_lo, x)}$ modulo 43, which equals $c_{{\\mathrm{{lo}}}}({x})$ computed directly.')

frag['run'] = (
    table(['Step', 'Party', 'Value or check'], [
        [1, 'Both', f'Hold $s(X, Y)$, $t(X, Z)$ and $k(Y) = {PUBLIC - 5}Y^3$'],
        [2, 'Prover sends oracle', f'$r(X) = {show(r_vec)}$'],
        [3, 'Verifier sends challenges', f'$z = {z}$, $y = {y}$'],
        [4, 'Prover computes', f'$f(X) = r({z}X) + s(X, {y}) + t(X, {z})$ and the product $r(X)f(X)$'],
        [5, 'Prover sends oracles', f'$c_1(X) = {show(c1)}$ and $c_2(X) = {show(c2)}$'],
        [6, 'Verifier sends challenge', f'$x = {x}$, so $xz = {xz}$ and $x^{{-1}} = {xinv}$'],
        [7, 'Verifier queries $r$', f'$r({x}) = {vals["r"]}$ and $r({xz}) = {vals["rz"]}$'],
        [8, 'Verifier queries $c_1$', f'$c_1({xinv}) = {vals["c1"]}$ and $c_1(0) = {c1[0]}$'],
        [9, 'Verifier queries $c_2$', f'$c_2({x}) = {vals["c2"]}$'],
        [10, 'Verifier computes locally', f'$s({x}, {y}) = {vals["s"]}$, $t({x}, {z}) = {vals["t"]}$, $k({y}) = {target}$'],
        [11, 'Verifier checks the split', f'${vals["r"]} \\cdot ({vals["rz"]} + {vals["s"]} + {vals["t"]}) = {lhs}$ and ${pow(x, 7, Q)} \\cdot {vals["c1"]} + {pow(x, 8, Q)} \\cdot {vals["c2"]} = {lhs}$'],
        [12, 'Verifier checks the target', f'$c_1(0) = {c1[0]} = k({y})$'],
    ])
    + f'\n\nBoth checks pass. Repeating step 11 at all {Q - 1} nonzero values of $x$ shows that the honest polynomials pass at every one.')

# Cheating at the coefficient: x = 4, same challenges
lucky_r = trace(*witness(4))
lucky = sum(1 for at_z in range(Q) for at_y in range(Q)
            if sum(lucky_r[i] * right_factor(lucky_r, at_z, at_y)[N - 1 - i] for i in range(N)) % Q == k_at(at_y))
assert lucky == 43
frag['lucky'] = f'For the false witness with $x = 4$, counting all pairs finds {lucky} of the {Q * Q} that do so.'
frag['toy-one'] = (f'Our toy circuit has no `ONE` wire. Its $r(0) = c_0$ is the wire value {r_vec[0]} and its $k(0)$ is {k_at(0)}, so the run in Section 14 leaves this check out.')
r_bad = trace(*witness(4))
f_bad = right_factor(r_bad, z, y)
T_bad = full_product(r_bad, f_bad)
delta = (T_bad[N - 1] - target) % Q
assert delta != 0 and r_bad == [16, 21, 16, 4, 4, 4, 0, 0]
c1_naive = T_bad[:N][::-1]
c1_naive[0] = target
c2_true = T_bad[N:] + [0]
assert c1_naive[0] == target
naive_passes = [a for a in range(1, Q) if peval(r_bad, a) * peval(f_bad, a) % Q == split_side(c1_naive, c2_true, a)]
assert naive_passes == []
frag['cheat-naive'] = (
    f'Take the false witness with $x = 4$ from Section 7, so $r\'(X) = {show(r_bad)}$, at the same $z = {z}$ and $y = {y}$. '
    f'The coefficient of $X^7$ in $r\'(X)f\'(X)$ is {T_bad[N - 1]}, while $k({y}) = {target}$, so the honest split would fail the target check. '
    f'The prover can change the constant term of $c_1$ to {target} and leave everything else alone, which fixes the target check. '
    f'The two sides of the split check then differ by ${delta}X^7$, and the verifier rejects at all {Q - 1} nonzero values of $x$.')

# A prover who plans for the split check: D(X) with 15 nonzero roots and the right middle coefficient.
for roots in itertools.combinations(range(1, Q), 15):
    D_poly = [1]
    for root in roots:
        D_poly = pmul(D_poly, [-root, 1])
    if D_poly[N - 1] != 0:
        break
assert D_poly[N - 1] != 0 and len(D_poly) == 16
D_poly = pscale(delta * inv(D_poly[N - 1]), D_poly)
assert D_poly[N - 1] == delta
T_padded = T_bad + [0]
faked = [(T_padded[i] - D_poly[i]) % Q for i in range(16)]
assert faked[N - 1] == target
c1_best, c2_best = faked[:N][::-1], faked[N:]
assert c1_best[0] == target and len(c2_best) == N
best_passes = [a for a in range(1, Q) if peval(r_bad, a) * peval(f_bad, a) % Q == split_side(c1_best, c2_best, a)]
assert best_passes == list(roots) and len(best_passes) == 15
frag['cheat-best'] = (
    f'The prover can do better by spreading the difference over many powers of $X$. Let $D(X)$ be a polynomial of degree 15 whose coefficient of $X^7$ is {delta}, which is the amount the true coefficient must change by. '
    f'Writing $D$ as a multiple of $(X-1)(X-2)\\cdots(X-{roots[-1]})$ gives it the 15 roots $1, \\ldots, {roots[-1]}$. The prover then splits $r\'(X)f\'(X) - D(X)$ instead of the true product, '
    f'and the new $c_1$ has $c_1(0) = {c1_best[0]}$, as the target check requires. The split check now compares $r\'(x)f\'(x)$ with $r\'(x)f\'(x) - D(x)$, so it passes exactly where $D(x) = 0$. '
    f'Testing every nonzero $x$ finds {len(best_passes)} passing values out of {Q - 1}, which is the most a polynomial of degree 15 allows. For $n = 2^{{11}}$ on a field of about $2^{{255}}$ elements, the same limit of $8n - 1$ roots gives a probability below $2^{{-240}}$.')

# A prover who knows x in advance
adjust = delta * inv(x) % Q
c1_late = list(T_bad[:N][::-1])
c1_late[0] = target
c2_late = list(c2_true)
c2_late[0] = (c2_late[0] + adjust) % Q
late_passes = [a for a in range(1, Q) if peval(r_bad, a) * peval(f_bad, a) % Q == split_side(c1_late, c2_late, a)]
assert late_passes == [x]
frag['cheat-early'] = (
    f'Suppose the prover also knows $x = {x}$ before sending $c_1$ and $c_2$. Changing the constant term of $c_1$ moved the split check by ${delta}x^7$, and adding a constant $e$ to $c_2$ moves it by $ex^8$ in the other direction. '
    f'Choosing $e = {delta} / {x} = {adjust}$ cancels the two at this one point. The forged pair passes both checks at $x = {x}$, and testing the other nonzero values confirms that it passes at no other point.')

print(json.dumps(frag))
