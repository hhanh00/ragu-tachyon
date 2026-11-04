"""Which epochs each party checks; pnpm docs:manim --page scaling-zcash."""
from manim import *
from concept_diagrams import label, math, heading, box, INK, MUTED, BLUE, TEAL, ORANGE, PALE


class EpochCoverage(Scene):
    def construct(self):
        heading(self, 'A spend in epoch 7 of a note created in epoch 3', 'The proof covers the closed epochs, and validators check the epochs they still hold')
        epochs = list(range(2, 9))
        step = 1.85
        xs = {e: (e - 5) * step + 0.9 for e in epochs}
        y0 = 1.2
        self.add(label('epoch', -6.55, y0, 24, MUTED))
        for e in epochs:
            self.add(box(xs[e], y0, 1.6, 0.8, MUTED), math(str(e), xs[e], y0, 32, INK))

        # Row 1: nullifiers tested by the exclusion proof, each against its own epoch.
        y1 = -0.15
        self.add(label('exclusion\nproof', -6.55, y1, 24, BLUE))
        for e in range(3, 7):
            self.add(box(xs[e], y1, 1.6, 0.8, BLUE), math(rf'\mathsf{{nf}}_{e}\ \text{{absent}}', xs[e], y1, 22, BLUE))

        # Row 2: the epochs that validators retain.
        y2 = -1.5
        self.add(label('validators\nretain', -6.55, y2, 24, TEAL))
        self.add(label('pruned', (xs[2] + xs[5]) / 2, y2, 26, MUTED))
        for e in (6, 7):
            self.add(box(xs[e], y2, 1.6, 0.8, TEAL), label('all values', xs[e], y2, 22, TEAL))

        # Row 3: the spend's published pair.
        y3 = -2.85
        self.add(label('spend\npublishes', -6.55, y3, 24, ORANGE))
        for e in (7, 8):
            self.add(box(xs[e], y3, 1.6, 0.8, ORANGE), math(rf'\mathsf{{nf}}_{e}', xs[e], y3, 30, ORANGE))
