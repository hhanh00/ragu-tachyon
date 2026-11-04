"""Figures for statements-and-challenges.md; pnpm docs:manim --page statements-and-challenges."""
from manim import *
from concept_diagrams import arrow, box, heading, label, math, MUTED, BLUE, TEAL, ORANGE, PALE

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
