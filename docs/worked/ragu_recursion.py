"""Worked examples for ragu-recursion.md. Prints fragments as JSON.

The transcript run mirrors the schedule of crates/ragu_pcd/src/fuse/mod.rs and
the circuits hashes_1.rs and hashes_2.rs at Ragu commit 3219e08. The compression
run mirrors crates/ragu_pcd/src/compress/ at the same commit, on the small
circuits of staging.py, with groups of 3 in place of the code's 7. Counts of real
proofs are read from the codec in crates/ragu_pcd/src/wire/compressed.rs and the
standard Shape pinned in crates/ragu_pcd/src/profile.rs.
"""
import contextlib
import io
import json
from math import log, log2

with contextlib.redirect_stdout(io.StringIO()):
    from staging import (A_POLY, CUBE, F_CU, F_SQ, GD, GENS, N, Q, SQUARE, U, add, commit, ev, mask, mask_closed,
                         curve_points, mul, plus, poly, pos, revdot, scale, show, square_circuit, square_final, stage_a,
                         table, vec)
    from statements_and_challenges import RATE, T, Sponge, permutation

frag = {}
D = 4 * N
SPECIAL = set(GENS + [U, None])


def inv(a):
    assert a % Q != 0
    return pow(a, -1, Q)


def lin(*terms):
    """A linear combination of vectors, given (scalar, vector) pairs."""
    out = [0] * D
    for k, v in terms:
        out = [(e + k * f) % Q for e, f in zip(out, v)]
    return out


def combine(*terms):
    out = None
    for k, a in terms:
        out = add(out, mul(k % Q, a))
    return out


def pt(a):
    return '$' + show(a) + '$'


def n(k):
    return f'{k:,}'


# ---------------------------------------------------------------- The standard shape
# profile.rs standard_is_the_crate_layout, native/mod.rs and nested/mod.rs at 3219e08.
NATIVE_STEPS, NESTED_STEPS, NATIVE_RX, NESTED_RX = 23, 26, 45, 39
BINDERS = 4
NATIVE_FIXED = ['hashes_1', 'hashes_2', 'collapse', 'compute_v', 'bind_beta', 'bind_endoscalar']
NATIVE_CIRCUITS = len(NATIVE_FIXED) + BINDERS + NATIVE_STEPS
NATIVE_MASKS = 11 + 5
NESTED_CIRCUITS = NESTED_STEPS + 2                 # the steps, collapse and compute_v
NATIVE_CLAIMS = 2 + 2 + 2 * NATIVE_CIRCUITS + NATIVE_MASKS
NESTED_CLAIMS_TOTAL = 72                           # internal/tests.rs, as chapter 14 recorded
NESTED_BONDINGS = NESTED_CLAIMS_TOTAL - 2 - 2 * NESTED_CIRCUITS
assert NATIVE_CIRCUITS == 33 and NATIVE_CLAIMS == 86 and NESTED_BONDINGS == 14
assert NATIVE_RX == 1 + 6 + BINDERS + NATIVE_STEPS + 11
assert NATIVE_RX + 4 + NESTED_RX + 4 == 92
NUM_POLYS = 92
frag['census'] = (
    f'In the standard profile, one fuse therefore fills ${NATIVE_RX}$ native polynomials, of which ${NATIVE_CIRCUITS + 1}$ are circuit traces and $11$ are stages, '
    f'and ${NESTED_RX}$ nested polynomials, and it adds the $a$, $b$, `registry_xy` and $p$ polynomials on each side, for [${NUM_POLYS}$ in all]'
    '(https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L2364-L2379). '
    f'The native side folds ${NATIVE_CLAIMS}$ revdot claims and the nested side folds ${NESTED_CLAIMS_TOTAL}$.')


# ---------------------------------------------------------------- The transcript
SCHEDULE = [('preamble', ['w']), ('s_prime', ['y', 'z']), ('inner_error', ['mu']), ('outer_error', ['mu_prime']),
            ('ab', ['x']), ('query', ['alpha']), ('f', ['u']), ('eval', ['pre_beta'])]
NAMES = dict(w='w', y='y', z='z', mu=r'\mu', mu_prime=r"\mu'", x='x', alpha=r'\alpha', u='u', pre_beta=r'\text{pre\_beta}')
BRIDGE = dict(zip([s for s, _ in SCHEDULE], [(21, 25)] + GD[:7]))    # (21, 25) is the bridge commitment of staging.md
assert all(pt_[0] and pt_[1] for pt_ in BRIDGE.values()) and len(set(BRIDGE.values())) == 8


def absorb_point(s, a):
    s.absorb(a[0])
    s.absorb(a[1])


whole = Sponge()
one_run = {}
for stage, squeezes in SCHEDULE:
    absorb_point(whole, BRIDGE[stage])
    for name in squeezes:
        one_run[name] = whole.squeeze()
assert len(whole.trace) == 8 and RATE == 2 and T == 3

# hashes_1: three absorptions, the third followed by save_state.
first = Sponge()
absorb_point(first, BRIDGE['preamble'])
w_1 = first.squeeze()
absorb_point(first, BRIDGE['s_prime'])
y_1, z_1 = first.squeeze(), first.squeeze()
absorb_point(first, BRIDGE['inner_error'])
first.permute()
SAVED = list(first.state)
assert len(first.trace) == 3


def resume(state):
    """Transcript::resume_from_state: squeeze-only until the first challenge is out."""
    s = Sponge()
    s.state = list(state)
    s.squeezing = True
    s.values = s.state[:RATE][::-1]
    return s


def second_half(state):
    s = resume(state)
    mu = s.squeeze()
    out = dict(mu=mu)
    for stage, name in [('outer_error', 'mu_prime'), ('ab', 'x'), ('query', 'alpha'), ('f', 'u'), ('eval', 'pre_beta')]:
        absorb_point(s, BRIDGE[stage])
        out[name] = s.squeeze()
    return out, len(s.trace)


second, second_perms = second_half(SAVED)
assert second_perms == 5
assert dict(w=w_1, y=y_1, z=z_1, **second) == one_run
assert all(v != 0 for v in one_run.values()) and len(set(SAVED)) == 3 and 0 not in SAVED

GATES_PER_PERM, GATE_LIMIT = 288, 2 ** 11     # poseidon/tests/mod.rs L96; ProductionRank n
assert (3 + 5) * GATES_PER_PERM > GATE_LIMIT
frag['perm-cost'] = (
    f'A permutation costs [${GATES_PER_PERM}$ gates](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_primitives/src/poseidon/tests/mod.rs#L96), '
    f'and the code documents [$3$ permutations](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_1.rs#L7-L17) in the first half and '
    f'[$5$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_2.rs#L7-L23) in the second. '
    f'Together that makes ${3 + 5}$ permutations and ${n((3 + 5) * GATES_PER_PERM)}$ gates, which already exceeds the limit of ${n(GATE_LIMIT)}$ gates per circuit before any other check runs. '
    f'The two halves cost ${n(3 * GATES_PER_PERM)}$ and ${n(5 * GATES_PER_PERM)}$ gates, so each fits.')

rows = []
for stage, squeezes in SCHEDULE:
    a_ = BRIDGE[stage]
    who = '`hashes_1`' if stage in ('preamble', 's_prime') else ('`hashes_1`, then saved' if stage == 'inner_error' else '`hashes_2`')
    got = ', '.join(f'${NAMES[k]} = {one_run[k]}$' for k in squeezes)
    rows.append((f'`{stage}`', pt(a_), got, who))
