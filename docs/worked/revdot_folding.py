"""Worked example for revdot-folding.md. Prints fragments as JSON.

Every honest run and every cheating attempt goes through the same fold_prove and
fold_verify functions. The verifier functions read instances and prover messages only,
so a printed verdict is a computed one.
"""
import json
import math
import random
from functools import lru_cache

import toy_curve
from toy_curve import G, H, Q, add, curve_points, log, show

frag = {}


@lru_cache(maxsize=None)
def mul(k, a):
    return toy_curve.mul(k % Q, a)


def msm(scalars, points):
    out = None
    for k, a in zip(scalars, points):
        out = add(out, mul(k, a))
    return out


# The same eight generators as the complete proof chapter.
GENS = G + [(4, 6), (5, 2), (25, 2), (30, 23)]
assert all(a in curve_points() for a in GENS) and len(set(GENS + [H])) == 9


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


def dot(p, q):
    return sum(x * y for x, y in zip(p, q)) % Q


def lin(*terms):
    size = max(len(p) for _, p in terms)
    return [sum(k * (p[i] if i < len(p) else 0) for k, p in terms) % Q for i in range(size)]


def commit(v, gamma=0):
    return add(msm(v, GENS), mul(gamma, H))


def combine_points(weights, points):
    return msm(weights, points)


def divide(p, at):
    """Synthetic division by X - at, which ignores any claimed value."""
    out, carry = [0] * (len(p) - 1), 0
    for i in range(len(p) - 1, 0, -1):
        carry = (p[i] + at * carry) % Q
        out[i - 1] = carry
    return out + [0]


def table(head, rows):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '| ' + ' | '.join(['---'] * len(head)) + ' |']
                     + ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows])


def pt(a):
    return f'${show(a)}$'


def n(k):
    return f'{k:,}'


# ------------------------------------------------------------- the toy circuit
# The circuit of the complete proof chapter, for x^3 + x + 5 = output.
NG = 2
ROWS = [
    {('a', 0): 1, ('b', 0): -1},
    {('a', 1): 1, ('c', 0): -1},
    {('a', 0): -1, ('b', 1): 1},
    {('a', 0): 1, ('c', 1): 1},
]


def s_poly(y):
    out = [0] * (4 * NG)
    for j, row in enumerate(ROWS):
        weight = pow(y, j, Q)
        for (kind, i), coeff in row.items():
            pos = {'a': 2 * NG + i, 'b': 2 * NG - 1 - i, 'c': 4 * NG - 1 - i}[kind]
            out[pos] = (out[pos] + weight * coeff) % Q
    return out


def t_poly(z):
    out = [0] * (4 * NG)
    for i in range(NG):
        out[4 * NG - 1 - i] = -(pow(z, 2 * NG - 1 - i, Q) + pow(z, 2 * NG + i, Q)) % Q
    return out


def trace(x):
    w1 = x * x % Q
    a, b, c = [x, w1], [x, x], [w1, w1 * x % Q]
    return [e % Q for e in c + a[::-1] + b + [0, 0]]


def step(z):
    return (z * z * z + z + 5) % Q


GAMMA_A, GAMMA_B = 17, 29


class Claim:
    """A revdot claim: instance (A, B, c) and witness (a, b, ga, gb)."""

    def __init__(self, a, b, ga, gb, c, label=''):
        self.a, self.b, self.ga, self.gb, self.c, self.label = a, b, ga, gb, c, label
        self.A, self.B = commit(a, ga), commit(b, gb)

    @property
    def inst(self):
        return (self.A, self.B, self.c)

    def true(self):
        return revdot(self.a, self.b) == self.c


def proof_claim(input_z, z, y, output=None, ga=GAMMA_A, gb=GAMMA_B):
    """The revdot claim of one step's proof. The target always comes from the statement."""
    output = step(input_z) if output is None else output
    a = trace(input_z)
    b = lin((1, [a[i] * pow(z, i, Q) % Q for i in range(8)]), (1, s_poly(y)), (1, t_poly(z)))
    c = (output - 5) * pow(y, 3, Q) % Q
    return Claim(a, b, ga, gb, c, f'${output} = F({input_z})$')


def decide(inst, a, b, ga, gb):
    """The decider of this chapter. This is the only one of the checks that reads vectors."""
    A, B, c = inst
    return commit(a, ga) == A and commit(b, gb) == B and revdot(a, b) == c


# ---------------------------------------------------- the error-matrix fold
def error_matrix(claims):
    return [[revdot(p.a, q.b) for q in claims] for p in claims]


def weight_a(mu, i):
    return pow(inv(mu), i, Q)


def weight_b(mu, nu, j):
    return pow(mu * nu, j, Q)


def cell_weight(mu, nu, i, j):
    return weight_a(mu, i) * weight_b(mu, nu, j) % Q


def fold_verify(insts, cross, mu, nu):
    """Compute the new instance from instances and the off-diagonal terms. No vector appears."""
    m = len(insts)
    A = combine_points([weight_a(mu, i) for i in range(m)], [x[0] for x in insts])
    B = combine_points([weight_b(mu, nu, j) for j in range(m)], [x[1] for x in insts])
    c = 0
    for i in range(m):
        for j in range(m):
            e = insts[i][2] if i == j else cross[i][j]
            c = (c + cell_weight(mu, nu, i, j) * e) % Q
    return (A, B, c)


def fold_prove(claims, mu, nu, cross=None):
    """The prover's side. A cheater may pass its own off-diagonal terms."""
    m = len(claims)
    cross = error_matrix(claims) if cross is None else cross
    a = lin(*[(weight_a(mu, i), claims[i].a) for i in range(m)])
    b = lin(*[(weight_b(mu, nu, j), claims[j].b) for j in range(m)])
    ga = sum(weight_a(mu, i) * claims[i].ga for i in range(m)) % Q
    gb = sum(weight_b(mu, nu, j) * claims[j].gb for j in range(m)) % Q
    inst = fold_verify([x.inst for x in claims], cross, mu, nu)
    new = Claim(a, b, ga, gb, inst[2])
    assert (new.A, new.B) == inst[:2]
    return new, cross


def passes(claims, cross, mu, nu):
    new, _ = fold_prove(claims, mu, nu, cross)
    return revdot(new.a, new.b) == new.c


def all_pairs():
    return [(mu, nu) for mu in range(1, Q) for nu in range(Q)]


# ------------------------------------------------------------- the running claims
STATES = [3, 35, 1, 7, 11, 14]
assert all(step(STATES[i]) == STATES[i + 1] for i in range(5))
# The first two match the proofs printed in chapters 09 and 12. The rest take their own blinding
# factors, because the toy curve has so few points that repeated values would land on the same one.
PROOF_CH = [dict(z=5, y=7), dict(z=16, y=34), dict(z=33, y=23, ga=23, gb=11),
            dict(z=12, y=19, ga=8, gb=11), dict(z=27, y=8, ga=8, gb=5), dict(z=6, y=31, ga=8, gb=11)]
claims = [proof_claim(STATES[i], **PROOF_CH[i]) for i in range(6)]
assert all(x.true() for x in claims)
for x in claims:
    assert x.c and x.A is not None and x.B is not None and x.A not in GENS + [H] and x.B not in GENS + [H]
assert len({x.A for x in claims}) == 6 and len({x.B for x in claims}) == 6

# Values the earlier chapters printed.
assert claims[0].inst == ((22, 24), (1, 29), 13)
assert claims[0].b == [9, 6, 16, 30, 20, 8, 31, 17]
assert claims[1].A == (7, 25) and claims[1].B == (27, 30) and claims[1].c == 35
three = claims[:3]

