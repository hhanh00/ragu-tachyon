"""Slides for chapter twenty-five, Final Recap.

Every label comes from audio/scripts/25-recap.txt or docs/recap.md. The
chapter adds no protocol content and no new numbers; the epochs (3 to 8) are
those of the running spend in docs/proof-tree.md.

Colors: BLUE for data (notes, commitments, tachygrams, headers), TEAL for
proofs and checks that pass, ORANGE for the party or step under discussion,
PURPLE for Ragu-specific material, RED only for failure, a blocked double
spend, or something missing from the code, MUTED for context.
"""
from manim import *

from engine import *

STEM = "25-recap"
deck = Deck(f"scripts/{STEM}.txt")
slide = deck.slide

PROV = "Reconstructed from code at the commit this site pins, not confirmed by the authors."


def at(mob, x, y):
    return mob.move_to([x, y, 0])


def lft(mob, x, y):
    """Place a mobject with its left edge at x."""
    return mob.move_to([x + mob.width / 2, y, 0])


def pts(first, title, items, sub=None, chars=56, size=32, y=None, gap=0.42, dot=BLUE):
    """A slide whose points arrive one at a time."""
    @slide(first, title, sub)
    def build(s):
        rows = bullets(items, chars, size, gap=gap, dot=dot)
        rows.move_to([-7.0 + rows.width / 2, 0 if y is None else y, 0])
        for row in rows:
            yield [FadeIn(row, shift=RIGHT * 0.15)]
    return build


# ------------------------------------------------------------------ the journey
JOURNEY = [("note", BLUE), ("pool", BLUE), ("sync service", ORANGE), ("proof tree", TEAL),
           ("aggregator\nand miner", ORANGE), ("block", TEAL)]


def journey(y=0.3, w=2.05, h=1.25, size=24):
    boxes = VGroup(*[card(t, w, h, c, size) for t, c in JOURNEY]).arrange(RIGHT, buff=0.42)
    at(boxes, 0, y)
    arrows = [arrow(a, b, buff=0.06) for a, b in zip(boxes, boxes[1:])]
    return boxes, arrows


# ------------------------------------------------------------------ opening
deck.part("Chapter twenty-five")


@slide("Chapter twenty-five.", "Final Recap")
def opening(s):
    boxes, arrows = journey()
    yield [FadeIn(boxes[0], shift=UP * 0.2)]
    yield [LaggedStart(*[AnimationGroup(GrowArrow(a), FadeIn(b)) for a, b in zip(arrows, boxes[1:])], lag_ratio=0.35)]


@slide("This chapter follows one spend", "One spend, and the chapter for each part")
def follows(s):
    boxes, arrows = journey(y=0.9)
    s.add(boxes, *arrows)
    tags = ["20", "21", "22", "23", "24", "21, 24"]
    chips = VGroup(*[at(chip("ch " + t, MUTED, size=20), b.get_x(), -0.3) for t, b in zip(tags, boxes)])
    yield [LaggedStart(*[FadeIn(c, shift=UP * 0.15) for c in chips], lag_ratio=0.15)]
    yield [FadeIn(at(T("no new protocol content", 30, ORANGE, True), 0, -1.6))]
    yield [FadeIn(caption("Derivations, numbers, and the arguments about cheating stay in the chapters named.", y=-2.6, color=INK, size=28, chars=70))]


@slide("Tachyon has not activated on mainnet", "The status of this design")
def status(s):
    t = at(card("Tachyon\nat the pinned commit", 4.2, 1.5, BLUE, 26), -4.6, 1.0)
    r = at(card("Ragu\nat the pinned commit", 4.2, 1.5, PURPLE, 26), 0.2, 1.0)
    r2 = at(card("Ragu\nat the commit Tachyon pins", 4.2, 1.5, MUTED, 26), 5.0, 1.0)
    yield [FadeIn(at(T("not activated on mainnet; design still changing", 27, MUTED), 0, 2.3)), FadeIn(t), FadeIn(r)]
    pin = CurvedArrow(t.get_bottom() + DOWN * 0.05, r2.get_bottom() + DOWN * 0.05, angle=PI / 5, color=MUTED, stroke_width=3)
    yield [FadeIn(r2), Create(pin), FadeIn(at(T("Tachyon itself pins a different commit", 23, MUTED), 2.6, -0.85))]
    miss = VGroup(chip("real Tachyon circuits", RED, size=24), chip("validator", RED, size=24)).arrange(RIGHT, buff=0.6)
    at(miss, 0, -1.75)
    yield [FadeIn(miss), *[Create(strike(m)) for m in miss]]
    yield [FadeIn(caption("A step that checks something means what the design asks for. A later section separates what exists from what does not.", y=-3.0, color=INK, size=27, chars=72))]


# ------------------------------------------------------------------ the spend
deck.part("The spend we follow")


def people(y=0.6):
    bob = at(card("Bob", 2.2, 1.0, MUTED, 28), -5.4, y)
    alice = at(card("Alice", 2.2, 1.0, ORANGE, 28), 0, y)
    carol = at(card("Carol", 2.2, 1.0, MUTED, 28), 5.4, y)
    return bob, alice, carol


@slide("The spend we follow.", "Alice's spend")
def spend(s):
    bob, alice, carol = people()
    note = at(chip("note", BLUE, size=26), -2.7, 1.25)
    yield [FadeIn(bob), FadeIn(alice), GrowArrow(arrow(bob, alice)), FadeIn(note)]
    ep = at(VGroup(chip("created in epoch 3", BLUE, size=24), chip("target epoch 7", ORANGE, size=24)).arrange(RIGHT, buff=0.5), -1.5, -0.7)
    yield [FadeIn(ep)]
    out = at(chip("one output", BLUE, size=24), 2.7, 1.25)
    st = at(pill("published stamp", TEAL, 26), 0, -2.2)
    yield [FadeIn(carol), GrowArrow(arrow(alice, carol)), FadeIn(out), FadeIn(st),
           FadeIn(at(T("one spend, one output", 26, MUTED), 4.6, -0.7))]