frag['transcript-run'] = table(['Bridge commitment', 'Toy point on $E\'$', 'Squeezed next', 'Replayed by'], rows)

frag['transcript-split'] = (
    f'The first half ends by permuting and saving the three cells of the state, $({SAVED[0]}, {SAVED[1]}, {SAVED[2]})$. '
    f'The second half loads those cells and squeezes $\\mu = {second["mu"]}$ with no further permutation, which is why its count starts from the absorption of `outer_error`. '
    f'We ran the sponge once straight through and once split at this point, and all nine challenges agree. The toy sponge takes $3$ permutations in the first half and $5$ in the second, as the code does, because we leave out the domain tag and its rate of 2 fits one point per permutation.')

# Which saved states pass, by exhaustion.
target_mu = (second['mu'] + 7) % Q
passing = choosing = 0
for s0 in range(Q):
    for s1 in range(Q):
        for s2 in range(Q):
            if [s0, s1, s2] == SAVED:
                passing += 1
            if s0 == target_mu:
                choosing += 1
assert passing == 1 and choosing == Q * Q
forged_state = [target_mu, SAVED[1], SAVED[2]]
forged, _ = second_half(forged_state)
assert forged['mu'] == target_mu
frag['transcript-tamper'] = (
    f'Suppose a prover wants $\\mu = {target_mu}$, and it writes the state $({forged_state[0]}, {forged_state[1]}, {forged_state[2]})$ into `outer_error`. '
    f'The second half alone would resume from this state and produce $\\mu = {forged["mu"]}$ and $\\mu\' = {forged["mu_prime"]}$. '
    f'Of the ${n(Q ** 3)}$ possible states, ${n(choosing)}$ give the wanted $\\mu$, but the first half compares the stage with the state it computed, and exactly ${passing}$ state passes that comparison, the honest one. '
    'Both circuits read one committed stage polynomial, so the prover cannot show them different values.')

# ---------------------------------------------------------------- Public inputs
# Slot owners, from the receive and provide calls in internal/native/circuits at 3219e08.
SLOTS = [('Bridge commitments for preamble, $s\'$ and inner error; $w$, $y$, $z$', 3, 3, '`hashes_1`'),
         ('Bridge commitments for outer error, $ab$, query, $f$ and eval; $\\mu$, $\\mu\'$, $x$, $\\alpha$, $u$, `pre_beta`', 5, 6, '`hashes_2`'),
         ('$c$', 0, 1, '`collapse`'),
         ('$v$', 0, 1, '`compute_v`'),
         ('The nested challenge stage\'s partial commitment', 1, 0, 'The last `bind_challenges`'),
         ('$P_n$, $A_n$, $B_n$ and the nested registry restriction', 4, 0, '`bind_endoscalar`')]
SLOT_POINTS, SLOT_ELEMENTS = sum(r[1] for r in SLOTS), sum(r[2] for r in SLOTS)
UNIFIED_WIRES = 2 * SLOT_POINTS + SLOT_ELEMENTS
assert UNIFIED_WIRES == 37 and SLOT_POINTS == 13 and SLOT_ELEMENTS == 11
frag['slots'] = table(['Slots', 'Wires', 'Owner'], [(r[0], f'${2 * r[1] + r[2]}$', r[3]) for r in SLOTS]) + (
    f'\n\nThe rows add to ${SLOT_POINTS}$ points and ${SLOT_ELEMENTS}$ elements, which is the code\'s [${UNIFIED_WIRES}$ wires](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/unified.rs#L43).')

def horner(wires, y):
    out = 0
    for w in wires:
        out = (out * y + w) % Q
    return out


def k_at(wires, y):
    return (horner(wires, y) * y + 1) % Q


Y0 = one_run['y']
TOY_UNIFIED = [BRIDGE['preamble'][0], BRIDGE['preamble'][1], one_run['w'], one_run['y'], one_run['z']]
HEADER_LEFT, HEADER_RIGHT, HEADER_OUT = [8, 3], [12, 3], [20, 3]
pre = horner(TOY_UNIFIED, Y0)
k_unified = (((pre * Y0 + 0) % Q) * Y0 + 1) % Q
k_bridge_prefix = pre
for w in HEADER_LEFT + HEADER_RIGHT + [0]:
    k_bridge_prefix = (k_bridge_prefix * Y0 + w) % Q
k_bridge = (k_bridge_prefix * Y0 + 1) % Q
k_app = k_at(HEADER_LEFT + HEADER_RIGHT + HEADER_OUT, Y0)
assert k_unified == k_at(TOY_UNIFIED + [0], Y0)
assert k_bridge == k_at(TOY_UNIFIED + HEADER_LEFT + HEADER_RIGHT + [0], Y0)
assert len({k_unified, k_bridge, k_app}) == 3 and 0 not in (k_unified, k_bridge, k_app, pre)
frag['k-run'] = '\n'.join([
    f'Take a toy unified output of five wires, $({", ".join(map(str, TOY_UNIFIED))})$, which are the first bridge point and the challenges $w$, $y$ and $z$ from the run above. '
    f'Take child headers $({HEADER_LEFT[0]}, {HEADER_LEFT[1]})$ and $({HEADER_RIGHT[0]}, {HEADER_RIGHT[1]})$, whose second entry is the suffix, and the output header $({HEADER_OUT[0]}, {HEADER_OUT[1]})$. At $y = {Y0}$:', '',
    table(['Polynomial', 'Wires, in order', 'Value at $y$', 'Coefficient of $Y$'], [
        ('$k_{\\text{unified}}$', 'Unified output, $0$', f'${k_unified}$', '$0$'),
        ('$k_{\\text{bridge}}$', 'Unified output, left, right, $0$', f'${k_bridge}$', '$0$'),
        ('$k_{\\text{app}}$', 'Left, right, output', f'${k_app}$', f'${HEADER_OUT[1]}$'),
        ('Endoscaling step', '$0$', f'${k_at([0], Y0)}$', '$0$'),
    ]), '',
    f'Horner\'s rule reaches ${pre}$ after the five unified wires, and both $k_{{\\text{{unified}}}}$ and $k_{{\\text{{bridge}}}}$ continue from that value. Each table entry also matches a direct evaluation of the polynomial.'])

# Substitution: internal k = aY^3 + bY^2 + 0Y + 1, application k = dY^2 + sY + 1, by exhaustion.
same_with_zero_suffix = sum(1 for a in range(Q) for b in range(Q) for d in range(Q) if a == 0 and b == d)
same_with_nonzero = 0
worst = 0
for s_ in (3, 4, 5):
    for a in range(Q):
        for gap_bd in range(Q):
            hits = sum(1 for y in range(1, Q) if (a * y ** 3 + gap_bd * y * y - s_ * y) % Q == 0)
            worst = max(worst, hits)
            same_with_nonzero += hits == Q - 1
