"""The error matrix and the two-layer fold; pnpm docs:manim --page revdot-folding."""
from manim import *
from concept_diagrams import label, math, heading, box, arrow, INK, MUTED, BLUE, TEAL, ORANGE, PURPLE


class ErrorMatrix(Scene):
    def construct(self):
        heading(self, 'Every pair of claims has its own cell in the error matrix',
                'The verifier knows the diagonal, and the prover sends every other cell before the challenges')
        cw, ch = 2.5, 1.35
        x0, y0 = -3.1, 0.55
        for j in range(3):
            self.add(math(rf'\mathbf{{b}}_{j}', x0 + j * cw, y0 + 1.15, 30, MUTED),
                     math(rf'(\mu\nu)^{j}', x0 + j * cw, y0 + 1.65, 24, TEAL))
        for i in range(3):
            self.add(math(rf'\mathbf{{a}}_{i}', x0 - 1.75, y0 - i * ch, 30, MUTED),
                     math(rf'\mu^{{-{i}}}', x0 - 2.8, y0 - i * ch, 24, BLUE))
        for i in range(3):
            for j in range(3):
                color = ORANGE if i == j else BLUE
                x, y = x0 + j * cw, y0 - i * ch
                self.add(box(x, y, cw - 0.12, ch - 0.12, color))
                entry = rf'c_{i}' if i == j else rf'e_{{{i},{j}}}'
                self.add(math(entry, x, y + 0.26, 30, color))
                power = j - i
                mu = '' if power == 0 else (r'\mu' if power == 1 else rf'\mu^{{{power}}}')
                nu = '1' if j == 0 and not mu else ('' if j == 0 else (r'\nu' if j == 1 else rf'\nu^{j}'))
                self.add(math(mu + nu, x, y - 0.27, 24, MUTED))
        self.add(box(5.45, 0.9, 2.9, 0.95, ORANGE), label('Diagonal: from the', 5.45, 1.05, 20, ORANGE, 2.7),
                 label('instances', 5.45, 0.72, 20, ORANGE, 2.7),
                 box(5.45, -0.4, 2.9, 0.95, BLUE), label('Off the diagonal: sent', 5.45, -0.25, 20, BLUE, 2.7),
                 label('by the prover', 5.45, -0.58, 20, BLUE, 2.7),
                 label('Grey: the weight of the cell', 5.45, -1.6, 20, MUTED, 2.9))


class TwoLayers(Scene):
    def construct(self):
        heading(self, 'Two layers replace one large matrix with several small ones',
                'Six claims fold into two with one pair of challenges, and those two fold into one with a fresh pair')
        xs = [-6.0, -3.9, -1.8, 1.8, 3.9, 6.0]
        y_in, y_mid, y_out = 1.55, -0.65, -2.85
        for k, x in enumerate(xs):
            self.add(box(x, y_in, 1.6, 0.85, BLUE), math(rf'\text{{claim }}{k}', x, y_in, 24, BLUE))
        mids = [-3.9, 3.9]
        for g, x in enumerate(mids):
            self.add(box(x, y_mid, 3.2, 0.95, ORANGE),
                     math(rf'(\bar{{A}}^{{({g})}},\ \bar{{B}}^{{({g})}},\ c^{{({g})}})', x, y_mid, 26, ORANGE, 3.0))
            for k in range(3):
                self.add(arrow((xs[g * 3 + k], y_in - 0.45), (x + (k - 1) * 0.9, y_mid + 0.5), MUTED))
        self.add(label('Layer 1: 6 cross terms per group, then', -0.0, 0.62, 21, INK, 3.1),
                 math(r'\mu,\ \nu', 0.0, 0.2, 28, ORANGE))
        self.add(box(0, y_out, 3.2, 0.95, TEAL),
                 math(r'(\bar{A}^*,\ \bar{B}^*,\ c^*)', 0, y_out, 26, TEAL, 3.0),
                 arrow((mids[0] + 0.9, y_mid - 0.5), (-0.9, y_out + 0.5), MUTED),
                 arrow((mids[1] - 0.9, y_mid - 0.5), (0.9, y_out + 0.5), MUTED))
        self.add(label('Layer 2: 2 cross terms between groups, then', 0.0, -1.32, 21, INK, 3.6),
                 math(r"\mu',\ \nu'", 0.0, -1.72, 28, TEAL))