@slide("Most of the values in those chapters", "Where the numbers live")
def values(s):
    a = at(card("Proof tree chapter\nAlice's bundle", 5.4, 1.7, BLUE, 28), -3.7, 0.9)
    b = at(card("Aggregation chapter\nbundle Y", 5.4, 1.7, BLUE, 28), 3.7, 0.9)
    yield [FadeIn(a), FadeIn(at(W("most values: stand-in hashes, not real Poseidon outputs", 30, 25, MUTED, align=ORIGIN), -3.7, -0.55))]
    yield [FadeIn(b), FadeIn(at(T("also one spend and one output", 25, MUTED), 3.7, -0.55))]
    yield [GrowArrow(arrow(b, a, color=ORANGE)), FadeIn(at(T("Y stands in for Alice's bundle", 28, ORANGE, True), 0, -2.2))]


@slide("Most of this chapter follows the spend", "The route through this chapter")
def route(s):
    a = at(card("Follow the spend\nthrough Tachyon", 4.4, 1.7, BLUE, 28), -4.8, 0.2)
    b = at(card("Pause at one node:\nthe proof system", 4.4, 1.7, PURPLE, 28), 0, 0.2)
    c = at(card("Every layer\nwith its chapter", 4.4, 1.7, TEAL, 28), 4.8, 0.2)
    yield [FadeIn(a, shift=UP * 0.2)]
    yield [FadeIn(b, shift=UP * 0.2), FadeIn(c, shift=UP * 0.2)]


# ------------------------------------------------------------------ keys and note
deck.part("The note reaches Alice")


@slide("The note reaches Alice.", "Alice's keys")
def keys(s):
    sk = at(chip("spending key", ORANGE, size=28, h=0.75), -4.6, 1.2)
    ask = at(chip("ask: authorize spends", BLUE, size=24), 0.6, 1.9)
    nk = at(chip("nk: derive nullifiers", BLUE, size=24), 0.6, 0.5)
    yield [FadeIn(sk), GrowArrow(arrow(sk, ask)), GrowArrow(arrow(sk, nk)), FadeIn(ask), FadeIn(nk)]
    pk = at(chip("payment key = hash(ak, nk)", TEAL, size=26, h=0.7), 0.6, -1.1)
    bob = at(card("Bob", 2.0, 0.9, MUTED, 26), 5.8, -1.1)
    yield [FadeIn(pk), GrowArrow(arrow(pk, bob)), FadeIn(bob)]
    yield [FadeIn(caption("Bob can name Alice as the owner without learning nk.", y=-2.6, color=INK, size=29))]


@slide("Bob then forms the note", "The note and its commitment")
def note(s):
    fields = VGroup(*[chip(t, BLUE, size=26) for t in ("pk", "v", "ψ", "rcm")]).arrange(RIGHT, buff=0.25)
    at(fields, -3.2, 1.4)
    cm = at(chip("cm", BLUE, size=30, h=0.75), 4.2, 1.4)
    yield [FadeIn(fields), GrowArrow(arrow(fields, cm)), FadeIn(cm)]
    pay = at(card("payment protocol outside\nthe shielded protocol", 5.6, 1.4, ORANGE, 26), -3.2, -0.6)
    yield [FadeIn(pay), GrowArrow(arrow(pay.get_top(), fields.get_bottom(), color=ORANGE)),
           FadeIn(at(T("no trial decryption of all traffic", 26, TEAL), 3.4, -0.6))]
    warn = at(T("a sender who reuses ψ can make one of her notes unspendable", 27, RED), 0, -2.3)
    yield [Indicate(fields[2], color=RED, scale_factor=1.3), FadeIn(warn),
           FadeIn(at(T("so her wallet compares the note against her others", 25, MUTED), 0, -2.95))]


# ------------------------------------------------------------------ pool
deck.part("The pool records the commitment")


@slide("The pool records the commitment.", "The commitment becomes a tachygram")
def tachygram(s):
    stamp = at(card("Bob's stamp", 3.2, 1.3, TEAL, 28), -4.8, 0.8)
    tg = at(chip("tachygram: cm", BLUE, size=26, h=0.7), 0.2, 0.8)
    yield [FadeIn(stamp), GrowArrow(arrow(stamp, tg)), FadeIn(tg)]
    yield [FadeIn(at(T("one kind of value for commitments and nullifiers", 26, MUTED), 0.2, -0.3))]
    val = at(card("validators\neventually forget", 3.4, 1.3, MUTED, 26), -4.6, -1.9)
    ref = at(card("short reference\nkept by the pool", 3.4, 1.3, BLUE, 26), 4.6, -1.9)
    yield [FadeIn(val), FadeIn(ref), FadeIn(at(T("Alice proves facts later", 25, ORANGE), 0, -1.9))]


@slide("The stamp's tachygrams become", "From a set to the anchor")
def chainslide(s):
    roots = at(chip("roots of a polynomial", BLUE, size=24), -5.3, 0.9)
    pt = at(chip("one point", BLUE, size=24), -1.4, 0.9)
    hc = at(card("Poseidon\nhash chain", 2.8, 1.3, TEAL, 26), 2.0, 0.9)
    ep = at(chip("block's epoch", MUTED, size=22), 2.0, -0.6)
    yield [FadeIn(roots), GrowArrow(arrow(roots, pt)), FadeIn(pt),
           FadeIn(at(T("Pedersen", 22, MUTED), -3.25, 1.4))]
    yield [GrowArrow(arrow(pt, hc)), FadeIn(hc), FadeIn(ep), GrowArrow(arrow(ep, hc))]
    bd = at(chip("boundary digest", ORANGE, size=22), 5.5, 0.9)
    yield [GrowArrow(arrow(hc, bd)), FadeIn(bd), FadeIn(at(W("joins each epoch to the next", 16, 24, MUTED, align=ORIGIN), 5.5, -0.15))]


