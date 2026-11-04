"""Worked examples for scaling-zcash.md. Prints fragments as JSON.

Nothing here uses the toy curve, because the chapter has no proof machinery.
SHA-256 stands in for the real commitment and nullifier functions, and every
throughput figure is a hypothetical input chosen for the arithmetic.
"""
import hashlib
import json

frag = {}


def h(*parts):
    """A labelled stand-in hash, shortened so that it fits on the page."""
    return hashlib.sha256('|'.join(str(p) for p in parts).encode()).hexdigest()[:8]


def num(x):
    return f'{x:,}'


def gb(n_bytes):
    return f'{n_bytes / 10 ** 9:,.1f} GB'


# ---------------------------------------------------------------- toy ledger
notes = [
    ('Alice', 'nk-alice', 40, 'r1'),
    ('Bob', 'nk-bob', 25, 'r2'),
    ('Bob', 'nk-bob', 25, 'r3'),
]
cms = [h('cm', o, v, r) for o, _, v, r in notes]
nfs = [h('nf', nk, r) for _, nk, _, r in notes]
assert len(set(cms)) == 3 and len(set(nfs)) == 3
# The second and third notes have the same owner and value, yet look unrelated.
assert cms[1] != cms[2] and nfs[1] != nfs[2]
# Another key produces another nullifier, so a sender cannot predict this one.
wrong_key = h('nf', 'nk-carol', 'r2')
assert wrong_key != nfs[1]

frag['toy-pool'] = '\n'.join(
    ['| Note | Owner | Value | Commitment (public) | Nullifier (secret until spent) |', '| --- | --- | --- | --- | --- |']
    + [f'| {i} | {o} | {v} | `{cms[i]}` | `{nfs[i]}` |' for i, (o, _, v, _) in enumerate(notes)])

spent = set()
assert nfs[1] not in spent
spent.add(nfs[1])
assert nfs[1] in spent  # the second attempt is rejected
frag['toy-spend'] = (
    f'Suppose Bob spends note 1. He publishes the nullifier `{nfs[1]}` and proves in zero knowledge that it belongs '
    f'to some commitment in the list. The validators see that `{nfs[1]}` is new, accept the spend, and add it to the '
    f'nullifier set. If he tries again, the proof forces him to publish `{nfs[1]}` a second time, and the validators '
    f'reject it. An observer cannot match `{nfs[1]}` to `{cms[1]}` rather than to `{cms[0]}` or `{cms[2]}`, because '
    f'matching them requires Bob\'s key. Carol could not compute this nullifier either, since her key gives '
    f'`{wrong_key}` for the same note.')

# ----------------------------------------------------- hypothetical workload
TPS = 100
SPENDS, OUTPUTS = 2, 2
DAY, YEAR = 86_400, 365 * 86_400
NF_BYTES = 32
ORCHARD_ACTIONS = max(SPENDS, OUTPUTS)  # an Orchard action pairs a spend and an output
nf_rate = TPS * SPENDS
nf_bytes_per_s = nf_rate * NF_BYTES

frag['state-growth'] = '\n'.join([
    f'Take a hypothetical load of {TPS} transactions per second, each with {SPENDS} spends and {OUTPUTS} outputs. '
    f'These inputs are illustrative and do not forecast anything. Each spend adds one {NF_BYTES}-byte nullifier, so the '
    f'set grows by {num(nf_rate)} nullifiers per second. Counting only the raw bytes, with no index structure:',
    '',
    '| Elapsed time | Nullifiers | Raw size |', '| --- | --- | --- |',
    *[f'| {name} | {num(nf_rate * s)} | {gb(nf_bytes_per_s * s)} |'
      for name, s in [('1 day', DAY), ('1 year', YEAR), ('5 years', 5 * YEAR)]],
    '',
    'The last column has no ceiling, because no entry ever leaves the set.',
])

# -------------------------------------------------------------- wallet load
EPK, CMX = 32, 32
ENC, OUT = 580, 80
CV, RK = 32, 32
ACTION_BYTES = CV + NF_BYTES + RK + CMX + EPK + ENC + OUT
assert ACTION_BYTES == 820  # ZIP 225
COMPACT_CT = 52
COMPACT_OUTPUT = EPK + CMX + COMPACT_CT
assert COMPACT_OUTPUT == 116  # ZIP 307
COMPACT_ACTION = COMPACT_OUTPUT + NF_BYTES
action_rate = TPS * ORCHARD_ACTIONS

