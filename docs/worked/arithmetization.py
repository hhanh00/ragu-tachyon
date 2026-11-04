"""Worked example for arithmetization.md. Prints fragments as JSON."""
import json
from toy_curve import Q

n = 2
z, y = 5, 7
PUBLIC = 35
frag = {}


def vec(v):
    return '(' + ', '.join(str(e % Q) for e in v) + ')'


def rev(p, q):
    return sum(p[k] * q[len(q) - 1 - k] for k in range(len(p))) % Q


def witness(x):
    w1 = x * x % Q
    w2 = w1 * x % Q
    return [x, w1], [x, x], [w1, w2]


a, b, c = witness(3)
assert (c[1] + a[0] + 5) % Q == PUBLIC

frag['flatten'] = '\n'.join([
    '| Step | Operation | Value for $x = 3$ |', '| --- | --- | --- |',
    '| 1 | $w_1 = x \\cdot x$ | ' + str(c[0]) + ' |',
    '| 2 | $w_2 = w_1 \\cdot x$ | ' + str(c[1]) + ' |',
    f'| 3 | $w_2 + x + 5$ | {(c[1] + a[0] + 5) % Q} |',
])

frag['gates'] = '\n'.join(
    ['| Gate $i$ | $a_i$ | $b_i$ | $c_i$ | Check |', '| --- | --- | --- | --- | --- |']
    + [f'| {i} | {a[i]} | {b[i]} | {c[i]} | ${a[i]} \\cdot {b[i]} = {c[i]}$ |' for i in range(n)])

# (u, v, w, k) for each constraint; the remaining rows of 4n are empty.
rows = [
    ('a_0 - b_0 = 0', [1, 0], [-1, 0], [0, 0], 0),
    ('a_1 - c_0 = 0', [0, 1], [0, 0], [-1, 0], 0),
    ('b_1 - a_0 = 0', [-1, 0], [0, 1], [0, 0], 0),
    (f'c_1 + a_0 = {PUBLIC - 5}', [1, 0], [0, 0], [0, 1], (PUBLIC - 5) % Q),
]
rows_u = [r[1] for r in rows] + [[0, 0]] * 4
rows_v = [r[2] for r in rows] + [[0, 0]] * 4
rows_w = [r[3] for r in rows] + [[0, 0]] * 4
k = [r[4] for r in rows] + [0] * 4


def dot(p, q):
    return sum(e * f for e, f in zip(p, q)) % Q


def residual(j, a, b, c):
    return (dot(rows_u[j], a) + dot(rows_v[j], b) + dot(rows_w[j], c) - k[j]) % Q


assert all(residual(j, a, b, c) == 0 for j in range(8))
frag['constraints'] = '\n'.join(
    ['| $j$ | Constraint | $\\v{u}_j$ | $\\v{v}_j$ | $\\v{w}_j$ | $k_j$ |', '| --- | --- | --- | --- | --- | --- |']
    + [f'| {j} | ${r[0]}$ | $({r[1][0]}, {r[1][1]})$ | $({r[2][0]}, {r[2][1]})$ | $({r[3][0]}, {r[3][1]})$ | {r[4]} |' for j, r in enumerate(rows)])

a4, b4, c4 = witness(4)
assert all(residual(j, a4, b4, c4) == 0 for j in range(3))
frag['wrong-input'] = (f'Try $x = 4$ instead. Filling in the gates gives $\\v{{a}} = {vec(a4)}$, $\\v{{b}} = {vec(b4)}$ and $\\v{{c}} = {vec(c4)}$, '
                       f'with $4 \\cdot 4 = {c4[0]}$ and ${a4[1]} \\cdot 4 = {c4[1]}$ modulo 43. Both gates and the first three constraints hold. '
                       f'The last constraint gives $c_1 + a_0 = {(c4[1] + a4[0]) % Q}$, which is not {PUBLIC - 5}, so this witness is rejected.')

