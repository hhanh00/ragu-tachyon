"""How one folding round sorts the four inner products; pnpm docs:manim --page inner-product-argument."""
from manim import *
from concept_diagrams import label, math, heading, box, INK, MUTED, BLUE, TEAL, ORANGE


class FoldingGrid(Scene):
    def construct(self):
        heading(self, 'One round of folding sorts four inner products',
                'The diagonal stays with weight 1, and each off-diagonal cell becomes a cross term')
        xs = [-2.6, 2.6]
        ys = [0.75, -1.85]
        w, h = 4.6, 2.2
        self.add(math(r'u^{-1}\,\mathbf{G}_{lo}', xs[0], 2.25, 34, MUTED),
                 math(r'u\,\mathbf{G}_{hi}', xs[1], 2.25, 34, MUTED),
                 math(r'u\,\mathbf{a}_{lo}', -6.2, ys[0], 34, MUTED),
                 math(r'u^{-1}\,\mathbf{a}_{hi}', -6.2, ys[1], 34, MUTED))
        cells = [
            (0, 0, BLUE, r'\langle \mathbf{a}_{lo}, \mathbf{G}_{lo} \rangle', 'weight 1, part of C'),
            (1, 0, ORANGE, r'u^{2}\,\langle \mathbf{a}_{lo}, \mathbf{G}_{hi} \rangle', 'goes into R'),
            (0, 1, TEAL, r'u^{-2}\,\langle \mathbf{a}_{hi}, \mathbf{G}_{lo} \rangle', 'goes into L'),
            (1, 1, BLUE, r'\langle \mathbf{a}_{hi}, \mathbf{G}_{hi} \rangle', 'weight 1, part of C'),
        ]
        for col, row, color, tex, note in cells:
            self.add(box(xs[col], ys[row], w, h, color),
                     math(tex, xs[col], ys[row] + 0.3, 34, color),
                     label(note, xs[col], ys[row] - 0.55, 24, MUTED))