frag['wallet-load'] = '\n'.join([
    f'With the same hypothetical {TPS} transactions per second, Orchard-style pairing gives {ORCHARD_ACTIONS} actions per '
    f'transaction and {num(action_rate)} actions per second. A wallet attempts {num(action_rate * DAY)} trial decryptions '
    f'per day whether or not anyone has paid it.',
    '',
    '| What the wallet downloads | Bytes per action | Per day | After 30 days offline |', '| --- | --- | --- | --- |',
    f'| Full action | {ACTION_BYTES} | {gb(ACTION_BYTES * action_rate * DAY)} | {gb(ACTION_BYTES * action_rate * 30 * DAY)} |',
    f'| Compact form | {COMPACT_ACTION} | {gb(COMPACT_ACTION * action_rate * DAY)} | {gb(COMPACT_ACTION * action_rate * 30 * DAY)} |',
])

# --------------------------------------------------------------- epoch length
EPOCH_BLOCKS = 4096  # crates/tachyon/src/constants.rs at the pinned commit
BLOCK_SECONDS = 75  # ZIP 208
EPOCH_SECONDS = EPOCH_BLOCKS * BLOCK_SECONDS
frag['epoch-length'] = (
    f'At the current {BLOCK_SECONDS}-second block target, {num(EPOCH_BLOCKS)} blocks last '
    f'{num(EPOCH_SECONDS)} seconds, or about {EPOCH_SECONDS / DAY:.2f} days.')

# ------------------------------------------------------ evolving stand-in
nk, psi = 'nk-bob', 'psi-2'
mk = h('mk', nk, psi)
series = [(e, h('nfe', mk, e)) for e in range(5, 9)]
assert len({v for _, v in series}) == len(series)
frag['toy-evolving'] = '\n'.join(
    ['| Epoch $e$ | Stand-in $\\mathsf{nf}_e$ |', '| --- | --- |']
    + [f'| {e} | `{v}` |' for e, v in series])


# -------------------------------------------- double-spend enumeration
def nf(e):
    return ('nf', e)


def second_spend_accepted(t1, a1, t2, a2, pair, window, exclusion):
    """A note created in epoch 0 is spent twice. Is the second spend accepted?"""
    history = {}
    published = [nf(t1), nf(t1 + 1)] if pair else [nf(t1)]
    history.setdefault(a1, set()).update(published)
    candidate = [nf(t2), nf(t2 + 1)] if pair else [nf(t2)]
    if exclusion:
        # The stamp proves nf_j absent from all of epoch j, for each closed epoch before the target.
        if any(nf(j) in history.get(j, set()) for j in range(0, t2)):
            return False
    retained = set()
    for epoch in range(a2 - window + 1, a2 + 1):
        retained |= history.get(epoch, set())
    return not any(c in retained for c in candidate)


def scenarios(top=6):
    for t1 in range(1, top + 1):
        for a1 in (t1, t1 + 1):
            for t2 in range(1, top + 1):
                for a2 in (t2, t2 + 1):
                    if a2 >= a1:
                        yield t1, a1, t2, a2


cases = list(scenarios())
TOTAL = len(cases)


def uncaught(**rule):
    return [c for c in cases if second_spend_accepted(*c, **rule)]


full = uncaught(pair=True, window=2, exclusion=True)
single = uncaught(pair=False, window=2, exclusion=True)
short = uncaught(pair=True, window=1, exclusion=True)
no_excl = uncaught(pair=True, window=2, exclusion=False)
no_win = uncaught(pair=True, window=0, exclusion=True)
assert not full
assert single and short and no_excl and no_win
# The specific failures quoted in the chapter.
assert (5, 6, 6, 6) in single
assert (5, 5, 5, 6) in short
assert (2, 2, 5, 5) in no_excl
assert (5, 5, 5, 5) in no_win

