# Building slide decks

A deck turns a chapter's listening script into a silent, animated slide video. It plays in sync with the audio, and `subtitles.py` can add the script as a subtitle track. The reference deck is `deck_01.py`. Read it in full, together with `engine.py`, before writing a new deck.

## How a deck is tied to the script

Each slide is a generator registered with `@slide("first words", "Title")`. The first argument is the opening words of the script sentence where the slide begins. `Deck.resolve` matches those words in order, so slides must follow the script's order, and the opening words must be long enough to match only the intended sentence. The slide stays on screen until the next slide's sentence starts. Each `yield [animations]` is one build step, and the engine spreads the steps evenly over the time the narration spends on the slide.

Write the script first, following `audio/BRIEF.md`, and build the deck against the final script. If you change the script later, re-render the audio, because the video uses the sentence timings in `audio/timings/`.

## Pace

- Start a new slide every two to three sentences. `deck_01.py` averages 2.7 sentences per slide. Never leave more than four sentences on one slide, because a static screen under a long stretch of narration loses the viewer.
- Start a new slide at every spoken heading, and call `deck.part("Heading")` first so that the section name appears above the slide titles.
- Give each slide two to four build steps, roughly one per sentence or per idea, so that something changes while the narration moves on.

## Animation

Use Manim Community through the helpers in `engine.py` (`T`, `W`, `card`, `pill`, `chip`, `arrow`, `bullets`, `caption`, `check`, `cross`, `strike`). Animate the idea itself rather than only revealing text:

- Show a process as motion. A value moves into a box, an arrow grows from input to output, two pieces combine into one, and a failed check gets a red cross.
- Keep a running example on screen across a few slides, and change it step by step instead of redrawing it from scratch.
- Use `Indicate`, `Flash`, or a colored outline to point at the part the narration is talking about.
- Keep text-only slides, built with the `pts` and `cards` helpers, to about a fifth of the deck. They suit lists of assumptions or properties. They do not suit mechanisms.

## Color

The background is white and the type is Helvetica Neue, with Menlo for values. Use only the palette in `engine.py`, and give each color one meaning for the whole deck, stated in a comment at the top of the deck file. For example:

- `BLUE` for data and headers
- `TEAL` for a check that passes, or a proof
- `ORANGE` for the step or party under discussion
- `PURPLE` for Ragu-specific material
- `RED` only for failure, cheating, or a rejected value
- `MUTED` and `LINE` for context and connectors

Use `fill=` on a card for emphasis sparingly, at most once or twice per slide.

## Layout

- The frame is 16 by 9 units. The title and section name sit above y = 2.75, so content goes below that line, within x from -7.5 to 7.5.
- Captions sit at the bottom, around y = -3.7.
- Keep text at size 22 or larger, and keep wrapped text to about 60 characters per line.
- Nothing may overlap or run off the frame. Check every contact sheet from the preview before rendering video.

## Accuracy

Every label and number on a slide must come from the script or its chapter. The chapter's numbers come from `docs/worked/`, so copy them rather than computing new ones. Slides may show digits and short symbols where the script spells them out. Keep the site's provenance labels: put "Reconstructed from code at the commit this site pins, not confirmed by the authors" in the slide's subtitle (the third argument to `@slide`) wherever the script says it.

## Building

Create the Manim environment once, from the repository root:

```sh
uv venv .manim-venv --python 3.14
uv pip install --python .manim-venv/bin/python manim av pillow
```

Then, from `audio/slides/`:

```sh
../../.manim-venv/bin/python build.py deck_NN preview          # final frame of each slide, as contact sheets
../../.manim-venv/bin/python build.py deck_NN preview --only 4,5
../../.manim-venv/bin/python build.py deck_NN video            # needs audio/timings/STEM.json
../../.manim-venv/bin/python subtitles.py STEM                 # needs ffmpeg
```

The preview prints where it wrote the contact sheets. Look at every sheet, and fix overlaps, clipped text, and empty slides before rendering the video.