assert same_with_zero_suffix == Q and same_with_nonzero == 0 and worst == 2
frag['substitution'] = (
    f'Let an internal circuit expose wires $(a, b)$ and its zero suffix, so that $k_{{\\text{{int}}}}(Y) = aY^3 + bY^2 + 1$, and let an application circuit expose a header $(d, s)$, so that $k_{{\\text{{app}}}}(Y) = dY^2 + sY + 1$. '
    f'If an application could use the suffix $s = 0$, then ${same_with_zero_suffix}$ of the ${n(Q ** 3)}$ triples $(a, b, d)$ would make the two polynomials identical, and the swap would pass at every $y$. '
    f'For $s = 3, 4, 5$ the difference depends only on $a$ and $b - d$, so we tried all ${n(Q * Q)}$ pairs of those, and none makes the polynomials identical. The two values then agree at no more than ${worst}$ of the $42$ nonzero values of $y$, and on a real field the same count is a negligible fraction.')


# ---------------------------------------------------------------- The compression run
# Challenges picked by hand, as in earlier chapters; the search behind them asked only
# for distinct evaluation points and no degenerate point. In the code a transcript
# supplies them, and fresh w, y, z are drawn here, unrelated to the fuse's own.
X0, Y0F, Z0 = 9, 7, 5                    # the fuse's x, y, z, as in staging.md
U_FUSE = 9                               # the fuse's u; chapter 06's opening point
P_OLD = [7, 2, 5, 3] + [0] * (D - 4)     # chapter 06's polynomial stands in for the fuse's batch p
CH = dict(y=35, z=11, w=7, sigma=20, mu=19, nu=38, mu_p=2, nu_p=33, rho=41, r=18, alpha=17, u=38, beta=20,
          xi=29, z_ipa=12, us=[12, 17, 33, 41])
S_RAW = [11, 4, 19, 6, 2, 30, 8, 1, 16, 9, 25, 12, 3, 21, 7, 14]
ALPHA_Q = 27
GROUP = 3


def split_circuits(y):
    return SQUARE.s(y), CUBE.s(y)


def registry_poly(x, y):
    """m(W, x, y) for circuits at W = 1 and W = -1, the two-point toy domain."""
    v0 = ev(CUBE.s(y), x)
    v1 = ev(SQUARE.s(y), x)
    half = inv(2)
    return [(v0 + v1) * half % Q, (v0 - v1) * half % Q] + [0] * (D - 2), v0, v1


def old_accumulator():
    """The child's accumulator: the squaring claim at x = 5, with target 26, at the fuse's y and z."""
    circuit = square_circuit(26)
    r5 = plus(stage_a(5, 25, 8), square_final(5, 6))
    b5 = circuit.right(r5, Z0, Y0F)
    return r5, b5, revdot(r5, b5)


