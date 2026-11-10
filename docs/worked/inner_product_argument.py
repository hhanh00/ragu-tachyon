"""Worked example for inner-product-argument.md. Prints fragments as JSON."""
import itertools
import json
from toy_curve import G, H, Q, U, add, curve_points, log, msm, mul, show

frag = {}


def inv(a):
    return pow(a, -1, Q)


def neg(a):
    return mul(Q - 1, a)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b)) % Q


def vec(a):
    return '(' + ', '.join(map(str, a)) + ')'


def pts(a):
    return '(' + ',\\ '.join(show(p) for p in a) + ')'


def nondegenerate(*points):
    """No identity points and no point equal to a public generator."""
    for p in points:
        assert p is not None and p not in G and p not in (H, U), p


def fold_a(a, u):
    h = len(a) // 2
    return [(u * a[i] + inv(u) * a[i + h]) % Q for i in range(h)]


def fold_b(b, u):
    h = len(b) // 2
    return [(inv(u) * b[i] + u * b[i + h]) % Q for i in range(h)]


def fold_g(g, u):
    h = len(g) // 2
    return [add(mul(inv(u), g[i]), mul(u, g[i + h])) for i in range(h)]


def cross(a, b, g, gen=U):
    """Returns L, R and their parts for a split at the midpoint."""
    h = len(a) // 2
    l_g, r_g = msm(a[h:], g[:h]), msm(a[:h], g[h:])
    l_v, r_v = dot(a[h:], b[:h]), dot(a[:h], b[h:])
    return add(l_g, mul(l_v, gen)), add(r_g, mul(r_v, gen)), l_v, r_v


# ---------------------------------------------------------------- the claim
a = [7, 2, 5, 3]
x = 9
n, k = 4, 2
b = [x ** i % Q for i in range(n)]
y = dot(a, b)
C = msm(a, G)
P_stmt = add(C, mul(y, U))
assert y == 37 and P_stmt == add(msm(a, G), mul(dot(a, b), U))
nondegenerate(C, P_stmt)

frag['setup'] = '\n'.join([
    '| Quantity | Value |', '| --- | --- |',
    f'| Coefficient vector | $\\v{{a}} = {vec(a)}$ |',
    f'| Evaluation point | $x = {x}$ |',
    f'| Power vector | $\\v{{b}} = {vec(b)}$ |',
    f'| Claimed value | $y = \\dot{{\\v{{a}}}}{{\\v{{b}}}} = {y}$ |',
    f'| Commitment | $C = \\dot{{\\v{{a}}}}{{\\v{{G}}}} = {show(C)}$ |',
    f'| Statement point | $P = C + {y} \\cdot U = {show(P_stmt)}$ |',
])

# ---------------------------------------------------------------- the four pieces
# The running vector has <a_hi, G_hi> = O by coincidence, which would hide the effect
# of a weight on that piece, so these two fragments use chapter 06's second vector.
assert msm(a[2:], G[2:]) is None
d = [3, 1, 8, 4]
C_d = msm(d, G)
d_lo, d_hi = d[:2], d[2:]
G_lo, G_hi = G[:2], G[2:]
LL, HH = msm(d_lo, G_lo), msm(d_hi, G_hi)
HL, LH = msm(d_hi, G_lo), msm(d_lo, G_hi)
assert add(LL, HH) == C_d
nondegenerate(LL, HH, HL, LH, C_d)
naive_a = [(s + t) % Q for s, t in zip(d_lo, d_hi)]
naive_G = [add(s, t) for s, t in zip(G_lo, G_hi)]
naive = msm(naive_a, naive_G)
assert naive == add(add(LL, HH), add(HL, LH)) and naive != C_d

frag['naive'] = '\n'.join([
    f'Take $\\v{{d}} = {vec(d)}$, whose commitment is $C_d = {show(C_d)}$. It splits into $\\v{{d}}_{{lo}} = {vec(d_lo)}$ and $\\v{{d}}_{{hi}} = {vec(d_hi)}$, and the four inner products between the halves are:', '',
    '| Piece | Point |', '| --- | --- |',
    f'| $\\dot{{\\v{{d}}_{{lo}}}}{{\\v{{G}}_{{lo}}}}$ | ${show(LL)}$ |',
    f'| $\\dot{{\\v{{d}}_{{hi}}}}{{\\v{{G}}_{{hi}}}}$ | ${show(HH)}$ |',
    f'| $\\dot{{\\v{{d}}_{{hi}}}}{{\\v{{G}}_{{lo}}}}$ | ${show(HL)}$ |',
    f'| $\\dot{{\\v{{d}}_{{lo}}}}{{\\v{{G}}_{{hi}}}}$ | ${show(LH)}$ |', '',
    f'The first two pieces add up to $C_d$. The plain sums are $\\v{{d}}_{{lo}} + \\v{{d}}_{{hi}} = {vec(naive_a)}$ and '
    f'$\\v{{G}}_{{lo}} + \\v{{G}}_{{hi}} = {pts(naive_G)}$, and their inner product is ${show(naive)}$. That point is the sum of all four pieces, so it differs from $C_d$.',
])

# Equal weights on both high halves break the wanted terms; opposite weights keep them.
t = 3
same_d = [(s + t * r) % Q for s, r in zip(d_lo, d_hi)]
same_G = [add(s, mul(t, r)) for s, r in zip(G_lo, G_hi)]
opp_d = [(s + inv(t) * r) % Q for s, r in zip(d_lo, d_hi)]
same = msm(same_d, same_G)
opp = msm(opp_d, same_G)
sq = t * t % Q
cross_same = add(mul(t, HL), mul(t, LH))
same_wanted = add(same, neg(cross_same))
opp_wanted = add(opp, neg(add(mul(inv(t), HL), mul(t, LH))))
assert same_wanted == add(LL, mul(sq, HH)) and same_wanted != C_d and opp_wanted == C_d
frag['weights'] = (
    f'Take the weight ${t}$, whose inverse modulo 43 is ${inv(t)}$. Scaling both high halves by ${t}$ gives ${show(same)}$. '
    f'Removing the cross pieces, each of which carries weight ${t}$, leaves ${show(same_wanted)}$, which is $\\dot{{\\v{{d}}_{{lo}}}}{{\\v{{G}}_{{lo}}}} + {sq}\\dot{{\\v{{d}}_{{hi}}}}{{\\v{{G}}_{{hi}}}}$ and not $C_d$. '
    f'Scaling $\\v{{d}}_{{hi}}$ by ${inv(t)}$ and $\\v{{G}}_{{hi}}$ by ${t}$ gives ${show(opp)}$. Removing the cross pieces, which now carry weights ${inv(t)}$ and ${t}$, leaves ${show(opp_wanted)} = C_d$.')

