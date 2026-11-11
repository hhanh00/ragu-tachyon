"""Render listening scripts to AAC with Kokoro, one chapter at a time.

Usage: render.py MODEL_DIR SCRIPTS_DIR OUT_DIR [--force] [--only STEM]

The environment variables VOICE (default am_michael) and SPEED (default 1.0)
choose the Kokoro voice and pace.

Skips chapters whose .m4a is newer than their script, so an interrupted run
can restart, and an edited script re-renders on the next run. Writes each
sentence's timing to audio/timings/STEM.json for the slide videos.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

VOICE = os.environ.get("VOICE", "am_michael")
SPEED = float(os.environ.get("SPEED", "1.0"))
RATE = 24000
HEADING_MAX_WORDS = 7

model_dir, scripts_dir, out_dir = map(Path, sys.argv[1:4])
force = "--force" in sys.argv
only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
out_dir.mkdir(parents=True, exist_ok=True)
kokoro = Kokoro(str(model_dir / "kokoro-v1.0.onnx"), str(model_dir / "voices-v1.0.bin"))


def silence(seconds):
    return np.zeros(int(seconds * RATE), dtype=np.float32)


def render(text):
    """Return the audio and each sentence's start and end time in seconds."""
    chunks, timings, position = [], [], 0

    def add(samples):
        nonlocal position
        chunks.append(samples)
        position += len(samples)

    for para in (p.strip() for p in text.split("\n\n")):
        if not para:
            continue
        is_heading = len(para.split()) <= HEADING_MAX_WORDS
        if is_heading:
            add(silence(0.9))
        for sentence in re.split(r"(?<=[.!?])\s+", para):
            samples, rate = kokoro.create(sentence, voice=VOICE, speed=SPEED, lang="en-us")
            assert rate == RATE
            begin = position / RATE
            add(samples)
            timings.append({"text": sentence, "start": begin, "end": position / RATE, "heading": is_heading})
            add(silence(0.12))
        add(silence(0.7 if is_heading else 0.35))
    return np.concatenate(chunks), timings


total = 0.0
timings_dir = out_dir.parent / "timings"
timings_dir.mkdir(exist_ok=True)
for script in sorted(scripts_dir.glob("*.txt")):
    if only and script.stem != only:
        continue
    target = out_dir / f"{script.stem}.m4a"
    if not force and target.exists() and target.stat().st_mtime > script.stat().st_mtime:
        print(f"skip {script.stem}", flush=True)
        continue
    start = time.time()
    audio, timings = render(script.read_text())
    (timings_dir / f"{script.stem}.json").write_text(json.dumps(timings, indent=1))
    wav = out_dir / f"{script.stem}.wav"
    sf.write(wav, audio, RATE)
    subprocess.run(
        ["afconvert", "-f", "m4af", "-d", "aac", "-b", "64000", str(wav), str(target)],
        check=True,
    )
    wav.unlink()
    seconds = len(audio) / RATE
    total += seconds
    print(f"done {script.stem}: {seconds/60:.1f} min audio in {(time.time()-start)/60:.1f} min", flush=True)

print(f"finished: {total/3600:.2f} h rendered this run", flush=True)
