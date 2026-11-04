"""How a structured vector pairs its entries; pnpm docs:manim --page arithmetization."""
from manim import *
from concept_diagrams import label, math, heading, box, INK, MUTED, BLUE, TEAL, ORANGE, PALE


class RevdotPairing(Scene):
    def construct(self):
        heading(self, 'The revdot product pairs entries from opposite ends', 'Position k pairs with position 7 - k, so each a wire meets the b wire of its own gate')
        names = ['c_0', 'c_1', 'a_1', 'a_0', 'b_0', 'b_1', 'd_1', 'd_0']
        colors = [MUTED, MUTED, BLUE, BLUE, ORANGE, ORANGE, MUTED, MUTED]
        y0, step = -2.9, 1.65
        xs = [(k - 3.5) * step for k in range(8)]
        for k, (name, color) in enumerate(zip(names, colors)):
            self.add(box(xs[k], y0, 1.3, 0.95, color), math(name, xs[k], y0, 36, color),
                     label(str(k), xs[k], y0 - 0.85, 24, MUTED))
        pairs = [(0, 7, MUTED, 'c_0 d_0'), (1, 6, MUTED, 'c_1 d_1'), (2, 5, ORANGE, 'a_1 b_1'), (3, 4, BLUE, 'a_0 b_0')]
        for lo, hi, color, text in pairs:
            arc = ArcBetweenPoints([xs[hi], y0 + 0.55, 0], [xs[lo], y0 + 0.55, 0], angle=PI * 0.8, color=color, stroke_width=4)
            self.add(arc, math(text, 0, arc.get_top()[1] + 0.25, 28, color))
        self.add(label('position', -6.9, y0 - 0.85, 22, MUTED))
