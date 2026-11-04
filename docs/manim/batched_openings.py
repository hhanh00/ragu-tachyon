"""How batching moves claims to one point and then one polynomial; pnpm docs:manim --page batched-openings."""
from manim import *
from concept_diagrams import label, math, arrow, heading, box, INK, MUTED, BLUE, TEAL, ORANGE


class BatchedClaims(Scene):
    def construct(self):
        heading(self, 'Batching moves the claims to one point, then to one polynomial',
                'Each dot is one evaluation claim, placed by its polynomial (row) and its point (column)')
        cols = ['x_0', 'x_1', 'x_2', 'u']
        rows = ['p_0', 'p_1', 'p_2', 'f', 'p']
        panel_x = [-5.2, 0, 5.2]
        cell_w, cell_h = 0.8, 0.72
        y_top = 1.45

        def cell(panel, col, row):
            return panel_x[panel] + (col - 1.5) * cell_w, y_top - row * cell_h

        for panel in range(3):
            for c, name in enumerate(cols):
                x_, _ = cell(panel, c, 0)
                self.add(math(name, x_, y_top + 0.62, 26, MUTED))
            for r, name in enumerate(rows):
                x_, y_ = cell(panel, 0, r)
                self.add(math(name, x_ - 0.72, y_, 26, MUTED))
                for c in range(4):
                    cx, cy = cell(panel, c, r)
                    self.add(Rectangle(width=cell_w, height=cell_h, stroke_color=MUTED,
                                       stroke_width=1, stroke_opacity=0.35).move_to([cx, cy, 0]))

        def dot(panel, col, row, color):
            cx, cy = cell(panel, col, row)
            self.add(Dot([cx, cy, 0], radius=0.15, color=color))

        for i in range(3):
            dot(0, i, i, BLUE)
        for i in range(3):
            dot(1, 3, i, BLUE)
        dot(1, 3, 3, ORANGE)
        dot(2, 3, 4, TEAL)

        y_caption = y_top - 5 * cell_h - 0.3
        self.add(label('The input claims\nuse different points', panel_x[0], y_caption, 24),
                 label('All values now sit at u,\nand f is the new polynomial', panel_x[1], y_caption, 24),
                 label('One claim remains,\nabout the combination p', panel_x[2], y_caption, 24))
        mid_y = y_top - 2 * cell_h
        self.add(arrow((-3.3, mid_y), (-2.15, mid_y), INK, 4), arrow((1.9, mid_y), (3.05, mid_y), INK, 4))
        self.add(math(r'\alpha,\,u', -2.72, mid_y + 0.42, 28, INK), math(r'\beta', 2.47, mid_y + 0.42, 28, INK))
