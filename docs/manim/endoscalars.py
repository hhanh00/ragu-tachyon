"""One bit string gives one scalar per field, and each scalar is used twice; pnpm docs:manim --page endoscalars."""
from manim import *
from concept_diagrams import label, math, heading, box, arrow, INK, MUTED, BLUE, TEAL, ORANGE


class TwoScalars(Scene):
    def use(self, x, y, title, lines, color):
        self.add(box(x, y, 4.5, 1.25, color))
        self.add(label(title, x, y + 0.3, 21, color, 4.2))
        self.add(math(lines, x, y - 0.22, 24, INK, 4.2))

    def construct(self):
        heading(self, 'One string, two scalars',
                'Each scalar is computed as a field value in one circuit and applied to points as a walk in the other')
        self.add(box(-6.05, -0.4, 2.7, 1.5, ORANGE),
                 label('Bit string', -6.05, -0.08, 22, ORANGE),
                 math(r'\hat{s} \in \{0,1\}^{\ell}', -6.05, -0.62, 26, INK, 2.4))
        self.add(box(-2.45, -0.4, 2.9, 1.5, INK),
                 label('Element', -2.45, -0.08, 22, INK),
                 math(r'k = a + b\lambda', -2.45, -0.62, 26, INK, 2.5))
        self.add(arrow((-4.7, -0.4), (-3.9, -0.4), ORANGE, 4))
        top, low = 1.15, -1.95
        self.add(math(r'\lambda \mapsto \lambda_{43}', -0.5, 0.75, 22, BLUE),
                 math(r'\lambda \mapsto \lambda_{31}', -0.5, -1.55, 22, TEAL))
        self.add(arrow((-1.0, 0.1), (1.35, top + 0.1), BLUE, 3),
                 arrow((-1.0, -0.9), (1.35, low - 0.1), TEAL, 3))
        self.add(math(r'\beta \in \mathbb{F}_{43}', 2.0, top + 0.1, 26, BLUE),
                 math(r"\beta' \in \mathbb{F}_{31}", 2.0, low - 0.1, 26, TEAL))
        self.use(5.45, top + 0.72, r'Circuit over F43, lift', r'v = \ldots + \beta \cdot p_i(u)', BLUE)
        self.use(5.45, top - 0.72, r'Circuit over F31, walk on E', r'P = \beta \cdot \ldots + C_i', BLUE)
        self.use(5.45, low + 0.72, r"Circuit over F31, lift", r"v' = \ldots + \beta' \cdot p'_i(u')", TEAL)
        self.use(5.45, low - 0.72, r"Circuit over F43, walk on E'", r"P' = \beta' \cdot \ldots + C'_i", TEAL)
        self.add(arrow((2.85, top + 0.25), (3.15, top + 0.65), BLUE, 3),
                 arrow((2.85, top - 0.05), (3.15, top - 0.6), BLUE, 3),
                 arrow((2.85, low + 0.05), (3.15, low + 0.6), TEAL, 3),
                 arrow((2.85, low - 0.25), (3.15, low - 0.65), TEAL, 3))