# ---------------------------------------------------------------- Section 1
c0 = claims[0]
assert decide(c0.inst, c0.a, c0.b, c0.ga, c0.gb)
frag['one-claim'] = (
    f'Chapter 09\'s proof gives the instance $(\\bar{{A}}, \\bar{{B}}, c) = ({show(c0.A)},\\ {show(c0.B)},\\ {c0.c})$ '
    f'and the witness $\\v{{a}} = {vec(c0.a)}$, $\\v{{b}} = {vec(c0.b)}$, $\\gamma_a = {c0.ga}$, $\\gamma_b = {c0.gb}$. '
    f'Checking the claim takes both parts. The two commitments recompute to the stated points, and $\\revdot{{\\v{{a}}}}{{\\v{{b}}}} = {revdot(c0.a, c0.b)}$.')

SIZE = 2 ** 13
FFT_POINTS = 2 ** 14
BUTTERFLY = 14 * FFT_POINTS // 2
frag['two-routes'] = table(
    ['Route', 'Who pays', 'Work for one claim, $4n = 2^{13}$', 'What travels'],
    [['Direct check (chapter 09)', 'Verifier', f'{n(SIZE)} field multiplications and 2 MSMs of size {n(SIZE)}', 'Both vectors'],
     ['Split (chapter 05)', 'Prover', f'At least 3 FFTs over {n(FFT_POINTS)} points, about {n(BUTTERFLY)} multiplications each', 'Two commitments and a few values']])

# ---------------------------------------------------------------- Section 2
u0, w0, u1, w1 = [2, 5], [7, 3], [4, 6], [1, 8]
# Chapter 12 wrote inner products. Reversing its b vectors gives the same numbers as revdot products.
b0, b1 = w0[::-1], w1[::-1]
e00, e01, e10, e11 = revdot(u0, b0), revdot(u0, b1), revdot(u1, b0), revdot(u1, b1)
assert (e00, e11) == (dot(u0, w0), dot(u1, w1)) == (29, 9)
E_two = (e01 + e10) % Q
assert E_two == 2
r_ = 9
fa, fb = lin((1, u0), (r_, u1)), lin((1, b0), (r_, b1))
assert revdot(fa, fb) == (e00 + r_ * E_two + r_ * r_ * e11) % Q
frag['two-claims'] = (
    f'Chapter 12 used inner products, so we reverse its $\\v{{b}}$ vectors to write the same numbers as revdot products. '
    f'Take $\\v{{a}}_0 = {vec(u0)}$, $\\v{{b}}_0 = {vec(b0)}$ with $c_0 = {e00}$, and $\\v{{a}}_1 = {vec(u1)}$, $\\v{{b}}_1 = {vec(b1)}$ with $c_1 = {e11}$. '
    f'The two products that mix the claims are $\\revdot{{\\v{{a}}_0}}{{\\v{{b}}_1}} = {e01}$ and $\\revdot{{\\v{{a}}_1}}{{\\v{{b}}_0}} = {e10}$, so $E = {e01} + {e10} = {E_two}$ modulo 43, as chapter 12 found. '
    f'At $r = {r_}$ the folded vectors are ${vec(fa)}$ and ${vec(fb)}$, their revdot product is ${revdot(fa, fb)}$, and $c_0 + r E + r^2 c_1 = {e00} + {r_} \\cdot {E_two} + {r_ * r_ % Q} \\cdot {e11} = {(e00 + r_ * E_two + r_ * r_ * e11) % Q}$.')

# A false c_0, with every possible E, at every r.
false_c0 = (e00 + 1) % Q
counts = []
for E_try in range(Q):
    hits = [r for r in range(Q)
            if revdot(lin((1, u0), (r, u1)), lin((1, b0), (r, b1))) == (false_c0 + r * E_try + r * r * e11) % Q]
    counts.append((E_try, hits))
assert [h for e, h in counts if e == E_two] == [[]]
assert all(len(h) == 1 for e, h in counts if e != E_two)
frag['two-count'] = (
    f'Suppose the prover states the false $c_0 = {false_c0}$. The two sides then differ by $1 + r(E\' - E)$, where $E\'$ is the value it sends. '
    f'We tried all 43 values of $E\'$ against all 43 values of $r$. The honest $E\' = {E_two}$ never passes, and each of the other 42 values passes at exactly one $r$. '
    f'If the prover could choose $E\'$ after seeing $r$, then it could solve this linear equation and pass every time.')

# ---------------------------------------------------------------- Section 3
frag['three-claims'] = table(
    ['Claim', 'Statement', '$\\v{a}_i$', '$\\v{b}_i$', '$\\bar{A}_i$', '$\\bar{B}_i$', '$c_i$'],
    [[i, x.label, f'${vec(x.a)}$', f'${vec(x.b)}$', pt(x.A), pt(x.B), x.c] for i, x in enumerate(three)])

false_mid = proof_claim(4, 5, 7, output=35)
assert revdot(false_mid.a, false_mid.b) == 18 and false_mid.c == 13 and not false_mid.true()
false_list = [claims[1], false_mid, claims[2]]
gap = (revdot(false_mid.a, false_mid.b) - false_mid.c) % Q
EF = error_matrix(false_list)
assert gap == 5


def one_challenge_lhs(items, r):
    a = lin(*[(pow(r, i, Q), x.a) for i, x in enumerate(items)])
    b = lin(*[(pow(r, j, Q), x.b) for j, x in enumerate(items)])
    return a, b, revdot(a, b)


def one_challenge_rhs(items, E1, E2, E3, r):
    return (items[0].c + r * E1 + r * r * (items[1].c + E2) + pow(r, 3, Q) * E3 + pow(r, 4, Q) * items[2].c) % Q


E1 = (EF[0][1] + EF[1][0]) % Q
E2 = (EF[0][2] + EF[2][0]) % Q
E3 = (EF[1][2] + EF[2][1]) % Q
assert all(one_challenge_lhs(false_list, r)[2] != one_challenge_rhs(false_list, E1, E2, E3, r) for r in range(1, Q))
assert one_challenge_lhs(false_list, 0)[2] == one_challenge_rhs(false_list, E1, E2, E3, 0) and false_list[0].true()
E2_cheat = (E2 + gap) % Q
assert E2 and E2_cheat != E2
assert all(one_challenge_lhs(false_list, r)[2] == one_challenge_rhs(false_list, E1, E2_cheat, E3, r) for r in range(Q))
r_show = 9
a_s, b_s, c_s = one_challenge_lhs(false_list, r_show)
com_a = add(msm([1, r_show, r_show * r_show % Q], [x.A for x in false_list]), None)
assert com_a == commit(a_s, sum(pow(r_show, i, Q) * x.ga for i, x in enumerate(false_list)) % Q)
frag['false-list'] = table(
    ['Slot', 'Statement', 'Witness', 'Stated $c$', 'True $\\revdot{\\v{a}}{\\v{b}}$'],
    [[0, false_list[0].label, 'Honest proof (claim 1 above)', false_list[0].c, revdot(false_list[0].a, false_list[0].b)],
     [1, f'{three[0].label}, the statement of claim 0', f'Chapter 09\'s false trace for $x = 4$, where $F(4) = {step(4)}$', false_mid.c, revdot(false_mid.a, false_mid.b)],
     [2, false_list[2].label, 'Honest proof (claim 2 above)', false_list[2].c, revdot(false_list[2].a, false_list[2].b)]])
assert false_list[0].true() and false_list[2].true() and false_mid.c == three[0].c
assert false_list[0] is claims[1] and false_list[2] is claims[2]
frag['collision'] = (
    f'The false claim sits in slot 1, so its diagonal entry carries $r^2$, and it is false by ${gap}$. '
    f'Write $E_k$ for the sum of cross terms in the coefficient of $r^k$, so that $E_1 = e_{{0,1}} + e_{{1,0}}$, $E_2 = e_{{0,2}} + e_{{2,0}}$ and $E_3 = e_{{1,2}} + e_{{2,1}}$. '
    f'The honest values are $E_1 = {E1}$, $E_2 = {E2}$ and $E_3 = {E3}$, and with them the fold rejects at all 42 nonzero values of $r$. '
    f'It passes at $r = 0$, where every weight except slot 0\'s vanishes, so only the true claim in slot 0 is checked. '
    f'The cheater sends $E_2\' = {E2} + {gap} = {E2_cheat}$ instead, before it knows $r$. '
    f'At $r = {r_show}$ both sides equal ${c_s}$, and running all 43 values of $r$ gives 43 passes. '
    f'The output is a true claim, because the vectors $\\v{{a}}^*$ and $\\v{{b}}^*$ really have that revdot product, so the decider accepts it too.')

