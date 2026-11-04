"""Worked examples for recursive-proofs.md. Prints fragments as JSON.

The level-0 proof is the short proof of nark.md Section 17, imported from that
chapter's script so the two chapters cannot drift apart. The "verifier as gates"
below is a small tracer over F_43 that records each multiplication, so every gate
count in the chapter comes from running the arithmetic. Importing this module
(the Manim figure does) prints nothing.
"""
import contextlib
import io
import json

with contextlib.redirect_stdout(io.StringIO()):
    import nark
from nark import (GENS, K_POLY, Q, R_FALSE, R_HONEST, TOY, Transcript, U, add, commit, ev, g_coeffs, inv, lin, msm, mul,
                  revdot, table, vec)
from pcd_intro import tally
from toy_curve import B_DUAL, P, curve_points, show
from toy_curve import add as add_any


def neg(a):
    return None if a is None else (a[0], -a[1] % P)


# ---- The step function: chapter 04's cubic, applied repeatedly over F_43 ----
def F(z):
    return (z ** 3 + z + 5) % Q


Z0 = 3
CHAIN = [Z0]
for _ in range(5):
    CHAIN.append(F(CHAIN[-1]))
assert CHAIN[1] == 35 and len(set(CHAIN)) == len(CHAIN) and 0 not in CHAIN


# ---- A tracer: one entry per multiplication gate ----
class Trace:
    def __init__(self):
        self.gates, self.checks = [], []

    def mul(self, a, b, cat):
        c = a * b % Q
        self.gates.append((a % Q, b % Q, c, cat))
        return c

    def invert(self, a, cat):
        ai = inv(a)
        assert self.mul(a, ai, cat) == 1
        return ai

    def pow(self, base, e, cat):
        """Square and multiply, with one gate per square and per set bit after the first."""
        assert e >= 1
        out = base
        for bit in bin(e)[3:]:
            out = self.mul(out, out, cat)
            if bit == '1':
                out = self.mul(out, base, cat)
        return out

    def equal(self, a, b, name):
        # An equality between wires or linear combinations costs no gate.
        self.checks.append((name, a % Q == b % Q))

    def count(self, cat):
        return sum(1 for g in self.gates if g[3] == cat)

    def ok(self):
        return all(c for _, c in self.checks)


def pow_gates(e):
    return len(bin(e)) - 3 + bin(e).count('1') - 1


# ---- Each verifier computation, run as gates ----
def s_as_gates(tr, x, y, rows=TOY.rows, n=2):
    """Powers of x and y, then one gate per wiring term. A coefficient is a constant, which costs nothing."""
    xp = [1, x]
    for _ in range(4 * n - 2):
        xp.append(tr.mul(xp[-1], x, 's'))
    yp = [1, y]
    for _ in range(len(rows) - 2):
        yp.append(tr.mul(yp[-1], y, 's'))
    total = 0
    for j, row in enumerate(rows):
        for (kind, i), coeff in row.items():
            pos = {'a': 2 * n + i, 'b': 2 * n - 1 - i, 'c': 4 * n - 1 - i, 'd': i}[kind]
            term = xp[pos] if j == 0 else tr.mul(yp[j], xp[pos], 's')
            total = (total + coeff * term) % Q
    return total


def t_as_gates(tr, x, z, n=2):
    """The closed form from nark.md Section 16."""
    zi = tr.invert(z, 't')
    x3n = tr.pow(x, 3 * n, 't')
    zn = tr.pow(z, n, 't')
    z3 = tr.pow(z, 3 * n - 1, 't')
    w1, w2 = tr.mul(x, z, 't'), tr.mul(x, zi, 't')
    s1 = tr.mul(tr.pow(w1, n, 't') - 1, tr.invert(w1 - 1, 't'), 't')
    s2 = tr.mul(tr.pow(w2, n, 't') - 1, tr.invert(w2 - 1, 't'), 't')
    one = tr.mul(tr.mul(x3n, zn, 't'), s1, 't')
    two = tr.mul(tr.mul(x3n, z3, 't'), s2, 't')
    return -(one + two) % Q


CH = dict(z=nark.z, y=nark.y, x=nark.x, u=nark.u, alpha=nark.alpha, beta=nark.beta)
assert (CH['z'], CH['y'], CH['x'], CH['u'], CH['alpha'], CH['beta']) == (5, 7, 9, 17, 11, 23)


def short_proof(r, ch=CH):
    """The prover of nark.md Section 17 for a trace r, keeping only what the field checks read."""
    z, y, x, u, alpha, beta = (ch[n] for n in ('z', 'y', 'x', 'u', 'alpha', 'beta'))
    b = TOY.right(r, z, y)
    full = [0] * 15
    for i, e in enumerate(r):
        for j, g in enumerate(b):
            full[i + j] = (full[i + j] + e * g) % Q
    c1, c2 = full[:8][::-1], full[8:] + [0]
    xz, xi = x * z % Q, inv(x)
    return dict(r=r, c1=c1, c2=c2, r_x=ev(r, x), r_xz=ev(r, xz), c1_0=ev(c1, 0), c1_inv=ev(c1, xi), c2_x=ev(c2, x),
                r_u=ev(r, u), c1_u=ev(c1, u), c2_u=ev(c2, u))


