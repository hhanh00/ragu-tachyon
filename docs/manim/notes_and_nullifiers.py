"""Where a spend's nullifiers land; pnpm docs:manim --page notes-and-nullifiers."""
from manim import *
from concept_diagrams import label, math, heading, box, INK, MUTED, BLUE, TEAL, ORANGE, PALE


class PairPlacement(Scene):
    def construct(self):
        heading(self, 'A later proof tests each nullifier against its own epoch only',
                'The pair guarantees that the epoch of acceptance holds its own nullifier')
        epochs = [6, 7, 8, 9]
        xs = {e: (e - 7.5) * 2.75 + 2.0 for e in epochs}
        left = -5.0

        y = 1.85
        self.add(label('epoch', left, y, 26, MUTED))
        for e in epochs:
            self.add(box(xs[e], y, 2.4, 0.72, MUTED), math(str(e), xs[e], y, 32, INK))

        y = 0.85
        self.add(label('later proof tests', left, y, 26, BLUE))
        for e in epochs:
            self.add(box(xs[e], y, 2.4, 0.72, BLUE), math(rf'\mathsf{{nf}}_{e}\ \text{{absent?}}', xs[e], y, 26, BLUE))

        rows = [
            ('pair, target 7,\naccepted in 7', 7, [('7', True), ('8', False)], -0.45),
            ('pair, target 7,\naccepted in 8', 8, [('7', False), ('8', True)], -1.65),
            ('only nf7, target 7,\naccepted in 8', 8, [('7', False)], -2.85),
        ]
        for text, epoch, values, y in rows:
            self.add(label(text, left, y, 24, INK))
            self.add(box(xs[epoch], y, 2.4, 0.95, TEAL))
            for i, (name, hit) in enumerate(values):
                dx = 0 if len(values) == 1 else (-0.55 if i == 0 else 0.55)
                self.add(math(rf'\mathsf{{nf}}_{name}', xs[epoch] + dx, y, 30, ORANGE if hit else MUTED))
            verdict = 'test fails' if any(hit for _, hit in values) else 'no test notices'
            other = xs[9] if epoch != 9 else xs[6]
            self.add(label(verdict, other, y, 24, ORANGE if any(hit for _, hit in values) else MUTED))
