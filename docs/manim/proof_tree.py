"""Where a note's lineage rests on the anchor chain; pnpm docs:manim --page proof-tree."""
from manim import *
from concept_diagrams import label, math, heading, box, arrow, INK, MUTED, BLUE, TEAL, ORANGE, PURPLE, PALE


class LineageRail(Scene):
    def construct(self):
        heading(self, 'A lineage rests at different places on the anchor chain',
                'Each step below moves the spendable or the stamp to the marked position')
        y = 0.75
        spans = [('epoch 3', -6.5, -3.0), ('epochs 4, 5, 6', -2.8, 1.4), ('epoch 7', 1.6, 6.6)]
        for t, lo, hi in spans:
            self.add(Line([lo, y, 0], [hi, y, 0], color=MUTED, stroke_width=6))
            self.add(label(t, (lo + hi) / 2, y + 1.3, 25, MUTED))
        self.add(Line([-3.0, y, 0], [-2.8, y, 0], color=ORANGE, stroke_width=6),
                 Line([1.4, y, 0], [1.6, y, 0], color=ORANGE, stroke_width=6))

        marks = [
            (-4.75, r'\text{after creation}', BLUE, 'SpendableInit', 'spends in epoch 3 only', -1.2),
            (-2.8, r'\mathsf{entry}(4)', TEAL, 'QrSpendableInit', 'tests epoch 3, can lift', 0.0),
            (1.6, r'\mathsf{entry}(7)', TEAL, 'SpendableLift', 'crosses epochs 4 to 6', 0.0),
            (3.6, r'a_1', ORANGE, 'ActionLift', 'moves actions in epoch 7', 0.0),
            (6.2, r'a_3', PURPLE, 'StampLift', 'moves the stamp in epoch 7', 0.0),
        ]
        for x, name, color, step, note, _ in marks:
            self.add(Dot([x, y, 0], radius=0.11, color=color))
            self.add(math(name, x, y + 0.5, 25, color))

        rows = [
            (-5.0, -1.05, BLUE, 'SpendableInit', 'rests just after', 'the creation stamp'),
            (-2.25, -1.05, TEAL, 'QrSpendableInit', 'tests epoch 3,', 'rests on an entry anchor'),
            (0.5, -1.05, TEAL, 'SpendableLift', 'crosses whole', 'epochs 4, 5, 6'),
            (3.25, -1.05, ORANGE, 'ActionLift', 'moves actions', 'within epoch 7'),
            (5.95, -1.05, PURPLE, 'StampLift', 'moves the stamp', 'within epoch 7'),
        ]
        for (x, by, color, step, l1, l2), (mx, *_ ) in zip(rows, marks):
            self.add(box(x, by, 2.6, 1.55, color))
            self.add(label(step, x, by + 0.42, 22, color, 2.5))
            self.add(label(l1, x, by - 0.1, 19, INK, 2.5))
            self.add(label(l2, x, by - 0.45, 19, INK, 2.5))
            self.add(Line([mx, y - 0.13, 0], [x, by + 0.8, 0], color=color, stroke_width=2))

        self.add(label('The orange joins are boundary digests. A lift by a segment can start only on an entry anchor, so the spendable from SpendableInit cannot use it.', 0, -2.75, 23, MUTED, 13.5))
