"""Worked example for polynomial-commitments.md. Prints fragments as JSON."""
import json
from toy_curve import G, H, Q, U, add, curve_points, log, msm, mul, show

n = 4
f = [7, 2, 5, 3]
g = [3, 1, 8, 4]
x = 9
frag = {}


def poly(c, var='X'):
    coef = lambda a: '' if a == 1 else str(a)
    terms = [str(c[0])] + [f'{coef(a)}{var}' if i == 1 else f'{coef(a)}{var}^{i}' for i, a in enumerate(c) if i]
    return ' + '.join(terms)


def ev(c, at):
    return sum(a * at ** i for i, a in enumerate(c)) % Q


C = msm(f, G)
rows = ['| Term | Point | Running sum |', '| --- | --- | --- |']
running = None
for i, a in enumerate(f):
    term = mul(a, G[i])
    running = add(running, term)
    rows.append(f'| ${a}\\cdot G_{i}$ | ${show(term)}$ | ${show(running)}$ |')
frag['generators'] = '\n'.join(
    ['| Name | Point |', '| --- | --- |']
    + [f'| $G_{i}$ | ${show(a)}$ |' for i, a in enumerate(G)]
    + [f'| $H$ | ${show(H)}$ |', f'| $U$ | ${show(U)}$ |'])
frag['commit'] = (f'Take $\\v{{a}} = ({", ".join(map(str, f))})$. Scalars live in $\\F_{{43}}$, and each point sum '
                  'follows the curve addition law over $\\F_{31}$.\n\n' + '\n'.join(rows)
                  + f'\n\nThe commitment is the single point $C = {show(C)}$.')

a1 = log(G[1], G[0])
forged = [(f[0] + a1) % Q, (f[1] - 1) % Q, f[2], f[3]]
assert msm(forged, G) == C and forged != f
frag['forgery'] = (f'Counting multiples of $G_0$ shows that $G_1 = {a1}\\cdot G_0$, so ${a1}\\cdot G_0 - G_1 = \\mathcal{{O}}$. '
                   f'Adding this relation to the honest vector gives $\\v{{a}}\' = ({f[0]}+{a1},\\ {f[1]}-1,\\ {f[2]},\\ {f[3]}) = '
                   f'({", ".join(map(str, forged))})$ with scalars reduced modulo 43. Computing '
                   f'$\\dot{{\\v{{a}}\'}}{{\\v{{G}}}}$ gives ${show(msm(forged, G))}$, the same point as $C$, so this commitment now has two valid openings.')

Cg = msm(g, G)
r = 6
combo = [(u + r * v) % Q for u, v in zip(f, g)]
combined = add(C, mul(r, Cg))
assert combined == msm(combo, G)
frag['homomorphism'] = (f'Take a second vector $\\v{{b}} = ({", ".join(map(str, g))})$, whose commitment is $C_b = {show(Cg)}$, and the scalar $r = {r}$. '
                        f'Working only with the two points, we compute ${r} \\cdot C_b$ and add $C$, which gives $C + {r} \\cdot C_b = {show(combined)}$. '
                        f'Working only with the vectors, we form $\\v{{a}} + {r}\\v{{b}} = ({f[0]} + {r}\\cdot {g[0]},\\ {f[1]} + {r}\\cdot {g[1]},\\ {f[2]} + {r}\\cdot {g[2]},\\ {f[3]} + {r}\\cdot {g[3]}) = ({", ".join(map(str, combo))})$ '
                        f'modulo 43 and commit to it directly, which gives ${show(msm(combo, G))}$. The two routes reach the same point, '
                        'and the first route never looked at either vector.')

g1, g2 = 20, 29
frag['hiding'] = (f'Committing to $\\v{{a}}$ with blinding factors $\\gamma = {g1}$ and $\\gamma = {g2}$ gives '
                  f'${show(add(C, mul(g1, H)))}$ and ${show(add(C, mul(g2, H)))}$. Both differ from the unblinded $C = {show(C)}$, '
                  'and without the blinding factor an observer cannot test a guessed vector against either point.')

