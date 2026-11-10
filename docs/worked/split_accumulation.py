"""Worked example for split-accumulation.md. Prints fragments as JSON.

The accumulation verifier below reads instances only: it never receives a
polynomial. Every honest run and every cheating attempt goes through the same
acc_prove, acc_verify and decide functions, so a printed verdict is a computed one.
"""
import json
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
    return sum(p[i] * q[len(q) - 1 - i] for i in range(len(p))) % Q


def lin(*terms):
    size = max(len(p) for _, p in terms)
    return [sum(k * (p[i] if i < len(p) else 0) for k, p in terms) % Q for i in range(size)]


def commit(v, gamma=0):
    return add(msm(v, GENS), mul(gamma, H))


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


# ------------------------------------------------------------- the toy circuit
# The circuit of the complete proof chapter, for x^3 + x + 5 = output.
N = 2
ROWS = [
    {('a', 0): 1, ('b', 0): -1},
    {('a', 1): 1, ('c', 0): -1},
    {('a', 0): -1, ('b', 1): 1},
    {('a', 0): 1, ('c', 1): 1},
]


def s_poly(y):
    out = [0] * (4 * N)
    for j, row in enumerate(ROWS):
        weight = pow(y, j, Q)
        for (kind, i), coeff in row.items():
            pos = {'a': 2 * N + i, 'b': 2 * N - 1 - i, 'c': 4 * N - 1 - i, 'd': i}[kind]
            out[pos] = (out[pos] + weight * coeff) % Q
    return out


def t_poly(z):
    out = [0] * (4 * N)
    for i in range(N):
        out[4 * N - 1 - i] = -(pow(z, 2 * N - 1 - i, Q) + pow(z, 2 * N + i, Q)) % Q
    return out


def trace(x):
    w1 = x * x % Q
    a, b, c = [x, w1], [x, x], [w1, w1 * x % Q]
    return [e % Q for e in c + a[::-1] + b + [0, 0]]


def step(z):
    return (z * z * z + z + 5) % Q


GAMMA_A, GAMMA_B = 17, 29


def nark_proof(input_z, z, y, x):
    """The instance and witness of one step's proof, up to the point of batching."""
    output = step(input_z)
    k = [0, 0, 0, (output - 5) % Q, 0, 0, 0, 0]
    a = trace(input_z)
    s = s_poly(y)
    t = t_poly(z)
    b = lin((1, [a[i] * pow(z, i, Q) % Q for i in range(8)]), (1, s), (1, t))
    c = ev(k, y)
    # The checks of the complete proof chapter that this chapter does not fold.
    assert revdot(a, b) == c
    assert ev(b, x) == (ev(a, x * z % Q) + ev(s, x) + ev(t, x)) % Q
    entries = [
        ('a', a, GAMMA_A, commit(a, GAMMA_A), x * z % Q, ev(a, x * z % Q)),
        ('b', b, GAMMA_B, commit(b, GAMMA_B), x, ev(b, x)),
        ('s', s, 0, commit(s), x, ev(s, x)),
        ('k', k, 0, commit(k), y, c),
    ]
    return dict(input=input_z, output=output, z=z, y=y, x=x, entries=entries)


# ------------------------------------------------- the three algorithms
class Acc:
    """An accumulator: instance (P, u, v) and witness (p, gamma)."""

    def __init__(self, P, u, v, p, gamma):
        self.P, self.u, self.v, self.p, self.gamma = P, u, v, p, gamma

    @property
    def inst(self):
        return (self.P, self.u, self.v)


def inputs_of(accs, proofs):
    """Each input as (polynomial, blinding, commitment, point, value). Accumulators come first."""
    out = [(c.p, c.gamma, c.P, c.u, c.v) for c in accs]
    for proof in proofs:
        out += [(p, g, com, at, val) for _, p, g, com, at, val in proof['entries']]
    return out


def claims_of(acc_insts, proofs):
    """The same list with only what the accumulation verifier may read."""
    out = list(acc_insts)
    for proof in proofs:
        out += [(com, at, val) for _, _, _, com, at, val in proof['entries']]
    return out


def acc_prove(accs, proofs, alpha, u, beta, gamma_f, shift=None):
    """Acc.P. The optional shift lets a cheater alter the values it sends at u."""
    items = inputs_of(accs, proofs)
    f = [0] * 8
    for p, _, _, at, _ in items:
        f = lin((alpha, f), (1, divide(p, at)))
    F = commit(f, gamma_f)
    values = [ev(p, u) for p, _, _, _, _ in items]
    if shift:
        for index, e in shift.items():
            values[index] = (values[index] + e) % Q
    new_p, new_gamma = f, gamma_f
    for p, g, _, _, _ in items:
        new_p = lin((beta, new_p), (1, p))
        new_gamma = (new_gamma * beta + g) % Q
    pf = (F, values)
    P, v = fold_instance(claims_of([c.inst for c in accs], proofs), pf, alpha, u, beta)
    return Acc(P, u, v, new_p, new_gamma), pf, f


def derive_fu(claims, values, alpha, u):
    fu = 0
    for (_, at, val), pu in zip(claims, values):
        fu = (fu * alpha + (pu - val) * inv(u - at)) % Q
    return fu


def fold_instance(claims, pf, alpha, u, beta):
    """The instance arithmetic. It takes commitments and field elements, never a polynomial."""
    F, values = pf
    fu = derive_fu(claims, values, alpha, u)
    P, v = F, fu
    for (com, _, _), pu in zip(claims, values):
        P = add(mul(beta, P), com)
        v = (v * beta + pu) % Q
    return P, v


