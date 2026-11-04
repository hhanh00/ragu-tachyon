"""Worked example for polynomial-commitments.md. Prints fragments as JSON."""
import json
from toy_curve import G, H, Q, U, add, log, msm, mul, show

n = 4
f = [7, 2, 5, 3]
g = [3, 1, 8, 4]
x = 9
frag = {}


def poly(c, var='X'):
    terms = [str(c[0])] + [f'{a}{var}' if i == 1 else f'{a}{var}^{i}' for i, a in enumerate(c) if i]
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
total = [(u + v) % Q for u, v in zip(f, g)]
r = 6
scaled = [r * u % Q for u in f]
assert add(C, Cg) == msm(total, G) and mul(r, C) == msm(scaled, G)
frag['homomorphism'] = (f'With $\\v{{b}} = ({", ".join(map(str, g))})$, the commitment is $C_b = {show(Cg)}$. Adding points gives '
                        f'$C + C_b = {show(add(C, Cg))}$. Committing directly to the sum $\\v{{a}} + \\v{{b}} = ({", ".join(map(str, total))})$ gives '
                        f'${show(msm(total, G))}$, the same point. Scaling works the same way: ${r}\\cdot C = {show(mul(r, C))}$, and committing to '
                        f'${r}\\v{{a}} = ({", ".join(map(str, scaled))})$ gives ${show(msm(scaled, G))}$.')

g1, g2 = 17, 29
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

c = 2
# h = f + c(X - 1)(X - 2)(X - 3), so h agrees with f at exactly three points.
cubic = [-6, 11, -6, 1]
h = [(u + c * v) % Q for u, v in zip(f, cubic)]
agree = [t for t in range(Q) if ev(f, t) == ev(h, t)]
assert agree == [1, 2, 3]
frag['agreement'] = (f'Take the different polynomial $q(X) = p(X) + {c}(X-1)(X-2)(X-3) = {poly(h)}$. Evaluating $p$ and $q$ at all 43 points of $\\F_{{43}}$ '
                     f'finds agreement only at $x \\in \\{{{", ".join(map(str, agree))}\\}}$. A uniformly random challenge therefore misses the difference with probability '
                     f'${len(agree)}/{Q}$, which is the Schwartz–Zippel bound for degree 3. On a curve the size of Pallas, the same bound is below $2^{{-240}}$ for any polynomial of the degree Ragu uses.')

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
perm = next(v for v in ([f[2], f[0], f[3], f[1]], [f[3], f[2], f[1], f[0]], [f[1], f[3], f[0], f[2]]) if msm(v, G) != C)
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
combo = [(u + r * v) % Q for u, v in zip(f, g)]
assert ev(combo, x) == (ya + r * yb) % Q and msm(combo, G) == add(C, mul(r, Cg))
frag['combination'] = (f'Take $r = {r}$ with the vectors $\\v{{a}}$ and $\\v{{b}}$ from Section 5, each read as a polynomial, at $x = {x}$. Their evaluations are ${ya}$ and ${yb}$. '
                       f'The combined vector is $\\v{{a}} + {r}\\v{{b}} = ({", ".join(map(str, combo))})$, and its polynomial evaluates to ${ev(combo, x)}$ at $x = {x}$, '
                       f'which equals ${ya} + {r} \\cdot {yb}$ modulo 43. Its commitment is ${show(msm(combo, G))}$, which equals $C + {r} \\cdot C_b$.')

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
frag['forged-claim'] = (f'Counting gives the discrete logs of $G_1, G_2, G_3$ and $U$ relative to $G_0$: ${logs[1]}$, ${logs[2]}$, ${logs[3]}$ and ${u}$. '
                        f'The prover wants to claim the false value $y = {wrong}$, whose statement point is $C + {wrong} \\cdot U = {show(statement)}$. '
                        f'With every point written as a multiple of $G_0$, the equation for $P$ becomes one linear equation over $\\F_{{43}}$ in the four entries of the vector. '
                        f'Keeping entries 1 to 3 fixed and solving for entry 0 gives $\\v{{a}}\' = ({", ".join(map(str, fake))})$. '
                        f'This vector has inner product ${inner}$ with the power vector, and $\\dot{{\\v{{a}}\'}}{{\\v{{G}}}} + {inner} \\cdot U = {show(add(msm(fake, G), mul(inner, U)))}$, '
                        f'so it satisfies the equation for the false statement point. The vector does not open $C$ and does not evaluate to ${wrong}$, yet the check passes.')

# Challenge order
early = list(f)
early[0] = (early[0] - x) % Q
early[1] = (early[1] + 1) % Q
assert ev(early, x) == y and early != f
frag['early-challenge'] = (f'Suppose the prover learns $x = {x}$ before committing. It can then take $q(X) = p(X) + (X - {x}) = {poly(early)}$, a different polynomial that has the same value at this point: '
                           f'$q({x}) = p({x}) = {y}$. A check at $x = {x}$ cannot distinguish the two polynomials, even though their commitments ${show(msm(early, G))}$ and ${show(C)}$ differ.')

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
k = 13
frag['sizes'] = (f'For $n = 2^{{{k}}}$ with 32-byte values, revealing the coefficients costs ${2 ** k} \\times 32 = {2 ** k * 32:,}$ bytes. '
                 f'An argument with ${2 * k}$ group elements costs ${2 * k * 32}$ bytes, plus a small constant number of extra values.')

print(json.dumps(frag))