@slide("The chain's state is the anchor", "Anchors pin history")
def anchors(s):
    xs = [-5.6, -2.8, 0, 2.8]
    st = [at(chip("anchor", BLUE, size=24), x, 0.6) for x in xs]
    arr = [arrow(a, b, buff=0.08) for a, b in zip(st, st[1:])]
    yield [LaggedStart(*[FadeIn(c) for c in st], lag_ratio=0.15), *[GrowArrow(a) for a in arr]]
    yield [FadeIn(at(T("the proof tree chapter lists the anchors this note lives through", 25, MUTED), 0, 1.7))]
    check_ = at(card("one consensus\ncheck", 2.6, 1.2, TEAL, 24), 5.9, 0.6)
    brace = Brace(VGroup(*st[:3]), DOWN, color=ORANGE)
    yield [FadeIn(check_), GrowArrow(arrow(st[3], check_, color=TEAL)),
           FadeIn(brace), FadeIn(at(T("witnessed freely by the proof", 26, ORANGE), st[1].get_x(), -0.75))]
    yield [FadeIn(caption("The check at the far end pins every earlier state.", y=-2.2, color=INK, size=29))]


# ------------------------------------------------------------------ obligations
deck.part("What the spend has to show")

EPOCHS = [3, 4, 5, 6, 7, 8]


def epoch_row(y=0.9):
    boxes = VGroup(*[card(f"epoch {e}", 1.95, 0.95, MUTED, 24) for e in EPOCHS]).arrange(RIGHT, buff=0.25)
    return at(boxes, 0, y)


@slide("What the spend has to show.", "A nullifier for every epoch")
def nullifiers(s):
    boxes = epoch_row(y=0.5)
    mk = at(chip("mk + sponge", ORANGE, size=26), 0, 2.1)
    nfs = VGroup(*[at(chip(f"nf{e}", BLUE, size=22), b.get_x(), -0.6) for e, b in zip(EPOCHS, boxes)])
    yield [FadeIn(mk), FadeIn(boxes), LaggedStart(*[FadeIn(n, shift=DOWN * 0.15) for n in nfs], lag_ratio=0.1)]
    yield [FadeIn(at(T("the note's commitment pins them: no choice", 27, TEAL), 0, -1.5))]
    win = SurroundingRectangle(VGroup(boxes[4], boxes[5]), color=ORANGE, buff=0.12, corner_radius=0.12)
    yield [Create(win), FadeIn(at(T("validators hold only two epochs", 27, ORANGE, True), 3.2, -2.5))]


@slide("For each of the closed epochs", "Two kinds of obligation")
def obligations(s):
    boxes = epoch_row(y=0.5)
    s.add(boxes)
    nfs = VGroup(*[at(chip(f"nf{e}", BLUE, size=22), b.get_x(), -0.6) for e, b in zip(EPOCHS, boxes)])
    s.add(nfs)
    closed = SurroundingRectangle(VGroup(*boxes[:4]), color=TEAL, buff=0.12, corner_radius=0.12)
    yield [Create(closed), FadeIn(at(T("prove absent from its own epoch", 27, TEAL, True), closed.get_x(), 1.55))]
    win = SurroundingRectangle(VGroup(boxes[4], boxes[5], nfs[4], nfs[5]), color=ORANGE, buff=0.12, corner_radius=0.12)
    yield [Create(win), FadeIn(at(T("publish both", 27, ORANGE, True), win.get_x(), 1.55)),
           nfs[4][0].animate.set_stroke(ORANGE, 3), nfs[5][0].animate.set_stroke(ORANGE, 3)]


@slide("The spend might land", "Why publish the pair")
def pair(s):
    boxes = epoch_row(y=0.5)
    s.add(boxes)
    nf7 = at(chip("nf7", ORANGE, size=24), boxes[4].get_x(), -0.6)
    nf8 = at(chip("nf8", ORANGE, size=24), boxes[5].get_x(), -0.6)
    s.add(nf7, nf8)
    yield [Indicate(boxes[4], color=ORANGE), Indicate(boxes[5], color=ORANGE),
           FadeIn(at(T("lands in epoch 7 or epoch 8", 27, INK), 0, 1.7))]
    yield [FadeIn(caption("A spend accepted in either epoch puts that epoch's nullifier there, where a later test will find it.", y=-1.8, color=INK, size=28, chars=64))]
    yield [FadeIn(at(T("no claim about epoch 7 in the proof: the window covers it", 26, MUTED), 0, -3.2))]


# ------------------------------------------------------------------ sync
deck.part("The sync service tests old nullifiers")


@slide("The sync service tests old nullifiers.", "Handing the work to a service")
def handoff(s):
    w = at(card("Alice's\nwallet", 2.8, 1.4, ORANGE, 28), -5.2, 0.6)
    sv = at(card("sync\nservice", 2.8, 1.4, MUTED, 28), 5.2, 0.6)
    yield [FadeIn(w), FadeIn(at(T("testing absence means reading whole epochs", 27, MUTED), 0, 2.2))]
    req = at(VGroup(*[chip(f"nf{e}", BLUE, size=22) for e in (3, 4, 5, 6)]).arrange(RIGHT, buff=0.18), 0, 0.6)
    yield [FadeIn(sv), FadeIn(req), GrowArrow(arrow(w, req)), GrowArrow(arrow(req, sv)),
           FadeIn(at(T("each epoch's value is unrelated to the others", 25, TEAL), 0, -0.3))]
    kept = at(VGroup(chip("nf7", RED, size=22), chip("nf8", RED, size=22)).arrange(RIGHT, buff=0.18), -5.2, -1.7)
    yield [FadeIn(kept), FadeIn(at(T("explicit values, no key; nf7 and nf8 never leave the wallet", 26, INK), 1.4, -1.7))]


