# Reviewing a chapter as a student

The repository is /Users/hanh/projects/ragu-tachyon, a VuePress site in `docs/` that teaches Ragu and Tachyon from first principles. Chapter order is the sidebar in `docs/.vuepress/config.js`.

You are a fresh, unanchored reviewer. Read the chapter you are assigned as a capable student would: someone who knows linear algebra, hashes, discrete log, and the definitions of finite fields, polynomials and elliptic curves, but nothing about proving systems beyond what the earlier chapters taught.

## Calibrate first

Read `CLAUDE.md` (writing and scope rules). Then read the benchmark chapters in full:
- `docs/scaling-zcash.md` (chapter 1) is the quality bar.
- `docs/pcd-intro.md` (chapter 2) was recently revised to reach that bar and scored 8.5/10.

Skim the chapter just before yours, and the start of the one after, so you know what the reader already has and what is deferred.

## Judge the assigned chapter

Score it out of 10, where chapter 1 is about 9. Judge:
1. **Motivation**: does each step say why it is needed before taking it?
2. **Clarity for a student**: undefined terms, jumps in algebra, symbols used before introduction, forward references to material the reader cannot use yet.
3. **Worked examples**: does each new idea get a numeric example? Are numbers inserted between `<!-- worked:... -->` markers (generated) rather than typed into prose?
4. **Pacing and density**: is it overloaded with reference detail (internals, code paths, edge cases) that belongs in a later chapter? Is it padded with restatement?
5. **Structure**: does the order of sections build one idea on another? Plain declarative headers?
6. **Writing rules from CLAUDE.md**: agentless passives, rhetorical-question headers, aphoristic one-liners, colon/dash chains, "simply/of course", restatement.
7. **Scope rules**: protocol chapters need a step-by-step derivation, a numeric run on the toy curve, and an informal reason why cheating fails; code-derived claims carry the "Reconstructed from code at commit X" label.
8. **Correctness**: anything that looks mathematically wrong or inconsistent with earlier chapters. Run the worked script (`python3 docs/worked/<slug_with_underscores>.py`) if you want to check numbers.

Do not edit any file.

## Output

Write your review to the file path you were given, in this form:

```
# Review: <slug> (round N)
Score: X/10   (chapter 1 ≈ 9)
Verdict: <one paragraph>

## Must fix (blocks reaching the bar)
1. [section / line numbers] problem — why it hurts a student — concrete suggested fix
...
## Should fix
...
## Keep (what works; the editor must not break these)
...
## Cross-chapter notes
Material that should move to/from another chapter, or broken/missing links to other chapters.
```

Be specific: cite line numbers and quote short phrases. Prefer few high-impact issues over many nits. Then reply with only the score, the verdict paragraph, and the number of must-fix items.
