# Checking listening scripts against their chapters

A script in `audio/scripts/` is a spoken rewrite of a chapter in `docs/`. `audio/BRIEF.md` describes the rules the script was written under, including what it may legitimately drop. Read the brief, then read each source chapter in full and each script in full, and compare them claim by claim.

The scripts are final in length and style, so this pass only corrects errors. Look for:

1. Factual errors: a claim, cause, order of protocol steps, or attribution that differs from the chapter, including a condensation that changes the meaning. Who does a step (prover, verifier, wallet, service) and when matters.
2. Wrong numbers: check every spoken number against the chapter, or against the matching `docs/worked/` output where the chapter takes it from there.
3. Invented content: a claim or number with no basis in the chapter. A summary directly derivable from the chapter's own table is acceptable.
4. Missing provenance: a "reconstructed from code, not confirmed by the authors" label, or a disagreement between book and code, that the script lost or stated as settled fact.
5. A missing argument: a step of reasoning the later text depends on, or an explanation of why cheating fails, that the script dropped.
6. A sentence a listener could not parse or would mishear in a way that changes the meaning.

Do not report dropped coordinates, hashes, code listings, or confirmatory tables, because the brief allows those. Do not polish wording, restructure, or trim anything that is correct.

Fix each real problem in place with the smallest edit that makes it right, keeping the file format from the brief: allowed characters only, numbers in words, sentences under 40 words, headings at most 7 words, other paragraphs longer than 7 words. Change only the assigned script files. Do not commit.

Reply with, per file, each correction as one line (what the script said, what it says now), plus any problem you could not resolve from the chapter or that looks like an error in the chapter itself. Do not edit `docs/`. If a file had no problems, say so.