@slide("An epoch's polynomial is too large", "Buckets cover the epoch")
def buckets(s):
    ep = at(card("one epoch's tachygrams\ntoo large to open directly", 4.8, 1.5, BLUE, 25), -4.6, 0.5)
    bs = VGroup(*[card(f"bucket", 1.8, 0.9, BLUE, 24) for _ in range(4)]).arrange(DOWN, buff=0.18)
    at(bs, 2.0, 0.2)
    yield [FadeIn(ep)]
    yield [LaggedStart(*[GrowArrow(arrow(ep.get_right(), b.get_left(), buff=0.1)) for b in bs], lag_ratio=0.1), FadeIn(bs),
           FadeIn(at(T("routed by quadratic-\nresidue profile", 23, MUTED), -1.0, -1.4))]
    seal = VGroup(*[at(chip("seal", TEAL, size=20), 3.6, b.get_y()) for b in bs])
    yield [FadeIn(seal), FadeIn(at(W("each seal computes the crossing, so it covers the whole epoch", 22, 24, TEAL), 6.0, 0.2))]


@slide("The service opens the matching bucket", "A segment that names no note")
def segment(s):
    b = at(card("matching bucket", 3.4, 1.1, BLUE, 26), -4.8, 0.9)
    v = at(chip("nf", BLUE, size=24), -4.8, 2.1)
    seg = at(card("segment\nArbitraryUnspent", 4.0, 1.4, TEAL, 26), 1.5, 0.9)
    yield [FadeIn(b), FadeIn(v), GrowArrow(arrow(v, b)), GrowArrow(arrow(b, seg)), FadeIn(seg),
           FadeIn(at(T("names no note", 26, MUTED), 5.4, 0.9))]
    a = at(card("proof tree chapter\nall four epochs, one bucket each", 6.2, 1.4, MUTED, 25), -3.5, -1.3)
    c = at(card("oblivious sync chapter\na narrower range", 6.2, 1.4, MUTED, 25), 3.5, -1.3)
    yield [FadeIn(a), FadeIn(c)]
    yield [FadeIn(caption("Both are choices of example, and a wallet may run these steps itself.", y=-3.0, color=INK, size=28))]


# ------------------------------------------------------------------ proof tree
deck.part("The wallet builds the proof tree")

TREE = [
    ("NoteSeed", -5.4, 1.75), ("NullifierDerive", -1.8, 1.75), ("UnspentBind", 1.8, 1.75), ("QrSpendableInit", 5.4, 1.75),
    ("SpendableLift", 5.4, 0.2), ("SpendBind", 1.8, 0.2), ("SpendAction", -1.8, 0.2), ("OutputBind +\nOutputAction", -5.4, 0.2),
    ("ActionLift +\nActionMerge", -3.6, -1.35), ("FeeFuse", 0, -1.35), ("StampLift", 3.6, -1.35),
]
EDGES = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 8), (7, 8), (8, 9), (9, 10)]


def tree_boxes(color=BLUE):
    return [at(card(n, 3.1, 0.95, color, 23), x, y) for n, x, y in TREE]


def tree_slide(first, title, old, new, cap, sub=None):
    @slide(first, title, sub)
    def build(s):
        old_boxes = tree_boxes(BLUE)
        new_boxes = tree_boxes(ORANGE)
        s.add(*[old_boxes[i] for i in old])
        s.add(*[arrow(old_boxes[a], old_boxes[b], buff=0.06) for a, b in EDGES if a in old and b in old])
        for group in new:
            anims = []
            for i in group:
                anims.append(FadeIn(new_boxes[i], shift=UP * 0.15))
                for a, b in EDGES:
                    if b == i and (a in old or any(a in g for g in new[:new.index(group) + 1])):
                        anims.append(GrowArrow(arrow(new_boxes[a], new_boxes[b], buff=0.06)))
            yield anims
        yield [FadeIn(caption(cap, y=-3.0, color=INK, size=27, chars=72))]
    return build


tree_slide("The wallet builds the proof tree.", "From note to stamp, one step at a time", [], [[0], [1]],
           "NoteSeed pairs cm with mk. NullifierDerive commits a window of (epoch, nullifier) pairs as a product of irreducible cubic factors.")
tree_slide("Second, Unspent Bind", "The service's work joins the note", [0, 1], [[2]],
           "UnspentBind divides the service's polynomial out of the window, with a factor that carries its epoch.")
tree_slide("Third, QR Spendable Init", "Into the window and the spend", [0, 1, 2], [[3], [4], [5, 6]],
           "Test of epoch 3 and cm in its bucket; lift to the entry anchor of epoch 7; nf7, nf8, value commitment, rk, actions.")
tree_slide("Fifth, Output Bind", "Carol's output joins the spend", [0, 1, 2, 3, 4, 5, 6], [[7], [8]],
           "The output has the same header type and two tachygrams. The two actions move to one anchor and combine.")
tree_slide("Seventh, Fee Fuse", "Fee, stamp, and a later anchor", [0, 1, 2, 3, 4, 5, 6, 7, 8], [[9], [10]],
           "FeeFuse applies a fee chosen after signing and turns Actions into a Stamp exactly once. StampLift moves it within epoch 7.")


@slide("The whole tree appears in chapter twenty-three", "Two facts outside the proof")
def outside(s):
    yield [FadeIn(at(T("the exact mix of steps is chapter 23's own reconstruction", 27, MUTED), 0, 2.2))]
    sig = at(card("signature under rk\nneeds ask", 4.8, 1.6, ORANGE, 28), -3.6, 0.5)
    dev = at(VGroup(card("custody device\nholds the key", 3.3, 1.2, MUTED, 24), card("another device\nproves", 3.3, 1.2, MUTED, 24)).arrange(RIGHT, buff=0.3), -3.6, -1.6)
    yield [FadeIn(sig), FadeIn(dev), GrowArrow(arrow(sig, dev))]
    bind = at(card("binding signature\nthe bundle balances", 4.8, 1.6, TEAL, 28), 3.8, 0.5)
    yield [FadeIn(bind), FadeIn(at(T("no step adds up values", 26, MUTED), 3.8, -1.0))]


# ------------------------------------------------------------------ one fuse
deck.part("What one fuse proves")


