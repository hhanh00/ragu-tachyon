"""Turn a deck of generator-based slides into a silent video.

A slide is a generator function registered with @deck.slide("first words of its
first sentence", "Title"). Each `yield [animations]` is one build step, and the
engine spreads the steps evenly over the time the narration spends on the slide.

    python build.py DECK preview   # final frame of every slide, as contact sheets
    python build.py DECK video     # 1080p clips, joined into one silent mp4
"""
import re
import textwrap
from pathlib import Path

from manim import *

INK = "#172b4d"
MUTED = "#526477"
LINE = "#c5d0dd"
BLUE = "#2563eb"
TEAL = "#008577"
ORANGE = "#c66a08"
PURPLE = "#8052bd"
RED = "#c8322b"
PALE = "#eef3fa"
FONT = "Helvetica Neue"
MONO = "Menlo"
TOP = 2.75  # upper edge of the content area, below the title


def T(text, size=30, color=INK, bold=False, font=FONT):
    """Text in the deck's type, sharp at any size."""
    return Text(text, font=font, color=color, font_size=size, weight=BOLD if bold else NORMAL)


def W(text, chars=40, size=30, color=INK, bold=False, align=LEFT):
    """Text wrapped to a number of characters per line."""
    lines = [T(line, size, color, bold) for line in textwrap.wrap(text, chars)]
    return VGroup(*lines).arrange(DOWN, buff=0.17 * size / 30, aligned_edge=align)


def code(text, size=26, color=INK):
    return T(text, size, color, font=MONO)


def card(text=None, w=3, h=1.2, color=BLUE, size=26, fill=None, text_color=None, bold=False):
    """A rounded box, optionally with centered text (newlines allowed)."""
    box = RoundedRectangle(width=w, height=h, corner_radius=min(0.16, h / 3), stroke_color=color,
                           stroke_width=2.5, fill_color=fill or color, fill_opacity=1 if fill else 0.08)
    if not text:
        return VGroup(box)
    lines = VGroup(*[T(t, size, text_color or INK, bold) for t in text.split("\n")]).arrange(DOWN, buff=0.1)
    if lines.width > w - 0.25:
        lines.scale_to_fit_width(w - 0.25)
    lines.move_to(box)
    return VGroup(box, lines)


def pill(text, color=BLUE, size=22):
    label = T(text, size, WHITE, True)
    box = RoundedRectangle(width=label.width + 0.42, height=label.height + 0.26, corner_radius=0.16,
                           stroke_width=0, fill_color=color, fill_opacity=1)
    label.move_to(box)
    return VGroup(box, label)


def chip(text, color=INK, w=None, h=0.56, size=22):
    """A value in monospace, such as a commitment or a nullifier."""
    label = code(text, size, color)
    box = RoundedRectangle(width=w or label.width + 0.34, height=h, corner_radius=0.09, stroke_color=color,
                           stroke_width=2, fill_color=WHITE, fill_opacity=1)
    label.move_to(box)
    return VGroup(box, label)


def arrow(a, b, color=MUTED, width=4, buff=0.1):
    """An arrow between two points or mobjects, joining the facing edges of mobjects."""
    if isinstance(a, Mobject) and isinstance(b, Mobject):
        if b.get_left()[0] > a.get_right()[0]:
            a, b = a.get_right(), b.get_left()
        elif b.get_right()[0] < a.get_left()[0]:
            a, b = a.get_left(), b.get_right()
        elif b.get_y() < a.get_y():
            a, b = a.get_bottom(), b.get_top()
        else:
            a, b = a.get_top(), b.get_bottom()
    return Arrow(a, b, buff=buff, color=color, stroke_width=width, tip_length=0.2,
                 max_tip_length_to_length_ratio=0.4, max_stroke_width_to_length_ratio=20)


def bullets(items, chars=52, size=30, color=INK, gap=0.34, dot=BLUE):
    rows = VGroup()
    for item in items:
        mark = Dot(radius=0.07, color=dot)
        body = W(item, chars, size, color)
        mark.next_to(body[0], LEFT, buff=0.24)
        rows.add(VGroup(mark, body))
    return rows.arrange(DOWN, buff=gap, aligned_edge=LEFT)


