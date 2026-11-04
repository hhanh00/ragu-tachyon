"""The anchor chain and the consensus window; pnpm docs:manim --page pool-state."""
from manim import *
from concept_diagrams import label, math, heading, box, arrow, INK, MUTED, BLUE, TEAL, ORANGE, PURPLE, PALE


class AnchorChain(Scene):
    def construct(self):
        heading(self, 'Two kinds of fold build the anchor chain',
                'Stamp absorptions stay inside an epoch, and one boundary digest joins each epoch to the next')
        y = 0.2
        xs = [-6.3, -3.9, -1.5, 0.9, 3.3, 5.7]
        names = [r'\mathsf{final}(e-1)', r'\mathsf{entry}(e)', r'a_1', r'\mathsf{final}(e)', r'\mathsf{entry}(e+1)', r'a_2']
        colors = [BLUE, ORANGE, BLUE, BLUE, ORANGE, BLUE]
        for x, n, c in zip(xs, names, colors):
            self.add(box(x, y, 1.95, 0.95, c), math(n, x, y, 26, c, 1.7))
        folds = [(0, ORANGE, r'H_\mathsf{ep}'), (1, BLUE, r'H_\mathsf{st}'), (2, BLUE, r'H_\mathsf{st}'),
                 (3, ORANGE, r'H_\mathsf{ep}'), (4, BLUE, r'H_\mathsf{st}')]
        for i, c, t in folds:
            self.add(arrow((xs[i] + 0.98, y), (xs[i + 1] - 0.98, y), c, 4))
            self.add(math(t, (xs[i] + xs[i + 1]) / 2, y + 0.42, 22, c))
        for lo, hi, t in [(-3.9 - 1.0, 0.9 + 1.0, 'epoch e'), (3.3 - 1.0, 7.1, 'epoch e + 1')]:
            self.add(Line([lo, y - 0.95, 0], [hi, y - 0.95, 0], color=MUTED, stroke_width=3))
            self.add(label(t, (lo + hi) / 2, y - 1.3, 24, MUTED))
        self.add(Line([-7.3, y - 0.95, 0], [-5.05, y - 0.95, 0], color=MUTED, stroke_width=3),
                 label('epoch e - 1', -6.2, y - 1.3, 24, MUTED))
        self.add(label('Stamp fold: absorbs the previous anchor, the block\'s epoch, and the two limbs of the stamp commitment', 0, -2.15, 23, BLUE, 14.5))
        self.add(label('Boundary fold: absorbs the previous anchor and the epoch being entered, and no tachygrams', 0, -2.7, 23, ORANGE, 14.5))
        self.add(label('An epoch with no stamps has entry(e) = final(e), but still has its own boundary digest', 0, -3.25, 23, MUTED, 14.5))


class ConsensusWindow(Scene):
    def construct(self):
        heading(self, 'A stamp anchored in epoch e has two epochs to land',
                'The window of retained tachygrams moves with the block that carries the stamp')
        xs = {'e - 1': -3.6, 'e': -0.9, 'e + 1': 1.8, 'e + 2': 4.5}
        w, h = 2.55, 0.95
        top = 1.65
        for t, x in xs.items():
            self.add(label('epoch ' + t, x, top + 0.2, 24, MUTED))
        rows = [
            ('Lands in e', 0.8, ['e - 1', 'e'], 'e', TEAL),
            ('Lands in e + 1', -0.55, ['e', 'e + 1'], 'e + 1', TEAL),
            ('Lands in e + 2', -1.9, ['e + 1', 'e + 2'], 'e + 2', ORANGE),
        ]
        for name, y, window, land, c in rows:
            self.add(label(name, -6.3, y, 26, c))
            for t, x in xs.items():
                inside = t in window
                r = RoundedRectangle(width=w, height=h, corner_radius=0.12,
                                     stroke_color=(BLUE if inside else MUTED), stroke_width=(3 if inside else 1),
                                     fill_color=(PALE if inside else WHITE), fill_opacity=1).move_to([x, y, 0])
                self.add(r)
                if inside:
                    self.add(label('window', x, y + 0.26, 20, BLUE))
                if t == land:
                    self.add(label('accepted' if c == TEAL else 'rejected', x, y - 0.2, 22, c))
        self.add(label('Rejected in the last row because the anchor\'s epoch is no longer current or preceding', 0, -3.1, 24, ORANGE, 14.5))