# ---------------------------------------------------------------- Section 4
pair_count = len(all_pairs())
assert pair_count == 42 * 43


def d_of(offsets, gap_values, mu, nu):
    """The difference between the stated c* and the true revdot, from offsets on each cell."""
    out = 0
    for (i, j), d in offsets.items():
        out = (out + cell_weight(mu, nu, i, j) * d) % Q
    for i, g in gap_values.items():
        out = (out + cell_weight(mu, nu, i, i) * g) % Q
    return out


# The same cheat against two challenges. A cell (0, 2) offset of +gap, against a -gap on the diagonal.
stated_gap = {1: (-gap) % Q}
same_cheat = {(0, 2): gap}
same_hits = [p for p in all_pairs() if d_of(same_cheat, stated_gap, *p) == 0]
nonzero_nu = [p for p in same_hits if p[1]]
assert len(nonzero_nu) == 42 and len(same_hits) == 84
cheated = [row[:] for row in EF]
cheated[0][2] = (cheated[0][2] + gap) % Q
assert sum(passes(false_list, cheated, *p) for p in all_pairs()) == len(same_hits)
frag['two-challenge-cheat'] = (
    f'We replay the cheat of Section 3, with the same false claim and the same shift of ${gap}$ on the cross term in cell $(0, 2)$. '
    f'The diagonal error now has weight $\\nu$ and the shift has weight $\\mu^2 \\nu^2$, so the two cancel only where $\\mu^2 \\nu = 1$ or $\\nu = 0$. '
    f'Across all {n(pair_count)} pairs with $\\mu \\neq 0$ the fold passes at {len(same_hits)}, which is {len(same_hits) / pair_count:.3f} of them. '
    f'Half of those have $\\nu = 0$, where $\\v{{b}}^*$ reduces to $\\v{{b}}_0$ and the other claims drop out of the check.')

# ---------------------------------------------------------------- Section 5
MU, NU = 6, 13
E3x3 = error_matrix(three)
assert [E3x3[i][i] for i in range(3)] == [x.c for x in three]
assert all(E3x3[i][j] for i in range(3) for j in range(3))
frag['matrix'] = table(
    ['$e_{i,j}$', '$\\v{b}_0$', '$\\v{b}_1$', '$\\v{b}_2$'],
    [[f'$\\v{{a}}_{i}$'] + [f'**{E3x3[i][j]}**' if i == j else E3x3[i][j] for j in range(3)] for i in range(3)])
acc_w = [weight_a(MU, i) for i in range(3)]
bcc_w = [weight_b(MU, NU, j) for j in range(3)]
assert len(set(acc_w)) == 3 and len(set(bcc_w)) == 3
frag['weights'] = (
    f'The verifier sends $\\mu = {MU}$ and $\\nu = {NU}$, so $\\mu^{{-1}} = {inv(MU)}$ and $\\mu\\nu = {MU * NU % Q}$. '
    f'The weights on the $\\v{{a}}_i$ are ${vec(acc_w)}$, and the weights on the $\\v{{b}}_j$ are ${vec(bcc_w)}$. '
    f'Each cell of the next table is the matching weight times the entry above:\n\n'
    + table(['$\\mu^{j-i}\\nu^j e_{i,j}$', '$j = 0$', '$j = 1$', '$j = 2$'],
            [[f'$i = {i}$'] + [cell_weight(MU, NU, i, j) * E3x3[i][j] % Q for j in range(3)] for i in range(3)])
    + '\n\n' + f'All nine cells sum to $c^* = {sum(cell_weight(MU, NU, i, j) * E3x3[i][j] for i in range(3) for j in range(3)) % Q}$.')
for i in range(3):
    assert cell_weight(MU, NU, i, i) == pow(NU, i, Q)
fold3, _ = fold_prove(three, MU, NU)
inst3 = fold_verify([x.inst for x in three], E3x3, MU, NU)
assert inst3 == fold3.inst and fold3.true()
assert decide(inst3, fold3.a, fold3.b, fold3.ga, fold3.gb)
frag['fold-result'] = table(
    ['Part', 'Computed from', 'Result'],
    [['$\\bar{A}^*$', f'${acc_w[0]} \\cdot \\bar{{A}}_0 + {acc_w[1]} \\cdot \\bar{{A}}_1 + {acc_w[2]} \\cdot \\bar{{A}}_2$', pt(fold3.A)],
     ['$\\bar{B}^*$', f'${bcc_w[0]} \\cdot \\bar{{B}}_0 + {bcc_w[1]} \\cdot \\bar{{B}}_1 + {bcc_w[2]} \\cdot \\bar{{B}}_2$', pt(fold3.B)],
     ['$c^*$', 'The nine cells above', fold3.c],
     ['$\\v{a}^*$', 'Prover, the same weights on the vectors', f'${vec(fold3.a)}$'],
     ['$\\v{b}^*$', 'Prover, the same weights on the vectors', f'${vec(fold3.b)}$'],
     ['$\\gamma_a^*, \\gamma_b^*$', 'Prover, the same weights on the blinding factors', f'${fold3.ga},\\ {fold3.gb}$']])
frag['fold-check'] = (
    f'The decider now has one claim to check. It computes $\\revdot{{\\v{{a}}^*}}{{\\v{{b}}^*}} = {revdot(fold3.a, fold3.b)}$, which equals $c^*$, '
    f'and it recomputes both commitments, which gives {pt(commit(fold3.a, fold3.ga))} and {pt(commit(fold3.b, fold3.gb))}. '
    f'Three revdot products and six commitment checks have become one and two.')
honest_all = sum(passes(three, E3x3, *p) for p in all_pairs())
assert honest_all == pair_count
frag['honest-count'] = f'Repeating the fold for all {n(pair_count)} pairs $(\\mu, \\nu)$ with $\\mu \\neq 0$ gives a true output claim every time.'

# ---------------------------------------------------------------- Section 6
FOLD_CH = [(21, 8), (31, 4)]
accs = [claims[0]]
rows = [['Start', 'Proof of ' + claims[0].label, '', '', f'$({show(claims[0].A)},\\ {show(claims[0].B)},\\ {claims[0].c})$', f'${vec(claims[0].a)}$', f'${vec(claims[0].b)}$']]
for k, (mu, nu) in enumerate(FOLD_CH):
    inputs = [accs[-1], claims[k + 1]]
    new, cross = fold_prove(inputs, mu, nu)
    assert fold_verify([x.inst for x in inputs], cross, mu, nu) == new.inst and new.true()
    assert new.A is not None and new.B is not None and new.c
    assert cross[0][1] and cross[1][0]
    assert all(new.a[:6]) and all(new.b)
    rows.append([f'Fold {k + 1}', 'Proof of ' + claims[k + 1].label, f'$({cross[0][1]},\\ {cross[1][0]})$', f'$({mu},\\ {nu})$',
                 f'$({show(new.A)},\\ {show(new.B)},\\ {new.c})$', f'${vec(new.a)}$', f'${vec(new.b)}$'])
    accs.append(new)
frag['chain'] = table(['Step', 'New claim from', 'Cross terms $(e_{0,1}, e_{1,0})$', '$(\\mu, \\nu)$', 'Accumulator instance', '$\\v{a}$', '$\\v{b}$'], rows)
last = accs[-1]
assert decide(last.inst, last.a, last.b, last.ga, last.gb)
frag['decider'] = (
    f'The decider receives the last accumulator. It finds $\\revdot{{\\v{{a}}}}{{\\v{{b}}}} = {revdot(last.a, last.b)} = c$, '
    f'and with $\\gamma_a = {last.ga}$ and $\\gamma_b = {last.gb}$ both commitments recompute to the instance. It accepts.')