def field_checks(tr, pi, z1, ch=CH, s_override=None):
    """The level-1 circuit's field part: it reads the inner proof and its public z1 as witness."""
    z, y, x, u, alpha, beta = (ch[n] for n in ('z', 'y', 'x', 'u', 'alpha', 'beta'))
    s = s_override if s_override is not None else s_as_gates(tr, x, y)
    t = t_as_gates(tr, x, z)
    y3 = tr.pow(y, 3, 'k')
    k = tr.mul((z1 - 5) % Q, y3, 'k')  # z1 is a wire of this circuit, so this is a real gate
    xi = tr.invert(x, 'split')
    assert xi == inv(x)
    x7 = tr.pow(x, 7, 'split')
    x8 = tr.mul(x7, x, 'split')
    left = tr.mul(pi['r_x'], pi['r_xz'] + s + t, 'split')
    m1, m2 = tr.mul(x7, pi['c1_inv'], 'split'), tr.mul(x8, pi['c2_x'], 'split')
    tr.equal(left, m1 + m2, 'split')
    tr.equal(pi['c1_0'], k, 'target')
    xz = x * z % Q
    claims = [(pi['r_u'], x, pi['r_x']), (pi['r_u'], xz, pi['r_xz']), (pi['c1_u'], 0, pi['c1_0']),
              (pi['c1_u'], xi, pi['c1_inv']), (pi['c2_u'], x, pi['c2_x'])]
    fu = 0
    for i, (val, at, claimed) in enumerate(claims):
        di = tr.invert((u - at) % Q, 'batch')
        term = tr.mul((val - claimed) % Q, di, 'batch')
        fu = (term if i == 0 else tr.mul(fu, alpha, 'batch') + term) % Q
    v = fu
    for val in (pi['r_u'], pi['c1_u'], pi['c2_u']):
        v = (tr.mul(v, beta, 'batch') + val) % Q
    return dict(s=s, t=t, k=k, f_u=fu, v=v, left=left, m1=m1, m2=m2)


# ---- Level 0: the short proof of nark.md Section 17 ----
PI0 = short_proof(R_HONEST)
assert (PI0['r_x'], PI0['r_xz'], PI0['c1_0'], PI0['c1_inv'], PI0['c2_x']) == (5, 9, 13, 6, 30)
assert (PI0['r_u'], PI0['c1_u'], PI0['c2_u']) == (42, 2, 18)

LEVEL1 = Trace()
a1 = CHAIN[1]
w1 = LEVEL1.mul(a1, a1, 'F')
w2 = LEVEL1.mul(w1, a1, 'F')
LEVEL1.equal((w2 + a1 + 5) % Q, CHAIN[2], 'F')
OUT = field_checks(LEVEL1, PI0, CHAIN[1])
assert LEVEL1.ok() and OUT['s'] == 23 and OUT['t'] == 3 and OUT['k'] == 13
assert OUT['f_u'] == nark.sf_u == 29 and OUT['v'] == nark.sv == 36

# The IPA's scalars, then the group operations, on the same trace.
ks = nark.UCHAL
k_toy = len(ks)
uinv = [LEVEL1.invert(c, 'ipa') for c in ks]
usq = [LEVEL1.mul(c, c, 'ipa') for c in ks]
uinvsq = [LEVEL1.mul(c, c, 'ipa') for c in uinv]


def g_at_gates(tr, chals, chinv, at):
    powers = [at]
    for _ in range(len(chals) - 1):
        powers.append(tr.mul(powers[-1], powers[-1], 'ipa'))
    out = 1
    for j, (c, ci) in enumerate(zip(chals, chinv)):
        factor = (ci + tr.mul(c, powers[len(chals) - 1 - j], 'ipa')) % Q
        out = factor if j == 0 else tr.mul(out, factor, 'ipa')
    return out


bhat = g_at_gates(LEVEL1, ks, uinv, CH['u'])
assert bhat == nark.b_hat == 30
ab = LEVEL1.mul(nark.a_hat, bhat, 'ipa')


def g_coeffs_gates(tr, chals, chinv, chsq):
    """One product for the first coefficient, then one gate per later coefficient."""
    size = 2 ** len(chals)
    first = chinv[0]
    for ci in chinv[1:]:
        first = tr.mul(first, ci, 'g')
    out = [first] + [0] * (size - 1)
    for i in range(1, size):
        low = i & -i
        j = len(chals) - 1 - (len(bin(low)) - 3)
        out[i] = tr.mul(out[i - low], chsq[j], 'g')
    return out


gc = g_coeffs_gates(LEVEL1, ks, uinv, usq)
assert gc == g_coeffs(ks) == nark.gc


# ---- A scalar multiplication as gates, on E' whose coordinates live in F_43 ----
EP = sorted(curve_points(Q, B_DUAL))
assert len(EP) + 1 == P


def dual_mul(k, pt):
    out = None
    for _ in range(k):
        out = add_any(out, pt, Q)
    return out