# ---------------------------------------------------------------- the full run
def run_round(a_, b_, G_, P_, u):
    L, R, lv, rv = cross(a_, b_, G_)
    a2, b2, G2 = fold_a(a_, u), fold_b(b_, u), fold_g(G_, u)
    ui, ui2, u_sq = inv(u), inv(u) ** 2 % Q, u * u % Q
    P2 = add(add(P_, mul(ui2, L)), mul(u_sq, R))
    # The prover computes the same point from the folded vectors.
    assert P2 == add(msm(a2, G2), mul(dot(a2, b2), U))
    # The folded inner product has the four expected parts.
    assert dot(a2, b2) == (dot(a_, b_) + ui2 * lv + u_sq * rv) % Q
    nondegenerate(L, R, P2)
    return dict(L=L, R=R, lv=lv, rv=rv, a=a2, b=b2, G=G2, P=P2, u=u, ui=ui, ui2=ui2, u_sq=u_sq, ip=dot(a2, b2))


def clean_challenges(s_, t_):
    """Rejects runs with identity points, repeated points, or a point equal to a generator."""
    if pow(s_, 2, Q) in (1, Q - 1) or pow(t_, 2, Q) in (1, Q - 1) or pow(s_, 2, Q) == pow(t_, 2, Q):
        return False
    try:
        one = run_round(a, b, G, P_stmt, s_)
        two = run_round(one['a'], one['b'], one['G'], one['P'], t_)
        nondegenerate(*one['G'], *two['G'])
    except AssertionError:
        return False
    seen = [P_stmt, C, one['L'], one['R'], one['P'], two['L'], two['R'], two['P'], one['G'][0], one['G'][1], two['G'][0]]
    if len(set(seen)) != len(seen):
        return False
    return all(val not in (0, 1) for val in one['a'] + one['b'] + two['a'] + two['b'])


u1, u2 = next((p, q) for p in range(2, Q) for q in range(2, Q) if clean_challenges(p, q))
r1 = run_round(a, b, G, P_stmt, u1)
r2 = run_round(r1['a'], r1['b'], r1['G'], r1['P'], u2)
a_hat, b_hat, G_hat = r2['a'][0], r2['b'][0], r2['G'][0]
final_rhs = mul(a_hat, add(G_hat, mul(b_hat, U)))
assert r2['P'] == final_rhs
nondegenerate(G_hat, final_rhs)
assert a_hat != 0 and b_hat != 0


def round_tables(r, j, a_prev, b_prev, G_prev, P_prev):
    h = len(a_prev) // 2
    al, ah = vec(a_prev[:h]), vec(a_prev[h:])
    bl, bh = vec(b_prev[:h]), vec(b_prev[h:])
    prover = '\n'.join([
        '| Prover computes | Value |', '| --- | --- |',
        f'| $\\dot{{\\v{{a}}_{{hi}}}}{{\\v{{b}}_{{lo}}}}$ with $\\v{{a}}_{{hi}} = {ah}$, $\\v{{b}}_{{lo}} = {bl}$ | ${r["lv"]}$ |',
        f'| $\\dot{{\\v{{a}}_{{lo}}}}{{\\v{{b}}_{{hi}}}}$ with $\\v{{a}}_{{lo}} = {al}$, $\\v{{b}}_{{hi}} = {bh}$ | ${r["rv"]}$ |',
        f'| $L_{j} = \\dot{{\\v{{a}}_{{hi}}}}{{\\v{{G}}_{{lo}}}} + {r["lv"]} \\cdot U$ | ${show(r["L"])}$ |',
        f'| $R_{j} = \\dot{{\\v{{a}}_{{lo}}}}{{\\v{{G}}_{{hi}}}} + {r["rv"]} \\cdot U$ | ${show(r["R"])}$ |',
    ])
    after = '\n'.join([
        '| Party | Computation | Result |', '| --- | --- | --- |',
        f'| Prover | $\\v{{a}}^{{({j})}} = {r["u"]}\\v{{a}}_{{lo}} + {r["ui"]}\\v{{a}}_{{hi}}$ | ${vec(r["a"])}$ |',
        f'| Both | $\\v{{b}}^{{({j})}} = {r["ui"]}\\v{{b}}_{{lo}} + {r["u"]}\\v{{b}}_{{hi}}$ | ${vec(r["b"])}$ |',
        f'| Both | $\\v{{G}}^{{({j})}} = {r["ui"]}\\v{{G}}_{{lo}} + {r["u"]}\\v{{G}}_{{hi}}$ | ${pts(r["G"])}$ |',
        f'| Verifier | $P^{{({j})}} = P^{{({j - 1})}} + {r["ui2"]} \\cdot L_{j} + {r["u_sq"]} \\cdot R_{j}$ | ${show(r["P"])}$ |',
        f'| Prover | $\\dot{{\\v{{a}}^{{({j})}}}}{{\\v{{G}}^{{({j})}}}} + {r["ip"]} \\cdot U$ | ${show(r["P"])}$ |',
    ])
    return prover, after


frag['round1-prover'], frag['round1-after'] = round_tables(r1, 1, a, b, G, P_stmt)
frag['round2-prover'], frag['round2-after'] = round_tables(r2, 2, r1['a'], r1['b'], r1['G'], r1['P'])
frag['round1-challenge'] = (f'The verifier sends $u_1 = {u1}$. Its inverse is $u_1^{{-1}} = {r1["ui"]}$, and the weights on the cross terms are '
                            f'$u_1^{{-2}} = {r1["ui2"]}$ and $u_1^{{2}} = {r1["u_sq"]}$.')
frag['round1-ip'] = (f'The inner product changes the way the algebra predicts: ${y} + {r1["ui2"]} \\cdot {r1["lv"]} + {r1["u_sq"]} \\cdot {r1["rv"]} = {r1["ip"]}$ modulo 43, '
                     f'and direct computation of $\\dot{{\\v{{a}}^{{(1)}}}}{{\\v{{b}}^{{(1)}}}}$ gives ${r1["ip"]}$ as well.')
