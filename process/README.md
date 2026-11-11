# Editorial process and current state

This folder records how the chapters and their audio and slides were produced, so the work can resume in a new session or on another machine. It is not part of the published site (VuePress builds only `docs/`).

## Standing preferences of the site owner

- **Chapter 1 is the quality bar.** `docs/scaling-zcash.md` sets the standard for clarity, motivation, worked examples and pacing. Chapter 2 (`docs/pcd-intro.md`) was revised to reach it.
- **Keep the math in the main text to a minimum.** The main text carries the motivation, the statement of each result, the intuition in plain words and a generated numeric example, with the example before the general statement. Derivations, proofs and reference tables go into collapsible `::: details <title>` boxes rather than being deleted. "Why cheating fails" arguments stay in the main text, told in words and numbers.
- **Coordinates and values should never look magical.** Chapter 3 now explains point addition and gives a table of k·G, and every curve example states its multiplier. Apply the same idea wherever a value would otherwise appear from nowhere.
- **Every slide deck after chapter 1 opens with a recap of the previous chapter**: a short spoken paragraph after the title and one or two slides under `deck.part("Previously")`.
- **Narration voice** is Kokoro's `am_michael`.

## Tools

| Command | Purpose |
| --- | --- |
| `pnpm docs:worked` / `pnpm docs:worked --page <slug>` | Fill generated numbers into a page from `docs/worked/<slug>.py` |
| `pnpm docs:worked --check` | Fail if any page is out of date with its script |
| `pnpm docs:build` | Build the site; also catches broken containers and KaTeX errors |
| `pnpm docs:manim --page <slug>` | Render a page's static diagrams |
| `python3 scripts/check-links.py` | Check every relative `.md#anchor` link against heading slugs |
| `python3 scripts/fix-chapter-numbers.py [slug ...]` | Set bare-number chapter links like `[21](./pool-state.md)` to the sidebar number; arguments are pages to skip |
| `audio/make_video.sh <stem>` | Narration, slide video, subtitles and final video; see `audio/README.md` |

Run `pnpm docs:worked --check`, `python3 scripts/check-links.py` and `pnpm docs:build` before every commit. In the built HTML, a literal `:::` means a container broke; a warning nested inside a details box needs the outer box written with four colons (`::::`).

## The chapter quality loop

Used for chapters 3 to 22 in November 2026.

1. A fresh reviewer agent with no earlier context follows `review-brief.md`: it calibrates on chapters 1 and 2, reads the chapter as a student, scores it out of 10 (chapter 1 is about 9) and writes must-fix, should-fix and keep lists.
2. An editor agent follows `edit-brief.md` with that review.
3. A new reviewer scores the result. Repeat until the score reaches 8.5, then do one polish pass. Stop after four reviews and do one final polish pass regardless.

Editors run in parallel, so each may change only its own chapter page and its own worked script, regenerate with `--page`, and must not rename or renumber `##` headings without reporting the inbound links that break. Cross-chapter moves and link fixes are collected and done one at a time afterwards with `scripts/check-links.py`.

`math-brief.md` is the brief for the minimal-math pass, and `slides-brief.md` the brief for writing a chapter's listening script and deck. `audio/BRIEF.md`, `audio/REVIEW.md` and `audio/slides/BRIEF.md` hold the detailed rules for scripts and decks.

## Final review scores (November 2026)

Chapters numbered as in the sidebar. Scores are the last review before the final polish pass, which was not re-scored.

| Score | Chapters |
| --- | --- |
| 8.5 | 3, 4, 5, 7, 8, 9, 10, 11, 12, 20, 21 |
| 8 (four-review cap) | 6, 13, 14, 15, 16, 17, 19, 22, 23 |
| 7.5 (four-review cap) | 18 |

Chapter 19, Compression in Ragu, was split out of chapter 18 at the owner's request, which renumbered every later chapter by one.

## State of the audio and slides

- Listening scripts exist for chapters 1 to 26 (26 is the glossary appendix) in `audio/scripts/`.
- Slide decks exist for chapters 1 to 25 in `audio/slides/deck_NN.py`.
- Only decks 2 and 3 open with the recap of the previous chapter. Decks 4 to 25 still need one, and their scripts need the matching recap paragraph.
- Scripts and decks 4 to 25 were written before the minimal-math pass. The content still matches, but a few sections were reordered to put the example first, so some slides follow a slightly different order from the page.
- Videos have been rendered for chapters 2 and 3 only. Rendered files in `audio/out/` and `audio/timings/` are not committed.
- Untested idea: Kokoro currently runs on the CPU through onnxruntime (about 16 minutes for a 9,000-word chapter on an M4). The Core ML execution provider (`Kokoro.from_session`) or the MLX port (`mlx-audio`) might be faster.

## Open issues in the chapters

- **Chapter 15:** the statement that the parent commits to bᵢ before drawing x has not been checked against Ragu's code.
- **Chapter 13, Section 3:** it never says that the toy curves E and E′ have the form y² = x³ + b, which the cycle search assumes.
- **Chapter 18:** the transcript table says τ is "replayed by hashes_1", while the slot table assigns τ to hashes_2.
- **Chapters 23 and 24:** they pin slightly different GitHub line ranges for the same steps (`StampMerge`, `StampUnmerge`, `FeeFuse`, `FeeSeed`).
- **Chapters 4 and 5:** w₁ and w₂ clash with the vector w. A rename has to change both chapters at once.
- **Chapter 9:** it writes the witness as x = 4 next to the challenge x = 9. Chapter 10 now uses z₀ for the witness.
- **Site-wide:** chapter references mix styles ("Chapter 09", "chapter 07", "chapter 3").
- **Scripts:** many run at 100–115% of the chapter's prose length, against the 75–80% target in `audio/BRIEF.md`, mainly because numbers are spelled out.
