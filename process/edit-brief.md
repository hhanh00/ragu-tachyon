# Revising a chapter from a review

The repository is /Users/hanh/projects/ragu-tachyon, a VuePress site in `docs/` that teaches Ragu and Tachyon from first principles. A fresh reviewer has scored your chapter against chapter 1 (`docs/scaling-zcash.md`, the quality bar). Your job is to revise the chapter until it reaches that bar (about 8.5/10 or better).

## Before editing

- Read `CLAUDE.md` and follow every rule in it. They are binding.
- Read the review file you were given, and your chapter in full.
- Read `docs/scaling-zcash.md` and `docs/pcd-intro.md` (recently revised to the bar) to match their voice, pacing and use of examples.

## How to revise

- Fix every must-fix item, and the should-fix items that are cheap. Keep everything the review lists under "Keep".
- Motivate before asserting, show the intermediate algebra, and give each new idea a numeric example.
- Every number in prose must come from the chapter's worked script `docs/worked/<slug_with_underscores>.py`. To add or change numbers, edit that script so it prints a new fragment, add `<!-- worked:name -->` / `<!-- /worked:name -->` markers in the page, then run `pnpm docs:worked --page <slug>` and `pnpm docs:worked --check --page <slug>`. Never type computed values into prose. Every fragment the script prints must have markers.
- If the chapter is overloaded with detail the reader cannot use yet, trim it to one worked example per idea and note the detail that should live in a later chapter.
- Keep code-derived claims labeled "Reconstructed from code at commit X, not confirmed by the authors" and keep commit pins.
- Add length through missing steps and examples, not restatement.

## Boundaries (other editors are working on other chapters at the same time)

- Edit only your chapter's `.md` file and its own worked script. Do not edit other chapters, other worked scripts, `docs/.vuepress/`, or anything under `audio/`. Do not run `pnpm docs:worked` without `--page`.
- If you rename or remove a heading, run `grep -rn "<slug>.md#" docs` and list every inbound link that now breaks; do not fix them yourself.
- If material should move to or from another chapter, do not move it. Describe it in your report.
- Do not commit.

## Check your work

- `pnpm docs:worked --check --page <slug>` passes.
- Mermaid diagrams and KaTeX still parse (balanced `$`, fenced ```mermaid blocks).
- Reread the whole chapter once for the CLAUDE.md writing rules.

## Report

Reply with: what you changed (short list), headings renamed or removed with the inbound links that break, cross-chapter moves you recommend, and any review item you deliberately did not fix and why.