powers = [x ** i % Q for i in range(n)]
rows = ['| $i$ | $a_i$ | $x^i$ | $a_i x^i$ |', '| --- | --- | --- | --- |']
for i in range(n):
    rows.append(f'| {i} | {f[i]} | {powers[i]} | {f[i] * powers[i] % Q} |')
y = sum(a * b for a, b in zip(f, powers)) % Q
assert y == ev(f, x)
frag['evaluation'] = (f'Let $p(X) = {poly(f)}$ over $\\F_{{43}}$, whose coefficient vector is the $\\v{{a}}$ from Section 3, and take $x = {x}$.\n\n'
                      + '\n'.join(rows)
                      + f'\n\nThe last column sums to $y = {y}$ modulo 43. Direct substitution into $p$ gives $p({x}) = {ev(f, x)}$, the same value.')

P_point = add(C, mul(y, U))
assert P_point == msm(f + [y], G + [U])
wrong = (y + 1) % Q
frag['claim'] = (f'The statement point is $P = C + {y}\\cdot U = {show(P_point)}$. Treating it as a five-entry commitment to $({", ".join(map(str, f))},\\ {y})$ '
                 f'under the generators $(G_0, G_1, G_2, G_3, U)$ gives ${show(msm(f + [y], G + [U]))}$, the same point. '
                 f'A prover claiming $y = {wrong}$ instead has the statement point $C + {wrong}\\cdot U = {show(add(C, mul(wrong, U)))}$, '
                 'which does not match the honest computation from the coefficients.')

# Curve arithmetic
G0 = G[0]
s = 3 * G0[0] ** 2 * pow(2 * G0[1], -1, 31) % 31
x3 = (s * s - 2 * G0[0]) % 31
y3 = (s * (G0[0] - x3) - G0[1]) % 31
assert (x3, y3) == mul(2, G0)
rows = ['| $k$ | $k \\cdot G_0$ |', '| --- | --- |']
for k in [1, 2, 3, 4, 41, 42]:
    rows.append(f'| {k} | ${show(mul(k, G0))}$ |')
assert add(mul(42, G0), G0) is None and add(add(mul(42, G0), G0), G0) == G0
frag['doubling'] = (f'Doubling $G_0 = {show(G0)}$ uses the tangent slope, computed modulo 31: '
                    f'$s = 3x^2 / (2y) = {3 * G0[0] ** 2} / {2 * G0[1]} = {s}$. The new coordinates are '
                    f'$x_3 = s^2 - 2x = {x3}$ and $y_3 = s(x - x_3) - y = {y3}$, so $2 \\cdot G_0 = {show((x3, y3))}$.')
frag['multiples'] = '\n'.join(rows) + (f'\n\nOne more addition gives $43 \\cdot G_0 = \\mathcal{{O}}$, and one after that gives $44 \\cdot G_0 = G_0$. '
                                       'The multiples repeat with period 43, so only the value of a scalar modulo 43 affects the result.')

# Why one generator per position
# Chosen so that its commitment does not coincide with U or another named point.
perm = [f[0], f[2], f[3], f[1]]
assert msm(perm, G) not in (C, Cg, U, H, *G)
assert sum(perm) % Q == sum(f) % Q and msm(perm, G) != C
frag['same-generator'] = (f'The vectors $({", ".join(map(str, f))})$ and $({", ".join(map(str, perm))})$ have the same entries in different positions. '
                          f'With $G_0$ in every position, both produce ${sum(f) % Q} \\cdot G_0 = {show(mul(sum(f), G0))}$. '
                          f'With a separate generator for each position, they produce ${show(C)}$ and ${show(msm(perm, G))}$.')