def acc_verify(claims, new_inst, pf, alpha, u, beta):
    """Acc.V. Recompute the instance from the inputs and compare."""
    P, v = fold_instance(claims, pf, alpha, u, beta)
    return new_inst == (P, u, v)


def distinct_weights(alpha, beta, claims_count):
    """Every claim needs its own power of alpha, and every input its own power of beta."""
    return (len({pow(alpha, i, Q) for i in range(claims_count)}) == claims_count
            and len({pow(beta, i, Q) for i in range(claims_count + 1)}) == claims_count + 1)


def decide(inst, p, gamma):
    """Acc.Decide. This is the only one of the checks that reads the witness."""
    P, u, v = inst
    return commit(p, gamma) == P and ev(p, u) == v


# ------------------------------------------------------------- the chain
STATES = [3, 35, 1, 7]
assert all(step(STATES[i]) == STATES[i + 1] for i in range(3))

PROOF_CH = [dict(z=5, y=7, x=9), dict(z=16, y=34, x=37), dict(z=33, y=23, x=31)]
FOLD_CH = [dict(alpha=11, u=17, beta=23, gamma_f=5),
           dict(alpha=20, u=30, beta=25, gamma_f=7),
           dict(alpha=24, u=26, beta=38, gamma_f=42)]

proofs = [nark_proof(STATES[i], **PROOF_CH[i]) for i in range(3)]
accs, pfs, fs = [], [], []
for i in range(3):
    old = accs[-1:]
    new, pf, f = acc_prove(old, [proofs[i]], **FOLD_CH[i])
    claims = claims_of([c.inst for c in old], [proofs[i]])
    ch = {k: FOLD_CH[i][k] for k in ('alpha', 'u', 'beta')}
    assert distinct_weights(ch['alpha'], ch['beta'], len(claims))
    assert acc_verify(claims, new.inst, pf, **ch)
    assert decide(new.inst, new.p, new.gamma)
    # Honest values: the derived f(u) equals the polynomial's value.
    assert derive_fu(claims, pf[1], ch['alpha'], ch['u']) == ev(f, ch['u'])
    assert all(ch['u'] != at for _, at, _ in claims)
    assert new.P is not None and new.P not in GENS + [H] and new.v and new.v != new.u
    assert pf[0] is not None and pf[0] not in GENS + [H] and all(pf[1])
    assert all((pu - val) % Q for (_, _, val), pu in zip(claims, pf[1]))
    assert len(new.p) == 8
    accs.append(new)
    pfs.append(pf)
    fs.append(f)

# The first fold has no earlier accumulator, so it reproduces the complete proof's batch exactly.
assert fs[0] == [13, 4, 12, 3, 31, 17, 2, 0]
assert pfs[0][0] == (11, 30) and pfs[0][1] == [42, 29, 35, 29]
assert accs[0].P == (23, 24) and accs[0].v == 23 and accs[0].gamma == 27
assert accs[0].p == [17, 12, 34, 38, 23, 36, 30, 17]
for entry, expected in zip(proofs[0]['entries'], [((22, 24), 2, 9), ((1, 29), 9, 35), ((7, 6), 9, 23), ((27, 1), 7, 13)]):
    assert (entry[3], entry[4], entry[5]) == expected

# ------------------------------------------------------- the opening costs
K = 13
N4 = 2 ** K
BYTES = 32
ipa_split = 2 * K + 2           # the L_j and R_j, then the final check, stopping before the MSM
merge_two = 1 + 2 * K + 2       # chapter 11's count for one merge of two claims
assert merge_two == 29
batch_own = 5 + 1               # the proof's own batch of four polynomials and f, then v times U
atomic_step = batch_own + ipa_split + merge_two
ipa_prover = sum(2 * 2 ** j for j in range(1, K + 1))
assert ipa_prover == 32764
SHORT_POINTS, SHORT_SCALARS = 30, 9
frag['atomic-cost'] = (
    f'Take $4n = 2^{{{K}}}$ generators, which is the size chapter 09 writes as $4n$ and chapter 11 wrote as $n$. Consider one step that holds one earlier accumulator and one new proof. '
    f'The circuit batches the proof\'s claims, which takes ${batch_own}$ scalar multiplications (${batch_own - 1}$ to form $\\bar{{P}}$ and one more to scale $v$ by the inner product argument\'s point $U$), runs the proof\'s inner product argument up to the point where it hands off $\\hat{{G}}$, which takes ${ipa_split}$, '
    f'and then runs the merge, which takes ${merge_two}$, for ${atomic_step}$ in all. '
    f'Outside the circuit, the prover commits to $f$ with ${N4:,}$ scalar multiplications and runs two inner product arguments at ${ipa_prover:,}$ each, '
    f'so ${N4 + 2 * ipa_prover:,}$ at every step. '
    f'When the chain ends, the final verifier does the same work outside any circuit. It splits the last proof\'s inner product argument (${ipa_split}$), '
    f'checks a merge proof attached to that proof (${merge_two}$), and decides the merged claim once with an MSM of ${N4:,}$.')