@slide("What one fuse proves.", "One node, one call to fuse")
def fuse(s):
    c1 = at(VGroup(chip("header", BLUE, size=22), pill("proof", TEAL, 22)).arrange(RIGHT, buff=0.15), -5.0, 1.3)
    c2 = at(VGroup(chip("header", BLUE, size=22), pill("proof", TEAL, 22)).arrange(RIGHT, buff=0.15), -5.0, -0.5)
    f = at(card("fuse\nruns the step", 3.0, 1.6, PURPLE, 28), 0, 0.4)
    out = at(VGroup(chip("header", BLUE, size=24), pill("proof", TEAL, 24)).arrange(RIGHT, buff=0.15), 4.8, 0.4)
    yield [FadeIn(c1), FadeIn(c2), FadeIn(f), GrowArrow(arrow(c1, f)), GrowArrow(arrow(c2, f))]
    yield [GrowArrow(arrow(f, out)), FadeIn(out)]
    yield [f[1].animate.set_color(ORANGE), FadeIn(at(T("take SpendBind as the node", 28, ORANGE, True), 0, -2.0))]


def flow(items, y, w=2.9, h=1.3, size=24, buff=0.45):
    boxes = VGroup(*[card(t, w, h, c, size) for t, c in items]).arrange(RIGHT, buff=buff)
    at(boxes, 0, y)
    return boxes, [arrow(a, b, buff=0.06) for a, b in zip(boxes, boxes[1:])]


@slide("Its step first becomes gates", "The step as one equation")
def equation(s):
    boxes, arrs = flow([("gates and linear\nconstraints", BLUE), ("one consolidated\nequation", BLUE),
                        ("one coefficient of\na polynomial product", PURPLE)], y=0.8, w=4.0)
    yield [FadeIn(boxes[0])]
    yield [GrowArrow(arrs[0]), FadeIn(boxes[1]), FadeIn(at(T("random powers", 22, MUTED), arrs[0].get_x(), 1.8))]
    alt = at(card("QAP: quotient by a\nvanishing polynomial", 4.0, 1.3, MUTED, 24), boxes[2].get_x(), -1.2)
    yield [GrowArrow(arrs[1]), FadeIn(boxes[2]), FadeIn(at(T("Ragu", 24, PURPLE, True), boxes[2].get_x(), 1.85))]
    yield [FadeIn(alt), FadeIn(at(T("where a QAP would use", 24, MUTED), 0.4, -1.2))]


@slide("The prover commits to its polynomials", "The parts of one proof")
def parts(s):
    boxes, arrs = flow([("commit to\npolynomials", BLUE), ("batch claims\ninto one", BLUE), ("inner product\nargument opens", BLUE),
                        ("Fiat–Shamir", TEAL)], y=0.8, w=3.0, buff=0.55)
    yield [FadeIn(boxes[0]), GrowArrow(arrs[0]), FadeIn(boxes[1]), GrowArrow(arrs[1]), FadeIn(boxes[2])]
    whole = at(card("one complete proof (chapter 9)", 6.4, 1.1, TEAL, 28), 0, -1.4)
    yield [GrowArrow(arrs[2]), FadeIn(boxes[3]), FadeIn(at(T("no interaction", 22, MUTED), boxes[3].get_x(), -0.25))]
    yield [FadeIn(whole), GrowArrow(arrow(VGroup(boxes).get_bottom() + DOWN * 0.45, whole.get_top(), buff=0.05))]


@slide("That proof leaves the verifier", "Two linear costs")
def costs(s):
    v = at(card("verifier", 3.0, 1.2, TEAL, 28), -4.8, 0.8)
    a = at(chip("s(x, y)", ORANGE, size=28), -0.8, 1.5)
    b = at(chip("Ĝ", ORANGE, size=28), -0.8, 0.1)
    yield [FadeIn(v), FadeIn(a), FadeIn(b), GrowArrow(arrow(v, a)), GrowArrow(arrow(v, b)),
           FadeIn(at(T("wiring value", 22, MUTED), 1.4, 1.5)), FadeIn(at(T("combined generator", 22, MUTED), 1.75, 0.1))]
    circ = at(card("node's circuit\nverifies its children", 4.2, 1.4, PURPLE, 24), 4.8, -1.4)
    x = at(cross(Square(0.45), width=6), 2.2, -1.4)
    yield [FadeIn(circ), Create(x), FadeIn(at(T("these costs block this", 25, RED), 4.8, -2.5))]
    yield [FadeIn(caption("So the rest of the proof system moves that work out of the circuit, with the checks that read whole vectors.", y=-3.3, color=INK, size=26, chars=76))]


MOVES = [("Ĝ", "accumulation, split: no inner product argument in a fuse"),
         ("product claims", "revdot folding carries them forward"),
         ("s(x, y)", "registry: one polynomial holding every circuit"),
         ("other curve's points", "Pasta cycle handles them natively"),
         ("challenges", "endoscalars carry them across"),
         ("shared data", "stages")]


def move_rows(y0=1.9, dy=0.88):
    rows = []
    for k, (left, right) in enumerate(MOVES):
        y = y0 - k * dy
        l = lft(chip(left, ORANGE, size=24), -7.1, y)
        r = lft(T(right, 25, INK), -2.0, y)
        a = arrow([l.get_right()[0] + 0.12, y, 0], [-2.12, y, 0], color=PURPLE, buff=0)
        rows.append(VGroup(l, a, r))
    return rows


@slide("Accumulation turns G hat into a claim", "Moving work out of the circuit")
def moves1(s):
    rows = move_rows()
    yield [FadeIn(rows[0], shift=RIGHT * 0.15)]
    yield [FadeIn(rows[1], shift=RIGHT * 0.15)]


@slide("The registry replaces s of x and y", "Moving work out of the circuit")
def moves2(s):
    rows = move_rows()
    s.add(rows[0], rows[1])
    yield [FadeIn(rows[2], shift=RIGHT * 0.15), FadeIn(lft(T("a node pays only for the step it chooses", 23, MUTED), -2.0, rows[2].get_y() - 0.43))]
    yield [LaggedStart(*[FadeIn(r, shift=RIGHT * 0.15) for r in rows[3:]], lag_ratio=0.3)]