# Checking the forgery
frag['forgery-check'] = '\n'.join([
    '| Part of the sum | Honest vector | Forged vector |', '| --- | --- | --- |',
    f'| Entry 0 term | ${f[0]} \\cdot G_0 = {show(mul(f[0], G[0]))}$ | ${forged[0]} \\cdot G_0 = {show(mul(forged[0], G[0]))}$ |',
    f'| Entry 1 term | ${f[1]} \\cdot G_1 = {show(mul(f[1], G[1]))}$ | ${forged[1]} \\cdot G_1 = {show(mul(forged[1], G[1]))}$ |',
    f'| Sum of entries 0 and 1 | ${show(add(mul(f[0], G[0]), mul(f[1], G[1])))}$ | ${show(add(mul(forged[0], G[0]), mul(forged[1], G[1])))}$ |',
    f'| Entries 2 and 3 | Unchanged | Unchanged |',
    f'| Commitment | ${show(C)}$ | ${show(msm(forged, G))}$ |',
])

# Hiding
guesses = [g, perm, f]
rows = ['| Guess | Recomputed commitment | Matches $C$ |', '| --- | --- | --- |']
for v in guesses:
    rows.append(f'| $({", ".join(map(str, v))})$ | ${show(msm(v, G))}$ | {"Yes" if msm(v, G) == C else "No"} |')
frag['guess-test'] = '\n'.join(rows)
blinded = add(C, mul(g1, H))
other_log = log(add(blinded, mul(Q - 1, Cg)), H)
assert add(Cg, mul(other_log, H)) == blinded
frag['hiding-any'] = (f'Take the blinded commitment $\\bar{{C}} = {show(blinded)}$ made from $\\v{{a}}$ with $\\gamma = {g1}$. '
                      f'The unrelated vector $\\v{{b}} = ({", ".join(map(str, g))})$ also explains this point, using $\\gamma = {other_log}$: '
                      f'$\\dot{{\\v{{b}}}}{{\\v{{G}}}} + {other_log} \\cdot H = {show(add(Cg, mul(other_log, H)))}$. '
                      'An observer sees one point, and every candidate vector has exactly one blinding factor that fits it.')

# Padding
short = [6, 1, 0, 0]
frag['padding'] = (f'The polynomial $6 + X$ has degree 1, so its vector is padded with zeros to $({", ".join(map(str, short))})$. '
                   f'Its commitment is $6 \\cdot G_0 + 1 \\cdot G_1 = {show(msm(short, G))}$, because the zero entries contribute $\\mathcal{{O}}$.')

# Linear combinations of evaluations
ya, yb = ev(f, x), ev(g, x)
assert ev(combo, x) == (ya + r * yb) % Q
frag['combination'] = (f'Read $\\v{{b}}$ as the polynomial $q(X) = {poly(g)}$, the same $q$ that Statements and Challenges used. '
                       f'The verifier holds $C$ and $C_b$ together with the claims $p({x}) = {ya}$ and $q({x}) = {yb}$. '
                       f'From the points alone it computes $C + {r} \\cdot C_b = {show(combined)}$, as in Section 5, and from the claims alone it computes '
                       f'${ya} + {r} \\cdot {yb} = {(ya + r * yb) % Q}$ modulo 43. These two values belong together. The point ${show(combined)}$ commits to '
                       f'$({", ".join(map(str, combo))})$, and that polynomial takes the value ${ev(combo, x)}$ at $x = {x}$.')

