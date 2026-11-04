"""Worked example for nark.md. Prints fragments as JSON.

The verifier below is one function, and every honest run and every cheating
attempt in the chapter goes through it, so a printed verdict is a computed one.
"""
import hashlib
import json
from functools import lru_cache

import toy_curve
from toy_curve import Q, G, H, U, add, curve_points, log, show

frag = {}


@lru_cache(maxsize=None)
def mul(k, a):
    return toy_curve.mul(k % Q, a)


def msm(scalars, points):
    out = None
    for k, a in zip(scalars, points):
        out = add(out, mul(k, a))
    return out


def neg(a):
    return None if a is None else (a[0], -a[1] % 31)


# The shared curve exports four generators, and a trace of 4n entries needs 4n.
# These extend the list. A search over the unused x-coordinates picked them so that
# no commitment in the main run equals a public generator or another commitment.
EXTRA = [(4, 6), (5, 2), (25, 2), (30, 23), (9, 9), (14, 22), (20, 6), (28, 21)]
assert all(a in curve_points() for a in EXTRA)
GENS = G + EXTRA
assert len(set(GENS + [H, U])) == 14 and all(p is not None for p in GENS)


# Vectors and polynomials are lists over F_43, lowest degree first.
def vec(v):
    return '(' + ', '.join(str(e % Q) for e in v) + ')'


def inv(a):
    assert a % Q
    return pow(a, Q - 2, Q)


def ev(p, at):
    out = 0
    for e in reversed(p):
        out = (out * at + e) % Q
    return out


def revdot(p, q):
    assert len(p) == len(q)
    return sum(p[i] * q[len(q) - 1 - i] for i in range(len(p))) % Q


def lin(*terms):
    size = max(len(p) for _, p in terms)
    return [sum(k * (p[i] if i < len(p) else 0) for k, p in terms) % Q for i in range(size)]


def poly_str(p):
    terms = []
    for i, e in enumerate(p):
        e %= Q
        if e:
            power = '' if i == 0 else 'X' if i == 1 else f'X^{{{i}}}' if i > 9 else f'X^{i}'
            terms.append(str(e) if i == 0 else power if e == 1 else f'{e}{power}')
    return ' + '.join(terms) if terms else '0'


def commit(v, gamma=0):
    return add(msm(v, GENS), mul(gamma, H))


def table(head, rows):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '| ' + ' | '.join(['---'] * len(head)) + ' |']
                     + ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows])


def divide(p, at):
    """Synthetic division by X - at, which ignores any claimed value."""
    out, carry = [0] * (len(p) - 1), 0
    for i in range(len(p) - 1, 0, -1):
        carry = (p[i] + at * carry) % Q
        out[i - 1] = carry
    return out


# The circuit: rows hold sparse maps from wire names to coefficients.
class Circuit:
    def __init__(self, n, rows):
        self.n, self.rows = n, rows

    def s(self, y):
        n, out = self.n, [0] * (4 * self.n)
        for j, row in enumerate(self.rows):
            weight = pow(y, j, Q)
            for (kind, i), coeff in row.items():
                pos = {'a': 2 * n + i, 'b': 2 * n - 1 - i, 'c': 4 * n - 1 - i, 'd': i}[kind]
                out[pos] = (out[pos] + weight * coeff) % Q
        return out

    def t(self, z):
        n, out = self.n, [0] * (4 * self.n)
        for i in range(n):
            out[4 * n - 1 - i] = -(pow(z, 2 * n - 1 - i, Q) + pow(z, 2 * n + i, Q)) % Q
        return out

    def trace(self, a, b, c, d=None):
        d = d or [0] * self.n
        return [e % Q for e in list(c) + list(a)[::-1] + list(b) + list(d)[::-1]]

    def right(self, r, z, y):
        dil = [r[i] * pow(z, i, Q) % Q for i in range(4 * self.n)]
        return lin((1, dil), (1, self.s(y)), (1, self.t(z)))


TOY = Circuit(2, [
    {('a', 0): 1, ('b', 0): -1},
    {('a', 1): 1, ('c', 0): -1},
    {('a', 0): -1, ('b', 1): 1},
    {('a', 0): 1, ('c', 1): 1},
])
K_POLY = [0, 0, 0, 30, 0, 0, 0, 0]


def toy_witness(x):
    w1 = x * x % Q
    return [x, w1], [x, x], [w1, w1 * x % Q]


R_HONEST = TOY.trace(*toy_witness(3))
R_FALSE = TOY.trace(*toy_witness(4))


# Challenge sources: hand-picked values, or a Fiat-Shamir transcript.
class Fixed:
    def __init__(self, **values):
        self.values = values

    def absorb_point(self, _):
        pass

    def absorb(self, _):
        pass

    def squeeze(self, name):
        return self.values[name]


HAND = dict(z=5, y=7, x=9, alpha=11, u=17, beta=23)
GAMMA_R, GAMMA_B, GAMMA_F = 17, 29, 5


def prove(circuit, r, k, ch, gamma_r=GAMMA_R, gamma_b=GAMMA_B, gamma_f=GAMMA_F, constant_claims=False,
          b_shift=None, c_override=None, eval_shift=None, value_shift=None, committed_r=None):
    """Runs the prover. The optional arguments let a cheater deviate at one message."""
    p = {}
    p['K'] = commit(k)
    # A cheater holding a generator relation can open a different r under this point.
    p['R'] = committed_r if committed_r is not None else commit(r, gamma_r)
    ch.absorb_point(p['K'])
    ch.absorb_point(p['R'])
    z, y = ch.squeeze('z'), ch.squeeze('y')
    p['z'], p['y'] = z, y

    a = r
    s = circuit.s(y)
    b = circuit.right(r, z, y)
    if b_shift is not None:
        b = lin((1, b), (1, b_shift))
    p['S'], p['A'], p['B'] = commit(s), p['R'], commit(b, gamma_b)
    p['c'] = ev(k, y) if c_override is None else c_override
    ch.absorb_point(p['S'])
    ch.absorb_point(p['B'])
    ch.absorb(p['c'])
    p.update(s=s, a=a, b=b, gamma_a=gamma_r, gamma_b=gamma_b)

    x = ch.squeeze('x')
    p['x'] = x
    xz = x * z % Q
    evals = {'a': ev(a, xz), 's': ev(s, x), 'b': ev(b, x)}
    if eval_shift:
        evals['b'] = (evals['b'] + eval_shift) % Q
    p['evals'] = evals
    for key in ('a', 's', 'b'):
        ch.absorb(evals[key])

    alpha = ch.squeeze('alpha')
    claims = claim_list(p, constant_claims)
    polys = {'a': a, 'b': b, 's': s, 'k': k}
    f = [0] * len(a)
    for poly, at, _ in claims:
        f = lin((alpha, f), (1, divide(polys[poly], at)))
    p['f'], p['alpha'] = f, alpha
    p['F'] = commit(f, gamma_f)
    ch.absorb_point(p['F'])

    u = ch.squeeze('u')
    p['u'] = u
    values = {key: ev(polys[key], u) for key in 'absk'}
    if value_shift:
        for key, shift in value_shift.items():
            values[key] = (values[key] + shift) % Q
    p['values'] = values
    for key in 'absk':
        ch.absorb(values[key])

    beta = ch.squeeze('beta')
    p['beta'] = beta
    combined, gamma = f, gamma_f
    for key, g in (('a', gamma_r), ('b', gamma_b), ('s', 0), ('k', 0)):
        combined = lin((beta, combined), (1, polys[key]))
        gamma = (gamma * beta + g) % Q
    p['p'], p['gamma'] = combined, gamma
    return p


