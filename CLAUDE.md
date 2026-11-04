Avoid agentless passive constructions. ("The solution requires promoting coefficients to operators.") Give sentences a real subject and active verb — either the thing being acted on ("promoting the coefficients to operators solves this") or direct address to the reader ("promote the coefficients to operators"). Don't hide actions behind abstractions like "the solution" or "the theory requires."
No rhetorical-question section headers. ("Which picture suits quantum fields?", "What objects are being constructed?") Use plain declarative headers instead ("Choosing a picture," "Building the fields").
Avoid aphoristic one-liners used for dramatic effect. ("The split is bookkeeping, not physics, but relativity has a strong preference.") If a punchy line like this appears, follow it immediately with a plain-language explanation rather than letting it stand alone as a flourish.
Limit colon/dash-heavy clipped sentence structure. Vary sentence length and connect ideas with ordinary transitions ("because," "so," "which means") instead of chaining fragments with dashes and colons.
Cut redundant restatement. When two sections explain the same point in different phrasing, merge them into one or remove the duplicate — don't keep both just because each phrasing sounds nice.
Avoid labels implying the material is self-evidently easy. ("The Basic Operation," "simply," "of course," "trivially.") Let the reader judge difficulty themselves.
Motivate before asserting. Walk through why a step is taken before declaring the result, rather than announcing the conclusion and justifying it afterward.
Keep a consistent, plain expository tone throughout. Write as if explaining to a capable peer, not performing for an audience or demonstrating command of the material.

## Site scope

This site explains Ragu and Tachyon from first principles and is unofficial.

Assume readers know linear algebra, hashes, discrete log, and the definitions of finite fields, polynomials, and elliptic curves. Assume no knowledge of proving systems.

Go well beyond the Ragu Book in detail, with little coverage of programming or APIs. Teach the general construction first, then present Ragu's changes as differences from it. Cover Ragu's arithmetization in depth and compare others only briefly.

Each protocol chapter needs a step-by-step derivation with no skipped algebra, a numeric run on the shared toy curve, and an informal explanation of why cheating fails. State assumptions, but leave out security proofs, reductions, and formal definitions of soundness.

Generate every worked number with a script in `docs/worked/` and insert it with `pnpm docs:worked`. Do not type computed values into the prose.

Pin code excerpts and code-derived claims to a named commit. Label anything rebuilt from code or papers as "Reconstructed from code at commit X, not confirmed by the authors". Where the official description and the code disagree, show both.
