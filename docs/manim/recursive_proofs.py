"""Recursive circuits with and without linear verifier steps; pnpm docs:manim --page recursive-proofs."""
import sys
from pathlib import Path

from manim import *
from concept_diagrams import label, math, heading, box, arrow, INK, MUTED, BLUE, TEAL, ORANGE

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'worked'))
from recursive_proofs import growth, lg  # noqa: E402

BITS = 255
LEVELS = 4


class VerifierNesting(Scene):
    def row(self, title, y, widths, sizes, color):
        self.add(label(title, -5.0, y + 1.55, 26, color))
        x = -7.2
        for level, (w, n) in enumerate(zip(widths, sizes)):
            cx = x + w / 2
            self.add(box(cx, y, w, 1.5, color))
            self.add(label(f'Level {level}', cx, y + 0.98, 20, MUTED))
            self.add(math(f'n = 2^{{{lg(n)}}}', cx, y - 1.05, 26, INK))
            step_w = 0.72
            if level == 0:
                self.add(box(cx, y, step_w, 0.72, BLUE), math('F', cx, y, 26, BLUE))
            else:
                left = cx - w / 2 + 0.12 + step_w / 2
                self.add(box(left, y, step_w, 0.72, BLUE), math('F', left, y, 26, BLUE))
                inner_w = w - step_w - 0.36
                inner_x = left + step_w / 2 + 0.12 + inner_w / 2
                self.add(box(inner_x, y, inner_w, 0.92, ORANGE),
                         math(f'V_{{{level - 1}}}', inner_x, y, 26, ORANGE))
            x += w + 0.32

    def construct(self):
        heading(self, 'A circuit that contains the previous verifier',
                'Box widths are schematic. The exponents come from the gate counts in this chapter')
        linear = [n for _, _, n in growth(BITS, True, levels=LEVELS)]
        small = [n for _, _, n in growth(BITS, False, levels=LEVELS)]
        self.row('With the linear steps', 1.05, [1.3, 2.7, 4.1, 5.5], linear, ORANGE)
        self.row('Without the linear steps', -2.25, [1.3, 3.1, 3.7, 3.7], small, TEAL)
