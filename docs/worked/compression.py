"""Worked examples for compression.md. Prints fragments as JSON.

The compression run mirrors crates/ragu_pcd/src/compress/ at Ragu commit 3219e08,
on the small circuits of staging.py, with groups of 3 in place of the code's 7.
Counts of real proofs are read from the codec in crates/ragu_pcd/src/wire/compressed.rs
and the standard Shape pinned in crates/ragu_pcd/src/profile.rs. The helpers and
the counts of the standard profile come from ragu_recursion.py, the chapter before.
"""
import contextlib
import io
import json
from math import log, log2

with contextlib.redirect_stdout(io.StringIO()):
    from staging import (A_POLY, CUBE, F_CU, F_SQ, GENS, N, Q, SQUARE, U, add, commit, ev, mask, mask_closed,
                         curve_points, mul, plus, poly, pos, revdot, scale, show, square_circuit, square_final, stage_a,
                         table, vec)
    from ragu_recursion import (D, NATIVE_CIRCUITS, NATIVE_MASKS, NATIVE_RX, NESTED_BONDINGS, NESTED_CIRCUITS,
                                NESTED_RX, NUM_POLYS, SPECIAL, combine, inv, lin, n, one_run, pt)

frag = {}

# ---------------------------------------------------------------- The compression run
# Challenges picked by hand, as in earlier chapters; the search behind them asked only
# for distinct evaluation points and no degenerate point. In the code a transcript
# supplies them, and fresh w, y, z are drawn here, unrelated to the fuse's own.
X0, Y0F, Z0 = 9, 7, 5                    # the fuse's x, y, z, as in staging.md
U_FUSE = 9                               # the fuse's u; chapter 06's opening point
P_OLD = [7, 2, 5, 3] + [0] * (D - 4)     # chapter 06's polynomial stands in for the fuse's batch p
CH = dict(y=35, z=11, w=3, sigma=20, mu=19, nu=38, mu_p=2, nu_p=33, rho=41, r=18, alpha=17, u=38, beta=20,
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

    inner_terms, inner_weights, inner_pairs = [], [], []
    for g, members in enumerate(groups):
        for i in members:
            for j in members:
                if i != j:
                    inner_pairs.append((i, j))
                    inner_terms.append(revdot(a_list[i], b_list[j]))
                    inner_weights.append(pow(mu_p * nu_p % Q, g, Q) * pow(mu, i % GROUP, Q) * pow(nu, j % GROUP, Q) % Q)
    e1 = inner_terms + [0] * (D - len(inner_terms))
    w1 = [0] * D
    for d, wt in enumerate(inner_weights):
        w1[D - 1 - d] = wt

    a_g = [lin(*[(pow(mu, i % GROUP, Q), a_list[i]) for i in mem]) for mem in groups]
    b_g = [lin(*[(pow(nu, i % GROUP, Q), b_list[i]) for i in mem]) for mem in groups]
    outer_terms, outer_weights, outer_pairs = [], [], []
    for g in range(len(groups)):
        for h in range(len(groups)):
            if g != h:
                outer_pairs.append((g, h))
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
    run.update(inner_pairs=inner_pairs, inner_weights=inner_weights, outer_pairs=outer_pairs, outer_weights=outer_weights,
               e1=e1, e2=e2, w1=w1, w2=w2, eps1=eps1, eps2=eps2, K=K, K_diag=K_diag, A=A, B=B, inner=len(inner_terms), outer=len(outer_terms))
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
               pub_a=pub_a, pub_b=pub_b, ri=ri, t_poly=t_poly, la=la, et=et, Er=ev(expected, r))
    run['split_ok'] = lhs == rhs

    # --- Phase 3: the batch. Polynomial order: A_c, T, B_c, E1, E2, p, q, registry, then P, A, B.
    polys = [A_c, T_, B_c, e1, e2, p_poly, q_split, rx_poly, P_OLD, a_old, b_old]
    pts = [A_c_pt, T_pt, B_c_pt, E1_pt, E2_pt, p_pt, q_pt, P_['RX'], P_['Pold'], P_['Aold'], P_['Bold']]
    names = ['A_c', 'T', 'B_c', 'E_1', 'E_2', '\\Pi_{\\text{lo}}', '\\Pi_{\\text{hi}}', 'm(W, x_f, y_f)', 'P_f', 'A_{\\text{acc}}', 'B_{\\text{acc}}']
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

    y_c, z_c, w_c = CH['y'], CH['z'], CH['w']
    assert X0 == U_FUSE and len({w_c, X0, Y0F, Z0}) == 4
    frag['challenges'] = '\n'.join([
        table(['Values', 'Source', 'Used for'], [
            (f'$x_f = {X0}$, $y_f = {Y0F}$', 'Left by the last fuse', 'The restriction $m(W, x_f, y_f)$'),
            (f'$z_f = {Z0}$', 'Left by the last fuse', 'How the fuse built the accumulator pair. Compression evaluates nothing at it'),
            (f'$u_f = {U_FUSE}$', 'Left by the last fuse', 'The batch claim $(P_f, u_f, v_f)$'),
            (f'$y = {y_c}$, $z = {z_c}$', 'Fresh in compression', "The circuit claims' wiring $s_i(X, y)$ and $t(X, z)$, and the weight that puts two stages under one mask"),
            (f'$\\sigma = {CH["sigma"]}$', 'Fresh in compression', 'The wire binding of Section 3'),
            (f'$w = {w_c}$', 'Fresh in compression', 'The point at which the verifier opens the restriction, in Section 6'),
        ]), '',
        f'The fuse values here are not the output of the [transcript run of the last chapter](./ragu-recursion.md#_4-splitting-the-transcript), which would give $x_f = {one_run["x"]}$, $y_f = {one_run["y"]}$ and $u_f = {one_run["u"]}$. '
        f'We built the instance from the two circuits of the staging chapter so that every vector stays short, and we chose the fuse values to suit it. Two of them coincide by chance, since $x_f = u_f = {X0}$.'])

    frag['instance'] = '\n'.join([
        table(['Instance entry', 'Toy value', 'Role'], [
            ('$\\bar{A}$, $\\bar{Q}$', f'{pt(pp["A"])}, {pt(pp["Q"])}', 'Two stages. $a$ is the stage of the staging chapter, and $q$ holds the values read from the registry'),
            ("$\\bar{R}'_1$, $\\bar{R}'_2$", f'{pt(pp["R1"])}, {pt(pp["R2"])}', 'Final traces of the squaring and cubing circuits'),
            ('$\\bar{A}_{\\text{acc}}$, $\\bar{B}_{\\text{acc}}$', f'{pt(pp["Aold"])}, {pt(pp["Bold"])}', 'The accumulator pair'),
            ('$c_{\\text{acc}}$', f'${run["c_old"]}$', "The pair's stored revdot value"),
            ('$\\bar{M}$', pt(pp['RX']), 'The restriction $m(W, x_f, y_f)$'),
            ('$\\bar{P}_f$, $v_f$', f'{pt(pp["Pold"])}, ${run["v_old"]}$', 'The batch claim at $u_f$'),
            ('$A_{\\text{acc}}(u_f)$, $B_{\\text{acc}}(u_f)$', f'${run["a_u"]}$, ${run["b_u"]}$', 'The values of the accumulator pair at $u_f$ that the last fuse\'s eval stage claims'),
        ])])

    claim_names = ['Accumulator', 'Squaring circuit', 'Cubing circuit', 'Stage mask', 'Final mask', 'Wire binding']
    kinds = ['Raw', 'Circuit', 'Circuit', 'Bonding', 'Bonding', 'Masked']
    a_desc = ['$A_{\\text{acc}}$', "$r_1 = a + r'_1$", "$r_2 = a + r'_2$", '$z\\,a + q$', "$z\\,r'_1 + r'_2$", '$q - E_\\sigma$']
    b_desc = ['$B_{\\text{acc}}$', "$r_1(zX) + s_1(X, y) + t(X, z)$", "$r_2(zX) + s_2(X, y) + t(X, z)$", 'Mask freeing gate 1', 'Mask freeing gates 2, 3', '$M_\\sigma$']
    frag['claims'] = table(['Slot $i$', 'Claim', 'Kind', 'Left vector $\\v{\\ell}_i$', 'Right vector $\\v{b}_i$', 'Target $k_i$'],
                           [(i, claim_names[i], kinds[i], a_desc[i], b_desc[i], f'${run["k_list"][i]}$') for i in range(6)])
    assert run['actual'] == run['k_list']
    k1c, k2c = SQUARE.k[1], CUBE.k[1]
    assert SQUARE.k[0] == CUBE.k[0] == 1 and run['k_list'][1:3] == [(1 + k1c * y_c) % Q, (1 + k2c * y_c) % Q]
    frag['targets'] = (
        f'The target of slot 0 is the stored value $c_{{\\text{{acc}}}} = {run["c_old"]}$. The targets of slots 1 and 2 are the circuits\' public input polynomials at $y$. '
        f'The squaring circuit has $k_1(Y) = 1 + {k1c}Y$ and the cubing circuit has $k_2(Y) = 1 + {k2c}Y$, so the targets are $1 + {k1c} \\cdot {y_c} = {run["k_list"][1]}$ and $1 + {k2c} \\cdot {y_c} = {run["k_list"][2]}$ modulo 43. '
        'The three remaining claims have target 0, because masks and wire bindings carry no public inputs.')
    m1, m2 = run['m1'], run['m2']
    frag['binding'] = (
        f'The registry here has two circuits at $W = 1$ and $W = -1$, whose wiring gives $m(1, x_f, y_f) = {m1}$ and $m(-1, x_f, y_f) = {m2}$. The stage $q(X)$ claims those values in the wires $a_1$ and $d_1$, so the expected values are $q^*_0 = {m1}$ and $q^*_1 = {m2}$. '
        f'With $\\sigma = {CH["sigma"]}$, the mask $M_\\sigma$ has a $1$ opposite $a_1$ and a ${CH["sigma"]}$ opposite $d_1$, and $E_\\sigma$ holds the expected values at those two degrees. So the product is $(a_1 - {m1}) + {CH["sigma"]}(d_1 - {m2}) = 0$. '
        f'If the stage holds a wrong $a_1$, the product is nonzero at all 43 values of $\\sigma$. If both wires are wrong, the two errors cancel at one value of $\\sigma$ out of 43. '
        f'This registry holds the staging chapter\'s two circuits and not the registry of [chapter 15](./wiring-and-registry.md), so its $m(W, {X0}, {Y0F})$ is a different polynomial from the one that the [last chapter\'s toy](./ragu-recursion.md) committed under the same name, even though the two runs share $x_f = {X0}$ and $y_f = {Y0F}$.')
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

    # Which first-layer terms vanish, and why: the paired vectors have no entries in mirrored positions.
    al, bl = run['a_list'], run['b_list']
    pairs = [(i, j) for g in range(2) for i in range(3 * g, 3 * g + 3) for j in range(3 * g, 3 * g + 3) if i != j]
    zero_pairs = [pr for pr, e in zip(pairs, run['e1']) if e == 0]
    assert zero_pairs == [(4, 5), (5, 3), (5, 4)]
    for i, j in zero_pairs:
        assert all(al[i][k] * bl[j][D - 1 - k] % Q == 0 for k in range(D))
    assert [k for k, e in enumerate(al[5]) if e] == [pos('a', 0, N)]
    la_, et_ = run['la'], run['et']
    assert la_[4] == CH['mu_p'] * CH['mu'] % Q
    ip, iw, op, ow = run['inner_pairs'], run['inner_weights'], run['outer_pairs'], run['outer_weights']
    mu_c, nu_c, mup_c, nup_c = CH['mu'], CH['nu'], CH['mu_p'], CH['nu_p']
    assert iw[0] == nu_c and iw[2] == mu_c and iw[6] == mup_c * nup_c * nu_c % Q
    assert run['w1'][D - 1] == iw[0] and run['w1'][D - 1 - 6] == iw[6]
    assert op == [(0, 1), (1, 0)] and ow == [nup_c, mup_c]
    inner_sums = [sum(e * w for e, w in zip(run['e1'][6 * g:6 * g + 6], iw[6 * g:6 * g + 6])) % Q for g in range(2)]
    assert (inner_sums[0] + inner_sums[1]) % Q == run['eps1']
    e2a, e2b = run['e2'][0], run['e2'][1]
    assert (e2a * nup_c + e2b * mup_c) % Q == run['eps2']
    assert (run['K_diag'] + run['eps1'] + run['eps2']) % Q == run['K'] == revdot(run['A'], run['B'])

    def pair_table(g):
        cols = range(6 * g, 6 * g + 6)
        return table([f'Pair $(i, j)$, group {g}'] + [f'$({ip[c][0]}, {ip[c][1]})$' for c in cols], [
            ['$e_{i,j}$'] + [f'${run["e1"][c]}$' for c in cols],
            ['Weight in $\\v{W}_1$'] + [f'${iw[c]}$' for c in cols],
        ])
    frag['fold-run'] = '\n'.join([
        f'Claim $i$ sits in group $\\gamma = \\lfloor i / 3 \\rfloor$ at slot $\\kappa = i \\bmod 3$. Claim 4, for example, has $\\gamma = 1$ and $\\kappa = 1$, so $\\lambda_4 = \\mu\'_c\\mu_c$. '
        f'With $\\mu_c = {mu_c}$, $\\nu_c = {nu_c}$, $\\mu\'_c = {mup_c}$ and $\\nu\'_c = {nup_c}$, that is $\\lambda_4 = {mup_c} \\cdot {mu_c} = {la_[4]}$, and the six pairs of weights are these.', '',
        table(['Claim $i$'] + [str(i) for i in range(6)], [
            ['$\\lambda_i$'] + [f'${v}$' for v in la_],
            ['$\\eta_i$'] + [f'${v}$' for v in et_],
        ]), '',
        f'**First layer.** The prover computes the twelve in-group cross terms and commits to them as $\\bar{{E}}_1 = {show(run["E1_pt"])}$ before any weight exists. '
        f'Once all four challenges are drawn, each term gets the weight $(\\mu\'_c\\nu\'_c)^\\gamma \\mu_c^\\kappa \\nu_c^{{\\kappa\'}}$. The pair $(0, 1)$ has $\\gamma = 0$, $\\kappa = 0$ and $\\kappa\' = 1$, so its weight is $\\nu_c = {iw[0]}$. '
        f'The pair $(3, 4)$ has $\\gamma = 1$, $\\kappa = 0$ and $\\kappa\' = 1$, so its weight is $\\mu\'_c\\nu\'_c\\nu_c = {mup_c} \\cdot {nup_c} \\cdot {nu_c} = {iw[6]}$ modulo 43.', '',
        pair_table(0), '',
        pair_table(1), '',
        f'The first term sits at degree 0 of $\\v{{E}}_1$, and its weight ${iw[0]}$ sits at degree $15$ of $\\v{{W}}_1$. The seventh term sits at degree 6 and its weight ${iw[6]}$ at degree $9$. '
        f'Multiplying each term by its weight and adding gives ${inner_sums[0]}$ for group 0 and ${inner_sums[1]}$ for group 1, so $\\varepsilon_1 = {run["eps1"]}$ modulo 43.', '',
        f'The last three terms of group 1, $e_{{4,5}}$, $e_{{5,3}}$ and $e_{{5,4}}$, are zero because the paired vectors never meet in mirrored positions. '
        'The wire-binding vector $q - E_\\sigma$ keeps only the random entry $a_0$ of the stage $q$, which sits in gate 0, and no mask touches gate 0. '
        'The vector $M_\\sigma$ reads only the wires $a_1$ and $d_1$, which belong to the stages, and the final traces leave gate 1 empty.', '',
        f'**Second layer.** With $\\mu_c$ and $\\nu_c$ known, the prover forms $\\v{{A}}_0$, $\\v{{B}}_0$, $\\v{{A}}_1$ and $\\v{{B}}_1$ and computes the two cross-group terms $\\revdot{{\\v{{A}}_0}}{{\\v{{B}}_1}} = {e2a}$ and $\\revdot{{\\v{{A}}_1}}{{\\v{{B}}_0}} = {e2b}$. '
        f'It commits to them as $\\bar{{E}}_2 = {show(run["E2_pt"])}$, and only then are $\\mu\'_c$ and $\\nu\'_c$ drawn. Their weights are $(\\mu\'_c)^0(\\nu\'_c)^1 = {nup_c}$ and $(\\mu\'_c)^1(\\nu\'_c)^0 = {mup_c}$, so '
        f'$\\varepsilon_2 = {e2a} \\cdot {nup_c} + {e2b} \\cdot {mup_c} = {run["eps2"]}$ modulo 43.', '',
        f'**The target.** The prover sends $\\varepsilon_1 = {run["eps1"]}$ and $\\varepsilon_2 = {run["eps2"]}$. The diagonal gives $\\sum_i \\lambda_i \\eta_i k_i = {run["K_diag"]}$, so the verifier sets '
        f'$K = {run["K_diag"]} + {run["eps1"]} + {run["eps2"]} = {run["K"]}$. The prover can check that $\\revdot{{\\v{{A}}}}{{\\v{{B}}}}$ is also ${revdot(run["A"], run["B"])}$, but the verifier cannot compute that product, and the split of Section 5 is what tests it.'])

    frag['derived'] = (
        f'The verifier obtains $\\bar{{A}}_c = {show(run["A_c_pt"])}$, $\\bar{{T}} = {show(run["T_pt"])}$ and $\\bar{{B}}_c = {show(run["B_c_pt"])}$ from small MSMs over the instance\'s points, with the weights above. Because $\\eta_0 = 1$ in every proof, the point $\\bar{{B}}_c$ is $\\bar{{B}}_{{\\text{{acc}}}}$ itself. Committing to the three polynomials directly gives the same points.')

    o = run['o']
    rho, r_c = CH['rho'], CH['r']
    rho2 = rho * rho % Q
    assert run['target_p0'] == (run['K'] + rho * run['eps1'] + rho2 * run['eps2']) % Q
    ab_r = run['A_r'] * run['B_r'] % Q
    t2 = rho * o['E1'] * run['W1r'] % Q
    t3 = rho2 * o['E2'] * run['W2r'] % Q
    rp = pow(r_c, D - 1, Q) * o['p'] % Q
    rq = pow(r_c, D, Q) * o['q'] % Q
    assert (ab_r + t2 + t3) % Q == run['lhs'] and (rp + rq) % Q == run['rhs']
    assert run['pub_a'] == (-la_[5] * run['Er']) % Q
    et = et_
    frag['split-run'] = '\n'.join([
        f'At $\\rho = {rho}$ the prover commits to $\\bar{{\\Pi}}_{{\\text{{lo}}}} = {show(run["p_pt"])}$ and $\\bar{{\\Pi}}_{{\\text{{hi}}}} = {show(run["q_pt"])}$. '
        f'The verifier sets aside the required value $\\Pi_{{\\text{{lo}}}}(0) = K + \\rho\\,\\varepsilon_1 + \\rho^2\\varepsilon_2 = {run["K"]} + {rho} \\cdot {run["eps1"]} + {rho2} \\cdot {run["eps2"]} = {run["target_p0"]}$, using $\\rho^2 = {rho2}$. '
        f'It then picks $r = {r_c}$, so that $rz = {r_c * z_c % Q}$ and $1/r = {run["ri"]}$, and the prover sends seven values.', '',
        table(['$A_c(r)$', '$T(rz)$', '$B_c(r)$', '$E_1(r)$', '$E_2(r)$', '$\\Pi_{\\text{lo}}(1/r)$', '$\\Pi_{\\text{hi}}(r)$'],
              [tuple(f'${o[k]}$' for k in ['Ac', 'T', 'Bc', 'E1', 'E2', 'p', 'q'])]), '',
        f'The verifier evaluates the public parts at $r$ itself. Only the wire binding contributes to $A_{{\\text{{pub}}}}$, and $E_\\sigma(r) = {run["Er"]}$, so',
        '',
        f'$$A_{{\\text{{pub}}}}(r) = -\\lambda_5 E_\\sigma(r) = -{la_[5]} \\cdot {run["Er"]} = {run["pub_a"]} \\pmod{{43}}.$$',
        '',
        f'For $B_{{\\text{{pub}}}}$ it computes $s_1(r, y) = {run["s1r"]}$, $s_2(r, y) = {run["s2r"]}$ and $t(r, z) = {run["tr"]}$, the stage mask and final mask at $r$, which are ${run["ma"]}$ and ${run["mf"]}$, and $M_\\sigma(r) = {run["mr"]}$. With the weights $\\eta_i$ from Section 4,',
        '',
        f'$$B_{{\\text{{pub}}}}(r) = \\eta_1 (s_1 + t) + \\eta_2 (s_2 + t) + \\eta_3\\, \\text{{mask}}_1(r) + \\eta_4\\, \\text{{mask}}_{{2,3}}(r) + \\eta_5 M_\\sigma(r) = {et[1]}({run["s1r"]} + {run["tr"]}) + {et[2]}({run["s2r"]} + {run["tr"]}) + {et[3]} \\cdot {run["ma"]} + {et[4]} \\cdot {run["mf"]} + {et[5]} \\cdot {run["mr"]} = {run["pub_b"]}.$$',
        '',
        f'So $A(r) = A_c(r) + A_{{\\text{{pub}}}}(r) = {o["Ac"]} + {run["pub_a"]} = {run["A_r"]}$ and $B(r) = B_c(r) + T(rz) + B_{{\\text{{pub}}}}(r) = {o["Bc"]} + {o["T"]} + {run["pub_b"]} = {run["B_r"]}$, modulo 43. '
        f'The public vectors of the fold give $W_1(r) = {run["W1r"]}$ and $W_2(r) = {run["W2r"]}$, so the left side of the split is',
        '',
        f'$$A(r)B(r) + \\rho\\,E_1(r)W_1(r) + \\rho^2 E_2(r)W_2(r) = {ab_r} + {t2} + {t3} = {run["lhs"]},$$',
        '',
        f'and the right side is $r^{{15}}\\Pi_{{\\text{{lo}}}}(1/r) + r^{{16}}\\Pi_{{\\text{{hi}}}}(r) = {rp} + {rq} = {run["rhs"]}$.'])

    rows = []
    for j, (i, at, val) in enumerate(run['claims']):
        rows.append((j, f'${run["names"][i]}$', pt(run['pts'][i]), f'${at}$', f'${val}$'))
    n_red = sum(1 for i, _, _ in run['claims'] if i <= 6)
    n_inst = len(run['claims']) - n_red
    n_vals = 7
    assert n_red == n_vals + 1 and n_inst == 4
    frag['claims-count'] = (
        f'The reduction leaves ${n_red}$ claims, ${n_vals}$ from the values above and one for the required $\\Pi_{{\\text{{lo}}}}(0)$. '
        f'The instance adds [${n_inst}$ of its own](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L717-L741), which carry the fuse\'s accumulators into the check.')
    n_polys, n_claims = len(run['polys']), len(run['claims'])
    assert n_polys == 11 and n_claims == 12 and n_polys == n_claims - 1
    frag['batch-counts'] = (
        f'[Chapter 8\'s batch](./batched-openings.md#_7-beta-batching) turns all ${n_claims}$ claims into one. It needs two counts, because several claims can be about the same polynomial. '
        f'Write $h_0, \\ldots, h_{{N-1}}$ for the distinct polynomials and $J$ for the number of claims, where claim $j$ is about the polynomial $h_{{i_j}}$. '
        f'$\\Pi_{{\\text{{lo}}}}$ appears in two claims and counts once, so our run has $N = {n_polys}$ polynomials and $J = {n_claims}$ claims.')
    frag['claims-list'] = table(['Claim $j$', 'Polynomial', 'Commitment', 'Point $x_j$', 'Value $y_j$'], rows)

    # Points that repeat by chance on the 43-point toy curve.
    named = [('\\bar{A}', pp['A']), ('\\bar{Q}', pp['Q']), ("\\bar{R}'_1", pp['R1']), ("\\bar{R}'_2", pp['R2']),
             ('\\bar{A}_{\\text{acc}}', pp['Aold']), ('\\bar{B}_{\\text{acc}}', pp['Bold']), ('\\bar{M}', pp['RX']), ('\\bar{P}_f', pp['Pold']),
             ('\\bar{A}_c', run['A_c_pt']), ('\\bar{T}', run['T_pt']), ('\\bar{B}_c', run['B_c_pt']), ('\\bar{E}_1', run['E1_pt']),
             ('\\bar{E}_2', run['E2_pt']), ('\\bar{\\Pi}_{\\text{lo}}', run['p_pt']), ('\\bar{\\Pi}_{\\text{hi}}', run['q_pt']), ('\\bar{F}', bat['F_pt']), ('\\bar{H}', bat['H_pt']),
             ('\\bar{S}', arg['S_pt']), ('start', arg['start'])]
    for j, (l_, r2) in enumerate(arg['rounds']):
        named += [(f'L_{j + 1}', l_), (f'R_{j + 1}', r2)]
    assert run['et'][0] == 1 and run['B_c_pt'] == pp['Bold']
    named = [(nm, p_) for nm, p_ in named if nm != '\\bar{B}_c']
    groups_ = {}
    for nm, p_ in named:
        groups_.setdefault(p_, []).append(nm)
    repeats = [(p_, nms) for p_, nms in groups_.items() if len(nms) > 1]
    assert len(repeats) >= 3

    def label(nm):
        return 'the IPA statement' if nm == 'start' else f'${nm}$'

    def listing(nms):
        names_ = [label(nm) for nm in nms]
        if len(names_) == 2:
            return f'{names_[0]} and {names_[1]} are both'
        return ', '.join(names_[:-1]) + f' and {names_[-1]} are all'

    frag['coincidence'] = (
        'With only 43 points on the toy curve, several points in this run repeat by chance: '
        + '; '.join(f'{listing(nms)} ${show(p_)}$' for p_, nms in repeats)
        + '. The vectors behind them differ. On the real curves, with about $2^{254}$ points each, such a repeat does not happen in practice.')

    m_w = run['m_w']
    half = inv(2)
    assert m_w == ((1 + w_c) * m1 + (1 - w_c) * m2) * half % Q
    frag['registry-value'] = (
        f'Claim 8 opens $m(W, x_f, y_f)$ at the fresh point $w = {w_c}$. The verifier computes the value for itself. It evaluates the wiring of both circuits at $(x_f, y_f)$, which gives ${m1}$ and ${m2}$ as above, and combines them with the Lagrange weights of the two domain points $1$ and $-1$: '
        f'$m(w, x_f, y_f) = \\tfrac{{1}}{{2}}\\big((1 + w) \\cdot {m1} + (1 - w) \\cdot {m2}\\big) = \\tfrac{{1}}{{2}}\\big({(1 + w_c) * m1} - {(w_c - 1) * m2}\\big) = {m_w}$ modulo 43. '
        'This is the step that reads the whole registry.')
    frag['batch-run'] = (
        f'With $\\alpha = {CH["alpha"]}$ the quotient commits to $\\bar{{F}} = {show(bat["F_pt"])}$. At $u = {CH["u"]}$ the prover sends the eleven values $h_i(u)$, which are ${vec(bat["zs"])}$. '
        f'The verifier derives $f(u) = {bat["fu"]}$ from those values and the claims. With $\\beta = {CH["beta"]}$ this gives $\\bar{{H}} = {show(bat["H_pt"])}$ and $v = {bat["v"]}$, and the prover\'s polynomial $H$ agrees on both.')
    rows = [(j + 1, CH['us'][j], pt(l_), pt(r2)) for j, (l_, r2) in enumerate(arg['rounds'])]
    frag['ipa-run'] = '\n'.join([
        f'The argument commits to the masking polynomial, $\\bar{{S}} = {show(arg["S_pt"])}$, and takes $\\xi = {CH["xi"]}$ and a multiplier $\\zeta = {CH["z_ipa"]}$ on $U$. The statement becomes $\\bar{{H}} - v \\cdot G_0 + \\xi \\cdot \\bar{{S}} = {show(arg["start"])}$. Then come $\\log_2 16 = 4$ rounds.', '',
        table(['Round', 'Challenge', '$L_j$', '$R_j$'], rows), '',
        f'The final scalar is $\\hat{{a}} = {arg["c"]}$. The verifier computes $\\hat{{G}} = {show(arg["G_hat"])}$ from an MSM over all sixteen generators and $\\hat{{b}} = {arg["b_hat"]}$ from a product of four factors. The folded statement is ${show(arg["end"])}$, and $\\hat{{a}} \\cdot (\\hat{{G}} + \\hat{{b}} \\zeta \\cdot U) = {show(arg["right"])}$, so the verifier accepts.'])

    # --- Cheating on the fold: a false target.
    bad = compress(CH, targets=((1 + 11 * CH['y']) % Q, run['k_list'][2]))
    assert not bad['fold_ok']
    gap_ = (revdot(bad['A'], bad['B']) - bad['K']) % Q
    assert gap_ != 0
    shift_ = (bad['K'] - revdot(bad['A'], bad['B'])) % Q
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
    bal_shift = (revdot(bad['A'], bad['B']) - bad['K']) % Q
    bal_rho = [rho for rho in range(Q)
               if (revdot(bad['A'], bad['B']) + rho * bad['eps1'] + rho * rho * bad['eps2']) % Q
               == (bad['K'] + bal_shift + rho * (bad['eps1'] + bal_shift) + rho * rho * bad['eps2']) % Q]
    assert len(bal_rho) == 1
    bal_rho = bal_rho[0]
    assert bal_rho == 0
    # Exhaustive over (mu, nu) for a prover that lowers the term e_{0,1}, of weight nu, by e before the challenges.
    k_gap = (bad['k_list'][1] - run['k_list'][1]) % Q
    assert k_gap == CH['y']
    assert shift_ == k_gap * CH['mu'] * CH['nu'] % Q and revdot(bad['A'], bad['B']) == run['K']
    counts = set()
    for extra in range(1, Q):
        counts.add(sum(1 for mu in range(1, Q) for nu in range(1, Q) if (k_gap * mu * nu - extra * nu) % Q == 0))
    assert counts == {42}
    EXTRA_E = 5
    mu_star = EXTRA_E * inv(k_gap) % Q
    hit = compress(dict(CH, mu=mu_star), targets=((1 + 11 * CH['y']) % Q, run['k_list'][2]))
    assert (hit['K'] - EXTRA_E * CH['nu']) % Q == revdot(hit['A'], hit['B'])
    frag['cheat-target'] = (
        f'Suppose the prover claims the output $11$ for the squaring circuit in place of $10$, so $k_1(Y)$ becomes $1 + 11Y$ and its target rises by $y = {CH["y"]}$ while its vectors stay honest. The target $K$ of the folded pair then rises by ${k_gap}\\mu_c\\nu_c$, which at our challenges is ${shift_}$, while $\\revdot{{\\v{{A}}}}{{\\v{{B}}}}$ stays at ${revdot(bad["A"], bad["B"])}$, so the pair falls short of its new target by ${shift_}$. '
        f'The prover sees $\\mu_c$ and $\\nu_c$ only after it commits to $\\v{{E}}_1$, so any correction has to go in before them. It can lower the term $e_{{0,1}}$, whose weight is $\\lambda_0 \\eta_1 = \\nu_c$, by some amount $\\delta$. The false target adds ${k_gap}\\mu_c\\nu_c$ to $K$ and the lowered term removes $\\delta\\nu_c$, so the fold balances only if $\\mu_c = \\delta / {k_gap}$. '
        f'For $\\delta = {EXTRA_E}$ that means $\\mu_c = {mu_star}$, and we confirmed the balance there on the full vectors. Over all ${n(42 * 42)}$ nonzero pairs $(\\mu_c, \\nu_c)$, every nonzero $\\delta$ balances exactly ${counts.pop()}$ pairs, which is one value of $\\mu_c$ out of 42.')
    frag['cheat-epsilon'] = (
        f'Take the false public input above again, where $K$ exceeds $\\revdot{{\\v{{A}}}}{{\\v{{B}}}}$ by ${shift_}$. After seeing all four fold challenges, the prover could shift $\\varepsilon_1$ alone by some $\\delta$ and leave $\\v{{E}}_1$ as committed. '
        f'The verifier\'s $K$ moves by $\\delta$ as well, so $\\delta = -{shift_} = {bal_shift}$ modulo 43 makes $(A, B)$ balance, with a new target $K\' = \\revdot{{\\v{{A}}}}{{\\v{{B}}}}$. '
        f'The claim $(E_1, W_1, \\varepsilon_1)$ is now false by $\\delta$, and that shows up in the split. The required constant term is $K\' + \\rho(\\varepsilon_1 + \\delta) + \\rho^2\\varepsilon_2$, while the true coefficient of $X^{{15}}$ in $\\Pi$ is $K\' + \\rho\\,\\varepsilon_1 + \\rho^2\\varepsilon_2$, '
        f'so the two differ by $\\rho\\delta$, which vanishes only at $\\rho = {bal_rho}$. The prover fixes $\\varepsilon_1$ before $\\rho$ is drawn, so it cannot steer $\\rho$ there. '
        f'A shift that does not balance $(A, B)$ leaves both gaps open, and they cancel at no more than one $\\rho$. '
        f'We tried all $42$ nonzero shifts against all $43$ values of $\\rho$, and each shift passes at exactly ${rho_passes_each[0]}$ value of $\\rho$.')

    # --- Cheating on the split. A false claim leaves the true coefficient of X^(D-1) off the required value by
    # delta; we model it as the honest product with halves whose constant is off by delta, which gives the same
    # difference polynomial. The other coefficients are chosen to create roots.
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
        f'Suppose one of the three claims is false, so that the true $\\Pi$\'s coefficient of $X^{{15}}$ misses the required value by ${delta}$. The prover commits to a $\\Pi_{{\\text{{lo}}}}$ whose constant term is the required value anyway, so that the opening at $0$ passes. '
        f'The coefficient of $X^{{15}}$ in $X^{{15}}\\Pi_{{\\text{{lo}}}}(1/X) + X^{{16}}\\Pi_{{\\text{{hi}}}}(X)$ is exactly $\\Pi_{{\\text{{lo}}}}(0)$, so whatever else the prover does, the committed halves differ from the true product by a nonzero polynomial of degree at most ${2 * D - 2}$. '
        f'The prover can choose the other coefficients of $\\Pi_{{\\text{{lo}}}}$ and $\\Pi_{{\\text{{hi}}}}$ to give that difference as many roots as possible, and we built such a pair. It passes the split at ${r_pass}$ of the $42$ nonzero values of $r$. '
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
        f'A real compressed proof has ${native_single}$ native claims, namely one accumulator pair, one application circuit, ${NATIVE_CIRCUITS}$ internal circuits, ${NATIVE_MASKS}$ masks and $5$ wire bindings, and it has ${nested_single}$ nested claims.')
    # Why groups: the length of the cross-term vectors with one layer and with two.
    one_layer = native_single * (native_single - 1)
    assert one_layer < 2 ** 13
    frag['group-reason'] = (
        f'The real claim lists of Section 3 show the effect. With one layer, every ordered pair of distinct claims gives a cross term, so the ${native_single}$ native claims would need ${native_single} \\cdot {native_single - 1} = {n(one_layer)}$ terms in $\\v{{E}}_1$. '
        f'In groups of $7$ they form ${ng}$ groups. The pairs inside each group give ${ni}$ first-layer terms in $\\v{{E}}_1$, and the ordered pairs of distinct groups give ${no}$ second-layer terms in $\\v{{E}}_2$, or ${ni + no}$ in all. '
        f'The ${nested_single}$ nested claims form ${mg}$ groups in the same way, with ${mi}$ first-layer and ${mo}$ second-layer terms. '
        f'Even the single layer fits in a vector of ${n(2 ** 13)}$ entries, so the vector length does not force the grouping.')
    frag['verifier-cost'] = table(['Verifier step, per curve', 'Work', 'Growth'], [
        ('Replay the fuse transcript (Section 2)', f'${3 + 5}$ permutations, on the native field only', 'Constant'),
        ('Recompute the challenge stage and the `ab` bridge (Section 2)', 'Two small commitments, on the nested curve only', 'Constant'),
        ('Compute targets $k(y)$', 'One Horner step per public wire', 'Size of the instance'),
        ('Derive $\\bar{A}_c$, $\\bar{T}$, $\\bar{B}_c$, $\\bar{H}$', 'MSMs over the instance\'s points', 'Size of the instance'),
        ('Compute $s_i(r, y)$ for each circuit claim', f'${NATIVE_CIRCUITS + 1}$ native and ${NESTED_CIRCUITS}$ nested circuits, one term per wiring coefficient', '**Linear in the circuits**'),
        ('Compute registry values for the wire bindings', 'One pass over the domain at $(x_f, y_f)$, plus a constant number of further evaluations', '**Linear in the registry**'),
        ('Compute $m(w, x_f, y_f)$', 'One pass over the registry, with Lagrange weights', '**Linear in the registry**'),
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
    ]) + '\n\n' + (
        f'Each row matches a message of this chapter. The revdot reduction sends ${reduction_p}$ points, $\\bar{{E}}_1$, $\\bar{{E}}_2$, $\\bar{{\\Pi}}_{{\\text{{lo}}}}$ and $\\bar{{\\Pi}}_{{\\text{{hi}}}}$, '
        f'and ${reduction_s}$ scalars, which are $\\varepsilon_1$, $\\varepsilon_2$ and the ${reduction_s - 2}$ values of Section 5. The batch sends the point $\\bar{{F}}$ and the ${batch_s}$ values $h_i(u)$. '
        f'The IPA sends $\\bar{{S}}$ and one pair $L_j$, $R_j$ for each of ${rank}$ rounds, which is ${ipa_p}$ points, and the final scalar $\\hat{{a}}$.')
    frag['size-total'] = (
        f'At 32 bytes per point or scalar, with [4 bytes for the circuit index](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/registry.rs#L7-L20) and the [28-byte envelope](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/format.rs#L41), that comes to ${n(compressed)}$ bytes. '
        f'The [uncompressed encoding](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/polynomial.rs#L1-L10) writes ${n(2 ** rank)}$ coefficients for each of ${NUM_POLYS}$ polynomials, which is ${n(uncompressed_polys)}$ bytes before counting its cached points, so compression shrinks the proof by a factor of about ${uncompressed_polys // compressed:,}$. '
        f'Most of the compressed proof is the instance, with ${inst_points}$ of its ${total_p}$ points. The IPA rounds, the only part that grows with the circuit size, take ${2 * 2 * rank}$ points.')

    frag['header-extra'] = (
        f'A header larger than ${H_SIZE}$ elements adds ${2 * 32}$ bytes per extra element, since the proof holds the two child headers. The output header does not count, because [the verifier supplies it](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/verifier.rs#L83) as the statement.')
    frag['recap-size'] = (
        f'7. By our count a compressed proof takes ${n(compressed)}$ bytes, against more than ${n(uncompressed_polys)}$ uncompressed. Rerandomization and hiding are not yet established, and the comparison with Orchard remains an estimate.')

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
    inv0 = inv(l0)
    gap_pt = combine((1, out_pt), (Q - l1, seed_pt))
    back = mul(inv0, gap_pt)
    assert back == input_pt and seed_pt == pp['Aold'] and input_pt == pp['Bold']
    frag['rerandomize'] = (
        f'Reduce the fold to one commitment and let the output be $\\bar{{A}}_{{\\text{{out}}}} = \\lambda_0 \\bar{{A}}_{{\\text{{in}}}} + \\lambda_1 \\bar{{A}}_{{\\text{{seed}}}}$, with the public weights $\\lambda_0 = {l0}$ and $\\lambda_1 = {l1}$ and the cached seeded point $\\bar{{A}}_{{\\text{{seed}}}} = {show(seed_pt)}$. '
        f'An input of ${show(input_pt)}$ gives the output ${show(out_pt)}$. Because the weights are public, an observer can run the equation backwards, '
        f'$\\bar{{A}}_{{\\text{{in}}}} = \\lambda_0^{{-1}}(\\bar{{A}}_{{\\text{{out}}}} - \\lambda_1 \\bar{{A}}_{{\\text{{seed}}}})$, with $\\lambda_0^{{-1}} = {inv0}$. '
        f'Here $\\bar{{A}}_{{\\text{{out}}}} - {l1} \\cdot \\bar{{A}}_{{\\text{{seed}}}} = {show(gap_pt)}$, and ${inv0} \\cdot {show(gap_pt)} = {show(back)}$, which is the input. '
        f'So each output names exactly one input, and anyone can compute which. Several of these points also appear in the compression run above, by the same chance as in Section 6.')

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
        f'Take the stage $a(X)$ from [chapter 17](./staging.md), where $v = x^2$ and one random entry sits at $a_0$. Among all ${n(Q * Q)}$ pairs $(x, a_0)$, the commitment ${show(A_pt)}$ matches ${by_commit}$. '
        f'Adding one value at a point, $a({OPEN}) = {value}$, leaves ${len(by_both)}$ pairs, the true $(3, {ALPHA})$ and also ${other}$. On the toy curve we can find each generator\'s discrete log by search, so the commitment becomes one linear equation in $a_0$, $x$ and $v = x^2$ with known coefficients. The value $a({OPEN}) = {value}$ gives a second linear equation in the same unknowns, and eliminating $a_0$ leaves a quadratic equation in $x$ with these two roots. On a real curve nobody can list the commitment\'s matches, but the value still gives one linear equation in the secret wires, which is the sense in which the proof does not hide them.')

    print(json.dumps(frag))