def caption(text, y=-3.72, color=MUTED, size=25, chars=90):
    return W(text, chars, size, color, align=ORIGIN).move_to([0, y, 0])


def strike(mob, color=RED):
    return Line(mob.get_corner(DL), mob.get_corner(UR), color=color, stroke_width=6)


def cross(mob, color=RED, width=7):
    return VGroup(Line(mob.get_corner(DL), mob.get_corner(UR), color=color, stroke_width=width),
                  Line(mob.get_corner(UL), mob.get_corner(DR), color=color, stroke_width=width))


def check(color=TEAL, size=0.4):
    return VMobject(color=color, stroke_width=8).set_points_as_corners(
        [[-0.5 * size, 0, 0], [-0.1 * size, -0.4 * size, 0], [0.6 * size, 0.5 * size, 0]])


def appear(*mobs, shift=0.0, lag=0.12):
    return [LaggedStart(*[FadeIn(m, shift=shift * DOWN) for m in mobs], lag_ratio=lag)]


class Deck:
    def __init__(self, script_path):
        self.slides = []
        self.section = ""
        self.script_path = Path(script_path)

    def part(self, name):
        """Name the section shown above the titles of the slides that follow."""
        self.section = name

    def slide(self, at, title, sub=None):
        def register(fn):
            self.slides.append({"at": at, "title": title, "sub": sub, "fn": fn, "section": self.section})
            return fn
        return register

    def resolve(self, sentences):
        """Find each slide's first sentence, requiring the deck to follow the script's order."""
        cursor = 0
        for slide in self.slides:
            for i in range(cursor, len(sentences)):
                if sentences[i].startswith(slide["at"]):
                    slide["first"] = i
                    cursor = i + 1
                    break
            else:
                raise ValueError(f"No sentence after index {cursor} starts with: {slide['at']!r}")
        for slide, after in zip(self.slides, self.slides[1:]):
            slide["last"] = after["first"] - 1
        self.slides[-1]["last"] = len(sentences) - 1


def script_sentences(path):
    out = []
    for para in Path(path).read_text().split("\n\n"):
        if para.strip():
            out.extend(re.split(r"(?<=[.!?])\s+", para.strip()))
    return out


class Dry:
    """Stands in for the scene when counting a slide's steps."""

    def add(self, *mobs):
        pass


class SlideScene(Scene):
    def __init__(self, slide, duration=None, **kwargs):
        super().__init__(**kwargs)
        self.slide = slide
        self.duration = duration

    def header(self):
        s = self.slide
        title = T(s["title"], 44, INK, True)
        if title.width > 15:
            title.scale_to_fit_width(15)
        title.to_corner(UL, buff=0).move_to([-7.45 + title.width / 2, 3.72, 0])
        items = VGroup(title)
        kicker = T(s["section"].upper(), 19, BLUE, True)
        kicker.move_to([-7.45 + kicker.width / 2, 4.27, 0])
        items.add(kicker)
        if s["sub"]:
            sub = W(s["sub"], 96, 25, MUTED)
            sub.move_to([-7.45 + sub.width / 2, 3.14 - (sub.height - 0.3) / 2, 0])
            items.add(sub)
        return items

    def construct(self):
        fn = self.slide["fn"]
        count = sum(1 for _ in fn(Dry()))
        header = self.header()
        if self.duration is None:  # preview: show the slide's final state
            self.add(header)
            for step in fn(self):
                self.play(*step)
            return
        self.add(header)
        # Work in whole frames, so that clip lengths add up to the narration's length.
        fps = config.frame_rate
        total = round(self.duration * fps)
        each = total // max(count, 1)
        run = max(1, min(fps, int(each * 0.6)))
        for i, step in enumerate(fn(self)):
            hold = total - run * count - (each - run) * (count - 1) if i == count - 1 else each - run
            self.play(*step, run_time=run / fps)
            if hold > 0:
                self.wait(hold / fps)