# A claim forged with a known relation to U
logs = [log(a, G[0]) for a in G]
u = log(U, G[0])
weights = [(lg + pw * u) % Q for lg, pw in zip(logs, powers)]
target = (sum(a * lg for a, lg in zip(f, logs)) + wrong * u) % Q
first = (target - sum(a * w for a, w in zip(f[1:], weights[1:]))) * pow(weights[0], -1, Q) % Q
fake = [first] + f[1:]
inner = sum(a * b for a, b in zip(fake, powers)) % Q
statement = add(C, mul(wrong, U))
assert add(msm(fake, G), mul(inner, U)) == statement and inner != wrong
gap_a = (f[0] - fake[0]) % Q
gap_y = (wrong - inner) % Q
assert add(mul(gap_a, G[0]), mul(gap_y, U)) is None
lhs = ' + '.join(('a_0' if i == 0 else f'{logs[i]}a_{i}') for i in range(n))
pw_sum = ' + '.join(('a_0' if i == 0 else f'{powers[i]}a_{i}') for i in range(n))
known = sum(a * w for a, w in zip(f[1:], weights[1:])) % Q
assert logs[0] == 1 and (target - known) * pow(weights[0], -1, Q) % Q == fake[0]
assert statement == mul(target, G[0])
frag['forged-claim'] = (
    f'Counting gives the discrete logs of $G_1, G_2, G_3$ and $U$ relative to $G_0$: ${logs[1]}$, ${logs[2]}$, ${logs[3]}$ and ${u}$. '
    f'The prover wants to claim the false value $y = {wrong}$, whose statement point is $C + {wrong} \\cdot U = {show(statement)}$. '
    f'Counting once more shows that this point is ${target} \\cdot G_0$.\n\n'
    f'Next, the prover writes every point in the equation $P = \\dot{{\\v{{a}}}}{{\\v{{G}}}} + \\dot{{\\v{{a}}}}{{\\v{{x^n}}}} \\cdot U$ as a multiple of $G_0$. '
    f'Each term $a_i \\cdot G_i$ contributes $a_i$ times the discrete log of $G_i$, and the inner product with the powers $({", ".join(map(str, powers))})$ of $x = {x}$ '
    f'gets multiplied by the discrete log of $U$, which is ${u}$. Comparing the multiples of $G_0$ on both sides gives one linear equation over $\\F_{{43}}$:\n\n'
    f'$${lhs} + {u}({pw_sum}) \\equiv {target} \\pmod{{43}}.$$\n\n'
    f'Collecting the terms for each entry and reducing modulo 43 gives\n\n'
    f'$${weights[0]}a_0 + {weights[1]}a_1 + {weights[2]}a_2 + {weights[3]}a_3 \\equiv {target} \\pmod{{43}}.$$\n\n'
    f'The prover keeps entries 1 to 3 of the honest vector, $a_1 = {f[1]}$, $a_2 = {f[2]}$ and $a_3 = {f[3]}$. '
    f'Their terms add up to ${weights[1]} \\cdot {f[1]} + {weights[2]} \\cdot {f[2]} + {weights[3]} \\cdot {f[3]} = {known}$ modulo 43, '
    f'so ${weights[0]}a_0 \\equiv {target} - {known} = {(target - known) % Q}$, and dividing by ${weights[0]}$ gives $a_0 = {fake[0]}$. '
    f'The next table checks the forged vector against the false statement point.\n\n'
    + '\n'.join([
        '| Quantity | Value |', '| --- | --- |',
        f'| Forged vector $\\v{{a}}\'$ | $({", ".join(map(str, fake))})$ |',
        f'| Inner product $\\dot{{\\v{{a}}\'}}{{\\v{{x^n}}}}$ | ${inner}$ |',
        f'| $\\dot{{\\v{{a}}\'}}{{\\v{{G}}}} + {inner} \\cdot U$ | ${show(add(msm(fake, G), mul(inner, U)))}$ |',
        f'| False statement point $C + {wrong} \\cdot U$ | ${show(statement)}$ |',
    ])
    + f'\n\nThe last two rows agree, so the check passes, although the forged vector does not open $C$ and its inner product is ${inner}$ rather than ${wrong}$.\n\n'
    f'The honest vector gives a second opening $(\\v{{a}},\\ {wrong})$ of the same point, as in the derivation above. Subtracting the forged opening from it leaves the relation '
    f'$({f[0]} - {fake[0]}) \\cdot G_0 + ({wrong} - {inner}) \\cdot U = {gap_a} \\cdot G_0 + {gap_y} \\cdot U = \\mathcal{{O}}$. '
    f'The prover can cancel these two terms only because it knows $U = {u} \\cdot G_0$, which turns ${gap_y} \\cdot U$ into ${gap_y * u % Q} \\cdot G_0$.')