frag['prover-cost'] = (
    f'A fold of one accumulator and one new claim needs $2$ cross terms, at {n(SIZE)} multiplications each for dense vectors of $2^{{13}}$ entries, so {n(2 * SIZE)} multiplications. '
    f'The split of chapter 05 needs at least 3 FFTs of about {n(BUTTERFLY)} multiplications each, or {n(3 * BUTTERFLY)}, and then the prover still has to commit to two more polynomials.')

# ---------------------------------------------------------------- Section 7
THETA = 22
a_vals = [ev(x.a, THETA) for x in three]
b_vals = [ev(x.b, THETA) for x in three]
a_star_val = sum(acc_w[i] * a_vals[i] for i in range(3)) % Q
b_star_val = sum(bcc_w[i] * b_vals[i] for i in range(3)) % Q
assert a_star_val == ev(fold3.a, THETA) and b_star_val == ev(fold3.b, THETA)
assert all(a_vals) and all(b_vals) and a_star_val and b_star_val
frag['spot-check'] = (
    f'Take $\\theta = {THETA}$ for the fold of Section 5. The prover sends these values:\n\n'
    + table(['Polynomial', 'Value at $\\theta$', 'Weight', 'Polynomial', 'Value at $\\theta$', 'Weight'],
            [[f'$a_{i}$', a_vals[i], acc_w[i], f'$b_{i}$', b_vals[i], bcc_w[i]] for i in range(3)]
            + [['$a^*$', a_star_val, '', '$b^*$', b_star_val, '']])
    + '\n\n' + f'Field arithmetic alone confirms both sums: '
    f'${acc_w[0]} \\cdot {a_vals[0]} + {acc_w[1]} \\cdot {a_vals[1]} + {acc_w[2]} \\cdot {a_vals[2]} = {a_star_val}$ and '
    f'${bcc_w[0]} \\cdot {b_vals[0]} + {bcc_w[1]} \\cdot {b_vals[1]} + {bcc_w[2]} \\cdot {b_vals[2]} = {b_star_val}$ modulo 43.')

# The claims that chapter 12's list already holds for each proof: a_i at x z and b_i at x.
NARK_X = [9, 37, 31]
assert [ev(three[0].a, 9 * 5 % Q), ev(three[0].b, 9)] == [9, 35]
nark_pts = [(x_ * PROOF_CH[i]['z'] % Q, x_) for i, x_ in enumerate(NARK_X)]
polys = [(x.a, x.ga, x.A) for x in three] + [(fold3.a, fold3.ga, fold3.A)] \
    + [(x.b, x.gb, x.B) for x in three] + [(fold3.b, fold3.gb, fold3.B)]
# Each claim names a polynomial by its index in polys, a point and a value.
old_claims = [(i, nark_pts[i][0], ev(three[i].a, nark_pts[i][0])) for i in range(3)] \
    + [(4 + i, nark_pts[i][1], ev(three[i].b, nark_pts[i][1])) for i in range(3)]
spot_claims = [(k, THETA, ev(polys[k][0], THETA)) for k in range(8)]
all_claims = old_claims + spot_claims
ALPHA, U, BETA, GAMMA_F = 11, 17, 23, 7
assert U != THETA and all(U != at and THETA != at for _, at, _ in old_claims)


def batch(polys, claims, alpha, u, beta, gamma_f):
    """Chapter 08 with shared polynomials (its Section 10) and the weights of chapter 12."""
    f = [0] * 8
    for k, at, _ in claims:
        f = lin((alpha, f), (1, divide(polys[k][0], at)))
    F = commit(f, gamma_f)
    values = [ev(p, u) for p, _, _ in polys]
    fu = 0
    for k, at, val in claims:
        fu = (fu * alpha + (values[k] - val) * inv(u - at)) % Q
    P, v, new_p, new_g = F, fu, f, gamma_f
    for (p, g, com), pu in zip(polys, values):
        P = add(mul(beta, P), com)
        v = (v * beta + pu) % Q
        new_p = lin((beta, new_p), (1, p))
        new_g = (new_g * beta + g) % Q
    return dict(F=F, fu=fu, P=P, v=v, p=new_p, gamma=new_g, values=values, f=f)


# Take the first listed beta whose output avoids the identity point and a zero value.
BETA, bat = next((b, r) for b, r in ((b, batch(polys, all_claims, ALPHA, U, b, GAMMA_F)) for b in (23, 25, 38, 32, 18))
                 if r['P'] is not None and r['v'] and r['P'] not in GENS + [H])
assert bat['fu'] == ev(bat['f'], U)
assert commit(bat['p'], bat['gamma']) == bat['P'] and ev(bat['p'], U) == bat['v']
assert bat['P'] is not None and bat['v']
assert not {bat['F'], bat['P']} & {com for _, _, com in polys}
frag['spot-old'] = (
    f'For the three proofs of Section 5, chapter 12\'s list already holds these six claims, one about $a_i$ at $x_i z_i$ and one about $b_i$ at $x_i$:\n\n'
    + table(['Proof', '$x_i$', '$z_i$', '$x_i z_i$', '$a_i(x_i z_i)$', '$b_i(x_i)$'],
            [[i, NARK_X[i], PROOF_CH[i]['z'], nark_pts[i][0], old_claims[i][2], old_claims[3 + i][2]] for i in range(3)]))

# The prover names a wrong commitment for the folded vector.
d_one = [0, 0, 0, 0, 1, 0, 0, 0]
a_wrong = lin((1, fold3.a), (1, d_one))
wrong_hits_one = [t for t in range(Q) if ev(a_wrong, t) == sum(weight_a(MU, i) * ev(three[i].a, t) for i in range(3)) % Q]
assert wrong_hits_one == [0]
roots_poly = [1]
for root in range(1, 8):
    roots_poly = [((roots_poly[i - 1] if i else 0) - root * (roots_poly[i] if i < len(roots_poly) else 0)) % Q for i in range(len(roots_poly) + 1)]
a_wrong7 = lin((1, fold3.a), (1, roots_poly))
wrong_hits = [t for t in range(Q) if ev(a_wrong7, t) == sum(weight_a(MU, i) * ev(three[i].a, t) for i in range(3)) % Q]
assert wrong_hits == [1, 2, 3, 4, 5, 6, 7]
frag['spot-cheat'] = (
    f'Suppose the prover names $\\bar{{A}}^* = {show(commit(a_wrong, fold3.ga))}$, a commitment to $\\v{{a}}^*$ with its entry 4 raised by one, and reports true values for that vector. '
    f'The difference between the two sides of the linear check is then $\\theta^4$, so the check fails at every $\\theta$ except 0.')
frag['spot-cheat7'] = (
    f'A cheater who chooses the change more carefully does better, but only up to a limit. The vectors have 8 entries, so the difference is a polynomial of degree at most 7 and has at most 7 roots. '
    f'Adding $(X - 1)(X - 2) \\cdots (X - 7)$ to $a^*(X)$ reaches that limit. The prover names $\\bar{{A}}^* = {show(commit(a_wrong7, fold3.ga))}$, and the check passes at $\\theta = 1, \\ldots, 7$, which is {len(wrong_hits)} of the 43 values. '
    f'At the other {Q - len(wrong_hits)} values, a prover who wants the linear check to pass has to report a false value for some polynomial, and that entry of the list becomes a false evaluation claim for chapter 08\'s batching to catch.')
assert commit(a_wrong7, fold3.ga) not in (None, fold3.A)
n_old = len({k for k, _, _ in old_claims})
n_new = len(polys)
frag['spot-count'] = (
    f'Before the spot check, $\\bar{{P}}$ combined $\\bar{{F}}$ and the {n_old} commitments $\\bar{{A}}_i$ and $\\bar{{B}}_i$, at one scalar multiplication each. '
    f'After it, $\\bar{{P}}$ combines $\\bar{{F}}$ and {n_new} commitments. The {n_old} old polynomials keep their single power of $\\beta$, and only $\\bar{{A}}^*$ and $\\bar{{B}}^*$ are new. '
    f'The spot check therefore adds ${n_new - n_old}$ scalar multiplications to the work deferred to the circuit on the other curve, where the direct sums would add $2m = {2 * 3}$. '
    f'Its other new work is {len(spot_claims)} terms of $f(u)$ and the two weighted sums of the spot check, all of which are field arithmetic.')