# Which verifier steps read a witness vector.
frag['reads'] = table(
    ['Verifier step from chapter 09', 'Work for $4n = 2^{13}$', 'What it reads'],
    [
        ['Compute $t(x, z)$', 'Two geometric sums', 'Challenges'],
        ['Check the split of $b(x)$', 'A few field operations', 'Instance values'],
        ['Derive $f(u)$', 'One inverse and a few multiplications per claim', 'Instance values and prover messages'],
        ['Compute $\\bar{P}$ and $v$', '5 scalar multiplications', 'Instance commitments and prover messages'],
        ['Recompute $S$, $\\bar{A}$, $\\bar{B}$', f'3 MSMs of size $4n$, or ${3 * N4:,}$ scalar multiplications', '**Witness vectors**'],
        ['Compute $\\revdot{\\v{a}}{\\v{b}}$', f'${N4:,}$ field multiplications', '**Witness vectors**'],
        ['Recompute $\\bar{P}$ from $\\v{p}$', f'1 MSM of size $4n$, or ${N4:,}$ scalar multiplications', '**Witness vector**'],
        ['Evaluate $p(u)$', f'${N4:,}$ field multiplications', '**Witness vector**'],
    ])

# ------------------------------------------------------ one claim, split
first = proofs[0]['entries'][0]
assert commit(first[1], first[2]) == first[3] and ev(first[1], first[4]) == first[5]
frag['one-claim'] = (
    f'Take the first claim of chapter 09. Its instance is $(\\bar{{A}}, xz, a(xz)) = ({show(first[3])},\\ {first[4]},\\ {first[5]})$, '
    f'three values that anyone can hold. Its witness is $\\v{{a}} = {vec(first[1])}$ with $\\gamma_a = {first[2]}$. '
    f'Checking the claim takes both parts, since $\\dot{{\\v{{a}}}}{{\\v{{G}}}} + {first[2]} \\cdot H = {show(first[3])}$ and $a({first[4]}) = {first[5]}$.')

# How little the instance says about the polynomial.
small_count = sum(1 for a in range(Q) for b in range(Q) for c in range(Q) if ev([a, b, c], accs[0].u) == accs[0].v)
assert small_count == Q ** 2
frag['underdetermined'] = (
    f'For $(u, v) = ({accs[0].u}, {accs[0].v})$, trying all ${Q ** 3:,}$ polynomials with 3 coefficients finds ${small_count:,}$ that pass through this point, '
    f'and each extra coefficient multiplies that count by 43. With 8 coefficients there are $43^7 = {Q ** 7:,}$ of them. '
    f'In chapter 11, by contrast, $\\v{{u}} = (15, 10)$ gave one polynomial and only one.')

# -------------------------------------------------------- the first fold
frag['first-acc'] = (
    f'Chapter 09\'s proof of $z_1 = {STATES[1]}$ gives the input list, and no accumulator exists yet. Running the fold with $\\alpha = {FOLD_CH[0]["alpha"]}$, $u = {FOLD_CH[0]["u"]}$ and $\\beta = {FOLD_CH[0]["beta"]}$ '
    f'repeats chapter 09\'s batching with no changes, so $\\mathsf{{pf}}_1 = ({show(pfs[0][0])},\\ {", ".join(map(str, pfs[0][1]))})$. The result is\n\n'
    f'$$\\mathsf{{acc}}_1.\\text{{inst}} = ({show(accs[0].P)},\\ {accs[0].u},\\ {accs[0].v}), \\qquad \\mathsf{{acc}}_1.\\text{{wit}} = ({vec(accs[0].p)},\\ {accs[0].gamma}).$$')

# ------------------------------------------------------- the second proof
second = proofs[1]
ch1 = FOLD_CH[1]
frag['second-proof'] = (
    f'The second step applies $F$ to ${second["input"]}$ and outputs ${second["output"]}$. Its challenges are $z = {second["z"]}$, $y = {second["y"]}$ and $x = {second["x"]}$, so $xz = {second["x"] * second["z"] % Q}$. '
    f'The statement gives $k(Y) = {(second["output"] - 5) % Q}\\,Y^3$. The script confirms that this proof\'s revdot product and the check on the split of $b(x)$ hold, and these are its polynomials and claims:\n\n'
    + table(['Polynomial', 'Coefficients of $X^0, \\ldots, X^7$', 'Blinding', 'Commitment', 'Point', 'Value'],
            [[f'${n}$', vec(p), g, pt(c), at, val] for n, p, g, c, at, val in second['entries']]))

names = ['p_1', 'a', 'b', 's', 'k']
coms = ['\\bar{P}_1', '\\bar{A}', '\\bar{B}', 'S', 'K']
items = inputs_of(accs[:1], [second])
quotients = [divide(p, at) for p, _, _, at, _ in items]
a_pows = [pow(ch1['alpha'], 4 - i, Q) for i in range(5)]
rows = [[f'$q_{{{names[i]}}}$', a_pows[i], vec(quotients[i][:7])] for i in range(5)]
rows.append(['$f$', '', vec(fs[1][:7])])
assert fs[1] == lin(*[(a_pows[i], quotients[i]) for i in range(5)])
frag['fold-f'] = (
    f'The verifier sends $\\alpha = {ch1["alpha"]}$, whose powers give the weights in the next table. The first row divides $p_1(X) - {accs[0].v}$ by $X - {accs[0].u}$, '
    f'which is the only difference from chapter 09\'s list.\n\n'
    + table(['Quotient', 'Weight', 'Coefficients of $X^0, \\ldots, X^6$'], rows)
    + f'\n\nWith the blinding factor $\\gamma_f = {ch1["gamma_f"]}$, the prover sends $\\bar{{F}} = {show(pfs[1][0])}$.')

claims1 = claims_of([accs[0].inst], [second])
values1 = pfs[1][1]
rows, total = [], 0
for i, ((_, at, val), pu) in enumerate(zip(claims1, values1)):
    ratio = (pu - val) * inv(ch1['u'] - at) % Q
    term = a_pows[i] * ratio % Q
    assert ratio == ev(quotients[i], ch1['u'])
    total = (total + term) % Q
    rows.append([f'${names[i]}$', pu, val, (ch1['u'] - at) % Q, ratio, a_pows[i], term])
