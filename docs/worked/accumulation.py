"""Worked example for accumulation.md. Prints fragments as JSON."""
import json
from functools import lru_cache

import toy_curve
from toy_curve import G, H, Q, U, show

frag = {}


# ------------------------------------------------------------------ two groups
# The toy curve gives anyone every discrete log, so a forgery exists there for
# almost any claim. To count what a prover can do when no relation among the
# generators is known, the script also runs the protocol in a formal group: a
# point is its coefficient vector on (G_0, G_1, G_2, G_3, U).
@lru_cache(maxsize=None)
def add(a, c):
    return toy_curve.add(a, c)


@lru_cache(maxsize=None)
def mul(k, a):
    return toy_curve.mul(k % Q, a)


class Curve:
    add = staticmethod(add)
    mul = staticmethod(mul)
    G = list(G)
    U = U
    zero = None


class Formal:
    @staticmethod
    def add(a, c):
        return tuple((s + t) % Q for s, t in zip(a, c))

    @staticmethod
    def mul(k, a):
        return tuple(k * s % Q for s in a)

    G = [tuple(int(i == j) for j in range(5)) for i in range(4)]
    U = tuple(int(j == 4) for j in range(5))
    zero = (0, 0, 0, 0, 0)


def msm(grp, scalars, points):
    out = grp.zero
    for s, p in zip(scalars, points):
        out = grp.add(out, grp.mul(s, p))
    return out


def neg(a):
    return mul(Q - 1, a)


def inv(a):
    return pow(a, -1, Q)


def dot(a, b):
    return sum(s * t for s, t in zip(a, b)) % Q


def vec(a):
    return '(' + ', '.join(map(str, a)) + ')'


def powers(x, n=4):
    return [pow(x, i, Q) for i in range(n)]


def poly_eval(a, x):
    return dot(a, powers(x, len(a)))


def nondegenerate(*points):
    for p in points:
        assert p is not None and p not in G and p not in (H, U), p


# ------------------------------------------------------------------ the polynomial g
def g_factors(us, x):
    k = len(us)
    return [(inv(u) + u * pow(x, 2 ** (k - j - 1), Q)) % Q for j, u in enumerate(us)]


def g_eval(us, x):
    out = 1
    for f in g_factors(us, x):
        out = out * f % Q
    return out


def g_coeffs(us):
    """Coefficients of the product, built from the factors of chapter 07."""
    k = len(us)
    out = [1]
    for j, u in enumerate(us):
        e = 2 ** (k - j - 1)
        new = [0] * max(len(out), e + len(out))
        for i, c in enumerate(out):
            new[i] = (new[i] + inv(u) * c) % Q
            new[i + e] = (new[i + e] + u * c) % Q
        out = new
    return out


# ------------------------------------------------------------------ the IPA, symmetric form
def cross(grp, a, b, g, gen):
    h = len(a) // 2
    L = grp.add(msm(grp, a[h:], g[:h]), grp.mul(dot(a[h:], b[:h]), gen))
    R = grp.add(msm(grp, a[:h], g[h:]), grp.mul(dot(a[:h], b[h:]), gen))
    return L, R


def ipa_prove(grp, a, x, us, weight=1):
    """Folds honestly, returns rounds, final scalar, b-hat, and the folded generator."""
    gen = grp.mul(weight, grp.U)
    a, b, g = list(a), powers(x, len(a)), list(grp.G)
    rounds = []
    for u in us:
        L, R = cross(grp, a, b, g, gen)
        rounds.append((L, R))
        h = len(a) // 2
        ui = inv(u)
        a = [(u * a[i] + ui * a[i + h]) % Q for i in range(h)]
        b = [(ui * b[i] + u * b[i + h]) % Q for i in range(h)]
        g = [grp.add(grp.mul(ui, g[i]), grp.mul(u, g[i + h])) for i in range(h)]
    return rounds, a[0], b[0], g[0]


def left_side(grp, start, rounds, us):
    out = start
    for (L, R), u in zip(rounds, us):
        out = grp.add(out, grp.add(grp.mul(inv(u * u % Q), L), grp.mul(u * u % Q, R)))
    return out


def right_side(grp, a_hat, g_hat, b_hat, weight=1):
    return grp.mul(a_hat, grp.add(g_hat, grp.mul(weight * b_hat, grp.U)))


def decide(grp, g_hat, us):
    return g_hat == msm(grp, g_coeffs(us), grp.G)