# ---------------------------------------------------------------- Section 8
def book_cost(M, N):
    return N * M * M + N * N - N + 3


def single_cost(m):
    return m * m + 1


frag['param-choice'] = (
    f'For its 133 claims the book picks $(M, N) = (7, 19)$, which costs {n(book_cost(7, 19))} constraints, '
    f'where one layer over all 133 claims would cost $133^2 + 1 = {n(single_cost(133))}$.')
best = min(((book_cost(M_, math.ceil(133 / M_)), M_, math.ceil(133 / M_)) for M_ in range(2, 67)))
assert best == (1276, 7, 19)
assert book_cost(7, 19) == 1276 and single_cost(133) == 17690

# Horner for the fold of Section 5, counting multiplications.
minv, mn = inv(MU), MU * NU % Q
mults, outer = 0, 0
row_values = []
for i in reversed(range(3)):
    row = 0
    for j in reversed(range(3)):
        row = (row * mn + E3x3[i][j]) % Q
        mults += 1 if j != 2 else 0
    row_values.insert(0, row)
    outer = (outer * minv + row) % Q
    mults += 1 if i != 2 else 0
assert outer == fold3.c and mults == 3 * 3 - 1
frag['horner'] = (
    f'For the matrix of Section 5, the three inner sums at $\\mu\\nu = {mn}$ are ${vec(row_values)}$, which take $2$ multiplications per row. '
    f'The outer sum at $\\mu^{{-1}} = {minv}$ takes $2$ more and gives $c^* = {outer}$, the same value as before. That is ${mults} = 3^2 - 1$ multiplications, plus the $2$ that precomputed $\\mu\\nu$ and $\\mu^{{-1}}$.')

M_T, N_T = 3, 2
groups = [claims[g * M_T:(g + 1) * M_T] for g in range(N_T)]
MU1, NU1 = 6, 13
MU2, NU2 = 29, 10
frag['six-claims'] = table(
    ['Group', 'Slot', 'Statement', '$\\bar{A}$', '$\\bar{B}$', '$c$'],
    [[g, s, x.label, pt(x.A), pt(x.B), x.c] for g in range(N_T) for s, x in enumerate(groups[g])])
layer1 = []
rows1 = []
for g, grp in enumerate(groups):
    new, cross = fold_prove(grp, MU1, NU1)
    assert fold_verify([x.inst for x in grp], cross, MU1, NU1) == new.inst and new.true()
    layer1.append(new)
    rows1.append([g, '; '.join(f'{cross[i][j]}' for i in range(3) for j in range(3) if i != j), pt(new.A), pt(new.B), new.c])
frag['layer-one'] = (
    f'The prover sends $2 \\cdot 3 \\cdot 2 = 12$ cross terms, listed row by row with the diagonal left out. The verifier then sends $\\mu = {MU1}$ and $\\nu = {NU1}$, and both sides compute one intermediate instance per group. '
    f'Group 0 holds the claims of Section 5, so its result is the one we already found.\n\n'
    + table(['Group $g$', 'Cross terms $e^{(g)}_{i,j}$', '$\\bar{A}^{(g)}$', '$\\bar{B}^{(g)}$', '$c^{(g)}$'], rows1))
assert layer1[0].inst == fold3.inst
final, cross2 = fold_prove(layer1, MU2, NU2)
assert fold_verify([x.inst for x in layer1], cross2, MU2, NU2) == final.inst and final.true()
assert decide(final.inst, final.a, final.b, final.ga, final.gb)
assert cross2[0][1] and cross2[1][0] and final.c and final.A is not None and final.B is not None
frag['layer-two'] = (
    f'The prover now computes the cross terms between the two intermediate claims, $e_{{0,1}} = {cross2[0][1]}$ and $e_{{1,0}} = {cross2[1][0]}$, and sends them. '
    f'The verifier sends fresh challenges $\\mu\' = {MU2}$ and $\\nu\' = {NU2}$. The diagonal entries are the $c^{{(g)}}$ that both sides already hold, so '
    f'$c^* = {layer1[0].c} + {cell_weight(MU2, NU2, 0, 1)} \\cdot {cross2[0][1]} + {cell_weight(MU2, NU2, 1, 0)} \\cdot {cross2[1][0]} + {cell_weight(MU2, NU2, 1, 1)} \\cdot {layer1[1].c} = {final.c}$ modulo 43.')
frag['layer-final'] = (
    f'The final instance is $({show(final.A)},\\ {show(final.B)},\\ {final.c})$. '
    f'The prover\'s vectors are $\\v{{a}}^* = {vec(final.a)}$ and $\\v{{b}}^* = {vec(final.b)}$, whose revdot product is ${revdot(final.a, final.b)}$, and the decider accepts. '
    f'The prover sent $12 + 2 = 14$ cross terms, where a single layer over six claims would have needed $6 \\cdot 5 = 30$. '
    f'The book\'s count for $(M, N) = (3, 2)$ is ${book_cost(3, 2)}$ constraints against ${single_cost(6)}$.')

# ---------------------------------------------------------------- Section 9
# A fixed false claim with honest cross terms, then the best offsets found.
honest_hits = [p for p in all_pairs() if d_of({}, stated_gap, *p) == 0]
assert all(p[1] == 0 for p in honest_hits) and len(honest_hits) == 42
assert sum(passes(false_list, EF, *p) for p in all_pairs()) == 42
frag['cheat-honest'] = (
    f'Take the false list of Section 3, whose false claim sits in slot 1 with diagonal weight $\\nu$, and let the prover send every cross term honestly. '
    f'The stated $c^*$ then differs from the true product by the diagonal error alone, $({false_mid.c} - {revdot(false_mid.a, false_mid.b)})\\,\\nu = {(-gap) % Q}\\,\\nu$, which is zero only at $\\nu = 0$. '
    f'The fold passes at {len(honest_hits)} of the {n(pair_count)} pairs, all of them with $\\nu = 0$, where the claims in slots 1 and 2 drop out.')

rng = random.Random(14)
cells = [(i, j) for i in range(3) for j in range(3) if i != j]
weights_table = {p: {cell: cell_weight(p[0], p[1], *cell) for cell in cells} for p in all_pairs()}
diag_table = {p: cell_weight(p[0], p[1], 1, 1) * stated_gap[1] % Q for p in all_pairs()}


def hits_of(offsets):
    total = 0
    for p, row in weights_table.items():
        v = diag_table[p]
        for cell, d in offsets.items():
            v += row[cell] * d
        if v % Q == 0:
            total += 1
    return total


random_best = 0
for _ in range(300):
    random_best = max(random_best, hits_of({cell: rng.randrange(Q) for cell in cells}))

# A structured choice. With offsets on (0, 1) and (2, 1) only, the difference is
# nu (-gap + d01 mu + d21 / mu), so two values of mu pass for every nu.
M1, M2 = 3, 7
d01 = gap * inv(M1 + M2) % Q
d21 = M1 * M2 * d01 % Q
assert all((-gap + d01 * t + d21 * inv(t)) % Q == 0 for t in (M1, M2))
best_offsets = {(0, 1): d01, (2, 1): d21}
best_hits = hits_of(best_offsets)
assert best_hits == 2 * Q + (Q - 3)
bound_pairs = 6 * Q
assert random_best <= best_hits <= bound_pairs
cheated_best = [row[:] for row in EF]
for (i, j), d in best_offsets.items():
    cheated_best[i][j] = (cheated_best[i][j] + d) % Q