assert total == ev(fs[1], ch1['u'])
frag['fold-fu'] = (
    f'The verifier sends $u = {ch1["u"]}$, and the prover sends the five values. The verifier then derives $f(u)$ from those values and the instances:\n\n'
    + table(['Input', 'Value at $u$', 'Claimed value', '$u - x_i$', 'Ratio', 'Weight', 'Term'], rows)
    + f'\n\nThe last column sums to $f({ch1["u"]}) = {total}$, and the prover gets the same number by evaluating $f$.')

b_pows = [pow(ch1['beta'], 5 - i, Q) for i in range(6)]
rows = [['$\\bar{F}$', b_pows[0], pt(pfs[1][0]), total, ch1['gamma_f']]]
for i, (p, g, com, _, _) in enumerate(items):
    rows.append([f'${coms[i]}$', b_pows[i + 1], pt(com), values1[i], g])
rows.append(['Combined', '', f'$\\bar{{P}}_2 = {show(accs[1].P)}$', f'$v_2 = {accs[1].v}$', f'$\\gamma_2 = {accs[1].gamma}$'])
frag['fold-beta'] = (
    f'The verifier sends $\\beta = {ch1["beta"]}$. Each input carries its weight into the commitment, the value and the blinding factor.\n\n'
    + table(['Input', 'Weight', 'Commitment', 'Value at $u$', 'Blinding factor'], rows))

ip = commit(accs[1].p, accs[1].gamma)
frag['fold-result'] = (
    f'The accumulation verifier has now finished. It read no polynomial, and its recomputation gave $({show(accs[1].P)},\\ {accs[1].u},\\ {accs[1].v})$. '
    f'The prover computes the new witness from the polynomials, using the same weights, which gives $\\v{{p}}_2 = {vec(accs[1].p)}$ and $\\gamma_2 = {accs[1].gamma}$. '
    f'This vector has 8 entries, the same as $\\v{{p}}_1$.')

rows = []
for i in range(3):
    c = accs[i]
    n_inputs = 4 if i == 0 else 5
    rows.append([i + 1, f'${STATES[i + 1]} = F({STATES[i]})$', n_inputs, f'$({FOLD_CH[i]["alpha"]},\\ {FOLD_CH[i]["u"]},\\ {FOLD_CH[i]["beta"]})$',
                 f'$({show(c.P)},\\ {c.u},\\ {c.v})$', vec(c.p)])
frag['chain'] = table(['Fold', 'New proof covers', 'Input claims', '$(\\alpha, u, \\beta)$', 'Accumulator instance', 'Accumulator witness $\\v{p}$'], rows)

last = accs[2]
assert decide(last.inst, last.p, last.gamma)
frag['decide'] = (
    f'The decider receives $\\mathsf{{acc}}_3$. It computes $\\dot{{\\v{{p}}}}{{\\v{{G}}}} + {last.gamma} \\cdot H = {show(commit(last.p, last.gamma))}$, which equals $\\bar{{P}}_3$, '
    f'and it evaluates $p_3({last.u}) = {ev(last.p, last.u)}$, which equals $v_3$. It accepts. '
    f'One MSM over 8 generators and one evaluation of 8 coefficients stand in for opening all twelve polynomials of the three proofs.')

# ------------------------------------------------------------ a tree
left = nark_proof(STATES[2], z=41, y=5, x=28)
right_start = 8
right_old = nark_proof(right_start, z=22, y=15, x=27)
right = nark_proof(right_old['output'], z=17, y=5, x=38)
assert right_old['output'] == 9
acc_l = accs[1]
acc_r, pf_r, _ = acc_prove([], [right_old], alpha=26, u=20, beta=4, gamma_f=17)
assert acc_r.P not in GENS + [H, None]
assert decide(acc_r.inst, acc_r.p, acc_r.gamma)
joined, pf_j, _ = acc_prove([acc_l, acc_r], [left, right], alpha=18, u=17, beta=32, gamma_f=18)
claims_j = claims_of([acc_l.inst, acc_r.inst], [left, right])
assert len(claims_j) == 10 and all(at != 17 for _, at, _ in claims_j)
assert acc_verify(claims_j, joined.inst, pf_j, 18, 17, 32)
assert distinct_weights(18, 32, 10) and distinct_weights(26, 4, 4)
assert joined.P not in GENS + [H, None] and joined.v
assert decide(joined.inst, joined.p, joined.gamma)
frag['tree'] = (
    f'Suppose a second chain has proved ${right_old["output"]} = F({right_start})$ and reached the accumulator $({show(acc_r.P)},\\ {acc_r.u},\\ {acc_r.v})$. A node takes this one and $\\mathsf{{acc}}_2$ from its two children, '
    f'along with one new proof from each side, a proof of ${left["output"]} = F({STATES[2]})$ on the first side and a proof of ${right["output"]} = F({right_old["output"]})$ on the second. The input list has $2 + 2 \\cdot 4 = {len(claims_j)}$ claims. With $\\alpha = 18$, $u = 17$ and $\\beta = 32$, '
    f'the fold outputs $({show(joined.P)},\\ {joined.u},\\ {joined.v})$. The accumulation verifier accepts, and the decider accepts the witness ${vec(joined.p)}$. '
    f'The proof $\\mathsf{{pf}}$ grows to one point and {len(pf_j[1])} values, while the output keeps the same three-part instance and 8-entry witness.')