frag['enumeration'] = '\n'.join([
    f'The script behind this chapter enumerates every pair of spends of one note created in epoch 0, with targets in '
    f'epochs 1 to 6 and each spend accepted during its target epoch or the next, which gives {TOTAL} scenarios. It models '
    f'nullifiers as labels and applies the rules above to the second spend. Each row below changes one rule.',
    '',
    '| Rule set | Double spends accepted | Example that gets through |', '| --- | --- | --- |',
    f'| Pair of nullifiers, two-epoch window, exclusion proof | {len(full)} of {TOTAL} | none |',
    f'| Publish only $\\mathsf{{nf}}_e$ | {len(single)} of {TOTAL} | target 5 accepted in epoch 6, then target 6 |',
    f'| Keep only the current epoch | {len(short)} of {TOTAL} | target 5 accepted in epoch 5, then target 5 accepted in epoch 6 |',
    f'| No exclusion proof | {len(no_excl)} of {TOTAL} | target 2, then target 5 three epochs later |',
    f'| No retained window | {len(no_win)} of {TOTAL} | target 5 twice in epoch 5 |',
])

# ---------------------------------------------------------- bounded window
TACHYON_ACTIONS = SPENDS + OUTPUTS
TG_PER_TX = 2 * TACHYON_ACTIONS + 1
assert TG_PER_TX == 9
tg_rate = TPS * TG_PER_TX
tg_bytes_per_s = tg_rate * NF_BYTES
window_peak = 2 * EPOCH_SECONDS * tg_bytes_per_s
crossover_days = window_peak / nf_bytes_per_s / DAY
assert 31 < crossover_days < 33
frag['window'] = '\n'.join([
    f'Return to the hypothetical {TPS} transactions per second. A Tachyon action is either a spend or an output, so each '
    f'transaction has {TACHYON_ACTIONS} actions and publishes ${TG_PER_TX} = 2 \\cdot {TACHYON_ACTIONS} + 1$ tachygrams. '
    f'The window holds at most two epochs of these, which is {num(2 * EPOCH_SECONDS)} seconds of traffic:',
    '',
    '| Elapsed time | Orchard-style nullifier set | Tachyon window (peak) |', '| --- | --- | --- |',
    *[f'| {name} | {gb(nf_bytes_per_s * s)} | {gb(min(tg_bytes_per_s * s, window_peak))} |'
      for name, s in [('1 week', 7 * DAY), ('1 month', 30 * DAY), ('1 year', YEAR), ('5 years', 5 * YEAR)]],
    '',
    f'For the first {crossover_days:.0f} days or so the window is the larger of the two, because it records more values per '
    f'transaction. After that the nullifier set keeps growing while the window stays where it is.',
])

# --------------------------------------------------------- on-chain bytes
SIG = 64
ORCHARD_PROOF_BASE, ORCHARD_PROOF_PER_ACTION = 2720, 2272
orch_actions = ORCHARD_ACTIONS * ACTION_BYTES
orch_sigs = ORCHARD_ACTIONS * SIG
orch_proof = ORCHARD_PROOF_BASE + ORCHARD_PROOF_PER_ACTION * ORCHARD_ACTIONS
orch_total = orch_actions + orch_sigs + orch_proof
ty_actions = TACHYON_ACTIONS * (CV + RK)
ty_sigs = TACHYON_ACTIONS * SIG
ty_grams = TG_PER_TX * NF_BYTES
ty_fee = 32
ty_total = ty_actions + ty_sigs + ty_grams + ty_fee
assert ty_total < orch_total
frag['chain-bytes'] = '\n'.join([
    f'| Component, for {SPENDS} spends and {OUTPUTS} outputs | Orchard bytes | Tachyon bytes |', '| --- | --- | --- |',
    f'| Action descriptions | ${ORCHARD_ACTIONS} \\cdot {ACTION_BYTES} = {num(orch_actions)}$ | ${TACHYON_ACTIONS} \\cdot {CV + RK} = {ty_actions}$ |',
    f'| Authorization signatures | ${ORCHARD_ACTIONS} \\cdot {SIG} = {orch_sigs}$ | ${TACHYON_ACTIONS} \\cdot {SIG} = {ty_sigs}$ |',
    f'| Published tachygrams | included in the actions | ${TG_PER_TX} \\cdot {NF_BYTES} = {ty_grams}$ |',
    f'| Maximum fee value commitment | none | {ty_fee} |',
    f'| Proof | ${ORCHARD_PROOF_BASE} + {ORCHARD_PROOF_PER_ACTION} \\cdot {ORCHARD_ACTIONS} = {num(orch_proof)}$ | a share of one aggregate proof |',
    f'| Total without the shared proof | {num(orch_total)} | {num(ty_total)} |',
])

print(json.dumps(frag))