def acc_group(color=PURPLE, size=20):
    sides = VGroup(*[VGroup(*[Square(0.34, color=color, fill_color=color, fill_opacity=0.25, stroke_width=2) for _ in range(3)]).arrange(RIGHT, buff=0.08)
                     for _ in range(2)]).arrange(RIGHT, buff=0.3)
    return sides


@slide("Chapter eighteen, on recursion in Ragu, assembles", "Three accumulators per side")
def accs(s):
    yield [FadeIn(at(T("many small internal circuits", 27, PURPLE), 0, 2.2))]
    kids = []
    for x in (-3.6, 3.6):
        p = at(card(None, 3.6, 1.6, TEAL), x, -1.6)
        g = at(acc_group(), x, -1.6)
        kids.append(VGroup(p, g))
    par = VGroup(at(card(None, 3.6, 1.6, TEAL), 0, 0.8), at(acc_group(), 0, 0.8))
    g0 = kids[0][1]
    labels = VGroup(T("side one", 22, MUTED).next_to(kids[0], DOWN, buff=0.12).set_x(g0[0].get_x()),
                    T("side two", 22, MUTED).next_to(kids[0], DOWN, buff=0.12).set_x(g0[1].get_x()))
    yield [*[FadeIn(k) for k in kids], FadeIn(labels)]
    yield [*[GrowArrow(arrow(k, par)) for k in kids], FadeIn(par),
           FadeIn(at(T("two of each become one", 26, ORANGE, True), 4.6, 0.8))]
    yield [FadeIn(caption("SpendBind's proof has the same shape as the proof at the top.", y=-3.5, color=INK, size=27))]


@slide("A proof that leaves the tree", "Compression")
def compression(s):
    big = at(card("proof from\nthe tree", 3.0, 1.8, PURPLE, 26), -5.4, 0.6)
    small = at(VGroup(chip("commitments", BLUE, size=22), chip("a few values", BLUE, size=22),
                      chip("IPA on each curve", TEAL, size=22)).arrange(DOWN, buff=0.18), -0.4, 0.6)
    yield [FadeIn(big), GrowArrow(arrow(big, small)), FadeIn(small),
           FadeIn(at(T("compression", 24, PURPLE, True), -2.9, 1.9))]
    v = at(card("verifier pays the deferred\nlinear costs once", 4.4, 1.6, TEAL, 24), 5.0, 0.6)
    yield [GrowArrow(arrow(small, v)), FadeIn(v)]
    yield [FadeIn(caption("Chapter 19, on compression, gives the size of the result.", y=-2.4, color=MUTED, size=27))]


# ------------------------------------------------------------------ to a block
deck.part("From the stamp to a block")


@slide("From the stamp to a block.", "The bundle on the wire")
def wire(s):
    body = at(card("effecting data", 6.0, 1.2, BLUE, 28), -2.4, 0.9)
    trailer = at(card("trailer: stamp", 3.6, 1.2, TEAL, 28), 3.0, 0.9)
    yield [FadeIn(body), FadeIn(trailer), FadeIn(at(T("autonome: Alice's bundle as she publishes it", 26, MUTED), 0, 2.2))]
    sig = at(Brace(body, DOWN, color=ORANGE), body.get_x(), -0.1)
    yield [FadeIn(sig), FadeIn(at(T("signatures cover this", 26, ORANGE, True), body.get_x(), -0.7)),
           Indicate(trailer, color=TEAL), FadeIn(at(T("can change", 26, TEAL), 3.0, -0.4))]
    yield [FadeIn(caption("A miner could include it as it stands, and a validator would rebuild its header from published data.", y=-2.5, color=INK, size=27, chars=72))]


@slide("An aggregator may instead merge it", "Merging stamps")
def merge(s):
    ins = VGroup(*[chip(t, BLUE if i else ORANGE, size=22) for i, t in enumerate(("Alice's stamp", "stamp", "stamp"))]).arrange(DOWN, buff=0.3)
    at(ins, -5.2, 0.6)
    agg = at(card("aggregator\none anchor, disjoint", 4.0, 1.5, ORANGE, 25), 0, 0.6)
    out = at(pill("aggregate stamp", TEAL, 24), 4.9, 0.6)
    yield [FadeIn(ins), FadeIn(agg), *[GrowArrow(arrow(i.get_right(), agg.get_left(), buff=0.1)) for i in ins],
           GrowArrow(arrow(agg, out)), FadeIn(out)]
    yield [FadeIn(at(T("needs none of Alice's secrets: reads only commitments and published values", 24, MUTED), 0, -1.0))]
    yield [FadeIn(caption("If a block mines one input first, StampUnmerge divides it out.", y=-2.4, color=INK, size=28))]


@slide("A miner then strips each covered bundle", "Stripping")
def strip(s):
    before = at(VGroup(card("body", 2.2, 1.0, BLUE, 26), card("fee", 1.6, 1.0, BLUE, 26), card("stamp", 2.0, 1.0, TEAL, 26)).arrange(RIGHT, buff=0.12), -3.6, 1.0)
    yield [FadeIn(before)]
    after = at(VGroup(card("body", 2.2, 1.0, BLUE, 26), card("fee", 1.6, 1.0, BLUE, 26), card("→ aggregate's wtxid", 3.6, 1.0, ORANGE, 24)).arrange(RIGHT, buff=0.12), 2.6, -0.6)
    yield [GrowArrow(arrow(before.get_bottom(), after.get_left() + LEFT * 0.05, color=MUTED)), FadeIn(after), Create(strike(before[2]))]
    tx = at(chip("txid: stable", TEAL, size=26), -3.6, -2.2)
    yield [FadeIn(tx), FadeIn(at(T("Alice's wallet still recognizes the bundle", 26, INK), 2.0, -2.2))]


CHECKS = ["signatures", "pointers", "coverage", "tachygram count", "set commitment", "proof"]
RULES = ["look up the anchor", "epoch current or preceding", "each tachygram against the window", "absorb the commitment"]