def merge(grp, claims, x, alpha, tau, us_m, polys=None, hidden=None):
    """The merge of Section 5. claims is a list of (point, challenges).

    polys optionally replaces the polynomials the prover really holds, so a
    prover with a false claim can be run. Returns everything a table needs.
    """
    n = len(claims)
    weights = [pow(alpha, i, Q) for i in range(n)]
    C = grp.zero
    for w, (pt, _) in zip(weights, claims):
        C = grp.add(C, grp.mul(w, pt))
    v = sum(w * g_eval(us, x) for w, (_, us) in zip(weights, claims)) % Q
    held = polys if polys is not None else [g_coeffs(us) for _, us in claims]
    a = [sum(w * p[i] for w, p in zip(weights, held)) % Q for i in range(4)]
    start = grp.add(C, grp.mul(tau * v, grp.U))
    rounds, a_hat, b_hat, g_hat = ipa_prove(grp, a, x, us_m, tau)
    lhs = left_side(grp, start, rounds, us_m)
    rhs = right_side(grp, a_hat, g_hat, b_hat, tau)
    return dict(C=C, v=v, a=a, start=start, rounds=rounds, a_hat=a_hat, b_hat=b_hat,
                g_hat=g_hat, lhs=lhs, rhs=rhs, accepted=lhs == rhs)


# ------------------------------------------------------------------ claim 1, from chapter 07
a1, x1, u1 = [7, 2, 5, 3], 9, [15, 10]
y1 = poly_eval(a1, x1)
C1 = msm(Curve, a1, G)
P1 = add(C1, mul(y1, U))
rounds1, ahat1, bhat1, Ghat1 = ipa_prove(Curve, a1, x1, u1)
lhs1 = left_side(Curve, P1, rounds1, u1)
assert y1 == 37 and C1 == (27, 30) and P1 == (5, 29)
assert rounds1 == [((22, 7), (30, 8)), ((28, 21), (14, 9))]
assert (ahat1, bhat1, Ghat1) == (4, 19, (20, 25))
assert lhs1 == (14, 22) == right_side(Curve, ahat1, Ghat1, bhat1)
coeffs1 = g_coeffs(u1)
assert coeffs1 == [41, 15, 23, 21] and g_eval(u1, x1) == bhat1
assert decide(Curve, Ghat1, u1)

f1 = g_factors(u1, x1)
frag['split-run'] = '\n'.join([
    f'Here is the split applied to the run of chapter 07, with $\\v{{u}} = {vec(u1)}$. The prover sends $\\hat{{G}} = {show(Ghat1)}$ along with the proof.', '',
    '| Verifier step | Computation | Result |', '| --- | --- | --- |',
    f'| Combine the cross terms | $P + \\sum_j (u_j^{{-2}} \\cdot L_j + u_j^{{2}} \\cdot R_j)$ | ${show(lhs1)}$ |',
    f'| Evaluate $g_{{\\v{{u}}}}$ at $x = {x1}$ | ${f1[0]} \\cdot {f1[1]}$, one factor per round | $\\hat{{b}} = {bhat1}$ |',
    f'| Final check with the supplied point | ${ahat1} \\cdot ({show(Ghat1)} + {bhat1} \\cdot U)$ | ${show(lhs1)}$ |',
    f'| Output | The claim $(\\hat{{G}}, \\v{{u}})$ | $({show(Ghat1)},\\ {vec(u1)})$ |',
])

# ------------------------------------------------------------------ a false value, passing
y_false = 38
P_false = add(C1, mul(y_false, U))
lhs_false = left_side(Curve, P_false, rounds1, u1)
delta_forge = inv(ahat1)
Gstar = add(Ghat1, mul(delta_forge, U))
assert lhs_false != right_side(Curve, ahat1, Ghat1, bhat1)
assert lhs_false == right_side(Curve, ahat1, Gstar, bhat1)
assert not decide(Curve, Gstar, u1)
nondegenerate(lhs_false, Gstar)
frag['forge'] = (
    f'Take the false value $y = {y_false}$ from chapter 07, where the true value is ${y1}$. The statement point now carries an extra $1 \\cdot U$, and honest folding keeps it, '
    f'so the folded point is ${show(lhs_false)}$. With the true $\\hat{{G}} = {show(Ghat1)}$ the final check fails. The prover keeps $\\hat{{a}} = {ahat1}$ and instead supplies '
    f'$\\hat{{G}}^* = \\hat{{G}} + {delta_forge} \\cdot U = {show(Gstar)}$, where ${delta_forge}$ is the inverse of ${ahat1}$ modulo 43. '
    f'The right side becomes ${ahat1} \\cdot ({show(Gstar)} + {bhat1} \\cdot U) = {show(lhs_false)}$, so the check passes. '
    f'Only the claim is wrong, because $\\dot{{\\v{{g}}_{{\\v{{u}}}}}}{{\\v{{G}}}} = {show(Ghat1)}$ and not ${show(Gstar)}$.'
)

frag['decide-one'] = (
    f'For the claim $({show(Ghat1)},\\ {vec(u1)})$, the factors $(23 + 15X^2)(13 + 10X)$ multiply out to the coefficients ${vec(coeffs1)}$, and the MSM with $\\v{{G}}$ gives ${show(Ghat1)}$, so the decider accepts. '
    f'For the forged claim from the last section, the same MSM gives the same point, which differs from ${show(Gstar)}$, so the decider rejects.'
)

