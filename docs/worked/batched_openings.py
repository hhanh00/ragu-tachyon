"""Worked example for batched-openings.md. Prints fragments as JSON."""
import json
import math
from collections import Counter

from toy_curve import G, H, Q, add, log, msm, mul, show

n = 4
frag = {}


def poly(c, var='X'):
    terms = []
    for i, a in enumerate(c):
        a %= Q
        if a == 0 and i:
            continue
        coeff = '' if a == 1 and i else str(a)
        terms.append(coeff if i == 0 else f'{coeff}{var}' if i == 1 else f'{coeff}{var}^{i}')
    return ' + '.join(terms)


def vec(c):
    return '(' + ', '.join(str(a % Q) for a in c) + ')'


def ev(c, at):
    return sum(a * pow(at, i, Q) for i, a in enumerate(c)) % Q


def padded(c):
    return [a % Q for a in c] + [0] * (n - len(c))


def commit(c):
    return msm(padded(c), G)


def lin(*pairs):
    """Linear combination of coefficient lists, given as (weight, coefficients)."""
    out = [0] * max(len(c) for _, c in pairs)
    for w, c in pairs:
        for i, a in enumerate(c):
            out[i] = (out[i] + w * a) % Q
    return out


def divide(c, x):
    """Synthetic division by X - x. Returns the quotient and the remainder p(x)."""
    running = 0
    out = []
    for a in reversed(c):
        running = (a + x * running) % Q
        out.append(running)
    rem = out.pop()
    return out[::-1], rem


