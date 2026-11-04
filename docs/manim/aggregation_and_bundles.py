"""The two bundle layouts; pnpm docs:manim --page aggregation-and-bundles."""
from manim import *
from concept_diagrams import label, heading, INK, MUTED, BLUE, ORANGE, PALE


def cell(x, y, w, h, text, color, size=20):
    rect = Rectangle(width=w, height=h, stroke_color=color, stroke_width=2,
                     fill_color=color, fill_opacity=0.14).move_to([x + w / 2, y, 0])
    return VGroup(rect, label(text, x + w / 2, y, size, INK, w - 0.12))


class WireFormat(Scene):
    def construct(self):
        heading(self, 'Stripping replaces the trailer and leaves the body alone',
                'The signatures cover effecting data, so the fields they do not cover can change after signing')
        body = [('value\nbalance', 1.3, BLUE), ('descriptors', 1.75, BLUE), ('max fee\ncommitment', 1.75, BLUE),
                ('action and\nbinding\nsignatures', 1.75, ORANGE), ('memo', 1.1, BLUE)]
        stamped = [('fee', 0.8), ('indicator,\nanchor,\ntachygrams', 1.75), ('proof', 1.5)]
        stripped = [('fee', 0.8), ('aggregate\nwtxid', 1.75)]
        for y, name, trailer in [(1.05, 'Stamped (0x01)', stamped), (-0.95, 'Stripped (0x02)', stripped)]:
            self.add(label(name, -5.9, y + 0.85, 24, INK))
            x = -7.1
            self.add(cell(x, y, 0.85, 1.1, 'state', ORANGE, 22))
            x += 0.85
            for text, w, color in body:
                self.add(cell(x, y, w, 1.1, text, color, 22))
                x += w
            for text, w in trailer:
                self.add(cell(x, y, w, 1.1, text, ORANGE, 22))
                x += w
        self.add(Rectangle(width=0.4, height=0.3, stroke_color=BLUE, fill_color=BLUE, fill_opacity=0.14, stroke_width=2).move_to([-3.4, -2.5, 0]),
                 label('Effecting data, in the bundle commitment and so in txid', 0.2, -2.5, 23, BLUE, 9.2))
        self.add(Rectangle(width=0.4, height=0.3, stroke_color=ORANGE, fill_color=ORANGE, fill_opacity=0.14, stroke_width=2).move_to([-3.4, -3.1, 0]),
                 label('Authorization data, in auth_digest, which makes wtxid differ', 0.2, -3.1, 23, ORANGE, 9.2))