# ------------------------------------------------------------------ costs
k_real, n_real, N_claims = 13, 2 ** 13, 1000
acc_scalars = k_real
acc_bytes = (1 + k_real) * 32
ipa_points = 2 * k_real
merge_proof_bytes = (ipa_points + 1) * 32
fold_g_cost = sum(n_real >> j for j in range(k_real))
cross_cost = sum(n_real >> j for j in range(k_real))
prover_cost = fold_g_cost + cross_cost
assert prover_cost == 4 * n_real - 4
frag['pile-up'] = (
    f'With $n = 2^{{{k_real}}}$ and a hypothetical ${N_claims:,}$ steps, checking every claim directly takes ${N_claims:,}$ MSMs of ${n_real:,}$ terms, or ${N_claims * n_real:,}$ scalar multiplications. '
    f'The statement would also carry ${N_claims:,}$ points and ${N_claims * k_real:,}$ challenges.'
)

# ------------------------------------------------------------------ evaluating g against direct evaluation
x_m = 29
vals1 = g_factors(u1, x_m)
g1_at = g_eval(u1, x_m)
assert g1_at == poly_eval(coeffs1, x_m)
frag['spot-one'] = (
    f'Take the claim from chapter 07 and the point $x = {x_m}$. The two factors of $g_{{\\v{{u}}}}$ are $23 + 15 \\cdot {x_m}^2 = {vals1[0]}$ and $13 + 10 \\cdot {x_m} = {vals1[1]}$, '
    f'and their product is ${g1_at}$. Evaluating the four coefficients ${vec(coeffs1)}$ directly gives ${g1_at}$ as well, but that route needs all $n$ of them, while the factors need only $k$ terms.'
)

# Two claimed polynomials can only agree at few points.
diff = [(-2 * 7 * 20) % Q, (2 * 7 + 2 * 20 + 7 * 20) % Q, (-(2 + 7 + 20)) % Q, 1]
roots = [x for x in range(Q) if poly_eval(diff, x) == 0]
assert roots == [2, 7, 20]
h1 = [(s + t) % Q for s, t in zip(coeffs1, diff)]
agree = [x for x in range(Q) if poly_eval(h1, x) == g_eval(u1, x)]
assert agree == roots
worst = 0
for c0 in range(0, 43, 5):
    for c1 in range(0, 43, 5):
        for c2 in range(0, 43, 5):
            for c3 in range(0, 43, 5):
                d = [c0, c1, c2, c3]
                if any(d):
                    worst = max(worst, sum(poly_eval(d, x) == 0 for x in range(Q)))
assert worst <= 3
frag['spot-count'] = (
    f'Suppose that the point in a claim commits to $h$ with coefficients ${vec(h1)}$ instead of $g_{{\\v{{u}}}}$. We chose the difference $h - g_{{\\v{{u}}}} = (X-2)(X-7)(X-20)$ to have as many roots as a cubic can. '
    f'Testing all 43 points, the two polynomials agree at $x \\in \\{{{", ".join(map(str, agree))}\\}}$ and nowhere else, so the spot check catches this claim at ${Q - len(agree)}$ of the 43 points.'
)

# ------------------------------------------------------------------ claim 2
a2, x2, u2 = [3, 1, 8, 4], 5, [3, 5]
y2 = poly_eval(a2, x2)
C2 = msm(Curve, a2, G)
P2 = add(C2, mul(y2, U))
rounds2, ahat2, bhat2, Ghat2 = ipa_prove(Curve, a2, x2, u2)
lhs2 = left_side(Curve, P2, rounds2, u2)
assert lhs2 == right_side(Curve, ahat2, Ghat2, bhat2)
coeffs2 = g_coeffs(u2)
assert decide(Curve, Ghat2, u2) and g_eval(u2, x2) == bhat2
nondegenerate(C2, P2, Ghat2, lhs2)
assert Ghat2 != Ghat1
frag['claims'] = '\n'.join([
    '| | Claim 1 | Claim 2 |', '| --- | --- | --- |',
    f'| Polynomial opened | $(7, 2, 5, 3)$ at $x_1 = {x1}$ | ${vec(a2)}$ at $x_2 = {x2}$ |',
    f'| Value | ${y1}$ | ${y2}$ |',
    f'| First round cross terms | $L = {show(rounds1[0][0])}$, $R = {show(rounds1[0][1])}$ | $L = {show(rounds2[0][0])}$, $R = {show(rounds2[0][1])}$ |',
    f'| Second round cross terms | $L = {show(rounds1[1][0])}$, $R = {show(rounds1[1][1])}$ | $L = {show(rounds2[1][0])}$, $R = {show(rounds2[1][1])}$ |',
    f'| Challenges | $\\v{{u}}_1 = {vec(u1)}$ | $\\v{{u}}_2 = {vec(u2)}$ |',
    f'| Final scalar | ${ahat1}$ | ${ahat2}$ |',
    f'| Supplied point | $\\hat{{G}}_1 = {show(Ghat1)}$ | $\\hat{{G}}_2 = {show(Ghat2)}$ |',
    f'| Final check, both sides | ${show(lhs1)}$ | ${show(lhs2)}$ |',
])

