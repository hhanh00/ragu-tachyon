# Recursion in Ragu

Part four built the pieces one at a time. We have a way to [fold revdot claims](./revdot-folding.md), a [registry](./wiring-and-registry.md) that makes wiring cheap to check, [endoscalars](./endoscalars.md) that let challenges cross the [curve cycle](./curve-cycles.md), and [stages](./staging.md) that let circuits share data. This chapter puts them together into the operation that Ragu runs at every node of the tree.

That operation is one fuse. We list what it has to do, name the stages and commitments it produces, and follow the order of its messages. Then we look at the circuits that divide the work, the split of the transcript between two of those circuits, the public inputs they share, and what a proof hands to its parent. The [next chapter](./compression.md) takes the proof that leaves the root of the tree and makes it short.

::: warning Reconstructed from code at commit 3219e08, not confirmed by the authors
The descriptions of the circuits and stages follow the code and the book's recursion chapters. The numeric runs use the toy sponge and small stand-in values, so they show the structure of the code and not its real contents. We did not build or run the code.
:::

::: tip Terminology
This site says **fuse** for the operation at a node of the tree, [as chapter 2 explained](./pcd-intro.md#fusing-in-ragu), and **native** and **nested** for the two sides of the cycle, [as chapter 13 explained](./curve-cycles.md#_12-cycles-in-ragu). The **decider** is the check that runs [when the recursion ends](./accumulation.md#_3-deciding-a-claim). The code writes `pre_beta` for the challenge from which $\beta$ is [extracted](./endoscalars.md#_9-extracting-bits-from-a-challenge). The two challenges of the revdot fold are $\tau$ and $\tau'$, as in [chapter 14's quotient fold](./revdot-folding.md#_10-the-quotient-fold-in-ragu-s-fuse) (the code's $\mu$, $\mu'$).
:::

## 1. What one fuse has to do

A fuse receives two child proofs and a step, and it has to produce a new proof that a parent can fuse in turn. [Chapter 10](./recursive-proofs.md#_2-a-proof-about-a-verifier) described the idea as a proof about a verifier. The children's verifier cannot run in full, so each child's expensive work joins an accumulator, and a fuse checks the cheap remainder inside its circuits. That remainder is still large compared with one circuit, which [may hold at most](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/polynomials/mod.rs#L35-L37) $n = 2^{11}$ gates.

<!-- worked:remainder -->

Replaying the transcript alone takes $2,304$ gates, more than one circuit holds, as Section 4 counts. The walk that folds the other curve's commitments fills $23$ circuits of its own, a count that [chapter 16 derived](./endoscalars.md#_13-feedback-between-the-walks).

<!-- /worked:remainder -->

So the work has to be divided. The table lists the jobs, the chapter that explained each one, and the circuits that Section 3 assigns it to.

| Job | Explained in | Where the code does it |
| --- | --- | --- |
| Run the application's step | [Chapter 2](./pcd-intro.md#_4-steps) | Application circuit |
| Replay the transcript to get the challenges | [Chapter 3](./statements-and-challenges.md#_7-removing-the-verifier-with-fiat–shamir) | `hashes_1`, `hashes_2` |
| Compute the children's $k(y)$ from their public data | [Chapter 10](./recursive-proofs.md#_3-writing-the-verifier-as-gates) | `hashes_1`, `collapse` |
| Fold the scalars of the revdot claims | [Chapter 14](./revdot-folding.md#_10-the-quotient-fold-in-ragu-s-fuse) | `collapse` |
| Check the batched evaluation $v$ | [Chapter 8](./batched-openings.md#_7-beta-batching) | `compute_v` |
| Connect the challenges to the other side of the cycle | [Chapter 16](./endoscalars.md#_11-transcript-bridging) | `bind_challenges`, `bind_beta` |
| Fold the other curve's commitments | [Chapter 16](./endoscalars.md#_10-folding-with-an-endoscalar) | `bind_endoscalar`, `endoscaling_step` |

Dividing the jobs among circuits creates a new need, because the circuits have to agree with each other. They must use the same challenges, and they must read the same child data. Stages give them shared witness data, and Section 5 gives them shared public inputs. So a fuse produces many small traces where a textbook recursion step would produce one large one. The end of Section 3 counts them, after Sections 2 and 3 have given each one a name.

## 2. The order of the messages

Each challenge has to depend on everything it tests, so the order of the commitments is the backbone of a fuse. Before we list that order, we need names for what gets committed, because the code refers to each group of commitments by a short name and later sections use those names.

### The stages and their names

Most of the shared data of a fuse sits in [stages](./staging.md#_2-splitting-a-trace), the partial traces that several circuits read. The native side has five stages that carry the recursion's data, and a few more that serve the endoscaling walk. The table lists them, with what each one holds and where the code defines it.

| Native stage | What it holds |
| --- | --- |
| [Preamble](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/preamble.rs#L1-L3) | The children's data, which is their headers, their unified instances (Section 5) and their circuit IDs |
| [Inner error](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/inner_error.rs#L1-L3) | The error terms of the first layer of the revdot fold, from [chapter 14](./revdot-folding.md#_10-the-quotient-fold-in-ragu-s-fuse) |
| [Outer error](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/outer_error.rs#L1-L3) | The error terms of the second layer, the values the first layer produced, and the sponge state of Section 4 |
| [Query](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/query.rs#L1-L15) | Claimed values of polynomials at $x$ and $xz$, and the values of the registry polynomial $m$ that the circuits use |
| [Eval](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/eval.rs#L1-L24) | The value of every queried polynomial at $u$, and running sums for the challenge binding of Section 3 |
| [Five points stages](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/points.rs#L14-L20) | The nested-curve commitments that the walk combines, grouped by the challenge each must come before (described after the schedule) |
| [Walk](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/mod.rs#L605-L606) | The bits of the endoscalar and the intermediate points of the walk |

Here the **walk** is the sequence of point additions that multiplies a point by an endoscalar in gates, as in [chapter 16](./endoscalars.md#_10-folding-with-an-endoscalar).

The stages also form a tree, which matters in Section 3. [Chapter 17](./staging.md#_7-a-mask-for-every-polynomial) showed that a stage names a parent and starts in the layout where its parent ends. Indenting each stage under its parent gives the native tree:

- Points binding
  - Preamble
    - Outer error
      - Inner error
    - Query
      - Eval
  - Points children
    - Points `registry_wx`
      - Points ab
        - Points f
          - Walk

The order in the layout is separate from the order of commitment, so inner error sits under outer error in the layout although the fuse commits it first.

Not everything a fuse commits to is a stage. The restrictions $m(w, x_i, Y)$, the new accumulator pair $A$ and $B$, and the batch quotient $f$ are ordinary polynomials. The code still gives each group a short name, `s_prime` for the restrictions, `ab` for the pair and `f` for the quotient, because each group has to reach the transcript in the same way as a stage.

That way is the bridge. The transcript runs in the native field, and a native commitment has coordinates in the other field, so the transcript cannot absorb it directly. [Chapter 17](./staging.md#_11-stages-across-the-cycle) solved this by writing the coordinates into a stage of the nested circuit and committing to that stage on the nested curve, whose coordinates are native. Ragu does this once for each of eight groups, named `preamble`, `s_prime`, `inner_error`, `outer_error`, `ab`, `query`, `f` and `eval`. The nested stage for a group is its **bridge stage**, and the nested commitment to it is its **bridge commitment**. A bridge stage can carry more than coordinates. The `inner_error` bridge, for instance, also holds the nested side's own first-layer error terms, which then reach the transcript at the same moment.

### The schedule

The [code](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/mod.rs#L100-L290) follows one schedule of eleven phases. In each phase the prover commits to something, the transcript absorbs the bridge commitment named in the third column, and the transcript then releases the challenge that tests it.

| Phase | What the prover commits to | Bridge absorbed | Challenge that follows |
| --- | --- | --- | --- |
| 1 | The trace of the application's step, which includes the child and output headers | None | None |
| 2 | The preamble stage, points binding and points children | `preamble` | $w$ |
| 3 | Each child's restriction $m(w, x_i, Y)$, and points `registry_wx` | `s_prime` | $y$, $z$ |
| 4 | The restriction $m(w, X, y)$, and the inner error stage | `inner_error` | $\tau$ |
| 5 | The outer error stage | `outer_error` | $\tau'$ |
| 6 | The new accumulator pair $A$, $B$, and points ab | `ab` | $x$ |
| 7 | The restriction $m(W, x, y)$, and the query stage | `query` | $\alpha$ |
| 8 | The batch quotient $f$, and points f | `f` | $u$ |
| 9 | The eval stage, and after `pre_beta` the nested challenge stage | `eval` | `pre_beta` |
| 10 | The walk stage, and the new batch polynomial $p$ | None | None |
| 11 | The traces of the internal circuits | None | None |

Nearly every row is a step of an earlier chapter. Phases 2 to 4 and 7 run the [registry consistency check of chapter 15](./wiring-and-registry.md#_6-consistency-for-the-registry), phases 4 to 6 run the [quotient fold of chapter 14](./revdot-folding.md#_10-the-quotient-fold-in-ragu-s-fuse), and phases 8 to 10 run the [split accumulation of chapter 12](./split-accumulation.md#_6-a-run-on-the-toy-curve).

The points stages hold nested-curve commitments, and each one is committed in the phase where its points first exist, so that its commitment rides in the bridge absorbed in that phase. The box lists what each of the five holds and which challenge it must precede.

::: details The five points stages

The [code's table](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/points.rs#L14-L20) lists what each holds. Here $m_n$, $A_n$, $B_n$, $F_n$ and $P_n$ are the nested side's own restrictions, accumulator pair, quotient and batch commitment.

| Points stage | What it holds | Fixed before | Carried by |
| --- | --- | --- | --- |
| Points binding | The children's bridge and challenge stage commitments, and their $A_n$, $B_n$, $m_n(W, x, y)$ and $P_n$ | $w$ | `preamble` |
| Points children | The rest of the children's nested commitments | $w$ | `preamble` |
| Points `registry_wx` | The nested restrictions $m_n(w, x_i, Y)$ | $y$ | `s_prime` |
| Points ab | The nested restriction $m_n(w, X, y)$, and the new $A_n$, $B_n$ | $x$ | `ab` |
| Points f | The nested restriction $m_n(W, x, y)$, and $F_n$ | $u$ | `f` |

:::

Phases 9 and 10 need a further word. Phase 9 ends with `pre_beta`, which has to lie in the range from which [chapter 16 extracts an endoscalar](./endoscalars.md#_9-extracting-bits-from-a-challenge). When a squeeze lands outside that range, the prover [re-randomizes the eval stage and squeezes again](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/mod.rs#L261-L287). [Chapter 3](./statements-and-challenges.md#_9-repeated-trials) called this kind of retrying **grinding**, and it showed that the transform already charges a cheater for every retry, since each one costs a hash call. The retry in the code gives a prover nothing it lacked, because a cheating prover could always re-randomize the eval stage and squeeze again on its own. An honest prover [almost never retries](./endoscalars.md#_9-extracting-bits-from-a-challenge), since the values outside the range are a vanishing fraction of the field. The code grinds no other challenge.

The nested **challenge stage** of phase 9 holds the lifts of all nine challenges to the nested field, which [chapter 16 used](./endoscalars.md#_11-transcript-bridging) to carry the challenges across the cycle. The prover can fill it only once `pre_beta` exists, so it comes after the squeeze, and its commitment first reaches a transcript in the parent. For the same reason the check that the stage holds `pre_beta` also waits for the parent, while this fuse checks the other eight challenges. The walk stage comes in phase 10 because it holds the bits of `pre_beta`. The box explains the timing in detail.

::: details Why part of the challenge check waits for the parent

The code [commits the challenge stage after the squeeze](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/mod.rs#L290-L297), without blinding. Its commitment enters no transcript in this fuse, and it first reaches one in the parent, through the parent's points binding stage. The circuits that check it face a timing problem. The `bind_challenges` circuits of Section 3 sum the stage's terms for the first eight challenges into a partial commitment, and that partial sum sits in the eval stage. But the eval bridge is what `pre_beta` hashes, so the eval stage is committed before `pre_beta` exists and its partial sum cannot contain `pre_beta`'s term. The parent's `bind_beta` adds that term later, as Section 3 describes.

:::

Phase 1 has no challenge, because nothing in this fuse's transcript tests the application trace. Its commitment [enters the parent's preamble bridge](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/stages/preamble.rs#L38-L56), in the same way as the internal traces described next.

The internal circuits come last because they prove statements about everything before them. Their traces feed no challenge of this fuse. Instead their commitments [enter the parent's preamble](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/stages/preamble.rs#L38-L47), which puts them on the parent's transcript.

## 3. The internal circuits

We can now say what each native circuit does. The table describes each circuit's job, and the paragraphs after it explain how the circuits divide the stages among themselves.

| Circuit | Its job |
| --- | --- |
| `hashes_1` | Replays the first part of the transcript to get $w$, $y$ and $z$, and saves the sponge state for `hashes_2` (Section 4). It also computes the children's public input values for the internal circuits (Section 5), and checks that each child's circuit ID is a point of the registry's domain |
| `hashes_2` | Resumes from the saved state and replays the rest of the transcript, to get $\tau$, $\tau'$, $x$, $\alpha$, $u$ and `pre_beta` |
| `collapse` | Computes the children's public input values for the application circuit, and checks both layers of the revdot fold down to the new value $c$ |
| `compute_v` | Computes the batched value $v$ from the values held in the query and eval stages. It needs $\beta$ as a native field element, which it gets from the bits of `pre_beta` as [chapter 16 described](./endoscalars.md#_10-folding-with-an-endoscalar) |
| `bind_challenges` (4 circuits) | Each takes two of the transcript's challenges and checks that the nested side's challenge stage holds them, by [walking that stage's generators](./endoscalars.md#_11-transcript-bridging) |
| `bind_beta` | For each child, adds the `pre_beta` term to the partial sum that the child's `bind_challenges` circuits exported, and compares the result with the child's challenge stage commitment. The child could not add that term itself, because its eval stage, which holds the partial sum, was committed before `pre_beta` was squeezed (Section 2). It also checks that the points the child's walk used are the ones the child's public inputs name |
| `bind_endoscalar` | Checks that the bits driving the walk are the bits of `pre_beta` and that the walk's points lie on the curve, and makes the walk's final point public |
| `endoscaling_step` (23 circuits) | Each performs 4 steps of the walk that combines the nested commitments with powers of $\beta$, as in [chapter 16](./endoscalars.md#_10-folding-with-an-endoscalar), which also [derives the count of 23](./endoscalars.md#_13-feedback-between-the-walks) |

A circuit reads a stage by including it in its sum, as [chapter 17 described](./staging.md#_9-two-circuits-on-one-stage). In the layout, the stages a circuit reads sit along one path of the tree from Section 2, and the circuit's own final trace takes the gates after the last stage on that path. The circuit's **final mask** covers those gates, so it is named after that last stage, and circuits that end on the same stage share one final mask, as [chapter 17 noted](./staging.md#_15-staging-in-ragu). For example, `compute_v` reads the preamble, query and eval stages, which lie on one path, so its final mask is named after eval.

Some constraints on a stage, such as a point lying on its curve, have to be written by one of the circuits that read it. [Chapter 17](./staging.md#_10-what-a-mask-does-not-check) explained that the code marks that circuit by loading the stage **enforced**, while the other readers load it unenforced and rely on that one. For example, `bind_endoscalar` checks once that every point in the points stages lies on the curve, and the endoscaling steps rely on that check. Stages that no circuit loads enforced, such as query and eval, get their contents pinned some other way. The first box gives every circuit's stages and final mask, and the second gives the reason behind each enforced load.

::: details Which stages each circuit reads

The last column gives the enforcing circuit, as the [claim list](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L177-L296) and the circuits' [load calls](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/compute_v.rs#L159-L164) show them. The stages in each sum are listed in layout order.

| Circuit | Stages in its sum, in layout order | Final mask | Stages it loads enforced |
| --- | --- | --- | --- |
| `hashes_1` | Preamble, outer error | Outer error | None |
| `hashes_2` | Outer error | Outer error | None |
| `collapse` | Preamble, outer error, inner error | Inner error | [Inner error, outer error](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/collapse.rs#L184-L188) |
| `compute_v` | Preamble, query, eval | Eval | Preamble |
| `bind_challenges` | Preamble, query, eval | Eval | None |
| `bind_beta` | Points binding, preamble | Preamble | None |
| `bind_endoscalar` | The five points stages, walk | Walk | [The five points stages](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/bind_endoscalar.rs#L113-L118) |
| `endoscaling_step` | The five points stages, walk | Walk | None |

The `collapse` row shows why the final mask needs its own column. The circuit reads outer error, but inner error follows outer error in the tree, so `collapse` ends on inner error even though the fuse commits inner error earlier. In the code, the [final mask for inner error](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L374-L376) covers `collapse` alone.

:::

::: warning The stage chains
**Book:** the [recursion chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/index.md?plain=1#L87-L88) gives `hashes_2` the chain preamble, outer error.

**Code at `3219e08`:** [`hashes_2`'s claim](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L192-L197) sums only its own trace and the outer error stage, and [its documentation](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_2.rs#L28-L34) marks the preamble as skipped. The layout still reserves the preamble's gates, which is what [skipping a stage](./staging.md#_9-two-circuits-on-one-stage) means.

This site follows the code.
:::

::: details How each stage's contents get checked

The enforced column of the previous box needs a reason for each stage it covers, and the next table gives one. For the stages that no circuit loads enforced, it gives the check that pins their contents instead.

| Stage | What needs checking | How the code checks it |
| --- | --- | --- |
| Preamble | The children's points and some bits must be well formed | `compute_v` loads it enforced. The code's [comment](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/compute_v.rs#L159-L161) gives no reason for choosing `compute_v`, and any single reader would serve |
| Five points stages | Every point must lie on the curve | `bind_endoscalar` checks this once, and the endoscaling steps rely on it |
| Walk | The bits and intermediate points must be the right ones | No enforced load. `bind_endoscalar` compares the bits wire by wire with `pre_beta`, and each intermediate point must equal the point an endoscaling step computes from enforced inputs, as the [code's comment](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/endoscaling_step.rs#L14-L16) explains |
| Query and eval | The values must be the true evaluations of the committed polynomials. Field elements need no check to be well formed, in our reading | No enforced load. `compute_v` computes $v$ from these values, and the claim $p(u) = v$ joins the accumulator, so a false value leaves a false claim that a later fold or the [final verifier](./compression.md) catches |

:::

One example shows why [stages](./staging.md) were worth building. The `hashes_1` circuit computes each child's public input value and needs the child's data, which sits in the preamble. The `collapse` circuit reads that same data. Both read one polynomial, so a prover cannot show them different children, and only the preamble's commitment has to enter the transcript.

The nested side has a shorter list, with no transcript and no application circuit, as [chapter 13 found](./curve-cycles.md#_12-cycles-in-ragu). Its [`collapse`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/circuits/collapse.rs#L1-L24) checks the nested fold, its [`compute_v`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/circuits/compute_v.rs#L1-L32) computes the nested $v$, and [26 endoscaling steps](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L2372) combine the native commitments, a count that [chapter 16 also derives](./endoscalars.md#_13-feedback-between-the-walks).

The application's circuit [uses no stages](./staging.md#_15-staging-in-ragu). All of the machinery above sits beside it and leaves its budget of gates to the application.

### What one fuse produces

With the stages and circuits named, we can count what [one call to `fuse`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/mod.rs#L74-L81) commits. The count matters in two places. Section 7 argues that a proof keeps the same shape at every depth, and the [next chapter](./compression.md) measures how large that shape is.

<!-- worked:census -->

The table counts the polynomials of one fuse in the standard profile, side by side.

|  | Native side | Nested side |
| --- | --- | --- |
| Circuit traces | $34$: the $33$ internal circuits of this section and the application | $28$: $26$ endoscaling steps, `collapse` and `compute_v` |
| Stages | $11$: preamble, inner error, outer error, query, eval, the five points stages and the walk | $11$: the eight bridge stages, the challenge stage, and one stage each for the endoscalar's bits and the points it walks |
| Accumulators | $4$: $A$, $B$, $m(W, x, y)$ and $p$ | $4$: their nested counterparts |
| Used only inside the fuse | $4$: $m(w, x_0, Y)$, $m(w, x_1, Y)$, $m(w, X, y)$ and $f$ | $4$: their nested counterparts |
| Committed in all | $53$ | $47$ |

The schedule commits $100$ polynomials in all. A proof carries $92$ of them to its parent, which is the count [the code records](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L2364-L2379). The other $8$ serve only the fuse that made them. Their values at the fuse's points sit in the query and eval stages, and the fuse folds the polynomials themselves into its new batch polynomial $p$, so a parent that holds $p$ never needs them again. The code [marks them as ephemeral](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/_03_s_prime.rs#L23-L24).

<!-- /worked:census -->

The traces and stages also set how many revdot claims the fuse folds, since each child's trace and stage commitments become claims. The box breaks that count down by kind on each side.

::: details Counting the claims

<!-- worked:census-claims -->

The claims follow the same split. The native side folds $86$ revdot claims, a count that [chapter 17 derived](./staging.md#_15-staging-in-ragu). Its $16$ mask claims are one for each of the $11$ stages and one for each of the $5$ final masks, and those $5$ are exactly the distinct entries of the "Final mask" column in the stage table of this section, namely outer error, inner error, eval, preamble and walk. The nested side folds $72$, which are $2$ raw claims (one per child), $56$ circuit claims ($28$ per child) and $14$ mask claims, one for each of its $11$ stages and $3$ for final masks.

<!-- /worked:census-claims -->

:::

## 4. Splitting the transcript

The transcript has to be replayed in circuit, because the [Fiat–Shamir challenges](./statements-and-challenges.md#_7-removing-the-verifier-with-fiat–shamir) would otherwise be numbers that the prover merely asserts. One circuit cannot hold the whole replay, as a count of gates shows.

<!-- worked:perm-cost -->

A permutation costs [$288$ gates](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_primitives/src/poseidon/tests/mod.rs#L96), and the code documents [$3$ permutations](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_1.rs#L7-L17) in the first half and [$5$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_2.rs#L7-L23) in the second. Together that makes $8$ permutations and $2,304$ gates, which already exceeds the limit of $2,048$ gates per circuit before any other check runs. The two halves cost $864$ and $1,440$ gates, so each fits.

<!-- /worked:perm-cost -->

So the replay has to cross a circuit boundary, and the sponge's state has to cross with it. The second circuit cannot recompute the state without repeating the permutations it is trying to avoid, and passing the state as a public input would [add wires to every $k(Y)$](./staging.md#_1-two-jobs-for-a-partial-commitment). The code places it in a stage. The state is known once the inner error bridge is absorbed, and the outer error stage is the next one committed, because it holds values folded with the $\tau$ that the state produces.

![Eight bridge commitments in a row, with the challenge each one releases below it. A blue line marks the first three as hashes_1, and a teal line marks the last five as hashes_2. An arrow takes the sponge state from the inner error commitment into a box for the outer error stage, and another arrow takes it to hashes_2, which squeezes mu first.](./manim/ragu-recursion-transcript.png)

The figure labels the fold challenges with the code's names, so its $\mu$ and $\mu'$ are our $\tau$ and $\tau'$.

We run this on the [toy sponge from chapter 3](./statements-and-challenges.md#a-toy-poseidon). The bridge commitments are points on $E'$, whose coordinates lie in $\F_{43}$, the field the sponge works in. The first point is the one [chapter 17 built](./staging.md#_11-stages-across-the-cycle), and the others are stand-ins. The table gives each point with the challenges squeezed after it.

<!-- worked:transcript-run -->

| Bridge commitment | Toy point on $E'$ | Squeezed next | Replayed by |
| --- | --- | --- | --- |
| `preamble` | $(21,\,25)$ | $w = 11$ | `hashes_1` |
| `s_prime` | $(32,\,3)$ | $y = 4$, $z = 10$ | `hashes_1` |
| `inner_error` | $(34,\,3)$ | $\tau = 2$ | `hashes_1`, then saved |
| `outer_error` | $(35,\,21)$ | $\tau' = 10$ | `hashes_2` |
| `ab` | $(37,\,7)$ | $x = 4$ | `hashes_2` |
| `query` | $(40,\,18)$ | $\alpha = 12$ | `hashes_2` |
| `f` | $(42,\,7)$ | $u = 25$ | `hashes_2` |
| `eval` | $(2,\,12)$ | $\text{pre\_beta} = 33$ | `hashes_2` |

<!-- /worked:transcript-run -->

Splitting the replay at `inner_error` changes none of the challenges. The box shows the saved state and the permutation count of each half.

::: details The split on the toy sponge

<!-- worked:transcript-split -->

The first half ends by permuting and saving the three cells of the state, $(2, 42, 12)$. The second half loads those cells and squeezes $\tau = 2$ with no further permutation, so the second half's five permutations begin when it absorbs `outer_error`. We ran the sponge once straight through and once split at this point, and all nine challenges agree. The toy sponge takes $3$ permutations in the first half and $5$ in the second, as the code does, because we leave out the domain tag and its rate of 2 fits one point per permutation.

<!-- /worked:transcript-split -->

:::

Reading the state from a stage leaves one question, which is what forces the stage to hold the right value. Only `hashes_1` knows that value, having computed it, so the check goes [in that circuit](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_1.rs#L281-L286):

```rust
// save_state() applies a permutation (since there's pending absorbed data)
// and returns the raw state, ready for squeeze-mode resumption in hashes_2.
transcript
    .save_state(dr)
    .expect("save_state should succeed after absorbing")
    .enforce_equal(dr, &outer_error.sponge_state)?;
```

Without this line, a prover could pick the state and with it the challenges. The tamper below changes only the first cell of the honest saved state, which the box above shows.

<!-- worked:transcript-tamper -->

Suppose a prover wants $\tau = 9$, and it writes the state $(9, 42, 12)$ into `outer_error`. The second half alone would resume from this state and produce $\tau = 9$ and $\tau' = 20$. Of the $79,507$ possible states, $1,849$ give the wanted $\tau$, but the first half compares the stage with the state it computed, and exactly $1$ state passes that comparison, the honest one. Both circuits read one committed stage polynomial, so the prover cannot show them different values.

<!-- /worked:transcript-tamper -->

## 5. Public inputs

Each circuit also has a public input polynomial $k(Y)$, and a parent has to compute $k(y)$ for each of a child's circuits. If every internal circuit exposed its own values, a parent would compute many different polynomials. The code avoids that with a **unified instance**, one [structure of values](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/unified.rs#L274-L332) that nearly all internal circuits expose in full, so that one computed $k(y)$ serves them all.

Sharing an instance raises the question of who checks each value, since a circuit that merely exposes a value proves nothing about it. The code assigns each slot to exactly one owner circuit, which constrains the value, and soundness rests on those constraints. The prover code also [asserts](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/unified.rs#L155-L156) that every slot was filled, but that is a consistency check for honest provers and adds nothing to soundness. Other circuits read a slot as a witness, and the shared $k(y)$ forces them to agree with the owner. The table below lists the owners.

<!-- worked:slots -->

| Slots | Wires | Owner |
| --- | --- | --- |
| Bridge commitments for preamble, $s'$ and inner error; $w$, $y$, $z$ | $9$ | `hashes_1` |
| Bridge commitments for outer error, $ab$, query, $f$ and eval; $\tau$, $\tau'$, $x$, $\alpha$, $u$, `pre_beta` | $16$ | `hashes_2` |
| $c$ | $1$ | `collapse` |
| $v$ | $1$ | `compute_v` |
| The nested challenge stage's partial commitment | $2$ | The last `bind_challenges` |
| $P_n$, $A_n$, $B_n$ and the nested registry restriction | $8$ | `bind_endoscalar` |

The rows add to $13$ points and $11$ elements, which is the code's [$37$ wires](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/unified.rs#L43).

<!-- /worked:slots -->

Recursion uses [three forms of $k(Y)$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/preamble.rs#L112-L144) over these values, plus a fourth with no wires of its own. Each one lists some wires and appends the [constant wire's 1](./nark.md#_15-the-constant-wire), and the list becomes the coefficients of $k(Y)$, highest power first.

- $k_{\text{unified}}$ lists the unified instance, then a $0$.
- $k_{\text{headers}}$ lists the unified instance, the left and right child headers, then a $0$.
- $k_{\text{app}}$ lists the left, right and output headers.

Because the 1 is the constant term, the last wire before it is the coefficient of $Y$. Section 6 uses that coefficient. The box writes the three forms as formulas.

::: details The three forms as Horner evaluations

$$k_{\text{unified}}(Y) = \text{Horner}(\text{unified} \,\|\, 0 \,\|\, 1,\ Y),$$

$$k_{\text{headers}}(Y) = \text{Horner}(\text{unified} \,\|\, \text{left} \,\|\, \text{right} \,\|\, 0 \,\|\, 1,\ Y),$$

$$k_{\text{app}}(Y) = \text{Horner}(\text{left} \,\|\, \text{right} \,\|\, \text{output} \,\|\, 1,\ Y).$$

Here Horner over wires $h_0, \ldots, h_{m-1}$ and the final 1 means $(\cdots(h_0 y + h_1) y + \cdots + h_{m-1}) y + 1$, so the last wire before the 1 is the coefficient of $Y$.

:::

The `hashes_1` circuit uses $k_{\text{headers}}$ because it also exposes the child headers. The application circuit exposes the same headers through $k_{\text{app}}$. A parent computes both values from the one preamble, so together the two claims stop a proof from using one pair of headers in the step and another in the recursion.

The fourth form belongs to the endoscaling steps. An endoscaling step exposes [nothing but the zero](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/endoscaling_step.rs#L19-L24), so its polynomial is $k(Y) = 1$.

The code calls $k_{\text{headers}}$ [`unified_bridge_ky`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L37-L38). That name has nothing to do with the bridge stages and bridge commitments of Section 2, so we use a different one here.

<!-- worked:k-run -->

Take a toy unified output of five wires, $(21, 25, 11, 4, 10)$, which are the first bridge point and the challenges $w$, $y$ and $z$ from the run above. Take child headers $(8, 3)$ and $(12, 3)$, whose second entry is the suffix, and the output header $(20, 3)$. At $y = 4$:

| Polynomial | Wires, in order | Value at $y$ | Coefficient of $Y$ |
| --- | --- | --- | --- |
| $k_{\text{unified}}$ | Unified output, $0$ | $39$ | $0$ |
| $k_{\text{headers}}$ | Unified output, left, right, $0$ | $26$ | $0$ |
| $k_{\text{app}}$ | Left, right, output | $6$ | $3$ |
| Endoscaling step | $0$ | $1$ | $0$ |

Horner's rule reaches $40$ after the five unified wires, and both $k_{\text{unified}}$ and $k_{\text{headers}}$ continue from that value. Each table entry also matches a direct evaluation of the polynomial.

<!-- /worked:k-run -->

These values reach the fold through the parent. Its `hashes_1` and `collapse` circuits [compute each child's values](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_1.rs#L265-L272) from the preamble stage with gates, at the $y$ of the current fuse, and those values become the targets of the claims being folded.

::: warning The unified instance
**Book:** the [public inputs chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/public_inputs.md?plain=1#L81-L83) says that the shared structure holds 29 wires, from eight commitments and thirteen field elements. The [recursion chapter's list](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/index.md?plain=1#L44-L50) gives nine challenges and two final values, which makes eleven elements. The public inputs chapter also says that [four internal circuits](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/public_inputs.md?plain=1#L96-L97) share $k_{\text{unified}}$.

**Code at `3219e08`:** thirteen points and eleven elements, which makes the 37 wires above. The five additional points are in the last two rows of the table. The [count of circuits sharing $k_{\text{unified}}$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L33-L46) is nine, because `bind_challenges` has four instances.

This site follows the code.
:::

## 6. Keeping internal and application circuits apart

The registry holds internal and application circuits side by side, and [a proof names its application circuit](./wiring-and-registry.md#_9-what-the-prover-may-select) by a domain point the prover selects. So a prover could try to name an internal circuit and claim its trace as an application step. To rule that out, the code makes the two kinds of $k(Y)$ unable to coincide. Each internal circuit ends its output with a zero, and each application header ends with a [suffix that is never zero](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/header.rs#L13-L27).

Section 5 showed that the last wire before the final 1 becomes the coefficient of $Y$ in $k(Y)$, and the last column of its toy table recorded that coefficient. It was zero for every internal circuit and equal to the header's suffix for the application. That one coefficient is enough to keep the two kinds apart, and a toy run shows how much the suffix matters.

<!-- worked:substitution -->

Take a toy internal circuit with two output wires and its zero, and a toy application circuit with a one-entry header and its suffix, and compare their $k(Y)$ over $\F_{43}$. If an application could use the suffix $0$, then $43$ of the $79,507$ possible choices of wires would make the two polynomials identical, and for those the swap would pass at every $y$. With the suffixes $3$, $4$ and $5$ we tried every choice and found none that makes them identical, and the two values agree at no more than $2$ of the $42$ nonzero values of $y$.

<!-- /worked:substitution -->

In words, an internal $k(Y)$ always has $Y$-coefficient $0$ and an application $k(Y)$ always has $Y$-coefficient $s \ne 0$, so no choice of the other wires makes the two polynomials equal. Two different polynomials of low degree agree at only a few points, so at a random $y$ their values differ except with negligible probability, and a prover cannot pass an internal trace off as an application step. The box carries out the algebra behind the toy count.

::: details The algebra of the toy run

<!-- worked:substitution-detail -->

Let an internal circuit expose wires $(a, b)$ and its zero suffix, so that $k_{\text{int}}(Y) = aY^3 + bY^2 + 0 \cdot Y + 1$, and let an application circuit expose a header $(d, s)$, so that $k_{\text{app}}(Y) = dY^2 + sY + 1$. Their difference is $aY^3 + (b - d)Y^2 - sY$. If an application could use the suffix $s = 0$, the difference would vanish whenever $a = 0$ and $b = d$. That happens for $43$ of the $79,507$ triples $(a, b, d)$, and for those the swap would pass at every $y$. For $s = 3, 4, 5$ the coefficient of $Y$ in the difference is $-s$, which is not zero, so no choice of $a$ and $b - d$ can cancel it. We tried all $1,849$ pairs $(a, b - d)$ for each $s$ and found none that makes the polynomials identical. At a nonzero $y$ the difference vanishes only where $ay^2 + (b - d)y - s$ does, and a polynomial of degree $2$ has at most $2$ roots. The worst pair reaches that bound, so the two values agree at no more than $2$ of the $42$ nonzero values of $y$. On a real field the same count of roots is a negligible fraction.

<!-- /worked:substitution-detail -->

:::

This also explains why an endoscaling step needs the zero although it exposes nothing. [Its comments](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/endoscaling_step.rs#L19-L24) say that the suffix is what stops a step from satisfying an application instance, given that the application's circuit ID may name any native slot. The nested registry [holds internal circuits only](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/unified.rs#L28-L29), so it omits the zero.

::: warning The first application suffix
**Book:** [application-defined suffixes begin at two](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/public_inputs.md?plain=1#L107-L109), with one reserved for the trivial header.

**Code at `3219e08`:** [three values are reserved](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/header.rs#L13-L27), with 0 for fixed circuits, 1 for the unit header and 2 for the `Dummy` header of the base case, so [application suffixes begin at three](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/header.rs#L68-L73).

This site follows the code. The book's argument is unaffected, since it needs only that the suffix is nonzero.
:::

::: tip Why the value 2 is reserved
The suffix 2 marks the base case of [chapter 10](./recursive-proofs.md#the-base-case-in-ragu), where [`collapse` waives its final comparison](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/collapse.rs#L276-L287). So a step whose suffix is a witness, and not a constant, has to [constrain that wire away from 2](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/step/encoder.rs#L172-L177), or it could claim the waiver.
:::

## 7. What a proof carries to its parent

A parent does not repeat the checks in a child's circuits. It folds the child's claims into its own accumulators and reads the child's public data. The table lists what it takes from each child.

| From the child | What the parent does with it | Explained in |
| --- | --- | --- |
| Headers and unified instance | Holds them in the preamble and computes the child's $k(y)$ values | Section 5 |
| $(A, B, c)$ | Adds the pair as a [raw claim with target $c$](./revdot-folding.md#_10-the-quotient-fold-in-ragu-s-fuse), folded into the new $(A, B, c)$ | [Chapter 14](./revdot-folding.md) |
| Each trace and stage commitment | Adds a circuit claim or mask claim to the same fold | [Chapter 17](./staging.md) |
| $(P, u, v)$ | Adds [the claim $p(u) = v$](./split-accumulation.md#_11-split-accumulation-in-ragu) to its batch, folded into the new $(P, u, v)$ | [Chapter 12](./split-accumulation.md) |
| $m(W, x_i, y_i)$ | Checks it against the parent's own restriction, as described below the table | [Chapter 15](./wiring-and-registry.md) |
| Nested points and challenge partial | Walks the points and completes the challenge binding in `bind_beta` | [Chapter 16](./endoscalars.md) |

Three of these rows are accumulators, namely $(A, B, c)$, $(P, u, v)$ and the restriction $m(W, x_i, y_i)$. A parent receives two of each, one from each child, and it has to leave exactly one of each, because otherwise its own parent would receive more than two and the work per fuse would grow with depth. A toy run shows each pair becoming one. We reuse the worked runs of chapters 14, 12 and 15, with one side of the cycle only, so the challenge values below come from those chapters' runs and not from the transcript run of Section 4.

<!-- worked:shape -->

| Accumulator | Left child | Right child | Parent leaves |
| --- | --- | --- | --- |
| $(A, B, c)$ | $((22,\,24),\ (1,\,29),\ 13)$ | $((7,\,25),\ (27,\,30),\ 35)$ | $((4,\,6),\ (20,\,25),\ 19)$ |
| $(P, u, v)$ | $((23,\,24),\ 17,\ 23)$ | $((24,\,1),\ 30,\ 6)$ | $((25,\,29),\ 12,\ 10)$ |
| Restriction | $m(W, 9, 7)$, committed as $(5,\,29)$ | $m(W, 37, 34)$, committed as $(27,\,30)$ | $m(W, 21, 12)$, committed as $(23,\,7)$ |

<!-- /worked:shape -->

Each row has two inputs and one output, which is the point of the table. The first row uses the quotient fold of chapter 14, the second the batching of chapter 12, and the third the registry chain of chapter 15. The box gives the intermediate values of each fold.

::: details How each row was folded

<!-- worked:shape-detail -->

In the first row the children's pairs are the first two proof claims of chapter 14. The parent folds them with one layer of [that chapter's quotient fold](./revdot-folding.md#_10-the-quotient-fold-in-ragu-s-fuse), the fold the schedule runs in phases 4 and 5. For two claims the quotient has the single coefficient $19$, and at $\tau = 20$, the challenge of chapter 14's run, the weights are $(24, 20)$ and the new value is $c^* = 23 + 36 \cdot 19 = 19$. The folded vectors satisfy $\revdot{\v{a}}{\v{b}} = 19$.

In the second row the left child holds the first accumulator of [chapter 12's run](./split-accumulation.md#_6-a-run-on-the-toy-curve) and the right child holds a fresh one. The parent batches the two claims $p_L(17) = 23$ and $p_R(30) = 6$ with $\alpha = 7$, $u = 12$ and $\beta = 19$, and the new $p$ evaluates to $10$ at $12$.

The third row is the registry run of [chapter 15](./wiring-and-registry.md#_6-consistency-for-the-registry), with the parent's fresh $w = 14$.

<!-- /worked:shape-detail -->

:::

The restriction row packs two openings into one step, so here they are in turn. The parent does not keep the child's $m(W, x_i, y_i)$. It opens that polynomial at the parent's fresh $w$, and the [chain of restrictions in chapter 15](./wiring-and-registry.md#_6-consistency-for-the-registry) carries the result into the parent's single new $m(W, x, y)$. The parent then opens its new restriction at the [child's circuit ID](./wiring-and-registry.md#_7-selecting-a-circuit), which gives the wiring value $s(x, y)$ of the child's circuit, the value it needs for the child's circuit claim. In the toy run the two children's circuits are A and B of chapter 15, at the domain points $\omega^0$ and $\omega^1$:

<!-- worked:restriction-openings -->

| Polynomial | Opened at | Value | What the value is for |
| --- | --- | --- | --- |
| Left child's $m(W, 9, 7)$ | $W = w = 14$ | $10$ | Enters the chain of restrictions |
| Right child's $m(W, 37, 34)$ | $W = w = 14$ | $7$ | Enters the chain of restrictions |
| Parent's $m(W, 21, 12)$ | $W = w = 14$ | $12$ | Closes the chain |
| Parent's $m(W, 21, 12)$ | $W = \omega^0 = 1$ | $2$ | $s_A(21, 12)$, for the left child's circuit claim |
| Parent's $m(W, 21, 12)$ | $W = \omega^1 = 42$ | $17$ | $s_B(21, 12)$, for the right child's circuit claim |

<!-- /worked:restriction-openings -->

All of these values sit in the query stage, and only one restriction leaves the fuse.

The real fuse folds far more into each accumulator than the toy run does, since the children's circuit and mask claims join the same $(A, B, c)$ and every queried polynomial joins the same $(P, u, v)$. The count of inputs changes, but the output is still one of each, per side of the cycle. So a proof has the same shape at every depth. A child's internal circuits do not run again in the parent, and they cannot be skipped either, since their claims are among those folded.


## 8. Why cheating fails in a fuse

The earlier chapters counted cheating at each building block, and those counts still apply here. This chapter added a new risk, which comes from dividing one verifier among many circuits. A prover might try to show different circuits different data, or to exploit a check that one circuit assumes another has made. The sections above met each form of that attempt, and we collect them here.

- **Choosing the challenges.** The second transcript circuit resumes from a sponge state that it reads from a stage, so a prover might write a state that gives the challenges it wants. Section 4 counted how many states give a chosen $\tau$, and showed that `hashes_1` rejects every one except the state it computed itself.
- **Showing two circuits different children.** `hashes_1` and `collapse` both need the children's data, and both read it from the one preamble polynomial, whose mask stops a circuit's final trace from overwriting it. So the two circuits see the same children, and only one commitment has to reach the transcript.
- **Leaving a shared value unchecked.** Every slot of the unified instance has one owner circuit that constrains it (Section 5). The other circuits read the slot as a witness, and the shared $k(y)$ makes them agree with the owner.
- **Leaving a stage's contents unchecked.** Every stage that needs a check of its own, such as points lying on the curve, has one circuit that loads it enforced (Section 3).
- **Passing off an internal circuit as a step.** The zero at the end of an internal circuit's output and the nonzero suffix of an application header keep the two kinds of $k(Y)$ apart, and Section 6 counted how often they could agree by chance.
- **Skipping a child's checks.** A parent does not rerun a child's internal circuits, but it folds their claims into its accumulator (Section 7), and the fold's error terms are committed before the challenges that weight them, as [chapter 14](./revdot-folding.md) showed.

The argument is informal, and it rests on the assumptions of the earlier chapters. Nobody knows a relation among the generators on either curve, so commitments bind. The transcript behaves as a random oracle, and each challenge comes after the bridge commitment that carries what it tests. The checks that cross the cycle rely on the endoscalar lift being injective, as [chapter 16](./endoscalars.md#_12-why-cheating-fails) found for Pasta.

## 9. Where this chapter leaves us

This chapter took the following steps:

1. A fuse divides its checks among many small circuits, because each circuit holds at most $2^{11}$ gates, and those circuits share data through stages and public inputs.
2. The native stages are the preamble, inner error, outer error, query and eval stages, together with the points stages and the walk. Each group of commitments reaches the transcript through a bridge stage on the nested curve, whose commitment the transcript absorbs.
3. One transcript runs through eleven phases, each bridge commitment coming before the challenge that tests it.
4. The replay takes more gates than one circuit holds, so `hashes_1` and `hashes_2` share it, with the sponge state held in the outer error stage and checked by the first circuit.
5. The internal circuits expose one unified instance, with each slot owned by one circuit, so one $k(y)$ serves them.
6. Internal outputs end in zero and application headers end in a nonzero suffix, so the coefficient of $Y$ keeps the two kinds of circuit apart.
7. A parent folds three accumulators per side from each child, namely $(A, B, c)$, $(P, u, v)$ and $m(W, x, y)$, so a proof keeps its shape at every depth.

That shape has a cost. Every accumulator, stage and trace is a polynomial with $2^{13}$ coefficients, and a parent needs all of them to compute its fold, so a proof that leaves the root of the tree carries every one. A verifier outside the tree wants something far smaller, and it also still owes the deferred work that the accumulators postponed. The [next chapter](./compression.md) replaces the polynomials with commitments and a few values, and it runs the final checks on the toy curve.