# A commitment that hides a multiple of U
delta = 6
C_star = add(C, mul(delta, U))
y_star = (y - delta) % Q
P_star = add(C_star, mul(y_star, U))
assert P_star == P_point == add(msm(f, G), mul(y, U)) and y_star != y
x_other = 2
shifted = [(f[0] - delta) % Q] + f[1:]
C_shifted = msm(shifted, G)
assert C_shifted != C_star and ev(shifted, x) == y_star
assert all(ev(shifted, t) == (ev(f, t) - delta) % Q for t in range(Q))
frag['hidden-u'] = (
    f'The prover keeps the honest vector $\\v{{a}} = ({", ".join(map(str, f))})$ but sends $C^* = C + {delta} \\cdot U = {show(C_star)}$ in place of $C$. '
    f'The polynomial in the $\\v{{G}}$ part of $C^*$ is still $p$, so its value at $x = {x}$ is ${y}$. The prover claims $y = {y} - {delta} = {y_star}$ instead.\n\n'
    + '\n'.join([
        '| Quantity | Value |', '| --- | --- |',
        f'| Statement point $C^* + {y_star} \\cdot U$ | ${show(P_star)}$ |',
        f'| Inner product $\\dot{{\\v{{a}}}}{{\\v{{x^n}}}}$ | ${y}$ |',
        f'| $\\dot{{\\v{{a}}}}{{\\v{{G}}}} + {y} \\cdot U$ | ${show(add(msm(f, G), mul(y, U)))}$ |',
    ])
    + f'\n\nThe last two rows agree, so the honest vector satisfies the textbook statement for the false claim ${y_star}$. '
    f'The hidden ${delta} \\cdot U$ and the claimed ${y_star} \\cdot U$ add up to the ${y} \\cdot U$ that the true value needs.')
frag['hidden-u-shift'] = (
    f'At $x = {x_other}$ the same $C^*$ passes only with the claim $p({x_other}) - {delta} = {ev(f, x_other)} - {delta} = {ev(shifted, x_other)}$. '
    f'These accepted values belong to the polynomial $p - {delta}$, whose coefficient vector is $({", ".join(map(str, shifted))})$. '
    f'Its ordinary commitment would be $C - {delta} \\cdot G_0$, a point built from $\\v{{G}}$ alone, and no vector the prover knows opens $C^*$ under $\\v{{G}}$ alone.')

# Knowing the point before committing
early = [(f[0] - x) % Q, (f[1] + 1) % Q, f[2], f[3]]   # p(X) + (X - 9)
C_early = msm(early, G)
agree = [t for t in range(Q) if ev(early, t) == ev(f, t)]
assert agree == [x] and C_early != C and ev(early, x) == y
frag['early-point'] = (
    f'Suppose the protocol requires a commitment to $p$, and the prover learns the point $x = {x}$ before it commits. It can commit instead to '
    f'$p\'(X) = p(X) + (X - {x}) = {poly(early)}$, whose commitment is $C\' = {show(C_early)}$. '
    f'This is an honest commitment to $p\'$, and an honest opening gives $p\'({x}) = {ev(early, x)}$, the same value as $p({x})$, so the check at ${x}$ cannot tell the two apart. '
    f'At any other point the two values differ by $x - {x} \\neq 0$, and checking all 43 points of $\\F_{{43}}$ confirms that $p\'$ and $p$ agree only at ${x}$. '
    f'If the verifier picks $x$ after receiving $C\'$, the substitution passes with probability $1/43$.')

