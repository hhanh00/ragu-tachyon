"""Build a slide deck. See engine.py.

Usage: build.py DECK preview|video [--only N,N] [--work DIR] [--scale X]

DECK is a module in this folder, such as deck_01. Video clips are kept in the
work directory, so a rerun rebuilds only slides whose code or timing changed.
--scale stretches all timing, for narration that runs longer or shorter.
"""
import hashlib
import importlib
import inspect
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from manim import config  # noqa: E402

import av  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
import engine  # noqa: E402


def opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


deck_name, mode = sys.argv[1:3]
module = importlib.import_module(deck_name)
deck, stem = module.deck, module.STEM
audio = HERE.parent
work = Path(opt("--work", "/tmp/slides-work")) / stem
only = {int(n) for n in opt("--only", "").split(",") if n}
scale = float(opt("--scale", "1"))
sentences = engine.script_sentences(audio / "scripts" / f"{stem}.txt")
deck.resolve(sentences)
print(f"{len(deck.slides)} slides for {len(sentences)} sentences", flush=True)

config.frame_width = 16
config.frame_height = 9
config.background_color = "#ffffff"
config.disable_caching = True
config.verbosity = "ERROR"
config.progress_bar = "none"
config.media_dir = str(work / "media")


def clean(writer):
    shutil.rmtree(Path(writer.partial_movie_directory), ignore_errors=True)


def preview():
    config.pixel_width, config.pixel_height = 960, 540
    config.save_last_frame = True
    config.write_to_movie = False
    stills = work / "stills"
    stills.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, slide in enumerate(deck.slides):
        path = stills / f"{i:03d}.png"
        paths.append(path)
        if only and i not in only:
            continue
        config.output_file = f"p{i:03d}"
        scene = engine.SlideScene(slide)
        scene.render()
        Image.fromarray(scene.renderer.get_frame()).convert("RGB").save(path)
    sheets = work / "sheets"
    sheets.mkdir(exist_ok=True)
    per = 12
    for start in range(0, len(paths), per):
        batch = [(start + k, p) for k, p in enumerate(paths[start:start + per]) if p.exists()]
        if only and not any(n in only for n, _ in batch):
            continue
        sheet = Image.new("RGB", (3 * 660, 4 * 372), "#667788")
        for k, (n, p) in enumerate(batch):
            image = Image.open(p).resize((652, 366))
            ImageDraw.Draw(image).text((8, 350), str(n), fill="#c8322b")
            sheet.paste(image, ((k % 3) * 660 + 4, (k // 3) * 372 + 3))
        sheet.save(sheets / f"sheet-{start:03d}.png")
    print(f"sheets in {sheets}", flush=True)


def video():
    config.pixel_width, config.pixel_height, config.frame_rate = 1920, 1080, 30
    timings = json.loads((audio / "timings" / f"{stem}.json").read_text())
    assert [t["text"] for t in timings] == sentences, "timings do not match the script; re-render the audio"
    clips = work / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    starts = [timings[s["first"]]["start"] * scale for s in deck.slides]
    starts[0] = 0.0
    total = (timings[-1]["end"] + 1.0) * scale
    paths = []
    for i, slide in enumerate(deck.slides):
        end = starts[i + 1] if i + 1 < len(starts) else total
        duration = round((end - starts[i]) * 30) / 30
        closure = [c.cell_contents for c in slide["fn"].__closure__ or []]
        key = hashlib.sha1(f"{inspect.getsource(slide['fn'])}{closure}{duration}{slide['title']}{slide['sub']}"
                           f"{slide['section']}{inspect.getsource(engine)}".encode()).hexdigest()[:10]
        path = clips / f"{i:03d}-{key}.mp4"
        paths.append(path)
        if path.exists() or (only and i not in only):
            continue
        config.output_file = f"s{i:03d}"
        scene = engine.SlideScene(slide, duration)
        scene.render()
        writer = scene.renderer.file_writer
        shutil.move(writer.movie_file_path, path)
        clean(writer)
        print(f"clip {i}/{len(deck.slides)-1}: {duration:.1f}s", flush=True)
    if only:
        return
    keep = set(paths)
    for stale in clips.glob("*.mp4"):
        if stale not in keep:
            stale.unlink()
    join(paths, audio / "out" / f"{stem}-slides.mp4")


def join(paths, target):
    """Join the clips without re-encoding, since they share one encoder setup."""
    output = av.open(str(target), "w")
    first = av.open(str(paths[0]))
    stream = output.add_stream_from_template(first.streams.video[0])
    first.close()
    offset = 0
    for path in paths:
        clip = av.open(str(path))
        source = clip.streams.video[0]
        last = 0
        for packet in clip.demux(source):
            if packet.dts is None:
                continue
            step = packet.duration or 0
            packet.pts = int(packet.pts * source.time_base / stream.time_base) + offset
            packet.dts = int(packet.dts * source.time_base / stream.time_base) + offset
            last = max(last, packet.pts + int(step * source.time_base / stream.time_base))
            packet.stream = stream
            output.mux(packet)
        offset = last
        clip.close()
    output.close()
    print(f"wrote {target}", flush=True)


{"preview": preview, "video": video}[mode]()
