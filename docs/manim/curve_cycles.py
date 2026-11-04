"""The ping-pong of a recursive step on a curve cycle; pnpm docs:manim --page curve-cycles."""
from manim import *
from concept_diagrams import label, math, heading, box, arrow, INK, MUTED, BLUE, TEAL, ORANGE


class PingPong(Scene):
    def circuit(self, x, y, field, lines, color):
        self.add(box(x, y, 5.3, 2.0, color))
        self.add(math(field, x, y + 0.62, 30, color))
        self.add(label(lines[0], x, y + 0.04, 22, INK, 4.9))
        self.add(label(lines[1], x, y - 0.46, 22, INK, 4.9))

    def construct(self):
        heading(self, 'Each circuit folds the points of the other',
                'A commitment made in one step is folded in the next step, by the circuit whose wires hold its coordinates')
        self.add(label('Step i', -4.1, 2.25, 28, MUTED), label('Step i + 1', 4.1, 2.25, 28, MUTED))
        top, low = 1.0, -2.4
        self.circuit(-4.1, top, r'\text{Circuit over } \mathbb{F}_{43}',
                     ['folds values over F43', "folds points on E'"], BLUE)
        self.circuit(-4.1, low, r'\text{Circuit over } \mathbb{F}_{31}',
                     ['folds values over F31', 'folds points on E'], TEAL)
        self.circuit(4.1, top, r'\text{Circuit over } \mathbb{F}_{43}',
                     ['folds values over F43', "folds points on E'"], BLUE)
        self.circuit(4.1, low, r'\text{Circuit over } \mathbb{F}_{31}',
                     ['folds values over F31', 'folds points on E'], TEAL)
        self.add(arrow((-1.4, top - 0.6), (1.4, low + 0.6), ORANGE, 4))
        self.add(arrow((-1.4, low + 0.6), (1.4, top - 0.6), ORANGE, 4))
        self.add(label('trace committed on E,', 0, top + 0.32, 21, ORANGE),
                 label('coordinates in F31', 0, top - 0.02, 21, ORANGE))
        self.add(label("trace committed on E',", 0, low - 0.02, 21, ORANGE),
                 label('coordinates in F43', 0, low - 0.36, 21, ORANGE))