@slide("The block's validators then check", "Checks on the aggregate and consensus rules", PROV)
def block_checks(s):
    a = VGroup(*[VGroup(check(size=0.3), T(c, 26, INK)).arrange(RIGHT, buff=0.2) for c in CHECKS]).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
    b = VGroup(*[VGroup(check(size=0.3), T(c, 26, INK)).arrange(RIGHT, buff=0.2) for c in RULES]).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
    lft(a, -6.8, 0)
    lft(b, 0.4, 0)
    a.align_to([0, 1.3, 0], UP)
    b.align_to([0, 1.3, 0], UP)
    yield [FadeIn(lft(T("checks on the aggregate", 27, TEAL, True), -6.8, 1.9)), LaggedStart(*[FadeIn(r) for r in a], lag_ratio=0.15)]
    yield [FadeIn(lft(T("consensus rules", 27, TEAL, True), 0.4, 1.9)), LaggedStart(*[FadeIn(r) for r in b], lag_ratio=0.15)]


@slide("Finding the anchor closes", "The double spend is blocked")
def blocked(s):
    anc = at(chip("anchor found", TEAL, size=26), -4.4, 1.5)
    below = at(chip("free witnesses below it: closed", BLUE, size=24), 2.0, 1.5)
    yield [FadeIn(anc), GrowArrow(arrow(anc, below)), FadeIn(below)]
    pool = at(card("pool", 3.0, 1.4, BLUE, 28), -4.4, -1.0)
    nfs = VGroup(chip("nf7", ORANGE, size=22), chip("nf8", ORANGE, size=22)).arrange(RIGHT, buff=0.15).move_to(pool).shift(DOWN * 0.2)
    pool[1].shift(UP * 0.35)
    again = at(card("second spend\nof this note", 3.2, 1.4, MUTED, 26), 3.4, -1.0)
    yield [FadeIn(pool), FadeIn(nfs)]
    x = at(cross(Square(0.45), width=6), 0.9, -0.35)
    yield [FadeIn(again), GrowArrow(arrow(again, pool, color=RED)), Create(x),
           FadeIn(at(T("the window or the exclusion proof stops it", 25, RED), 0, -2.6))]


@slide("This sequence is reconstructed", "How we assembled that sequence", PROV)
def provenance(s):
    a = at(card("Bundle::verify\nin the crate", 4.2, 1.6, BLUE, 27), -4.4, 0.4)
    b = at(card("consensus rules\nfrom the book", 4.2, 1.6, BLUE, 27), 0.6, 0.4)
    yield [FadeIn(a), FadeIn(b), FadeIn(at(chip("no block validator in the crate", RED, size=24), -1.9, 1.95))]
    c = at(card("our reading:\nno source fixes\nthe full order", 3.4, 2.0, ORANGE, 25), 5.4, 0.4)
    yield [GrowArrow(arrow(b, c)), FadeIn(c)]
    yield [FadeIn(caption("Chapters 24 and 21 both note this.", y=-1.8, color=MUTED, size=28))]


# ------------------------------------------------------------------ layers
deck.part("The layers and their chapters")

GROUPS = ["Tachyon", "One proof", "Recursion and beyond"]


def group_bar(active):
    pills = VGroup(*[pill(g, ORANGE if i == active else LINE, 22) for i, g in enumerate(GROUPS)]).arrange(RIGHT, buff=0.3)
    return at(pills, 0, 2.2)


def layer_row(num, title, role, y):
    n = at(pill(num, BLUE, 24), -6.4, y)
    t = lft(T(title, 26, INK, True), -5.25, y)
    r = lft(T(role, 25, MUTED), 0.3, y)
    return VGroup(n, t, r)


def layer_slide(first, group, rows, title="The layers in trace order"):
    @slide(first, title)
    def build(s):
        s.add(group_bar(group))
        objs = [layer_row(n, t, r, 1.1 - k * 0.95) for k, (n, t, r) in enumerate(rows)]
        for o in objs:
            yield [FadeIn(o, shift=RIGHT * 0.15)]
    return build


@slide("The layers and their chapters.", "The layers in trace order")
def layers0(s):
    yield [FadeIn(group_bar(0))]
    for k, (n, t, r) in enumerate([("1", "Scaling Zcash", "why state and scanning have to shrink"),
                                    ("20", "Notes, nullifiers, tachygrams", "objects and their derivations")]):
        yield [FadeIn(layer_row(n, t, r, 1.1 - k * 0.95), shift=RIGHT * 0.15)]


layer_slide("Chapter twenty-one, on pool state", 0, [
    ("21", "Pool state and anchors", "a short reference to forgotten history"),
    ("22", "Oblivious sync", "epochs tested by a party blind to the note"),
    ("23", "The proof tree", "the steps from note to stamp"),
    ("2", "Proof-carrying data", "a header and a proof at every node")])
layer_slide("Next come the parts of one proof.", 1, [
    ("4", "Arithmetization", "a step written as one equation"),
    ("5", "QAP and polynomial encoding", "that equation as a polynomial test"),
    ("6", "Polynomial commitments", "one point per polynomial")])
layer_slide("Chapter eight, on batched openings", 1, [
    ("8", "Batched openings", "one claim in place of many"),
    ("7", "Inner product argument", "a short evaluation proof"),
    ("3", "Statements and challenges", "small checks standing for large ones"),
    ("9", "The complete proof", "the parts, with two linear costs left")])
layer_slide("Recursion follows.", 2, [
    ("10", "Recursive proofs", "a proof that its children verify"),
    ("11, 12", "Accumulation, split", "Ĝ carried as a claim"),
    ("14", "Revdot folding", "many revdot claims folded to one")])
layer_slide("Chapter fifteen, on wiring", 2, [
    ("15", "Wiring and the registry", "any registered step, fixed recursive cost"),
    ("13", "Curve cycles", "points handled on the other curve"),
    ("16", "Endoscalars", "one short string serving both curves"),
    ("17", "Staging", "circuits reading the same stage")])
