"""Figures for statements-and-challenges.md; pnpm docs:manim --page statements-and-challenges."""
import os
import sys
from manim import *
from concept_diagrams import arrow, box, heading, label, math, INK, MUTED, BLUE, TEAL, ORANGE, PURPLE, PALE
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'worked'))
import toy_curve

Q = 43
BAD_Y = 5


class ZeroGrid(Scene):
    def construct(self):
        self.add(math(r'\text{Zeros of } f(X, Y) = (Y - 5)(X^2 - Y) \text{ over } \mathbb{F}_{43}', 0, 3.7, 40),
                 label('One bad row is entirely zeros, and every other row holds at most two zeros', 0, 3.03, 23, MUTED, 14.5))
        side = 0.136
        left, bottom = -5.0, -3.55
        for x in range(Q):
            for y in range(Q):
                value = (y - BAD_Y) * (x * x - y) % Q
                color = PALE
                if y == BAD_Y:
                    color = ORANGE
                elif value == 0:
                    color = BLUE
                self.add(Square(side * 0.9, stroke_width=0, fill_color=color, fill_opacity=1)
                         .move_to([left + x * side, bottom + y * side, 0]))
        top = bottom + (Q - 1) * side
        right = left + (Q - 1) * side
        self.add(label('x', (left + right) / 2, bottom - 0.3, 24, MUTED),
                 label('y', left - 0.4, (bottom + top) / 2, 24, MUTED))
        row_y = bottom + BAD_Y * side
        self.add(arrow((3.0, row_y), (right + 0.1, row_y), ORANGE),
                 label('bad row y = 5:\nthe leading coefficient\nY - 5 is zero here', 4.95, row_y, 25, ORANGE))
        self.add(label('other rows:\na nonzero polynomial of\ndegree 2 in X, so at most\ntwo zeros in the row', 4.95, 0.85, 25, BLUE))


class SpongeFlow(Scene):
    def construct(self):
        heading(self, 'A sponge alternates between adding input and permuting',
                'Only the rate cells receive input and produce output, and the capacity cell carries state between permutations')
        ys = [1.05, -0.05, -1.15]
        names = ['rate', 'rate', 'capacity']
        colors = [BLUE, BLUE, MUTED]

        def stack(x):
            for yy, color in zip(ys, colors):
                self.add(box(x, yy, 0.95, 0.9, color))

        for yy, name in zip(ys, names):
            self.add(label(name, -7.1, yy, 22, MUTED))
        stack(-5.9)
        self.add(math('0', -5.9, ys[0], 30), math('0', -5.9, ys[1], 30), math('0', -5.9, ys[2], 30))
        for start, x_perm, x_next, first, second in [(-5.9, -3.2, -0.9, 'm_0', 'm_1'), (-0.9, 1.8, 4.1, 'm_2', 'm_3')]:
            x_plus = start + 1.2
            for yy in ys:
                self.add(arrow((start + 0.5, yy), (x_perm - 0.6, yy)), arrow((x_perm + 0.6, yy), (x_next - 0.5, yy)))
            for yy, text, shift in zip(ys[:2], (first, second), (0.42, -0.42)):
                self.add(Circle(0.2, stroke_width=0, fill_color=WHITE, fill_opacity=1).move_to([x_plus, yy, 0]),
                         math('+', x_plus, yy, 30, ORANGE), math(text, x_plus, yy + shift, 25, ORANGE))
            self.add(box(x_perm, -0.05, 1.15, 3.1, TEAL), math(r'\pi', x_perm, -0.05, 44, TEAL))
            stack(x_next)
        self.add(arrow((4.6, ys[0]), (6.2, ys[0]), ORANGE), math('c_0', 5.4, ys[0] + 0.42, 28, ORANGE),
                 arrow((4.6, ys[1]), (6.2, ys[1]), ORANGE), math('c_1', 5.4, ys[1] - 0.42, 28, ORANGE))
        self.add(label('absorb', -0.9, -2.45, 26, ORANGE), label('squeeze', 5.4, -2.45, 26, ORANGE))