def claim_list(p, constant_claims=False):
    """The order is the book's, and the first claim takes the highest power of alpha."""
    xz = p['x'] * p['z'] % Q
    claims = [('a', xz, p['evals']['a']), ('b', p['x'], p['evals']['b']), ('s', p['x'], p['evals']['s']),
              ('k', p['y'], p['c'])]
    if constant_claims:
        claims = [('a', 0, 0)] + claims[:3] + [('k', 0, 1), claims[3]]
    return claims


def derived_f_at_u(p, claims, alpha, u, values):
    out = 0
    for poly, at, value in claims:
        out = (out * alpha + (values[poly] - value) * inv(u - at)) % Q
    return out


def verify(circuit, p, ch, k_statement=None, constant_claims=False):
    """Returns the list of failed checks. An empty list means the verifier accepts."""
    failed = []
    if k_statement is not None and p['K'] != commit(k_statement):
        failed.append('statement')
    ch.absorb_point(p['K'])
    ch.absorb_point(p['R'])
    z, y = ch.squeeze('z'), ch.squeeze('y')
    ch.absorb_point(p['S'])
    ch.absorb_point(p['B'])
    ch.absorb(p['c'])
    if p['A'] != p['R']:
        failed.append('a-equals-r')
    if p['s'] != circuit.s(y) or commit(p['s']) != p['S']:
        failed.append('wiring')
    if revdot(p['a'], p['b']) != p['c']:
        failed.append('revdot')
    if commit(p['a'], p['gamma_a']) != p['A'] or commit(p['b'], p['gamma_b']) != p['B']:
        failed.append('recommit')
    x = ch.squeeze('x')
    for key in ('a', 's', 'b'):
        ch.absorb(p['evals'][key])
    tx = ev(circuit.t(z), x)
    if p['evals']['b'] != (p['evals']['a'] + p['evals']['s'] + tx) % Q:
        failed.append('tie')
    alpha = ch.squeeze('alpha')
    ch.absorb_point(p['F'])
    u = ch.squeeze('u')
    for key in 'absk':
        ch.absorb(p['values'][key])
    beta = ch.squeeze('beta')
    pp = dict(p, x=x, z=z, y=y)
    claims = claim_list(pp, constant_claims)
    assert all((u - at) % Q for _, at, _ in claims), 'u landed on a claim point'
    f_u = derived_f_at_u(pp, claims, alpha, u, p['values'])
    v, P = f_u, p['F']
    for key, C in (('a', p['A']), ('b', p['B']), ('s', p['S']), ('k', p['K'])):
        v = (v * beta + p['values'][key]) % Q
        P = add(mul(beta, P), C)
    if commit(p['p'], p['gamma']) != P:
        failed.append('p-commitment')
    if ev(p['p'], u) != v:
        failed.append('p-value')
    p['_P'], p['_v'], p['_f_u'] = P, v, f_u
    return failed


def run(r, k, verify_k=None, **kw):
    constant = kw.get('constant_claims', False)
    circuit = kw.pop('circuit', TOY)
    chal = kw.pop('chal', HAND)
    proof = prove(circuit, r, k, Fixed(**chal), **kw)
    return proof, verify(circuit, proof, Fixed(**chal), verify_k, constant)


# ---- Section 2: the starting polynomials ----
z, y, x, alpha, u, beta = (HAND[k] for k in ('z', 'y', 'x', 'alpha', 'u', 'beta'))
s_vec, t_vec = TOY.s(y), TOY.t(z)
dil = [R_HONEST[i] * pow(z, i, Q) % Q for i in range(8)]
b_vec = TOY.right(R_HONEST, z, y)
# The values must match the arithmetization and polynomial-encoding chapters.
assert R_HONEST == [9, 27, 9, 3, 3, 3, 0, 0] and s_vec == [0, 0, 6, 42, 37, 7, 42, 36]
assert t_vec == [0, 0, 0, 0, 0, 0, 32, 24] and b_vec == [9, 6, 16, 30, 20, 8, 31, 17]
assert revdot(R_HONEST, b_vec) == ev(K_POLY, y) == 13
frag['vectors'] = table(['Polynomial', 'Coefficients of $X^0, \\ldots, X^7$', 'Who can compute it'], [
    ['$k(Y)$', vec(K_POLY), 'Both, from the statement'],
    ['$a(X) = r(X)$', vec(R_HONEST), 'Prover'],
    ['$s(X, 7)$', vec(s_vec), 'Both, after $y$'],
    ['$t(X, 5)$', vec(t_vec), 'Both, after $z$'],
    ['$r(5X)$', vec(dil), 'Prover'],
    ['$b(X) = r(5X) + s(X, 7) + t(X, 5)$', vec(b_vec), 'Prover'],
])

# Extra generators
frag['generators'] = table(['Name', 'Point'], [[f'$G_{i + 4}$', f'${show(EXTRA[i])}$'] for i in range(4)])

# ---- The main honest run ----
honest, failed = run(R_HONEST, K_POLY, K_POLY)
assert failed == []
for key in ('K', 'R', 'S', 'B', 'F', '_P'):
    assert honest[key] is not None and honest[key] not in GENS[:8] + [H, U], key
assert len({honest[key] for key in ('K', 'R', 'S', 'B', 'F', '_P')}) == 6
K_pt, R_pt, S_pt, B_pt, F_pt, P_pt = (honest[key] for key in ('K', 'R', 'S', 'B', 'F', '_P'))
R_plain = commit(R_HONEST)
assert R_plain != R_pt and K_pt == mul(30, G[3])

frag['commit-first'] = (f'The public input polynomial is $k(Y) = 30Y^3$, so $K = 30 \\cdot G_3 = {show(K_pt)}$. '
                        f'The trace commitment with the blinding factor $\\gamma_r = {GAMMA_R}$ is '
                        f'$\\bar{{R}} = \\dot{{\\v{{r}}}}{{\\v{{G}}}} + {GAMMA_R} \\cdot H = {show(R_pt)}$. Without the blinding term the same vector would commit to ${show(R_plain)}$.')

c_val = honest['c']
frag['commit-second'] = (f'With the vectors from Section 2, the prover computes $S = {show(S_pt)}$ with no blinding, '
                         f'$\\bar{{B}} = \\dot{{\\v{{b}}}}{{\\v{{G}}}} + {GAMMA_B} \\cdot H = {show(B_pt)}$, and $c = k(7) = 30 \\cdot 7^3 = {c_val}$ modulo 43. '
                         f'It also sets $\\bar{{A}} = \\bar{{R}} = {show(R_pt)}$.')

pairs = [[i, R_HONEST[i], 7 - i, b_vec[7 - i], R_HONEST[i] * b_vec[7 - i] % Q] for i in range(8)]
assert sum(row[4] for row in pairs) % Q == c_val
frag['direct-checks'] = table(['Check', 'Left', 'Right'], [
    ['Recompute $\\v{s}$ from the circuit and $y = 7$', '$' + vec(TOY.s(y)) + '$', 'Sent $\\v{s}$ is identical'],
    ['Commit to the sent $\\v{s}$', f'${show(commit(s_vec))}$', f'$S = {show(S_pt)}$'],
    ['Compare $\\bar{A}$ with the earlier $\\bar{R}$', f'$\\bar{{A}} = {show(R_pt)}$', f'$\\bar{{R}} = {show(R_pt)}$'],
    ['Commit to the sent $\\v{a}$ with $\\gamma_a = ' + str(GAMMA_R) + '$', f'${show(commit(R_HONEST, GAMMA_R))}$', f'$\\bar{{A}} = {show(R_pt)}$'],
    ['Commit to the sent $\\v{b}$ with $\\gamma_b = ' + str(GAMMA_B) + '$', f'${show(commit(b_vec, GAMMA_B))}$', f'$\\bar{{B}} = {show(B_pt)}$'],
    ['$\\revdot{\\v{a}}{\\v{b}}$', f'${revdot(R_HONEST, b_vec)}$', f'$c = {c_val}$'],
])