# Collapsing the gates with powers of z
bad_a, bad_b, bad_c = [3, 8], [3, 3], [8, 27]
assert all(residual(j, bad_a, bad_b, bad_c) == 0 for j in range(8))
err = [(bad_a[i] * bad_b[i] - bad_c[i]) % Q for i in range(n)]
assert all(err)


def plain_gate_sum(a, b, c, at):
    return sum(at ** i * (a[i] * b[i] - c[i]) for i in range(n)) % Q


plain_roots = [t for t in range(Q) if plain_gate_sum(bad_a, bad_b, bad_c, t) == 0]
frag['gate-sum'] = (f'For the honest witness both gate errors are 0, so the sum is 0 for every $z$. Now take a dishonest witness with '
                    f'$\\v{{a}} = {vec(bad_a)}$, $\\v{{b}} = {vec(bad_b)}$ and $\\v{{c}} = {vec(bad_c)}$. It satisfies all the linear constraints above, '
                    f'but its gate errors are $a_0 b_0 - c_0 = {err[0]}$ and $a_1 b_1 - c_1 = {err[1]}$ modulo 43. At $z = {z}$ the sum is '
                    f'${err[0]} + {z} \\cdot {err[1]} = {plain_gate_sum(bad_a, bad_b, bad_c, z)}$, which exposes the error. Checking all 43 values of $z$ finds '
                    f'{len(plain_roots)} value that hides it, $z = {plain_roots[0]}$, the root of this degree-1 polynomial.')

uy = [sum(y ** j * rows_u[j][i] for j in range(8)) % Q for i in range(n)]
vy = [sum(y ** j * rows_v[j][i] for j in range(8)) % Q for i in range(n)]
wy = [sum(y ** j * rows_w[j][i] for j in range(8)) % Q for i in range(n)]
ky = sum(y ** j * k[j] for j in range(8)) % Q
assert (dot(uy, a) + dot(vy, b) + dot(wy, c)) % Q == ky
frag['constraint-sum'] = (f'At $y = {y}$, the combined vectors are $\\v{{u}}(y) = {vec(uy)}$, $\\v{{v}}(y) = {vec(vy)}$ and $\\v{{w}}(y) = {vec(wy)}$. '
                          f'The left side for the honest witness is ${dot(uy, a)} + {dot(vy, b)} + {dot(wy, c)} = {(dot(uy, a) + dot(vy, b) + dot(wy, c)) % Q}$ modulo 43. '
                          f'The right side is ${y}^3 \\cdot {PUBLIC - 5} = {ky}$, because only $k_3$ is nonzero.')

# Coefficient extraction
p, q_ = [1, 2, 3, 4], [5, 6, 7, 8]
prod = [0] * 7
for i, e in enumerate(p):
    for j, f in enumerate(q_):
        prod[i + j] = (prod[i + j] + e * f) % Q
assert prod[3] == rev(p, q_)
frag['product'] = (f'Let $p(X) = 1 + 2X + 3X^2 + 4X^3$ and $q(X) = 5 + 6X + 7X^2 + 8X^3$ over $\\F_{{43}}$. The coefficient of $X^3$ in $p(X)q(X)$ collects every pair of exponents that adds to 3: '
                   f'$1 \\cdot 8 + 2 \\cdot 7 + 3 \\cdot 6 + 4 \\cdot 5 = {prod[3]}$ modulo 43. The revdot product computes the same sum, since $\\rv{{q}} = (8, 7, 6, 5)$ and $\\dot{{\\v{{p}}}}{{\\rv{{q}}}} = {rev(p, q_)}$. '
                   f'The full product has coefficients ${vec(prod)}$, and the entry for $X^3$ is the one in the middle.')


def layout(a, b, c, d=(0, 0)):
    return [c[0], c[1], a[1], a[0], b[0], b[1], d[1], d[0]]