# A full run with the coefficients revealed
frag['reveal-run'] = '\n'.join([
    '| Step | Party | Value or check |', '| --- | --- | --- |',
    f'| 1 | Prover commits | $C = {show(C)}$ |',
    f'| 2 | Verifier sends a challenge | $x = {x}$ |',
    f'| 3 | Prover sends the claimed value | $y = {y}$ |',
    f'| 4 | Prover reveals the coefficients | $\\v{{a}} = ({", ".join(map(str, f))})$ |',
    f'| 5 | Verifier computes the statement point | $P = C + {y} \\cdot U = {show(P_point)}$ |',
    f'| 6 | Verifier computes the power vector | $\\v{{x^n}} = ({", ".join(map(str, powers))})$ |',
    f'| 7 | Verifier computes the inner product | $\\dot{{\\v{{a}}}}{{\\v{{x^n}}}} = {y}$ |',
    f'| 8 | Verifier checks the equation | $\\dot{{\\v{{a}}}}{{\\v{{G}}}} + {y} \\cdot U = {show(add(msm(f, G), mul(y, U)))}$, which equals $P$ |',
])
gates_log = 11                          # Ragu's production rank, at most 2^11 gates (crates/ragu_circuits/src/polynomials/mod.rs at 3219e08)
k = gates_log + 2                       # each polynomial has 4N coefficients for N gates
frag['sizes'] = (f'Ragu\'s circuits have at most $2^{{{gates_log}}}$ gates, a limit set by the '
                 '[production rank](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/polynomials/mod.rs#L123-L127) '
                 'at commit `3219e08`. The previous chapter\'s polynomials have four coefficients per gate, '
                 f'so the committed vectors have length $n = 4 \\cdot 2^{{{gates_log}}} = 2^{{{k}}}$. '
                 f'With 32-byte values, revealing the coefficients costs ${2 ** k:,} \\times 32 = {2 ** k * 32:,}$ bytes. '
                 f'The argument of the next chapter halves the vector once per round, which takes ${k}$ rounds, and it sends two points per round. '
                 f'Those ${2 * k}$ group elements cost ${2 * k * 32}$ bytes, plus a small constant number of extra values.')

# The named points of the chapter are distinct, so no coincidence carries meaning.
named = [C, Cg, add(C, mul(g1, H)), P_point, combined, U, H, *G]
assert len(set(named)) == len(named)


# The curve's size, counted rather than typed
frag['curve-size'] = f'This curve has {len(curve_points()) + 1} points including the identity $\\mathcal{{O}}$.'
assert len(curve_points()) + 1 == Q

# Replacing the oracles of the previous chapter's run with commitments and openings.
# The polynomials are the previous chapter's run (witness with secret input 3, z = 5, y = 7).
# N = 2 gates there, so each polynomial has 4N = 8 coefficients and needs 8 generators.
# The four extra generators are the ones the NARK chapter uses.
EXTRA = [(4, 6), (5, 2), (25, 2), (30, 23)]
assert all(a in curve_points() for a in EXTRA)
GENS = G + EXTRA
assert len(set(GENS + [H, U])) == 10
r_poly = [9, 27, 9, 3, 3, 3, 0, 0]
c1_poly = [13, 14, 29, 18, 9, 0, 39, 38]
c2_poly = [9, 29, 39, 15, 8, 0, 0, 0]
x_run, z_run = 9, 5
xinv = pow(x_run, -1, Q)
C_r, C_c1, C_c2 = msm(r_poly, GENS), msm(c1_poly, GENS), msm(c2_poly, GENS)
assert len({C_r, C_c1, C_c2}) == 3 and None not in (C_r, C_c1, C_c2)
gates_run = 2                             # the previous chapter's toy circuit
assert 4 * gates_run == len(GENS) == len(r_poly)
frag['replace-gens'] = (f'The previous chapter\'s toy run had {gates_run} gates, so each of $r(X)$, $c_1(X)$ and $c_2(X)$ has '
                        f'$4 \\cdot {gates_run} = {4 * gates_run}$ coefficients, as Section 7 explained, and needs {len(GENS)} generators. '
                        f'Section 2 fixed only {len(G)}, so we add {len(EXTRA)} more points at unused $x$-coordinates, the same ones that the '
                        '[NARK chapter](./nark.md) uses later.\n\n') + '\n'.join(
    ['| Name | Point |', '| --- | --- |']
    + [f'| $G_{i + 4}$ | ${show(a)}$ |' for i, a in enumerate(EXTRA)])