def pmul(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, u in enumerate(a):
        for j, w in enumerate(b):
            out[i + j] = (out[i + j] + u * w) % Q
    return out


def inv(a):
    return pow(a, -1, Q)


def neg(point):
    return mul(Q - 1, point)


# The three polynomials and three claims of the running example.
polys = [[7, 2, 5, 3], [3, 1, 8, 4], [2, 9, 4, 6]]
points = [9, 5, 2]
ys = [ev(c, x) for c, x in zip(polys, points)]
Cs = [commit(c) for c in polys]
assert all(ys) and all(c is not None and c not in G for c in Cs)
assert ys[:2] == [37, 20]
alpha, u, beta = 11, 17, 23
m = len(polys)
assert u not in points and len(set(points)) == m

# Section 1: the cost of separate openings.
k = 13
claims_book, polys_book = 6, 4
ipa_points = 2 * k
separate = claims_book * ipa_points
batched_points = ipa_points + 1
frag['cost'] = (f'Take $n = 2^{{{k}}}$ with 32-byte values, and the six claims above. '
                f'Six separate arguments carry ${claims_book} \\times {ipa_points} = {separate}$ group elements, or ${separate * 32:,}$ bytes. '
                f'One batched argument carries ${ipa_points}$ group elements, plus the extra commitment and the ${polys_book}$ scalars that this chapter introduces, '
                f'for ${batched_points * 32 + polys_book * 32:,}$ bytes. Both counts leave out the small constant number of extra values that each argument carries.')

# Section 2: different points do not combine.
r = 6
same_lhs = ev(lin((1, polys[0]), (r, polys[1])), 9)
p1_at_9 = ev(polys[1], 9)
assert same_lhs == (37 + r * p1_at_9) % Q
combined_claim = (ys[0] + r * ys[1]) % Q
assert combined_claim != same_lhs
frag['mismatch'] = (f'Suppose the prover claims $p_0({points[0]}) = {ys[0]}$ and $p_1({points[1]}) = {ys[1]}$, with the polynomials $p_0 = {poly(polys[0])}$ and $p_1 = {poly(polys[1])}$. '
                    f'Take $r = {r}$. The combination $p_0 + {r} p_1$ has the value ${same_lhs}$ at ${points[0]}$ and the value ${ev(lin((1, polys[0]), (r, polys[1])), points[1])}$ at ${points[1]}$, '
                    f'while the combined claim is ${ys[0]} + {r} \\cdot {ys[1]} = {combined_claim}$. The claimed number matches neither value, even though both claims are true, '
                    f'because the value at ${points[0]}$ needs $p_1({points[0]}) = {p1_at_9}$ and nobody has said anything about that.')

# Section 3: the division.
q0, rem0 = divide(polys[0], points[0])
assert rem0 == ys[0] and q0 == [32, 32, 3]
a, x = polys[0], points[0]
frag['division'] = '\n'.join([
    f'Take $p(X) = {poly(a)}$ and $x = {x}$, so $a_3, a_2, a_1, a_0 = {a[3]}, {a[2]}, {a[1]}, {a[0]}$.\n',
    '| Line | Formula | Value modulo 43 |', '| --- | --- | --- |',
    f'| $b_2$ | $a_3$ | ${q0[2]}$ |',
    f'| $b_1$ | $a_2 + x b_2 = {a[2]} + {x} \\cdot {q0[2]}$ | ${q0[1]}$ |',
    f'| $b_0$ | $a_1 + x b_1 = {a[1]} + {x} \\cdot {q0[1]}$ | ${q0[0]}$ |',
    f'| $y$ | $a_0 + x b_0 = {a[0]} + {x} \\cdot {q0[0]}$ | ${rem0}$ |',
    f'\nThe quotient is $q(X) = {poly(q0)}$, and the last line recovers $y = {rem0}$, the value of $p({x})$ from the [commitments chapter](./polynomial-commitments.md#_8-writing-an-evaluation-as-an-inner-product). '
    f'Multiplying out $(X - {x})({poly(q0)})$ returns ${poly(lin((1, a), (-rem0, [1])))}$, which equals $p(X) - {rem0}$ with coefficients reduced modulo 43.',
])
assert pmul([-x % Q, 1], q0) == lin((1, a), (-rem0, [1]))

wrong = (ys[0] + 1) % Q
frag['false-division'] = (f'Suppose the prover claims $p({x}) = {wrong}$ instead. The first three lines of the table do not involve $y$, so they produce the same $q(X)$. '
                          f'The last line still computes ${rem0}$, which contradicts the claim. Expanding shows the same mismatch, since $(X - {x}) q(X) = p(X) - {rem0}$ while the claim needs $p(X) - {wrong}$. '
                          f'No polynomial can repair this, because at $X = {x}$ the product $(X - {x}) q(X)$ is zero for every $q$, whereas $p({x}) - {wrong} = {(rem0 - wrong) % Q}$.')

# Section 4: the claim at a new point.
one_q, one_rem = divide(polys[1], points[1])
assert one_rem == ys[1]
tu1 = ev(polys[1], u)
qu1 = ev(one_q, u)
assert qu1 == (tu1 - ys[1]) * inv(u - points[1]) % Q
Q1 = commit(one_q)
assert Q1 is not None and Q1 not in G
frag['one-claim'] = '\n'.join([
    f'Take a second polynomial $p_1(X) = {poly(polys[1])}$, with the commitment $C_1 = {show(Cs[1])}$ and the claim $p_1({points[1]}) = {ys[1]}$. Division gives $q_1(X) = {poly(one_q)}$.\n',
    '| Step | Party | Value or check |', '| --- | --- | --- |',
    f'| 1 | Prover commits to the quotient | $Q_1 = {show(Q1)}$ |',
    f'| 2 | Verifier sends a challenge | $u = {u}$ |',
    f'| 3 | Prover sends the value of $p_1$ at $u$ | $p_1({u}) = {tu1}$ |',
    f'| 4 | Verifier derives the value of $q_1$ at $u$ | $({tu1} - {ys[1]}) / ({u} - {points[1]}) = {qu1}$ |',
    f'\nThe commitment $C_1$ must now open to ${tu1}$ at ${u}$, and $Q_1$ must open to ${qu1}$ at ${u}$. Evaluating the quotient directly confirms that $q_1({u}) = {qu1}$.',
])

# Section 5: alpha batching.
qs = []
for c, x_i, y_i in zip(polys, points, ys):
    q_i, rem = divide(c, x_i)
    assert rem == y_i and pmul([-x_i % Q, 1], q_i) == lin((1, c), (-y_i, [1]))
    qs.append(q_i)
rows = ['| Claim $i$ | Polynomial $p_i(X)$ | Point $x_i$ | Value $y_i$ | Commitment $C_i$ | Quotient $q_i(X)$ |', '| --- | --- | --- | --- | --- | --- |']
for i in range(m):
    rows.append(f'| {i} | ${poly(polys[i])}$ | {points[i]} | {ys[i]} | ${show(Cs[i])}$ | ${poly(qs[i])}$ |')
frag['claims'] = '\n'.join(rows)

# Plain sum with cancelling errors at one point.
pa, pb = polys[0], polys[1]
xs = 9
ta, tb = ev(pa, xs), ev(pb, xs)
ca, cb = (ta + 1) % Q, (tb - 1) % Q
qa, ra = divide(pa, xs)
qb, rb = divide(pb, xs)
summed = lin((1, qa), (1, qb))
assert pmul([-xs % Q, 1], summed) == lin((1, pa), (1, pb), (-(ca + cb), [1]))
assert ta != ca and tb != cb and ca and cb
frag['plain-sum'] = (f'The true values at ${xs}$ are $p_0({xs}) = {ta}$ and $p_1({xs}) = {tb}$. A cheater claims ${ca}$ and ${cb}$, so both claims are false. '
                     f'The errors are opposite, so $p_0 + p_1 - ({ca} + {cb})$ still has a root at ${xs}$ and division by $X - {xs}$ leaves no remainder. '
                     f'The result is the genuine polynomial ${poly(summed)}$, which the cheater can commit to and open at any point.')


def poles(a_):
    return (a_ * (ra - ca) + (rb - cb)) % Q


hiders = [a_ for a_ in range(Q) if poles(a_) == 0]
assert hiders == [1]
frag['alpha-count'] = (f'With the weights $\\alpha$ and $1$, the two errors from the previous example leave the remainder $\\alpha \\cdot {(ra - ca) % Q} + {(rb - cb) % Q}$ over $X - {xs}$. '
                       f'Trying all 43 values of $\\alpha$ finds that only $\\alpha = {hiders[0]}$ removes it, and that value is the plain sum.')

f = lin((alpha ** 2, qs[0]), (alpha, qs[1]), (1, qs[2]))
F = commit(f)
assert F is not None and F not in G
assert F == add(add(mul(alpha ** 2, commit(qs[0])), mul(alpha, commit(qs[1]))), commit(qs[2]))
frag['alpha-f'] = '\n'.join([
    f'Take $\\alpha = {alpha}$, so $\\alpha^2 = {alpha ** 2 % Q}$ modulo 43. Each column of the next table combines one power of $X$.\n',
    '| Term | $X^0$ | $X^1$ | $X^2$ |', '| --- | --- | --- | --- |',
    f'| $q_0(X)$ | {qs[0][0]} | {qs[0][1]} | {qs[0][2]} |',
    f'| $q_1(X)$ | {qs[1][0]} | {qs[1][1]} | {qs[1][2]} |',
    f'| $q_2(X)$ | {qs[2][0]} | {qs[2][1]} | {qs[2][2]} |',
    f'| $f(X) = {alpha ** 2 % Q}\\,q_0 + {alpha}\\,q_1 + q_2$ | {f[0]} | {f[1]} | {f[2]} |',
    f'\nThe prover commits to $f$ and sends the single point $F = {show(F)}$.',
])

# Section 6: values at u.
ts = [ev(c, u) for c in polys]
weights = [alpha ** 2 % Q, alpha, 1]
assert all(ts)
terms = [(t - y) * inv(u - x_i) % Q for t, y, x_i in zip(ts, ys, points)]
fu = sum(w * t for w, t in zip(weights, terms)) % Q
assert fu == ev(f, u) and fu != 0
rows = ['| $i$ | $p_i(u)$ | $u - x_i$ | $(p_i(u) - y_i) / (u - x_i)$ | Weight | Weighted term |', '| --- | --- | --- | --- | --- | --- |']
for i in range(m):
    rows.append(f'| {i} | {ts[i]} | {(u - points[i]) % Q} | {terms[i]} | {weights[i]} | {weights[i] * terms[i] % Q} |')
frag['derive-fu'] = (f'Take $u = {u}$. The prover sends $p_0({u}) = {ts[0]}$, $p_1({u}) = {ts[1]}$ and $p_2({u}) = {ts[2]}$, and the verifier computes each term from those values and the original claims.\n\n'
                     + '\n'.join(rows)
                     + f'\n\nThe last column sums to $f({u}) = {fu}$ modulo 43. The prover, who holds $f$, gets the same number by direct substitution into ${poly(f)}$. The verifier has obtained this value without seeing $f$.')

# Section 7: beta batching.
p = lin((beta ** 3, f), (beta ** 2, polys[0]), (beta, polys[1]), (1, polys[2]))
bw = [pow(beta, 3, Q), pow(beta, 2, Q), beta, 1]
P_pt = add(add(add(mul(bw[0], F), mul(bw[1], Cs[0])), mul(bw[2], Cs[1])), Cs[2])
v = (bw[0] * fu + bw[1] * ts[0] + bw[2] * ts[1] + ts[2]) % Q
assert P_pt == commit(p) and v == ev(p, u) and P_pt is not None and P_pt not in G and v != 0
frag['beta-p'] = '\n'.join([
    f'Take $\\beta = {beta}$, whose powers modulo 43 are $\\beta^2 = {bw[1]}$ and $\\beta^3 = {bw[0]}$.\n',
    '| Input | Weight | Commitment | Value at $u$ | Coefficients |', '| --- | --- | --- | --- | --- |',
    f'| $f$ | ${bw[0]}$ | ${show(F)}$ | {fu} | ${vec(padded(f))}$ |',
    f'| $p_0$ | ${bw[1]}$ | ${show(Cs[0])}$ | {ts[0]} | ${vec(polys[0])}$ |',
    f'| $p_1$ | ${bw[2]}$ | ${show(Cs[1])}$ | {ts[1]} | ${vec(polys[1])}$ |',
    f'| $p_2$ | ${bw[3]}$ | ${show(Cs[2])}$ | {ts[2]} | ${vec(polys[2])}$ |',
    f'| Combined $p$ | | $P = {show(P_pt)}$ | $v = {v}$ | ${vec(p)}$ |',
    f'\nThe verifier derives $P$ and $v$ from the first four rows, using only group operations and field arithmetic. The prover derives the coefficients of $p$. '
    f'Committing to those coefficients gives ${show(commit(p))}$, and substituting $u = {u}$ into $p$ gives ${ev(p, u)}$, so both agree with what the verifier computed.',
])

# Section 8: the whole run.
frag['run'] = '\n'.join([
    '| Step | Party | Value or check |', '| --- | --- | --- |',
    f'| 0 | Both hold the claims | $({show(Cs[0])},\\,{points[0]},\\,{ys[0]})$, $({show(Cs[1])},\\,{points[1]},\\,{ys[1]})$, $({show(Cs[2])},\\,{points[2]},\\,{ys[2]})$ |',
    f'| 1 | Verifier sends a challenge | $\\alpha = {alpha}$ |',
    f'| 2 | Prover commits to $f$ | $F = {show(F)}$ |',
    f'| 3 | Verifier sends a challenge | $u = {u}$ |',
    f'| 4 | Prover sends the values at $u$ | ${ts[0]},\\ {ts[1]},\\ {ts[2]}$ |',
    f'| 5 | Verifier sends a challenge | $\\beta = {beta}$ |',
    f'| 6 | Verifier derives $f(u)$ | ${fu}$ |',
    f'| 7 | Verifier derives the output claim | $P = {show(P_pt)}$, $v = {v}$ |',
    f'| 8 | Prover reveals $p$ | ${vec(p)}$ |',
    f'| 9 | Verifier checks the commitment | $\\dot{{\\v{{p}}}}{{\\v{{G}}}} = {show(msm(p, G))}$, which equals $P$ |',
    f'| 10 | Verifier checks the value | $p({u}) = {ev(p, u)}$, which equals $v$ |',
])
assert msm(p, G) == P_pt


# Section 9: cheating. Claim 1 is false, and the other two are true.
bad_y = (ys[1] + 1) % Q
cheat_ys = [ys[0], bad_y, ys[2]]
rem_bad = (ev(polys[1], points[1]) - bad_y) % Q
us = [t for t in range(Q) if t not in points]
assert len(us) == 40


def derived(sent, at, claim_ys=cheat_ys, pts=points, w=weights):
    return sum(wi * (s - y) * inv(at - x_i) for wi, s, y, x_i in zip(w, sent, claim_ys, pts)) % Q


def passes(fp, sent, at, b, claim_ys=cheat_ys):
    """The final check: the real polynomial behind P, opened at u, against the derived v."""
    wb = [pow(b, 3, Q), pow(b, 2, Q), b, 1]
    v_ = (wb[0] * derived(sent, at, claim_ys) + wb[1] * sent[0] + wb[2] * sent[1] + sent[2]) % Q
    real = (wb[0] * ev(fp, at) + wb[1] * ev(polys[0], at) + wb[2] * ev(polys[1], at) + ev(polys[2], at)) % Q
    return v_ == real


# Strategy A: commit to the quotients and report honest values.
fA = f
true_at = {t: [ev(c, t) for c in polys] for t in us}
gaps = [(ev(fA, t) - derived(true_at[t], t)) % Q for t in us]
assert all(gaps)
winsA = [(t, b) for t in us for b in range(Q) if passes(fA, true_at[t], t, b)]
assert len(winsA) == 40 and all(b == 0 for _, b in winsA)
gap17 = (ev(fA, u) - derived(true_at[u], u)) % Q
frag['cheat-drop'] = (f'The cheater claims $p_1({points[1]}) = {bad_y}$, whereas the true value is ${ys[1]}$. It computes the quotients by the division table, which ignores $y$, and commits to the same $f$, then reports true values at $u$. '
                      f'The false $y_1$ enters the verifier\'s formula, and at $u = {u}$ the derived value is ${derived(true_at[u], u)}$ while $f({u}) = {ev(fA, u)}$, a gap of ${gap17}$. '
                      f'We tried every pair of challenges, with 40 allowed values of $u$ and 43 of $\\beta$. The gap is nonzero at all 40 values of $u$, and the only passing runs are the {len(winsA)} that have $\\beta = 0$.')

# Strategy B: lie about one value at u so that f(u) looks right.
tB = list(true_at[u])
deltaB = gap17 * inv(alpha) * (u - points[1]) % Q
tB[1] = (tB[1] + deltaB) % Q
assert derived(tB, u) == ev(fA, u) and deltaB == (bad_y - ys[1]) % Q
winsB = [b for b in range(Q) if passes(fA, tB, u, b)]
assert winsB == [0]
expected = (beta ** 2 * ts[0] + beta * tB[1] + ts[2]) % Q
frag['cheat-lie'] = (f'At $u = {u}$ the cheater sends ${tB[1]}$ for $p_1({u})$ in place of the true ${ts[1]}$, a shift of ${deltaB}$ chosen so that the derived value equals $f({u}) = {ev(fA, u)}$. In effect it reports values of $p_1 + {deltaB}$, a polynomial that does satisfy the false claim, while its commitment still holds $p_1$. '
                     f'The output claim now carries that shift. With $\\beta = {beta}$, the value $v$ and the true $p({u})$ differ by $\\beta \\cdot {deltaB} = {beta * deltaB % Q}$, so the check fails. Of the 43 values of $\\beta$, only $\\beta = 0$ passes.')

# Best response at one u: every possible set of lies.
Dcoef = [weights[i] * inv(u - points[i]) % Q for i in range(3)]
base_gap = gap17
pow3 = [pow(b, 3, Q) for b in range(Q)]
pow2 = [pow(b, 2, Q) for b in range(Q)]
best = 0
for d0 in range(Q):
    for d1 in range(Q):
        for d2 in range(Q):
            e_f = (base_gap - Dcoef[0] * d0 - Dcoef[1] * d1 - Dcoef[2] * d2) % Q
            roots = 0
            for b in range(Q):
                if (pow3[b] * e_f - pow2[b] * d0 - b * d1 - d2) % Q == 0:
                    roots += 1
            assert e_f or d0 or d1 or d2, 'the error polynomial cannot vanish identically'
            best = max(best, roots)
assert best == 3
frag['cheat-best'] = (f'Fix $f$ and $u = {u}$ as above. The cheater can send any of $43^3 = {43 ** 3}$ triples of values. Trying all of them against all 43 values of $\\beta$ shows that no triple passes for more than ${best}$ values of $\\beta$, '
                      'which agrees with the fact that the error is a nonzero polynomial of degree at most 3 in $\\beta$.')

# Strategy C: commit to a polynomial that fits the formula at chosen points.
Dtrue = {t: derived(true_at[t], t) for t in us}
reach = Counter()
for c3 in range(Q):
    for c2 in range(Q):
        for c1 in range(Q):
            residues = Counter((Dtrue[t] - c1 * t - c2 * t * t - c3 * t * t * t) % Q for t in us)
            for count in residues.values():
                reach[count] += 1
best_agree = max(reach)
assert best_agree == 4 and reach[4] == math.comb(40, 4)
targets = [3, 11, u, 30]
assert all(t in us for t in targets)


def interpolate(xs_, ys_):
    out = [0]
    for i, (xi, yi) in enumerate(zip(xs_, ys_)):
        basis = [1]
        denom = 1
        for j, xj in enumerate(xs_):
            if j != i:
                basis = pmul(basis, [-xj % Q, 1])
                denom = denom * (xi - xj) % Q
        out = lin((1, out), (yi * inv(denom), basis))
    return out


fC = interpolate(targets, [Dtrue[t] for t in targets])
assert commit(fC) is not None and commit(fC) not in G
agree = [t for t in us if ev(fC, t) == Dtrue[t]]
assert agree == sorted(targets)
assert all(passes(fC, true_at[u], u, b) for b in range(Q))
frag['cheat-fit'] = (f'The cheater can make the committed polynomial match the verifier\'s formula at a few values of $u$ by interpolation. Through the four points $u \\in \\{{{", ".join(map(str, targets))}\\}}$ it gets $f\'(X) = {poly(fC)}$, '
                     f'with commitment ${show(commit(fC))}$. If the challenge lands on one of these four values, the cheater reports true values and passes for every $\\beta$. '
                     f'If it lands anywhere else among the 40 allowed values, this polynomial does not match. We tried all $43^4 = {43 ** 4:,}$ polynomials of degree at most 3. '
                     f'None matches the formula at more than ${best_agree}$ points, and exactly ${reach[4]:,}$ reach ${best_agree}$, one for each choice of four points.')
worst_num = best_agree * Q + (len(us) - best_agree) * best
frag['cheat-total'] = (f'Combining the counts bounds the best cheater on the toy curve. It wins on at most ${best_agree}$ of the 40 values of $u$ outright and on at most ${best}$ of the 43 values of $\\beta$ at each of the other ${len(us) - best_agree}$, '
                       f'which is at most ${worst_num}$ of the ${len(us) * Q}$ pairs of challenges.')

# Learning a challenge early.
frag['early-u'] = (f'Suppose the cheater learns $u = {u}$ before it commits. The interpolated polynomial $f\'$ from earlier in this section matches the formula at that point, so the cheater commits to it, reports true values, and passes for all 43 values of $\\beta$.')

b_ = beta
tE = list(true_at[u])
# Solve beta^3 (gap - coef*d) + ... so the error vanishes at the known beta, lying about p_1 only.
coef = Dcoef[1]
d_ = (pow(b_, 3, Q) * gap17) * inv((pow(b_, 3, Q) * coef + b_) % Q) % Q
tE[1] = (tE[1] + d_) % Q
assert passes(fA, tE, u, b_) and not passes(fA, tE, u, (b_ + 1) % Q) and d_
frag['early-beta'] = (f'Suppose the cheater learns $\\beta = {beta}$ before sending the values at $u = {u}$. It sends ${tE[1]}$ for $p_1({u})$, with the shift ${d_}$ solved from the one linear equation that makes the total error vanish at this $\\beta$. The check passes. Moving to $\\beta = {beta + 1}$ makes the same message fail.')

# Early alpha: two false claims at one point cancelling under the known alpha.
e0 = (ta - (ta + 1)) % Q
e1 = (-alpha * e0) % Q
y0c, y1c = (ta + 1) % Q, (tb - e1) % Q
assert (alpha * (ta - y0c) + (tb - y1c)) % Q == 0 and y0c != ta and y1c != tb
fc = lin((alpha, qa), (1, qb))
assert pmul([-xs % Q, 1], fc) == lin((alpha, pa), (1, pb), (-(alpha * y0c + y1c), [1]))
ok = 0
for t in range(Q):
    if t == xs:
        continue
    for b in range(Q):
        vv = (b * b * (alpha * (ev(pa, t) - y0c) + (ev(pb, t) - y1c)) * inv(t - xs) + b * ev(pa, t) + ev(pb, t)) % Q
        rr = (b * b * ev(fc, t) + b * ev(pa, t) + ev(pb, t)) % Q
        ok += vv == rr
assert ok == 42 * 43
frag['early-alpha'] = (f'Suppose the cheater learns $\\alpha = {alpha}$ before it makes its two claims at the point ${xs}$. It claims $p_0({xs}) = {y0c}$ and $p_1({xs}) = {y1c}$, whose errors ${e0}$ and ${e1}$ satisfy ${alpha} \\cdot {e0} + {e1} = 0$ modulo 43. '
                       f'Both claims are false, yet $\\alpha(p_0 - {y0c}) + (p_1 - {y1c})$ is divisible by $X - {xs}$, which gives the genuine polynomial $f = {poly(fc)}$. '
                       f'This cheater passes for all 42 values of $u$ and all 43 values of $\\beta$, a total of ${ok}$ of ${ok}$ runs.')

# Forging the final opening with known discrete logs.
logs = [log(g, G[0]) for g in G]
target_v = (v + 1) % Q
g0, g1 = logs[0], logs[1]
det = (g0 * u - g1) % Q
d0 = (-g1 * (target_v - v)) * inv(det) % Q
d1 = (g0 * (target_v - v)) * inv(det) % Q
forged_p = [(p[0] + d0) % Q, (p[1] + d1) % Q, p[2], p[3]]
assert msm(forged_p, G) == P_pt and ev(forged_p, u) == target_v and forged_p != p
frag['forged-open'] = (f'Using the known discrete logs of the toy generators, a prover can adjust entries 0 and 1 of $\\v{{p}}$ to get $\\v{{p}}\' = {vec(forged_p)}$. This vector commits to the same $P = {show(P_pt)}$ and evaluates to ${target_v}$ at $u = {u}$, not ${v}$. '
                       'A prover with this ability could satisfy the final check for a wrong $v$, which is why the discrete log relation assumption is necessary.')

# Real sizes.
real_n, real_m, real_d, real_l = 2 ** 13, 6, 4, 4
endo_bits = 143
total = (real_m - 1) + (real_n - 1 + real_d) + real_l
assert total < 2 ** 14
frag['real-bound'] = (f'For $n = 2^{{13}}$, with the six claims, four points and four polynomials from Section 1, the three bounds add up to $({real_m - 1} + {real_n - 1 + real_d} + {real_l}) / |\\F| = {total} / |\\F|$. '
                      f'For a field of about $2^{{254}}$ elements, as with the Pasta curves, this is below $2^{{-240}}$. The fuse step draws $\\beta$ from a {endo_bits}-bit endoscalar, as Section 13 notes, and with that range the $\\beta$ term alone is about ${real_l} / 2^{{{endo_bits}}} = 2^{{{2 - endo_bits}}}$ and dominates the sum.')

# Section 10: shared polynomials.
share_polys = [0, 1, 2, 0]
share_pts = [9, 5, 2, 2]
share_ys = [ev(polys[j], x_) for j, x_ in zip(share_polys, share_pts)]
assert share_ys[:3] == ys and share_ys[3] == 12
sq = [divide(polys[j], x_)[0] for j, x_ in zip(share_polys, share_pts)]
sw = [pow(alpha, 3 - i, Q) for i in range(4)]
sf = lin(*[(w, q_) for w, q_ in zip(sw, sq)])
sF = commit(sf)
sfu = sum(w * (ts[j] - y) * inv(u - x_) for w, j, y, x_ in zip(sw, share_polys, share_ys, share_pts)) % Q
assert sfu == ev(sf, u)
sp = lin((bw[0], sf), (bw[1], polys[0]), (bw[2], polys[1]), (1, polys[2]))
sP = add(add(add(mul(bw[0], sF), mul(bw[1], Cs[0])), mul(bw[2], Cs[1])), Cs[2])
sv = (bw[0] * sfu + bw[1] * ts[0] + bw[2] * ts[1] + ts[2]) % Q
assert sP == commit(sp) and sv == ev(sp, u) and sF is not None and sP is not None and sv
frag['shared'] = (f'Add a fourth claim, $p_0({share_pts[3]}) = {share_ys[3]}$. This claim reuses $p_0$ and also shares the point ${share_pts[3]}$ with claim 2. The quotient polynomial gains one term, $f(X) = \\alpha^3 q_0 + \\alpha^2 q_1 + \\alpha q_2 + q_3$ with $q_3 = {poly(sq[3])}$, '
                  f'and becomes $f(X) = {poly(sf)}$ with commitment $F = {show(sF)}$ at $\\alpha = {alpha}$. The prover still sends only the three values ${ts[0]}, {ts[1]}, {ts[2]}$, because both claims about $p_0$ use the same number ${ts[0]}$ when the verifier derives $f({u}) = {sfu}$. '
                  f'The output at $\\beta = {beta}$ is $P = {show(sP)}$ and $v = {sv}$, and opening $p = {poly(sp)}$ confirms both.')

# Section 11: blinding.
gammas = [17, 29, 11]
gamma_f = 5
blinded = [add(c, mul(g_, H)) for c, g_ in zip(Cs, gammas)]
Fbar = add(F, mul(gamma_f, H))
Pbar = add(add(add(mul(bw[0], Fbar), mul(bw[1], blinded[0])), mul(bw[2], blinded[1])), blinded[2])
gamma = (bw[0] * gamma_f + bw[1] * gammas[0] + bw[2] * gammas[1] + gammas[2]) % Q
assert Pbar == add(commit(p), mul(gamma, H)) and gamma
frag['blinding'] = (f'Take blinding factors $\\gamma_0, \\gamma_1, \\gamma_2 = {gammas[0]}, {gammas[1]}, {gammas[2]}$ and $\\gamma_f = {gamma_f}$. The blinded commitments are $\\bar{{C}}_0 = {show(blinded[0])}$, $\\bar{{C}}_1 = {show(blinded[1])}$, $\\bar{{C}}_2 = {show(blinded[2])}$ and $\\bar{{F}} = {show(Fbar)}$. '
                    f'The verifier combines them into $\\bar{{P}} = {show(Pbar)}$. The prover computes $\\gamma = {bw[0]} \\cdot {gamma_f} + {bw[1]} \\cdot {gammas[0]} + {bw[2]} \\cdot {gammas[1]} + {gammas[2]} = {gamma}$ modulo 43, and $\\dot{{\\v{{p}}}}{{\\v{{G}}}} + {gamma} \\cdot H = {show(add(commit(p), mul(gamma, H)))}$, the same point.')

# The book's formula read with the sum starting at i = 0.
bookw = [1, alpha, alpha ** 2 % Q]  # f = sum alpha^i q_i
fbook = lin((1, qs[0]), (alpha, qs[1]), (alpha ** 2, qs[2]))


def book_pass(sent, t, b):
    d = sum(wi * (s - y) * inv(t - xi) for wi, s, y, xi in zip(bookw, sent, cheat_ys, points)) % Q
    v_ = (d + sent[0] + b * sent[1] + b * b * sent[2]) % Q
    real = (ev(fbook, t) + ev(polys[0], t) + b * ev(polys[1], t) + b * b * ev(polys[2], t)) % Q
    return v_ == real


wins = 0
solved_at = None
blocked = []
for t in us:
    d_true = sum(wi * (s - y) * inv(t - xi) for wi, s, y, xi in zip(bookw, true_at[t], cheat_ys, points)) % Q
    gap = (ev(fbook, t) - d_true) % Q
    denom = (1 + inv(t - points[0])) % Q
    if denom == 0:
        blocked.append(t)
        continue
    delta = gap * inv(denom) % Q
    sent = list(true_at[t])
    sent[0] = (sent[0] + delta) % Q
    assert delta
    for b in range(Q):
        assert book_pass(sent, t, b)
        wins += 1
    if t == u:
        solved_at = (sent[0], delta, gap)
assert blocked == [(points[0] - 1) % Q] and wins == 39 * Q and solved_at
# The collision needs only the beta sum to start at 0: starting the alpha sum at 1 leaves the count unchanged.
shifted_alpha = [alpha * w % Q for w in bookw]
fshift = lin(*[(w, q_) for w, q_ in zip(shifted_alpha, qs)])
alpha_one_wins = 0
for t in us:
    d_true = sum(wi * (s - y) * inv(t - xi) for wi, s, y, xi in zip(shifted_alpha, true_at[t], cheat_ys, points)) % Q
    denom = (1 + shifted_alpha[0] * inv(t - points[0])) % Q
    if denom:
        sent0 = (true_at[t][0] + (ev(fshift, t) - d_true) * inv(denom)) % Q
        d_sent = (d_true + shifted_alpha[0] * (sent0 - true_at[t][0]) * inv(t - points[0])) % Q
        alpha_one_wins += Q * ((d_sent + sent0) % Q == (ev(fshift, t) + true_at[t][0]) % Q)
assert alpha_one_wins == wins
frag['collision'] = (f'Keep the false claim $p_1({points[1]}) = {bad_y}$, and use the sum from $i = 0$ in both places, so that $f$ and $p_0$ both have weight 1 in $p$. The cheater commits to the honest $f = \\sum_i \\alpha^i q_i$, which at $\\alpha = {alpha}$ is ${poly(fbook)}$. '
                     f'At $u = {u}$ the derived value misses $f({u})$ by ${solved_at[2]}$. The cheater then sends ${solved_at[0]}$ for $p_0({u})$, a shift of ${solved_at[1]}$. The shift changes the derived value of $f(u)$ and the $p_0$ term of $v$, and the two changes add up to exactly that miss. '
                     f'No power of $\\beta$ appears in this equation, so we checked that the forged message passes for all 43 values of $\\beta$. The attack works at 39 of the 40 allowed values of $u$, for a total of ${wins}$ of the ${40 * Q}$ pairs $(u, \\beta)$. This forgery fails only at $u = {blocked[0]}$, where $1 + 1/(u - x_0) = 0$ modulo 43.')

# Section 12: the SHPLONK form.
ZT = 1
for x_i in points:
    ZT = ZT * (u - x_i) % Q
L = [0]
Lpoint = None
for i in range(m):
    Zrest = 1
    for j in range(m):
        if j != i:
            Zrest = Zrest * (u - points[j]) % Q
    L = lin((1, L), (weights[i] * Zrest, lin((1, polys[i]), (-ys[i], [1]))))
    term = mul(weights[i] * Zrest % Q, add(Cs[i], neg(mul(ys[i], G[0]))))
    Lpoint = add(Lpoint, term)
L = lin((1, L), (-ZT, f))
Lpoint = add(Lpoint, neg(mul(ZT, F)))
assert ev(L, u) == 0 and Lpoint == commit(L) and Lpoint is not None
frag['shplonk'] = (f'In our run $Z_T(u) = {ZT}$, and the construction gives $L(X) = {poly(L)}$. Substituting $u = {u}$ gives ${ev(L, u)}$, and the combination of $C_i$, $y_i$ and $F$ gives the commitment ${show(Lpoint)}$, which matches $L$ directly. The prover sent no values at $u$ for this check.')

print(json.dumps(frag))