def real_curve(ax, x_max):
    """y^2 = x^3 + 3 over the real numbers, drawn as one closed-looking branch."""
    tip = -3 ** (1 / 3)
    ts = np.linspace(0, (x_max - tip) ** 0.5, 160)
    xs = tip + ts ** 2
    upper = [ax.c2p(x, max(x ** 3 + 3, 0) ** 0.5) for x in xs]
    lower = [ax.c2p(x, -max(x ** 3 + 3, 0) ** 0.5) for x in xs]
    return VMobject(color=INK, stroke_width=4).set_points_smoothly(upper[::-1] + lower[1:])


def third_point(p, lam, other_x):
    x3 = lam * lam - p[0] - other_x
    return x3, p[1] + lam * (x3 - p[0])


class ChordTangent(Scene):
    def construct(self):
        heading(self, 'Adding points with a line',
                'Over the real numbers: the line meets the curve at a third point, and reflecting it across the x-axis gives the sum')
        panels = [(-3.9, 'chord: P + Q'), (3.9, 'tangent: P + P = 2P')]
        r2 = 2 ** 0.5
        cases = [
            ((-1.0, -r2), (1.0, 2.0)),
            ((-1.0, r2), None),
        ]
        for (cx, title), (p, q) in zip(panels, cases):
            ax = Axes(x_range=[-2, 3.6, 1], y_range=[-6.5, 6.5, 2], x_length=6.6, y_length=5.6, tips=False,
                      axis_config={'color': '#9aaabb', 'include_numbers': False}).move_to([cx, -0.75, 0])
            self.add(ax, real_curve(ax, 3.4), label(title, cx, 2.35, 28, BLUE))
            if q is None:
                lam = 3 * p[0] ** 2 / (2 * p[1])
                third = third_point(p, lam, p[0])
            else:
                lam = (q[1] - p[1]) / (q[0] - p[0])
                third = third_point(p, lam, q[0])
            xs = (-1.8, 3.5)
            self.add(Line(ax.c2p(xs[0], p[1] + lam * (xs[0] - p[0])), ax.c2p(xs[1], p[1] + lam * (xs[1] - p[0])),
                          color=BLUE, stroke_width=3))
            result = (third[0], -third[1])
            self.add(DashedLine(ax.c2p(*third), ax.c2p(*result), color=ORANGE, stroke_width=3))
            dots = [(p, 'P', BLUE, LEFT)]
            if q is not None:
                dots.append((q, 'Q', BLUE, LEFT))
            dots += [(third, 'third point', MUTED, LEFT), (result, 'P + Q' if q else '2P', ORANGE, LEFT)]
            for pt, name, color, side in dots:
                at = ax.c2p(*pt)
                self.add(Dot(at, radius=0.1, color=color))
                lab = label(name, 0, 0, 26, color)
                lab.next_to(Dot(at), side, buff=0.15)
                self.add(lab)


class ToyMultiples(Scene):
    def construct(self):
        heading(self, 'Every point of the toy curve is a multiple of G',
                'Each of the 42 points with coordinates is labelled with the k for which it equals k · G, with G, 2G and 3G in orange')
        p = toy_curve.P
        ax = Axes(x_range=[0, p, 5], y_range=[0, p, 5], x_length=8.6, y_length=5.8, tips=False,
                  axis_config={'color': '#9aaabb'}).move_to([0, -0.75, 0])
        for v in range(0, p, 5):
            at_x, at_y = ax.c2p(v, 0), ax.c2p(0, v)
            self.add(label(str(v), at_x[0], at_x[1] - 0.3, 20, MUTED), label(str(v), at_y[0] - 0.3, at_y[1], 20, MUTED))
        self.add(ax, label('x', 4.75, -3.75, 24, MUTED), label('y', -4.75, 2.3, 24, MUTED))
        g = toy_curve.G[0]
        pt = None
        for k in range(1, toy_curve.Q):
            pt = toy_curve.add(pt, g)
            at = ax.c2p(*pt)
            color = ORANGE if k <= 3 else BLUE
            dx, dy = (-0.28, 0) if pt == (24, 1) else (0, 0.24)
            self.add(Dot(at, radius=0.065, color=color), label(str(k), at[0] + dx, at[1] + dy, 20, color))