frag['round2-challenge'] = (f'The verifier sends $u_2 = {u2}$, with $u_2^{{-1}} = {r2["ui"]}$, $u_2^{{-2}} = {r2["ui2"]}$ and $u_2^{{2}} = {r2["u_sq"]}$.')
frag['final'] = '\n'.join([
    f'The prover sends $\\hat{{a}} = {a_hat}$. The verifier already holds $\\hat{{b}} = {b_hat}$ and $\\hat{{G}} = {show(G_hat)}$ from folding, and it checks one equation:', '',
    f'$$P^{{(2)}} = {show(r2["P"])}, \\qquad \\hat{{a}} \\cdot (\\hat{{G}} + \\hat{{b}} \\cdot U) = {a_hat} \\cdot ({show(G_hat)} + {b_hat} \\cdot U) = {show(final_rhs)}.$$', '',
    'The two points match, so the verifier accepts.',
])
frag['proof-contents'] = (f'The whole proof is $L_1 = {show(r1["L"])}$, $R_1 = {show(r1["R"])}$, $L_2 = {show(r2["L"])}$, $R_2 = {show(r2["R"])}$ and $\\hat{{a}} = {a_hat}$. '
                          'For $n = 4$ that is four points and one scalar, against the four scalars of revealing $\\v{a}$. '
                          'The saving only appears at larger $n$, because the proof grows with $\\log_2 n$.')

# ---------------------------------------------------------------- fixed weights
# If the halves were combined with the fixed weight 1, P' = P + L + R and a prover could
# move a false U term into R before any challenge exists. For the running vector L + R
# happens to equal U, so the fragment does not print the resulting point.
y_bad = (y + 1) % Q
P_bad = add(C, mul(y_bad, U))
L_fix, R_fix, _, _ = cross(a, b, G)
R_shift = add(R_fix, neg(U))
P_fix_honest = add(add(P_stmt, L_fix), R_fix)
P_fix_cheat = add(add(P_bad, L_fix), R_shift)
assert P_fix_cheat == P_fix_honest and R_shift != R_fix
# The rest of the run with weight 1 is honest and passes.
fa, fb, fg = fold_a(a, 1), fold_b(b, 1), fold_g(G, 1)
assert P_fix_honest == add(msm(fa, fg), mul(dot(fa, fb), U))
nondegenerate(P_bad, R_shift)
frag['fixed-weight'] = (f'Suppose the halves were added with weight 1, as in the plain sums above, so that the verifier updates the statement point to $P + L + R$ with $L$ and $R$ as just defined. '
                        f'For the running example, a prover who claims $y = {y_bad}$ instead of ${y}$ starts from $C + {y_bad} \\cdot U = {show(P_bad)}$, which carries one extra $U$. '
                        f'It sends the honest $L = {show(L_fix)}$ and, in place of the honest $R = {show(R_fix)}$, the point $R - U = {show(R_shift)}$. '
                        f'The extra $U$ in the statement and the missing $U$ in $R$ cancel, so the verifier ends up with the same point it would hold for the true claim $y = {y}$, and the prover can continue honestly from there.')

# ---------------------------------------------------------------- cheating
y_false = (y + 1) % Q
e = (y_false - y) % Q
P_false = add(C, mul(y_false, U))


def honest_rounds(a_, b_, G_, P_, challenges, gen=U):
    """Folds honestly from a statement point; returns the final-check outcome and values."""
    cur_a, cur_b, cur_G, cur_P = list(a_), list(b_), list(G_), P_
    for u in challenges:
        L, R, _, _ = cross(cur_a, cur_b, cur_G, gen)
        cur_P = add(add(cur_P, mul(inv(u) ** 2 % Q, L)), mul(u * u % Q, R))
        cur_a, cur_b, cur_G = fold_a(cur_a, u), fold_b(cur_b, u), fold_g(cur_G, u)
    return cur_a[0], cur_b[0], cur_G[0], cur_P


# Honest folding from the false statement fails for every pair of challenges.
fails = 0
for s, v in itertools.product(range(1, Q), repeat=2):
    ah, bh, gh, ph = honest_rounds(a, b, G, P_false, [s, v])
    assert ph != mul(ah, add(gh, mul(bh, U)))
    fails += 1
assert fails == 42 * 42
frag['gap-values'] = (f'The honest statement point $C + {y} \\cdot U$ has coefficients $\\v{{a}} = {vec(a)}$ on $\\v{{G}}$ and ${y}$ on $U$, so its gap is ${y} - \\dot{{\\v{{a}}}}{{\\v{{b}}}} = {y} - {y} = 0$. '
                      f'The false statement point $C + {y_false} \\cdot U$ has the same coefficients on $\\v{{G}}$ and ${y_false}$ on $U$, so its gap is ${y_false} - {y} = {e}$.')
frag['honest-false'] = (f'Claim $y = {y_false}$ instead of ${y}$, so the statement point is $C + {y_false} \\cdot U = {show(P_false)}$, and fold honestly from $\\v{{a}}$. '
                        f'Running the argument for all ${42 * 42}$ pairs of nonzero challenges gives {fails} rejections and no acceptances, because the extra ${e} \\cdot U$ stays in the folded point in every round.')

# With discrete logs in hand, the final scalar can be solved for.
ah, bh, gh, ph = honest_rounds(a, b, G, P_false, [u1, u2])
base = add(gh, mul(bh, U))
forged_c = log(ph, G[0]) * inv(log(base, G[0])) % Q
assert mul(forged_c, base) == ph and forged_c != ah
frag['forge-logs'] = (f'Keep the false statement $y = {y_false}$ and the honest $L_j, R_j$. With challenges $({u1}, {u2})$ the folded point is ${show(ph)}$, and the right side of the check is a multiple of $\\hat{{G}} + \\hat{{b}} \\cdot U = {show(base)}$. '
                      f'Every point on the toy curve is a known multiple of $G_0$, and counting finds ${show(ph)} = {log(ph, G[0])} \\cdot G_0$ and ${show(base)} = {log(base, G[0])} \\cdot G_0$. '
                      f'The prover divides these logs to get $\\hat{{a}} = {log(ph, G[0])} / {log(base, G[0])} = {forged_c}$. Then ${forged_c} \\cdot {show(base)} = {show(ph)}$ and the verifier accepts the false value. '
                      'This is the attack the discrete log relation assumption rules out on a real curve.')

