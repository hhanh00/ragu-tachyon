# Recursion in Ragu

Part four built the pieces one at a time. We have a way to [fold revdot claims](./revdot-folding.md), a [registry](./wiring-and-registry.md) that makes wiring cheap to check, [endoscalars](./endoscalars.md) that let challenges cross the [curve cycle](./curve-cycles.md), and [stages](./staging.md) that let circuits share data. This chapter puts them together into the operation that Ragu actually runs, and then follows a finished proof out of the tree.

The first half describes one fuse. We list what it has to do, the order of its messages, the circuits that divide the work, the split of the transcript between two of those circuits, and the public inputs they share. The second half describes compression, with a complete run on the toy curve, and then covers what the verifier pays, the size of the result, rerandomization, and the comparison with Orchard.

::: warning Reconstructed from code at commit 3219e08, not confirmed by the authors
The descriptions of the circuits and of compression follow the code and the book's recursion chapters. The numeric runs use small circuits of our own and a shortened instance, so they show the structure of the code and not its real contents. The sizes come from our reading of the code's wire format. We did not build or run the code, and we did not run its benchmarks.
:::

::: tip Terminology
This site says **fuse** for the operation at a node of the tree, [as chapter 02 explained](./pcd-intro.md#_9-fusion-in-ragu), and **native** and **nested** for the two sides of the cycle, [as chapter 13 explained](./curve-cycles.md#_12-cycles-in-ragu). The **decider** is the check that runs [when the recursion ends](./accumulation.md#_3-deciding-a-claim). The code writes `pre_beta` for the challenge from which $\beta$ is [extracted](./endoscalars.md#_9-extracting-bits-from-a-challenge).
:::

## 1. What one fuse has to do

A fuse receives two child proofs and a step, and it has to produce a new proof that a parent can fuse in turn. [Chapter 10](./recursive-proofs.md#_2-a-proof-about-a-verifier) described the idea as a proof about a verifier. The children's verifier cannot run in full, so each child's expensive work joins an accumulator, and a fuse checks the cheap remainder inside its circuits. That remainder is still large, and a circuit [may hold at most](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/polynomials/mod.rs#L35-L37) $n = 2^{11}$ gates. These are the jobs:

| Job | Explained in | Where the code does it |
| --- | --- | --- |
| Run the application's step | [Chapter 02](./pcd-intro.md#_4-steps) | Application circuit |
| Replay the transcript to get the challenges | [Chapter 03](./statements-and-challenges.md#_8-removing-the-verifier-with-fiat–shamir) | `hashes_1`, `hashes_2` |
| Compute the children's $k(y)$ from their public data | [Chapter 10](./recursive-proofs.md#_3-writing-the-verifier-as-gates) | `hashes_1`, `collapse` |
| Fold the scalars of the revdot claims | [Chapter 14](./revdot-folding.md#_10-the-quotient-fold-in-ragu-s-fuse) | `collapse` |
| Check the batched evaluation $v$ | [Chapter 08](./batched-openings.md#_7-beta-batching) | `compute_v` |
| Connect the challenges to the other side of the cycle | [Chapter 16](./endoscalars.md#_11-transcript-bridging) | `bind_challenges`, `bind_beta` |
| Fold the other curve's commitments | [Chapter 16](./endoscalars.md#_10-folding-with-an-endoscalar) | `bind_endoscalar`, `endoscaling_step` |

Dividing the jobs among circuits creates a new need, because the circuits have to agree with each other. They must use the same challenges, and they must read the same child data. Stages give them shared witness data, and Section 5 gives them shared public inputs. So a fuse produces many small traces where a textbook recursion step would produce one large one.

<!-- worked:census -->

In the standard profile, one fuse therefore fills $45$ native polynomials, of which $34$ are circuit traces and $11$ are stages, and $39$ nested polynomials, and it adds the $a$, $b$, `registry_xy` and $p$ polynomials on each side, for [$92$ in all](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L2364-L2379). The native side folds $86$ revdot claims and the nested side folds $72$.

<!-- /worked:census -->

Each internal circuit's claim counts once per child in the fold, since a parent checks both children's copies. All of these polynomials come from [one call to `fuse`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/mod.rs#L74-L81).

## 2. The order of the messages

Each challenge has to depend on everything it tests, so the order of the commitments is the backbone of a fuse. The [code](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/mod.rs#L100-L290) follows one schedule, and its phases sit in numbered files:

| Phase | File | What the prover computes | Challenge that follows |
| --- | --- | --- | --- |
| 1 | `_01_application` | The step's trace, with the headers | None |
| 2 | `_02_preamble` | A stage holding the children's data | $w$ |
| 3 | `_03_s_prime` | The restrictions $m(w, x_i, Y)$ for each child | $y$, $z$ |
| 4 | `_04_inner_error` | $m(w, X, y)$ and the first layer's quotients | $\mu$ |
| 5 | `_05_outer_error` | The second layer's quotient, the groups' values and the saved sponge state | $\mu'$ |
| 6 | `_06_ab` | The new accumulator pair $A$, $B$ | $x$ |
| 7 | `_07_query` | $m(W, x, y)$ and the values that the registry claims | $\alpha$ |
| 8 | `_08_f` | The batch quotient $f$ | $u$ |
| 9 | `_09_eval` | The value of every polynomial at $u$ | `pre_beta` |
| 10 | `_10_p` | The new batch polynomial $p$ and the walks over its points | None |
| 11 | `_11_circuits` | The traces of the internal circuits | None |

Nearly every row is a step of an earlier chapter. Phases 2 to 4 and 7 run the [walk of chapter 15](./wiring-and-registry.md#_6-consistency-for-the-registry), phases 4 to 6 run the [quotient fold of chapter 14](./revdot-folding.md#_10-the-quotient-fold-in-ragu-s-fuse), and phases 8 to 10 run the [split accumulation of chapter 12](./split-accumulation.md#_6-a-run-on-the-toy-curve).

Two details of the last rows matter later. Only `pre_beta` is ground, because it has to lie in the endoscalar range, so the prover [re-blinds the eval stage and tries again](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/mod.rs#L261-L287) until it does. And the internal circuits come last, because they prove statements about everything before them. Their traces feed no challenge of this fuse. Instead their commitments [enter the parent's preamble](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/stages/preamble.rs#L38-L47), which puts them on the parent's transcript.

## 3. The internal circuits

We can now say what each circuit does. This table extends the one in [Section 15 of the staging chapter](./staging.md#_15-staging-in-ragu), and it adds a column for the job:

| Circuit | Its job | Stages in its sum | Final mask |
| --- | --- | --- | --- |
| `hashes_1` | Derives $w$, $y$, $z$, saves the sponge state, enforces the children's unified $k(y)$ and that their circuit IDs are domain points | Preamble, outer error | Outer error |
| `hashes_2` | Resumes from the saved state and derives $\mu$, $\mu'$, $x$, $\alpha$, $u$, `pre_beta` | Outer error | Outer error |
| `collapse` | Enforces the children's application $k(y)$, and checks both layers of the fold down to $c$ | Preamble, inner error, outer error | Inner error |
| `compute_v` | Computes $v$ from the query and eval stages, using the lift of $\beta$ | Preamble, query, eval | Eval |
| `bind_challenges` (4 circuits) | Recomputes the nested challenge stage's commitment from the transcript's challenges | Preamble, query, eval | Eval |
| `bind_beta` | Finishes that binding for each child, and ties the child's walked points to its unified instance | Points binding, preamble | Preamble |
| `bind_endoscalar` | Ties the walk's bits to `pre_beta`, enforces curve membership, and exports the walk's end point | The five input points stages, walk | Walk |
| `endoscaling_step` (23 circuits) | Performs 4 endoscalings of the Horner walk over the nested batch | The five input points stages, walk | Walk |

The stage column shows why [stages](./staging.md) were worth building. The `hashes_1` circuit computes each child's $k(y)$ and needs the child's data, which sits in the preamble. The `collapse` circuit reads that same data. Both read one polynomial, so a prover cannot show them different children, and only the bridge commitment has to enter the transcript.

The nested side has a shorter list. Its [`collapse`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/circuits/collapse.rs#L1-L24) checks the nested fold and pins its unified instance to the stages, its [`compute_v`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/circuits/compute_v.rs#L1-L32) computes $v_n$, and [26 endoscaling steps](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L2372) walk the native batch. The [loading polynomial](./staging.md#_10-linking-stages-with-a-bonding-polynomial) ties the walk's points to the bridge stages. That side has no transcript and no application circuit, as [chapter 13 found](./curve-cycles.md#_12-cycles-in-ragu).

The application's circuit [uses no stages](./staging.md#_15-staging-in-ragu). All of the machinery above sits beside it and leaves its budget of gates to the application.

::: warning The stage chains
**Book:** the [recursion chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/index.md?plain=1#L87-L88) gives `hashes_2` the chain preamble, outer error.

**Code at `3219e08`:** [`hashes_2`'s claim](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L192-L197) sums only its own trace and the outer error stage, and [its documentation](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_2.rs#L28-L34) marks the preamble as skipped. The layout still reserves the preamble's gates, which is what [skipping a stage](./staging.md#_9-two-circuits-on-one-stage) means.

This site follows the code.
:::

## 4. Splitting the transcript

The transcript has to be replayed in circuit, because the [Fiat–Shamir challenges](./statements-and-challenges.md#_8-removing-the-verifier-with-fiat–shamir) would otherwise be numbers that the prover merely asserts. One circuit cannot hold the whole replay:

<!-- worked:perm-cost -->

A permutation costs [$288$ gates](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_primitives/src/poseidon/tests/mod.rs#L96), and the code documents [$3$ permutations](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_1.rs#L7-L17) in the first half and [$5$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_2.rs#L7-L23) in the second. Together that makes $8$ permutations and $2,304$ gates, which already exceeds the limit of $2,048$ gates per circuit before any other check runs. The two halves cost $864$ and $1,440$ gates, so each fits.

<!-- /worked:perm-cost -->

So the replay has to cross a circuit boundary, and the sponge's state has to cross with it. The second circuit cannot recompute the state without repeating the permutations it is trying to avoid, and passing the state as a public input would [add wires to every $k(Y)$](./staging.md#_1-two-jobs-for-a-partial-commitment). The code places it in a stage. The state is known once the inner error bridge is absorbed, and the outer error stage is the next one committed, because it holds values folded with the $\mu$ that the state produces.

![Eight bridge commitments in a row, with the challenge each one releases below it. A blue line marks the first three as hashes_1, and a teal line marks the last five as hashes_2. An arrow takes the sponge state from the inner error commitment into a box for the outer error stage, and another arrow takes it to hashes_2, which squeezes mu first.](./manim/ragu-recursion-transcript.png)

We run this on the [toy sponge from chapter 03](./statements-and-challenges.md#a-toy-poseidon). The bridge commitments are points on $E'$, whose coordinates lie in $\F_{43}$, the field the sponge works in. The first point is the one [chapter 17 built](./staging.md#_12-stages-across-the-cycle), and the others are stand-ins:

<!-- worked:transcript-run -->

| Bridge commitment | Toy point on $E'$ | Squeezed next | Replayed by |
| --- | --- | --- | --- |
| `preamble` | $(21,\,25)$ | $w = 11$ | `hashes_1` |
| `s_prime` | $(32,\,3)$ | $y = 4$, $z = 10$ | `hashes_1` |
| `inner_error` | $(34,\,3)$ | $\mu = 2$ | `hashes_1`, then saved |
| `outer_error` | $(35,\,21)$ | $\mu' = 10$ | `hashes_2` |
| `ab` | $(37,\,7)$ | $x = 4$ | `hashes_2` |
| `query` | $(40,\,18)$ | $\alpha = 12$ | `hashes_2` |
| `f` | $(42,\,7)$ | $u = 25$ | `hashes_2` |
| `eval` | $(2,\,12)$ | $\text{pre\_beta} = 33$ | `hashes_2` |

<!-- /worked:transcript-run -->

<!-- worked:transcript-split -->

The first half ends by permuting and saving the three cells of the state, $(2, 42, 12)$. The second half loads those cells and squeezes $\mu = 2$ with no further permutation, which is why its count starts from the absorption of `outer_error`. We ran the sponge once straight through and once split at this point, and all nine challenges agree. The toy sponge takes $3$ permutations in the first half and $5$ in the second, as the code does, because we leave out the domain tag and its rate of 2 fits one point per permutation.

<!-- /worked:transcript-split -->

Reading the state from a stage leaves one question, which is what forces the stage to hold the right value. Only `hashes_1` knows that value, having computed it, so the check goes [in that circuit](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_1.rs#L281-L286):

```rust
// save_state() applies a permutation (since there's pending absorbed data)
// and returns the raw state, ready for squeeze-mode resumption in hashes_2.
transcript
    .save_state(dr)
    .expect("save_state should succeed after absorbing")
    .enforce_equal(dr, &outer_error.sponge_state)?;
```

Without this line, a prover could pick the state and with it the challenges:

<!-- worked:transcript-tamper -->

Suppose a prover wants $\mu = 9$, and it writes the state $(9, 42, 12)$ into `outer_error`. The second half alone would resume from this state and produce $\mu = 9$ and $\mu' = 20$. Of the $79,507$ possible states, $1,849$ give the wanted $\mu$, but the first half compares the stage with the state it computed, and exactly $1$ state passes that comparison, the honest one. Both circuits read one committed stage polynomial, so the prover cannot show them different values.

<!-- /worked:transcript-tamper -->

## 5. Public inputs

Each circuit also has a public input polynomial $k(Y)$, and a parent has to compute $k(y)$ for each of a child's circuits. If every internal circuit exposed its own values, a parent would compute many different polynomials. The code avoids that with a **unified instance**, one [structure of values](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/unified.rs#L274-L332) that nearly all internal circuits expose in full, so that one computed $k(y)$ serves them all.

Sharing an instance raises the question of who checks each value, since a circuit that merely exposes a value proves nothing about it. The code assigns each slot to exactly one circuit, and the prover [asserts](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/unified.rs#L155-L156) that all were covered. Other circuits read a slot as a witness, and the shared $k(y)$ forces them to agree with the owner:

<!-- worked:slots -->

| Slots | Wires | Owner |
| --- | --- | --- |
| Bridge commitments for preamble, $s'$ and inner error; $w$, $y$, $z$ | $9$ | `hashes_1` |
| Bridge commitments for outer error, $ab$, query, $f$ and eval; $\mu$, $\mu'$, $x$, $\alpha$, $u$, `pre_beta` | $16$ | `hashes_2` |
| $c$ | $1$ | `collapse` |
| $v$ | $1$ | `compute_v` |
| The nested challenge stage's partial commitment | $2$ | The last `bind_challenges` |
| $P_n$, $A_n$, $B_n$ and the nested registry restriction | $8$ | `bind_endoscalar` |

The rows add to $13$ points and $11$ elements, which is the code's [$37$ wires](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/unified.rs#L43).

<!-- /worked:slots -->

Recursion uses [three forms of $k(Y)$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/preamble.rs#L112-L144) over these values, plus a fourth with no wires of its own. All are Horner evaluations ending in the [constant wire's 1](./nark.md#_14-the-constant-wire):

$$k_{\text{unified}}(Y) = \text{Horner}(\text{unified} \,\|\, 0 \,\|\, 1,\ Y),$$

$$k_{\text{bridge}}(Y) = \text{Horner}(\text{unified} \,\|\, \text{left} \,\|\, \text{right} \,\|\, 0 \,\|\, 1,\ Y),$$

$$k_{\text{app}}(Y) = \text{Horner}(\text{left} \,\|\, \text{right} \,\|\, \text{output} \,\|\, 1,\ Y).$$

Here Horner over wires $w_0, \ldots, w_{m-1}$ and the final 1 means $(\cdots(w_0 y + w_1) y + \cdots + w_{m-1}) y + 1$, so the last wire before the 1 is the coefficient of $Y$. The `hashes_1` circuit uses $k_{\text{bridge}}$, because it exposes the child headers, and the application circuit exposes the same headers through $k_{\text{app}}$. Together those two claims stop a proof from using one pair of headers in the step and another in the recursion. An endoscaling step exposes [nothing but the zero](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/endoscaling_step.rs#L19-L24), so its polynomial is $k(Y) = 1$.

<!-- worked:k-run -->

Take a toy unified output of five wires, $(21, 25, 11, 4, 10)$, which are the first bridge point and the challenges $w$, $y$ and $z$ from the run above. Take child headers $(8, 3)$ and $(12, 3)$, whose second entry is the suffix, and the output header $(20, 3)$. At $y = 4$:

| Polynomial | Wires, in order | Value at $y$ | Coefficient of $Y$ |
| --- | --- | --- | --- |
| $k_{\text{unified}}$ | Unified output, $0$ | $39$ | $0$ |
| $k_{\text{bridge}}$ | Unified output, left, right, $0$ | $26$ | $0$ |
| $k_{\text{app}}$ | Left, right, output | $6$ | $3$ |
| Endoscaling step | $0$ | $1$ | $0$ |

Horner's rule reaches $40$ after the five unified wires, and both $k_{\text{unified}}$ and $k_{\text{bridge}}$ continue from that value. Each table entry also matches a direct evaluation of the polynomial.

<!-- /worked:k-run -->

These values reach the fold through the parent. Its `hashes_1` and `collapse` circuits [compute each child's values](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_1.rs#L265-L272) from the preamble stage with gates, at the $y$ of the current fuse, and those values become the targets of the claims being folded.

::: warning The unified instance
**Book:** the [public inputs chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/public_inputs.md?plain=1#L81-L83) says that the shared structure holds 29 wires, from eight commitments and thirteen field elements. The [recursion chapter's list](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/index.md?plain=1#L44-L50) gives nine challenges and two final values, which makes eleven elements. The public inputs chapter also says that [four internal circuits](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/public_inputs.md?plain=1#L96-L97) share $k_{\text{unified}}$.

**Code at `3219e08`:** thirteen points and eleven elements, which makes the 37 wires above. The five additional points are in the last two rows of the table. The [count of circuits sharing $k_{\text{unified}}$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L33-L46) is nine, because `bind_challenges` has four instances.

This site follows the code.
:::

## 6. Keeping internal and application circuits apart

The registry holds internal and application circuits side by side, and [a proof names its application circuit](./wiring-and-registry.md#_10-what-the-prover-may-select) by a domain point the prover selects. So a prover could try to name an internal circuit and claim its trace as an application step. To rule that out, the code makes the two kinds of $k(Y)$ unable to coincide. Each internal circuit ends its output with a zero, and each application header ends with a [suffix that is never zero](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/header.rs#L13-L27).

<!-- worked:substitution -->

Let an internal circuit expose wires $(a, b)$ and its zero suffix, so that $k_{\text{int}}(Y) = aY^3 + bY^2 + 1$, and let an application circuit expose a header $(d, s)$, so that $k_{\text{app}}(Y) = dY^2 + sY + 1$. If an application could use the suffix $s = 0$, then $43$ of the $79,507$ triples $(a, b, d)$ would make the two polynomials identical, and the swap would pass at every $y$. For $s = 3, 4, 5$ the difference depends only on $a$ and $b - d$, so we tried all $1,849$ pairs of those, and none makes the polynomials identical. The two values then agree at no more than $2$ of the $42$ nonzero values of $y$, and on a real field the same count is a negligible fraction.

<!-- /worked:substitution -->

This also explains why an endoscaling step needs the zero although it exposes nothing. [Its comments](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/endoscaling_step.rs#L19-L24) say that the suffix is what stops a step from satisfying an application instance, given that the application's circuit ID may name any native slot. The nested registry [holds internal circuits only](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/unified.rs#L28-L29), so it omits the zero.

::: warning The first application suffix
**Book:** [application-defined suffixes begin at two](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/public_inputs.md?plain=1#L107-L109), with one reserved for the trivial header.

**Code at `3219e08`:** [three values are reserved](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/header.rs#L13-L27), with 0 for fixed circuits, 1 for the unit header and 2 for the `Dummy` header of the base case, so [application suffixes begin at three](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/header.rs#L68-L73).

This site follows the code. The book's argument is unaffected, since it needs only that the suffix is nonzero.
:::

The value 2 has a job of its own, which [chapter 10 described](./recursive-proofs.md#the-base-case-in-ragu). Only the internal `Bootstrap` step declares the `Dummy` input, and only then does [`collapse` waive its final comparison](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/collapse.rs#L276-L287). The `Rerandomize` step has a witnessed suffix, so it [constrains that wire away from 2](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/step/encoder.rs#L172-L177).

## 7. What a proof carries to its parent

A parent does not repeat the checks in a child's circuits. It folds the child's claims into its own accumulators and reads the child's public data. Here is what it takes from a child:

| From the child | What the parent does with it | Explained in |
| --- | --- | --- |
| Headers and unified instance | Holds them in the preamble and computes the child's $k(y)$ values | Section 5 |
| $(A, B, c)$ | Adds the pair as a [raw claim with target $c$](./revdot-folding.md#_10-the-quotient-fold-in-ragu-s-fuse), folded into the new $(A, B, c)$ | [Chapter 14](./revdot-folding.md) |
| Each trace and stage commitment | Adds a circuit claim or mask claim to the same fold | [Chapter 17](./staging.md) |
| $(P, u, v)$ | Adds [the claim $p(u) = v$](./split-accumulation.md#_11-split-accumulation-in-ragu) to its batch, folded into the new $(P, u, v)$ | [Chapter 12](./split-accumulation.md) |
| $m(W, x_i, y_i)$ | Opens it at the new $w$, and opens its own new $m(W, x, y)$ at the [child's circuit ID](./wiring-and-registry.md#_7-selecting-a-circuit), so one restriction remains | [Chapter 15](./wiring-and-registry.md) |
| Nested points and challenge partial | Walks the points and completes the challenge binding in `bind_beta` | [Chapter 16](./endoscalars.md) |

Three accumulators therefore pass up the tree, namely $(A, B, c)$, $(P, u, v)$ and $m(W, x, y)$, one of each per side of the cycle. Each fuse replaces two of each with one, so a proof has the same shape at every depth. A child's internal circuits do not run again in the parent, and they cannot be skipped either, since their claims are among those folded.

The application's circuit sits [in the registry like any other](./wiring-and-registry.md#_5-a-polynomial-for-many-circuits), and the base case runs [through a single bootstrap proof](./recursive-proofs.md#the-base-case-in-ragu). Chapter 10 records that the code has [no Merkle root of initial states](./recursive-proofs.md#_10-tracking-initial-states).

## 8. From a large proof to a short one

The accumulators stay few, but each one still holds polynomials of $2^{13}$ coefficients, and so does each stage and trace. A parent needs those polynomials to compute its fold. A verifier outside the tree does not want to receive them. The code's [`verify_uncompressed`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/verify.rs#L1-L40) does hold every polynomial and checks the claims directly, and the code keeps it as a test oracle.

Compression replaces each polynomial with its commitment and a few of its values, and it restates the decider's checks so that those are enough. Chapter 09 [ran this idea on one circuit](./nark.md#_17-a-short-proof-from-the-same-parts). The [book's compression chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/compression.md) and the [code](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/mod.rs#L1-L21) arrange it in three reductions, which run once per curve:

```mermaid
flowchart LR
    I[Instance] --> R[Revdot claims]
    R -->|fold, then split| O[Opening claims]
    O -->|batch| H["One claim (H, u, v)"]
    H -->|IPA| A[Accept or reject]
```

The sections below run all three on the toy curve. We use the two circuits from the staging chapter, with $D = 16$ and the [sixteen generators](./staging.md#_2-splitting-a-trace) listed there. We choose the challenges by hand. In the code a [transcript under its own tag](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/mod.rs#L172-L185) supplies them, after absorbing the instance and the output header, with fresh $w$, $y$, $z$ and $\sigma$ on each curve.

## 9. The instance and its claims

The instance has to tell the verifier everything it would otherwise read off the polynomials. For our two circuits that gives this:

<!-- worked:instance -->

| Instance entry | Toy value | Role |
| --- | --- | --- |
| $\bar{A}$, $\bar{Q}$ | $(22,\,24)$, $(14,\,9)$ | Two stages. $\bar{Q}$ holds the values read from the registry |
| $\bar{R}'_1$, $\bar{R}'_2$ | $(24,\,30)$, $(24,\,1)$ | Final traces of the squaring and cubing circuits |
| $\bar{A}_{\text{acc}}$, $\bar{B}_{\text{acc}}$ | $(1,\,29)$, $(25,\,29)$ | The accumulator pair |
| $c$ | $11$ | Its stored revdot value |
| $\bar{M}$ | $(17,\,24)$ | The restriction $m(W, 9, 7)$ |
| $\bar{P}$, $v$ | $(27,\,30)$, $37$ | The batch claim at the fuse's $u = 9$ |
| $A(u)$, $B(u)$ | $35$, $15$ | The accumulator pair at that $u$ |

<!-- /worked:instance -->

These numbers carry over from earlier chapters. The accumulator pair stands in for what the last fuse left, and we took the squaring claim at $x = 5$ for it. The polynomial $p$ behind $\bar{P}$ is [chapter 06's example](./polynomial-commitments.md), with its opening point $9$. The real [instance](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L66-L102) holds a commitment for each native and nested polynomial, which makes it the largest part of the proof.

The verifier now rebuilds the decider's revdot claims from what it holds, in the order of the code's [claim list](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L160-L300):

<!-- worked:claims -->

| Slot | Claim | Kind | Left vector | Right vector | Target $k_i$ |
| --- | --- | --- | --- | --- | --- |
| 0 | Accumulator | Raw | $A_{\text{acc}}$ | $B_{\text{acc}}$ | $11$ |
| 1 | Squaring circuit | Circuit | $a + r'_1$ | $r_1(zX) + s_1(X, y) + t(X, z)$ | $7$ |
| 2 | Cubing circuit | Circuit | $a + r'_2$ | $r_2(zX) + s_2(X, y) + t(X, z)$ | $22$ |
| 3 | Stage mask | Bonding | $z\,a + q$ | Mask of gate 1 | $0$ |
| 4 | Final mask | Bonding | $z\,r'_1 + r'_2$ | Mask of gates 2, 3 | $0$ |
| 5 | Wire binding | Masked | $q - E_\sigma$ | $M_\sigma$ | $0$ |

<!-- /worked:claims -->

The first five claims have appeared in earlier chapters. The sixth exists because the decider also compares individual wires of certain stages against values it computes for itself, and a verifier that holds only a stage's commitment needs another way to make that comparison. The code [turns it into a revdot claim](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/revdot/claims.rs#L35-L52). For wires at degrees $d_j$ with expected values $e_j$, it sets

$$E_\sigma = \sum_j e_j X^{d_j}, \qquad M_\sigma = \sum_j \sigma^j X^{D - 1 - d_j},$$

and the revdot product picks out the differences at those wires:

$$\revdot{\v{q} - \v{E}_\sigma}{\v{M}_\sigma} = \sum_j \sigma^j (q_{d_j} - e_j).$$

The target is 0, and it holds at a random $\sigma$ only if each wire holds its expected value. The real list has [five such claims natively and three on the nested side](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L515-L710). In our run a small stage $q(X)$ plays the role of the query stage:

<!-- worked:binding -->

The registry here has two circuits at $W = 1$ and $W = -1$, whose wiring gives $m(1, 9, 7) = 11$ and $m(-1, 9, 7) = 12$. The stage $q(X)$ claims those values in the wires $a_1$ and $d_1$. With $\sigma = 20$, the mask $M_\sigma$ has a $1$ opposite $a_1$ and a $20$ opposite $d_1$, and $E_\sigma$ holds the expected values at those two degrees. So the product is $(a_1 - 11) + 20(d_1 - 12) = 0$. If the stage holds a wrong $a_1$, the product is nonzero at all 43 values of $\sigma$. If both wires are wrong, the two errors cancel at one value of $\sigma$ out of 43.

<!-- /worked:binding -->

<!-- worked:real-claims -->

A real compressed proof has $56$ native claims, namely one accumulator pair, one application circuit, $33$ internal circuits, $16$ masks and $5$ wire bindings, and it has $46$ nested claims. In groups of $7$, the native side has $8$ groups, $336$ first-layer terms and $56$ second-layer terms, and the nested side has $7$ groups, $264$ first-layer terms and $42$ second-layer terms.

<!-- /worked:real-claims -->

## 10. Folding to three claims

Now the fold, in the form the [code's compression](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/revdot/fold.rs#L1-L34) uses. [Chapter 14](./revdot-folding.md#_11-compression-and-the-forms-of-the-fold) noted that this differs from the fuse's quotient fold, and that the sources do not say why. Claim $i$ in group $g$ and slot $s$ takes the weights

$$\lambda_i = (\mu')^g \mu^s, \qquad \eta_i = (\nu')^g \nu^s,$$

and the folded pair is $A = \sum_i \lambda_i a_i$ and $B = \sum_i \eta_i b_i$. To see the target, expand the revdot product and separate the terms with $i = j$:

$$\revdot{\v{A}}{\v{B}} = \sum_i \lambda_i \eta_i \revdot{\v{a}_i}{\v{b}_i} + \varepsilon_1 + \varepsilon_2.$$

The first sum holds the true targets $k_i$. The other two terms collect the products $e_{i,j} = \revdot{\v{a}_i}{\v{b}_j}$ that the verifier cannot compute, with $\varepsilon_1$ for pairs inside a group and $\varepsilon_2$ for pairs across groups. The verifier does not need those products individually. The prover lays them out as low coefficients of a vector $\v{E}_\ell$ for each layer, and the weights go in mirrored positions of a public vector $\v{W}_\ell$, so that each $\varepsilon_\ell$ is itself a revdot product, as chapter 14 showed. Our six claims fall into two groups of three, where the code uses seven per group:

<!-- worked:fold-run -->

With $\mu = 19$, $\nu = 38$, $\mu' = 2$ and $\nu' = 33$:

| Value | Toy result |
| --- | --- |
| First-layer terms, group by group | $(40, 9, 2, 36, 11, 34, 36, 28, 29, 0, 0, 0)$ |
| $\bar{E}_1$, committed before $\mu$ and $\nu$ | $(20,\,25)$ |
| Second-layer terms | $(22, 30)$ |
| $\bar{E}_2$, committed before $\mu'$ and $\nu'$ | $(27,\,1)$ |
| $\varepsilon_1 = \revdot{\v{E}_1}{\v{W}_1}$ | $6$ |
| $\varepsilon_2 = \revdot{\v{E}_2}{\v{W}_2}$ | $12$ |
| $\sum_i \lambda_i \eta_i k_i$ | $10$ |
| $K$, the target of $(A, B)$ | $28$ |
| $\revdot{\v{A}}{\v{B}}$, for comparison | $28$ |

<!-- /worked:fold-run -->

The vectors $\v{A}$ and $\v{B}$ have public parts that nobody needs to commit to, so the verifier separates what it derives from commitments and what it evaluates alone. A circuit claim's $b_i$ contains $a_i(zX)$, so the committed polynomial $T = \sum_{\text{circuits}} \eta_i a_i$ takes care of that part at the dilated point $rz$:

$$A(X) = A_c(X) + A_{\text{pub}}(X), \qquad B(X) = B_c(X) + T(zX) + B_{\text{pub}}(X).$$

Here $B_{\text{pub}}$ holds the wiring restrictions, the $t(X, z)$ terms, the masks and $M_\sigma$, and $A_{\text{pub}}$ holds the expected values of the wire bindings. The commitments come from the instance:

<!-- worked:derived -->

The verifier obtains $\bar{A}_c = (11,\,30)$, $\bar{T} = (20,\,25)$ and $\bar{B}_c = (25,\,29)$ from small MSMs over the instance's points. Committing to the three polynomials directly gives the same points.

<!-- /worked:derived -->

## 11. The split

We have three revdot claims, $(A, B, K)$, $(E_1, W_1, \varepsilon_1)$ and $(E_2, W_2, \varepsilon_2)$, and nothing has yet shown that any of them is true. The [split from chapter 05](./polynomial-encoding.md#_12-splitting-the-product) handles this. The prover combines the products with a challenge $\rho$,

$$t(X) = A(X)B(X) + \rho\,E_1(X)W_1(X) + \rho^2 E_2(X)W_2(X),$$

and writes the result as $t(X) = X^{D-1} p(1/X) + X^D q(X)$. A revdot product is the coefficient of $X^{D-1}$ in the ordinary product, so that coefficient of $t$ is the combination of all three revdot products, and it lands in $p(0)$. This is the one place that [pays for the product polynomial and its FFTs](./revdot-folding.md#_11-compression-and-the-forms-of-the-fold). The verifier then picks a point $r$ and checks the identity at it, and it sets aside its required value of $p(0)$ to be opened later:

<!-- worked:split-run -->

At $\rho = 41$ the prover commits to $\bar{p} = (23,\,7)$ and $\bar{q} = (30,\,8)$, and the required value is $p(0) = K + \rho\,\varepsilon_1 + \rho^2\varepsilon_2 = 21$. At $r = 18$, so that $rz = 26$ and $1/r = 12$, it sends seven values:

| $A_c(r)$ | $T(rz)$ | $B_c(r)$ | $E_1(r)$ | $E_2(r)$ | $p(1/r)$ | $q(r)$ |
| --- | --- | --- | --- | --- | --- | --- |
| $38$ | $7$ | $12$ | $25$ | $3$ | $10$ | $8$ |

The verifier adds what it can compute alone. It needs $s_1(r, y) = 39$, $s_2(r, y) = 9$ and $t(r, z) = 3$, the masks at $r$, which are $28$, $29$ and $5$, and the two public vectors, $W_1(r) = 14$ and $W_2(r) = 7$. That gives $A(r) = 38 + 20 = 15$ and $B(r) = 12 + 7 + 10 = 29$, modulo 43. The left side of the split is $A(r)B(r) + \rho\,E_1(r)W_1(r) + \rho^2 E_2(r)W_2(r) = 34$, and the right side is $r^{15}p(1/r) + r^{16}q(r) = 34$.

<!-- /worked:split-run -->

The two sides agree, but all seven values are still only claims about commitments, which the next step settles.

## 12. Batching and the argument

The reduction leaves eight claims, seven from the values above and one for the required $p(0)$. The instance adds [four of its own](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L717-L741), which carry the fuse's accumulators into the check:

<!-- worked:claims-list -->

| Claim $j$ | Polynomial | Commitment | Point $x_j$ | Value $y_j$ |
| --- | --- | --- | --- | --- |
| 0 | $A_c$ | $(11,\,30)$ | $18$ | $38$ |
| 1 | $T$ | $(20,\,25)$ | $26$ | $7$ |
| 2 | $B_c$ | $(25,\,29)$ | $18$ | $12$ |
| 3 | $E_1$ | $(20,\,25)$ | $18$ | $25$ |
| 4 | $E_2$ | $(27,\,1)$ | $18$ | $3$ |
| 5 | $p$ | $(23,\,7)$ | $12$ | $10$ |
| 6 | $q$ | $(30,\,8)$ | $18$ | $8$ |
| 7 | $p$ | $(23,\,7)$ | $0$ | $21$ |
| 8 | $m(W, 9, 7)$ | $(17,\,24)$ | $7$ | $8$ |
| 9 | $P$ | $(27,\,30)$ | $9$ | $37$ |
| 10 | $A_{\text{acc}}$ | $(1,\,29)$ | $9$ | $35$ |
| 11 | $B_{\text{acc}}$ | $(25,\,29)$ | $9$ | $15$ |

<!-- /worked:claims-list -->

With only 43 points on the toy curve, some commitments repeat by chance, such as those of $T$ and $E_1$. The polynomials themselves differ.

The last four rows are what the decider still owes from the recursion. Claim 9 is the fuse's accumulated [$(P, u, v)$](./split-accumulation.md#_6-a-run-on-the-toy-curve), and claims 10 and 11 pin the values of the accumulator pair at that $u$. Claim 8 is the [restriction check of chapter 15](./wiring-and-registry.md#_13-wiring-and-the-registry-in-ragu):

<!-- worked:registry-value -->

Claim 8 opens $m(W, 9, 7)$ at the fresh point $w = 7$. The verifier computes the value $8$ for itself, by evaluating the wiring of both circuits and combining the results with Lagrange weights, and this is the step that reads the whole registry.

<!-- /worked:registry-value -->

[Chapter 08's batch](./batched-openings.md#_7-beta-batching) turns all twelve into one. The prover commits to the quotient $f(X) = \sum_j \alpha^{m-1-j}\, (h_{i_j}(X) - y_j) / (X - x_j)$ and sends each polynomial's value $z_i$ at a new point $u$. Then the verifier derives, with $n = 11$ polynomials and $m = 12$ claims,

$$\bar{H} = \beta^{n} \cdot \bar{F} + \sum_{i=0}^{n-1} \beta^{n-1-i} \cdot \bar{h}_i,$$

$$v = \beta^{n} \sum_{j=0}^{m-1} \alpha^{m-1-j}\, \frac{z_{i_j} - y_j}{u - x_j} + \sum_{i=0}^{n-1} \beta^{n-1-i} z_i.$$

Unlike the fuse's $\beta$, which has to be short so that a circuit can scale points with it, this $\beta$ is [an ordinary squeezed element](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/batch/verifier.rs#L65), since no circuit runs this verifier.

<!-- worked:batch-run -->

With $\alpha = 17$ the quotient commits to $\bar{F} = (5,\,29)$. At $u = 38$ the prover sends the eleven values $(18, 5, 35, 18, 1, 12, 36, 14, 5, 22, 35)$. The verifier derives $f(u) = 30$ from those values and the claims. With $\beta = 20$ this gives $\bar{H} = (28,\,10)$ and $v = 14$, and the prover's polynomial $H$ agrees on both.

<!-- /worked:batch-run -->

Now [the inner product argument of chapter 07](./inner-product-argument.md), in the code's form, proves $H(u) = v$:

<!-- worked:ipa-run -->

The argument commits to the masking polynomial, $\bar{S} = (26,\,23)$, and takes $\xi = 29$ and a multiplier $z = 12$ on $U$. The statement becomes $\bar{H} - v \cdot G_0 + \xi \cdot \bar{S} = (1,\,29)$. Then come $\log_2 16 = 4$ rounds:

| Round | Challenge | $L_j$ | $R_j$ |
| --- | --- | --- | --- |
| 1 | 12 | $(25,\,29)$ | $(23,\,7)$ |
| 2 | 17 | $(30,\,8)$ | $(22,\,7)$ |
| 3 | 33 | $(22,\,7)$ | $(25,\,29)$ |
| 4 | 41 | $(16,\,21)$ | $(23,\,24)$ |

The final scalar is $\hat{a} = 38$. The verifier computes $\hat{G} = (18,\,10)$ from an MSM over all sixteen generators and $\hat{b} = 14$ from a product of four factors. The folded statement is $(22,\,7)$, and $\hat{a} \cdot (\hat{G} + \hat{b} z \cdot U) = (22,\,7)$, so the verifier accepts.

<!-- /worked:ipa-run -->

That finishes the run on this curve. In the code the same three reductions run again on the nested curve with its own claims, [on one continuous transcript](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/mod.rs#L25-L26).

## 13. What the verifier pays

[Chapter 09 named two linear costs](./nark.md#_17-a-short-proof-from-the-same-parts), computing $s(x, y)$ and computing $\hat{G}$, and part three set out to remove them from the circuits. They have not disappeared. No circuit pays them, which is what recursion needed, and [the wiring chapter](./wiring-and-registry.md#_13-wiring-and-the-registry-in-ragu) deferred the last piece to this page. The verifier of a compressed proof pays them once, at the root:

<!-- worked:verifier-cost -->

| Verifier step, per curve | Work | Growth |
| --- | --- | --- |
| Replay the fuse transcript | $8$ permutations, on the native field only | Constant |
| Recompute two nested stages | Two small commitments, on the nested curve only | Constant |
| Compute targets $k(y)$ | One Horner step per public wire | Size of the instance |
| Derive $\bar{A}_c$, $\bar{T}$, $\bar{B}_c$, $\bar{H}$ | MSMs over the instance's points | Size of the instance |
| Compute $s_i(r, y)$ for each circuit claim | $34$ native and $28$ nested circuits, one term per wiring coefficient | **Linear in the circuits** |
| Compute registry values for the wire bindings | One pass over the domain at $(x, y)$, and natively $11$ further evaluations of $m$ | **Linear in the registry** |
| Compute $m(w, x, y)$ | One pass over the registry, with Lagrange weights | **Linear in the registry** |
| Compute masks and $t(r, z)$ | Closed forms | Logarithmic |
| Compute $\hat{b}$ and combine the $L_j$, $R_j$ | $26$ scalar multiplications and $13$ factors | Logarithmic |
| Compute $\hat{G}$ | 1 MSM of $8,192$ scalar multiplications | **Linear in the vector length** |

<!-- /worked:verifier-cost -->

The rows in bold are what remains of chapter 09's two costs. Wiring appears three times, because the compressed verifier evaluates [each circuit claim's restriction at $(r, y)$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/revdot/verifier.rs#L231), the [whole registry over its domain and at further points](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L555-L601) to fill the wire bindings, and the [registry at the fresh $(w, x, y)$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L734). This last evaluation is the one chapter 15 described. It lets a whole tree of fuses rely on one restriction polynomial, since the verifier [checks that polynomial against the full registry](./wiring-and-registry.md#_6-consistency-for-the-registry) exactly once. Each of these passes grows with the wiring of the registered circuits, including the application's steps.

The last row is the [deferred MSM of chapter 11](./accumulation.md). Compression [computes it in full](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/batch/verifier.rs#L28-L35), with one per curve. None of these costs grows with the depth of the tree, so a proof that covers many leaves has the same verifier as a proof that covers two.

## 14. The size of the result

Counting from the [code's wire format](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/compressed.rs#L69-L150) gives the following, for the standard profile at the production rank of 13 and headers of 4 elements, which is the [size the code's benchmarks use](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/benches/criterion/compress.rs#L35):

<!-- worked:sizes -->

| Part | Points | Scalars |
| --- | --- | --- |
| Instance, commitments and values | $93$ | $19$ |
| Instance, two child headers of $4$ elements | $0$ | $8$ |
| Revdot reduction, per curve | $4$ | $9$ |
| Batch, per curve | $1$ | $11$ |
| IPA, per curve | $27$ | $1$ |
| Total, with two curves | $157$ | $69$ |

<!-- /worked:sizes -->

<!-- worked:size-total -->

At 32 bytes per point or scalar, with [4 bytes for the circuit index](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/registry.rs#L7-L20) and the [28-byte envelope](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/format.rs#L40), that comes to $7,264$ bytes. The [uncompressed encoding](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/polynomial.rs#L1-L10) writes $8,192$ coefficients for each of $92$ polynomials, which is $24,117,248$ bytes before counting its cached points, so compression shrinks the proof by a factor of about $3,320$. Most of the compressed proof is the instance, with $93$ of its $157$ points. The IPA rounds, the only part that grows with the circuit size, take $52$ points.

<!-- /worked:size-total -->

The code's [comment on profiles](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L10-L11) says "a few kilobytes", which agrees with this count.

<!-- worked:header-extra -->

A header larger than $4$ elements adds $64$ bytes per extra element, since the proof holds the two child headers. The output header does not count, because [the verifier supplies it](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/verifier.rs#L83) as the statement.

<!-- /worked:header-extra -->

## 15. Why cheating fails

The chapters before this one each counted cheating at their own step. Here we look at what compression adds, which is the chance to hide a false claim in a value the verifier will never check directly. Start with a false public input:

<!-- worked:cheat-target -->

Suppose the prover claims the output $11$ for the squaring circuit in place of $10$, so its target rises by $y = 35$ while its vectors stay honest. At our challenges the folded pair then misses $K$ by $14$. Before the challenges, it can lower the term $e_{0,1}$, whose weight is $\nu$, by some amount $e$. The false target adds $35\mu\nu$ to $K$ and the lowered term removes $e\nu$, so the fold balances only if $\mu = e / 35$. For $e = 5$ that means $\mu = 37$, and we confirmed the balance there on the full vectors. Over all $1,764$ nonzero pairs $(\mu, \nu)$, every nonzero $e$ balances exactly $42$ pairs, which is one value of $\mu$ out of 42.

<!-- /worked:cheat-target -->

The value $\varepsilon_1$ is a second place to try:

<!-- worked:cheat-epsilon -->

After seeing $\mu$ and $\nu$, the prover could raise $\varepsilon_1$ alone and leave $\v{E}_1$ as committed. That can make $(A, B)$ balance, but it makes the claim $(E_1, W_1, \varepsilon_1)$ false by the same amount, and $\rho$ arrives only after $\varepsilon_1$ is fixed. We tried all $42$ nonzero shifts against all $43$ values of $\rho$, and each shift passes at exactly $1$ value of $\rho$.

<!-- /worked:cheat-epsilon -->

The prover could also try to change the required value of $p(0)$ directly:

<!-- worked:cheat-split -->

Suppose the prover wants $p(0)$ to be too large by $7$. The coefficient of $X^{15}$ in $X^{15}p(1/X) + X^{16}q(X)$ is exactly $p(0)$, so whatever else it does, the difference from the true product is a nonzero polynomial of degree at most $30$. The prover can choose the other coefficients of $p$ and $q$ to give that difference as many roots as possible, and we built such a pair. It passes the split at $30$ of the $42$ nonzero values of $r$. This is the toy field's small size at work, since the same count on the real parameters is $2^{14} - 2$ roots out of about $2^{254}$ values.

<!-- /worked:cheat-split -->

Once the split passes, every remaining claim is a statement about a commitment, and [chapter 08](./batched-openings.md) and [chapter 07](./inner-product-argument.md) already counted those. A prover cannot avoid the registry either, since the verifier computes both $m(w, x, y)$ and each $s_i(r, y)$ for itself. It cannot slip in a stray commitment, because every polynomial commitment the verifier reads [gets opened through the IPA](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/mod.rs#L26-L30). The code's one exception is the nested challenge stage's partial commitment, which commits to no polynomial, and [the `bind_challenges` claims hold it in place](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/mod.rs#L30-L34).

The argument above is informal, and it rests on these assumptions. Nobody knows a relation among the generators on either curve, so commitments bind. The two transcripts behave as random oracles, and each challenge comes after the commitments and values it tests. A false proof about a tree also has to get past the accumulation arguments of the earlier chapters. The book reports [Lean proofs for some gadget contracts](./endoscalars.md#_14-endoscalars-in-ragu) and says that these do not cover the protocol's overall soundness, which we do not establish here either.

## 16. Rerandomization and zero knowledge

A wallet would like two things from a proof beyond soundness. The proof should hide its witness, and when it reaches someone else it should not link back to the proof that produced it. As [chapter 02 recorded](./pcd-intro.md#_10-uncompressed-and-compressed-proofs), neither the Ragu Book nor the code at this commit establishes either property.

The code has an operation aimed at the second, [`rerandomize`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/lib.rs#L708-L743). It fuses the input proof as the left child with a cached proof of the unit header as the right child, under an [internal step](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/step/internal/rerandomize.rs#L1-L18) whose output header uses the same wires as the left input, so it cannot change the header. The result verifies as the input did. Both the [book](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/implementation/proofs.md?plain=1#L196-L208) and the code say that unlinkability is the intention, and the [comment on that function](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/lib.rs#L717-L724) says that it is not achieved today. One of its reasons is that the fold is deterministic:

<!-- worked:rerandomize -->

Reduce the fold to one commitment and let the output be $\bar{A}_{\text{out}} = \lambda_0 \bar{A}_{\text{in}} + \lambda_1 \bar{A}_{\text{seed}}$, with the public weights $\lambda_0 = 16$ and $\lambda_1 = 22$ and the cached seeded point $(1,\,29)$. An input of $(25,\,29)$ gives the output $(24,\,30)$. An observer who wonders which proof went in can test each candidate against that equation. We tried all $42$ points as candidates, and only the true input matches.

<!-- /worked:rerandomize -->

The comment's other reason is more direct, because the output holds the input's commitments and stage polynomials in the clear as left-child data. It lists the remaining work as a randomizer in the fold and a way of hiding the child data.

Hiding the witness has a similar status. The stages' [random $\alpha$](./staging.md#_3-gates-that-hold-free-values) is there to prevent cancellation and not for hiding, the [IPA is unblinded](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/ipa/mod.rs#L1-L16) at this commit, and the code says that [a compressed proof is not hiding](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/mod.rs#L45-L46), because its openings are evaluations of the witness polynomials. To see what one evaluation can tell an observer:

<!-- worked:leak -->

Take the stage $a(X)$ from [chapter 17](./staging.md), where $v = x^2$ and one random entry $\alpha$ sits at $a_0$. Among all $1,849$ pairs $(x, \alpha)$, the commitment $(22,\,24)$ matches $43$. Adding one value at a point, $a(17) = 3$, leaves $2$ pairs, the true $(3, 10)$ and also $(24, 42)$, because the commitment and the value together give a quadratic equation in $x$. On a real curve nobody can list the commitment's matches, but the value still gives one linear equation in the secret wires, which is the sense in which the proof does not hide them.

<!-- /worked:leak -->

This small case shows the effect of one value on one stage. A compressed proof opens combinations of polynomials at points the transcript chooses, so the leak there has a different shape, and we have not analyzed how much it reveals in practice. An uncompressed proof holds the polynomials themselves. The [Tachyon book's description of stamps](https://github.com/tachyon-zcash/tachyon/blob/7e502548db33845dbaacdc0efe905d1a3c45e626/book/src/bundle.md?plain=1#L35-L39) assumes zero knowledge, so this is an open requirement for Tachyon and not a settled property, as chapter 02 noted.

## 17. Performance against Orchard

The sizes above give a first comparison, which we can make from public formulas:

<!-- worked:orchard-size -->

[ZIP 225](https://zips.z.cash/zip-0225) gives an Orchard proof $2720 + 2272 \cdot n$ bytes for $n$ actions, which is $7,264$ bytes at $n = 2$ and $25,440$ bytes at $n = 10$. So by our count a compressed Ragu proof with headers of $4$ elements is about the size of an Orchard proof for two actions, and one Ragu proof can stand for many transactions. The exact match at $n = 2$ is a coincidence of these parameters.

<!-- /worked:orchard-size -->

For verification time, the [book's analysis chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md) gives a rough model, and it states that the figures need checking against benchmarks. It puts Orchard's [batch verification](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md?plain=1#L21-L25) at about 10 to 15 ms per proof on one thread, scaling as roughly $N_{\text{tx}} / \log N_{\text{tx}}$. It [estimates](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md?plain=1#L47-L49) a Ragu proof at about 100 ms at $K = 11$, driven mainly by an MSM of $2^{13}$ points. Setting the two equal gives the crossover, with $c$ the cost per proof:

$$\frac{N_{\text{tx}} \times c}{\log N_{\text{tx}}} \approx 100\text{ ms}.$$

The book reports [about 50 transactions](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md?plain=1#L66) with $c = 10$ ms, and it does not state the base of the logarithm. We solved the equation at both ends of its range and for the two natural bases:

<!-- worked:break-even -->

| Cost per proof in the model | $\log = \ln$ | $\log = \log_2$ |
| --- | --- | --- |
| $10$ ms | $N_{\text{tx}} \approx 36$ | $N_{\text{tx}} \approx 59$ |
| $15$ ms | $N_{\text{tx}} \approx 20$ | $N_{\text{tx}} \approx 34$ |

<!-- /worked:break-even -->

The book's figure sits inside the range the model allows, and the range is wide, as one would expect of a rough estimate. The shape of the curves is the more reliable conclusion. Batch verification of independent proofs keeps growing with the number of transactions, and verifying one aggregated proof does not.

The parameter $K$ gives a [trade-off](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md?plain=1#L78-L87) that the book leaves open. A larger circuit limit raises the verifier's cost for every proof and allows a shallower tree, and a smaller limit does the reverse.

::: warning The analysis chapter and the code
**Book:** the [analysis chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md?plain=1#L36-L44) attributes the factor of 4 in $4N$ to "the circuit structure across multiple stages", and it describes one MSM of $2^{13}$ points as the main cost.

**Code at `3219e08`:** the [number of coefficients is $4n$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/polynomials/mod.rs#L29-L37), and [chapter 04](./arithmetization.md#_8-arranging-the-witness) derives that factor from the four wires of each gate, independent of stages. A compressed verifier runs [the checks on each curve](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/verifier.rs#L98-L174), with one MSM per curve and the registry evaluations of Section 13. We read this as more work than the book's single MSM counts, which would raise the crossover, but we did not measure it.

The site follows the code for the structure and quotes the book for the estimates. The code has [benchmarks](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/benches/criterion/compress.rs#L1-L8) for compression and compressed verification, and we did not run them, so we report no timings of our own. The [book lists further analysis](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md?plain=1#L89-L97) as future work.
:::

These figures describe verification only. They leave out the prover's costs, which the sources do not quantify, and they compare with Orchard as it runs today, whereas Tachyon [changes what a transaction carries](./scaling-zcash.md). Tachyon has not activated on mainnet, its design is still changing, and it [pins a different Ragu revision](https://github.com/tachyon-zcash/tachyon/blob/7e502548db33845dbaacdc0efe905d1a3c45e626/crates/tachyon/Cargo.toml#L83) from the one this chapter reads.

## 18. Fusing after compression

One part of this design is still moving, and later chapters depend on it. [Chapter 02 recorded](./pcd-intro.md#_10-uncompressed-and-compressed-proofs) that the Ragu Book calls a compressed proof terminal, while the code's [profile comments](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L10-L15) foresee an `Aggregator` profile that verifies a compressed proof in circuit, with an internal [`Decompress` step](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/step/internal/decompress.rs#L1-L5) that outputs its header. The code [says this has not landed](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L720-L736), and [a test pins](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L2382-L2384) the aggregator's shape to the standard one until it does. Such a circuit would have to run the verifier of Section 13 with gates, which is why the design places it in extra circuits that only aggregators carry. The [chapter on aggregation](./aggregation-and-bundles.md) returns to this.

## 19. Where this chapter leaves us

This chapter took the following steps:

1. A fuse runs one transcript through eleven phases, each commitment coming before the challenge that tests it, and it divides the checks among many small circuits because each has at most $2^{11}$ gates.
2. The replay takes more gates than one circuit holds, so `hashes_1` and `hashes_2` share it, with the sponge state held in the outer error stage and checked by the first circuit.
3. The internal circuits expose one unified instance, with each slot owned by one circuit, so one $k(y)$ serves them.
4. Internal outputs end in zero and application headers end in a nonzero suffix, so the coefficient of $Y$ keeps the two kinds of circuit apart.
5. A parent folds three accumulators per side from each child, namely $(A, B, c)$, $(P, u, v)$ and $m(W, x, y)$, so a proof keeps its shape at every depth.
6. Compression replaces polynomials with commitments and values, through three reductions on each curve, from revdot claims to openings, from openings to one claim, and from that claim to an IPA.
7. A wire binding turns the decider's comparisons of stage wires into revdot claims that a verifier can check from commitments.
8. The compressed verifier pays the deferred linear costs once, as registry evaluations and one MSM per curve, and those costs do not depend on the tree.

<!-- worked:recap-size -->

9. By our count a compressed proof takes $7,264$ bytes, against more than $24,117,248$ uncompressed. Rerandomization and hiding are not yet established, and the comparison with Orchard remains an estimate.

<!-- /worked:recap-size -->

That completes Ragu as a proof system. The next part turns to what Tachyon proves with it, starting with [notes, nullifiers, and tachygrams](./notes-and-nullifiers.md).
