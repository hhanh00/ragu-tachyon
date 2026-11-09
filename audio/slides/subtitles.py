"""Add a chapter's script to its slide video as subtitles. Requires ffmpeg.

Usage: subtitles.py STEM [--scale X]

Reads audio/timings/STEM.json and audio/out/STEM-slides.mp4. Writes STEM-slides.srt
and STEM-slides-subtitled.mp4, which has a soft subtitle track that players can
switch on or off. --scale should match the value given to build.py.
"""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

LINE = 42
LINES_PER_CUE = 2
GAP = 0.04  # seconds between cues within a sentence

stem = sys.argv[1]
scale = float(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 1.0
out = Path(__file__).resolve().parent.parent / "out"
timings = json.loads((out.parent / "timings" / f"{stem}.json").read_text())


def balanced(text):
    """Wrap to the fewest cues, as evenly as fits, so no cue is left with a stray word."""
    if len(text) <= LINE:
        return [text]
    wrap = lambda width: textwrap.wrap(text, width, break_on_hyphens=False, break_long_words=False)
    needed = len(wrap(LINE))
    needed += needed % LINES_PER_CUE  # whole cues only
    width = LINE
    while width > 12 and len(wrap(width - 1)) <= needed:
        width -= 1
    return wrap(width)


def cues():
    """Split each sentence into cues of up to two lines, sharing its time by length."""
    result = []
    for sentence in timings:
        lines = balanced(sentence["text"])
        groups = [lines[i:i + LINES_PER_CUE] for i in range(0, len(lines), LINES_PER_CUE)]
        begin, length = sentence["start"] * scale, (sentence["end"] - sentence["start"]) * scale
        chars = sum(len(line) for group in groups for line in group)
        for group in groups:
            share = length * sum(len(line) for line in group) / chars
            result.append((begin, begin + share - GAP, "\n".join(group)))
            begin += share
    return result


def stamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


items = cues()
srt = out / f"{stem}-slides.srt"
srt.write_text("".join(f"{i}\n{stamp(a)} --> {stamp(b)}\n{text}\n\n" for i, (a, b, text) in enumerate(items, 1)))

subprocess.run(
    ["ffmpeg", "-y", "-loglevel", "error", "-i", str(out / f"{stem}-slides.mp4"), "-i", str(srt),
     "-map", "0", "-map", "1", "-c:v", "copy", "-c:s", "mov_text",
     "-metadata:s:s:0", "language=eng", "-metadata:s:s:0", "title=Script",
     str(out / f"{stem}-slides-subtitled.mp4")],
    check=True,
)
print(f"{len(items)} cues; wrote {srt.name} and {stem}-slides-subtitled.mp4")
