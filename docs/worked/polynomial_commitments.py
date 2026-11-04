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

print(json.dumps(frag))