xz = x * z % Q
ev_a, ev_s, ev_b = honest['evals']['a'], honest['evals']['s'], honest['evals']['b']
t_x = ev(t_vec, x)
assert (ev_a + ev_s + t_x) % Q == ev_b and (xz, ev_a, ev_s, t_x) == (2, 9, 23, 3)
frag['tie'] = (f'The verifier sends $x = {x}$, so $xz = {x} \\cdot {z} = {xz}$ modulo 43. The prover sends $a({xz}) = {ev_a}$, $s({x}, {y}) = {ev_s}$ and $b({x}) = {ev_b}$. '
               f'The verifier computes $t({x}, {z}) = {t_x}$ alone and checks ${ev_a} + {ev_s} + {t_x} = {ev_b}$.')

# Counting a wrong right factor through this one check
tie_passes = [t for t in range(Q) if (ev(R_HONEST, t * z) + ev(s_vec, t) + ev(t_vec, t) - ev(b_vec, t)) % Q == 0]
assert len(tie_passes) == Q

claims = claim_list(honest)
polys = {'a': R_HONEST, 'b': b_vec, 's': s_vec, 'k': K_POLY}
names = {'a': '\\bar{A}', 'b': '\\bar{B}', 's': 'S', 'k': 'K'}
commits = {'a': R_pt, 'b': B_pt, 's': S_pt, 'k': K_pt}
quotients = [divide(polys[n_], at) for n_, at, _ in claims]
rows = []
for i, ((n_, at, value), q) in enumerate(zip(claims, quotients)):
    assert ev(polys[n_], at) == value and lin((1, polys[n_]), (-value, [1])) == lin((-at, q), (1, [0] + q))[:8]
    rows.append([i, f'${names[n_]} = {show(commits[n_])}$', at, value, f'${vec(q)}$'])
frag['claims'] = table(['Claim $i$', 'Commitment', 'Point', 'Value', 'Quotient $q_i$, coefficients of $X^0, \\ldots, X^6$'], rows)

a_pows = [pow(alpha, 3 - i, Q) for i in range(4)]
f_vec = honest['f']
assert f_vec[:7] == lin(*[(a_pows[i], quotients[i]) for i in range(4)]) and honest['F'] == commit(f_vec, GAMMA_F)
assert f_vec[7:] == [0]
frag['alpha'] = (f'With $\\alpha = {alpha}$, the powers are $\\alpha^3 = {a_pows[0]}$, $\\alpha^2 = {a_pows[1]}$, $\\alpha = {a_pows[2]}$ and $1$. '
                 f'The combination $f(X) = {a_pows[0]}\\,q_0 + {a_pows[1]}\\,q_1 + {a_pows[2]}\\,q_2 + q_3$ has coefficients ${vec(f_vec[:7])}$, '
                 f'and with the blinding factor $\\gamma_f = {GAMMA_F}$ its commitment is $\\bar{{F}} = {show(F_pt)}$.')

vals = honest['values']
rows = []
total = 0
for i, (n_, at, value) in enumerate(claims):
    quot = (vals[n_] - value) * inv(u - at) % Q
    term = a_pows[i] * quot % Q
    total = (total + term) % Q
    rows.append([i, vals[n_], value, (u - at) % Q, quot, a_pows[i], term])
assert total == ev(f_vec, u) == honest['_f_u']
frag['derive-f'] = (f'At $u = {u}$ the prover sends $a({u}) = {vals["a"]}$, $b({u}) = {vals["b"]}$, $s({u}, {y}) = {vals["s"]}$ and $k({u}) = {vals["k"]}$. The verifier fills in the next table.\n\n'
                    + table(['$i$', 'Value at $u$', 'Claimed value $y_i$', '$u - x_i$', '$(p_i(u) - y_i)/(u - x_i)$', 'Weight', 'Term'], rows)
                    + f'\n\nThe last column sums to $f({u}) = {total}$, and the prover gets the same number by evaluating $f$.')

b_pows = [pow(beta, 4 - i, Q) for i in range(5)]
order = [('$\\bar{F}$', F_pt, total, GAMMA_F), ('$\\bar{A}$', R_pt, vals['a'], GAMMA_R), ('$\\bar{B}$', B_pt, vals['b'], GAMMA_B), ('$S$', S_pt, vals['s'], 0), ('$K$', K_pt, vals['k'], 0)]
rows = [[nm, b_pows[i], f'${show(pt)}$', val, gm] for i, (nm, pt, val, gm) in enumerate(order)]
v_val = honest['_v']
gamma_val = honest['gamma']
assert v_val == sum(b_pows[i] * order[i][2] for i in range(5)) % Q
assert gamma_val == sum(b_pows[i] * order[i][3] for i in range(5)) % Q
rows.append(['Combined', '', f'$\\bar{{P}} = {show(P_pt)}$', f'$v = {v_val}$', f'$\\gamma = {gamma_val}$'])
frag['beta'] = (f'Take $\\beta = {beta}$. Each input carries its weight into the commitment, the value and the blinding factor.\n\n'
                + table(['Input', 'Weight', 'Commitment', 'Value at $u$', 'Blinding factor'], rows))

p_vec = honest['p']
assert commit(p_vec, gamma_val) == P_pt and ev(p_vec, u) == v_val
frag['reveal'] = (f'The prover sends $\\v{{p}} = {vec(p_vec)}$ and $\\gamma = {gamma_val}$. Committing gives $\\dot{{\\v{{p}}}}{{\\v{{G}}}} + {gamma_val} \\cdot H = {show(commit(p_vec, gamma_val))}$, '
                  f'which equals $\\bar{{P}}$, and evaluating gives $p({u}) = {ev(p_vec, u)}$, which equals $v$.')

frag['run'] = table(['Step', 'Party', 'Value or check'], [
    [0, 'Both', 'Hold the circuit, which gives $s(X, Y)$ and $t(X, Z)$, and the statement, which gives $k(Y) = 30Y^3$'],
    [1, 'Prover sends', f'$K = {show(K_pt)}$, $\\bar{{R}} = {show(R_pt)}$'],
    [2, 'Verifier checks', f'$K$ commits to the $k(Y)$ of the statement'],
    [3, 'Verifier sends', f'$z = {z}$, $y = {y}$'],
    [4, 'Prover sends', f'$S = {show(S_pt)}$, $\\bar{{A}} = {show(R_pt)}$, $\\bar{{B}} = {show(B_pt)}$, $c = {c_val}$'],
    [5, 'Prover sends', f'$\\v{{s}}$, $\\v{{a}}$, $\\v{{b}}$, $\\gamma_a = {GAMMA_R}$, $\\gamma_b = {GAMMA_B}$'],
    [6, 'Verifier checks', f'Recomputes $\\v{{s}}$ and $S$, checks $\\bar{{A}} = \\bar{{R}}$, recomputes $\\bar{{A}}$ and $\\bar{{B}}$, and finds $\\revdot{{\\v{{a}}}}{{\\v{{b}}}} = {c_val} = c$'],
    [7, 'Verifier sends', f'$x = {x}$'],
    [8, 'Prover sends', f'$a({xz}) = {ev_a}$, $s({x}, {y}) = {ev_s}$, $b({x}) = {ev_b}$'],
    [9, 'Verifier checks', f'${ev_a} + {ev_s} + t({x}, {z}) = {ev_a} + {ev_s} + {t_x} = {ev_b}$'],
    [10, 'Verifier sends', f'$\\alpha = {alpha}$'],
    [11, 'Prover sends', f'$\\bar{{F}} = {show(F_pt)}$'],
    [12, 'Verifier sends', f'$u = {u}$'],
    [13, 'Prover sends', f'Values at $u$: ${vals["a"]},\\ {vals["b"]},\\ {vals["s"]},\\ {vals["k"]}$'],
    [14, 'Verifier sends', f'$\\beta = {beta}$'],
    [15, 'Verifier derives', f'$f({u}) = {total}$, $\\bar{{P}} = {show(P_pt)}$, $v = {v_val}$'],
    [16, 'Prover sends', f'$\\v{{p}} = {vec(p_vec)}$, $\\gamma = {gamma_val}$'],
    [17, 'Verifier checks', f'$\\dot{{\\v{{p}}}}{{\\v{{G}}}} + {gamma_val} \\cdot H = {show(P_pt)}$ and $p({u}) = {v_val}$'],
])

