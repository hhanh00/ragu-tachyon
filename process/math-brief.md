# Minimal math in the main text

Repository: /Users/hanh/projects/ragu-tachyon (VuePress site in `docs/`). Read `CLAUDE.md` first and follow it.

The site owner, reading chapter 3, asked to "keep the math to a minimum" and to put tedious proofs in expandable sections. Apply that to your chapter.

## What to do

- In the main text keep: the motivation for each step, the statement of each result, the intuition in plain words, and a worked numeric example (generated numbers). Lead with a concrete example before a general statement where the chapter currently does the reverse.
- Move derivations, step-by-step algebra, proofs, induction steps, long symbol manipulations, and reference-level detail into collapsible boxes:

  ```
  ::: details <short plain title, e.g. "The full derivation">

  ...moved content...

  :::
  ```

  Do not delete content; relocate it. Leave one or two plain sentences in the main text saying what the box shows and what its result is, so the main text still reads continuously without opening any box.
- Keep the informal "why cheating fails" arguments in the main text, told in words plus numbers rather than symbol manipulation where possible.
- Keep every "Reconstructed from code at commit X" label and every book-versus-code warning (they may go inside a details box if the material they label moves there, but must stay attached to it).
- Worked-number blocks (`<!-- worked:name -->` … `<!-- /worked:name -->`) may move into a details box together with their markers. Never type computed numbers into prose; if you change generated text, edit `docs/worked/<slug_underscored>.py` and run `pnpm docs:worked --page <slug>` then `pnpm docs:worked --check --page <slug>`.
- Do not rename, renumber, add or remove any `##` heading, and do not rename any `###` heading (other chapters link to these anchors). You may add new `###` headings.
- Edit only your chapter's `.md` file and its own worked script. Do not commit.

## Check

- `pnpm docs:worked --check --page <slug>` passes.
- Every `::: details` has a matching closing `:::`, and `$` delimiters are balanced.
- Reread the main text with all boxes closed: it must still make sense on its own.

## Report

Reply with: the main-text word count before and after (excluding details boxes), a list of the boxes you created (title and what moved), and anything you chose to keep in the main text despite being mathematical, with the reason.