# Knowing the challenge before sending R lets the prover cancel the error.
L0, R0, _, _ = cross(a, b, G)
R_cheat = add(R0, mul((Q - e) * inv(u1) ** 2 % Q, U))
P_after = add(add(P_false, mul(inv(u1) ** 2 % Q, L0)), mul(u1 * u1 % Q, R_cheat))
assert P_after == r1['P'] and R_cheat != R0


def cheat_passes(u):
    """The prover fixed R_cheat for the guess u1, then the verifier picks u."""
    cur = add(add(P_false, mul(inv(u) ** 2 % Q, L0)), mul(u * u % Q, R_cheat))
    aa, bb, gg = fold_a(a, u), fold_b(b, u), fold_g(G, u)
    L, R, _, _ = cross(aa, bb, gg)
    cur = add(add(cur, mul(inv(u2) ** 2 % Q, L)), mul(u2 * u2 % Q, R))
    return cur == mul(fold_a(aa, u2)[0], add(fold_g(gg, u2)[0], mul(fold_b(bb, u2)[0], U)))


wins = [u for u in range(1, Q) if cheat_passes(u)]
assert wins == sorted([u1, Q - u1]) and len(wins) == 2
frag['early-u'] = (f'Suppose the prover knows $u_1 = {u1}$ before it sends $R_1$, and it wants to pass with the false statement $y = {y_false}$, whose point carries an extra ${e} \\cdot U$. '
                   f'It replaces the honest $R_1 = {show(R0)}$ by $R_1 - u_1^{{-2}} \\cdot {e} \\cdot U = {show(R_cheat)}$. The weight $u_1^{{2}}$ then turns the change into $-{e} \\cdot U$, and $P^{{(1)}}$ comes out as ${show(P_after)}$, '
                   'exactly the honest folded point. The rest of the run is honest, and the verifier accepts.')
frag['early-count'] = (f'Now fix that altered $R_1$ first and let the challenge vary. Running the protocol for all 42 nonzero values of $u_1$ gives acceptance only at $u_1 \\in \\{{{wins[0]}, {wins[1]}\\}}$, '
                       f'the guess and its negative, which share the same square. The prover wins with probability ${len(wins)}/42$.')

# Generator-by-generator analysis for a two-entry vector, treating G_0, G_1, U as independent.
a2 = [7, 2]
b2 = [1, x]
true2 = dot(a2, b2)
y2 = (true2 + 1) % Q
nonzero = list(range(1, Q))


def passing(l0, l1, lu, r0, r1, ru):
    """Challenges for which some final scalar satisfies all three coefficient equations."""
    out = []
    for u in nonzero:
        ui, w, wi = inv(u), u * u % Q, inv(u) ** 2 % Q
        scal = (u * (a2[0] + wi * l0 + w * r0)) % Q  # forced by the G_0 equation
        if (a2[1] + wi * l1 + w * r1 - scal * u) % Q:
            continue
        if (y2 + wi * lu + w * ru - scal * (ui * b2[0] + u * b2[1])) % Q:
            continue
        out.append(u)
    return out


l0h, l1h, r0h, r1h = a2[1], 0, 0, a2[0]
honest_family = {}
for lu in range(Q):
    for ru in range(Q):
        c = len(passing(l0h, l1h, lu, r0h, r1h, ru))
        honest_family[c] = honest_family.get(c, 0) + 1
assert max(honest_family) == 4 and sum(honest_family.values()) == Q * Q
# The honest L, R values reject every challenge for a false claim.
assert passing(l0h, l1h, a2[1] * b2[0] % Q, r0h, r1h, a2[0] * b2[1] % Q) == []

# The gap of a point x_0 G_0 + x_1 G_1 + t U is t - <x, b>. Whatever the G coefficients,
# a passing challenge must satisfy gap(P) + gap(L) / u^2 + gap(R) u^2 = 0.
def gap(coefs):
    return (coefs[2] - coefs[0] * b2[0] - coefs[1] * b2[1]) % Q


sampled, sampled_max = 0, 0
for cl0, cl1, cr0, cr1 in itertools.product(range(1, Q, 9), repeat=4):
    for lu, ru in itertools.product(range(2, Q, 14), repeat=2):
        wins_here = passing(cl0, cl1, lu, cr0, cr1, ru)
        sampled += 1
        sampled_max = max(sampled_max, len(wins_here))
        for u in wins_here:
            w = u * u % Q
            assert (gap((a2[0], a2[1], y2)) + inv(w) * gap((cl0, cl1, lu)) + w * gap((cr0, cr1, ru))) % Q == 0
assert sampled_max <= 4
gP = gap((a2[0], a2[1], y2))
assert gP == 1
# A U-coefficient choice that reaches the maximum, shown with its quadratic and roots.
best_lu, best_ru = next((lu, ru) for lu in range(1, Q) for ru in range(1, Q)
                        if len(passing(l0h, l1h, lu, r0h, r1h, ru)) == 4)