layer_slide("Chapter eighteen, on recursion in Ragu, gives", 2, [
    ("18", "Recursion in Ragu", "the node's circuits"),
    ("19", "Compression in Ragu", "the short proof that leaves the tree"),
    ("24", "Aggregation and bundles", "fees, merging, stripping, block checks")])


# ------------------------------------------------------------------ status
deck.part("What exists at the pinned commits")

STATUS = [("Read as code", TEAL), ("Described, not\nfound in code", RED), ("Open in\nthe design", ORANGE)]


@slide("What exists at the pinned commits.", "Three kinds of status")
def status3(s):
    yield [FadeIn(at(T("the trace sounds like one working system", 28, MUTED), 0, 2.0))]
    row = VGroup(*[card(t, 4.4, 2.0, c, 30) for t, c in STATUS]).arrange(RIGHT, buff=0.4)
    at(row, 0, -0.2)
    yield [LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in row], lag_ratio=0.3)]
    yield [FadeIn(caption("Each chapter's warnings give the details.", y=-2.4, color=INK, size=28))]


@slide("First, here is what we read as code.", "Read as code")
def as_code(s):
    r = at(card(None, 6.6, 3.6, PURPLE), -3.6, -0.2)
    rt = at(T("Ragu, at the pinned commit", 27, PURPLE, True), -3.6, 1.2)
    rc = at(VGroup(*[chip(t, PURPLE, size=24) for t in ("fuse", "compress", "their verifiers")]).arrange(DOWN, buff=0.2), -3.6, -0.3)
    yield [FadeIn(r), FadeIn(rt), FadeIn(rc), FadeIn(at(T("not built or run by us; benchmarks not run", 23, MUTED), -3.6, -2.4))]
    t = at(card(None, 6.6, 3.6, BLUE), 3.6, -0.2)
    tt = at(T("Tachyon crate", 27, BLUE, True), 3.6, 1.2)
    tc = at(VGroup(*[chip(x, BLUE, size=22) for x in ("proof steps, native bodies", "fold functions", "wire format",
                                                       "Bundle::verify, one bundle")]).arrange(DOWN, buff=0.15), 3.6, -0.45)
    yield [FadeIn(t), FadeIn(tt), FadeIn(tc)]


@slide("Second, here is what the sources describe", "The mock of Ragu")
def mock(s):
    crate = at(card("Tachyon crate", 3.0, 1.3, BLUE, 27), -5.8, 0.4)
    m = at(card("mock fuse\nRagu commit Tachyon pins", 4.4, 1.5, MUTED, 25), -1.5, 0.4)
    yield [FadeIn(crate), GrowArrow(arrow(crate, m)), FadeIn(m), FadeIn(at(T("no real Tachyon circuits", 27, RED, True), -1.5, 2.0))]
    items = VGroup(VGroup(check(size=0.3), T("runs a step natively", 25)).arrange(RIGHT, buff=0.2),
                   VGroup(cross(Square(0.3), width=4), T("discards the polynomial openings", 25)).arrange(RIGHT, buff=0.2),
                   VGroup(cross(Square(0.3), width=4), T("does not verify child proofs", 25)).arrange(RIGHT, buff=0.2)).arrange(DOWN, buff=0.25, aligned_edge=LEFT)
    lft(items, 1.4, 0.4)
    yield [LaggedStart(*[FadeIn(i) for i in items], lag_ratio=0.3)]


pts("There is no validator and no mempool.", "Not found in code", [
    "No validator and no mempool",
    "Window and anchor lookup: only in the book and doc comments",
    "Block assembly and transaction-level balance: only in the book and tests",
    "No normative specification: the four ZIPs are empty outlines",
    "No wallet check for reused trapdoors"], size=29, dot=RED, gap=0.36)

pts("Third, here is what remains open", "Open in the design", [
    "Zero knowledge and unlinkability not yet established, though the Tachyon book assumes them",
    "Decompression has not landed: a compressed proof cannot be fused today, and aggregator costs are unknown"],
    size=30, dot=ORANGE, y=0.3)

pts("The sources differ on which anchors", "Open in the design", [
    "Which anchors consensus accepts, and where the crossing sits",
    "Service privacy, fee levels, aggregator payment, per-note proving delegation",
    "The comparison with Orchard is an estimate; real proof size is not settled"],
    size=30, dot=ORANGE)


# ------------------------------------------------------------------ close
deck.part("Where this chapter leaves us")


def recap_slide(first, lit, captions):
    @slide(first, "Where this chapter leaves us")
    def build(s):
        boxes, arrows = journey(y=1.2)
        s.add(boxes, *arrows)
        prev = None
        for group, text in zip(lit, captions):
            c = at(W(text, 58, 28, INK, align=ORIGIN), 0, -1.4)
            anims = [Indicate(boxes[i], color=ORANGE, scale_factor=1.1) for i in group]
            anims += [FadeOut(prev), FadeIn(c)] if prev else [FadeIn(c)]
            prev = c
            yield anims
    return build


recap_slide("Where this chapter leaves us.", [[0, 1], [2]], [
    "A note becomes a tachygram, referred to by a polynomial commitment absorbed into a hash chain.",
    "A spend proves absence for closed epochs with a service's help, and publishes a nullifier pair."])
recap_slide("Each step of the wallet's tree", [[3], [4, 5], []], [
    "Each step is one fuse, and Ragu's accumulators keep the proof the same shape at every depth.",
    "A stamp passes an aggregator and a miner without disturbing Alice's signatures, and validators check it.",
    "A design at fixed commits: mock proofs on the Tachyon side, no validator, and later commits may differ."])


@slide("This is the last chapter.", "References")
def refs(s):
    row = VGroup(*[card(t, 4.2, 1.6, BLUE, 30) for t in ("Glossary", "Notation", "Curves")]).arrange(RIGHT, buff=0.4)
    at(row, 0, 0)
    yield [FadeIn(at(T("This is the last chapter.", 32, INK, True), 0, 1.8))]
    yield [LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in row], lag_ratio=0.3)]