frag['replace-commit'] = '\n'.join([
    '| Step | Party | Message |', '| --- | --- | --- |',
    f'| 1 | Prover commits to $r(X)$ | $C_r = {show(C_r)}$ |',
    f'| 2 | Verifier sends challenges | $z = {z_run}$, $y = 7$ |',
    f'| 3 | Prover commits to $c_1(X)$ and $c_2(X)$ | $C_{{c_1}} = {show(C_c1)}$, $C_{{c_2}} = {show(C_c2)}$ |',
    f'| 4 | Verifier sends challenge | $x = {x_run}$ |',
])
claims = [('C_r', 'r', C_r, r_poly, x_run, 'r(x)'),
          ('C_r', 'r', C_r, r_poly, x_run * z_run % Q, 'r(xz)'),
          ('C_{c_1}', 'c_1', C_c1, c1_poly, xinv, 'c_1(x^{-1})'),
          ('C_{c_1}', 'c_1', C_c1, c1_poly, 0, 'c_1(0)'),
          ('C_{c_2}', 'c_2', C_c2, c2_poly, x_run, 'c_2(x)')]
expected = [5, 9, 6, 13, 30]          # the oracle answers in the previous chapter's run
rows = ['| Oracle query | Commitment | Point | Power vector | Value |',
        '| --- | --- | --- | --- | --- |']
for (cname, _, _, coeffs, at, label), want in zip(claims, expected):
    pw = [pow(at, i, Q) if i else 1 for i in range(8)]
    val = sum(a * b for a, b in zip(coeffs, pw)) % Q
    assert val == ev(coeffs, at) == want
    rows.append(f'| ${label}$ | ${cname}$ | ${at}$ | $({", ".join(map(str, pw))})$ | ${val}$ |')
frag['replace-claims'] = '\n'.join(rows)

# The split and target checks with the opened values.
# s(9, 7), t(9, 5) and k(7) are the verifier's own values from step 10 of the previous chapter's run.
s_val, t_val, k_val = 23, 3, 13
rx, rxz, c1inv, c10, c2x = expected
deg = 4 * gates_run
lhs_split = rx * (rxz + s_val + t_val) % Q
xa, xb = pow(x_run, deg - 1, Q), pow(x_run, deg, Q)
rhs_split = (xa * c1inv + xb * c2x) % Q
assert lhs_split == rhs_split and c10 == k_val
frag['replace-checks'] = (
    f'The split check compares $r(x)\\big(r(xz) + s(x, y) + t(x, z)\\big)$ with '
    f'$x^{{4N-1}} c_1(x^{{-1}}) + x^{{4N}} c_2(x)$, where $N = {gates_run}$ is the gate count, so the powers are $x^{{{deg - 1}}}$ and $x^{{{deg}}}$. The verifier computes $s(9, 7) = {s_val}$ and $t(9, 5) = {t_val}$ itself, '
    f'as in step 10 of the previous chapter\'s run, along with $x^{{{deg - 1}}} = {xa}$ and $x^{{{deg}}} = {xb}$. Substituting the opened values gives '
    f'${rx} \\cdot ({rxz} + {s_val} + {t_val}) = {lhs_split}$ on the left and '
    f'${xa} \\cdot {c1inv} + {xb} \\cdot {c2x} = {rhs_split}$ on the right, the same equality as step 11 there. '
    f'The target check compares the opened $c_1(0) = {c10}$ with $k(7) = {k_val}$, as in step 12.')

print(json.dumps(frag))