# ------------------------------------------------------------------ the merge
alpha, tau, u_m = 16, 22, [8, 12]
claims12 = [(Ghat1, u1), (Ghat2, u2)]
m = merge(Curve, claims12, x_m, alpha, tau, u_m)
assert m['accepted']
g1x, g2x = g_eval(u1, x_m), g_eval(u2, x_m)
assert m['v'] == (g1x + alpha * g2x) % Q == poly_eval(m['a'], x_m)
assert m['a'] == [(s + alpha * t) % Q for s, t in zip(coeffs1, coeffs2)]
assert m['C'] == msm(Curve, m['a'], G)
assert m['b_hat'] == g_eval(u_m, x_m) and m['g_hat'] == msm(Curve, g_coeffs(u_m), G)
nondegenerate(m['C'], m['start'], m['g_hat'], m['lhs'])
for L, R in m['rounds']:
    nondegenerate(L, R)
assert m['g_hat'] not in (Ghat1, Ghat2)
assert m['v'] not in (0, 1) and m['C'] != mul(tau, U)
assert m['C'] != m['g_hat'] and len({m['C'], m['start'], m['lhs'], m['g_hat'], Ghat1, Ghat2}) == 6
assert m['start'] not in (Ghat1, Ghat2, m['C'])
Ghat_m = m['g_hat']
coeffs_m = g_coeffs(u_m)
assert decide(Curve, Ghat_m, u_m)

fm1, fm2 = g_factors(u1, x_m), g_factors(u2, x_m)
frag['merge-setup'] = '\n'.join([
    f'The verifier sends $x_M = {x_m}$ and $\\alpha = {alpha}$, then computes the merged commitment and value from public data:', '',
    '| Quantity | Computation | Result |', '| --- | --- | --- |',
    f'| $g_1(x_M)$ | ${fm1[0]} \\cdot {fm1[1]}$ | ${g1x}$ |',
    f'| $g_2(x_M)$ | ${fm2[0]} \\cdot {fm2[1]}$ | ${g2x}$ |',
    f'| $v_M$ | ${g1x} + {alpha} \\cdot {g2x}$ | ${m["v"]}$ |',
    f'| $C_M$ | ${show(Ghat1)} + {alpha} \\cdot {show(Ghat2)}$ | ${show(m["C"])}$ |', '',
    f'The prover computes the two coefficient vectors from the public challenges, namely $\\v{{g}}_1 = {vec(coeffs1)}$ and $\\v{{g}}_2 = {vec(coeffs2)}$, and combines them into $\\v{{a}}_M = \\v{{g}}_1 + {alpha}\\v{{g}}_2 = {vec(m["a"])}$. '
    f'Committing to this vector directly gives ${show(m["C"])}$, and evaluating it at ${x_m}$ gives ${m["v"]}$, so the claim is true.',
])

t_u = mul(tau, U)
start_m = m['start']
frag['merge-start'] = (
    f'The verifier then sends $\\tau = {tau}$. Both sides form the statement point $P_M = C_M + (\\tau v_M) \\cdot U = {show(m["C"])} + {tau * m["v"] % Q} \\cdot U = {show(start_m)}$, '
    f'and the rounds use $\\tau \\cdot U = {show(t_u)}$ as the value generator.'
)

(lm1, rm1), (lm2, rm2) = m['rounds']
after1 = left_side(Curve, start_m, [m['rounds'][0]], [u_m[0]])
assert after1 not in (start_m, m['lhs'], m['C'], Ghat_m)
frag['merge-rounds'] = '\n'.join([
    '| Round $j$ | $L_j$ | $R_j$ | $u_j$ | Folded point |', '| --- | --- | --- | --- | --- |',
    f'| 1 | ${show(lm1)}$ | ${show(rm1)}$ | ${u_m[0]}$ | ${show(after1)}$ |',
    f'| 2 | ${show(lm2)}$ | ${show(rm2)}$ | ${u_m[1]}$ | ${show(m["lhs"])}$ |',
])

