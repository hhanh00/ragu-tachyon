"""The walk of registry restrictions in one fold; pnpm docs:manim --page wiring-and-registry."""
from manim import *
from concept_diagrams import label, math, heading, box, arrow, INK, MUTED, BLUE, TEAL, ORANGE, PURPLE


class RegistryWalk(Scene):
    def construct(self):
        heading(self, 'One fold moves one variable at a time',
                'Each arrow is a pair of claims that must open to the same value')
        y_top, y_bot, y_mid = 1.35, -1.75, -0.2
        w, h = 2.75, 1.0
        xs = [-6.15, -2.35, 1.45, 5.65]

        def node(x, y, name, poly, color):
            self.add(box(x, y, w, h, color),
                     math(name, x, y + 0.24, 24, color, w - 0.3),
                     math(poly, x, y - 0.22, 22, INK, w - 0.3))

        node(xs[0], y_top, r'S_0', r'm(W, x_0, y_0)', BLUE)
        node(xs[0], y_bot, r'S_1', r'm(W, x_1, y_1)', BLUE)
        node(xs[1], y_top, r"S'_0", r'm(w, x_0, Y)', ORANGE)
        node(xs[1], y_bot, r"S'_1", r'm(w, x_1, Y)', ORANGE)
        node(xs[2], y_mid, r"S''", r'm(w, X, y)', PURPLE)
        node(xs[3], y_mid, r'S_{\mathrm{new}}', r'm(W, x, y)', TEAL)

        self.add(arrow((xs[0] + w / 2, y_top), (xs[1] - w / 2, y_top), MUTED),
                 arrow((xs[0] + w / 2, y_bot), (xs[1] - w / 2, y_bot), MUTED),
                 arrow((xs[1] + w / 2, y_top - 0.3), (xs[2] - w / 2, y_mid + 0.2), MUTED),
                 arrow((xs[1] + w / 2, y_bot + 0.3), (xs[2] - w / 2, y_mid - 0.2), MUTED),
                 arrow((xs[2] + w / 2, y_mid), (xs[3] - w / 2, y_mid), MUTED))

        def value(s, x, y):
            self.add(math(s, x, y, 21, MUTED))

        mid01 = (xs[0] + xs[1]) / 2
        value(r'v_0', mid01, y_top + 0.28)
        value(r'v_1', mid01, y_bot - 0.28)
        mid12 = (xs[1] + xs[2]) / 2
        value(r'v_2', mid12 + 0.15, y_top - 0.15)
        value(r'v_3', mid12 + 0.15, y_bot + 0.15)
        mid23 = (xs[2] + xs[3]) / 2
        value(r'v_4', mid23, y_mid + 0.28)

        self.add(label('Old accumulators', xs[0], y_top + 0.85, 19, BLUE),
                 label('After w', xs[1], y_top + 0.85, 19, ORANGE),
                 label('After y', xs[2], y_mid + 0.85, 19, PURPLE),
                 label('After x', xs[3], y_mid + 0.85, 19, TEAL))

        self.add(arrow((xs[3], y_mid - h / 2), (xs[3], -2.3), TEAL),
                 math(r's_i(x, y) = m(\omega^i, x, y)', xs[3], -2.6, 22, TEAL, 3.1))