best_wins = passing(l0h, l1h, best_lu, r0h, r1h, best_ru)
gl_best = gap((l0h, l1h, best_lu))
gr_best = gap((r0h, r1h, best_ru))
roots_w = sorted(w for w in range(1, Q) if (gr_best * w * w + gP * w + gl_best) % Q == 0)
assert len(roots_w) == 2 and sorted({u * u % Q for u in best_wins}) == roots_w
honest_lu, honest_ru = a2[1] * b2[0] % Q, a2[0] * b2[1] % Q
frag['two-entry'] = '\n'.join([
    f'Take $\\v{{a}} = {vec(a2)}$ and $\\v{{b}} = {vec(b2)}$, whose true inner product is ${true2}$, and the false claim $y = {y2}$. The statement point is $P = {a2[0]} \\cdot G_0 + {a2[1]} \\cdot G_1 + {y2} \\cdot U$, with gap ${y2} - {true2} = {gP}$. '
    f'The honest cross terms have $\\v{{G}}$ parts $L = {a2[1]} \\cdot G_0 + \\ldots$ and $R = {a2[0]} \\cdot G_1 + \\ldots$, from $\\v{{a}}_{{hi}} = ({a2[1]})$ and $\\v{{a}}_{{lo}} = ({a2[0]})$. '
    f'With these $\\v{{G}}$ parts the first two equations both give $\\hat{{a}} = {a2[0]}u + {a2[1]}u^{{-1}}$, so they never conflict, and only the gap equation decides. '
    f'The honest $U$ parts are $l_U = {honest_lu}$ and $r_U = {honest_ru}$, which give $\\text{{gap}}(L) = \\text{{gap}}(R) = 0$, and the gap equation becomes ${gP} = 0$, so no challenge passes.', '',
    f'A cheater can choose other $U$ parts. With $l_U = {best_lu}$ and $r_U = {best_ru}$, the gaps are $\\text{{gap}}(L) = {best_lu} - {honest_lu} = {gl_best}$ and $\\text{{gap}}(R) = {best_ru} - {honest_ru} = {gr_best}$ modulo 43, and the quadratic is ${gr_best}w^2 + {'' if gP == 1 else gP}w + {gl_best} = 0$. '
    f'Its roots are $w = {roots_w[0]}$ and $w = {roots_w[1]}$. Both are squares modulo 43, and their square roots are $u \\in \\{{{", ".join(map(str, best_wins))}\\}}$. '
    f'Running the check for all 42 nonzero challenges confirms that exactly these {len(best_wins)} pass. '
    f'Trying all ${Q * Q:,}$ choices of the two $U$ parts in the same way, no choice passes more than ${max(honest_family)}$ of the 42 challenges.',
])

# Running gap in the early-challenge attack on the n = 4 run.
gap_L = 0
gap_R = (Q - e) * inv(u1) ** 2 % Q
assert (e + u1 * u1 * gap_R) % Q == 0
frag['early-gap'] = (f'In this attack $\\text{{gap}}(P) = {e}$, $\\text{{gap}}(L_1) = {gap_L}$ and $\\text{{gap}}(R_1) = {gap_R}$. The equation ${e} + {gap_R} \\cdot u_1^{{2}} = 0$ has the solutions $u_1^{{2}} = {u1 * u1 % Q}$, which are the two challenges just found.')

# The bound for a real field: 4 challenges per round, over about 2^254 nonzero values.
k_real = 13
assert 4 * k_real < 2 ** 6
frag['bound'] = (f'For $n = 2^{{{k_real}}}$ over a Pasta scalar field, which has about $2^{{254}}$ elements, this bound is ${4 * k_real}$ divided by about $2^{{254}}$, which is below $2^{{-248}}$.')

# ---------------------------------------------------------------- the s vector and g(X)
s_vec = []
rows = ['| $i$ | Bits of $i$ | $s_i$ | Value |', '| --- | --- | --- | --- |']
for i in range(n):
    b1, b0 = (i >> 1) & 1, i & 1
    val = ((u1 if b1 else inv(u1)) * (u2 if b0 else inv(u2))) % Q
    s_vec.append(val)
    expr = f'u_1^{{{"" if b1 else "-1"}}} u_2^{{{"" if b0 else "-1"}}}'.replace('^{}', '')
    rows.append(f'| {i} | {b1}{b0} | ${expr}$ | ${val}$ |')
assert msm(s_vec, G) == G_hat and dot(s_vec, b) == b_hat
frag['s-table'] = '\n'.join(rows) + (f'\n\nWith $(u_1, u_2) = ({u1}, {u2})$, the multi-scalar multiplication $\\dot{{\\v{{s}}}}{{\\v{{G}}}}$ gives ${show(msm(s_vec, G))}$, the same point as $\\hat{{G}}$ from the round-by-round folding. '
                                     f'The same weights applied to $\\v{{b}}$ give $\\dot{{\\v{{s}}}}{{\\v{{b}}}} = {dot(s_vec, b)} = \\hat{{b}}$.')


def poly_mul(p, q):
    out = [0] * (len(p) + len(q) - 1)
    for i, c in enumerate(p):
        for j, d in enumerate(q):
            out[i + j] = (out[i + j] + c * d) % Q
    return out


def g_coeffs(us):
    """Coefficients of the product of (u_j^-1 + u_j X^(2^(k-j))), for j = 1..k."""
    kk = len(us)
    out = [1]
    for j, u in enumerate(us, start=1):
        factor = [0] * (2 ** (kk - j) + 1)
        factor[0], factor[-1] = inv(u), u
        out = poly_mul(out, factor)
    return out


def g_eval(us, at):
    kk = len(us)
    out = 1
    for j, u in enumerate(us, start=1):
        out = out * (inv(u) + u * pow(at, 2 ** (kk - j), Q)) % Q
    return out


coeffs = g_coeffs([u1, u2])
assert coeffs == s_vec and g_eval([u1, u2], x) == b_hat
f1 = (inv(u1) + u1 * pow(x, 2, Q)) % Q
f2 = (inv(u2) + u2 * x) % Q
assert f1 * f2 % Q == b_hat
frag['g-poly'] = (f'With $(u_1, u_2) = ({u1}, {u2})$, the polynomial is $g(X) = ({inv(u1)} + {u1}X^2)({inv(u2)} + {u2}X)$. Multiplying it out gives coefficients ${vec(coeffs)}$, which is the $\\v{{s}}$ of the table. '
                  f'At $x = {x}$ the first factor is ${inv(u1)} + {u1} \\cdot {pow(x, 2, Q)} = {f1}$, the second is ${inv(u2)} + {u2} \\cdot {x} = {f2}$, and their product is ${f1 * f2 % Q} = \\hat{{b}}$.')

factor1 = (inv(u1) + u1 * pow(x, 2, Q)) % Q
assert r1['b'] == [factor1, factor1 * x % Q]
frag['b-scaled'] = (f'In the run of Section 5, $\\v{{b}}^{{(1)}} = {vec(r1["b"])}$. The predicted factor is $u_1^{{-1}} + u_1 x^2 = {inv(u1)} + {u1} \\cdot {pow(x, 2, Q)} = {factor1}$, and ${factor1} \\cdot (1, {x}) = {vec(r1["b"])}$ modulo 43.')