# ---------------------------------------------------------- comparing costs
split_one = 5 + 1            # F, the accumulator's commitment, and four from the proof
split_tree = 2 * 5 + 1
atomic_tree = 2 * (batch_own + ipa_split) + (3 + 2 * K + 2)
pf_bytes = BYTES * (1 + 5)
inst_bytes = BYTES * 3
wit_bytes = BYTES * (N4 + 1)
atomic_bytes = BYTES * (1 + K)
short_bytes = BYTES * (SHORT_POINTS + SHORT_SCALARS)
nark_inst_bytes, nark_wit_bytes = 384, 1048832
assert atomic_bytes == 448 and short_bytes == 1248
frag['compare'] = table(
    ['For $4n = 2^{13}$ and 32-byte values', 'Atomic (chapter 11)', 'Split (this chapter)'],
    [
        ['Scalar multiplications in the circuit, one proof and one accumulator', f'${atomic_step}$', f'${split_one}$'],
        ['Scalar multiplications in the circuit, two proofs and two accumulators', f'${atomic_tree}$', f'${split_tree}$'],
        ['Growth of that count with $4n$', 'Logarithmic', 'None'],
        ['Prover\'s scalar multiplications for this opening work at each step', f'${N4 + 2 * ipa_prover:,}$', f'${N4:,}$, to commit to $f$'],
        ['Accumulator data that the circuit reads', f'${atomic_bytes}$ bytes', f'${inst_bytes}$ bytes'],
        ['Proof and accumulator data handed to the next prover', f'${short_bytes + atomic_bytes:,}$ bytes', f'${nark_inst_bytes + nark_wit_bytes:,}$ bytes'],
        ['How much of that is the accumulator\'s witness', 'None', f'${wit_bytes:,}$ bytes'],
        ['Final verifier\'s scalar multiplications', f'${ipa_split} + {merge_two} + {N4:,} = {ipa_split + merge_two + N4:,}$', f'${split_one} + {N4:,} = {split_one + N4:,}$, and one evaluation'],
    ]) + (
    f'\n\nThe atomic handoff is a short proof of ${short_bytes:,}$ bytes and an accumulator of ${atomic_bytes}$ bytes. '
    f'The split handoff is chapter 09\'s proof, except that the batched $\\v{{p}}$ and $\\gamma$ at its end are now the accumulator\'s witness. '
    f'In chapter 09 those two entries were the proof\'s own batch. In this scheme a proof has no batch of its own, because Section 5 puts its claims straight into the fold, and the accumulator\'s $\\v{{p}}$ and $\\gamma$ have the same length, so the size does not change. '
    f'The handoff is therefore ${nark_inst_bytes}$ bytes of instance and ${nark_wit_bytes:,}$ bytes of witness, and the ${wit_bytes:,}$ bytes of the next row are part of that witness.')

# ------------------------------------------------------ the product relation
u1, w1 = [2, 5], [7, 3]
u2, w2 = [4, 6], [1, 8]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b)) % Q


c1, c2 = dot(u1, w1), dot(u2, w2)
r_ = 9
cross = (dot(u1, w2) + dot(u2, w1)) % Q
uf, wf = lin((1, u1), (r_, u2)), lin((1, w1), (r_, w2))
assert dot(uf, wf) == (c1 + r_ * cross + r_ * r_ * c2) % Q
assert dot(uf, wf) != (c1 + r_ * r_ * c2) % Q and cross
frag['cross-term'] = (
    f'Take $\\v{{a}}_1 = {vec(u1)}$, $\\v{{b}}_1 = {vec(w1)}$ with $c_1 = {c1}$, and $\\v{{a}}_2 = {vec(u2)}$, $\\v{{b}}_2 = {vec(w2)}$ with $c_2 = {c2}$. '
    f'At $r = {r_}$ the folded vectors are ${vec(uf)}$ and ${vec(wf)}$, and their inner product is ${dot(uf, wf)}$. '
    f'The two old values give only $c_1 + r^2 c_2 = {(c1 + r_ * r_ * c2) % Q}$. The prover supplies the cross term $E = {cross}$ before it learns $r$, '
    f'and $c_1 + r E + r^2 c_2 = {(c1 + r_ * cross + r_ * r_ * c2) % Q}$ matches.')

# ---------------------------------------------------------------- cheating
# Tampering with the output or with the prover's messages, at the second fold.
new1 = accs[1]
ch = {k: ch1[k] for k in ('alpha', 'u', 'beta')}
group = [None] + curve_points()
assert len(group) == Q
bad_P = sum(acc_verify(claims1, (c, new1.u, new1.v), pfs[1], **ch) for c in group if c != new1.P)
bad_v = sum(acc_verify(claims1, (new1.P, new1.u, w), pfs[1], **ch) for w in range(Q) if w != new1.v)
bad_F = sum(acc_verify(claims1, new1.inst, (c, values1), **ch) for c in group if c != pfs[1][0])
assert bad_P == bad_v == bad_F == 0
shift_pass = []
for index in range(5):
    for e in range(1, Q):
        changed = list(values1)
        changed[index] = (changed[index] + e) % Q
        if acc_verify(claims1, new1.inst, (pfs[1][0], changed), **ch):
            shift_pass.append((index, e))
# A shift at index i passes exactly where its two effects cancel, which depends on the challenges only.
cancelling = [i for i in range(5)
              if (pow(ch['beta'], 1 + i, Q) * pow(ch['alpha'], 4 - i, Q) * inv(ch['u'] - claims1[i][1]) + 1) % Q == 0]
