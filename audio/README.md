# Audio and video

Each chapter in `docs/` has a listening script in `scripts/` and an animated slide deck in `slides/`. From these, the tools here produce a narrated video with subtitles.

| Step | Tool | Output in `audio/out/` |
| --- | --- | --- |
| Narration | `render.py` (Kokoro text to speech) | `STEM.m4a`, plus sentence timings in `audio/timings/STEM.json` |
| Slides | `slides/build.py` (Manim), timed to the narration | `STEM-slides.mp4`, silent |
| Subtitles | `slides/subtitles.py` | `STEM-slides.srt` and `STEM-slides-subtitled.mp4` |
| Final video | `make_video.sh` (ffmpeg) | `STEM-video.mp4`, with slides, narration and subtitles |

`STEM` is a script's file name without `.txt`, such as `03-statements-and-challenges`. Everything in `audio/out/` and `audio/timings/` is generated and not committed.

How to write scripts and decks is covered elsewhere: `BRIEF.md` for scripts, `REVIEW.md` for checking them, and `slides/BRIEF.md` for decks.

## One-time setup

Run these from the repository root. You need [uv](https://docs.astral.sh/uv/) and ffmpeg (`brew install ffmpeg`).

The Manim environment renders the slides:

```sh
uv venv .manim-venv --python 3.14
uv pip install --python .manim-venv/bin/python manim av pillow
```

The text-to-speech environment runs Kokoro through onnxruntime:

```sh
uv venv .tts-venv --python 3.12
uv pip install --python .tts-venv/bin/python kokoro-onnx soundfile numpy
```

The Kokoro model files come from the kokoro-onnx project's release (about 350 MB together):

```sh
mkdir -p .kokoro
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  curl -L -o .kokoro/$f https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f
done
```

`.manim-venv/`, `.tts-venv/` and `.kokoro/` are listed in `.gitignore`.

## Regenerating videos

Render one or more chapters from start to finish:

```sh
audio/make_video.sh 03-statements-and-challenges
audio/make_video.sh 02-pcd-intro 03-statements-and-challenges
```

After a change to a deck but not to its script, skip the narration, which is the slow step:

```sh
audio/make_video.sh --skip-audio 03-statements-and-challenges
```

Any change to a script needs the narration rendered again, because the slides are timed to it.

On an M4 Mac the narration takes about 15 minutes for a 9,000-word chapter, and the slide video a few more. Slide clips are cached in `$WORK` (default `/tmp/slides-work`), so a rerun only re-renders slides whose code or timing changed. Set `WORK` to keep the cache elsewhere (see Settings).

## Previewing slides without audio

To check a deck's layout before rendering any audio, write the last frame of every slide to contact sheets:

```sh
cd audio/slides
../../.manim-venv/bin/python build.py deck_03 preview
../../.manim-venv/bin/python build.py deck_03 preview --only 4,5
```

The command prints where it wrote the sheets.

## Settings

`make_video.sh` reads these environment variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `VOICE` | `am_michael` | Kokoro voice |
| `SPEED` | `1.0` | Speaking pace |
| `KOKORO` | `.kokoro` | Directory holding `kokoro-v1.0.onnx` and `voices-v1.0.bin` |
| `WORK` | `/tmp/slides-work` | Cache of rendered slide clips |

For example:

```sh
VOICE=bm_george KOKORO=~/models/kokoro audio/make_video.sh 03-statements-and-challenges
```

`render.py` reads `VOICE` and `SPEED` too, if you run it on its own. To compare voices, list the available ones:

```sh
.tts-venv/bin/python -c "from kokoro_onnx import Kokoro; print(Kokoro('.kokoro/kokoro-v1.0.onnx', '.kokoro/voices-v1.0.bin').get_voices())"
```

Voice names start with `am_` for American male, `af_` for American female, and `bm_` or `bf_` for British.