names = ['c_0', 'c_1', 'a_1', 'a_0', 'b_0', 'b_1', 'd_1', 'd_0']
r = layout(a, b, c)
frag['layout'] = '\n'.join(
    ['| Position $k$ | Entry | Value | Partner position $7 - k$ | Partner entry |', '| --- | --- | --- | --- | --- |']
    + [f'| {k_} | ${names[k_]}$ | {r[k_]} | {7 - k_} | ${names[7 - k_]}$ |' for k_ in range(8)])
assert rev(r, r) == 2 * dot(a, b) % Q
frag['plain-revdot'] = (f'For our witness, $\\v{{r}} = {vec(r)}$. Multiplying each entry by its partner and summing gives $\\revdot{{\\v{{r}}}}{{\\v{{r}}}} = {rev(r, r)}$, and $2\\dot{{\\v{{a}}}}{{\\v{{b}}}} = 2({a[0]} \\cdot {b[0]} + {a[1]} \\cdot {b[1]}) = {2 * dot(a, b) % Q}$ modulo 43.')

zp = [z ** i % Q for i in range(8)]
dil = [r[i] * zp[i] % Q for i in range(8)]
term_rows = ['| $k$ | $r_k$ | $r_{7-k}$ | $z^{7-k}$ | Term |', '| --- | --- | --- | --- | --- |']
for k_ in range(8):
    term_rows.append(f'| {k_} | {r[k_]} | {r[7 - k_]} | {zp[7 - k_]} | {r[k_] * r[7 - k_] * zp[7 - k_] % Q} |')
weights = [(z ** (2 * n - 1 - i) + z ** (2 * n + i)) % Q for i in range(n)]
dil_total = rev(r, dil)
assert dil_total == sum(a[i] * b[i] * weights[i] for i in range(n)) % Q
frag['dilation'] = (f'At $z = {z}$ the powers are ${vec(zp)}$, so $\\v{{r}} \\circ \\v{{z^{{8}}}} = {vec(dil)}$.\n\n' + '\n'.join(term_rows)
                    + f'\n\nThe last column sums to {dil_total}. The formula above gives the same value, using weights $z^3 + z^4 = {weights[0]}$ and $z^2 + z^5 = {weights[1]}$: '
                      f'${a[0] * b[0]} \\cdot {weights[0]} + {a[1] * b[1]} \\cdot {weights[1]} = {dil_total}$ modulo 43.')


def t_vector(at):
    t = [0] * 8
    for i in range(n):
        t[7 - i] = -(at ** (2 * n - 1 - i) + at ** (2 * n + i)) % Q
    return t


t = t_vector(z)
assert rev(r, t) == -sum(c[i] * weights[i] for i in range(n)) % Q
assert rev(r, [(dil[i] + t[i]) % Q for i in range(8)]) == 0
frag['t-vector'] = (f'At $z = {z}$, $\\v{{t}} = {vec(t)}$. Its two nonzero entries sit at positions 7 and 6, the partners of $c_0$ and $c_1$. Then $\\revdot{{\\v{{r}}}}{{\\v{{t}}}} = {rev(r, t)}$, '
                    f'and adding the dilated term gives ${dil_total} + {rev(r, t)} = 0$ modulo 43, as it should for a witness that satisfies its gates.')


def s_vector(at):
    s = [0] * 8
    for j in range(8):
        for i in range(n):
            s[2 * n + i] += at ** j * rows_u[j][i]
            s[2 * n - 1 - i] += at ** j * rows_v[j][i]
            s[4 * n - 1 - i] += at ** j * rows_w[j][i]
    return [e % Q for e in s]


s = s_vector(y)
assert rev(r, s) == ky
frag['s-vector'] = (f'At $y = {y}$, placing the vectors from Section 6 at the partner positions gives $\\v{{s}} = {vec(s)}$, and $\\revdot{{\\v{{r}}}}{{\\v{{s}}}} = {rev(r, s)}$. This equals $\\dot{{\\v{{k}}}}{{\\v{{y^{{8}}}}}} = {ky}$.')