fmm = g_factors(u_m, x_m)
frag['merge-final'] = (
    f'The prover sends $\\hat{{a}}_M = {m["a_hat"]}$ and supplies $\\hat{{G}}_M = {show(Ghat_m)}$. The verifier computes $\\hat{{b}}_M = g_M({x_m}) = {fmm[0]} \\cdot {fmm[1]} = {m["b_hat"]}$ from the challenges $\\v{{u}}_M = {vec(u_m)}$, and the final check is\n\n'
    f'$${show(m["lhs"])} = {m["a_hat"]} \\cdot \\left({show(Ghat_m)} + ({tau} \\cdot {m["b_hat"]}) \\cdot U\\right).$$\n\n'
    f'Both sides are the same point, so the verifier accepts and outputs the single claim $({show(Ghat_m)},\\ {vec(u_m)})$.'
)

frag['merge-decide'] = (
    f'The decider multiplies out $g_M$ to get the coefficients ${vec(coeffs_m)}$, computes the MSM with $\\v{{G}}$, and gets ${show(Ghat_m)}$, so it accepts. '
    f'This one MSM is the only linear group work outside the prover. We can also check what it vouches for by running the two MSMs it replaced, which give $\\dot{{\\v{{g}}_1}}{{\\v{{G}}}} = {show(Ghat1)}$ and $\\dot{{\\v{{g}}_2}}{{\\v{{G}}}} = {show(Ghat2)}$, the two input points.'
)

# ------------------------------------------------------------------ a chain of merges
chain_inputs = [
    ([6, 2, 9, 1], 4, [7, 16], 21, 3, 14, [12, 18]),
    ([2, 8, 1, 5], 3, [2, 17], 26, 10, 22, [3, 8]),
]
acc, acc_u = Ghat_m, u_m
rows = [f'| 1 and 2 | ${x_m}$ | ${alpha}$ | ${show(Ghat_m)}$ | ${vec(u_m)}$ |']
next_claim = 3
seen_outputs = {Ghat1, Ghat2, Ghat_m}
chain_accs = []
for a_c, x_c, u_c, xm_c, alpha_c, tau_c, um_c in chain_inputs:
    y_c = poly_eval(a_c, x_c)
    start_c = add(msm(Curve, a_c, G), mul(y_c, U))
    rounds_c, ahat_c, bhat_c, Ghat_c = ipa_prove(Curve, a_c, x_c, u_c)
    lhs_c = left_side(Curve, start_c, rounds_c, u_c)
    assert lhs_c == right_side(Curve, ahat_c, Ghat_c, bhat_c)
    chain_accs.append(((acc, acc_u), (Ghat_c, u_c), lhs_c))
    assert decide(Curve, Ghat_c, u_c)
    nondegenerate(Ghat_c)
    mc = merge(Curve, [(acc, acc_u), (Ghat_c, u_c)], xm_c, alpha_c, tau_c, um_c)
    assert mc['accepted'] and decide(Curve, mc['g_hat'], um_c)
    nondegenerate(mc['g_hat'])
    rows.append(f'| Accumulator and claim {next_claim}, $({show(Ghat_c)},\\ {vec(u_c)})$ | ${xm_c}$ | ${alpha_c}$ | ${show(mc["g_hat"])}$ | ${vec(um_c)}$ |')
    assert mc['g_hat'] not in seen_outputs and Ghat_c not in seen_outputs
    seen_outputs.update((mc['g_hat'], Ghat_c))
    acc, acc_u = mc['g_hat'], um_c
    next_claim += 1
assert decide(Curve, acc, acc_u)
frag['chain'] = '\n'.join([
    '| Inputs | $x_M$ | $\\alpha$ | New $\\hat{G}$ | New $\\v{u}$ |', '| --- | --- | --- | --- | --- |',
    *rows, '',
    f'The decider computes one MSM for the last row, gets ${show(acc)}$, and accepts. That single check covers all four input claims.',
])

# The placeholder claim for the first step: every challenge 1, point = sum of the generators.
u_ph = [1] * len(u1)
assert g_coeffs(u_ph) == [1, 1, 1, 1]
ph_pt = msm(Curve, [1, 1, 1, 1], G)
nondegenerate(ph_pt)
m_ph = merge(Curve, [(ph_pt, u_ph), (Ghat1, u1)], x_m, alpha, tau, u_m)
assert m_ph['accepted'] and decide(Curve, m_ph['g_hat'], u_m) and decide(Curve, ph_pt, u_ph)
assert ph_pt == m['C']
frag['placeholder'] = (
    f'On the toy curve the placeholder claim is $({show(ph_pt)},\\ {vec(u_ph)})$. Its factors are $(1 + X^2)(1 + X)$, and the point is $G_0 + G_1 + G_2 + G_3 = {show(ph_pt)}$, which by chance equals the $C_M$ of Section 6. '
    f'Merging it with claim 1, reusing the challenges of Section 6, gives $v_M = {m_ph["v"]}$ and $C_M = {show(m_ph["C"])}$, the final check passes, and the decider accepts the output claim $({show(m_ph["g_hat"])},\\ {vec(u_m)})$. '
    f'The placeholder behaves like any other true claim.'
)