# Ordering check at k = 3 with eight generators.
big_G = [p for p in curve_points() if p not in G and p not in (H, U)][::4][:8]
assert len(set(big_G)) == 8
big_u = [3, 5, 7]
cur = list(big_G)
cur_b = [x ** i % Q for i in range(8)]
for u in big_u:
    cur, cur_b = fold_g(cur, u), fold_b(cur_b, u)
big_s = g_coeffs(big_u)
assert cur[0] == msm(big_s, big_G) and cur_b[0] == g_eval(big_u, x)
for i in range(8):
    val = 1
    for j, u in enumerate(big_u, start=1):
        bit = (i >> (3 - j)) & 1
        val = val * (u if bit else inv(u)) % Q
    assert val == big_s[i]
# The book's labels count down: its u_1 is this chapter's last challenge, with exponent 2^(j-1).
book_u = {j: big_u[3 - j] for j in (1, 2, 3)}
book_val = 1
for j in (1, 2, 3):
    book_val = book_val * (inv(book_u[j]) + book_u[j] * pow(x, 2 ** (j - 1), Q)) % Q
assert book_val == g_eval(big_u, x)
frag['order-check'] = (f'The script behind this chapter repeats the comparison for $k = 3$ with eight generators and challenges ${vec(big_u)}$: round-by-round folding gives $\\hat{{G}} = {show(cur[0])}$, and the coefficients of $g$ give the same point through one multi-scalar multiplication. '
                       f'The folded power vector and $g({x})$ also agree, at ${cur_b[0]}$.')

ks = 13
frag['costs'] = '\n'.join([
    '| Task for $n = 2^{13}$ | Operations |', '| --- | --- |',
    f'| Computing $\\hat{{b}} = g(x)$ with repeated squaring | ${ks - 1}$ squarings and ${ks}$ factor multiplications in $\\F_q$ |',
    f'| Computing $\\v{{s}}$ from the challenges | about ${2 ** ks:,}$ field multiplications |',
    f'| Computing $\\hat{{G}} = \\dot{{\\v{{s}}}}{{\\v{{G}}}}$ | ${2 ** ks:,}$ scalar multiplications, one per generator |',
    f'| Combining the $L_j$ and $R_j$ | ${2 * ks}$ scalar multiplications |',
])

# ---------------------------------------------------------------- the code's fold
def code_fold(vec_a, vec_b, vec_G, u):
    h = len(vec_a) // 2
    ui = inv(u)
    return ([(vec_a[i] + ui * vec_a[i + h]) % Q for i in range(h)],
            [(vec_b[i] + u * vec_b[i + h]) % Q for i in range(h)],
            [add(vec_G[i], mul(u, vec_G[i + h])) for i in range(h)])


# Same statement, code-style weights, with code challenge equal to the square of the book's.
c1, c2 = u1 * u1 % Q, u2 * u2 % Q
ca1, cb1, cG1 = code_fold(a, b, G, c1)
ca2, cb2, cG2 = code_fold(ca1, cb1, cG1, c2)
L1c, R1c, _, _ = cross(a, b, G)
L2c, R2c, _, _ = cross(ca1, cb1, cG1)
Pc1 = add(add(P_stmt, mul(inv(c1), L1c)), mul(c1, R1c))
Pc2 = add(add(Pc1, mul(inv(c2), L2c)), mul(c2, R2c))
assert Pc1 == r1['P'] and Pc2 == r2['P'] and L1c == r1['L'] and R1c == r1['R']
assert Pc2 == mul(ca2[0], add(cG2[0], mul(cb2[0], U)))
prod_u = u1 * u2 % Q
assert a_hat == prod_u * ca2[0] % Q and b_hat == inv(prod_u) * cb2[0] % Q and G_hat == mul(inv(prod_u), cG2[0])
frag['code-fold'] = '\n'.join([
    f'Run the same statement $P = {show(P_stmt)}$ with the code\'s weights and the squared challenges $(w_1, w_2) = ({c1}, {c2})$, which are the squares of $({u1}, {u2})$ modulo 43.', '',
    '| Value | Symmetric form | One-sided form |', '| --- | --- | --- |',
    f'| First-round cross terms | $L_1 = {show(r1["L"])}$, $R_1 = {show(r1["R"])}$ | $L_1 = {show(L1c)}$, $R_1 = {show(R1c)}$ |',
    f'| Point after round 1 | ${show(r1["P"])}$ | ${show(Pc1)}$ |',
    f'| Point after round 2 | ${show(r2["P"])}$ | ${show(Pc2)}$ |',
    f'| Vector after round 1 | ${vec(r1["a"])}$ | ${vec(ca1)}$ |',
    f'| Final scalar | $\\hat{{a}} = {a_hat}$ | ${ca2[0]}$ |',
    f'| Final $\\v{{b}}$ entry | $\\hat{{b}} = {b_hat}$ | ${cb2[0]}$ |',
    f'| Final generator | $\\hat{{G}} = {show(G_hat)}$ | ${show(cG2[0])}$ |', '',
    f'The product of the challenges is $u_1 u_2 = {prod_u}$, and multiplying the one-sided scalar by it gives ${ca2[0]} \\cdot {prod_u} = {a_hat} = \\hat{{a}}$. Dividing the one-sided $\\v{{b}}$ entry and generator by it gives $\\hat{{b}}$ and $\\hat{{G}}$ as well. Both forms pass their final checks.',
])


def code_g(us):
    kk = len(us)
    out = [1]
    for j, u in enumerate(us, start=1):
        factor = [0] * (2 ** (kk - j) + 1)
        factor[0], factor[-1] = 1, u
        out = poly_mul(out, factor)
    return out


def compute_b(at, us):
    """Same loop as verifier.rs compute_b."""
    tmp, cur_pow = 1, at
    for u in reversed(us):
        tmp = tmp * (1 + u * cur_pow) % Q
        cur_pow = cur_pow * cur_pow % Q
    return tmp


def compute_s(us, init):
    """Same loop as verifier.rs compute_s."""
    v = [0] * (2 ** len(us))
    v[0] = init
    length = 1
    for u in reversed(us):
        for i in range(length):
            v[length + i] = v[i] * u % Q
        length *= 2
    return v


