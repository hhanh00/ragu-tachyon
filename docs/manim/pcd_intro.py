"""The tally tree from pcd-intro; pnpm docs:manim --page pcd-intro."""
import sys
from pathlib import Path

from manim import *
from concept_diagrams import label, math, heading, box, arrow, INK, MUTED, BLUE, TEAL, ORANGE, PALE

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'worked'))
from pcd_intro import balanced_nodes  # noqa: E402


class TallyTree(Scene):
    def construct(self):
        heading(self, 'A tree of tally headers', 'Each node claims the sum over a range of positions, and a verifier reads only the root')
        nodes = balanced_nodes()
        layer_y = {1: -3.3, 2: -1.6, 4: 0.1, 8: 1.8}
        place = {}
        for name, step, inputs, h in nodes:
            span = h[1] - h[0]
            x = ((h[0] + h[1]) / 2 - 4) * 1.9
            y = layer_y[span]
            if span == 8:
                color = TEAL
            elif h[1] <= 4:
                color = BLUE
            else:
                color = ORANGE
            w = 1.72 if span == 1 else 2.2
            self.add(box(x, y, w, 0.8, color),
                     math(f'({h[0]},\\,{h[1]},\\,{h[2]})', x, y, 28, color))
            place[name] = (x, y)
        for name, step, inputs, h in nodes:
            if inputs is None:
                continue
            x, y = place[name]
            for child in (inputs[0], inputs[2]):
                cx, cy = place[child]
                self.add(arrow((cx, cy + 0.45), (x, y - 0.5)))
        self.add(label('Alice', -3.8, 0.85, 22, BLUE), label('Bob', 3.8, 0.85, 22, ORANGE))