assert sorted({i for i, _ in shift_pass}) == cancelling
assert len(shift_pass) == 42 * len(cancelling)
ci = cancelling[0] if cancelling else 0
cancel_pairs = sum(1 for a_ in range(1, Q) for b_ in range(1, Q)
                   if pow(b_, 1 + ci, Q) * pow(a_, 4 - ci, Q) % Q == (claims1[ci][1] - ch['u']) % Q)
frag['tamper'] = (
    f'At the second fold, we replaced $\\bar{{P}}_2$ with each of the 42 other group elements, replaced $v_2$ with each of the 42 other values, and separately replaced $\\bar{{F}}$ with each of the 42 other group elements while keeping the output. '
    f'We also shifted each of the five values at $u$ by each of the 42 nonzero amounts while keeping the output, which makes 210 more cases. '
    + (f'The accumulation verifier rejected all ${42 * 3 + 210}$ altered runs.' if not shift_pass else
       f'The accumulation verifier rejected ${42 * 3 + 210 - len(shift_pass)}$ of the ${42 * 3 + 210}$ altered runs. The other ${len(shift_pass)}$ are shifts of the value for ${names[ci]}$, and a short calculation shows why. '
       f'Shifting $h_{ci}(u)$ by $\\delta$ has two effects on $v$. It changes the derived $f(u)$ by $\\alpha^{{{4 - ci}}}\\delta/(u - x_{ci})$, and $f(u)$ enters $v$ with weight $\\beta^5$. It also changes the term $\\beta^{{{4 - ci}}} h_{ci}(u)$ by $\\beta^{{{4 - ci}}}\\delta$. Adding the two contributions gives\n\n'
       f'$$\\Delta v = \\beta^5 \\alpha^{{{4 - ci}}} \\cdot \\frac{{\\delta}}{{u - x_{ci}}} + \\beta^{{{4 - ci}}} \\delta = \\beta^{{{4 - ci}}} \\delta \\cdot \\left( \\frac{{\\beta^{{{1 + ci}}} \\alpha^{{{4 - ci}}}}}{{u - x_{ci}}} + 1 \\right).$$\n\n'
       f'The bracket is zero exactly when $\\beta^{{{1 + ci}}}\\alpha^{{{4 - ci}}} = x_{ci} - u$. Here $\\beta^{{{1 + ci}}} = {pow(ch["beta"], 1 + ci, Q)}$ and $\\alpha^{{{4 - ci}}} = {pow(ch["alpha"], 4 - ci, Q)}$, whose product is ${pow(ch["beta"], 1 + ci, Q) * pow(ch["alpha"], 4 - ci, Q) % Q}$, and $x_{ci} - u = {claims1[ci][1]} - {ch["u"]} = {(claims1[ci][1] - ch["u"]) % Q}$. '
       f'The condition holds for this input and fails for the other four, so every shift of this one value leaves the output unchanged. The output then stays the same true claim, and the prover gains nothing. '
       f'The coincidence comes from our hand-picked challenges. With $u = {ch["u"]}$ fixed, only ${cancel_pairs}$ of the ${42 * 42:,}$ pairs of nonzero $\\alpha$ and $\\beta$ satisfy the condition for this input, about 1 in ${round(42 * 42 / cancel_pairs)}$.'))

# A consistent false F passes Acc.V, and only the decider sees it.
F_pass, F_decide = 0, 0
for c in group:
    if c == pfs[1][0]:
        continue
    P_, v_ = fold_instance(claims1, (c, values1), **ch)
    assert v_ == new1.v
    F_pass += acc_verify(claims1, (P_, new1.u, v_), (c, values1), **ch)
    F_decide += decide((P_, new1.u, v_), new1.p, new1.gamma)
assert F_pass == 42 and F_decide == 0
other_F = next(c for c in group if c not in (pfs[1][0], None) and c not in GENS
               and fold_instance(claims1, (c, values1), **ch)[0] not in GENS + [H, None])
other_P, _ = fold_instance(claims1, (other_F, values1), **ch)
# A cheater who knows what its false F commits to: the MSM passes, the evaluation fails.
f_star = list(fs[1])
f_star[0] = (f_star[0] + 1) % Q
F_star = commit(f_star, ch1['gamma_f'])
P_star, v_star = fold_instance(claims1, (F_star, values1), **ch)
assert acc_verify(claims1, (P_star, ch['u'], v_star), (F_star, values1), **ch)
p_star = lin((pow(ch['beta'], 5, Q), f_star), *[(pow(ch['beta'], 4 - i, Q), items[i][0]) for i in range(5)])
assert commit(p_star, new1.gamma) == P_star
assert ev(p_star, ch['u']) != v_star and not decide((P_star, ch['u'], v_star), p_star, new1.gamma)
frag['consistent'] = (
    f'For example, a prover can send $\\bar{{F}}^* = {show(other_F)}$ and output the matching point {pt(other_P)}. The accumulation verifier recomputes that same point and accepts. '
    f'This happens for all 42 false values of $\\bar{{F}}$, because the verifier has no way to see what $\\bar{{F}}$ commits to.\n\n'
    f'A prover who wants to survive the decider as well has to know a vector behind its false commitment. Say it takes $\\v{{f}}^*$ equal to $\\v{{f}}$ with the constant coefficient raised by 1, '
    f'so that $\\bar{{F}}^* = {show(F_star)}$ and the output is $({show(P_star)},\\ {ch["u"]},\\ {v_star})$. Combining $\\v{{f}}^*$ with the other polynomials gives $\\v{{p}}^* = {vec(p_star)}$, '
    f'and the decider\'s MSM accepts it, since it commits to {pt(P_star)}. The evaluation check rejects, because $p^*({ch["u"]}) = {ev(p_star, ch["u"])}$ while the output states ${v_star}$.')

