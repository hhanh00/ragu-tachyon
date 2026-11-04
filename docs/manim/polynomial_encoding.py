"""How the product polynomial splits into c_1 and c_2; pnpm docs:manim --page polynomial-encoding."""
from manim import *
from concept_diagrams import label, math, arrow, heading, box, INK, MUTED, BLUE, TEAL, ORANGE


class ProductSplit(Scene):
    def construct(self):
        heading(self, 'Splitting the product and reversing the lower half',
                'For 4n = 8, the middle coefficient of the product becomes the constant term of the first piece')
        step, width, height = 1.0, 0.86, 0.72
        xs = [(k - 7) * step for k in range(15)]
        y_top, y_low = 1.15, -1.75

        def color_of(k):
            return ORANGE if k == 7 else BLUE if k < 7 else TEAL

        self.add(label('coefficients of the product', 0, y_top + 0.85, 24, MUTED))
        for k in range(15):
            self.add(box(xs[k], y_top, width, height, color_of(k)),
                     math(f'X^{{{k}}}', xs[k], y_top, 26, color_of(k)))

        # c_1 keeps the left eight columns in reverse order; c_2 keeps the right seven in order.
        for p in range(8):
            source = 7 - p
            self.add(box(xs[p], y_low, width, height, color_of(source)),
                     math(f'X^{{{source}}}', xs[p], y_low, 26, color_of(source)),
                     label(str(p), xs[p], y_low - 0.62, 20, MUTED))
        for k in range(8, 15):
            self.add(box(xs[k], y_low, width, height, TEAL),
                     math(f'X^{{{k}}}', xs[k], y_low, 26, TEAL),
                     label(str(k - 8), xs[k], y_low - 0.62, 20, MUTED))

        drop_top, drop_low = y_top - height / 2, y_low + height / 2
        self.add(arrow((xs[7], drop_top), (xs[0], drop_low), ORANGE, 4),
                 arrow((xs[0], drop_top), (xs[7], drop_low), BLUE, 3),
                 arrow((xs[8], drop_top), (xs[8], drop_low), TEAL, 3),
                 arrow((xs[14], drop_top), (xs[14], drop_low), TEAL, 3))
        self.add(label('reversed', xs[3] + 0.5, -1.05, 24, BLUE), label('same order', xs[11], -0.3, 24, TEAL))
        self.add(math('c_1(X)', xs[3] + 0.5, y_low - 1.2, 34, INK), math('c_2(X)', xs[11], y_low - 1.2, 34, INK))
        self.add(label('power of X in the new polynomial', -6.05, y_low - 1.2, 18, MUTED, 3.0))
