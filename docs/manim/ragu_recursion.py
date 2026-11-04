"""The transcript of one fuse, split across two circuits; pnpm docs:manim --page ragu-recursion."""
from manim import *
from concept_diagrams import label, math, arrow, heading, box, INK, MUTED, BLUE, TEAL, ORANGE, PALE


class TranscriptSplit(Scene):
    def construct(self):
        heading(self, 'One transcript, replayed by two circuits',
                'Each bridge commitment is absorbed before the challenges that depend on it are squeezed')
        names = ['preamble', "s'", 'inner error', 'outer error', 'ab', 'query', 'f', 'eval']
        out = ['w', 'y,\\ z', '', "\\mu'", 'x', '\\alpha', 'u', '\\text{pre\\_beta}']
        xs = [-6.3 + 1.8 * i for i in range(8)]
        for i, (x, name, c) in enumerate(zip(xs, names, out)):
            color = BLUE if i < 3 else TEAL
            self.add(box(x, 1.25, 1.6, 0.95, color), label(name, x, 1.25, 22, INK, 1.45))
            if c:
                self.add(math(c, x, -0.15, 34, INK, 1.5))
                self.add(arrow((x, 0.72), (x, 0.2), color))
        self.add(label('Bridge commitments, absorbed from left to right', 0, 2.1, 24, MUTED))
        self.add(Line([-7.1, -0.85, 0], [-1.9, -0.85, 0], color=BLUE, stroke_width=4))
        self.add(Line([-1.7, -0.85, 0], [7.1, -0.85, 0], color=TEAL, stroke_width=4))
        self.add(label('hashes_1: 3 permutations', -4.5, -1.25, 25, BLUE))
        self.add(label('hashes_2: 5 permutations', 2.7, -1.25, 25, TEAL))
        self.add(box(-1.8, -2.75, 5.2, 1.15, ORANGE))
        self.add(label('Sponge state, held in the outer error stage', -1.8, -2.55, 22, INK, 4.9))
        self.add(label('hashes_1 checks it, hashes_2 resumes from it', -1.8, -3.0, 20, MUTED, 4.9))
        self.add(arrow((-2.7, 0.72), (-2.7, -2.15), ORANGE))
        self.add(arrow((0.85, -2.5), (2.0, -1.6), ORANGE))
        self.add(label('squeezes', 2.95, -2.35, 24, TEAL))
        self.add(math('\\mu', 3.85, -2.35, 34, TEAL))
        self.add(label('first', 4.55, -2.35, 24, TEAL))