assert sum(passes(false_list, cheated_best, *p) for p in all_pairs()) == best_hits
frag['cheat-best'] = (
    f'A cheater can also move the cross terms away from their honest values. The best attack we found raises $e_{{0,1}}$ by ${d01}$ and $e_{{2,1}}$ by ${d21}$, which makes the two sides agree for every $\\nu$ at $\\mu = {M1}$ and at $\\mu = {M2}$. '
    f'It passes at {best_hits} of the {n(pair_count)} pairs with $\\mu \\neq 0$, and the best of 300 random choices of offsets passes at {random_best}. '
    f'No choice of cross terms can pass at more than ${bound_pairs}$ of these pairs.')

frag['cheat-bound'] = (
    f'With shifted cross terms, the difference between the two sides becomes a polynomial in $\\mu$ and $\\nu$, nonzero because of the diagonal error, and multiplying by $\\mu^{{m-1}}$ clears the negative powers and leaves total degree at most $3(m - 1) = 6$. '
    f'The multiplication changes no root with $\\mu \\neq 0$, because $\\mu^{{m-1}}$ is nonzero there. '
    f'The [Schwartz–Zippel bound](./statements-and-challenges.md#_5-polynomials-in-several-variables) therefore allows at most ${bound_pairs}$ roots among all $43^2$ pairs, so at most ${bound_pairs}$ among the {n(pair_count)} pairs with $\\mu \\neq 0$ that the fold can use. '
    f'For the best attack above, the difference is $\\nu({(-gap) % Q} + {d01}\\mu + {d21}\\mu^{{-1}})$, and the bracket vanishes at $\\mu = {M1}$ and $\\mu = {M2}$.')

frag['cheat-real'] = (
    f'On a 255-bit field, $m = 133$ gives a bound of $3 \\cdot 132 / 2^{{254}}$, which is below $2^{{-{int(254 - math.log2(3 * 132))}}}$.')

# Cross terms chosen after the challenges.
lmu, lnu = 6, 13
late = [row[:] for row in EF]
w_d, w_o = cell_weight(lmu, lnu, 1, 1), cell_weight(lmu, lnu, 0, 2)
late_shift = (w_d * gap) * inv(w_o) % Q
late[0][2] = (late[0][2] + late_shift) % Q
assert passes(false_list, late, lmu, lnu) and not passes(false_list, EF, lmu, lnu)
late_passes = sum(passes(false_list, late, *p) for p in all_pairs())
frag['cheat-late'] = (
    f'At $\\mu = {lmu}$ and $\\nu = {lnu}$, the false list fails with honest cross terms. A prover who already knows these challenges raises $e_{{0,2}}$ by ${late_shift}$, which solves one linear equation, and the fold passes. '
    f'The same shift committed in advance passes at only {late_passes} of the {n(pair_count)} pairs.')


# Two layers, a false claim in group 0.
false_group0 = [claims[0], false_mid, claims[2]]
six_false = [false_group0, groups[1]]
pass1 = sum(passes(false_group0, error_matrix(false_group0), *p) for p in all_pairs())
new_g0, cross_g0 = fold_prove(false_group0, MU1, NU1)
new_g1, _ = fold_prove(groups[1], MU1, NU1)
gap1 = (new_g0.c - revdot(new_g0.a, new_g0.b)) % Q
assert gap1 and new_g1.true()
assert pass1 == 42
pair_layer = [new_g0, new_g1]
Ecross = error_matrix(pair_layer)
pass2_honest = sum(passes(pair_layer, Ecross, *p) for p in all_pairs())
assert pass2_honest == 0
frag['cheat-layers'] = (
    f'Now put the false claim in slot 1 of group 0 of the six-claim run, in place of the honest proof of $1 = F(35)$, and keep the cross terms honest. At $\\mu = {MU1}$ and $\\nu = {NU1}$ the group\'s stated value $c^{{(0)}} = {new_g0.c}$ differs from the true product by ${gap1}$, and over all pairs the first layer passes at {pass1} of {n(pair_count)}. '
    f'That error sits in a diagonal slot of the second layer, in the group with weight 1, so with honest cross terms the second layer passes at {pass2_honest} of its {n(pair_count)} pairs.')

# Reusing the challenges.
reuse = [row[:] for row in Ecross]
wo = cell_weight(MU1, NU1, 0, 1)
reuse[0][1] = (reuse[0][1] + (-(new_g0.c - revdot(new_g0.a, new_g0.b))) * inv(wo)) % Q
assert passes(pair_layer, reuse, MU1, NU1)
reuse_all = 0
for mu, nu in all_pairs():
    if nu == 0:
        continue
    g0, _ = fold_prove(false_group0, mu, nu)
    g1, _ = fold_prove(groups[1], mu, nu)
    e = error_matrix([g0, g1])
    w = cell_weight(mu, nu, 0, 1)
    e[0][1] = (e[0][1] - (g0.c - revdot(g0.a, g0.b)) * inv(w)) % Q
    if passes([g0, g1], e, mu, nu):
        reuse_all += 1
assert reuse_all == 42 * 42
fresh_same = sum(passes(pair_layer, reuse, *p) for p in all_pairs())
assert fresh_same < 100
frag['cheat-reuse'] = (
    f'Suppose the second layer reused $\\mu$ and $\\nu$. The prover learns them before it sends the second layer\'s cross terms, so it can compute the error in $c^{{(0)}}$ and cancel it through $e_{{0,1}}$. '
    f'At $\\mu = {MU1}$ and $\\nu = {NU1}$ the shift is ${(reuse[0][1] - Ecross[0][1]) % Q}$. Doing this at every pair with $\\mu, \\nu \\neq 0$ passes all {n(reuse_all)} of them. '
    f'With fresh challenges the same message is fixed first, and it passes at {fresh_same} of the {n(pair_count)} pairs $(\\mu\', \\nu\')$.')

# A false claim in a chain reaches the decider.
start = false_mid
gaps = [(start.c - revdot(start.a, start.b)) % Q]
acc = start
rows = [['Start', f'{acc.c}', revdot(acc.a, acc.b), gaps[-1]]]
for k, (mu, nu) in enumerate(FOLD_CH):
    new, cross = fold_prove([acc, claims[k + 1]], mu, nu)
    assert fold_verify([acc.inst, claims[k + 1].inst], cross, mu, nu) == new.inst
    gaps.append((new.c - revdot(new.a, new.b)) % Q)
    rows.append([f'Fold {k + 1}', new.c, revdot(new.a, new.b), gaps[-1]])
    acc = new
assert gaps[0] and all(g == gaps[0] for g in gaps)
assert not decide(acc.inst, acc.a, acc.b, acc.ga, acc.gb)
frag['cheat-carry'] = (
    'Start the chain of Section 6 from the false witness of the false list in place of the proof of $35 = F(3)$, keeping every later step honest. The false claim is now the starting accumulator, in slot 0 of each fold.\n\n'
    + table(['Step', 'Stated $c$', 'True $\\revdot{\\v{a}}{\\v{b}}$', 'Stated minus true'], rows)
    + '\n\n' + f'The verifier computes each new instance and sees nothing wrong. The accumulator sits in slot 0, whose diagonal weight is $\\nu^0 = 1$, so the gap of ${gaps[0]}$ passes through each fold unchanged. The decider rejects the last accumulator because its product differs from its stated value.')

# A prover who knows relations among the toy generators.
logs = [log(g, G[0]) for g in GENS]
target = (fold3.c + 1) % Q
need = 1
rev_b = fold3.b[::-1]
i_, j_ = next((i, j) for i in range(8) for j in range(i + 1, 8) if (logs[i] * rev_b[j] - logs[j] * rev_b[i]) % Q)
det = (logs[i_] * rev_b[j_] - logs[j_] * rev_b[i_]) % Q
d_i, d_j = (-logs[j_] * need) * inv(det) % Q, (logs[i_] * need) * inv(det) % Q
forged = list(fold3.a)
forged[i_] = (forged[i_] + d_i) % Q
forged[j_] = (forged[j_] + d_j) % Q
assert commit(forged, fold3.ga) == fold3.A and revdot(forged, fold3.b) == target
assert decide((fold3.A, fold3.B, target), forged, fold3.b, fold3.ga, fold3.gb)
frag['cheat-binding'] = (
    f'Using the known discrete logs of the toy generators, a prover can state the false $c^* = {target}$ for the fold of Section 5 and present $\\v{{a}}^* = {vec(forged)}$. '
    f'This vector commits to the same $\\bar{{A}}^* = {show(fold3.A)}$, and its revdot product with $\\v{{b}}^*$ is ${target}$, so the decider accepts it.')