def scalar_mul_gates(tr, k, pt, bits):
    """Double-and-add with incomplete formulas. Each lower bit: 1 boolean, 4 double, 3 add, 2 select."""
    digits = [int(d) for d in bin(k)[2:].zfill(bits)]
    assert digits[0] == 1 and len(digits) == bits
    for d in digits:
        assert tr.mul(d, (1 - d) % Q, 'bit') == 0
    acc = pt
    for d in digits[1:]:
        # Doubling: x^2, the slope, the slope squared, the new y.
        xx = tr.mul(acc[0], acc[0], 'double')
        lam = 3 * xx * inv(2 * acc[1]) % Q
        assert tr.mul(lam, 2 * acc[1] % Q, 'double') == 3 * xx % Q
        x3 = (tr.mul(lam, lam, 'double') - 2 * acc[0]) % Q
        y3 = (tr.mul(lam, (acc[0] - x3) % Q, 'double') - acc[1]) % Q
        dbl = (x3, y3)
        assert dbl == add_any(acc, acc, Q)
        # Adding the base point: the slope, the slope squared, the new y.
        assert dbl[0] != pt[0]
        lam = (pt[1] - dbl[1]) * inv(pt[0] - dbl[0]) % Q
        assert tr.mul(lam, (pt[0] - dbl[0]) % Q, 'add') == (pt[1] - dbl[1]) % Q
        x4 = (tr.mul(lam, lam, 'add') - dbl[0] - pt[0]) % Q
        y4 = (tr.mul(lam, (dbl[0] - x4) % Q, 'add') - dbl[1]) % Q
        added = (x4, y4)
        assert added == add_any(dbl, pt, Q)
        # Selecting by the bit: one gate per coordinate.
        sx = (dbl[0] + tr.mul(d, (added[0] - dbl[0]) % Q, 'select')) % Q
        sy = (dbl[1] + tr.mul(d, (added[1] - dbl[1]) % Q, 'select')) % Q
        acc = (sx, sy)
        assert acc == (added if d else dbl)
    return acc


def m_gates(bits):
    return 10 * bits - 9


# A 5-bit scalar, the width of E' scalars, with no exceptional additions.
BASE_DUAL = (1, next(y for y in range(Q) if (y * y - 1 - B_DUAL) % Q == 0)) if any(pt[0] == 1 for pt in EP) else EP[5]
SCALAR = 23
tr_sm = Trace()
sm_out = scalar_mul_gates(tr_sm, SCALAR, BASE_DUAL, 5)
assert sm_out == dual_mul(SCALAR, BASE_DUAL) and len(tr_sm.gates) == m_gates(5) == 41
sm_per = {c: tr_sm.count(c) for c in ('bit', 'double', 'add', 'select')}
assert sm_per == {'bit': 5, 'double': 16, 'add': 12, 'select': 8}

# ---- The hash, as gates ----
SBOX_GATES = 3  # v^2, v^4, v^5
PERM_GATES = sum(nark.SCHEDULE) * SBOX_GATES
assert PERM_GATES == 96


def hash_perms(k):
    """Permutations the verifier's transcript runs, in the order of nark.md Section 17."""
    counter = {'n': 0}

    class Counting(Transcript):
        def _permute(self):
            counter['n'] += 1
            super()._permute()

    t = Counting(nark.TAG)
    pt = (1, 2)
    t.absorb_point(pt)                 # R
    t.squeeze('z'), t.squeeze('y')
    t.absorb_point(pt), t.absorb_point(pt)  # C1, C2
    t.squeeze('x')
    for _ in range(5):
        t.absorb(1)                    # the five evaluations
    t.squeeze('alpha')
    t.absorb_point(pt)                 # F
    t.squeeze('u')
    for _ in range(3):
        t.absorb(1)                    # the values at u
    t.squeeze('beta')
    for _ in range(k):
        t.absorb_point(pt), t.absorb_point(pt)  # L_j, R_j
        t.squeeze('u_j')
    return counter['n']


# ---- The cost of the whole verifier as a function of n ----
def lg(x):
    assert x & (x - 1) == 0
    return len(bin(x)) - 3


def verifier_costs(n, bits):
    """Gates per row. Wiring keeps the toy circuit's density: 2n constraints and 4n terms."""
    four_n = 4 * n
    k = lg(four_n)
    m = m_gates(bits)
    t_tr = Trace()
    t_as_gates(t_tr, 9, 5, n)
    return {
        's': 10 * n - 6,
        't': len(t_tr.gates),
        'k': pow_gates(3) + 1,
        'split': 1 + pow_gates(four_n - 1) + 1 + 3,
        'batch': 5 + 5 + 4 + 3,
        'ipa': k + 2 * k + (k - 1) + k + (k - 1) + 1,
        'g': (k - 1) + (four_n - 1),
        'hash': hash_perms(k) * PERM_GATES,
        'small_group': (4 + 2 * k + 2) * m,
        'Ghat': four_n * m,
    }


LINEAR_ROWS = ('s', 'g', 'Ghat')