def compress(ch, targets=None, bad_wire=None):
    y, z, w, sigma = ch['y'], ch['z'], ch['w'], ch['sigma']
    mu, nu, mu_p, nu_p = ch['mu'], ch['nu'], ch['mu_p'], ch['nu_p']
    rho, r = ch['rho'], ch['r']
    run = {}

    # --- The instance
    rx_poly, m1, m2 = registry_poly(X0, Y0F)
    q_poly = poly(N, {('a', 0): ALPHA_Q, ('a', 1): m1, ('d', 1): m2})
    a_old, b_old, c_old = old_accumulator()
    points = dict(A=commit(A_POLY), R1=commit(F_SQ), R2=commit(F_CU), Q=commit(q_poly), Aold=commit(a_old),
                  Bold=commit(b_old), RX=commit(rx_poly), Pold=commit(P_OLD))
    v_old = ev(P_OLD, U_FUSE)
    a_u, b_u = ev(a_old, U_FUSE), ev(b_old, U_FUSE)
    run.update(points=points, c_old=c_old, v_old=v_old, a_u=a_u, b_u=b_u, m1=m1, m2=m2)

    # --- Phase 1: claims. a, b, target, and how the verifier sees each.
    s1, s2 = split_circuits(y)
    tz = SQUARE.t(z)
    r_sq = plus(A_POLY, F_SQ)
    r_cu = plus(A_POLY, F_CU)

    def dil(v):
        return [e * pow(z, i, Q) % Q for i, e in enumerate(v)]

    mask_a = mask(N, 1, 1, y)
    mask_f = mask(N, 2, 2, y)
    expected = [0] * D
    expected[pos('a', 1, N)] = (m1 if bad_wire is None else (m1 + bad_wire[0])) % Q
    expected[pos('d', 1, N)] = (m2 if bad_wire is None else (m2 + bad_wire[1])) % Q
    wire_mask = [0] * D
    wire_mask[D - 1 - pos('a', 1, N)] = 1
    wire_mask[D - 1 - pos('d', 1, N)] = sigma
    a_list = [a_old, r_sq, r_cu, lin((z, A_POLY), (1, q_poly)), lin((z, F_SQ), (1, F_CU)), lin((1, q_poly), (Q - 1, expected))]
    b_list = [b_old, plus(dil(r_sq), s1, tz), plus(dil(r_cu), s2, tz), mask_a, mask_f, wire_mask]
    k_sq, k_cu = (1 + 10 * y) % Q, (1 + 35 * y) % Q
    if targets:
        k_sq, k_cu = targets
    k_list = [c_old, k_sq, k_cu, 0, 0, 0]
    actual = [revdot(a, b) for a, b in zip(a_list, b_list)]
    run.update(a_list=a_list, b_list=b_list, k_list=k_list, actual=actual, wire_mask=wire_mask, expected=expected)

    # --- Phase 2: the fold, with groups of GROUP and the code's weights.
    m = len(a_list)
    groups = [list(range(g, min(g + GROUP, m))) for g in range(0, m, GROUP)]

    def weight_a(i):
        return pow(mu_p, i // GROUP, Q) * pow(mu, i % GROUP, Q) % Q

    def weight_b(i):
        return pow(nu_p, i // GROUP, Q) * pow(nu, i % GROUP, Q) % Q

    inner_terms, inner_weights = [], []
    for g, members in enumerate(groups):
        for i in members:
            for j in members:
                if i != j:
                    inner_terms.append(revdot(a_list[i], b_list[j]))
                    inner_weights.append(pow(mu_p * nu_p % Q, g, Q) * pow(mu, i % GROUP, Q) * pow(nu, j % GROUP, Q) % Q)
    e1 = inner_terms + [0] * (D - len(inner_terms))
    w1 = [0] * D
    for d, wt in enumerate(inner_weights):
        w1[D - 1 - d] = wt

    a_g = [lin(*[(pow(mu, i % GROUP, Q), a_list[i]) for i in mem]) for mem in groups]
    b_g = [lin(*[(pow(nu, i % GROUP, Q), b_list[i]) for i in mem]) for mem in groups]
    outer_terms, outer_weights = [], []
    for g in range(len(groups)):
        for h in range(len(groups)):
            if g != h:
                outer_terms.append(revdot(a_g[g], b_g[h]))
                outer_weights.append(pow(mu_p, g, Q) * pow(nu_p, h, Q) % Q)
    e2 = outer_terms + [0] * (D - len(outer_terms))
    w2 = [0] * D
    for d, wt in enumerate(outer_weights):
        w2[D - 1 - d] = wt

    A = lin(*[(weight_a(i), a_list[i]) for i in range(m)])
    B = lin(*[(weight_b(i), b_list[i]) for i in range(m)])
    eps1, eps2 = revdot(e1, w1), revdot(e2, w2)
    K_diag = sum(weight_a(i) * weight_b(i) * k_list[i] for i in range(m)) % Q
    K = (K_diag + eps1 + eps2) % Q
    run.update(e1=e1, e2=e2, w1=w1, w2=w2, eps1=eps1, eps2=eps2, K=K, K_diag=K_diag, A=A, B=B, inner=len(inner_terms), outer=len(outer_terms))
    run['fold_ok'] = revdot(A, B) == K

    # What the verifier derives from commitments.
    la = [weight_a(i) for i in range(m)]
    et = [weight_b(i) for i in range(m)]
    A_c = lin((la[0], a_old), (la[1], r_sq), (la[2], r_cu), (la[3], lin((z, A_POLY), (1, q_poly))),
              (la[4], lin((z, F_SQ), (1, F_CU))), (la[5], q_poly))
    T_ = lin((et[1], r_sq), (et[2], r_cu))
    B_c = scale(et[0], b_old)
    P_ = points
    A_c_pt = combine((la[0], P_['Aold']), (la[1], P_['A']), (la[1], P_['R1']), (la[2], P_['A']), (la[2], P_['R2']),
                     (la[3] * z, P_['A']), (la[3], P_['Q']), (la[4] * z, P_['R1']), (la[4], P_['R2']), (la[5], P_['Q']))
    T_pt = combine((et[1], P_['A']), (et[1], P_['R1']), (et[2], P_['A']), (et[2], P_['R2']))
    B_c_pt = mul(et[0], P_['Bold'])
    E1_pt, E2_pt = commit(e1), commit(e2)
    assert A_c_pt == commit(A_c) and T_pt == commit(T_) and B_c_pt == commit(B_c)

    # --- The split on the three claims, under rho.
    def product(a, b):
        out = [0] * (2 * D - 1)
        for i, u_ in enumerate(a):
            for j, v_ in enumerate(b):
                out[i + j] = (out[i + j] + u_ * v_) % Q
        return out

    t_poly = [(g0 + rho * g1 + rho * rho * g2) % Q for g0, g1, g2 in zip(product(A, B), product(e1, w1), product(e2, w2))]
    p_poly = [t_poly[D - 1 - i] for i in range(D)]
    q_split = t_poly[D:] + [0]
    assert len(p_poly) == D and len(q_split) == D
    target_p0 = (K + rho * eps1 + rho * rho * eps2) % Q
    run['p0'] = p_poly[0]
    run['target_p0'] = target_p0
    p_pt, q_pt = commit(p_poly), commit(q_split)

    # The verifier at r.
    ri = inv(r)
    o = dict(Ac=ev(A_c, r), T=ev(T_, r * z % Q), Bc=ev(B_c, r), E1=ev(e1, r), E2=ev(e2, r), p=ev(p_poly, ri), q=ev(q_split, r))
    pub_a = (-la[5] * ev(expected, r)) % Q
    s1r, s2r, tr = ev(s1, r), ev(s2, r), ev(tz, r)
    ma = mask_closed(N, 1, 1, r * y % Q)
    mf = mask_closed(N, 2, 2, r * y % Q)
    assert ma == ev(mask_a, r) and mf == ev(mask_f, r)
    mr = ev(wire_mask, r)
    pub_b = (et[1] * (s1r + tr) + et[2] * (s2r + tr) + et[3] * ma + et[4] * mf + et[5] * mr) % Q
    A_r = (o['Ac'] + pub_a) % Q
    B_r = (o['Bc'] + o['T'] + pub_b) % Q
    assert A_r == ev(A, r) and B_r == ev(B, r)
    W1r, W2r = ev(w1, r), ev(w2, r)
    lhs = (A_r * B_r + rho * o['E1'] * W1r + rho * rho * o['E2'] * W2r) % Q
    rhs = (pow(r, D - 1, Q) * o['p'] + pow(r, D, Q) * o['q']) % Q
    run.update(s1r=s1r, s2r=s2r, tr=tr, ma=ma, mf=mf, mr=mr, A_r=A_r, B_r=B_r, W1r=W1r, W2r=W2r, lhs=lhs, rhs=rhs, o=o,
               pub_a=pub_a, pub_b=pub_b, ri=ri, t_poly=t_poly)
    run['split_ok'] = lhs == rhs

    # --- Phase 3: the batch. Polynomial order: A_c, T, B_c, E1, E2, p, q, registry, then P, A, B.
    polys = [A_c, T_, B_c, e1, e2, p_poly, q_split, rx_poly, P_OLD, a_old, b_old]
    pts = [A_c_pt, T_pt, B_c_pt, E1_pt, E2_pt, p_pt, q_pt, P_['RX'], P_['Pold'], P_['Aold'], P_['Bold']]
    names = ['A_c', 'T', 'B_c', 'E_1', 'E_2', 'p', 'q', 'm(W, 9, 7)', 'P', 'A_{\\text{acc}}', 'B_{\\text{acc}}']
    m_w = ev(rx_poly, w)
    half = inv(2)
    assert m_w == ((1 + w) * m1 + (1 - w) * m2) * half % Q
    claims = [(0, r, o['Ac']), (1, r * z % Q, o['T']), (2, r, o['Bc']), (3, r, o['E1']), (4, r, o['E2']),
              (5, ri, o['p']), (6, r, o['q']), (5, 0, target_p0), (7, w, m_w), (8, U_FUSE, v_old), (9, U_FUSE, a_u), (10, U_FUSE, b_u)]
    run.update(polys=polys, pts=pts, names=names, claims=claims, m_w=m_w, p_pt=p_pt, q_pt=q_pt, E1_pt=E1_pt, E2_pt=E2_pt, A_c_pt=A_c_pt, T_pt=T_pt, B_c_pt=B_c_pt)
    return run


def batch(run, ch):
    alpha, u, beta = ch['alpha'], ch['u'], ch['beta']
    polys, claims, pts = run['polys'], run['claims'], run['pts']
    count = len(claims)
    f = [0] * D
    for j, (i, at, val) in enumerate(claims):
        shifted = list(polys[i])
        shifted[0] = (shifted[0] - val) % Q
        carry, quot = 0, [0] * D
        for d in range(D - 1, 0, -1):
            carry = (shifted[d] + carry * at) % Q
            quot[d - 1] = carry
        assert (shifted[0] + carry * at) % Q == 0, 'a claim is false'
        f = lin((1, f), (pow(alpha, count - 1 - j, Q), quot))
    F_pt = commit(f)
    zs = [ev(h, u) for h in polys]
    nn = len(polys)
    fu = 0
    for j, (i, at, val) in enumerate(claims):
        fu = (fu + pow(alpha, count - 1 - j, Q) * (zs[i] - val) * inv(u - at)) % Q
    assert fu == ev(f, u)
    v = (pow(beta, nn, Q) * fu + sum(pow(beta, nn - 1 - i, Q) * zs[i] for i in range(nn))) % Q
    H = lin((pow(beta, nn, Q), f), *[(pow(beta, nn - 1 - i, Q), polys[i]) for i in range(nn)])
    H_pt = combine((pow(beta, nn, Q), F_pt), *[(pow(beta, nn - 1 - i, Q), pts[i]) for i in range(nn)])
    assert H_pt == commit(H) and ev(H, u) == v
    return dict(f=f, F_pt=F_pt, zs=zs, fu=fu, v=v, H=H, H_pt=H_pt)


def ipa_cross(a, b, g, gen):
    h = len(a) // 2
    lv = sum(x * y for x, y in zip(a[h:], b[:h])) % Q
    rv = sum(x * y for x, y in zip(a[:h], b[h:])) % Q
    L = None
    R = None
    for k, pt_ in zip(a[h:], g[:h]):
        L = add(L, mul(k, pt_))
    for k, pt_ in zip(a[:h], g[h:]):
        R = add(R, mul(k, pt_))
    return add(L, mul(lv, gen)), add(R, mul(rv, gen))


def ipa(H, H_pt, at, v, ch):
    """prover.rs create_proof and verifier.rs verify_proof, with the challenges supplied."""
    xi, z_i, us = ch['xi'], ch['z_ipa'], ch['us']
    s_at = ev(S_RAW, at)
    spoly = [(S_RAW[0] - s_at) % Q] + S_RAW[1:]
    assert ev(spoly, at) == 0
    S_pt = commit(spoly)
    pp = [(s_ * xi + c) % Q for s_, c in zip(spoly, H)]
    assert ev(pp, at) == v
    pp[0] = (pp[0] - v) % Q
    bb = [pow(at, i, Q) for i in range(D)]
    gg = list(GENS)
    gen = mul(z_i, U)
    rounds = []
    for u_ in us:
        L, R = ipa_cross(pp, bb, gg, gen)
        rounds.append((L, R))
        h = len(pp) // 2
        ui = inv(u_)
        pp, bb, gg = ([(pp[i] + ui * pp[i + h]) % Q for i in range(h)], [(bb[i] + u_ * bb[i + h]) % Q for i in range(h)],
                      [add(gg[i], mul(u_, gg[i + h])) for i in range(h)])
    c = pp[0]
    # The verifier.
    start = combine((1, H_pt), (Q - v, GENS[0]), (xi, S_pt))
    point = start
    for u_, (L, R) in zip(us, rounds):
        point = add(add(point, mul(inv(u_), L)), mul(u_, R))
    tmp, cur = 1, at
    for u_ in reversed(us):
        tmp = tmp * (1 + u_ * cur) % Q
        cur = cur * cur % Q
    b_hat = tmp
    coeffs = [0] * D
    coeffs[0] = 1
    length = 1
    for u_ in reversed(us):
        for i in range(length):
            coeffs[length + i] = coeffs[i] * u_ % Q
        length *= 2
    G_hat = None
    for k, pt_ in zip(coeffs, GENS):
        G_hat = add(G_hat, mul(k, pt_))
    assert G_hat == gg[0] and b_hat == bb[0]
    right = add(mul(c, G_hat), mul(c * b_hat * z_i % Q, U))
    return dict(S_pt=S_pt, rounds=rounds, c=c, start=start, end=point, right=right, b_hat=b_hat, G_hat=G_hat, coeffs=coeffs, ok=point == right)


def clean(ch):
    """True for a run with distinct evaluation points and no degenerate point or value."""
    run = compress(ch)
    assert run['fold_ok'] and run['split_ok'] and run['p0'] == run['target_p0']
    b_ = batch(run, ch)
    i_ = ipa(b_['H'], b_['H_pt'], ch['u'], b_['v'], ch)
    assert i_['ok']
    r, z = ch['r'], ch['z']
    at = [r, r * z % Q, inv(r), 0, ch['w'], U_FUSE]
    if len(set(at)) != 6 or ch['u'] in at or z == 1:
        return False
    named = list(run['points'].values()) + list(run['pts']) + [b_['F_pt'], b_['H_pt'], i_['S_pt'], i_['start']]
    if set(named) & SPECIAL:
        return False
    if None in [i_['G_hat'], i_['end'], i_['right']] + [p_ for pair in i_['rounds'] for p_ in pair]:
        return False
    if i_['b_hat'] == 0 or U in [p_ for pair in i_['rounds'] for p_ in pair]:
        return False
    values = list(run['o'].values()) + b_['zs'] + [b_['v'], b_['fu'], i_['c'], run['eps1'], run['eps2'], run['K'], run['p0'], run['m_w']]
    return 0 not in values


if __name__ == '__main__':
    assert clean(CH)
    run = compress(CH)
    bat = batch(run, CH)
    arg = ipa(bat['H'], bat['H_pt'], CH['u'], bat['v'], CH)
    pp = run['points']
    r_, z_ = CH['r'], CH['z']

    frag['instance'] = '\n'.join([
        table(['Instance entry', 'Toy value', 'Role'], [
            ('$\\bar{A}$, $\\bar{Q}$', f'{pt(pp["A"])}, {pt(pp["Q"])}', 'Two stages. $\\bar{Q}$ holds the values read from the registry'),
            ("$\\bar{R}'_1$, $\\bar{R}'_2$", f'{pt(pp["R1"])}, {pt(pp["R2"])}', 'Final traces of the squaring and cubing circuits'),
            ('$\\bar{A}_{\\text{acc}}$, $\\bar{B}_{\\text{acc}}$', f'{pt(pp["Aold"])}, {pt(pp["Bold"])}', 'The accumulator pair'),
            ('$c$', f'${run["c_old"]}$', 'Its stored revdot value'),
            ('$\\bar{M}$', pt(pp['RX']), f'The restriction $m(W, {X0}, {Y0F})$'),
            ('$\\bar{P}$, $v$', f'{pt(pp["Pold"])}, ${run["v_old"]}$', f'The batch claim at the fuse\'s $u = {U_FUSE}$'),
            ('$A(u)$, $B(u)$', f'${run["a_u"]}$, ${run["b_u"]}$', 'The accumulator pair at that $u$'),
        ])])

    claim_names = ['Accumulator', 'Squaring circuit', 'Cubing circuit', 'Stage mask', 'Final mask', 'Wire binding']
    kinds = ['Raw', 'Circuit', 'Circuit', 'Bonding', 'Bonding', 'Masked']
    a_desc = ['$A_{\\text{acc}}$', "$a + r'_1$", "$a + r'_2$", '$z\\,a + q$', "$z\\,r'_1 + r'_2$", '$q - E_\\sigma$']
    b_desc = ['$B_{\\text{acc}}$', "$r_1(zX) + s_1(X, y) + t(X, z)$", "$r_2(zX) + s_2(X, y) + t(X, z)$", 'Mask of gate 1', 'Mask of gates 2, 3', '$M_\\sigma$']
    frag['claims'] = table(['Slot', 'Claim', 'Kind', 'Left vector', 'Right vector', 'Target $k_i$'],
                           [(i, claim_names[i], kinds[i], a_desc[i], b_desc[i], f'${run["k_list"][i]}$') for i in range(6)])
    assert run['actual'] == run['k_list']
    m1, m2 = run['m1'], run['m2']
    frag['binding'] = (
        f'The registry here has two circuits at $W = 1$ and $W = -1$, whose wiring gives $m(1, {X0}, {Y0F}) = {m1}$ and $m(-1, {X0}, {Y0F}) = {m2}$. The stage $q(X)$ claims those values in the wires $a_1$ and $d_1$. '
        f'With $\\sigma = {CH["sigma"]}$, the mask $M_\\sigma$ has a $1$ opposite $a_1$ and a ${CH["sigma"]}$ opposite $d_1$, and $E_\\sigma$ holds the expected values at those two degrees. So the product is $(a_1 - {m1}) + {CH["sigma"]}(d_1 - {m2}) = 0$. '
        f'If the stage holds a wrong $a_1$, the product is nonzero at all 43 values of $\\sigma$. If both wires are wrong, the two errors cancel at one value of $\\sigma$ out of 43.')
    # The false wire claim, on the real vectors, at every sigma.
    wrong_one, wrong_two = [], []
    q_vec = run['a_list'][5]
    for sg in range(Q):
        for label_, bad_w, sink in (('one', (5, 0), wrong_one), ('two', (5, 9), wrong_two)):
            exp = [0] * D
            exp[pos('a', 1, N)] = (m1 + bad_w[0]) % Q
            exp[pos('d', 1, N)] = (m2 + bad_w[1]) % Q
            real_q = lin((1, q_vec), (1, run['expected']))
            mk = [0] * D
            mk[D - 1 - pos('a', 1, N)] = 1
            mk[D - 1 - pos('d', 1, N)] = sg
            sink.append(revdot(lin((1, real_q), (Q - 1, exp)), mk))
    assert wrong_one.count(0) == 0 and wrong_two.count(0) == 1

    frag['fold-run'] = '\n'.join([
        f'With $\\mu = {CH["mu"]}$, $\\nu = {CH["nu"]}$, $\\mu\' = {CH["mu_p"]}$ and $\\nu\' = {CH["nu_p"]}$:', '',
        table(['Value', 'Toy result'], [
            ('First-layer terms, group by group', f'${vec(run["e1"][:run["inner"]])}$'),
            ('$\\bar{E}_1$, committed before $\\mu$ and $\\nu$', pt(run['E1_pt'])),
            ('Second-layer terms', f'${vec(run["e2"][:run["outer"]])}$'),
            ('$\\bar{E}_2$, committed before $\\mu\'$ and $\\nu\'$', pt(run['E2_pt'])),
            ('$\\varepsilon_1 = \\revdot{\\v{E}_1}{\\v{W}_1}$', f'${run["eps1"]}$'),
            ('$\\varepsilon_2 = \\revdot{\\v{E}_2}{\\v{W}_2}$', f'${run["eps2"]}$'),
            ('$\\sum_i \\lambda_i \\eta_i k_i$', f'${run["K_diag"]}$'),
            ('$K$, the target of $(A, B)$', f'${run["K"]}$'),
            ('$\\revdot{\\v{A}}{\\v{B}}$, for comparison', f'${revdot(run["A"], run["B"])}$'),
        ])])
    frag['derived'] = (
        f'The verifier obtains $\\bar{{A}}_c = {show(run["A_c_pt"])}$, $\\bar{{T}} = {show(run["T_pt"])}$ and $\\bar{{B}}_c = {show(run["B_c_pt"])}$ from small MSMs over the instance\'s points. Committing to the three polynomials directly gives the same points.')

    o = run['o']
    frag['split-run'] = '\n'.join([
        f'At $\\rho = {CH["rho"]}$ the prover commits to $\\bar{{p}} = {show(run["p_pt"])}$ and $\\bar{{q}} = {show(run["q_pt"])}$, and the required value is $p(0) = K + \\rho\\,\\varepsilon_1 + \\rho^2\\varepsilon_2 = {run["target_p0"]}$. '
        f'At $r = {r_}$, so that $rz = {r_ * z_ % Q}$ and $1/r = {run["ri"]}$, it sends seven values:', '',
        table(['$A_c(r)$', '$T(rz)$', '$B_c(r)$', '$E_1(r)$', '$E_2(r)$', '$p(1/r)$', '$q(r)$'],
              [tuple(f'${o[k]}$' for k in ['Ac', 'T', 'Bc', 'E1', 'E2', 'p', 'q'])]), '',
        f'The verifier adds what it can compute alone. It needs $s_1(r, y) = {run["s1r"]}$, $s_2(r, y) = {run["s2r"]}$ and $t(r, z) = {run["tr"]}$, the masks at $r$, which are ${run["ma"]}$, ${run["mf"]}$ and ${run["mr"]}$, and the two public vectors, $W_1(r) = {run["W1r"]}$ and $W_2(r) = {run["W2r"]}$. '
        f'That gives $A(r) = {o["Ac"]} + {run["pub_a"]} = {run["A_r"]}$ and $B(r) = {o["Bc"]} + {o["T"]} + {run["pub_b"]} = {run["B_r"]}$, modulo 43. '
        f'The left side of the split is $A(r)B(r) + \\rho\\,E_1(r)W_1(r) + \\rho^2 E_2(r)W_2(r) = {run["lhs"]}$, and the right side is $r^{{15}}p(1/r) + r^{{16}}q(r) = {run["rhs"]}$.'])

    rows = []
    for j, (i, at, val) in enumerate(run['claims']):
        rows.append((j, f'${run["names"][i]}$', pt(run['pts'][i]), f'${at}$', f'${val}$'))
    frag['claims-list'] = table(['Claim $j$', 'Polynomial', 'Commitment', 'Point $x_j$', 'Value $y_j$'], rows)
    frag['registry-value'] = (
        f'Claim 8 opens $m(W, {X0}, {Y0F})$ at the fresh point $w = {CH["w"]}$. The verifier computes the value ${run["m_w"]}$ for itself, by evaluating the wiring of both circuits and combining the results with Lagrange weights, and this is the step that reads the whole registry.')
    frag['batch-run'] = (
        f'With $\\alpha = {CH["alpha"]}$ the quotient commits to $\\bar{{F}} = {show(bat["F_pt"])}$. At $u = {CH["u"]}$ the prover sends the eleven values ${vec(bat["zs"])}$. '
        f'The verifier derives $f(u) = {bat["fu"]}$ from those values and the claims. With $\\beta = {CH["beta"]}$ this gives $\\bar{{H}} = {show(bat["H_pt"])}$ and $v = {bat["v"]}$, and the prover\'s polynomial $H$ agrees on both.')
    rows = [(j + 1, CH['us'][j], pt(l_), pt(r2)) for j, (l_, r2) in enumerate(arg['rounds'])]
    frag['ipa-run'] = '\n'.join([
        f'The argument commits to the masking polynomial, $\\bar{{S}} = {show(arg["S_pt"])}$, and takes $\\xi = {CH["xi"]}$ and a multiplier $z = {CH["z_ipa"]}$ on $U$. The statement becomes $\\bar{{H}} - v \\cdot G_0 + \\xi \\cdot \\bar{{S}} = {show(arg["start"])}$. Then come $\\log_2 16 = 4$ rounds:', '',
        table(['Round', 'Challenge', '$L_j$', '$R_j$'], rows), '',
        f'The final scalar is $\\hat{{a}} = {arg["c"]}$. The verifier computes $\\hat{{G}} = {show(arg["G_hat"])}$ from an MSM over all sixteen generators and $\\hat{{b}} = {arg["b_hat"]}$ from a product of four factors. The folded statement is ${show(arg["end"])}$, and $\\hat{{a}} \\cdot (\\hat{{G}} + \\hat{{b}} z \\cdot U) = {show(arg["right"])}$, so the verifier accepts.'])

    # --- Cheating on the fold: a false target.
    bad = compress(CH, targets=((1 + 11 * CH['y']) % Q, run['k_list'][2]))
    assert not bad['fold_ok']
    gap_ = (revdot(bad['A'], bad['B']) - bad['K']) % Q
    assert gap_ != 0
    # After mu, nu the prover knows the gap and could shift eps1 to cover it, but then (E1, W1, eps1) is false.
    rho_passes_each = []
    for shift in range(1, Q):
        passes = 0
        for rho in range(Q):
            K2 = (bad['K'] + shift) % Q
            total = (revdot(bad['A'], bad['B']) + rho * bad['eps1'] + rho * rho * bad['eps2']) % Q
            want = (K2 + rho * (bad['eps1'] + shift) + rho * rho * bad['eps2']) % Q
            passes += total == want
        rho_passes_each.append(passes)
    assert set(rho_passes_each) == {1}
    # Exhaustive over (mu, nu) for a prover that lowers the term e_{0,1}, of weight nu, by e before the challenges.
    k_gap = (bad['k_list'][1] - run['k_list'][1]) % Q
    assert k_gap == CH['y']
    counts = set()
    for extra in range(1, Q):
        counts.add(sum(1 for mu in range(1, Q) for nu in range(1, Q) if (k_gap * mu * nu - extra * nu) % Q == 0))
    assert counts == {42}
    EXTRA_E = 5
    mu_star = EXTRA_E * inv(k_gap) % Q
    hit = compress(dict(CH, mu=mu_star), targets=((1 + 11 * CH['y']) % Q, run['k_list'][2]))
    assert (hit['K'] - EXTRA_E * CH['nu']) % Q == revdot(hit['A'], hit['B'])
    frag['cheat-target'] = (
        f'Suppose the prover claims the output $11$ for the squaring circuit in place of $10$, so its target rises by $y = {CH["y"]}$ while its vectors stay honest. At our challenges the folded pair then misses $K$ by ${gap_}$. '
        f'Before the challenges, it can lower the term $e_{{0,1}}$, whose weight is $\\nu$, by some amount $e$. The false target adds ${k_gap}\\mu\\nu$ to $K$ and the lowered term removes $e\\nu$, so the fold balances only if $\\mu = e / {k_gap}$. '
        f'For $e = {EXTRA_E}$ that means $\\mu = {mu_star}$, and we confirmed the balance there on the full vectors. Over all ${n(42 * 42)}$ nonzero pairs $(\\mu, \\nu)$, every nonzero $e$ balances exactly ${counts.pop()}$ pairs, which is one value of $\\mu$ out of 42.')
    frag['cheat-epsilon'] = (
        f'After seeing $\\mu$ and $\\nu$, the prover could raise $\\varepsilon_1$ alone and leave $\\v{{E}}_1$ as committed. That can make $(A, B)$ balance, but it makes the claim $(E_1, W_1, \\varepsilon_1)$ false by the same amount, and $\\rho$ arrives only after $\\varepsilon_1$ is fixed. '
        f'We tried all $42$ nonzero shifts against all $43$ values of $\\rho$, and each shift passes at exactly ${rho_passes_each[0]}$ value of $\\rho$.')

    # --- Cheating on the split: p(0) forged, the other coefficients chosen to create roots.
    delta = 7
    roots = [v for v in range(1, Q)][:2 * D - 2]
    diff = [1]
    for rt in roots:
        nxt = [0] * (len(diff) + 1)
        for i, c in enumerate(diff):
            nxt[i + 1] = (nxt[i + 1] + c) % Q
            nxt[i] = (nxt[i] - rt * c) % Q
        diff = nxt
    assert len(diff) == 2 * D - 1 and diff[D - 1] != 0
    factor = delta * inv(diff[D - 1]) % Q
    diff = [c * factor % Q for c in diff]
    assert diff[D - 1] == delta
    fake_t = [(a + b) % Q for a, b in zip(run['t_poly'], diff)]
    fake_p = [fake_t[D - 1 - i] for i in range(D)]
    fake_q = fake_t[D:] + [0]
    assert fake_p[0] == (run['p0'] + delta) % Q
    r_pass = 0
    for rr in range(1, Q):
        left = (ev(run['t_poly'], rr)) % Q
        right = (pow(rr, D - 1, Q) * ev(fake_p, inv(rr)) + pow(rr, D, Q) * ev(fake_q, rr)) % Q
        r_pass += left == right
    assert r_pass == 2 * D - 2
    frag['cheat-split'] = (
        f'Suppose the prover wants $p(0)$ to be too large by ${delta}$. The coefficient of $X^{{15}}$ in $X^{{15}}p(1/X) + X^{{16}}q(X)$ is exactly $p(0)$, so whatever else it does, the difference from the true product is a nonzero polynomial of degree at most $30$. '
        f'The prover can choose the other coefficients of $p$ and $q$ to give that difference as many roots as possible, and we built such a pair. It passes the split at ${r_pass}$ of the $42$ nonzero values of $r$. '
        f'This is the toy field\'s small size at work, since the same count on the real parameters is $2^{{14}} - 2$ roots out of about $2^{{254}}$ values.')

    # --- The real claim lists, from native/claims.rs, nested/claims.rs and compress/instance.rs.
    native_single = 1 + 1 + NATIVE_CIRCUITS + NATIVE_MASKS + 5
    nested_single = 1 + NESTED_CIRCUITS + NESTED_BONDINGS + 3
    def layout(m, g=7):
        groups = -(-m // g)
        sizes = [g] * (m // g) + ([m % g] if m % g else [])
        return groups, sum(k * (k - 1) for k in sizes), groups * (groups - 1)
    ng, ni, no = layout(native_single)
    mg, mi, mo = layout(nested_single)
    assert native_single == 56 and nested_single == 46 and ni + no < 2 ** 13
    frag['real-claims'] = (
        f'A real compressed proof has ${native_single}$ native claims, namely one accumulator pair, one application circuit, ${NATIVE_CIRCUITS}$ internal circuits, ${NATIVE_MASKS}$ masks and $5$ wire bindings, and it has ${nested_single}$ nested claims. '
        f'In groups of $7$, the native side has ${ng}$ groups, ${ni}$ first-layer terms and ${no}$ second-layer terms, and the nested side has ${mg}$ groups, ${mi}$ first-layer terms and ${mo}$ second-layer terms.')
    frag['verifier-cost'] = table(['Verifier step, per curve', 'Work', 'Growth'], [
        ('Replay the fuse transcript', f'${3 + 5}$ permutations, on the native field only', 'Constant'),
        ('Recompute two nested stages', 'Two small commitments, on the nested curve only', 'Constant'),
        ('Compute targets $k(y)$', 'One Horner step per public wire', 'Size of the instance'),
        ('Derive $\\bar{A}_c$, $\\bar{T}$, $\\bar{B}_c$, $\\bar{H}$', 'MSMs over the instance\'s points', 'Size of the instance'),
        ('Compute $s_i(r, y)$ for each circuit claim', f'${NATIVE_CIRCUITS + 1}$ native and ${NESTED_CIRCUITS}$ nested circuits, one term per wiring coefficient', '**Linear in the circuits**'),
        ('Compute registry values for the wire bindings', f'One pass over the domain at $(x, y)$, and natively ${7 + 4}$ further evaluations of $m$', '**Linear in the registry**'),
        ('Compute $m(w, x, y)$', 'One pass over the registry, with Lagrange weights', '**Linear in the registry**'),
        ('Compute masks and $t(r, z)$', 'Closed forms', 'Logarithmic'),
        ('Compute $\\hat{b}$ and combine the $L_j$, $R_j$', f'${2 * 13}$ scalar multiplications and $13$ factors', 'Logarithmic'),
        ('Compute $\\hat{G}$', f'1 MSM of ${n(2 ** 13)}$ scalar multiplications', '**Linear in the vector length**'),
    ])

    # --- Sizes, from the codec.
    H_SIZE = 4
    native_components, nested_components = 2 + NATIVE_RX, 2 + NESTED_RX
    inst_points = native_components + 2 + nested_components + 3
    inst_scalars = 5 + 6 + 2 + 4 + 2 + 2 * H_SIZE
    rank = 13
    reduction_p, reduction_s = 4, 9
    batch_p, batch_s = 1, 5 + 2 + 4
    ipa_p, ipa_s = 1 + 2 * rank, 1
    side_p, side_s = reduction_p + batch_p + ipa_p, reduction_s + batch_s + ipa_s
    total_p = inst_points + 2 * side_p
    total_s = inst_scalars + 2 * side_s
    ENVELOPE, CIRCUIT_ID = 28, 4
    compressed = 32 * (total_p + total_s) + CIRCUIT_ID + ENVELOPE
    uncompressed_polys = NUM_POLYS * 2 ** rank * 32
    assert compressed < 10 ** 4 and uncompressed_polys > 2 * 10 ** 7
    assert inst_points == 93 and side_p == 32 and side_s == 21
    frag['sizes'] = table(['Part', 'Points', 'Scalars'], [
        ('Instance, commitments and values', f'${inst_points}$', f'${inst_scalars - 2 * H_SIZE}$'),
        (f'Instance, two child headers of ${H_SIZE}$ elements', '$0$', f'${2 * H_SIZE}$'),
        ('Revdot reduction, per curve', f'${reduction_p}$', f'${reduction_s}$'),
        ('Batch, per curve', f'${batch_p}$', f'${batch_s}$'),
        ('IPA, per curve', f'${ipa_p}$', f'${ipa_s}$'),
        ('Total, with two curves', f'${total_p}$', f'${total_s}$'),
    ])
    frag['size-total'] = (
        f'At 32 bytes per point or scalar, with [4 bytes for the circuit index](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/registry.rs#L7-L20) and the [28-byte envelope](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/format.rs#L41), that comes to ${n(compressed)}$ bytes. '
        f'The [uncompressed encoding](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/polynomial.rs#L1-L10) writes ${n(2 ** rank)}$ coefficients for each of ${NUM_POLYS}$ polynomials, which is ${n(uncompressed_polys)}$ bytes before counting its cached points, so compression shrinks the proof by a factor of about ${uncompressed_polys // compressed:,}$. '
        f'Most of the compressed proof is the instance, with ${inst_points}$ of its ${total_p}$ points. The IPA rounds, the only part that grows with the circuit size, take ${2 * 2 * rank}$ points.')

    frag['header-extra'] = (
        f'A header larger than ${H_SIZE}$ elements adds ${2 * 32}$ bytes per extra element, since the proof holds the two child headers. The output header does not count, because [the verifier supplies it](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/verifier.rs#L83) as the statement.')
    frag['recap-size'] = (
        f'9. By our count a compressed proof takes ${n(compressed)}$ bytes, against more than ${n(uncompressed_polys)}$ uncompressed. Rerandomization and hiding are not yet established, and the comparison with Orchard remains an estimate.')

    def orchard(actions):
        return 2720 + 2272 * actions

    assert orchard(2) == 7264
    frag['orchard-size'] = (
        f'[ZIP 225](https://zips.z.cash/zip-0225) gives an Orchard proof $2720 + 2272 \\cdot n$ bytes for $n$ actions, which is ${n(orchard(2))}$ bytes at $n = 2$ and ${n(orchard(10))}$ bytes at $n = 10$. '
        f'So by our count a compressed Ragu proof with headers of ${H_SIZE}$ elements is about the size of an Orchard proof for two actions, and one Ragu proof can stand for many transactions. The exact match at $n = 2$ is a coincidence of these parameters.')

    # --- The book's break-even.
    def solve(cost_ms, log_fn):
        target = 100.0
        lo, hi = 2.0, 10000.0
        # N cost / log N is increasing above e; search above the minimum.
        lo = 3.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if mid * cost_ms / log_fn(mid) < target:
                lo = mid
            else:
                hi = mid
        return lo

    be = {(c, nm): solve(c, f) for c in (10, 15) for nm, f in (('ln', log), ('log2', log2))}
    assert 30 < be[(10, 'ln')] < 40 and 55 < be[(10, 'log2')] < 65
    frag['break-even'] = table(['Cost per proof in the model', '$\\log = \\ln$', '$\\log = \\log_2$'], [
        (f'${c}$ ms', f'$N_{{\\text{{tx}}}} \\approx {be[(c, "ln")]:.0f}$', f'$N_{{\\text{{tx}}}} \\approx {be[(c, "log2")]:.0f}$') for c in (10, 15)])

    # --- Rerandomization: a deterministic fold links output to input.
    seed_pt = commit(lin((1, A_POLY), (1, F_CU)))
    l0, l1 = 16, 22
    input_pt = commit(lin((1, A_POLY), (1, F_SQ)))
    out_pt = combine((l0, input_pt), (l1, seed_pt))
    pool = curve_points()
    matches = [cand for cand in pool if combine((l0, cand), (l1, seed_pt)) == out_pt]
    assert matches == [input_pt] and len(pool) == 42 and out_pt not in SPECIAL
    frag['rerandomize'] = (
        f'Reduce the fold to one commitment and let the output be $\\bar{{A}}_{{\\text{{out}}}} = \\lambda_0 \\bar{{A}}_{{\\text{{in}}}} + \\lambda_1 \\bar{{A}}_{{\\text{{seed}}}}$, with the public weights $\\lambda_0 = {l0}$ and $\\lambda_1 = {l1}$ and the cached seeded point ${show(seed_pt)}$. '
        f'An input of ${show(input_pt)}$ gives the output ${show(out_pt)}$. An observer who wonders which proof went in can test each candidate against that equation. We tried all $42$ points as candidates, and only the true input matches.')

    # --- The stage and one opening: what a single alpha can hide.
    honest = stage_a()
    ALPHA = honest[pos('a', 0, N)]
    OPEN = 17
    value = ev(honest, OPEN)
    A_pt = commit(honest)
    by_commit, by_both = 0, []
    for x_ in range(Q):
        for al in range(Q):
            trial = stage_a(x_, x_ * x_ % Q, al)
            if commit(trial) == A_pt:
                by_commit += 1
                if ev(trial, OPEN) == value:
                    by_both.append((x_, al))
    assert (3, ALPHA) in by_both and len(by_both) == 2
    other = next(pair for pair in by_both if pair != (3, ALPHA))
    frag['leak'] = (
        f'Take the stage $a(X)$ from [chapter 17](./staging.md), where $v = x^2$ and one random entry $\\alpha$ sits at $a_0$. Among all ${n(Q * Q)}$ pairs $(x, \\alpha)$, the commitment ${show(A_pt)}$ matches ${by_commit}$. '
        f'Adding one value at a point, $a({OPEN}) = {value}$, leaves ${len(by_both)}$ pairs, the true $(3, {ALPHA})$ and also ${other}$, because the commitment and the value together give a quadratic equation in $x$. On a real curve nobody can list the commitment\'s matches, but the value still gives one linear equation in the secret wires, which is the sense in which the proof does not hide them.')

    print(json.dumps(frag))
