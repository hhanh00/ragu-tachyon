"""Worked examples for ragu-recursion.md. Prints fragments as JSON.

The transcript run mirrors the schedule of crates/ragu_pcd/src/fuse/mod.rs and
the circuits hashes_1.rs and hashes_2.rs at Ragu commit 3219e08. The counts of
the standard profile come from crates/ragu_pcd/src/profile.rs. compression.py
imports the helpers and constants defined here; the fragments print only when
this file runs as a script.
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
NESTED_STAGES = NESTED_RX - NESTED_CIRCUITS     # eight bridges, the challenge stage, the endoscalar and points stages
assert NESTED_STAGES == 8 + 1 + 2 == 11
frag['remainder'] = (
    f'Replaying the transcript alone takes ${n(8 * 288)}$ gates, more than one circuit holds, as Section 4 counts. The walk that folds the other curve\'s commitments '
    f'fills ${NATIVE_STEPS}$ circuits of its own, a count that [chapter 16 derived](./endoscalars.md#_13-feedback-between-the-walks).')
# The schedule also commits four polynomials per side that a proof does not carry: the
# two child restrictions m(w, x_i, Y), the restriction m(w, X, y) and the quotient f
# (the Native/Nested SPrime, RegistryWy and F structs are "ephemeral" in fuse/_03, _04 and _08 at 3219e08).
CARRIED_EXTRA = ['A', 'B', 'm(W, x, y)', 'p']
EPHEMERAL = ['m(w, x_0, Y)', 'm(w, x_1, Y)', 'm(w, X, y)', 'f']
NATIVE_FINAL_MASKS = ['Outer error', 'Inner error', 'Eval', 'Preamble', 'Walk']   # the Final mask column of Section 3
assert NATIVE_MASKS == 11 + len(NATIVE_FINAL_MASKS)
NATIVE_COMMITTED = NATIVE_RX + len(CARRIED_EXTRA) + len(EPHEMERAL)
NESTED_COMMITTED = NESTED_RX + len(CARRIED_EXTRA) + len(EPHEMERAL)
assert NUM_POLYS == NATIVE_COMMITTED + NESTED_COMMITTED - 2 * len(EPHEMERAL)
frag['census'] = '\n'.join([
    'The table counts the polynomials of one fuse in the standard profile, side by side.', '',
    table(['', 'Native side', 'Nested side'], [
        ('Circuit traces', f'${NATIVE_CIRCUITS + 1}$: the ${NATIVE_CIRCUITS}$ internal circuits of this section and the application',
         f'${NESTED_CIRCUITS}$: ${NESTED_STEPS}$ endoscaling steps, `collapse` and `compute_v`'),
        ('Stages', '$11$: preamble, inner error, outer error, query, eval, the five points stages and the walk',
         f'${NESTED_STAGES}$: the eight bridge stages, the challenge stage, and one stage each for the endoscalar\'s bits and the points it walks'),
        ('Accumulators', '$4$: $A$, $B$, $m(W, x, y)$ and $p$', '$4$: their nested counterparts'),
        ('Used only inside the fuse', '$4$: $m(w, x_0, Y)$, $m(w, x_1, Y)$, $m(w, X, y)$ and $f$', '$4$: their nested counterparts'),
        ('Committed in all', f'${NATIVE_COMMITTED}$', f'${NESTED_COMMITTED}$'),
    ]), '',
    f'The schedule commits ${NATIVE_COMMITTED + NESTED_COMMITTED}$ polynomials in all. A proof carries ${NUM_POLYS}$ of them to its parent, '
    f'which is the count [the code records](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L2364-L2379). '
    f'The other ${2 * len(EPHEMERAL)}$ serve only the fuse that made them. Their values at the fuse\'s points sit in the query and eval stages, '
    'and the fuse folds the polynomials themselves into its new batch polynomial $p$, so a parent that holds $p$ never needs them again. '
    'The code [marks them as ephemeral](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/_03_s_prime.rs#L23-L24).', '',
    f'The claims follow the same split. The native side folds ${NATIVE_CLAIMS}$ revdot claims, a count that [chapter 17 derived](./staging.md#_15-staging-in-ragu). '
    f'Its ${NATIVE_MASKS}$ mask claims are one for each of the $11$ stages and one for each of the ${len(NATIVE_FINAL_MASKS)}$ final masks, '
    f'and those ${len(NATIVE_FINAL_MASKS)}$ are exactly the distinct entries of the "Final mask" column above, namely '
    + ', '.join(m.lower() for m in NATIVE_FINAL_MASKS[:-1]) + f' and {NATIVE_FINAL_MASKS[-1].lower()}. '
    f'The nested side folds ${NESTED_CLAIMS_TOTAL}$, which are $2$ raw claims (one per child), ${2 * NESTED_CIRCUITS}$ circuit claims (${NESTED_CIRCUITS}$ per child) '
    f'and ${NESTED_BONDINGS}$ mask claims, one for each of its ${NESTED_STAGES}$ stages and ${NESTED_BONDINGS - NESTED_STAGES}$ for final masks.'])


# ---------------------------------------------------------------- The transcript
SCHEDULE = [('preamble', ['w']), ('s_prime', ['y', 'z']), ('inner_error', ['mu']), ('outer_error', ['mu_prime']),
            ('ab', ['x']), ('query', ['alpha']), ('f', ['u']), ('eval', ['pre_beta'])]
NAMES = dict(w='w', y='y', z='z', mu=r'\tau', mu_prime=r"\tau'", x='x', alpha=r'\alpha', u='u', pre_beta=r'\text{pre\_beta}')
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
    f'The second half loads those cells and squeezes $\\tau = {second["mu"]}$ with no further permutation, so the second half\'s five permutations begin when it absorbs `outer_error`. '
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
    f'Suppose a prover wants $\\tau = {target_mu}$, and it writes the state $({forged_state[0]}, {forged_state[1]}, {forged_state[2]})$ into `outer_error`. '
    f'The second half alone would resume from this state and produce $\\tau = {forged["mu"]}$ and $\\tau\' = {forged["mu_prime"]}$. '
    f'Of the ${n(Q ** 3)}$ possible states, ${n(choosing)}$ give the wanted $\\tau$, but the first half compares the stage with the state it computed, and exactly ${passing}$ state passes that comparison, the honest one. '
    'Both circuits read one committed stage polynomial, so the prover cannot show them different values.')

# ---------------------------------------------------------------- Public inputs
# Slot owners, from the receive and provide calls in internal/native/circuits at 3219e08.
SLOTS = [('Bridge commitments for preamble, $s\'$ and inner error; $w$, $y$, $z$', 3, 3, '`hashes_1`'),
         ('Bridge commitments for outer error, $ab$, query, $f$ and eval; $\\tau$, $\\tau\'$, $x$, $\\alpha$, $u$, `pre_beta`', 5, 6, '`hashes_2`'),
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
        ('$k_{\\text{headers}}$', 'Unified output, left, right, $0$', f'${k_bridge}$', '$0$'),
        ('$k_{\\text{app}}$', 'Left, right, output', f'${k_app}$', f'${HEADER_OUT[1]}$'),
        ('Endoscaling step', '$0$', f'${k_at([0], Y0)}$', '$0$'),
    ]), '',
    f'Horner\'s rule reaches ${pre}$ after the five unified wires, and both $k_{{\\text{{unified}}}}$ and $k_{{\\text{{headers}}}}$ continue from that value. Each table entry also matches a direct evaluation of the polynomial.'])

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
    f'Let an internal circuit expose wires $(a, b)$ and its zero suffix, so that $k_{{\\text{{int}}}}(Y) = aY^3 + bY^2 + 0 \\cdot Y + 1$, and let an application circuit expose a header $(d, s)$, so that $k_{{\\text{{app}}}}(Y) = dY^2 + sY + 1$. '
    f'Their difference is $aY^3 + (b - d)Y^2 - sY$. '
    f'If an application could use the suffix $s = 0$, the difference would vanish whenever $a = 0$ and $b = d$. That happens for ${same_with_zero_suffix}$ of the ${n(Q ** 3)}$ triples $(a, b, d)$, and for those the swap would pass at every $y$. '
    f'For $s = 3, 4, 5$ the coefficient of $Y$ in the difference is $-s$, which is not zero, so no choice of $a$ and $b - d$ can cancel it. We tried all ${n(Q * Q)}$ pairs $(a, b - d)$ for each $s$ and found none that makes the polynomials identical. '
    f'At a nonzero $y$ the difference vanishes only where $ay^2 + (b - d)y - s$ does, and a polynomial of degree $2$ has at most $2$ roots. The worst pair reaches that bound, so the two values agree at no more than ${worst}$ of the $42$ nonzero values of $y$. On a real field the same count of roots is a negligible fraction.')


# ---------------------------------------------------------------- What passes up the tree
# Values reused from the worked runs of chapters 14 (revdot_folding), 12 (split_accumulation)
# and 15 (wiring_and_registry). Those scripts print on import, so we silence them.
with contextlib.redirect_stdout(io.StringIO()):
    import revdot_folding as rf
    import split_accumulation as sa
    import wiring_and_registry as wr

# (A, B, c): the two claims of chapter 14 stand in for the children's accumulators, and the
# parent folds them with one layer of chapter 14's quotient fold, at that chapter's tau.
ab_left, ab_right = rf.claims[0], rf.claims[1]
TAU = rf.LMU
ab_pair = [ab_left, ab_right]
ab_q = rf.quotient(rf.error_matrix(ab_pair))
assert not any(ab_q['rem']) and len(ab_q['q']) == 1 and TAU not in (0, 1)
ab_fold = rf.lagrange_fold(ab_pair, ab_q['q'], TAU)
assert rf.revdot(ab_fold['a'], ab_fold['b']) == ab_fold['c']
ab_new = rf.Claim(ab_fold['a'], ab_fold['b'], ab_fold['ga'], ab_fold['gb'], ab_fold['c'])
assert ab_new.true()
assert ab_new.A == rf.combine_points(ab_fold['lam'], [x.A for x in ab_pair])
assert ab_new.B == rf.combine_points(ab_fold['lam'], [x.B for x in ab_pair])

# (P, u, v): chapter 12's first accumulator for the left child, and a fresh one for the right.
pv_left = sa.accs[0]
pv_right, _, _ = sa.acc_prove([], [sa.proofs[1]], **sa.FOLD_CH[1])
PV_CH = dict(alpha=7, u=12, beta=19, gamma_f=3)
pv_new, pv_pf, _ = sa.acc_prove([pv_left, pv_right], [], **PV_CH)
pv_ch = {k: PV_CH[k] for k in ('alpha', 'u', 'beta')}
assert sa.distinct_weights(pv_ch['alpha'], pv_ch['beta'], 2)
assert sa.acc_verify([pv_left.inst, pv_right.inst], pv_new.inst, pv_pf, **pv_ch)
assert sa.decide(pv_left.inst, pv_left.p, pv_left.gamma) and sa.decide(pv_right.inst, pv_right.p, pv_right.gamma)
assert sa.decide(pv_new.inst, pv_new.p, pv_new.gamma)
assert PV_CH['u'] not in (pv_left.u, pv_right.u) and None not in (pv_left.P, pv_right.P, pv_new.P)

# m(W, x_i, y_i): the two children of chapter 15's registry run, and the parent's new restriction.
m_left, m_right, m_new = wr.s_acc0, wr.s_acc1, wr.s_new
assert None not in (wr.commit(m_left), wr.commit(m_right), wr.commit(m_new))


def inst_ab(c):
    return f'$({show(c.A)},\\ {show(c.B)},\\ {c.c})$'


def inst_pv(a):
    return f'$({show(a.P)},\\ {a.u},\\ {a.v})$'


def inst_m(poly_, x_, y_):
    return f'$m(W, {x_}, {y_})$, committed as ${show(wr.commit(poly_))}$'


frag['shape'] = table(['Accumulator', 'Left child', 'Right child', 'Parent leaves'], [
    ('$(A, B, c)$', inst_ab(ab_left), inst_ab(ab_right), inst_ab(ab_new)),
    ('$(P, u, v)$', inst_pv(pv_left), inst_pv(pv_right), inst_pv(pv_new)),
    ('Restriction', inst_m(m_left, wr.X0, wr.Y0), inst_m(m_right, wr.X1, wr.Y1), inst_m(m_new, wr.X, wr.Y)),
]) + (
    f'\n\nIn the first row the children\'s pairs are the first two proof claims of chapter 14. The parent folds them with one layer of [that chapter\'s quotient fold](./revdot-folding.md#_10-the-quotient-fold-in-ragu-s-fuse), the fold the schedule runs in phases 4 and 5. '
    f'For two claims the quotient has the single coefficient ${ab_q["q"][0]}$, and at $\\tau = {TAU}$, the challenge of chapter 14\'s run, the weights are $({ab_fold["lam"][0]}, {ab_fold["lam"][1]})$ and the new value is '
    f'$c^* = {ab_fold["k"]} + {ab_fold["z"]} \\cdot {ab_fold["q"]} = {ab_fold["c"]}$. The folded vectors satisfy $\\revdot{{\\v{{a}}}}{{\\v{{b}}}} = {ab_new.c}$.\n\n'
    f'In the second row the left child holds the first accumulator of [chapter 12\'s run](./split-accumulation.md#_6-a-run-on-the-toy-curve) and the right child holds a fresh one. The parent batches the two claims $p_L({pv_left.u}) = {pv_left.v}$ and $p_R({pv_right.u}) = {pv_right.v}$ with $\\alpha = {PV_CH["alpha"]}$, $u = {PV_CH["u"]}$ and $\\beta = {PV_CH["beta"]}$, and the new $p$ evaluates to ${pv_new.v}$ at ${pv_new.u}$.\n\n'
    f'The third row is the registry run of [chapter 15](./wiring-and-registry.md#_6-consistency-for-the-registry), with the parent\'s fresh $w = {wr.W}$.')

rows_m = [
    (f'Left child\'s $m(W, {wr.X0}, {wr.Y0})$', f'$W = w = {wr.W}$', f'${ev(m_left, wr.W)}$', 'Enters the chain of restrictions'),
    (f'Right child\'s $m(W, {wr.X1}, {wr.Y1})$', f'$W = w = {wr.W}$', f'${ev(m_right, wr.W)}$', 'Enters the chain of restrictions'),
    (f'Parent\'s $m(W, {wr.X}, {wr.Y})$', f'$W = w = {wr.W}$', f'${ev(m_new, wr.W)}$', 'Closes the chain'),
    (f'Parent\'s $m(W, {wr.X}, {wr.Y})$', f'$W = \\omega^0 = {wr.OMEGA[0]}$', f'${ev(m_new, wr.OMEGA[0])}$', f'$s_A({wr.X}, {wr.Y})$, for the left child\'s circuit claim'),
    (f'Parent\'s $m(W, {wr.X}, {wr.Y})$', f'$W = \\omega^1 = {wr.OMEGA[1]}$', f'${ev(m_new, wr.OMEGA[1])}$', f'$s_B({wr.X}, {wr.Y})$, for the right child\'s circuit claim'),
]
assert ev(m_left, wr.W) == wr.m(wr.W, wr.X0, wr.Y0) and ev(m_right, wr.W) == wr.m(wr.W, wr.X1, wr.Y1)
assert ev(m_new, wr.W) == wr.m(wr.W, wr.X, wr.Y)
assert ev(m_new, 1) == wr.A.sxy(wr.X, wr.Y) and ev(m_new, Q - 1) == wr.B.sxy(wr.X, wr.Y)
frag['restriction-openings'] = table(['Polynomial', 'Opened at', 'Value', 'What the value is for'], rows_m)


if __name__ == '__main__':
    print(json.dumps(frag))
