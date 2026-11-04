"""The toy curve as a set of points; pnpm docs:manim --page polynomial-commitments."""
import os
import sys
from manim import *
from concept_diagrams import label, math, heading, INK, MUTED, BLUE, ORANGE, PURPLE
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'worked'))
from toy_curve import G, H, U, P, curve_points


class ToyCurvePoints(Scene):
    def construct(self):
        heading(self, 'The toy curve is a finite set of points', r'y² = x³ + 3 over the integers modulo 31, with 42 affine points and the point at infinity')
        ax = Axes(x_range=[0, P, 5], y_range=[0, P, 5], x_length=8.0, y_length=5.4, tips=False,
                  axis_config={'color': '#9aaabb', 'include_numbers': False}).move_to([0, -0.75, 0])
        self.add(ax, label('x', 4.45, -3.45, 24, MUTED), label('y', -4.45, 2.2, 24, MUTED))
        for point in curve_points():
            self.add(Dot(ax.c2p(*point), radius=0.055, color='#9aaabb'))
        marked = [(f'G{i}', a, BLUE) for i, a in enumerate(G)] + [('H', H, PURPLE), ('U', U, ORANGE)]
        for name, a, color in marked:
            at = ax.c2p(*a)
            self.add(Dot(at, radius=0.1, color=color), label(name, at[0] + 0.32, at[1] + 0.2, 24, color))