# Three claims at once, as a node with two children and its own new claim would have.
three = [(Ghat1, u1), (Ghat2, u2), (Ghat_c, u_c)]
m3 = merge(Curve, three, x_m, alpha, tau, u_m)
assert m3['accepted'] and decide(Curve, m3['g_hat'], u_m)
frag['three'] = (
    f'Merge claims 1, 2 and 4 in one step. In a real run the transcript would absorb all three claims, so the challenges would differ from those of Section 6, but we reuse them here so that the two runs can be compared. '
    f'The merge gives $v_M = {m3["v"]}$ and $C_M = {show(m3["C"])}$, the final check passes, and the output point is ${show(m3["g_hat"])}$, the same as in the two-claim merge. '
    f'The output point is the folded generator, which depends only on $\\v{{u}}_M$. The inputs enter through $C_M$, $v_M$, the cross terms and the final scalar, and all four of these change when a claim is added.'
)
assert m3['C'] != m['C'] and m3['v'] != m['v'] and m3['a_hat'] != m['a_hat'] and m3['rounds'] != m['rounds']
assert m3['g_hat'] == Ghat_m

# ------------------------------------------------------------------ costs of a step
frag['costs'] = '\n'.join([
    f'| Work for one merge of two claims, $n = 2^{{{k_real}}}$ | Who | Amount |', '| --- | --- | --- |',
    f'| Evaluate $g_1$ and $g_2$ at $x_M$ | Verifier | ${k_real - 1}$ squarings and ${2 * k_real}$ factor multiplications |',
    f'| Compute $C_M$ | Verifier | $1$ scalar multiplication |',
    f'| Combine the $L_j$ and $R_j$ | Verifier | ${2 * k_real}$ scalar multiplications |',
    f'| Evaluate $g_M$ at $x_M$ | Verifier | ${k_real}$ factor multiplications, reusing the squarings |',
    f'| Final check | Verifier | $2$ scalar multiplications |',
    f'| Multiply out $g_1$ and $g_2$ | Prover | about ${2 * n_real:,}$ field multiplications |',
    f'| Compute all the $L_j$, $R_j$ and fold $\\v{{G}}$ | Prover | ${prover_cost:,}$ scalar multiplications |',
])
per_step_ver = 1 + 2 * k_real + 2
assert per_step_ver == 29
# The final verifier: the last proof carries acc_n, and its own IPA yields one more claim.
(acc_prev, acc_prev_u), (last_pt, last_u), last_lhs = chain_accs[-1]
ipa_split_cost = 2 * k_real + 2
assert ipa_split_cost == 28
final_merged = ipa_split_cost + 2 * n_real
final_one = ipa_split_cost + per_step_ver + n_real
assert last_lhs is not None
frag['final'] = (
    f'Suppose the chain stops after claim 4, and treat claim 4 as the last proof\'s own claim. The last proof carries the accumulator $({show(acc_prev)},\\ {vec(acc_prev_u)})$ in its statement, which covers claims 1 to 3. '
    f'The final verifier runs the last proof\'s inner product argument up to the split. Its final check passes with the supplied point, and this yields claim 4, $({show(last_pt)},\\ {vec(last_u)})$. '
    f'It then checks the prover\'s merge proof for these two claims, which is the third row of the table, and gets the claim $({show(acc)},\\ {vec(acc_u)})$. Finally it decides that one claim. '
    f'For $n = 2^{{{k_real}}}$ this costs ${ipa_split_cost}$ scalar multiplications for the split, ${per_step_ver}$ for the merge and ${n_real:,}$ for the decider, or ${final_one:,}$ in all. '
    f'Deciding the accumulator and the last claim separately needs no merge proof, but it still needs the ${ipa_split_cost}$ for the split and then two MSMs, or ${final_merged:,}$ scalar multiplications.'
)

frag['total'] = (
    f'Over the same hypothetical ${N_claims:,}$ claims, the group work that a verifier must do drops from ${N_claims * n_real:,}$ scalar multiplications to ${per_step_ver}$ per merge plus one decider MSM of ${n_real:,}$. '
    f'The accumulator stays at one point and ${acc_scalars}$ challenges, or ${acc_bytes}$ bytes at 32 bytes each, and each merge proof holds ${ipa_points}$ points and one scalar, or ${merge_proof_bytes}$ bytes.'
)

# ------------------------------------------------------------------ cheating, formal group
Ghat1_f = msm(Formal, coeffs1, Formal.G)
Ghat2_f = msm(Formal, coeffs2, Formal.G)
assert decide(Formal, Ghat1_f, u1) and decide(Formal, Ghat2_f, u2)
tau_fix, u_fix = tau, u_m

