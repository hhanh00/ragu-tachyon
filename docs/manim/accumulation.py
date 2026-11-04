"""One accumulator absorbing one new claim per step; pnpm docs:manim --page accumulation."""
from manim import *
from concept_diagrams import label, math, heading, box, arrow, INK, MUTED, BLUE, TEAL, ORANGE


class AccumulatorChain(Scene):
    def construct(self):
        heading(self, 'Each step merges one new claim into the accumulator',
                'The merge costs logarithmic work, and the single linear check waits until the end')
        xs = [-3.75, -0.3, 3.15]
        top, mid = 1.45, -0.75
        self.add(box(-6.95, mid, 1.5, 1.2, TEAL), math(r'\mathsf{acc}_0', -6.95, mid, 30, TEAL))
        previous = -6.2
        for i, x in enumerate(xs, 1):
            self.add(box(x, top, 2.5, 1.2, BLUE),
                     math(rf'(\hat{{G}}_{i},\ \mathbf{{u}}_{i})', x, top + 0.14, 30, BLUE),
                     label('new IPA claim', x, top - 0.33, 20, MUTED),
                     box(x, mid, 2.2, 1.2, ORANGE),
                     label('merge', x, mid + 0.17, 26, ORANGE),
                     math(r'x_M,\ \alpha,\ \tau', x, mid - 0.27, 24, MUTED),
                     arrow((x, top - 0.6), (x, mid + 0.6)),
                     arrow((previous, mid), (x - 1.1, mid)))
            if i < 3:
                self.add(math(rf'\mathsf{{acc}}_{i}', x + 1.72, mid + 0.34, 24, TEAL))
            previous = x + 1.1
        self.add(box(6.6, mid, 2.2, 1.2, TEAL),
                 label('decider', 6.6, mid + 0.17, 26, TEAL),
                 label('one MSM of size n', 6.6, mid - 0.27, 18, MUTED),
                 arrow((previous, mid), (5.5, mid)),
                 math(r'\mathsf{acc}_3', 4.87, mid + 0.34, 24, TEAL))
        self.add(label('The verifier\'s side of each merge grows as log n, and only the decider\'s check is linear.',
                       0, -2.65, 23, MUTED, 13.5))