def combined(a, b, c, at_z, at_y):
    rr = layout(a, b, c)
    pow_z = [at_z ** i % Q for i in range(8)]
    right = [(rr[i] * pow_z[i] + t_vector(at_z)[i] + s_vector(at_y)[i]) % Q for i in range(8)]
    return rev(rr, right), sum(at_y ** j * k[j] for j in range(8)) % Q


lhs, rhs = combined(a, b, c, z, y)
assert lhs == rhs
assert all(combined(a, b, c, u_, v_)[0] == combined(a, b, c, u_, v_)[1] for u_ in range(Q) for v_ in range(Q))
right = [(dil[i] + t[i] + s[i]) % Q for i in range(8)]
frag['combined'] = (f'At $z = {z}$ and $y = {y}$, the combined right vector is $\\v{{r}} \\circ \\v{{z^{{8}}}} + \\v{{t}} + \\v{{s}} = {vec(right)}$. Its revdot product with $\\v{{r}} = {vec(r)}$ is {lhs}, '
                    f'and $\\dot{{\\v{{k}}}}{{\\v{{y^{{8}}}}}} = {rhs}$. Checking the equation at all $43^2 = {Q * Q}$ pairs $(z, y)$ confirms that the honest witness passes at every pair.')

bound = 7
cases = [
    ('Gates fail, constraints hold', bad_a, bad_b, bad_c),
    ('Gates hold, last constraint fails', a4, b4, c4),
    ('Both fail', [4, 8], [4, 4], [8, 21]),
]
table = ['| Dishonest witness | $\\v{a}$ | $\\v{b}$ | $\\v{c}$ | Passing pairs $(z, y)$ | Fraction |', '| --- | --- | --- | --- | --- | --- |']
for name, ca, cb, cc in cases:
    count = sum(1 for u_ in range(Q) for v_ in range(Q) if combined(ca, cb, cc, u_, v_)[0] == combined(ca, cb, cc, u_, v_)[1])
    assert count * Q <= bound * Q * Q
    table.append(f'| {name} | ${vec(ca)}$ | ${vec(cb)}$ | ${vec(cc)}$ | {count} of {Q * Q} | {count / (Q * Q):.3f} |')
frag['cheats'] = '\n'.join(table) + f'\n\nThe bound for this circuit is $(4n - 1)/|\\F_q| = {bound}/{Q} \\approx {bound / Q:.3f}$, and each row falls below it.'

# R1CS for the same statement
A = [[0, 0, 1, 0, 0], [0, 0, 0, 1, 0], [5, 0, 1, 0, 1]]
B = [[0, 0, 1, 0, 0], [0, 0, 1, 0, 0], [1, 0, 0, 0, 0]]
C = [[0, 0, 0, 1, 0], [0, 0, 0, 0, 1], [0, 1, 0, 0, 0]]
zv = [1, PUBLIC, 3, c[0], c[1]]
assert all(dot(A[i], zv) * dot(B[i], zv) % Q == dot(C[i], zv) for i in range(3))


def matrix(m):
    return '\\begin{bmatrix}' + ' \\\\ '.join(' & '.join(map(str, row)) for row in m) + '\\end{bmatrix}'


frag['r1cs'] = (f'With $\\v{{w}} = (1, {PUBLIC}, 3, {c[0]}, {c[1]})$, holding the constant 1, the public output, $x$, $w_1$ and $w_2$, the three matrices are\n\n'
                f'$$A = {matrix(A)},\\quad B = {matrix(B)},\\quad C = {matrix(C)}.$$\n\n'
                f'The products are $A\\v{{w}} = {vec([dot(r_, zv) for r_ in A])}$ and $B\\v{{w}} = {vec([dot(r_, zv) for r_ in B])}$. Their entrywise product is ${vec([dot(A[i], zv) * dot(B[i], zv) for i in range(3)])}$, which equals $C\\v{{w}}$.')

print(json.dumps(frag))