# One false claim: the prover holds h, the polynomial its point really commits to.
false1_f = msm(Formal, h1, Formal.G)
passes = []
for x in range(Q):
    for al in range(1, Q):
        r = merge(Formal, [(false1_f, u1), (Ghat2_f, u2)], x, al, tau_fix, u_fix, polys=[h1, coeffs2])
        if r['accepted']:
            passes.append((x, al))
assert sorted({x for x, _ in passes}) == roots
assert len(passes) == 3 * 42
frag['count-one'] = (
    f'Take the false point from Section 4, which commits to $h$, and merge it with the true claim 2. For each of the {Q * (Q - 1):,} pairs of $x_M$ and nonzero $\\alpha$, run the merge with the prover folding its real vector and supplying its honest folded generator. '
    f'The check passes for {len(passes)} pairs, and these are exactly the pairs with $x_M \\in \\{{2, 7, 20\\}}$, the roots of $h - g_1$. The weight $\\alpha$ plays no part, because only one input is wrong.'
)

# Cross-check the same count on the toy curve.
false1 = msm(Curve, h1, G)
assert all(
    merge(Curve, [(false1, u1), (Ghat2, u2)], x, al, tau_fix, u_fix, polys=[h1, coeffs2])['accepted'] == (x in roots)
    for x in range(Q) for al in (1, 2, 6, 30)
)

# Both false: the errors could cancel, and this is what alpha prevents.
d2 = [1, 40, 0, 2]
h2 = [(s + t) % Q for s, t in zip(coeffs2, d2)]
false2_f = msm(Formal, h2, Formal.G)
passes2 = []
for x in range(Q):
    for al in range(1, Q):
        r = merge(Formal, [(false1_f, u1), (false2_f, u2)], x, al, tau_fix, u_fix, polys=[h1, h2])
        if r['accepted']:
            passes2.append((x, al))
        assert r['accepted'] == ((poly_eval(diff, x) + al * poly_eval(d2, x)) % Q == 0)
total_pairs = Q * (Q - 1)
assert len(passes2) <= 4 * Q
# Opposite errors cancel at every point when alpha is fixed at 1.
d_opp = [(-c) % Q for c in diff]
h_opp = [(s + t) % Q for s, t in zip(coeffs2, d_opp)]
opp_f = msm(Formal, h_opp, Formal.G)
opp_pass = [(x, al) for x in range(Q) for al in range(1, Q)
            if merge(Formal, [(false1_f, u1), (opp_f, u2)], x, al, tau_fix, u_fix, polys=[h1, h_opp])['accepted']]
assert all((x, 1) in opp_pass for x in range(Q))
assert len(opp_pass) == Q + 3 * (Q - 2)
frag['count-two'] = (
    f'Now make claim 2 false as well, with $h_2 - g_2$ having the coefficients ${vec(d2)}$. A pair $(x_M, \\alpha)$ passes when $(h_1 - g_1)(x_M) + \\alpha (h_2 - g_2)(x_M) = 0$. '
    f'Running all {total_pairs:,} pairs gives {len(passes2)} that pass, against the bound of $4 \\cdot 43 = {4 * Q}$ from the [multivariate root count](./statements-and-challenges.md#_5-polynomials-in-several-variables), since the expression has total degree at most 4.'
    f' To see what $\\alpha$ prevents, let the second error be the exact negative of the first. With $\\alpha$ fixed at 1 the errors cancel, and all {Q} values of $x_M$ pass. With $\\alpha$ random, the {len(opp_pass)} passing pairs are those {Q} pairs with $\\alpha = 1$ and the pairs at the three roots.'
)

# A false claim forces a false output. Allow the prover to pick the output point.
tau_f = tau_fix
false_out = 0
true_out = 0
for x in range(Q):
    r = merge(Formal, [(false1_f, u1), (Ghat2_f, u2)], x, alpha, tau_f, u_fix, polys=[h1, coeffs2])
    if r['accepted']:
        true_out += 1
    else:
        false_out += 1
assert true_out == 3 and false_out == 40

# The forged claim of Section 2 goes into a merge.
forged_f = Formal.add(Ghat1_f, Formal.mul(delta_forge, Formal.U))
assert not decide(Formal, forged_f, u1)
acc_count = 0
for x in range(Q):
    for al in range(1, Q):
        for t in (1, 2, 6, 11, 30):
            r = merge(Formal, [(forged_f, u1), (Ghat2_f, u2)], x, al, t, u_fix, polys=[coeffs1, coeffs2])
            acc_count += r['accepted']
assert acc_count == 0