assert compute_s([c1, c2], 1) == code_g([c1, c2])
assert [inv(prod_u) * t % Q for t in code_g([c1, c2])] == coeffs
frag['code-g'] = (f'For $(w_1, w_2) = ({c1}, {c2})$, the code\'s polynomial is $(1 + {c1}X^2)(1 + {c2}X)$, with coefficients ${vec(code_g([c1, c2]))}$. '
                  f'Dividing them by $u_1 u_2 = {prod_u}$ gives ${vec(coeffs)}$, the coefficients of the symmetric $g$. '
                  f'At $x = {x}$ the code\'s polynomial takes the value ${compute_b(x, [c1, c2])}$, which is the one-sided $\\v{{b}}$ entry from the table above.')
assert compute_b(x, [c1, c2]) == cb2[0]

# ---------------------------------------------------------------- the code's statement
raw_s = [11, 4, 19, 6]
s_at = sum(c * x ** i for i, c in enumerate(raw_s)) % Q
mask = [(raw_s[0] - s_at) % Q] + raw_s[1:]
assert sum(c * x ** i for i, c in enumerate(mask)) % Q == 0 and s_at != 0
S = msm(mask, G)
nondegenerate(S)


def code_prove(poly, spoly, xi_, z_, us, at=x):
    """Mirrors prover.rs create_proof, with the challenges supplied."""
    pp = [(s_ * xi_ + c) % Q for s_, c in zip(spoly, poly)]
    v_ = sum(c * at ** i for i, c in enumerate(pp)) % Q
    pp[0] = (pp[0] - v_) % Q
    bb = [at ** i % Q for i in range(len(pp))]
    gg = list(G)
    gen = mul(z_, U)
    rounds, trace = [], []
    for u in us:
        L, R, lv, rv = cross(pp, bb, gg, gen)
        rounds.append((L, R))
        pp2, bb2, gg2 = code_fold(pp, bb, gg, u)
        trace.append(dict(p=pp, b=bb, G=gg, L=L, R=R, lv=lv, rv=rv, u=u, p2=pp2, b2=bb2, G2=gg2))
        pp, bb, gg = pp2, bb2, gg2
    return v_, rounds, pp[0], trace


def code_verify(commitment, S_, v_, xi_, z_, us, rounds, c, at=x):
    """Mirrors verifier.rs verify_proof, then evaluates the MSM to the identity."""
    pt = add(add(commitment, mul(Q - v_, G[0])), mul(xi_, S_))
    start = pt
    for u, (L, R) in zip(us, rounds):
        pt = add(add(pt, mul(inv(u), L)), mul(u, R))
    bb = compute_b(at, us)
    ss = compute_s(us, 1)
    rhs = add(mul(c, msm(ss, G)), mul(c * bb * z_ % Q, U))
    return pt == rhs, start, pt, bb, ss, rhs


def clean_run(xi_, z_, us):
    """True when a run has no identity points and no point equal to a public generator."""
    try:
        _, rr, c_, tt = code_prove(a, mask, xi_, z_, us)
        _, start, end, _, _, rhs = code_verify(C, S, y, xi_, z_, us, rr, c_)
        nondegenerate(start, end, rhs, mul(z_, U))
        pts_ = [start, end, S, C]
        for tr_ in tt:
            nondegenerate(tr_['L'], tr_['R'], *tr_['G2'])
            pts_ += [tr_['L'], tr_['R'], *tr_['G2']]
    except AssertionError:
        return False
    return c_ not in (0, 1) and len(set(pts_)) == len(pts_) and all(val != 0 for tr_ in tt for val in tr_['p2'] + tr_['b2'])


# Keep the numbers small and readable, taking the first clean choice.
def distinct_scalars(xi_, z_, us):
    """The masked and unmasked final scalars differ from each other and from a_hat, s(x) and y."""
    c_mask = code_prove(a, mask, xi_, z_, us)[2]
    c_none = code_prove(a, [0, 0, 0, 0], xi_, z_, us)[2]
    return len({c_mask, c_none, a_hat, s_at, y}) == 5


xi, z, c_run = next((p, q, [r, t]) for p in range(6, 16) for q in range(10, 20) for r in range(14, 24) for t in range(17, 27) if r != t
                    if clean_run(p, q, [r, t]) and distinct_scalars(p, q, [r, t]))
v, rounds, c_final, trace = code_prove(a, mask, xi, z, c_run)
assert v == y
ok, Pp, Pend, b_end, s_end, rhs_end = code_verify(C, S, v, xi, z, c_run, rounds, c_final)
assert ok
p_prime = trace[0]['p']
assert sum(c * x ** i for i, c in enumerate(p_prime)) % Q == 0
assert Pp == msm(p_prime, G) and msm(s_end, G) == trace[1]['G2'][0] and b_end == trace[1]['b2'][0]
for tr in trace:
    nondegenerate(tr['L'], tr['R'])
nondegenerate(Pp, Pend, rhs_end)
assert c_final != 0

frag['mask'] = (f'Start from the random vector ${vec(raw_s)}$, whose polynomial takes the value ${s_at}$ at $x = {x}$. Subtracting that from the constant coefficient gives $\\v{{s}}_{{\\text{{mask}}}} = {vec(mask)}$, whose polynomial has a root at ${x}$. '
                f'Its commitment is $S = {show(S)}$.')
frag['p-prime'] = (f'With $\\xi = {xi}$, the combined vector is $\\v{{a}} + {xi}\\v{{s}}_{{\\text{{mask}}}} = {vec([(m * xi + c) % Q for m, c in zip(mask, a)])}$. It still evaluates to ${v}$ at $x = {x}$, because the mask contributes zero there. '
                   f'Subtracting $v = {v}$ from the constant coefficient gives $\\tilde{{\\v{{a}}}} = {vec(p_prime)}$, and direct evaluation gives $\\dot{{\\tilde{{\\v{{a}}}}}}{{\\v{{b}}}} = {dot(p_prime, b)}$. '
                   f'The verifier computes $\\tilde{{P}} = C - {v} \\cdot G_0 + {xi} \\cdot S = {show(Pp)}$, and committing to $\\tilde{{\\v{{a}}}}$ directly gives ${show(msm(p_prime, G))}$.')