# Completeness: the honest prover passes at every challenge the protocol allows.
passes = runs = 0
for z_ in range(Q):
    for y_ in range(Q):
        for x_ in (9, 21):
            points = {x_ * z_ % Q, x_, y_}
            u_ = next(t for t in (17, 18, 19, 20) if t not in points)
            chal = dict(z=z_, y=y_, x=x_, alpha=11, u=u_, beta=23)
            _, f_ = run(R_HONEST, K_POLY, K_POLY, chal=chal)
            runs += 1
            passes += not f_
assert passes == runs == 2 * Q * Q
frag['honest-count'] = (f'We ran the whole protocol for all $43^2 = {Q * Q}$ pairs $(z, y)$ at two values of $x$, moving $u$ whenever it would land on a claim point. The verifier accepted all {runs} runs.')

# ---- Fiat-Shamir ----
T, RATE, FULL, PARTIAL = 3, 2, 8, 8
RC = [[int.from_bytes(hashlib.sha256(f'toy-poseidon-{rd}-{i}'.encode()).digest(), 'big') % Q for i in range(T)] for rd in range(FULL + PARTIAL)]
MDS = [[pow(a_ + b_, -1, Q) for b_ in (3, 4, 5)] for a_ in (0, 1, 2)]
SCHEDULE = [T] * (FULL // 2) + [1] * PARTIAL + [T] * (FULL // 2)


def permutation(state):
    for rd, elems in enumerate(SCHEDULE):
        added = [(v + RC[rd][i]) % Q for i, v in enumerate(state)]
        boxed = [pow(v, 5, Q) if i < elems else v for i, v in enumerate(added)]
        state = [sum(MDS[i][j] * boxed[j] for j in range(T)) % Q for i in range(T)]
    return state


class Transcript:
    """The toy sponge of the Statements and Challenges chapter, with logging."""

    def __init__(self, tag):
        self.state, self.pending, self.values, self.squeezing = [0] * T, [], [], False
        self.log, self.current = [], []
        self._put(len(tag))
        for e in tag:
            self._put(e)

    def _permute(self):
        for i, v in enumerate(self.pending):
            self.state[i] = (self.state[i] + v) % Q
        self.pending = []
        self.state = permutation(self.state)

    def _put(self, v):
        if self.squeezing:
            self.squeezing, self.values = False, []
        if len(self.pending) == RATE:
            self._permute()
        self.pending.append(v % Q)

    def absorb_point(self, pt):
        assert pt is not None
        self._put(pt[0])
        self._put(pt[1])
        self.current.append(f'${show(pt)}$')

    def absorb(self, v):
        self._put(v)
        self.current.append(f'${v % Q}$')

    def squeeze(self, name):
        if not self.squeezing:
            self._permute()
            self.squeezing = True
            self.values = self.state[:RATE][::-1]
        if not self.values:
            self._permute()
            self.values = self.state[:RATE][::-1]
        out = self.values.pop()
        self.log.append((name, ', '.join(self.current), out))
        self.current = []
        return out


TAG = [7, 29]
ptr = Transcript(TAG)
fs_proof = prove(TOY, R_HONEST, K_POLY, ptr)
vtr = Transcript(TAG)
fs_failed = verify(TOY, fs_proof, vtr, K_POLY)
assert fs_failed == [] and [e[2] for e in ptr.log] == [e[2] for e in vtr.log]
fs_vals = {e[0]: e[2] for e in ptr.log}
assert all(fs_vals[k_] for k_ in fs_vals) and len(set(fs_vals.values())) == 6
assert len({fs_proof[k_] for k_ in ('K', 'R', 'S', 'B', 'F', '_P')}) == 6
syms = {'z': 'z', 'y': 'y', 'x': 'x', 'alpha': '\\alpha', 'u': 'u', 'beta': '\\beta'}
contents = {'z': '$K$, $\\bar{R}$', 'x': '$S$, $\\bar{B}$, $c$', 'alpha': '$a(xz)$, $s(x, y)$, $b(x)$', 'u': '$\\bar{F}$', 'beta': 'Values at $u$'}
rows = []
for name, absorbed, value in ptr.log:
    rows.append([contents.get(name, 'Nothing new'), absorbed if absorbed else '', f'${syms[name]} = {value}$'])
# Attacking the transcript: changing the first message moves every later challenge.
other = Transcript(TAG)
prove(TOY, R_HONEST, K_POLY, other, gamma_r=GAMMA_R + 1)
moved = [e[2] for e in other.log]
assert moved != [e[2] for e in ptr.log]
frag['fs-run'] = (table(['Messages absorbed', 'Values', 'Challenge squeezed'], rows)
                  + f'\n\nThe verifier replays the same absorptions from the proof, obtains the same six challenges, and accepts. Changing only the blinding factor of $\\bar{{R}}$ from ${GAMMA_R}$ to ${GAMMA_R + 1}$ changes the first absorbed message, and the six challenges become ${vec(moved)}$.')

# ---- Proof structure ----
frag['proof-parts'] = table(['Part', 'Item', 'Value in our run'], [
    ['Instance', '$K, \\bar{R}, S, \\bar{A}, \\bar{B}$', f'${show(K_pt)}$, ${show(R_pt)}$, ${show(S_pt)}$, ${show(R_pt)}$, ${show(B_pt)}$'],
    ['Instance', '$c$', c_val],
    ['Instance', '$a(xz), s(x, y), b(x)$', f'${ev_a},\\ {ev_s},\\ {ev_b}$'],
    ['Instance', '$\\bar{P}, u, v$', f'${show(P_pt)}$, ${u}$, ${v_val}$'],
    ['Witness', '$\\v{s}$', f'${vec(s_vec)}$'],
    ['Witness', '$\\v{a}$', f'${vec(R_HONEST)}$'],
    ['Witness', '$\\v{b}$', f'${vec(b_vec)}$'],
    ['Witness', '$\\gamma_a, \\gamma_b$', f'${GAMMA_R},\\ {GAMMA_B}$'],
    ['Witness', '$\\bar{F}$', f'${show(F_pt)}$'],
    ['Witness', 'Values at $u$', f'${vals["a"]},\\ {vals["b"]},\\ {vals["s"]},\\ {vals["k"]}$'],
    ['Witness', '$\\v{p}, \\gamma$', f'${vec(p_vec)}$, ${gamma_val}$'],
])
SIZE, BYTES = 2 ** 13, 32
inst_values = 6 + 6
wit_values = 4 * SIZE + 2 + 1 + 4 + 1
frag['proof-size'] = (f'Take $4n = 2^{{13}}$ with 32-byte values, the size the [Ragu Book\'s analysis](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md?plain=1#L38-L43) gives for its preferred threshold. '
                      f'The instance holds 6 points and 6 scalars, or ${inst_values * BYTES:,}$ bytes. The witness holds four vectors of ${SIZE:,}$ entries and 8 more values, or ${wit_values * BYTES:,}$ bytes, which is about 1 MB.')

# ---- Hiding ----
assert R_HONEST[3] == 3
matches_plain = [t for t in range(Q) if commit(TOY.trace(*toy_witness(t))) == R_plain]
assert matches_plain == [3]
fits = [[g for g in range(Q) if commit(TOY.trace(*toy_witness(t)), g) == R_pt] for t in range(Q)]
assert all(len(g) == 1 for g in fits)
frag['hiding-guess'] = (f'An observer who holds the unblinded commitment ${show(R_plain)}$ can build the trace for every candidate input and compare. Trying all 43 inputs gives exactly one match, $x = {matches_plain[0]}$. '
                        f'An observer who holds only $\\bar{{R}} = {show(R_pt)}$ gets no such answer, because each of the 43 candidate traces has exactly one blinding factor that fits this point.')
frag['hiding-read'] = (f'In our run the proof contains $\\v{{a}} = {vec(R_HONEST)}$. The layout from the arithmetization chapter puts the wire $a_0$ at position 3, so anyone can read the secret input $x = {R_HONEST[3]}$ straight from the proof.')

# ---- The constant wire: n = 3 with a system gate ----
ALPHA_WIRE = 11
ONE = Circuit(3, [
    {('d', 0): 1},
    {('c', 2): 1, ('a', 1): 1, ('d', 0): 5},
    {('a', 1): 1, ('b', 1): -1},
    {('a', 2): 1, ('c', 1): -1},
    {('a', 1): -1, ('b', 2): 1},
])
K_ONE = [1, 35] + [0] * 10


def one_trace(x_, d0=1):
    w1 = x_ * x_ % Q
    return ONE.trace([ALPHA_WIRE, x_, w1], [0, x_, x_], [0, w1, w1 * x_ % Q], [d0, 0, 0])


assert len(GENS) == 12  # twelve generators cover 4n = 12
R_ONE = one_trace(3)
assert ev(R_ONE, 0) == 0 and R_ONE[11] == 1
# s(X, 0) is the single term X^0, as the Ragu Book's local wiring chapter states.
assert ONE.s(0) == [1] + [0] * 11
for z_ in range(Q):
    for y_ in range(Q):
        assert revdot(R_ONE, ONE.right(R_ONE, z_, y_)) == ev(K_ONE, y_)
one_proof, one_failed = run(R_ONE, K_ONE, K_ONE, circuit=ONE, constant_claims=True)
assert one_failed == []
assert None not in [one_proof[k_] for k_ in ('K', 'R', 'S', 'B', 'F', '_P')]
one_claims = claim_list(one_proof, True)
assert len(one_claims) == 6 and one_claims[0][2] == 0 and one_claims[4][2] == 1
frag['one-trace'] = (f'Gate 0 holds $a_0 = {ALPHA_WIRE}$, $b_0 = 0$, $c_0 = 0$ and $d_0 = 1$, and gates 1 and 2 are the two gates from the arithmetization chapter. The first constraint says $d_0 = k_0$, and the second becomes $c_2 + a_1 + 5 d_0 = k_1$, so the constant 5 is now a multiple of the wire. '
                     f'The instance is $k(Y) = 1 + 35Y$, and the trace is $\\v{{r}} = {vec(R_ONE)}$. Its constant coefficient is $r(0) = c_0 = {ev(R_ONE, 0)}$, and its top coefficient is $d_0 = {R_ONE[11]}$. Checking all {Q * Q} challenge pairs confirms that the consolidated equation holds at every one.')
frag['one-claims'] = table(['Claim $i$', 'Polynomial', 'Point', 'Value', 'Weight'], [
    [i, f'${names[n_]}$', at, value, pow(alpha, 5 - i, Q)] for i, (n_, at, value) in enumerate(one_claims)])
frag['one-result'] = (f'With the same challenges as before, the prover sends $\\bar{{F}} = {show(one_proof["F"])}$ and four values at $u$, namely ${one_proof["values"]["a"]},\\ {one_proof["values"]["b"]},\\ {one_proof["values"]["s"]},\\ {one_proof["values"]["k"]}$. '
                      f'The verifier derives $\\bar{{P}} = {show(one_proof["_P"])}$ and $v = {one_proof["_v"]}$, the revealed $\\v{{p}}$ matches both, and the proof is accepted.')

# A prover who sets k_0 = 2 and d_0 = 2 turns the constant 5 into 10.
K_TWO = [2, 35] + [0] * 10
R_TWO = one_trace(4, d0=2)
assert (21 + 4 + 5 * 2) % Q == 35 and (4 ** 3 + 4 + 5) % Q == 30
assert all(revdot(R_TWO, ONE.right(R_TWO, z_, y_)) == ev(K_TWO, y_) for z_ in range(Q) for y_ in range(Q))
two_proof, two_failed = run(R_TWO, K_TWO, None, circuit=ONE, constant_claims=True)
assert two_failed and set(two_failed) <= {'p-value', 'p-commitment'}
beta_pass = 0
for b_ in range(Q):
    chal = dict(HAND, beta=b_)
    _, f_ = run(R_TWO, K_TWO, None, circuit=ONE, constant_claims=True, chal=chal)
    beta_pass += not f_
assert beta_pass == 1  # only beta = 0, which removes f from p
without_claim_proof, without_claim_failed = run(R_TWO, K_TWO, None, circuit=ONE, constant_claims=False)
assert without_claim_failed == []
assert all((ev(K_TWO, y_) - ev(K_ONE, y_)) % Q == 1 for y_ in range(Q))
frag['one-attack'] = (f'Take $x = 4$, which is false for the real statement, since $4^3 + 4 + 5 = 30$ modulo 43. A cheater sets $d_0 = 2$ and commits to $k\'(Y) = 2 + 35Y$. Then $c_2 + a_1 + 5 d_0 = 21 + 4 + 10 = 35$, so every gate and constraint holds, and the consolidated equation holds at all {Q * Q} challenge pairs. '
                      f'If the two constant claims are dropped from the list, the verifier accepts this proof. With the claims in the list, the false claim $k\'(0) = 1$ remains. Keeping the other challenges fixed, the verifier rejects for {Q - beta_pass} of the 43 values of $\\beta$, and it accepts only at $\\beta = 0$, which removes $f$ from $p$.')

# Back to the main circuit's size for the remaining sections.
# ---- Cheating ----
false_c = ev(K_POLY, y)
true_rd = revdot(R_FALSE, TOY.right(R_FALSE, z, y))
assert true_rd == 18 and false_c == 13
gap = (false_c - true_rd) % Q
lucky = sum(revdot(R_FALSE, TOY.right(R_FALSE, z_, y_)) == ev(K_POLY, y_) for z_ in range(Q) for y_ in range(Q))
assert lucky == 43
p_false, f_false = run(R_FALSE, K_POLY, K_POLY)
assert f_false == ['revdot', 'p-value', 'p-commitment'] or 'revdot' in f_false
frag['cheat-honest'] = (f'Take the false witness with $x = 4$, so $\\v{{r}}\' = {vec(R_FALSE)}$, and let the prover follow every instruction. At $z = {z}$ and $y = {y}$ the verifier computes $\\revdot{{\\v{{a}}}}{{\\v{{b}}}} = {true_rd}$, while $k({y}) = {false_c}$, so the revdot check fails. '
                        f'Counting all pairs of challenges finds {lucky} of the {Q * Q} where the two numbers happen to agree, the same count as in the [arithmetization chapter](./arithmetization.md#why-a-false-witness-fails).')


def u_for(points):
    return next(t for t in (17, 18, 19, 20, 22, 25) if t not in points)


def run_at_x(x_, **kw):
    chal = dict(HAND, x=x_, u=u_for({x_ * z % Q, x_, y}))
    return run(R_FALSE, K_POLY, K_POLY, chal=chal, **kw)


# One coefficient changed: position 4 pairs with a_0 at position 3 of the trace.
naive = [0] * 8
naive[4] = gap * inv(R_FALSE[3]) % Q
assert revdot(R_FALSE, lin((1, TOY.right(R_FALSE, z, y)), (1, naive))) == false_c
naive_pass = [x_ for x_ in range(Q) if not run_at_x(x_, b_shift=naive)[1]]
assert naive_pass == [0]
frag['cheat-naive'] = (f'The revdot check only looks at $\\v{{b}}$, so the cheater can replace it with $\\v{{b}}\' = \\v{{b}} + \\v{{d}}$, where $\\v{{d}}$ is any vector with $\\revdot{{\\v{{r}}\'}}{{\\v{{d}}}} = {false_c} - {true_rd} = {gap}$. The most direct choice puts one entry at position 4, the partner of $r\'_3 = {R_FALSE[3]}$, giving $d_4 = {naive[4]}$. The revdot check now passes. '
                       f'The check $b(x) = a(xz) + s(x, y) + t(x, z)$ then compares two polynomials that differ by $D(X) = {naive[4]}X^4$, which has only the root $0$. Running the whole protocol at all 43 values of $x$ gives one acceptance, at $x = 0$.')

# The best polynomial D has degree 7 and seven distinct roots.
roots = [1, 2, 3, 4, 5, 6, 7]
D = [1]
for rho in roots:
    D = lin((1, [0] + D), (-rho, D + [0]))
assert len(D) == 8
scale = revdot(R_FALSE, D)
assert scale
D = [e * gap * inv(scale) % Q for e in D]
assert revdot(R_FALSE, lin((1, TOY.right(R_FALSE, z, y)), (1, D))) == false_c
best_pass = [x_ for x_ in range(Q) if not run_at_x(x_, b_shift=D)[1]]
assert best_pass == roots
frag['cheat-best'] = (f'The cheater does better by spreading the difference over all eight coefficients. Let $D(X)$ be a multiple of $(X-1)(X-2)\\cdots(X-7)$, scaled so that $\\revdot{{\\v{{r}}\'}}{{\\v{{d}}}} = {gap}$, which gives $D(X) = {poly_str(D)}$. Running the whole protocol at all 43 values of $x$ gives acceptance at exactly $x \\in \\{{1, \\ldots, 7\\}}$, which is 7 out of 43. '
                      f'A polynomial with 8 coefficients has at most 7 roots, so no choice of $D$ can do better, and for $4n = 2^{{13}}$ on a field of about $2^{{254}}$ elements the same limit gives a probability below $2^{{-240}}$.')
assert 2 ** 13 < 2 ** 14

# A lie about the claimed value of b(x), to pass the tie check at a point where D does not vanish.
assert x not in roots
tie_gap = ev(D, x)
lie_proof, lie_failed = run(R_FALSE, K_POLY, K_POLY, b_shift=D, eval_shift=-tie_gap)
assert 'tie' not in lie_failed and 'revdot' not in lie_failed and 'p-value' in lie_failed
lie_beta = sum(not run(R_FALSE, K_POLY, K_POLY, chal=dict(HAND, beta=b_), b_shift=D, eval_shift=-tie_gap)[1] for b_ in range(Q))
assert lie_beta == 1
frag['cheat-lie'] = (f'At $x = {x}$ this polynomial is not zero, since $D({x}) = {tie_gap}$. The cheater can still pass the check by sending $b({x}) = {lie_proof["evals"]["b"]}$ in place of the true ${(lie_proof["evals"]["b"] + tie_gap) % Q}$, but that value is then a false evaluation claim about $\\bar{{B}}$. '
                     f'The batching of the previous chapter catches it. Running all 43 values of $\\beta$ with honest values at $u$ gives one acceptance, at $\\beta = 0$, where the derived $f(u)$ drops out of $v$.')

# Knowing (z, y) before committing to r: one entry can be solved for.
solved = None
for pos in range(8):
    for delta in range(1, Q):
        trial = list(R_FALSE)
        trial[pos] = (trial[pos] + delta) % Q
        if revdot(trial, TOY.right(trial, z, y)) == false_c:
            solved = (pos, delta, trial)
            break
    if solved:
        break
assert solved
early_proof, early_failed = run(solved[2], K_POLY, K_POLY)
assert early_failed == []
assert solved[2][3] * solved[2][4] % Q != solved[2][0]  # gate 0 of the solved vector fails
early_count = sum(revdot(solved[2], TOY.right(solved[2], z_, y_)) == ev(K_POLY, y_) for z_ in range(Q) for y_ in range(Q))
assert early_count < 200
frag['cheat-early'] = (f'Suppose the prover knows $z = {z}$ and $y = {y}$ before it sends $\\bar{{R}}$. Starting from the false trace, it changes entry {solved[0]} by ${solved[1]}$ to get $\\v{{r}}\'\' = {vec(solved[2])}$, a value found by solving the one quadratic equation. This vector is not a valid trace, because its gates do not hold. '
                       f'It still satisfies the consolidated equation at this one pair, and the verifier accepts the whole proof. The same vector, committed honestly before the challenges, passes the revdot check at only {early_count} of the {Q * Q} pairs.')

# Knowing a generator relation: open the committed point to a solved vector afterward.
logs = [log(g, G[0]) for g in GENS[:8]]
assert all(logs)
open_solved = None
for i in range(8):
    for j in range(i + 1, 8):
        for delta in range(1, Q):
            trial = list(R_FALSE)
            other_delta = -delta * logs[i] * inv(logs[j]) % Q
            trial[i] = (trial[i] + delta) % Q
            trial[j] = (trial[j] + other_delta) % Q
            if revdot(trial, TOY.right(trial, z, y)) == false_c:
                open_solved = (i, j, delta, other_delta, trial)
                break
        if open_solved:
            break
    if open_solved:
        break
assert open_solved
R_committed = commit(R_FALSE, GAMMA_R)
assert commit(open_solved[4], GAMMA_R) == R_committed
open_proof, open_failed = run(open_solved[4], K_POLY, K_POLY, committed_r=R_committed)
assert open_failed == []
frag['cheat-binding'] = (f'Suppose the prover commits to the false trace first, so $\\bar{{R}} = {show(R_committed)}$, and only then learns $z$ and $y$. Because it knows the discrete logs of the toy generators, it can change entries {open_solved[0]} and {open_solved[1]} by ${open_solved[2]}$ and ${open_solved[3]}$ without moving the commitment. One such change gives $\\v{{r}}\'\' = {vec(open_solved[4])}$, which commits to the same point and satisfies the consolidated equation at this pair. The verifier accepts, because each of its recomputations finds what it expects.')

# Omitting the statement comparison: k_3 = 25 makes x = 4 pass everywhere.
K_FALSE = [0, 0, 0, 25, 0, 0, 0, 0]
assert all(revdot(R_FALSE, TOY.right(R_FALSE, z_, y_)) == ev(K_FALSE, y_) for z_ in range(Q) for y_ in range(Q))
tied_proof, tied_none = run(R_FALSE, K_FALSE, None)
_, tied_checked = run(R_FALSE, K_FALSE, K_POLY)
assert tied_none == [] and tied_checked == ['statement']
frag['statement-tie'] = (f'A prover with $x = 4$ can commit to $k\'(Y) = 25Y^3$ instead of $30Y^3$, which is the instance of the statement $x^3 + x + 5 = 30$. Its $K = {show(tied_proof["K"])}$ differs from the correct ${show(K_pt)}$, while the claims about $K$ are all true, and every other check passes. The proof is valid for $30$ and says nothing about $35$, so a verifier that accepts $K$ without comparing it would be misled.')

# ---- Costs ----
SIZE = 2 ** 13
costs = [
    ['Compute $\\v{s}$ from the circuit', 'One term per wire in each constraint', 'Linear'],
    ['Recompute $S$, $\\bar{A}$, $\\bar{B}$', f'3 MSMs of size $4n$, or ${3 * SIZE:,}$ scalar multiplications', 'Linear'],
    ['Compute $\\revdot{\\v{a}}{\\v{b}}$', f'$4n$, or ${SIZE:,}$ field multiplications', 'Linear'],
    ['Compute $t(x, z)$', 'Two geometric sums, using repeated squaring', 'Logarithmic'],
    ['Compute $k(y)$ or compare $K$', 'One term per public input', 'Size of the instance'],
    ['Derive $f(u)$', 'One inverse and a few multiplications per claim', 'Constant'],
    ['Compute $\\bar{P}$ and $v$', 'Five scalar multiplications and field operations', 'Constant'],
    ['Recompute $\\bar{P}$ from $\\v{p}$', f'1 MSM of size $4n$, or ${SIZE:,}$ scalar multiplications', 'Linear'],
    ['Evaluate $p(u)$', f'$4n$, or ${SIZE:,}$ field multiplications', 'Linear'],
]
frag['costs'] = table(['Verifier step', 'Work', 'Growth'], costs)

# The closed form for t(x, z).
n_ = 2
closed = (pow(x, 3 * n_, Q) * pow(z, n_, Q) * sum(pow(x * z, k_, Q) for k_ in range(n_))
          + pow(x, 3 * n_, Q) * pow(z, 3 * n_ - 1, Q) * sum(pow(x * inv(z), k_, Q) for k_ in range(n_))) % Q
assert -closed % Q == t_x
frag['t-closed'] = (f'At $x = {x}$, $z = {z}$ and $n = 2$, the first sum is $1 + xz = {(1 + x * z) % Q}$ and the second is $1 + x/z = {(1 + x * inv(z)) % Q}$. The formula gives $-t = {closed}$, so $t({x}, {z}) = {t_x}$, which matches the direct sum over the entries of $\\v{{t}}$.')

# One batched check replaces the four recomputations.
rho = 8
batch_polys = [(R_HONEST, GAMMA_R, R_pt), (b_vec, GAMMA_B, B_pt), (s_vec, 0, S_pt), (p_vec, gamma_val, P_pt)]
fold, fold_gamma, fold_pt = [0] * 8, 0, None
for poly, g, pt in batch_polys:
    fold = lin((rho, fold), (1, poly))
    fold_gamma = (rho * fold_gamma + g) % Q
    fold_pt = add(mul(rho, fold_pt) if fold_pt else None, pt)
assert commit(fold, fold_gamma) == fold_pt and fold_pt not in (R_pt, B_pt, S_pt, P_pt, K_pt, F_pt) and fold_pt is not None
frag['recommit-batch'] = (f'For our run take $\\rho = {rho}$ and the four vectors $\\v{{a}}, \\v{{b}}, \\v{{s}}, \\v{{p}}$. The combined vector is ${vec(fold)}$ with blinding factor ${fold_gamma}$, and it commits to ${show(fold_pt)}$, the same point as $\\rho^3 \\cdot \\bar{{A}} + \\rho^2 \\cdot \\bar{{B}} + \\rho \\cdot S + \\bar{{P}}$. One MSM of size $4n$ did the work of four.')

# ---- Short form: split, batch, IPA ----
rx = R_HONEST
fx = b_vec
full = [0] * 15
for i, e in enumerate(rx):
    for j, g in enumerate(fx):
        full[i + j] = (full[i + j] + e * g) % Q
assert full[7] == 13
c1 = full[:8][::-1]
c2 = full[8:] + [0]
assert ev(c1, 0) == 13
C_R, C_1, C_2 = commit(rx), commit(c1), commit(c2)
xinv = inv(x)
ev_r_x, ev_r_xz, ev_c1_inv, ev_c1_0, ev_c2 = ev(rx, x), ev(rx, xz), ev(c1, xinv), ev(c1, 0), ev(c2, x)
lhs = ev_r_x * (ev_r_xz + ev(s_vec, x) + ev(t_vec, x)) % Q
rhs = (pow(x, 7, Q) * ev_c1_inv + pow(x, 8, Q) * ev_c2) % Q
assert lhs == rhs and ev_c1_0 == ev(K_POLY, y)
assert (ev_r_x, ev_r_xz, ev_c1_inv, ev_c2) == (5, 9, 6, 30)
sclaims = [('r', x, ev_r_x), ('r', xz, ev_r_xz), ('c1', 0, ev_c1_0), ('c1', xinv, ev_c1_inv), ('c2', x, ev_c2)]
spolys = {'r': rx, 'c1': c1, 'c2': c2}
scommit = {'r': C_R, 'c1': C_1, 'c2': C_2}
sf = [0] * 8
for name, at, _ in sclaims:
    sf = lin((alpha, sf), (1, divide(spolys[name], at)))
assert all(ev(spolys[name], at) == value for name, at, value in sclaims)
C_F = commit(sf)
svals = {name: ev(spolys[name], u) for name in spolys}
sf_u = 0
for name, at, value in sclaims:
    sf_u = (sf_u * alpha + (svals[name] - value) * inv(u - at)) % Q
assert sf_u == ev(sf, u)
sv, sP, sp = sf_u, C_F, sf
for name in ('r', 'c1', 'c2'):
    sv = (sv * beta + svals[name]) % Q
    sP = add(mul(beta, sP), scommit[name])
    sp = lin((beta, sp), (1, spolys[name]))
assert commit(sp) == sP and ev(sp, u) == sv
for pt in (C_R, C_1, C_2, C_F, sP):
    assert pt is not None and pt not in GENS[:8] + [H, U]
frag['short-commit'] = table(['Step', 'Party', 'Value or check'], [
    [1, 'Prover sends', f'$R = {show(C_R)}$'],
    [2, 'Verifier sends', f'$z = {z}$, $y = {y}$'],
    [3, 'Prover sends', f'$C_1 = {show(C_1)}$ and $C_2 = {show(C_2)}$, the commitments to $c_1(X)$ and $c_2(X)$'],
    [4, 'Verifier sends', f'$x = {x}$, so $xz = {xz}$ and $x^{{-1}} = {xinv}$'],
    [5, 'Prover sends', f'$r({x}) = {ev_r_x}$, $r({xz}) = {ev_r_xz}$, $c_1(0) = {ev_c1_0}$, $c_1({xinv}) = {ev_c1_inv}$, $c_2({x}) = {ev_c2}$'],
    [6, 'Verifier computes', f'$s({x}, {y}) = {ev(s_vec, x)}$, $t({x}, {z}) = {t_x}$, $k({y}) = {ev(K_POLY, y)}$'],
    [7, 'Verifier checks', f'The split, ${ev_r_x} \\cdot ({ev_r_xz} + {ev(s_vec, x)} + {t_x}) = {lhs}$ and ${pow(x, 7, Q)} \\cdot {ev_c1_inv} + {pow(x, 8, Q)} \\cdot {ev_c2} = {rhs}$, and the target, $c_1(0) = {ev_c1_0} = k({y})$'],
    [8, 'Verifier sends', f'$\\alpha = {alpha}$'],
    [9, 'Prover sends', f'$F = {show(C_F)}$, the commitment to the combined quotient'],
    [10, 'Verifier sends', f'$u = {u}$'],
    [11, 'Prover sends', f'Values at $u$: $r({u}) = {svals["r"]}$, $c_1({u}) = {svals["c1"]}$, $c_2({u}) = {svals["c2"]}$'],
    [12, 'Verifier sends', f'$\\beta = {beta}$'],
    [13, 'Verifier derives', f'$f({u}) = {sf_u}$, $P = {show(sP)}$, $v = {sv}$'],
])


# The symmetric inner product argument from chapter 07, with k = 3.
UCHAL = [15, 10, 3]


def ip(a_, b_):
    return sum(e * g for e, g in zip(a_, b_)) % Q


def ipa_run(vector, at, statement, chals):
    a_, b_, g_ = list(vector), [pow(at, i, Q) for i in range(len(vector))], list(GENS[:len(vector)])
    Pt = statement
    rows_, ls, rs = [], [], []
    for j, c_ in enumerate(chals, 1):
        h = len(a_) // 2
        L = add(msm(a_[h:], g_[:h]), mul(ip(a_[h:], b_[:h]), U))
        R = add(msm(a_[:h], g_[h:]), mul(ip(a_[:h], b_[h:]), U))
        ci = inv(c_)
        a_ = [(c_ * a_[i] + ci * a_[i + h]) % Q for i in range(h)]
        b_ = [(ci * b_[i] + c_ * b_[i + h]) % Q for i in range(h)]
        g_ = [add(mul(ci, g_[i]), mul(c_, g_[i + h])) for i in range(h)]
        Pt = add(add(Pt, mul(ci * ci, L)), mul(c_ * c_, R))
        ls.append(L)
        rs.append(R)
        rows_.append([j, f'${show(L)}$', f'${show(R)}$', c_, f'${show(Pt)}$', f'${vec(a_)}$'])
        assert L is not None and R is not None and Pt == add(msm(a_, g_), mul(ip(a_, b_), U))
    return Pt, a_[0], b_[0], g_[0], rows_, ls, rs


statement = add(sP, mul(sv, U))
assert statement == add(commit(sp), mul(ev(sp, u), U))
final_pt, a_hat, b_hat, G_hat, ipa_rows, ls, rs = ipa_run(sp, u, statement, UCHAL)


def g_coeffs(chals):
    k_ = len(chals)
    out = [1]
    for j, c_ in enumerate(chals, 1):
        factor = [0] * (2 ** (k_ - j) + 1)
        factor[0], factor[2 ** (k_ - j)] = inv(c_), c_
        new = [0] * (len(out) + len(factor) - 1)
        for i, e in enumerate(out):
            for m, g in enumerate(factor):
                new[i + m] = (new[i + m] + e * g) % Q
        out = new
    return out


gc = g_coeffs(UCHAL)
assert msm(gc, GENS) == G_hat and ev(gc, u) == b_hat and len(gc) == 8
assert add(mul(a_hat, G_hat), mul(a_hat * b_hat, U)) == final_pt
lhs_pt = statement
for c_, L, R in zip(UCHAL, ls, rs):
    lhs_pt = add(add(lhs_pt, mul(inv(c_) ** 2, L)), mul(c_ * c_, R))
assert lhs_pt == final_pt
frag['short-p'] = (f'The polynomial behind $P$ has coefficients $\\v{{p}} = {vec(sp)}$. The statement point for the argument is $P + v \\cdot U = {show(statement)}$.')
frag['short-ipa'] = table(['Round $j$', '$L_j$', '$R_j$', '$u_j$', 'Folded point', 'Folded $\\v{p}$'], ipa_rows)
frag['short-final'] = (f'The prover sends the final scalar $\\hat{{a}} = {a_hat}$. The verifier computes the coefficients of $g(X)$ from the three challenges, which are ${vec(gc)}$, then $\\hat{{b}} = g({u}) = {b_hat}$ and $\\hat{{G}} = {show(G_hat)}$ from one MSM over all eight generators. '
                       f'The left side of the check is ${show(lhs_pt)}$, and $\\hat{{a}} \\cdot (\\hat{{G}} + \\hat{{b}} \\cdot U) = {show(add(mul(a_hat, G_hat), mul(a_hat * b_hat, U)))}$, so the verifier accepts.')
# Size: R, C1, C2, F; 5 evaluations, 3 values; 2k IPA points; 1 scalar.
k_big = 13
short_points, short_scalars = 4 + 2 * k_big, 5 + 3 + 1
short_bytes = (short_points + short_scalars) * BYTES
frag['short-size'] = (f'For $4n = 2^{{13}}$ this proof holds ${short_points}$ points and ${short_scalars}$ scalars, or ${short_bytes:,}$ bytes at 32 bytes each, in place of about 1 MB.')
assert short_bytes < 2000

# Replacing only the reveal of p with an argument leaves the other three vectors.
with_ipa = (3 * SIZE + 7 + 2 * k_big + 1) * BYTES
assert with_ipa > 700000
frag['reveal-tradeoff'] = (f'For $4n = 2^{{13}}$, the witness part is ${wit_values * BYTES:,}$ bytes with $\\v{{p}}$ revealed. Replacing the reveal with an argument of $26$ points and one scalar brings it to ${with_ipa:,}$ bytes, because the vectors $\\v{{s}}$, $\\v{{a}}$ and $\\v{{b}}$ remain.')

# Evaluating s(x, y) touches every nonzero wiring coefficient.
terms = []
for j, row in enumerate(TOY.rows):
    for (kind, i), coeff in row.items():
        pos = {'a': 4 + i, 'b': 3 - i, 'c': 7 - i}[kind]
        terms.append(coeff * pow(y, j, Q) * pow(x, pos, Q) % Q)
assert sum(terms) % Q == ev(s_vec, x) == 23 and len(terms) == 8
frag['s-terms'] = (f'Our circuit has {len(terms)} nonzero wiring coefficients across its four constraints. Each contributes one term $\\text{{coefficient}} \\cdot y^j x^{{\\text{{position}}}}$, and at $x = {x}$, $y = {y}$ those terms are ${vec(terms)}$, which sum to $s({x}, {y}) = {ev(s_vec, x)}$. A circuit with more wiring has more terms, and no term can be skipped.')

frag['short-costs'] = table(['Verifier step', 'Work for $4n = 2^{13}$', 'Growth'], [
    ['Compute $s(x, y)$', 'One term per nonzero wiring coefficient', '**Linear**'],
    ['Compute $t(x, z)$', 'Two geometric sums', 'Logarithmic'],
    ['Compute $k(y)$', 'One term per public input', 'Size of the instance'],
    ['Split and target checks', 'A few field operations', 'Constant'],
    ['Derive $f(u)$, $P$ and $v$', f'{len(sclaims)} inverses and {len(spolys) + 1} scalar multiplications', 'Constant'],
    ['Combine the $L_j$ and $R_j$', f'${2 * k_big}$ scalar multiplications', 'Logarithmic'],
    ['Compute $\\hat{b} = g(u)$', f'${k_big - 1}$ squarings and ${k_big}$ factor multiplications', 'Logarithmic'],
    ['Compute the coefficients of $g$', f'About ${SIZE:,}$ field multiplications', '**Linear**'],
    ['Compute $\\hat{G}$', f'1 MSM of ${SIZE:,}$ scalar multiplications', '**Linear**'],
])

# The prover's FFT cost for the split form.
domain_min = 8 * (SIZE // 4) - 1
domain = 2 ** 14
assert domain >= domain_min and domain // 2 < domain_min
frag['fft'] = (f'The [book counts](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/nark.md?plain=1#L176-L196) at least 3 FFTs, over a domain with at least $8n - 1$ points. For $4n = 2^{{13}}$, that is at least ${domain_min:,}$ points, and the next power of two is ${domain:,}$.')

print(json.dumps(frag))