# A false accumulator value carried through honest folds.
DELTA = 1
false1 = Acc(accs[0].P, accs[0].u, (accs[0].v + DELTA) % Q, accs[0].p, accs[0].gamma)
false2, fpf2, _ = acc_prove([false1], [proofs[1]], **FOLD_CH[1])
assert acc_verify(claims_of([false1.inst], [proofs[1]]), false2.inst, fpf2, **ch)
false3, fpf3, _ = acc_prove([false2], [proofs[2]], **FOLD_CH[2])
ch2 = {k: FOLD_CH[2][k] for k in ('alpha', 'u', 'beta')}
assert acc_verify(claims_of([false2.inst], [proofs[2]]), false3.inst, fpf3, **ch2)
assert not decide(false1.inst, false1.p, false1.gamma)
assert not decide(false2.inst, false2.p, false2.gamma)
assert not decide(false3.inst, false3.p, false3.gamma)
assert false2.p == accs[1].p and false3.p == accs[2].p and false3.P == accs[2].P
fold3_mult = (-pow(FOLD_CH[2]['beta'], 5, Q) * pow(FOLD_CH[2]['alpha'], 4, Q) * inv(FOLD_CH[2]['u'] - FOLD_CH[1]['u'])) % Q
assert (false3.v - ev(false3.p, false3.u)) % Q == fold3_mult * (false2.v - ev(false2.p, false2.u)) % Q
rows = []
for name, c in (('$\\mathsf{acc}_1$', false1), ('$\\mathsf{acc}_2$', false2), ('$\\mathsf{acc}_3$', false3)):
    rows.append([name, pt(c.P), c.u, c.v, ev(c.p, c.u), (c.v - ev(c.p, c.u)) % Q])
frag['false-carry'] = (
    f'Take the run of Section 6, but let the prover state $v_1 = {false1.v}$ where the true value is ${accs[0].v}$. Every later step is honest, with the same challenges.\n\n'
    + table(['Accumulator', '$\\bar{P}$', '$u$', 'Stated $v$', 'True $p(u)$', 'Gap'], rows)
    + '\n\nThe accumulation verifier accepts both folds, because the output instance is what it recomputes. The decider rejects the last accumulator, since its value differs from the polynomial\'s. '
    + f'The gap is the same at the last two folds only by coincidence. At the third fold the multiplier $-\\beta^5\\alpha^4/(u - u_{{\\text{{old}}}})$ of the gap formula above equals '
    + f'$-{FOLD_CH[2]["beta"]}^5 \\cdot {FOLD_CH[2]["alpha"]}^4 / ({FOLD_CH[2]["u"]} - {FOLD_CH[1]["u"]}) = {fold3_mult}$, so it passes the gap on unchanged.')

# The gap formula, and an exhaustive count over the next fold's challenges.
base_items = inputs_of([accs[0]], [proofs[1]])
points = [it[3] for it in base_items]
polys_ = [it[0] for it in base_items]
ys = [it[4] for it in base_items]
gaps = 0
runs = 0
pass_runs = []
for u in range(Q):
    if u in points:
        continue
    q_at = [ev(divide(polys_[i], points[i]), u) for i in range(5)]
    p_at = [ev(polys_[i], u) for i in range(5)]
    for alpha in range(Q):
        for beta in range(Q):
            runs += 1
            powa = [pow(alpha, 4 - i, Q) for i in range(5)]
            powb = [pow(beta, 5 - i, Q) for i in range(6)]
            f_true = sum(powa[i] * q_at[i] for i in range(5)) % Q
            derived = (powa[0] * (p_at[0] - ys[0] - DELTA) * inv(u - points[0])
                       + sum(powa[i] * (p_at[i] - ys[i]) * inv(u - points[i]) for i in range(1, 5))) % Q
            stated = (powb[0] * derived + sum(powb[i + 1] * p_at[i] for i in range(5))) % Q
            true_v = (powb[0] * f_true + sum(powb[i + 1] * p_at[i] for i in range(5))) % Q
            gap = (stated - true_v) % Q
            assert gap == (-pow(beta, 5, Q) * pow(alpha, 4, Q) * DELTA * inv(u - points[0])) % Q
            if gap == 0:
                pass_runs.append((alpha, u, beta))
assert all(a == 0 or b == 0 for a, _, b in pass_runs)
nz_runs = sum(1 for u in range(Q) if u not in points) * 42 * 42
assert sum(1 for a, _, b in pass_runs if a and b) == 0
n_u = sum(1 for u in range(Q) if u not in points)
expected_gap = (-pow(ch1['beta'], 5, Q) * pow(ch1['alpha'], 4, Q) * DELTA * inv(ch1['u'] - accs[0].u)) % Q
assert expected_gap == (false2.v - ev(false2.p, false2.u)) % Q
frag['gap-count'] = (
    f'For the fold above, the formula gives $-{ch1["beta"]}^5 \\cdot {ch1["alpha"]}^4 \\cdot {DELTA} / ({ch1["u"]} - {accs[0].u}) = {expected_gap}$, which matches the table. '
    f'We also ran all ${nz_runs:,}$ choices of nonzero $\\alpha$, nonzero $\\beta$ and an allowed $u$ out of {n_u} values, with the gap computed directly and compared with the formula. The allowed values of $u$ leave out the {len(set(points))} distinct points {", ".join(map(str, dict.fromkeys(points)))}, where a quotient\'s denominator $u - x_i$ would vanish. No run gives a zero gap.')