rows = ['| Step | Party | Value |', '| --- | --- | --- |']
rows.append(f'| Transcript already holds $C$, $x$, $v$ | Both | ${show(C)}$, ${x}$, ${v}$ |')
rows.append(f'| Send mask commitment | Prover | $S = {show(S)}$ |')
rows.append(f'| Challenges | Verifier | $\\xi = {xi}$, $z = {z}$ |')
rows.append(f'| Compute $\\tilde{{P}}$ | Both | ${show(Pp)}$ |')
for j, tr in enumerate(trace, start=1):
    rows.append(f'| Send round {j} cross terms | Prover | $L_{j} = {show(tr["L"])}$, $R_{j} = {show(tr["R"])}$ |')
    rows.append(f'| Challenge | Verifier | $w_{j} = {tr["u"]}$ |')
    rows.append(f'| Fold the coefficient vector and $\\v{{b}}$ | Prover | ${vec(tr["p2"])}$ and ${vec(tr["b2"])}$ |')
    rows.append(f'| Fold $\\v{{G}}$ | Prover | ${pts(tr["G2"])}$ |')
rows.append(f'| Send final scalar | Prover | $c = {c_final}$ |')
rows.append(f'| Compute $\\hat{{b}}$ with `compute_b` | Verifier | ${b_end}$ |')
rows.append(f'| Compute $\\v{{s}}$ with `compute_s` | Verifier | ${vec(s_end)}$ |')
rows.append(f'| Compute $\\hat{{G}} = \\dot{{\\v{{s}}}}{{\\v{{G}}}}$ | Verifier | ${show(msm(s_end, G))}$ |')
rows.append(f'| Left side $\\tilde{{P}} + \\sum_j (w_j^{{-1}} \\cdot L_j + w_j \\cdot R_j)$ | Verifier | ${show(Pend)}$ |')
rows.append(f'| Right side $c \\cdot \\hat{{G}} + (c \\hat{{b}} z) \\cdot U$ | Verifier | ${show(rhs_end)}$ |')
frag['code-run'] = '\n'.join(rows)

# What the mask changes in the final scalar.
_, _, c_plain, _ = code_prove(a, [0, 0, 0, 0], xi, z, c_run)
assert c_plain != c_final
assert c_plain != a_hat and c_final != a_hat
frag['mask-effect'] = (f'Take the run above, with $\\xi = {xi}$, $z = {z}$ and $(w_1, w_2) = ({c_run[0]}, {c_run[1]})$, and repeat it with the mask set to zero. The final scalar becomes ${c_plain}$ in place of ${c_final}$. '
                       f'Without the mask, the scalar is a fixed linear combination of $\\v{{a}}$ whose weights anyone can compute from the public challenges. With the mask, it also depends on the random entries of $\\v{{s}}_{{\\text{{mask}}}}$, which the verifier never sees.')

# xi must come after S: a mask with s(x) != 0 can absorb a false v for one value of xi only.
bad_mask = raw_s
S_bad = msm(bad_mask, G)
v_false = y_false
target_xi = (v_false - y) * inv(s_at) % Q
wins = []
for candidate in range(Q):
    p2 = [(m * candidate + c) % Q for m, c in zip(bad_mask, a)]
    p2[0] = (p2[0] - v_false) % Q
    bb = list(b)
    gg = list(G)
    gen = mul(z, U)
    rr = []
    pp = p2
    for u in c_run:
        L, R, _, _ = cross(pp, bb, gg, gen)
        rr.append((L, R))
        pp, bb, gg = code_fold(pp, bb, gg, u)
    good, *_ = code_verify(C, S_bad, v_false, candidate, z, c_run, rr, pp[0])
    if good:
        wins.append(candidate)
assert wins == [target_xi]
frag['xi-count'] = (f'Suppose the prover claims the false value $v = {v_false}$ and commits to the unadjusted mask ${vec(bad_mask)}$, which takes the value ${s_at}$ at $x = {x}$. '
                    f'The combination evaluates to the claimed value only if ${y} + \\xi \\cdot {s_at} = {v_false}$, so the prover needs $\\xi = {target_xi}$. Running the full argument for all 43 values of $\\xi$ gives acceptance at $\\xi = {wins[0]}$ and nowhere else, a chance of ${len(wins)}/43$.')

# z guards the U coefficient.
delta = 6
v_shift = (y - delta) % Q
C_shift = add(C, mul(delta, U))
wins = []
for candidate in range(1, Q):
    gen = mul(candidate, U)
    pp = [(m * xi + c) % Q for m, c in zip(mask, a)]
    pp[0] = (pp[0] - v_shift) % Q
    bb, gg, rr = list(b), list(G), []
    for u in c_run:
        L, R, _, _ = cross(pp, bb, gg, gen)
        rr.append((L, R))
        pp, bb, gg = code_fold(pp, bb, gg, u)
    good, *_ = code_verify(C_shift, S, v_shift, xi, candidate, c_run, rr, pp[0])
    if good:
        wins.append(candidate)
assert wins == [1]
p_shift = [(m * xi + c) % Q for m, c in zip(mask, a)]
p_shift[0] = (p_shift[0] - v_shift) % Q
ip_shift = dot(p_shift, b)
z_pred = delta * inv(ip_shift) % Q
assert z_pred == wins[0]
nondegenerate(C_shift)
frag['z-count'] = (f'The prover sends $C^* = C + {delta} \\cdot U = {show(C_shift)}$ and claims $v = {y} - {delta} = {v_shift}$. The vector behind the $\\v{{G}}$ part of $C^*$ still evaluates to ${y}$, so the claim is false for that vector. '
                   f'After subtracting $v$, the inner product is $\\dot{{\\tilde{{\\v{{a}}}}}}{{\\v{{b}}}} = {ip_shift}$, and the spare ${delta} \\cdot U$ in $C^*$ supplies the matching $U$ term as long as $U$ carries weight 1. '
                   f'The formula above predicts that only $z = \\delta / \\dot{{\\tilde{{\\v{{a}}}}}}{{\\v{{b}}}} = {delta}/{ip_shift} = {z_pred}$ passes. '
                   f'Running the argument for all 42 nonzero values of $z$ confirms acceptance at $z = {wins[0]}$ only, which is the case where the scaling does nothing. A fixed, unscaled $U$ would therefore accept this claim every time, and a random $z$ accepts it with probability ${len(wins)}/42$.')

print(json.dumps(frag))