# The real-curve version of the same forgery, carried forward into a second forgery.
mf = merge(Curve, [(Gstar, u1), (Ghat2, u2)], x_m, alpha, tau, u_m)
assert not mf['accepted']
delta_out = delta_forge * inv(mf['a_hat']) % Q
Gm_star = add(mf['g_hat'], mul(delta_out, U))
assert mf['lhs'] == right_side(Curve, mf['a_hat'], Gm_star, mf['b_hat'], tau)
assert not decide(Curve, Gm_star, u_m)
assert mf['g_hat'] == Ghat_m
nondegenerate(Gm_star)
assert Gm_star not in (Ghat1, Ghat2, Ghat_m, Gstar)
assert Gm_star != mf['C'] and len({mf['C'], mf['lhs'], mf['rhs'], Gm_star, Ghat_m}) == 5
frag['forge-carry'] = (
    f'The forged claim from Section 2 is $({show(Gstar)},\\ {vec(u1)})$, and its point hides ${delta_forge} \\cdot U$. Merge it with the true claim 2, using the challenges of Section 6. '
    f'The commitment becomes ${show(mf["C"])}$, and the honest fold reaches $\\hat{{G}}_M = {show(mf["g_hat"])}$, but the check fails, since the left side is ${show(mf["lhs"])}$ and the right side is ${show(mf["rhs"])}$. '
    f'The script repeats this in the formal group for all {total_pairs:,} pairs and five values of $\\tau$, with no acceptances. '
    f'To continue, the prover has to repeat its trick and supply $\\hat{{G}}_M^* = \\hat{{G}}_M + {delta_out} \\cdot U = {show(Gm_star)}$. That passes the final check, so the false claim has moved to the output. The decider then computes ${show(Ghat_m)}$, sees that it differs from ${show(Gm_star)}$, and rejects.'
)

# The point fixed after the spot point: prover knowing x_M first.
r_const = 5
h_late = [c for c in coeffs1]
h_late[0] = (h_late[0] - r_const * x_m) % Q
h_late[1] = (h_late[1] + r_const) % Q
assert poly_eval(h_late, x_m) == g_eval(u1, x_m)
late_pt = msm(Curve, h_late, G)
assert not decide(Curve, late_pt, u1)
nondegenerate(late_pt)
late = merge(Curve, [(late_pt, u1), (Ghat2, u2)], x_m, alpha, tau, u_m, polys=[h_late, coeffs2])
assert late['accepted']
late_f = msm(Formal, h_late, Formal.G)
late_x = [x for x in range(Q)
          if merge(Formal, [(late_f, u1), (Ghat2_f, u2)], x, alpha, tau, u_m, polys=[h_late, coeffs2])['accepted']]
assert late_x == [x_m]
frag['late'] = (
    f'Suppose the prover learns $x_M = {x_m}$ before it fixes its point. It picks $h = g_1 + {r_const}(X - {x_m})$, whose coefficients are ${vec(h_late)}$, and sends the commitment ${show(late_pt)}$, which is not $\\hat{{G}}_1$. '
    f'Since $h({x_m}) = g_1({x_m})$, the merge passes, and every later step is honest. If instead the point is fixed first and $x_M$ varies over all 43 values, the merge passes only at $x_M = {late_x[0]}$.'
)

# Hidden U: a literally false claim that a fixed U cannot see.
eps = 6
hidden_pt_f = Formal.add(Formal.add(Ghat1_f, Formal.mul(eps, Formal.G[0])), Formal.mul(eps, Formal.U))
hidden_poly = [(coeffs1[0] + eps) % Q] + coeffs1[1:]
assert not decide(Formal, hidden_pt_f, u1)
fixed_ok = all(merge(Formal, [(hidden_pt_f, u1), (Ghat2_f, u2)], x, al, 1, u_fix, polys=[hidden_poly, coeffs2])['accepted']
               for x in range(Q) for al in range(1, Q))
tau_ok = [t for t in range(1, Q)
          if merge(Formal, [(hidden_pt_f, u1), (Ghat2_f, u2)], x_m, alpha, t, u_fix, polys=[hidden_poly, coeffs2])['accepted']]
assert fixed_ok and tau_ok == [1]
# The hidden term does not move the gap at the original point, so it cannot lift a false value.
gap_true = (0 - poly_eval(coeffs1, x1)) % Q
gap_hidden = (eps - poly_eval(hidden_poly, x1)) % Q
assert gap_true == gap_hidden == (-bhat1) % Q
hidden_pt = add(add(Ghat1, mul(eps, G[0])), mul(eps, U))
assert hidden_pt != late_pt
nondegenerate(hidden_pt)
frag['hidden'] = (
    f'Take the point $\\hat{{G}}_1 + {eps} \\cdot G_0 + {eps} \\cdot U = {show(hidden_pt)}$, so that the prover holds $g_1 + {eps}$ and the hidden ${eps} \\cdot U$ pays for the extra value. With $\\tau$ fixed at 1, the merge passes for all {total_pairs:,} pairs $(x_M, \\alpha)$, although the claim is false. '
    f'At our $x_M$ and $\\alpha$, running all 42 nonzero values of $\\tau$ gives acceptance at $\\tau = {tau_ok[0]}$ only.'
)

print(json.dumps(frag))