# Swapping a false accumulator for an unrelated true one.
swap_in = acc_r
swapped, spf, _ = acc_prove([swap_in], [proofs[1]], **FOLD_CH[1])
assert acc_verify(claims_of([swap_in.inst], [proofs[1]]), swapped.inst, spf, **ch)
assert decide(swapped.inst, swapped.p, swapped.gamma)
assert not acc_verify(claims_of([false1.inst], [proofs[1]]), swapped.inst, spf, **ch)
frag['swap'] = (
    f'Suppose the prover holds the false $\\mathsf{{acc}}_1$ from above and wants to be rid of it. It folds an unrelated true accumulator $({show(swap_in.P)},\\ {swap_in.u},\\ {swap_in.v})$ in its place, '
    f'and gets the output $({show(swapped.P)},\\ {swapped.u},\\ {swapped.v})$. If the circuit reads the swapped instance, the accumulation verifier accepts and the decider accepts. '
    f'Run against the instance of the false $\\mathsf{{acc}}_1$, the same output fails.')

# An accumulator chosen after the challenges.
ch_a, ch_u, ch_b = ch1['alpha'], ch1['u'], ch1['beta']
d_ = 3  # the stated value's error
weight = pow(ch_b, 5, Q) * pow(ch_a, 4, Q) * inv(ch_u - accs[0].u) % Q
e_ = weight * d_ * inv(weight + pow(ch_b, 4, Q)) % Q
late = Acc(accs[0].P, accs[0].u, (accs[0].v + d_) % Q, accs[0].p, accs[0].gamma)
assert not decide(late.inst, late.p, late.gamma)
lnew, lpf, _ = acc_prove([late], [proofs[1]], ch_a, ch_u, ch_b, ch1['gamma_f'], shift={0: e_})
late_claims = claims_of([late.inst], [proofs[1]])
assert acc_verify(late_claims, lnew.inst, lpf, ch_a, ch_u, ch_b)
assert decide(lnew.inst, lnew.p, lnew.gamma)
beta_pass = []
for beta in range(Q):
    P_, v_ = fold_instance(late_claims, lpf, ch_a, ch_u, beta)
    # The honest polynomial for this beta, with the prover's message left as sent.
    f_ = lin(*[(pow(ch_a, 4 - i, Q), quotients[i]) for i in range(5)])
    p_ = f_
    g_ = ch1['gamma_f']
    for pol, gam, _, _, _ in base_items:
        p_ = lin((beta, p_), (1, pol))
        g_ = (g_ * beta + gam) % Q
    if decide((P_, ch_u, v_), p_, g_):
        beta_pass.append(beta)
assert ch_b in beta_pass and len(beta_pass) == 2
frag['late'] = (
    f'Suppose the transcript leaves out the accumulator, so that the prover knows $\\alpha = {ch_a}$, $u = {ch_u}$ and $\\beta = {ch_b}$ before it fixes $v_1$. '
    f'It states the false value $v_1 = {late.v}$, an error of ${d_}$, and it sends ${lpf[1][0]}$ in place of the true $p_1({ch_u}) = {values1[0]}$, a shift of ${e_}$ that solves one linear equation. '
    f'The two errors cancel in $v_2$, so the output is the true claim $({show(lnew.P)},\\ {lnew.u},\\ {lnew.v})$. The accumulation verifier accepts and the decider accepts, although $\\mathsf{{acc}}_1$ was false. '
    f'The remedy is for the transcript to absorb $\\mathsf{{acc}}_1.\\text{{inst}}$ before it draws $\\alpha$, so that $v_1$ is fixed before any challenge exists. '
    f'Even a weaker ordering leaves the prover little. If it fixes the same two messages after seeing $\\alpha$ and $u$ but before $\\beta$, then trying all 43 values of $\\beta$ finds {len(beta_pass)} that pass, $\\beta = {beta_pass[0]}$ and $\\beta = {beta_pass[1]}$.')

# A prover who knows relations among the toy generators.
logs = [log(g, G[0]) for g in GENS]
assert all(logs)
target_v = (accs[1].v + 1) % Q
want = (target_v - ev(accs[1].p, accs[1].u)) % Q
# Change entries i and j so that the commitment stays put and the value moves by want.
i_, j_ = next((i, j) for i in range(8) for j in range(i + 1, 8)
              if (logs[i] * pow(accs[1].u, j, Q) - logs[j] * pow(accs[1].u, i, Q)) % Q)
ui, uj = pow(accs[1].u, i_, Q), pow(accs[1].u, j_, Q)
det = (logs[i_] * uj - logs[j_] * ui) % Q
d_i = (-logs[j_] * want) * inv(det) % Q
d_j = (logs[i_] * want) * inv(det) % Q
forged = list(accs[1].p)
forged[i_] = (forged[i_] + d_i) % Q
forged[j_] = (forged[j_] + d_j) % Q
assert commit(forged, accs[1].gamma) == accs[1].P and ev(forged, accs[1].u) == target_v
assert decide((accs[1].P, accs[1].u, target_v), forged, accs[1].gamma)
frag['binding'] = (
    f'Using the known discrete logs of the toy generators, a prover can state the false $v_2 = {target_v}$ and present the witness ${vec(forged)}$. '
    f'This vector commits to the same $\\bar{{P}}_2 = {show(accs[1].P)}$, and it evaluates to ${target_v}$ at $u = {accs[1].u}$, so the decider accepts it.')

print(json.dumps(frag))