def verifier_gates(n, bits, linear=True):
    costs = verifier_costs(n, bits)
    return sum(v for key, v in costs.items() if linear or key not in LINEAR_ROWS)


# The formulas must agree with the trace of the toy level-1 circuit.
TOY_COSTS = verifier_costs(2, 6)
for cat in ('s', 't', 'k', 'split', 'batch', 'ipa', 'g'):
    assert LEVEL1.count(cat) == TOY_COSTS[cat], (cat, LEVEL1.count(cat), TOY_COSTS[cat])
assert LEVEL1.count('F') == 2


def next_n(gates):
    n = 2
    while n < gates:
        n *= 2
    return n


def growth(bits, linear, children=1, f=2, levels=6, start=2):
    """Level i+1's circuit holds the step and one verifier per child of level i."""
    rows, n = [], start
    for level in range(levels):
        gates = f + children * verifier_gates(n, bits, linear) if level else f
        n = next_n(gates) if level else start
        rows.append((level, gates, n))
    return rows


def power(n):
    return f'2^{{{lg(n)}}}'


def big(v):
    if v < 10 ** 12:
        return f'{v:,}'
    mant, exp = f'{float(v):.1e}'.split('e+')
    return f'{mant} \\times 10^{{{int(exp)}}}'


# ---- Fragments ----
def fragments():
    frag = {}
    frag['unwind'] = (f'The proof $\\pi_2$ says that ${CHAIN[2]} = F({CHAIN[1]})$ and that $\\pi_1$ verifies for ${CHAIN[1]}$. The proof $\\pi_1$ in turn says that ${CHAIN[1]} = F({CHAIN[0]})$. A verifier holding $z_2 = {CHAIN[2]}$ and $\\pi_2$ runs one check, and it covers both applications of $F$.')
    left_h, right_h = tally(0, 4), tally(4, 8)
    root_h = tally(0, 8)
    assert (left_h[1] == right_h[0]) and left_h[2] + right_h[2] == root_h[2]
    frag['carol'] = (f'Carol from Chapter 02 joined $({left_h[0]}, {left_h[1]}, {left_h[2]})$ and $({right_h[0]}, {right_h[1]}, {right_h[2]})$ into $({root_h[0]}, {root_h[1]}, {root_h[2]})$. Her circuit checks ${left_h[1]} = {right_h[0]}$ and ${left_h[2]} + {right_h[2]} = {root_h[2]}$, and it runs the verifier twice, once on the proof of each input header.')
    frag['chain'] = table(['$i$'] + [str(i) for i in range(len(CHAIN))],
                          [['$z_i$'] + [str(z) for z in CHAIN]])

    # Separate proofs and one large proof, measured in the terms of nark.md.
    rows = []
    for steps in (1, 3, 1024):
        gates = 2 * steps
        rows.append([f'{steps:,}', f'${gates:,}$', f'${4 * next_n(gates):,}$', f'{steps:,}', 1])
    assert rows[0][2] == '$8$'
    frag['alternatives'] = table(['Steps', 'Gates if one circuit holds every step', 'Generators that circuit needs', 'Proofs to check if each step has its own', 'Proofs to check with recursion'], rows)

    # The example gates, read straight from the trace.
    g = LEVEL1.gates
    f_rows = [g_ for g_ in g if g_[3] == 'F']
    split_rows = [g_ for g_ in g if g_[3] == 'split']
    wanted = [('$F$', f_rows[0], f'$z_1 \\cdot z_1$'), ('$F$', f_rows[1], '$z_1^2 \\cdot z_1$')]
    left, m1, m2 = OUT['left'], OUT['m1'], OUT['m2']
    gate_left = next(g_ for g_ in split_rows if g_[2] == left and g_[0] == PI0['r_x'])
    gate_m1 = next(g_ for g_ in split_rows if g_[1] == PI0['c1_inv'] and g_[2] == m1)
    gate_m2 = next(g_ for g_ in split_rows if g_[1] == PI0['c2_x'] and g_[2] == m2)
    gate_k = next(g_ for g_ in g if g_[3] == 'k' and g_[0] == (CHAIN[1] - 5) % Q)
    assert gate_left[1] == (9 + 23 + 3) and (m1 + m2) % Q == left
    frag['example-gates'] = table(['Part', 'Left wire', 'Right wire', 'Output wire', 'What the gate computes'], [
        ['Step', f_rows[0][0], f_rows[0][1], f_rows[0][2], '$z_1 \\cdot z_1$'],
        ['Step', f_rows[1][0], f_rows[1][1], f_rows[1][2], '$z_1^2 \\cdot z_1$'],
        ['Verifier', gate_k[0], gate_k[1], gate_k[2], '$k(y) = (z_1 - 5) \\cdot y^3$'],
        ['Verifier', gate_left[0], gate_left[1], gate_left[2], '$r(x) \\cdot (r(xz) + s(x, y) + t(x, z))$'],
        ['Verifier', gate_m1[0], gate_m1[1], gate_m1[2], '$x^{4n-1} \\cdot c_1(x^{-1})$'],
        ['Verifier', gate_m2[0], gate_m2[1], gate_m2[2], '$x^{4n} \\cdot c_2(x)$'],
    ])
    frag['example-eqs'] = (f'Three linear constraints then finish this part, and they cost no gates. The step requires ${f_rows[1][2]} + {CHAIN[1]} + 5 = {CHAIN[2]}$ modulo 43, which is the public $z_2$. The split check requires ${m1} + {m2} = {left}$. '
                           f'The target check requires the proof\'s $c_1(0) = {PI0["c1_0"]}$ to equal the computed $k({CH["y"]}) = {OUT["k"]}$.')

    d0 = BASE_DUAL
    frag['scalar-mul'] = (f'Take the point $P\' = {show(d0)}$ on $E\'$ and the scalar ${SCALAR}$, written in binary as ${bin(SCALAR)[2:]}$. The circuit spends {sm_per["bit"]} gates to show that the digits are bits, {sm_per["double"]} on doublings, {sm_per["add"]} on additions and {sm_per["select"]} on selecting by each bit, for a total of {len(tr_sm.gates)} gates. '
                          f'Its output wires hold ${show(sm_out)}$, which equals ${SCALAR} \\cdot P\'$ computed outside the circuit. In general a scalar of $b$ bits costs $10b - 9$ gates here. That is {m_gates(6)} gates for the 6-bit scalars of $\\F_{{43}}$ and ${m_gates(255):,}$ gates for a 255-bit scalar.')

    # The toy verifier, measured.
    names = [('s', 'Compute $s(x, y)$', True), ('t', 'Compute $t(x, z)$', False), ('k', 'Compute $k(y)$', False),
             ('split', 'Split and target checks', False), ('batch', 'Derive $f(u)$ and $v$', False),
             ('ipa', 'IPA scalars and $\\hat{b} = g(u)$', False), ('g', 'Compute the coefficients of $g$', True),
             ('hash', 'Replay the transcript', False), ('small_group', 'Scalar multiplications for $P$, $v \\cdot U$, the $L_j$ and $R_j$, and the final check', False),
             ('Ghat', 'Compute $\\hat{G}$', True)]

    def cost_rows(costs):
        out = []
        for key, label, is_lin in names:
            out.append([label, f'${costs[key]:,}$', '**Linear**' if is_lin else ('Logarithmic' if key in ('t', 'split', 'ipa', 'hash', 'small_group') else 'Constant')])
        return out

    toy_total = sum(TOY_COSTS.values())
    frag['toy-costs'] = table(['Verifier step', 'Gates for $4n = 8$', 'Growth in $n$'], cost_rows(TOY_COSTS) + [['Total', f'${toy_total:,}$', '']])
    frag['toy-total'] = (f'The step itself took {LEVEL1.count("F")} gates, and verifying the proof of that same step takes ${toy_total:,}$. The field rows of this table come from running the gates on the values of the Chapter 09 proof, and a check confirms that the trace and the formula agree. The hash row is {hash_perms(3)} permutations at {PERM_GATES} gates each, and the scalar multiplications count {4 + 2 * 3 + 2 + 8} at {m_gates(6)} gates each.')

    # Production size.
    prod = verifier_costs(2048, 255)
    total = sum(prod.values())
    linear_part = sum(prod[key] for key in LINEAR_ROWS)
    assert prod['Ghat'] == 8192 * 2541 and total > 2 * 10 ** 7
    assert prod['g'] > 2048 and 8192 > 2048
    frag['prod-costs'] = table(['Verifier step', 'Gates for $4n = 2^{13}$, 255-bit scalars', 'Growth in $n$'], cost_rows(prod) + [['Total', f'${total:,}$', '']])
    frag['prod-budget'] = (f'The linear rows account for ${linear_part:,}$ of the ${total:,}$ gates, which is {100 * linear_part / total:.1f} percent. A circuit at this size has room for $n = 2,048$ gates. The coefficients of $g$ alone need ${prod["g"]:,}$, and $\\hat{{G}}$ would exceed the limit even if a scalar multiplication cost one gate, because there are $8,192$ of them.')

    # Removing a linear step: a wrong circuit.
    x, y, z = CH['x'], CH['y'], CH['z']
    four = 4
    lam = (30 - pow(four, 3, Q)) * inv(four) % Q
    # The cheater's circuit: x^3 + lam * x = 30, which x = 4 satisfies.
    other_rows = [dict(r) for r in TOY.rows]
    other_rows[3] = {('a', 0): lam, ('c', 1): 1}
    OTHER = nark.Circuit(2, other_rows)
    false_trace = R_FALSE
    assert (pow(four, 3, Q) + lam * four) % Q == 30 and lam != 1
    assert revdot(false_trace, OTHER.right(false_trace, z, y)) == ev(K_POLY, y)
    pi_other = other_proof(false_trace, OTHER)
    s_real, s_other = ev(TOY.s(y), x), ev(OTHER.s(y), x)
    tr_free = Trace()
    field_checks(tr_free, pi_other, CHAIN[1], s_override=s_other)
    assert tr_free.ok()
    tr_real = Trace()
    field_checks(tr_real, pi_other, CHAIN[1])
    assert not tr_real.ok() and dict(tr_real.checks)['target'] and not dict(tr_real.checks)['split']
    assert s_real != s_other
    frag['drop-s'] = (f'The value $x = 4$ does not satisfy our statement, since $4^3 + 4 + 5 = {F(4)}$, not 35. It does satisfy a different circuit, $x^3 + {lam} x = 30$, which differs from ours in one wiring coefficient. A prover who builds its proof from that other circuit passes the split and target checks if the verifier reads $s(x, y) = {s_other}$ from the proof. When the verifier computes the value from our circuit it gets ${s_real}$, and the split check fails.')

    # Removing a linear step: a claimed G-hat.
    honest_v, P_pt = nark.sv, nark.sP
    a_hat, b_hat, G_hat = nark.a_hat, nark.b_hat, nark.G_hat
    u_sq = [c * c % Q for c in ks]
    ui_sq = [inv(c) ** 2 % Q for c in ks]

    def lhs_for(v):
        pt = add(P_pt, mul(v, U))
        for a_, b_, L, R in zip(ui_sq, u_sq, nark.ls, nark.rs):
            pt = add(add(pt, mul(a_, L)), mul(b_, R))
        return pt

    def real_check(v):
        return lhs_for(v) == add(mul(a_hat, G_hat), mul(a_hat * b_hat, U))

    def forged_G(v):
        """Solve the final equation for the point. This takes no discrete log."""
        return add(mul(inv(a_hat), lhs_for(v)), neg(mul(b_hat, U)))

    assert real_check(honest_v)
    real_pass = [v for v in range(Q) if real_check(v)]
    assert real_pass == [honest_v]
    forged_pass = [v for v in range(Q) if add(mul(a_hat, forged_G(v)), mul(a_hat * b_hat, U)) == lhs_for(v)]
    assert len(forged_pass) == Q
    false_v = (honest_v + 1) % Q
    fake = forged_G(false_v)
    assert fake is not None and fake != G_hat and msm(g_coeffs(ks), GENS) != fake
    frag['drop-g'] = (f'Suppose the prover lies about the batched value and claims $v = {false_v}$ where the truth is ${honest_v}$, keeping every $L_j$, $R_j$ and $\\hat{{a}} = {a_hat}$ from the honest run. If the verifier computes $\\hat{{G}} = {show(G_hat)}$ itself, then of the {Q} possible values of $v$ only ${honest_v}$ passes the final equation with this $\\hat{{a}}$. '
                      f'If the verifier accepts $\\hat{{G}}$ from the proof, the prover can solve that equation for the point, which gives $\\hat{{G}}\' = \\hat{{a}}^{{-1}} \\cdot (\\text{{left side}}) - \\hat{{b}} \\cdot U = {show(fake)}$. This takes only point additions and scalar multiplications, and it succeeds for all {Q} values of $v$.')
    frag['drop-g-later'] = (f'In our example the prover\'s claim is $\\hat{{G}} = {show(fake)}$ for the challenges $({", ".join(str(c) for c in ks)})$, and the true MSM gives ${show(G_hat)}$.')

    # Free challenges.
    passing = [(a_, b_) for a_ in range(Q) for b_ in range(Q) if revdot(R_FALSE, TOY.right(R_FALSE, a_, b_)) == ev(K_POLY, b_)]
    assert len(passing) == 43
    # The gates of this trace hold, so only the constraint weighted by y^3 fails, and y = 0 removes it.
    assert all(b_ == 0 for _, b_ in passing)
    pair = (CH['z'], 0)
    assert pair in passing
    forged_ch = dict(CH, z=pair[0], y=pair[1])
    assert CH['x'] * pair[0] % Q not in (0, 1)
    assert (CH['x'] * inv(pair[0])) % Q != 1
    pi_false = short_proof(R_FALSE, forged_ch)
    # A u that avoids the claim points keeps the batching defined.
    tr_ch = Trace()
    field_checks(tr_ch, pi_false, CHAIN[1], forged_ch)
    assert tr_ch.ok()
    pi_false_fixed = short_proof(R_FALSE, CH)
    tr_fx = Trace()
    field_checks(tr_fx, pi_false_fixed, CHAIN[1], CH)
    assert not tr_fx.ok()
    frag['free-challenge'] = (f'Take the false trace with $x = 4$ and the statement 35. Of the {Q * Q} pairs $(z, y)$, {len(passing)} satisfy the revdot equation for this trace, the same count as in [Chapter 09](./nark.md#the-prover-follows-every-instruction). All of them have $y = 0$, because the gates of this trace hold and only the constraint weighted by $y^3$ fails. If the circuit read its challenges from the witness, the prover could set $(z, y) = ({pair[0]}, {pair[1]})$, and every field check in the level-1 circuit would pass. At the hand-picked pair $({CH["z"]}, {CH["y"]})$, the same false trace fails.')
    frag['hash-cost'] = (f'Replaying the transcript for $4n = 8$ takes {hash_perms(3)} permutations of the toy sponge. The sponge has {sum(nark.SCHEDULE)} S-boxes per permutation, each computing $v^5$ with {SBOX_GATES} gates, so the replay costs ${hash_perms(3) * PERM_GATES:,}$ gates.')

    # Tampering with the inner proof.
    keys = ('r_x', 'r_xz', 'c1_0', 'c1_inv', 'c2_x')
    tampered, caught = 0, 0
    for key in keys:
        for val in range(Q):
            if val == PI0[key]:
                continue
            tampered += 1
            tr = Trace()
            field_checks(tr, dict(PI0, **{key: val}), CHAIN[1])
            caught += not tr.ok()
    assert tampered == 5 * 42 and caught == tampered
    wrong_state = 0
    for z1 in range(Q):
        if z1 == CHAIN[1]:
            continue
        tr = Trace()
        field_checks(tr, PI0, z1)
        wrong_state += not tr.ok()
    assert wrong_state == 42
    frag['tamper'] = (f'Starting from the honest level-0 proof, we changed each of its five evaluations to each of the 42 other values and ran the field checks of the level-1 circuit, which makes {tampered} altered proofs. All {caught} left the circuit unsatisfied. We also kept the proof and replaced its public state $z_1 = {CHAIN[1]}$ with each of the 42 other values, and all {wrong_state} failed the target check. In these runs the challenges stay fixed, and a real transcript would also change them.')

    # ---- Growth ----
    bits = 255
    lin_rows = growth(bits, True)
    log_rows = growth(bits, False, levels=8)
    assert all(lin_rows[i][2] > 100 * lin_rows[i - 1][2] for i in range(2, len(lin_rows)))
    assert log_rows[-1][2] == log_rows[-2][2] == log_rows[-3][2]
    rows = []
    for (lv, ga, na), (_, gb, nb) in zip(lin_rows, log_rows):
        rows.append([lv, f'${big(ga)}$', f'${power(na)}$', f'${gb:,}$', f'${power(nb)}$'])
    frag['growth'] = table(['Level', 'Gates with the linear steps', 'Size $n$ needed', 'Gates without them', 'Size $n$ needed'], rows[:6])
    fixed = log_rows[-1][2]
    frag['growth-fixed'] = (f'Without the linear steps, the size settles at $n = {power(fixed)}$ and stays there, because a circuit of that size can verify a proof from a circuit of the same size.')
    slope_b = 14 + 4 * m_gates(bits)
    slope_one = 14 + 4
    frag['slope'] = (f'Counting the coefficient of $n$ in our rows gives 10 gates per $n$ for $s(x, y)$, 4 for the coefficients of $g$, and $4m$ for $\\hat{{G}}$, where $m$ is the cost of one scalar multiplication. So $c = 14 + 4m$. With $m = {m_gates(bits):,}$ that is $c = {slope_b:,}$, and even the impossible $m = 1$ gives $c = {slope_one}$.')
    # Exact slope check on the linear rows, which holds up to their constant terms.
    c_pair = verifier_costs(2 ** 20, bits), verifier_costs(2 ** 19, bits)
    assert sum(c_pair[0][key] - c_pair[1][key] for key in LINEAR_ROWS) - lg(2 ** 22) + lg(2 ** 21) == slope_b * 2 ** 19

    # ---- Trees ----
    tree_lin = growth(bits, True, children=2)
    tree_log = growth(bits, False, children=2, levels=8)
    assert tree_log[-1][2] == tree_log[-2][2]
    frag['tree-growth'] = (f'With the linear steps, level 1 already needs ${power(tree_lin[1][2])}$ gates, where the chain needed ${power(lin_rows[1][2])}$, and level 2 needs ${power(tree_lin[2][2])}$. Without them the size again settles, now at $n = {power(tree_log[-1][2])}$ compared with the chain\'s ${power(fixed)}$. Doubling the verifier work added {lg(tree_log[-1][2]) - lg(fixed)} to the exponent.')
    assert lg(tree_log[-1][2]) >= lg(fixed)

    # Ragu-shaped node counts for the tally of chapter 02.
    entries = 8
    balanced_nodes, balanced_real = 2 * entries - 1, 2 * entries - 2
    balanced_unit = 2 * balanced_nodes - balanced_real
    chain_nodes, chain_real = entries, entries - 1
    chain_unit = 2 * chain_nodes - chain_real
    assert (balanced_nodes, balanced_real, balanced_unit) == (15, 14, 16) and (chain_nodes, chain_real, chain_unit) == (8, 7, 9)
    frag['tree-shapes'] = table(['Shape', 'Nodes', 'Inputs carrying a tally', 'Unit inputs', 'Proofs verified inside circuits', 'Proofs the final verifier checks'], [
        ['Balanced tree', balanced_nodes, balanced_real, balanced_unit, 2 * balanced_nodes, 1],
        ['Chain', chain_nodes, chain_real, chain_unit, 2 * chain_nodes, 1],
    ])

    # ---- Base cases ----
    image = {F(a_) for a_ in range(Q)}
    assert CHAIN[1] in image and len(image) < Q

    def iterate(a_, i):
        for _ in range(i):
            a_ = F(a_)
        return a_

    i_target = 5
    design1 = sorted(image)
    design2 = sorted({iterate(a_, i_target) for a_ in range(Q)})
    design3 = sorted({iterate(a_, i_target) for a_ in [Z0]})
    assert design3 == [CHAIN[i_target]] and len(design1) > len(design2) > 1
    # Closure of the rules, computed by running the rules rather than the formula.
    closure1 = set()
    for a_ in range(Q):
        closure1.add(F(a_))  # the flag is free, so any a_ can be the input
    assert closure1 == image
    closure2 = {(0, a_) for a_ in range(Q)}
    for i in range(i_target):
        closure2 |= {(h + 1, F(a_)) for h, a_ in closure2 if h == i}
    assert sorted(a_ for h, a_ in closure2 if h == i_target) == design2
    closure3 = {(0, Z0, Z0)}
    for a_ in range(Q):
        closure3.add((0, a_, a_))
    for i in range(i_target):
        closure3 |= {(h + 1, start, F(a_)) for h, start, a_ in closure3 if h == i}
    at_target = {(start, a_) for h, start, a_ in closure3 if h == i_target}
    assert len(at_target) == Q
    assert [a_ for start, a_ in at_target if start == Z0] == [CHAIN[i_target]]
    frag['base-designs'] = table(['Design', 'Base-case rule', 'Header', 'Values a proof can claim for $z_5$'], [
        ['1', 'The prover sets a flag, and the flag skips the verifier', '$z$', f'{len(design1)} of {Q}, any output of $F$, at any claimed step'],
        ['2', 'The flag requires $i = 0$', '$(i, z)$', f'{len(design2)} of {Q}'],
        ['3', 'The flag requires $i = 0$ and $z = z_0$', '$(i, z_0, z)$', f'{Q} headers overall, and exactly 1 once the verifier requires $z_0 = {Z0}$, namely $z_5 = {CHAIN[i_target]}$'],
    ])

    # ---- Init-state root, with the toy sponge ----
    def H(a_, b_):
        t = Transcript(nark.TAG)
        t.absorb(a_), t.absorb(b_)
        return t.squeeze('h')

    leaves = [4, 11, 3, 7]
    assert leaves == [4, 11, 3, 7]

    def tree(vals, tag):
        lv = [H(v, tag) for v in vals]
        return lv, H(lv[0], lv[1]), H(lv[2], lv[3])

    # A search for a leaf tag whose tree has no repeated value keeps the table readable.
    LEAF_TAG = next(t for t in range(1, Q) if len({*tree(leaves, t)[0], *tree(leaves, t)[1:], H(*tree(leaves, t)[1:])}) == 7
                    and 0 not in {*tree(leaves, t)[0], *tree(leaves, t)[1:], H(*tree(leaves, t)[1:])})
    lh, r01, r23 = tree(leaves, LEAF_TAG)
    root = H(r01, r23)

    def root_with(pos, val):
        vals = list(leaves)
        vals[pos] = val
        _, left_, right_ = tree(vals, LEAF_TAG)
        return H(left_, right_)

    same = sum(1 for v in range(Q) if v != leaves[2] and root_with(2, v) == root)
    assert root_with(2, leaves[2]) == root and same < 8
    frag['init-root'] = table(['Node', 'Inputs', 'Root in the header'], [
        ['Leaf 0', f'$H({leaves[0]}, {LEAF_TAG})$', lh[0]],
        ['Leaf 1', f'$H({leaves[1]}, {LEAF_TAG})$', lh[1]],
        ['Leaf 2', f'$H({leaves[2]}, {LEAF_TAG})$', lh[2]],
        ['Leaf 3', f'$H({leaves[3]}, {LEAF_TAG})$', lh[3]],
        ['Join', f'$H({lh[0]}, {lh[1]})$', r01],
        ['Join', f'$H({lh[2]}, {lh[3]})$', r23],
        ['Top', f'$H({r01}, {r23})$', root],
    ])
    assert same == 1
    frag['init-count'] = (f'Replacing the start value of leaf 2 with each of the other 42 values changes the root in {42 - same} cases. The remaining case is a collision, which a hash with only 43 outputs cannot avoid, and a 255-bit output makes finding one infeasible.')
    return frag


def other_proof(r, circuit, ch=CH):
    z, y, x, u = ch['z'], ch['y'], ch['x'], ch['u']
    b = circuit.right(r, z, y)
    full = [0] * 15
    for i, e in enumerate(r):
        for j, g in enumerate(b):
            full[i + j] = (full[i + j] + e * g) % Q
    c1, c2 = full[:8][::-1], full[8:] + [0]
    xz, xi = x * z % Q, inv(x)
    return dict(r=r, c1=c1, c2=c2, r_x=ev(r, x), r_xz=ev(r, xz), c1_0=ev(c1, 0), c1_inv=ev(c1, xi), c2_x=ev(c2, x),
                r_u=ev(r, u), c1_u=ev(c1, u), c2_u=ev(c2, u))


if __name__ == '__main__':
    print(json.dumps(fragments()))