# ---------------------------------------------------------------- Section 10
def poly_mul(p, q):
    out = [0] * (len(p) + len(q) - 1)
    for i, x in enumerate(p):
        for j, y in enumerate(q):
            out[i + j] = (out[i + j] + x * y) % Q
    return out


def poly_add(p, q, k=1):
    size = max(len(p), len(q))
    return [((p[i] if i < len(p) else 0) + k * (q[i] if i < len(q) else 0)) % Q for i in range(size)]


def lagrange(m):
    basis = []
    for i in range(m):
        p, d = [1], 1
        for j in range(m):
            if j != i:
                p = poly_mul(p, [-j % Q, 1])
                d = d * (i - j) % Q
        basis.append([x * inv(d) % Q for x in p])
    z = [1]
    for j in range(m):
        z = poly_mul(z, [-j % Q, 1])
    return basis, z


def quotient(matrix, stated=None):
    """The code's division, with the diagonal of the matrix as targets unless a stated list is given."""
    m = len(matrix)
    basis, z = lagrange(m)
    ab = [0] * (2 * m - 1)
    for i in range(m):
        for j in range(m):
            ab = poly_add(ab, poly_mul(basis[i], basis[j]), matrix[i][j])
    targets = [matrix[i][i] for i in range(m)] if stated is None else stated
    k = [0]
    for i in range(m):
        k = poly_add(k, basis[i], targets[i])
    residual = poly_add(ab, k, -1)
    q = [0] * (m - 1)
    rem = list(residual)
    for t in reversed(range(m - 1)):
        lead = rem[t + m]
        q[t] = lead
        for s, coeff in enumerate(z):
            rem[t + s] = (rem[t + s] - lead * coeff) % Q
    return dict(ab=ab, k=k, residual=residual, q=q, z=z, basis=basis, rem=rem)


qd = quotient(E3x3)
assert not any(qd['rem'])
assert ev(qd['residual'], 0) == 0 and ev(qd['residual'], 1) == 0 and ev(qd['residual'], 2) == 0
frag['q-basis'] = (
    f'For three claims the nodes are $0, 1, 2$, and the basis polynomials over $\\F_{{43}}$ have these coefficients of $T^0, T^1, T^2$: '
    f'$L_0 = {vec(qd["basis"][0])}$, $L_1 = {vec(qd["basis"][1])}$ and $L_2 = {vec(qd["basis"][2])}$. '
    f'The vanishing polynomial is $Z(T) = T(T - 1)(T - 2)$, with coefficients ${vec(qd["z"])}$.')
frag['q-divide'] = (
    f'Using the matrix of Section 5 in the expansion gives the coefficients of $T^0, \\ldots, T^4$ below.\n\n'
    + table(['Polynomial', 'Coefficients'],
            [['$\\revdot{\\v{A}(T)}{\\v{B}(T)}$', f'${vec(qd["ab"])}$'],
             ['$K(T)$', f'${vec(qd["k"])}$'],
             ['$R(T)$', f'${vec(qd["residual"])}$']])
    + '\n\n' + f'Dividing by $Z(T)$ leaves no remainder and gives $Q(T) = {qd["q"][0]} + {qd["q"][1]}T$. The prover sends these two coefficients before it sees the challenge.')


def lagrange_fold(items, q, mu, stated=None):
    m = len(items)
    basis, z = lagrange(m)
    lam = [ev(basis[i], mu) for i in range(m)]
    a = lin(*[(lam[i], items[i].a) for i in range(m)])
    b = lin(*[(lam[i], items[i].b) for i in range(m)])
    ga = sum(lam[i] * items[i].ga for i in range(m)) % Q
    gb = sum(lam[i] * items[i].gb for i in range(m)) % Q
    targets = [x.c for x in items] if stated is None else stated
    k_mu = sum(lam[i] * targets[i] for i in range(m)) % Q
    c = (k_mu + ev(z, mu) * ev(q, mu)) % Q
    return dict(lam=lam, a=a, b=b, ga=ga, gb=gb, k=k_mu, z=ev(z, mu), q=ev(q, mu), c=c)


LMU = 20
lf = lagrange_fold(three, qd['q'], LMU)
assert revdot(lf['a'], lf['b']) == lf['c']
assert LMU not in (0, 1, 2) and all(lf['lam']) and lf['z'] and lf['q']
assert all(revdot(lagrange_fold(three, qd['q'], t)['a'], lagrange_fold(three, qd['q'], t)['b']) == lagrange_fold(three, qd['q'], t)['c'] for t in range(Q))
A_l = combine_points(lf['lam'], [x.A for x in three])
B_l = combine_points(lf['lam'], [x.B for x in three])
assert A_l == commit(lf['a'], lf['ga']) and B_l == commit(lf['b'], lf['gb'])
frag['q-run'] = (
    f'The verifier sends $\\tau = {LMU}$. The three weights are $\\ell_i = L_i({LMU})$, which gives ${vec(lf["lam"])}$, and the same weights apply on both sides, so '
    f'$\\bar{{A}}^* = {show(A_l)}$ and $\\bar{{B}}^* = {show(B_l)}$. '
    f'The verifier computes $K({LMU}) = {lf["k"]}$, $Z({LMU}) = {lf["z"]}$ and $Q({LMU}) = {lf["q"]}$, so the new value is $c^* = {lf["k"]} + {lf["z"]} \\cdot {lf["q"]} = {lf["c"]}$. '
    f'The prover\'s folded vectors are $\\v{{a}}^* = {vec(lf["a"])}$ and $\\v{{b}}^* = {vec(lf["b"])}$, and their revdot product is ${revdot(lf["a"], lf["b"])}$. '
    f'All 43 values of $\\tau$ pass for these honest claims. The prover sent two field elements where the error matrix needed six.')

# Soundness: every Q against every challenge, with the false claim in slot 1.
stated = [x.c for x in false_list]
EF_true = error_matrix(false_list)
true_q = quotient(EF_true, stated)
assert any(true_q['rem'])
# Tabulate the polynomial identity, and confirm it against the fold itself on samples.
ab_poly = quotient(EF_true)['ab']
k_poly = quotient(EF_true, stated)['k']
z_poly = lagrange(3)[1]
ab_vals = [ev(ab_poly, t) for t in range(Q)]
k_vals = [ev(k_poly, t) for t in range(Q)]
z_vals = [ev(z_poly, t) for t in range(Q)]
for t in (0, 7, 20):
    probe = lagrange_fold(false_list, [11, 23], t)
    assert revdot(probe['a'], probe['b']) == ab_vals[t]
    assert probe['c'] == (k_vals[t] + z_vals[t] * ev([11, 23], t)) % Q
tally = {}
for q0 in range(Q):
    for q1 in range(Q):
        hits = sum(1 for t in range(Q) if ab_vals[t] == (k_vals[t] + z_vals[t] * (q0 + q1 * t)) % Q)
        tally[hits] = tally.get(hits, 0) + 1
assert max(tally) <= 4
node_hits = [t for t in (0, 1, 2) if ab_vals[t] == k_vals[t]]
assert node_hits == [0, 2]
assert min(tally) >= 2
frag['q-count'] = (
    f'Take the false list of Section 3, whose false claim sits in slot 1 and is false by ${gap}$. We tried all $43^2 = {n(Q * Q)}$ values of the two quotient coefficients against all 43 values of $\\tau$. '
    f'The best choice passes at {max(tally)} values of $\\tau$, which is the bound $2m - 2 = 4$. Every choice passes at $\\tau = 0$ and $\\tau = 2$, because at a node the weights select one claim and $Z$ vanishes, so the fold checks only the claim in that slot. '
    f'No choice passes at $\\tau = 1$, the node of the false claim.')
