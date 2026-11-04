"""Which gates each polynomial of a staged circuit may use; pnpm docs:manim --page staging."""
from manim import *
from concept_diagrams import label, math, heading, box, INK, MUTED, BLUE, TEAL, ORANGE, PALE


class StageSlots(Scene):
    def cell(self, x, y, w, h, fill, opacity):
        rect = Rectangle(width=w, height=h, stroke_color=MUTED, stroke_width=2)
        rect.set_fill(fill, opacity=opacity)
        rect.move_to((x, y, 0))
        self.add(rect)

    def construct(self):
        heading(self, 'Each polynomial keeps to its reserved gates',
                'A mask forces the white cells to zero, so the polynomials can be added without overwriting each other')
        cols = [-1.8, 0.7, 3.2, 5.7]
        names = ['Gate 0: system', 'Gate 1', 'Gate 2', 'Gate 3']
        for x, name in zip(cols, names):
            self.add(label(name, x, 2.15, 24, MUTED))
        rows = [
            (r'Stage a(X)', 1.25, {0: PALE, 1: BLUE}, {1: 'x, v'}),
            (r'Stage b(X)', 0.05, {0: PALE, 2: TEAL}, {2: 'e, v'}),
            (r'Final trace after a(X)', -1.15, {0: PALE, 2: ORANGE, 3: ORANGE}, {2: 'free', 3: 'free'}),
            (r'Final trace after b(X)', -2.35, {0: PALE, 3: ORANGE}, {3: 'free'}),
        ]
        for name, y, colored, text in rows:
            self.add(label(name, -5.1, y, 25, INK, 3.6))
            for g, x in enumerate(cols):
                if g in colored:
                    self.cell(x, y, 2.3, 0.95, colored[g], 1.0 if colored[g] == PALE else 0.3)
                else:
                    self.cell(x, y, 2.3, 0.95, WHITE, 0.0)
                if g == 0:
                    self.add(label('blinding', x, y, 22, MUTED))
                elif g in text:
                    self.add(label(text[g], x, y, 24, INK))
                else:
                    self.add(label('zero', x, y, 22, MUTED))
