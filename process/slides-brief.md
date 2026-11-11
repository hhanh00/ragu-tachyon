# Script + slide deck for one chapter

Repository: /Users/hanh/projects/ragu-tachyon. The chapters in `docs/` were just heavily revised, so the listening script for your chapter is stale (or missing). Your job has two parts, done in order. Do not commit. Edit only your own script file and your own deck file.

## Part 1: rewrite the listening script

- Read `audio/BRIEF.md` (the rules), `audio/REVIEW.md` (the accuracy checklist), `CLAUDE.md` (prose rules), and the reference script `audio/scripts/06-polynomial-commitments.txt` together with `audio/scripts/02-pcd-intro.txt` (the most recent script, written for the current chapter 2).
- Read your chapter in `docs/` in full, plus its worked script output (`python3 docs/worked/<slug_underscored>.py`) where numbers come from.
- Write the script at the path you were given, from scratch or by revising the old file if one exists, so it matches the current chapter. Start with `Chapter <number in words>. <Title>.` using the chapter number you were given. Spoken references to other chapters must use the current numbering (sidebar order in `docs/.vuepress/config.js`: 1 scaling-zcash … 18 ragu-recursion, 19 compression, 20 notes-and-nullifiers, 21 pool-state, 22 oblivious-sync, 23 proof-tree, 24 aggregation-and-bundles, 25 recap).
- Then check your script against the chapter claim by claim using `audio/REVIEW.md`, and fix what you find.
- Validate the format mechanically: only allowed characters, no digits, sentences under 40 words, headings ≤ 7 words, other paragraphs > 7 words. Write a tiny checker if needed.

## Part 2: build the slide deck

- Read `audio/slides/BRIEF.md` (binding rules: a slide every 2–3 sentences, never more than 4; `deck.part` at each heading; 2–4 build steps; animate mechanisms; color meanings declared at the top; layout limits; accuracy and provenance subtitles).
- Read `audio/slides/engine.py` and `audio/slides/deck_02.py` in full (the most recent deck; follow its style and helpers), and skim `deck_01.py`.
- Write `audio/slides/deck_NN.py` with `STEM = "NN-slug"` matching your script's filename stem. Every `@slide("first words", ...)` must match your final script in order.
- Build previews from `audio/slides/` with
  `../../.manim-venv/bin/python build.py deck_NN preview --work /tmp/slides-work`
  The first run checks that every slide resolves to a sentence; fix mismatches.
- Open every contact sheet it writes (Read the PNGs) and fix overlaps, clipped text, off-frame content and empty slides. Iterate until every sheet is clean. Use `--only N,N` to re-render specific slides.
- Do not render video (no audio timings exist).

## Report

Reply with: script sentence and heading counts, slide count and sentences per slide, the contact-sheet folder, any chapter content you could not express or any likely error you noticed in the chapter itself, and anything left unfixed.