qlate_mu = 20
qlate_needed = (ab_vals[qlate_mu] - k_vals[qlate_mu]) * inv(z_vals[qlate_mu]) % Q
frag['q-late'] = (
    f'At $\\tau = {qlate_mu}$ the cheater needs $Q({qlate_mu}) = {qlate_needed}$, and one linear equation in the two coefficients provides it. This is why the code fixes the quotient before the challenge.')

# Six claims, two layers.
lay = []
Q1 = []
for grp in groups:
    qq = quotient(error_matrix(grp))
    assert not any(qq['rem'])
    Q1.append(qq['q'])
    res = lagrange_fold(grp, qq['q'], LMU)
    assert revdot(res['a'], res['b']) == res['c']
    lay.append(Claim(res['a'], res['b'], res['ga'], res['gb'], res['c']))
q2 = quotient(error_matrix(lay))
assert not any(q2['rem']) and len(q2['q']) == 1
SIG = 33
assert SIG not in (0, 1)
res2 = lagrange_fold(lay, q2['q'], SIG)
assert revdot(res2['a'], res2['b']) == res2['c']
assert res2['c'] and all(q2['q'])
frag['q-layers'] = (
    f'For the six claims of Section 8 with the groups unchanged, the prover sends the first layer\'s quotients $Q_0 = {vec(Q1[0])}$ and $Q_1 = {vec(Q1[1])}$. At $\\tau = {LMU}$ the groups give values $c^{{(0)}} = {lay[0].c}$ and $c^{{(1)}} = {lay[1].c}$. '
    f'The second layer has two inputs, so its quotient has the single coefficient ${q2["q"][0]}$. At $\\tau\' = {SIG}$ the final value is $c^* = {res2["c"]}$, which equals the revdot product of the final vectors. '
    f'The prover sent $2 \\cdot 2 + 1 = 5$ field elements, where Section 8 sent 14.')


def basis_gates(m):
    return 3 * m - 5


def quotient_gates(M, N):
    return basis_gates(M) + N * (2 * M - 1) + basis_gates(N) + (2 * N - 1)


def products(M, N):
    # Off-diagonal products only: an honest prover knows e_{i,i} = c_i.
    return N * M * (M - 1) + N * (N - 1)


def code_products(M, N):
    # The code's errors() forms the diagonal products as well.
    return N * M * M + N * N


# Substituting c_i for e_{i,i} leaves the quotient unchanged: L_i^2 - L_i vanishes on every node.
for m_ in (3, 7, 14):
    bas_, z_ = lagrange(m_)
    for i_ in range(m_):
        d_ = poly_add(poly_mul(bas_[i_], bas_[i_]), bas_[i_], -1)
        assert all(ev(d_, t) == 0 for t in range(m_))


NATIVE = (7, 14)
NESTED = (8, 10)
assert quotient_gates(*NATIVE) == 262 and quotient_gates(*NESTED) == 213
single_q = basis_gates(98) + 2 * 98 - 1
frag['q-costs'] = table(
    ['For 98 slots, $(M, N) = (7, 14)$', 'Book\'s two-layer error matrix', 'Code\'s quotient fold', 'Quotient fold with one layer'],
    [['Field elements the prover sends before the challenges', n(14 * 7 * 6 + 14 * 13), n(14 * 6 + 13), n(97)],
     ['Off-diagonal revdot products the prover computes', n(14 * 7 * 6 + 14 * 13), n(products(*NATIVE)), n(98 * 97)],
     ['Multiplication gates for the scalar fold', n(book_cost(*NATIVE)), n(quotient_gates(*NATIVE)), n(single_q)]])
assert products(*NATIVE) == 14 * 7 * 6 + 14 * 13 == 770 and code_products(*NATIVE) == products(*NATIVE) + 98 + 14
frag['q-why-layers'] = (
    f'With one layer over all 98 slots, the prover needs every product $\\revdot{{\\v{{a}}_i}}{{\\v{{b}}_j}}$ with $i \\neq j$, which is $98 \\cdot 97 = {n(98 * 97)}$ products. '
    f'With 14 groups of 7, it needs $7 \\cdot 6 = {7 * 6}$ products inside each group and $14 \\cdot 13 = {14 * 13}$ between the intermediate claims, '
    f'so $14 \\cdot {7 * 6} + {14 * 13} = {n(products(*NATIVE))}$ in all, the same number as the book\'s two-layer matrix. The circuit\'s count also falls, from {n(single_q)} gates to {n(quotient_gates(*NATIVE))}, '
    f'because the Lagrange weights for 98 nodes cost more to compute than the weights for 7 nodes and 14 nodes together.')
frag['q-code-diag'] = (
    f'The code forms the diagonal products as well. Its division routine [computes every product of a group, the diagonal included](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/fold_revdot.rs#L188-L224) and uses each diagonal product as that claim\'s target, '
    f'which adds $98 + 14$ products to the count, for ${n(code_products(*NATIVE))}$ in all. '
    f'This is a choice of the implementation and not a requirement of the fold, since substituting $c_i$ gives the same quotient.')
frag['q-bound'] = (
    f'The code\'s comments give each layer a failure bound of $(2m - 2)/|S|$ for a challenge uniform on a set $S$, and they put the nested challenges at $|S| = 2^{{143}}$, the [143-bit endoscalar challenges](./curve-cycles.md#shorter-challenges) of chapter 13. '
    f'The largest reduction on the nested side has $m = 10$, which gives ${2 * 10 - 2}/2^{{143}}$, and that is below $2^{{-{int(143 - math.log2(18))}}}$.')

# ---------------------------------------------------------------- Section 11
# The weights of the book, its other chapter, and the compression code are one family.
mu_c, nu_c = inv(MU), MU * NU % Q
lam = [pow(mu_c, i, Q) for i in range(3)]
eta = [pow(nu_c, j, Q) for j in range(3)]
assert lam == acc_w and eta == bcc_w
A_c = lin(*[(lam[i], three[i].a) for i in range(3)])
B_c = lin(*[(eta[i], three[i].b) for i in range(3)])
assert A_c == fold3.a and B_c == fold3.b
# structured_vectors.md: the same family with the two sides exchanged.
sv_a = lin(*[(pow(MU * NU, i, Q), three[i].a) for i in range(3)])
sv_b = lin(*[(pow(inv(MU), j, Q), three[j].b) for j in range(3)])
sv_c = sum(pow(MU, i - j, Q) * pow(NU, i, Q) * E3x3[i][j] if i >= j else pow(inv(MU), j - i, Q) * pow(NU, i, Q) * E3x3[i][j]
           for i in range(3) for j in range(3)) % Q
assert revdot(sv_a, sv_b) == sv_c
frag['reparam'] = (
    f'For the fold of Section 5, the book\'s $\\mu = {MU}$ and $\\nu = {NU}$ correspond to the plain weights $\\mu_c = \\lambda = {mu_c}$ and $\\nu_c = \\eta = {nu_c}$, and these give the same $\\v{{a}}^*$, $\\v{{b}}^*$ and $c^* = {fold3.c}$.')

# Compression's E and W, with one layer.
off = [(i, j) for i in range(3) for j in range(3) if i != j]
E_poly = [E3x3[i][j] for i, j in off] + [0, 0]
W_poly = [0] * 8
for k, (i, j) in enumerate(off):
    W_poly[7 - k] = pow(mu_c, i, Q) * pow(nu_c, j, Q) % Q
epsilon = revdot(E_poly, W_poly)
diag_sum = sum(pow(mu_c, i, Q) * pow(nu_c, i, Q) * three[i].c for i in range(3)) % Q
assert (diag_sum + epsilon) % Q == fold3.c == revdot(A_c, B_c)
assert epsilon and diag_sum
# The e-w packing is derived with its own run in the compression part of the recursion chapter.

print(json.dumps(frag))
