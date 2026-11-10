# Compression in Ragu

The [last chapter](./ragu-recursion.md) ended with a proof that keeps the same shape at every depth of the tree. It carries three accumulators per side of the cycle, along with every trace and stage of its last fuse, and each of those is a polynomial of $2^{13}$ coefficients. A parent needs the polynomials to compute its fold. A wallet or a node that only wants to check the proof does not, and it would rather not receive them.

This chapter makes the proof short. We start from the checks that the final verifier still owes, then build the compressed proof's instance and restate those checks over commitments, and we run every step on the toy curve. After the run we count what the verifier pays and how large the result is, look at what compression does not yet provide, and compare the result with Orchard.

::: warning Reconstructed from code at commit 3219e08, not confirmed by the authors
The description of compression follows the code and the book's compression chapter. The numeric run uses the small circuits of the staging chapter and a shortened instance, so it shows the structure of the code and not its real contents. The sizes come from our reading of the code's wire format. We did not build or run the code, and we did not run its benchmarks.
:::

::: tip Notation
Compression works on the proof that the last fuse produced, so it meets two sets of challenges, and several of them share a name. A subscript $f$ marks a value that the last fuse left, namely its challenges $x_f$, $y_f$, $z_f$ and $u_f$ and its batch claim $(P_f, u_f, v_f)$. Compression draws every challenge without that subscript fresh, and we introduce each one where it is drawn. So a fresh $y$ or $z$ is never the fuse challenge of the same name.
:::

## 1. From a large proof to a short one

The proof at the root still owes the deferred work. The [decider of chapter 11](./accumulation.md#_3-deciding-a-claim) is the party that finally does it, outside any circuit. In Ragu the code's [`verify_uncompressed`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/verify.rs#L1-L40) plays that part. It holds every polynomial of the proof and checks the following directly.

- Each revdot claim, including the accumulated pair $(A, B, c)$, by computing the revdot product.
- The accumulated batch claim, by evaluating $P_f$ at $u_f$ and comparing with $v_f$.
- The accumulated restriction $m(W, x_f, y_f)$, against the registry itself.
- The challenges, by replaying the fuse transcript over the bridge commitments.
- The values that the query and eval stages claim, against the registry and the polynomials.
- Every cached commitment, against the polynomial it commits to.

The code keeps this decider as a test oracle, because it needs the full polynomials. Compression replaces each polynomial with its commitment and a few of its values, and it restates the decider's checks so that those are enough. Chapter 9 [ran this idea on one circuit](./nark.md#_17-a-short-proof-from-the-same-parts). The [book's compression chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/compression.md) and the [code](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/mod.rs#L1-L21) arrange it in three reductions, which run once per curve:

```mermaid
flowchart LR
    I[Instance] --> R[Revdot claims]
    R -->|fold, then split| O[Opening claims]
    O -->|batch| H["One claim (H, u, v)"]
    H -->|IPA| A[Accept or reject]
```

The sections below run all three on the toy curve. We use the two circuits from the staging chapter, with $D = 16$ and the [sixteen generators](./staging.md#_2-splitting-a-trace) listed there. We choose the challenges by hand and introduce each one where it is drawn. In the code a [transcript under its own tag](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/mod.rs#L172-L185) supplies them, after absorbing the instance and the output header, with fresh $w$, $y$, $z$ and $\sigma$ on each curve.

## 2. Where the last fuse's challenges come from

Compression checks claims that the last fuse made at its own challenges. The accumulator pair was built at $y_f$ and $z_f$, the restriction is $m(W, x_f, y_f)$, and the batch claim sits at $u_f$. If the prover could name these values, it could choose them after building the polynomials, and every check below would test the polynomials at points the prover picked. That is the attack Fiat–Shamir exists to prevent, as [chapter 3](./statements-and-challenges.md#_8-removing-the-verifier-with-fiat–shamir) explained.

Inside the tree, a parent's circuits replayed the child's transcript. The root has no parent, so the verifier replays it itself. It does not need the polynomials for this, because the fuse transcript absorbs only the eight bridge commitments of the [last chapter's schedule](./ragu-recursion.md#the-schedule), and the instance carries all eight. So the verifier [absorbs them in the fuse's order and squeezes the fuse's challenges](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L312-L363), exactly as the [toy transcript run](./ragu-recursion.md#_4-splitting-the-transcript) did. That run lists all of them, and four of them matter here. Three, $x_f$, $y_f$ and $u_f$, enter the claims that compression checks. The fourth, $z_f$, matters only because the fuse built the accumulator pair at it, and in our reading of the code no check of compression evaluates anything at $z_f$. The prover cannot change $x_f$ without changing the bridge commitment that released it. The IPA at the end of compression opens every polynomial commitment that the verifier reads, on its own curve, with [one exception that Section 9 describes](#_9-why-cheating-fails).

The replay fixes the challenges, but two of the stages that the fuse committed to depend on nothing except those challenges and other public data. The verifier therefore [recomputes both](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L471-L512) and compares their commitments with the instance's.

- **The challenge stage** holds the lifts of the challenges and the child headers. Inside the tree, a parent finishes checking this stage for its child. The root has no parent, so the verifier does that job by rebuilding the stage from the challenges it just squeezed.
- **The `ab` bridge stage** holds the coordinates of the accumulator pair's commitments $\bar{A}_{\text{acc}}$ and $\bar{B}_{\text{acc}}$, among other values. The verifier rebuilds it so that the pair it checks is the pair the transcript absorbed before $x_f$.

::: details The same steps in the code
The `ab` bridge stage also holds the coordinates of one points stage, with a blinding value that the instance carries. The sources do not state why the verifier rebuilds this stage, and the following is our reading. The transcript absorbs the stage's commitment before it releases $x_f$. If the verifier did not rebuild the stage, a prover could fill it with the coordinates of some other pair, draw $x_f$ from that transcript, and only then pick the pair it puts in the instance. Rebuilding the stage from the instance's $\bar{A}_{\text{acc}}$ and $\bar{B}_{\text{acc}}$ rules this out.

Inside the tree, the circuits `hashes_1` and `hashes_2` replay a child's transcript. The verifier also rejects the proof if `pre_beta` lies outside the endoscalar range, as a parent's circuits would. A parent's `bind_beta` completes the binding of its child's challenge stage, because the child's own `bind_challenges` circuits ran before `pre_beta` existed, and the [code notes](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/verify.rs#L36-L38) that the root's verifier takes over that job. The code [describes the `ab` bridge stage](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/verify.rs#L362-L364) as a function of other proof data and rederives it.
:::

Our toy run skips the replay. It would need a sponge, eight bridge commitments and the nested circuit behind each one, and the run gains nothing from them, because the replay is the same computation that the last chapter already ran. So we fix the four fuse values by hand, as the table shows, together with the first fresh challenges of compression.

<!-- worked:challenges -->

| Values | Source | Used for |
| --- | --- | --- |
| $x_f = 9$, $y_f = 7$ | Left by the last fuse | The restriction $m(W, x_f, y_f)$ |
| $z_f = 5$ | Left by the last fuse | How the fuse built the accumulator pair. Compression evaluates nothing at it |
| $u_f = 9$ | Left by the last fuse | The batch claim $(P_f, u_f, v_f)$ |
| $y = 35$, $z = 11$ | Fresh in compression | The circuit claims' wiring $s_i(X, y)$ and $t(X, z)$, and the weight that puts two stages under one mask |
| $\sigma = 20$ | Fresh in compression | The wire binding of Section 3 |
| $w = 3$ | Fresh in compression | The point at which the verifier opens the restriction, in Section 6 |

The fuse values here are not the output of the [transcript run of the last chapter](./ragu-recursion.md#_4-splitting-the-transcript), which would give $x_f = 4$, $y_f = 4$ and $u_f = 25$. We built the instance from the two circuits of the staging chapter so that every vector stays short, and we chose the fuse values to suit it. Two of them coincide by chance, since $x_f = u_f = 9$.

<!-- /worked:challenges -->

## 3. The instance and its claims

The instance has to tell the verifier everything it would otherwise read off the polynomials. For our two circuits it holds the following entries.

<!-- worked:instance -->

| Instance entry | Toy value | Role |
| --- | --- | --- |
| $\bar{A}$, $\bar{Q}$ | $(22,\,24)$, $(14,\,9)$ | Two stages. $a$ is the stage of the staging chapter, and $q$ holds the values read from the registry |
| $\bar{R}'_1$, $\bar{R}'_2$ | $(24,\,30)$, $(24,\,1)$ | Final traces of the squaring and cubing circuits |
| $\bar{A}_{\text{acc}}$, $\bar{B}_{\text{acc}}$ | $(1,\,29)$, $(25,\,29)$ | The accumulator pair |
| $c_{\text{acc}}$ | $11$ | The pair's stored revdot value |
| $\bar{M}$ | $(17,\,24)$ | The restriction $m(W, x_f, y_f)$ |
| $\bar{P}_f$, $v_f$ | $(27,\,30)$, $37$ | The batch claim at $u_f$ |
| $A_{\text{acc}}(u_f)$, $B_{\text{acc}}(u_f)$ | $35$, $15$ | The values of the accumulator pair at $u_f$ that the last fuse's eval stage claims |

<!-- /worked:instance -->

These numbers carry over from earlier chapters. The accumulator pair stands in for what the last fuse left, and we took the claim of the squaring circuit with input 5, built at $y_f$ and $z_f$, for it. The polynomial behind $\bar{P}_f$ is [chapter 6's example](./polynomial-commitments.md), opened at its point $u_f$. The real [instance](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L66-L102) holds a commitment for each native and nested polynomial, which makes it the largest part of the proof.

The verifier now rebuilds the decider's revdot claims from what it holds, in the order of the code's [claim list](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L160-L300). Each circuit's full trace is its stage plus its final trace, so we write $r_1 = a + r'_1$ and $r_2 = a + r'_2$. The "Kind" column says how each claim was built. A raw claim is the stored accumulator pair, taken as it is. A circuit claim checks a trace against its wiring, as in [chapter 9](./nark.md). A mask counts as a bonding claim because the staging chapter treats a mask as [the special case of a bonding polynomial](./staging.md#_12-linking-stages-with-a-bonding-polynomial) whose constraints each set one wire to zero.

Each mask forces to zero every wire outside the gates it reserves, except for gate 0, which [no mask touches](./staging.md#_7-a-mask-for-every-polynomial) because every polynomial keeps its own random entry $a_0$ there. In our circuits the stages $a$ and $q$ occupy gate 1, so the stage mask leaves gates 0 and 1 free. The final traces occupy gates 2 and 3, so the final mask leaves gates 0, 2 and 3 free. Slot 3 combines the two stages under one mask, with the weight $z$, as [Section 8 of the staging chapter](./staging.md#_8-sharing-one-mask-claim) combined two children's stages. The wire binding in slot 5 is new, and the next subsection builds it.

<!-- worked:claims -->

| Slot $i$ | Claim | Kind | Left vector $\v{\ell}_i$ | Right vector $\v{b}_i$ | Target $k_i$ |
| --- | --- | --- | --- | --- | --- |
| 0 | Accumulator | Raw | $A_{\text{acc}}$ | $B_{\text{acc}}$ | $11$ |
| 1 | Squaring circuit | Circuit | $r_1 = a + r'_1$ | $r_1(zX) + s_1(X, y) + t(X, z)$ | $7$ |
| 2 | Cubing circuit | Circuit | $r_2 = a + r'_2$ | $r_2(zX) + s_2(X, y) + t(X, z)$ | $22$ |
| 3 | Stage mask | Bonding | $z\,a + q$ | Mask freeing gate 1 | $0$ |
| 4 | Final mask | Bonding | $z\,r'_1 + r'_2$ | Mask freeing gates 2, 3 | $0$ |
| 5 | Wire binding | Masked | $q - E_\sigma$ | $M_\sigma$ | $0$ |

<!-- /worked:claims -->

<!-- worked:targets -->

The target of slot 0 is the stored value $c_{\text{acc}} = 11$. The targets of slots 1 and 2 are the circuits' public input polynomials at $y$. The squaring circuit has $k_1(Y) = 1 + 10Y$ and the cubing circuit has $k_2(Y) = 1 + 35Y$, so the targets are $1 + 10 \cdot 35 = 7$ and $1 + 35 \cdot 35 = 22$ modulo 43. The three remaining claims have target 0, because masks and wire bindings carry no public inputs.

<!-- /worked:targets -->

### Binding stage wires to the registry

The first five claims have appeared in earlier chapters. The sixth answers a check from the decider's list in Section 1. The last fuse's query stage holds registry values such as $m(\omega_i, x_f, y_f)$, the wiring value of each internal circuit at the fuse's challenges, and the fuse's circuits used those wires in their checks. Nothing inside the tree ties the wires to the true registry, because no circuit can afford to evaluate the registry. The decider closes the gap by reading the wires off the stage polynomial and comparing them with values it computes from the registry. A compressed verifier holds only the stage's commitment, so it needs another way to make the same comparison. The code [turns each such comparison into a revdot claim](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/revdot/claims.rs#L35-L52). For wires at degrees $d_j$ with expected values $q^*_j$, it places the expected values at those degrees and puts the powers of a challenge $\sigma$ in the mirrored positions:

$$E_\sigma = \sum_j q^*_j X^{d_j}, \qquad M_\sigma = \sum_j \sigma^j X^{D - 1 - d_j}.$$

A revdot product pairs the coefficient of $X^k$ in its left vector with the coefficient of $X^{D-1-k}$ in its right vector. The only nonzero entries of $M_\sigma$ sit at $D - 1 - d_j$, so the product reads the left vector only at the degrees $d_j$, where $q - E_\sigma$ holds $q_{d_j} - q^*_j$:

$$\revdot{\v{q} - \v{E}_\sigma}{\v{M}_\sigma} = \sum_j \sigma^j (q_{d_j} - q^*_j).$$

The target is 0. The right side is a polynomial in $\sigma$ whose coefficients are the errors, so it vanishes at a random $\sigma$ only if each wire holds its expected value. The code calls this kind of claim "masked", because its right vector $M_\sigma$ is a public mask that reads chosen wires, where an ordinary mask forbids them. The real list has [five such claims natively and three on the nested side](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L515-L710). The query stage gives one of them, and the others cover the preamble, the eval stage and two points stages. In our run a small stage $q(X)$ plays the role of the query stage, and the comparison is the one just described.

<!-- worked:binding -->

The registry here has two circuits at $W = 1$ and $W = -1$, whose wiring gives $m(1, x_f, y_f) = 11$ and $m(-1, x_f, y_f) = 12$. The stage $q(X)$ claims those values in the wires $a_1$ and $d_1$, so the expected values are $q^*_0 = 11$ and $q^*_1 = 12$. With $\sigma = 20$, the mask $M_\sigma$ has a $1$ opposite $a_1$ and a $20$ opposite $d_1$, and $E_\sigma$ holds the expected values at those two degrees. So the product is $(a_1 - 11) + 20(d_1 - 12) = 0$. If the stage holds a wrong $a_1$, the product is nonzero at all 43 values of $\sigma$. If both wires are wrong, the two errors cancel at one value of $\sigma$ out of 43. This registry holds the staging chapter's two circuits and not the registry of [chapter 15](./wiring-and-registry.md), so its $m(W, 9, 7)$ is a different polynomial from the one that the [last chapter's toy](./ragu-recursion.md) committed under the same name, even though the two runs share $x_f = 9$ and $y_f = 7$.

<!-- /worked:binding -->

<!-- worked:real-claims -->

A real compressed proof has $56$ native claims, namely one accumulator pair, one application circuit, $33$ internal circuits, $16$ masks and $5$ wire bindings, and it has $46$ nested claims.

<!-- /worked:real-claims -->

## 4. Folding to three claims

Rather than prove the six revdot claims one at a time, the verifier folds them into one pair with random weights, as [chapter 14](./revdot-folding.md) did. It takes the grouping of chapter 14's [two-layer fold](./revdot-folding.md#_8-two-layers), which splits the claims into groups, and our run uses groups of three, so the six claims form two groups. We write claim $i$ as the pair $(\gamma, \kappa)$ of its group and its slot within the group. The fold draws four fresh challenges, $\mu_c$ and $\mu'_c$ for the left vectors and $\nu_c$ and $\nu'_c$ for the right ones. These are the plain weights that [chapter 14's Section 11](./revdot-folding.md#_11-compression-and-the-forms-of-the-fold) names $\mu_c$ and $\nu_c$, and they relate to the book's weights $\mu^{-i}$ and $(\mu\nu)^j$ of chapter 14's Section 8 through $\mu_c = \mu^{-1}$ and $\nu_c = \mu\nu$. Claim $(\gamma, \kappa)$ takes the weights

$$\lambda_i = (\mu'_c)^\gamma \mu_c^\kappa, \qquad \eta_i = (\nu'_c)^\gamma \nu_c^\kappa.$$

The accumulator pair always sits in slot 0 of group 0, at $(\gamma, \kappa) = (0, 0)$, so $\lambda_0 = \eta_0 = 1$ in every proof, whatever the challenges.

The folded pair is $\v{A} = \sum_i \lambda_i \v{\ell}_i$ and $\v{B} = \sum_i \eta_i \v{b}_i$. To see what target this pair should have, expand the revdot product by bilinearity. Write $e_{i,j} = \revdot{\v{\ell}_i}{\v{b}_j}$, and let claim $j$ sit at $(\gamma', \kappa')$:

$$\revdot{\v{A}}{\v{B}} = \sum_{i,j} \lambda_i \eta_j\, e_{i,j} = \sum_{i,j} (\mu'_c)^\gamma (\nu'_c)^{\gamma'} \mu_c^\kappa \nu_c^{\kappa'}\, e_{i,j}.$$

The pairs $(i, j)$ fall into three sets, and each set behaves differently.

- **The diagonal, $i = j$.** Here $e_{i,i}$ is claim $i$'s own product, which equals $k_i$ if the claim is true. These terms give $\sum_i \lambda_i \eta_i k_i$, which the verifier can compute.
- **Pairs in the same group, $\gamma = \gamma'$ and $\kappa \ne \kappa'$.** The weight is $(\mu'_c\nu'_c)^\gamma \mu_c^\kappa \nu_c^{\kappa'}$. We call the sum of these terms $\varepsilon_1$.
- **Pairs in different groups, $\gamma \ne \gamma'$.** For a fixed $\gamma$ and $\gamma'$ the factor $(\mu'_c)^\gamma (\nu'_c)^{\gamma'}$ is common to all the terms, and by bilinearity the rest adds up to the revdot product of two group-folded vectors, $\v{A}_\gamma = \sum_\kappa \mu_c^\kappa \v{\ell}_{(\gamma,\kappa)}$ and $\v{B}_{\gamma'} = \sum_{\kappa'} \nu_c^{\kappa'} \v{b}_{(\gamma',\kappa')}$. We call the sum of these terms $\varepsilon_2$.

Written out, the two sums are

$$\varepsilon_1 = \sum_\gamma (\mu'_c\nu'_c)^\gamma \sum_{\kappa \ne \kappa'} \mu_c^\kappa \nu_c^{\kappa'}\, e_{(\gamma,\kappa),(\gamma,\kappa')}, \qquad \varepsilon_2 = \sum_{\gamma \ne \gamma'} (\mu'_c)^\gamma (\nu'_c)^{\gamma'} \revdot{\v{A}_\gamma}{\v{B}_{\gamma'}}.$$

So the target of the folded pair is $K = \sum_i \lambda_i \eta_i k_i + \varepsilon_1 + \varepsilon_2$. The verifier cannot compute $\varepsilon_1$ or $\varepsilon_2$, because they need the vectors. The prover computes them and sends them as two scalars, and the verifier forms $K$ from them. If nothing else checked the two scalars, the prover could make $K$ anything it liked. Compression makes each of them a revdot claim of its own, which the split of Section 5 tests together with the folded pair.

The prover lays the first-layer terms $e_{(\gamma,\kappa),(\gamma,\kappa')}$ out as the low coefficients of a vector $\v{E}_1$, in the fuse's order, group by group and row by row. A public vector $\v{W}_1$ holds the weight of each term in the mirrored position, so the term at degree $d$ of $\v{E}_1$ meets its weight at degree $D - 1 - d$ of $\v{W}_1$. A revdot product pairs exactly those two degrees, so $\revdot{\v{E}_1}{\v{W}_1} = \varepsilon_1$. The second-layer terms $\revdot{\v{A}_\gamma}{\v{B}_{\gamma'}}$ and their weights $(\mu'_c)^\gamma (\nu'_c)^{\gamma'}$ go into $\v{E}_2$ and $\v{W}_2$ in the same way.

The order of the commitments matters. The first-layer terms depend only on the claims, so the prover commits to $\v{E}_1$ before $\mu_c$ and $\nu_c$ exist. The second-layer terms depend on $\mu_c$ and $\nu_c$, through $\v{A}_\gamma$ and $\v{B}_{\gamma'}$, so the prover can only compute them afterwards. It commits to $\v{E}_2$ after $\mu_c$ and $\nu_c$ and before $\mu'_c$ and $\nu'_c$, and it sends $\varepsilon_1$ and $\varepsilon_2$ once all four challenges are [in the transcript](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/revdot/fold.rs#L67-L76). So in both layers the prover fixes the cross terms before it knows the weights that will combine them, and Section 9 shows what a prover could do if the order were different.

<!-- worked:fold-run -->

Claim $i$ sits in group $\gamma = \lfloor i / 3 \rfloor$ at slot $\kappa = i \bmod 3$. Claim 4, for example, has $\gamma = 1$ and $\kappa = 1$, so $\lambda_4 = \mu'_c\mu_c$. With $\mu_c = 19$, $\nu_c = 38$, $\mu'_c = 2$ and $\nu'_c = 33$, that is $\lambda_4 = 2 \cdot 19 = 38$, and the six pairs of weights are these.

| Claim $i$ | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- | --- |
| $\lambda_i$ | $1$ | $19$ | $17$ | $2$ | $38$ | $34$ |
| $\eta_i$ | $1$ | $38$ | $25$ | $33$ | $7$ | $8$ |

**First layer.** The prover computes the twelve in-group cross terms and commits to them as $\bar{E}_1 = (20,\,25)$ before any weight exists. Once all four challenges are drawn, each term gets the weight $(\mu'_c\nu'_c)^\gamma \mu_c^\kappa \nu_c^{\kappa'}$. The pair $(0, 1)$ has $\gamma = 0$, $\kappa = 0$ and $\kappa' = 1$, so its weight is $\nu_c = 38$. The pair $(3, 4)$ has $\gamma = 1$, $\kappa = 0$ and $\kappa' = 1$, so its weight is $\mu'_c\nu'_c\nu_c = 2 \cdot 33 \cdot 38 = 14$ modulo 43.

| Pair $(i, j)$, group 0 | $(0, 1)$ | $(0, 2)$ | $(1, 0)$ | $(1, 2)$ | $(2, 0)$ | $(2, 1)$ |
| --- | --- | --- | --- | --- | --- | --- |
| $e_{i,j}$ | $40$ | $9$ | $2$ | $36$ | $11$ | $34$ |
| Weight in $\v{W}_1$ | $38$ | $25$ | $19$ | $2$ | $17$ | $1$ |

| Pair $(i, j)$, group 1 | $(3, 4)$ | $(3, 5)$ | $(4, 3)$ | $(4, 5)$ | $(5, 3)$ | $(5, 4)$ |
| --- | --- | --- | --- | --- | --- | --- |
| $e_{i,j}$ | $36$ | $28$ | $29$ | $0$ | $0$ | $0$ |
| Weight in $\v{W}_1$ | $14$ | $16$ | $7$ | $3$ | $4$ | $23$ |

The first term sits at degree 0 of $\v{E}_1$, and its weight $38$ sits at degree $15$ of $\v{W}_1$. The seventh term sits at degree 6 and its weight $14$ at degree $9$. Multiplying each term by its weight and adding gives $12$ for group 0 and $37$ for group 1, so $\varepsilon_1 = 6$ modulo 43.

The last three terms of group 1, $e_{4,5}$, $e_{5,3}$ and $e_{5,4}$, are zero because the paired vectors never meet in mirrored positions. The wire-binding vector $q - E_\sigma$ keeps only the random entry $a_0$ of the stage $q$, which sits in gate 0, and no mask touches gate 0. The vector $M_\sigma$ reads only the wires $a_1$ and $d_1$, which belong to the stages, and the final traces leave gate 1 empty.

**Second layer.** With $\mu_c$ and $\nu_c$ known, the prover forms $\v{A}_0$, $\v{B}_0$, $\v{A}_1$ and $\v{B}_1$ and computes the two cross-group terms $\revdot{\v{A}_0}{\v{B}_1} = 22$ and $\revdot{\v{A}_1}{\v{B}_0} = 30$. It commits to them as $\bar{E}_2 = (27,\,1)$, and only then are $\mu'_c$ and $\nu'_c$ drawn. Their weights are $(\mu'_c)^0(\nu'_c)^1 = 33$ and $(\mu'_c)^1(\nu'_c)^0 = 2$, so $\varepsilon_2 = 22 \cdot 33 + 30 \cdot 2 = 12$ modulo 43.

**The target.** The prover sends $\varepsilon_1 = 6$ and $\varepsilon_2 = 12$. The diagonal gives $\sum_i \lambda_i \eta_i k_i = 10$, so the verifier sets $K = 10 + 6 + 12 = 28$. The prover can check that $\revdot{\v{A}}{\v{B}}$ is also $28$, but the verifier cannot compute that product, and the split of Section 5 is what tests it.

<!-- /worked:fold-run -->

::: details Why groups, and which form of the fold
Compression uses the form of the fold in the [code's compression module](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/revdot/fold.rs#L1-L34). [Chapter 14](./revdot-folding.md#_11-compression-and-the-forms-of-the-fold) noted that this form differs from the fuse's quotient fold, and that the sources do not say why.

The code folds in two layers, as the run above did. [Chapter 14's reason for groups](./revdot-folding.md#_8-two-layers) was the cost inside a circuit, where the number of cross terms grows as the square of the list's length. Compression runs outside any circuit, so that reason does not carry over, and the sources give no reason specific to compression. The code labels its group size of seven as [the fuse's](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/revdot/fold.rs#L48-L49) and lays out the cross terms in the fuse's order, so in our reading compression reuses the fuse's arrangement.

<!-- worked:group-reason -->

The real claim lists of Section 3 show the effect. With one layer, every ordered pair of distinct claims gives a cross term, so the $56$ native claims would need $56 \cdot 55 = 3,080$ terms in $\v{E}_1$. In groups of $7$ they form $8$ groups. The pairs inside each group give $336$ first-layer terms in $\v{E}_1$, and the ordered pairs of distinct groups give $56$ second-layer terms in $\v{E}_2$, or $392$ in all. The $46$ nested claims form $7$ groups in the same way, with $264$ first-layer and $42$ second-layer terms. Even the single layer fits in a vector of $8,192$ entries, so the vector length does not force the grouping.

<!-- /worked:group-reason -->
:::

The vectors $\v{A}$ and $\v{B}$ have public parts that nobody needs to commit to, so the verifier separates what it derives from commitments and what it evaluates alone. A circuit claim's right vector contains its own trace dilated, $r_i(zX)$, so the committed polynomial $T = \eta_1 r_1 + \eta_2 r_2$ takes care of that part when it is evaluated at $zX$. Reading the left and right vectors off the claims table and sorting each term by whether it comes from a commitment gives

$$A(X) = A_c(X) + A_{\text{pub}}(X), \qquad B(X) = B_c(X) + T(zX) + B_{\text{pub}}(X),$$

with these parts:

$$
\begin{aligned}
A_c &= \lambda_0 A_{\text{acc}} + \lambda_1 r_1 + \lambda_2 r_2 + \lambda_3 (z\,a + q) + \lambda_4 (z\,r'_1 + r'_2) + \lambda_5\, q, \\
A_{\text{pub}} &= -\lambda_5 E_\sigma, \\
B_c &= \eta_0 B_{\text{acc}}, \\
B_{\text{pub}} &= \eta_1 \big(s_1(X, y) + t(X, z)\big) + \eta_2 \big(s_2(X, y) + t(X, z)\big) + \eta_3 \cdot \text{mask}_1 + \eta_4 \cdot \text{mask}_{2,3} + \eta_5 M_\sigma.
\end{aligned}
$$

The committed parts are combinations of the instance's points with known weights, so the verifier gets their commitments without any help from the prover.

<!-- worked:derived -->

The verifier obtains $\bar{A}_c = (11,\,30)$, $\bar{T} = (20,\,25)$ and $\bar{B}_c = (25,\,29)$ from small MSMs over the instance's points, with the weights above. Because $\eta_0 = 1$ in every proof, the point $\bar{B}_c$ is $\bar{B}_{\text{acc}}$ itself. Committing to the three polynomials directly gives the same points.

<!-- /worked:derived -->

## 5. The split

We have three revdot claims, $(A, B, K)$, $(E_1, W_1, \varepsilon_1)$ and $(E_2, W_2, \varepsilon_2)$, and nothing has yet shown that any of them is true. The [split from chapter 5](./polynomial-encoding.md#_12-splitting-the-product) handles this. Proving three products separately would cost three splits, so the prover first combines them with a fresh challenge $\rho$ into one product polynomial,

$$\Pi(X) = A(X)B(X) + \rho\,E_1(X)W_1(X) + \rho^2 E_2(X)W_2(X).$$

A revdot product is the coefficient of $X^{D-1}$ in the ordinary product, so the coefficient of $X^{D-1}$ in $\Pi$ is $K + \rho\,\varepsilon_1 + \rho^2\varepsilon_2$ when all three claims hold. To make that one coefficient checkable by an opening, the prover cuts $\Pi$, which has degree $2D - 2$, into a low half and a high half. The low half holds the coefficients of $X^0$ through $X^{D-1}$ in reverse order, and the high half holds the rest:

$$\Pi(X) = X^{D-1}\, \Pi_{\text{lo}}(1/X) + X^D\, \Pi_{\text{hi}}(X).$$

Reversing the low half moves the coefficient of $X^{D-1}$ to the constant term, so it lands in $\Pi_{\text{lo}}(0)$. The verifier received $\varepsilon_1$ and $\varepsilon_2$ from the prover and formed $K$ from them, so it can compute the value that $\Pi_{\text{lo}}(0)$ must have, and it checks that value later with an opening at $0$.

The prover commits to both halves, and the verifier now needs to know that they really are the two halves of $\Pi$. It picks a fresh random point $r$, a single field element unrelated to the traces $r_1$ and $r_2$, and checks the identity above at $X = r$. One point is enough for the following reason. If the committed halves are wrong, the two sides of the identity differ by a nonzero polynomial of degree at most $2D - 2$, and by [chapter 3's root count](./statements-and-challenges.md#_4-counting-the-roots-of-a-polynomial) such a polynomial vanishes at no more than $2D - 2$ points. So the two sides agree at a random $r$ with probability at most $(2D - 2)/|\F|$, and the prover had to commit to the halves before $r$ was drawn. Evaluating the identity at $r$ needs the value of each committed piece at $r$, except that $T$ is needed at $rz$ and $\Pi_{\text{lo}}$ at $1/r$.

<!-- worked:split-run -->

At $\rho = 41$ the prover commits to $\bar{\Pi}_{\text{lo}} = (23,\,7)$ and $\bar{\Pi}_{\text{hi}} = (30,\,8)$. The verifier sets aside the required value $\Pi_{\text{lo}}(0) = K + \rho\,\varepsilon_1 + \rho^2\varepsilon_2 = 28 + 41 \cdot 6 + 4 \cdot 12 = 21$, using $\rho^2 = 4$. It then picks $r = 18$, so that $rz = 26$ and $1/r = 12$, and the prover sends seven values.

| $A_c(r)$ | $T(rz)$ | $B_c(r)$ | $E_1(r)$ | $E_2(r)$ | $\Pi_{\text{lo}}(1/r)$ | $\Pi_{\text{hi}}(r)$ |
| --- | --- | --- | --- | --- | --- | --- |
| $38$ | $7$ | $12$ | $25$ | $3$ | $10$ | $8$ |

The verifier evaluates the public parts at $r$ itself. Only the wire binding contributes to $A_{\text{pub}}$, and $E_\sigma(r) = 7$, so

$$A_{\text{pub}}(r) = -\lambda_5 E_\sigma(r) = -34 \cdot 7 = 20 \pmod{43}.$$

For $B_{\text{pub}}$ it computes $s_1(r, y) = 39$, $s_2(r, y) = 9$ and $t(r, z) = 3$, the stage mask and final mask at $r$, which are $28$ and $29$, and $M_\sigma(r) = 5$. With the weights $\eta_i$ from Section 4,

$$B_{\text{pub}}(r) = \eta_1 (s_1 + t) + \eta_2 (s_2 + t) + \eta_3\, \text{mask}_1(r) + \eta_4\, \text{mask}_{2,3}(r) + \eta_5 M_\sigma(r) = 38(39 + 3) + 25(9 + 3) + 33 \cdot 28 + 7 \cdot 29 + 8 \cdot 5 = 10.$$

So $A(r) = A_c(r) + A_{\text{pub}}(r) = 38 + 20 = 15$ and $B(r) = B_c(r) + T(rz) + B_{\text{pub}}(r) = 12 + 7 + 10 = 29$, modulo 43. The public vectors of the fold give $W_1(r) = 14$ and $W_2(r) = 7$, so the left side of the split is

$$A(r)B(r) + \rho\,E_1(r)W_1(r) + \rho^2 E_2(r)W_2(r) = 5 + 31 + 41 = 34,$$

and the right side is $r^{15}\Pi_{\text{lo}}(1/r) + r^{16}\Pi_{\text{hi}}(r) = 5 + 29 = 34$.

<!-- /worked:split-run -->

The split is also where the prover does work that the fuse never does. Forming $\Pi$ means multiplying polynomials of $D$ coefficients, which the prover does with FFTs. A fuse folds a child's revdot claims into its own accumulator and leaves them unproved, so it never needs the product. Compression is where the accumulated claims [finally get proved](./revdot-folding.md#_11-compression-and-the-forms-of-the-fold), so it is the one step that pays for the product polynomial.

The two sides agree, but all seven values are still only claims about commitments, which the next step settles.

## 6. Batching and the argument

<!-- worked:claims-count -->

The reduction leaves $8$ claims, $7$ from the values above and one for the required $\Pi_{\text{lo}}(0)$. The instance adds [$4$ of its own](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L717-L741), which carry the fuse's accumulators into the check.

<!-- /worked:claims-count -->

Each claim says that a committed polynomial takes a value $y_j$ at a point $x_j$, in the notation of [chapter 8](./batched-openings.md).

<!-- worked:claims-list -->

| Claim $j$ | Polynomial | Commitment | Point $x_j$ | Value $y_j$ |
| --- | --- | --- | --- | --- |
| 0 | $A_c$ | $(11,\,30)$ | $18$ | $38$ |
| 1 | $T$ | $(20,\,25)$ | $26$ | $7$ |
| 2 | $B_c$ | $(25,\,29)$ | $18$ | $12$ |
| 3 | $E_1$ | $(20,\,25)$ | $18$ | $25$ |
| 4 | $E_2$ | $(27,\,1)$ | $18$ | $3$ |
| 5 | $\Pi_{\text{lo}}$ | $(23,\,7)$ | $12$ | $10$ |
| 6 | $\Pi_{\text{hi}}$ | $(30,\,8)$ | $18$ | $8$ |
| 7 | $\Pi_{\text{lo}}$ | $(23,\,7)$ | $0$ | $21$ |
| 8 | $m(W, x_f, y_f)$ | $(17,\,24)$ | $3$ | $10$ |
| 9 | $P_f$ | $(27,\,30)$ | $9$ | $37$ |
| 10 | $A_{\text{acc}}$ | $(1,\,29)$ | $9$ | $35$ |
| 11 | $B_{\text{acc}}$ | $(25,\,29)$ | $9$ | $15$ |

<!-- /worked:claims-list -->

The last four rows are what the decider still owes from the recursion. Claim 8 is the [restriction check of chapter 15](./wiring-and-registry.md#_13-wiring-and-the-registry-in-ragu). Claim 9 is the fuse's accumulated [$(P_f, u_f, v_f)$](./split-accumulation.md#_6-a-run-on-the-toy-curve).

Claims 10 and 11 need a word of explanation. The last fuse's eval stage holds wires that claim the values $A_{\text{acc}}(u_f)$ and $B_{\text{acc}}(u_f)$, and the fuse's circuit `compute_v` used those wires, along with the other values in its query and eval stages, to [compute $v_f$](./ragu-recursion.md#the-schedule). No circuit checked that the wires hold the true evaluations. The code closes the gap in two steps. The eval stage's [wire binding](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L575-L600) checks that the wires equal the instance's two values, and claims 10 and 11 [check that those values are the evaluations](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L713-L741) of the committed pair. Together they answer the decider's check of the values the eval stage claims. Our toy has no eval stage, so in our run the two values from the instance table feed only into their own openings.

<!-- worked:registry-value -->

Claim 8 opens $m(W, x_f, y_f)$ at the fresh point $w = 3$. The verifier computes the value for itself. It evaluates the wiring of both circuits at $(x_f, y_f)$, which gives $11$ and $12$ as above, and combines them with the Lagrange weights of the two domain points $1$ and $-1$: $m(w, x_f, y_f) = \tfrac{1}{2}\big((1 + w) \cdot 11 + (1 - w) \cdot 12\big) = \tfrac{1}{2}\big(44 - 24\big) = 10$ modulo 43. This is the step that reads the whole registry.

<!-- /worked:registry-value -->

<!-- worked:batch-counts -->

[Chapter 8's batch](./batched-openings.md#_7-beta-batching) turns all $12$ claims into one. It needs two counts, because several claims can be about the same polynomial. Write $h_0, \ldots, h_{N-1}$ for the distinct polynomials and $J$ for the number of claims, where claim $j$ is about the polynomial $h_{i_j}$. $\Pi_{\text{lo}}$ appears in two claims and counts once, so our run has $N = 11$ polynomials and $J = 12$ claims.

<!-- /worked:batch-counts -->

$B_c$ and $B_{\text{acc}}$ count as two polynomials, even though $B_c = \eta_0 B_{\text{acc}} = B_{\text{acc}}$ in every proof, as Section 4 noted. The code keeps the reduction's openings and the instance's openings in [separate lists](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L713-L741) and does not merge them, and our toy keeps the same layout. Merging the two would save one value in the batch.

The batch itself takes three messages. After a fresh challenge $\alpha$, the prover commits to the quotient $f(X) = \sum_j \alpha^{J-1-j}\, (h_{i_j}(X) - y_j) / (X - x_j)$. After a fresh point $u$, it sends each polynomial's value $h_i(u)$. A last challenge $\beta$ then weights the polynomials, and the verifier derives

$$\bar{H} = \beta^{N} \cdot \bar{F} + \sum_{i=0}^{N-1} \beta^{N-1-i} \cdot \bar{h}_i,$$

$$v = \beta^{N} \sum_{j=0}^{J-1} \alpha^{J-1-j}\, \frac{h_{i_j}(u) - y_j}{u - x_j} + \sum_{i=0}^{N-1} \beta^{N-1-i} h_i(u).$$

Unlike the fuse's $\beta$, which has to be short so that a circuit can scale points with it, this $\beta$ is [an ordinary squeezed element](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/batch/verifier.rs#L65), since no circuit runs this verifier.

<!-- worked:batch-run -->

With $\alpha = 17$ the quotient commits to $\bar{F} = (5,\,29)$. At $u = 38$ the prover sends the eleven values $h_i(u)$, which are $(18, 5, 35, 18, 1, 12, 36, 14, 5, 22, 35)$. The verifier derives $f(u) = 30$ from those values and the claims. With $\beta = 20$ this gives $\bar{H} = (28,\,10)$ and $v = 14$, and the prover's polynomial $H$ agrees on both.

<!-- /worked:batch-run -->

Now [the inner product argument of chapter 7](./inner-product-argument.md), in [the code's form](./inner-product-argument.md#_10-the-code-s-opening-statement), proves $H(u) = v$. Recall the three changes that form makes to the statement. It moves the value into the constant coefficient by subtracting $v \cdot G_0$, where $G_0$ is the first generator. It adds $\xi$ times a committed masking polynomial $\bar{S}$ that vanishes at $u$, for a fresh challenge $\xi$ (Section 10 discusses what this mask does not provide). Finally, it scales the generator $U$ by a fresh multiplier, which chapter 7 called $z$ and we call $\zeta$ here, because $z$ already names a challenge of this chapter. The four round challenges are fresh as well.

<!-- worked:ipa-run -->

The argument commits to the masking polynomial, $\bar{S} = (26,\,23)$, and takes $\xi = 29$ and a multiplier $\zeta = 12$ on $U$. The statement becomes $\bar{H} - v \cdot G_0 + \xi \cdot \bar{S} = (1,\,29)$. Then come $\log_2 16 = 4$ rounds.

| Round | Challenge | $L_j$ | $R_j$ |
| --- | --- | --- | --- |
| 1 | 12 | $(25,\,29)$ | $(23,\,7)$ |
| 2 | 17 | $(30,\,8)$ | $(22,\,7)$ |
| 3 | 33 | $(22,\,7)$ | $(25,\,29)$ |
| 4 | 41 | $(16,\,21)$ | $(23,\,24)$ |

The final scalar is $\hat{a} = 38$. The verifier computes $\hat{G} = (18,\,10)$ from an MSM over all sixteen generators and $\hat{b} = 14$ from a product of four factors. The folded statement is $(22,\,7)$, and $\hat{a} \cdot (\hat{G} + \hat{b} \zeta \cdot U) = (22,\,7)$, so the verifier accepts.

<!-- /worked:ipa-run -->

<!-- worked:coincidence -->

With only 43 points on the toy curve, several points in this run repeat by chance: $\bar{A}_{\text{acc}}$ and the IPA statement are both $(1,\,29)$; $\bar{B}_{\text{acc}}$, $L_1$ and $R_3$ are all $(25,\,29)$; $\bar{T}$ and $\bar{E}_1$ are both $(20,\,25)$; $\bar{\Pi}_{\text{lo}}$ and $R_1$ are both $(23,\,7)$; $\bar{\Pi}_{\text{hi}}$ and $L_2$ are both $(30,\,8)$; $R_2$ and $L_3$ are both $(22,\,7)$. The vectors behind them differ. On the real curves, with about $2^{254}$ points each, such a repeat does not happen in practice.

<!-- /worked:coincidence -->

That finishes the run on this curve. In the code the same three reductions run again on the nested curve with its own claims, [on one continuous transcript](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/mod.rs#L25-L26).

Section 1 listed six checks that the decider makes with the full polynomials. Each one now has a counterpart that works from commitments, as the table shows.

| Decider's check | Where compression makes it |
| --- | --- |
| Each revdot claim, including the accumulated pair | The fold of Section 4 and the split of Section 5, whose values are opened in the batch |
| The accumulated batch claim $P_f(u_f) = v_f$ | Claim 9, the opening of $P_f$ at $u_f$ |
| The restriction $m(W, x_f, y_f)$ against the registry | Claim 8, the opening of $m(W, x_f, y_f)$ at $w$, whose value the verifier computes from the registry |
| The challenges | The replay of Section 2 over the bridge commitments |
| The values in the query and eval stages | The wire bindings of Section 3, with claims 10 and 11 for the accumulator pair at $u_f$ |
| Every cached commitment | Each commitment enters the batch, and the IPA opens the batch |

## 7. What the verifier pays

[Chapter 9 named two linear costs](./nark.md#_17-a-short-proof-from-the-same-parts), computing $s(x, y)$ and computing $\hat{G}$, and the Recursion part set out to remove them from the circuits. Recursion moved these costs out of every circuit without removing them, and [the wiring chapter](./wiring-and-registry.md#_13-wiring-and-the-registry-in-ragu) deferred the last piece to this page. The verifier of a compressed proof pays them once, at the root, as the table shows.

<!-- worked:verifier-cost -->

| Verifier step, per curve | Work | Growth |
| --- | --- | --- |
| Replay the fuse transcript (Section 2) | $8$ permutations, on the native field only | Constant |
| Recompute the challenge stage and the `ab` bridge (Section 2) | Two small commitments, on the nested curve only | Constant |
| Compute targets $k(y)$ | One Horner step per public wire | Size of the instance |
| Derive $\bar{A}_c$, $\bar{T}$, $\bar{B}_c$, $\bar{H}$ | MSMs over the instance's points | Size of the instance |
| Compute $s_i(r, y)$ for each circuit claim | $34$ native and $28$ nested circuits, one term per wiring coefficient | **Linear in the circuits** |
| Compute registry values for the wire bindings | One pass over the domain at $(x_f, y_f)$, plus a constant number of further evaluations | **Linear in the registry** |
| Compute $m(w, x_f, y_f)$ | One pass over the registry, with Lagrange weights | **Linear in the registry** |
| Compute masks and $t(r, z)$ | Closed forms | Logarithmic |
| Compute $\hat{b}$ and combine the $L_j$, $R_j$ | $26$ scalar multiplications and $13$ factors | Logarithmic |
| Compute $\hat{G}$ | 1 MSM of $8,192$ scalar multiplications | **Linear in the vector length** |

<!-- /worked:verifier-cost -->

The rows in bold are what remains of chapter 9's two costs. Wiring appears in three of them, because the verifier needs wiring values for three different checks.

- The split needs $B(r)$, and each circuit claim's right vector contains that circuit's wiring $s_i(X, y)$. So the verifier evaluates [each circuit's wiring at $(r, y)$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/revdot/verifier.rs#L231).
- The wire bindings need the expected value of each registry wire that the last fuse's query and eval stages hold. So the verifier evaluates [the registry over its domain and at a few further points](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L555-L601).
- Claim 8 needs the true value of the restriction at $w$. So the verifier evaluates [the registry at $(w, x_f, y_f)$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/instance.rs#L734). This is the evaluation that chapter 15 described. It lets a whole tree of fuses rely on one restriction polynomial, since the verifier [checks that polynomial against the full registry](./wiring-and-registry.md#_6-consistency-for-the-registry) exactly once.

The pass over the domain gives one value for each internal circuit. Each of these evaluations grows with the wiring of the registered circuits, including the application's steps.

The last row is the [deferred MSM of chapter 11](./accumulation.md). Compression [computes it in full](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/batch/verifier.rs#L28-L35), with one per curve. None of these costs grows with the depth of the tree, so a proof that covers many leaves has the same verifier as a proof that covers two.

## 8. The size of the result

Counting from the [code's wire format](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/compressed.rs#L69-L150) gives the following, for the standard profile at the production rank of 13 and headers of 4 elements, which is the [size the code's benchmarks use](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/benches/criterion/compress.rs#L35). The table splits the count by part.

<!-- worked:sizes -->

| Part | Points | Scalars |
| --- | --- | --- |
| Instance, commitments and values | $93$ | $19$ |
| Instance, two child headers of $4$ elements | $0$ | $8$ |
| Revdot reduction, per curve | $4$ | $9$ |
| Batch, per curve | $1$ | $11$ |
| IPA, per curve | $27$ | $1$ |
| Total, with two curves | $157$ | $69$ |

Each row matches a message of this chapter. The revdot reduction sends $4$ points, $\bar{E}_1$, $\bar{E}_2$, $\bar{\Pi}_{\text{lo}}$ and $\bar{\Pi}_{\text{hi}}$, and $9$ scalars, which are $\varepsilon_1$, $\varepsilon_2$ and the $7$ values of Section 5. The batch sends the point $\bar{F}$ and the $11$ values $h_i(u)$. The IPA sends $\bar{S}$ and one pair $L_j$, $R_j$ for each of $13$ rounds, which is $27$ points, and the final scalar $\hat{a}$.

<!-- /worked:sizes -->

The first row has no single message behind it, so we read it off the wire format field by field. Its points are the instance's commitments, one for each native and nested polynomial that the proof carries, as Section 3 described. Its scalars are the stored values, among them $c_{\text{acc}}$, $v_f$, the two values $A_{\text{acc}}(u_f)$ and $B_{\text{acc}}(u_f)$, and the blinding value of the `ab` bridge stage.

<!-- worked:size-total -->

At 32 bytes per point or scalar, with [4 bytes for the circuit index](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/registry.rs#L7-L20) and the [28-byte envelope](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/format.rs#L41), that comes to $7,264$ bytes. The [uncompressed encoding](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/wire/polynomial.rs#L1-L10) writes $8,192$ coefficients for each of $92$ polynomials, which is $24,117,248$ bytes before counting its cached points, so compression shrinks the proof by a factor of about $3,320$. Most of the compressed proof is the instance, with $93$ of its $157$ points. The IPA rounds, the only part that grows with the circuit size, take $52$ points.

<!-- /worked:size-total -->

The code's [comment on profiles](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L10-L11) says "a few kilobytes", which agrees with this count.

<!-- worked:header-extra -->

A header larger than $4$ elements adds $64$ bytes per extra element, since the proof holds the two child headers. The output header does not count, because [the verifier supplies it](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/verifier.rs#L83) as the statement.

<!-- /worked:header-extra -->

## 9. Why cheating fails

The chapters before this one each counted cheating at their own step. Here we look at what compression adds, which is the chance to hide a false claim in a value the verifier will never check directly. The first attempt starts from a false public input.

<!-- worked:cheat-target -->

Suppose the prover claims the output $11$ for the squaring circuit in place of $10$, so $k_1(Y)$ becomes $1 + 11Y$ and its target rises by $y = 35$ while its vectors stay honest. The target $K$ of the folded pair then rises by $35\mu_c\nu_c$, which at our challenges is $29$, while $\revdot{\v{A}}{\v{B}}$ stays at $28$, so the pair falls short of its new target by $29$. The prover sees $\mu_c$ and $\nu_c$ only after it commits to $\v{E}_1$, so any correction has to go in before them. It can lower the term $e_{0,1}$, whose weight is $\lambda_0 \eta_1 = \nu_c$, by some amount $\delta$. The false target adds $35\mu_c\nu_c$ to $K$ and the lowered term removes $\delta\nu_c$, so the fold balances only if $\mu_c = \delta / 35$. For $\delta = 5$ that means $\mu_c = 37$, and we confirmed the balance there on the full vectors. Over all $1,764$ nonzero pairs $(\mu_c, \nu_c)$, every nonzero $\delta$ balances exactly $42$ pairs, which is one value of $\mu_c$ out of 42.

<!-- /worked:cheat-target -->

The value $\varepsilon_1$ is a second place to try, because the verifier never sees the cross terms behind it.

<!-- worked:cheat-epsilon -->

Take the false public input above again, where $K$ exceeds $\revdot{\v{A}}{\v{B}}$ by $29$. After seeing all four fold challenges, the prover could shift $\varepsilon_1$ alone by some $\delta$ and leave $\v{E}_1$ as committed. The verifier's $K$ moves by $\delta$ as well, so $\delta = -29 = 14$ modulo 43 makes $(A, B)$ balance, with a new target $K' = \revdot{\v{A}}{\v{B}}$. The claim $(E_1, W_1, \varepsilon_1)$ is now false by $\delta$, and that shows up in the split. The required constant term is $K' + \rho(\varepsilon_1 + \delta) + \rho^2\varepsilon_2$, while the true coefficient of $X^{15}$ in $\Pi$ is $K' + \rho\,\varepsilon_1 + \rho^2\varepsilon_2$, so the two differ by $\rho\delta$, which vanishes only at $\rho = 0$. The prover fixes $\varepsilon_1$ before $\rho$ is drawn, so it cannot steer $\rho$ there. A shift that does not balance $(A, B)$ leaves both gaps open, and they cancel at no more than one $\rho$. We tried all $42$ nonzero shifts against all $43$ values of $\rho$, and each shift passes at exactly $1$ value of $\rho$.

<!-- /worked:cheat-epsilon -->

A third place is the split's constant term. The verifier computes the required value of $\Pi_{\text{lo}}(0)$ itself, from $K$, $\varepsilon_1$, $\varepsilon_2$ and $\rho$, so the prover cannot change it. What the prover can try is to commit to halves that meet the required value even though the true product does not, and hope that the split still passes.

<!-- worked:cheat-split -->

Suppose one of the three claims is false, so that the true $\Pi$'s coefficient of $X^{15}$ misses the required value by $7$. The prover commits to a $\Pi_{\text{lo}}$ whose constant term is the required value anyway, so that the opening at $0$ passes. The coefficient of $X^{15}$ in $X^{15}\Pi_{\text{lo}}(1/X) + X^{16}\Pi_{\text{hi}}(X)$ is exactly $\Pi_{\text{lo}}(0)$, so whatever else the prover does, the committed halves differ from the true product by a nonzero polynomial of degree at most $30$. The prover can choose the other coefficients of $\Pi_{\text{lo}}$ and $\Pi_{\text{hi}}$ to give that difference as many roots as possible, and we built such a pair. It passes the split at $30$ of the $42$ nonzero values of $r$. This is the toy field's small size at work, since the same count on the real parameters is $2^{14} - 2$ roots out of about $2^{254}$ values.

<!-- /worked:cheat-split -->

The other checks of the table at the end of Section 6 leave no comparable gap. The verifier recomputes the fuse challenges, the registry values and each $s_i(r, y)$ itself, and once the split passes, every remaining claim is an opening, which [chapter 8](./batched-openings.md) and [chapter 7](./inner-product-argument.md) already counted. A prover cannot slip in a stray commitment either, because every polynomial commitment the verifier reads [gets opened through the IPA](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/mod.rs#L26-L30), with the one exception that the box below describes.

::: details One commitment that is not opened
The instance carries one point that commits to no polynomial, a partial commitment to the nested challenge stage. The code [holds it in place](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/mod.rs#L30-L34) through the `bind_challenges` claims instead of an opening.
:::

The argument above is informal, and it rests on these assumptions. Nobody knows a relation among the generators on either curve, so commitments bind. The two transcripts behave as random oracles, and each challenge comes after the commitments and values it tests. A false proof about a tree also has to get past the accumulation arguments of the earlier chapters. The book reports [Lean proofs for some gadget contracts](./endoscalars.md#_14-endoscalars-in-ragu) and says that these do not cover the protocol's overall soundness, which we do not establish here either.

## 10. Rerandomization and zero knowledge

A wallet would like two things from a proof beyond soundness. The proof should hide its witness, and when it reaches someone else it should not link back to the proof that produced it. As [chapter 2 recorded](./pcd-intro.md#proof-size-and-hiding-in-ragu), neither the Ragu Book nor the code at this commit establishes either property.

The code has an operation aimed at the second, [`rerandomize`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/lib.rs#L708-L743). It fuses the input proof as the left child with a cached proof of the unit header as the right child, under an [internal step](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/step/internal/rerandomize.rs#L1-L18) whose output header uses the same wires as the left input, so it cannot change the header. The result verifies as the input did. Both the [book](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/implementation/proofs.md?plain=1#L196-L208) and the code say that unlinkability is the intention, and the [comment on that function](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/lib.rs#L717-L724) says that it is not achieved today. One of its reasons is that the fold is deterministic, which a single commitment is enough to show.

<!-- worked:rerandomize -->

Reduce the fold to one commitment and let the output be $\bar{A}_{\text{out}} = \lambda_0 \bar{A}_{\text{in}} + \lambda_1 \bar{A}_{\text{seed}}$, with the public weights $\lambda_0 = 16$ and $\lambda_1 = 22$ and the cached seeded point $\bar{A}_{\text{seed}} = (1,\,29)$. An input of $(25,\,29)$ gives the output $(24,\,30)$. Because the weights are public, an observer can run the equation backwards, $\bar{A}_{\text{in}} = \lambda_0^{-1}(\bar{A}_{\text{out}} - \lambda_1 \bar{A}_{\text{seed}})$, with $\lambda_0^{-1} = 35$. Here $\bar{A}_{\text{out}} - 22 \cdot \bar{A}_{\text{seed}} = (20,\,25)$, and $35 \cdot (20,\,25) = (25,\,29)$, which is the input. So each output names exactly one input, and anyone can compute which. Several of these points also appear in the compression run above, by the same chance as in Section 6.

<!-- /worked:rerandomize -->

The comment's other reason is more direct, because the output holds the input's commitments and stage polynomials in the clear as left-child data. It lists the remaining work as a randomizer in the fold and a way of hiding the child data.

Hiding the witness has a similar status. The stages' [random entry](./staging.md#_3-gates-that-hold-free-values) is there to prevent cancellation and not for hiding. The [IPA is unblinded](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/ipa/mod.rs#L1-L16) at this commit. The code keeps the masking polynomial $\bar{S}$ of Section 6 for the folded coefficients, but without Pedersen blinding it does not make the opening hiding, and the code does not claim that it does. The code also says that [a compressed proof is not hiding](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/mod.rs#L45-L46), because its openings are evaluations of the witness polynomials. The toy stage below shows what one evaluation can tell an observer.

<!-- worked:leak -->

Take the stage $a(X)$ from [chapter 17](./staging.md), where $v = x^2$ and one random entry sits at $a_0$. Among all $1,849$ pairs $(x, a_0)$, the commitment $(22,\,24)$ matches $43$. Adding one value at a point, $a(17) = 3$, leaves $2$ pairs, the true $(3, 10)$ and also $(24, 42)$. On the toy curve we can find each generator's discrete log by search, so the commitment becomes one linear equation in $a_0$, $x$ and $v = x^2$ with known coefficients. The value $a(17) = 3$ gives a second linear equation in the same unknowns, and eliminating $a_0$ leaves a quadratic equation in $x$ with these two roots. On a real curve nobody can list the commitment's matches, but the value still gives one linear equation in the secret wires, which is the sense in which the proof does not hide them.

<!-- /worked:leak -->

This small case shows the effect of one value on one stage. A compressed proof opens combinations of polynomials at points the transcript chooses, so the leak there has a different shape, and we have not analyzed how much it reveals in practice. An uncompressed proof holds the polynomials themselves. The [Tachyon book's description of stamps](https://github.com/tachyon-zcash/tachyon/blob/7e502548db33845dbaacdc0efe905d1a3c45e626/book/src/bundle.md?plain=1#L35-L39) assumes zero knowledge, so this is an open requirement for Tachyon and not a settled property, as chapter 2 noted.

## 11. Performance against Orchard

The sizes above give a first comparison, which we can make from public formulas:

<!-- worked:orchard-size -->

[ZIP 225](https://zips.z.cash/zip-0225) gives an Orchard proof $2720 + 2272 \cdot n$ bytes for $n$ actions, which is $7,264$ bytes at $n = 2$ and $25,440$ bytes at $n = 10$. So by our count a compressed Ragu proof with headers of $4$ elements is about the size of an Orchard proof for two actions, and one Ragu proof can stand for many transactions. The exact match at $n = 2$ is a coincidence of these parameters.

<!-- /worked:orchard-size -->

For verification time, the [book's analysis chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md) gives a rough model, and it states that the figures need checking against benchmarks. It puts Orchard's [batch verification](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md?plain=1#L21-L25) at about 10 to 15 ms per proof on one thread, scaling as roughly $N_{\text{tx}} / \log N_{\text{tx}}$. The book's model has a parameter that it calls the recursion threshold, which we write $K_{\text{rec}}$ to keep it apart from the target $K$ of Section 4. A circuit has at most $2^{K_{\text{rec}}}$ gates, which the book writes $N$ and which we write $n$ as in [chapter 4](./arithmetization.md#_8-arranging-the-witness), to keep it apart from the $N$ of Section 6. With four wires per gate, a trace has $4n$ coefficients. The book [estimates](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md?plain=1#L36-L49) a Ragu proof at about 100 ms for its preferred $K_{\text{rec}} = 11$, driven mainly by an MSM over $4n = 2^{13}$ points. Batch-verifying $N_{\text{tx}}$ Orchard proofs costs about $N_{\text{tx}} \cdot c / \log N_{\text{tx}}$, where $c$ is the cost per proof, and verifying one Ragu proof costs about 100 ms. The crossover is where these two costs are equal.

$$\frac{N_{\text{tx}} \times c}{\log N_{\text{tx}}} \approx 100\text{ ms}.$$

The book reports [about 50 transactions](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md?plain=1#L66) with $c = 10$ ms, and it does not state the base of the logarithm. We solved the equation at both ends of its range and for the two natural bases:

<!-- worked:break-even -->

| Cost per proof in the model | $\log = \ln$ | $\log = \log_2$ |
| --- | --- | --- |
| $10$ ms | $N_{\text{tx}} \approx 36$ | $N_{\text{tx}} \approx 59$ |
| $15$ ms | $N_{\text{tx}} \approx 20$ | $N_{\text{tx}} \approx 34$ |

<!-- /worked:break-even -->

The book's figure sits inside the range the model allows, and the range is wide, as one would expect of a rough estimate. The shape of the two costs is the more reliable conclusion. Batch verification of independent proofs keeps growing with the number of transactions, and verifying one aggregated proof does not.

The parameter $K_{\text{rec}}$ gives a [trade-off](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md?plain=1#L78-L87) that the book leaves open. A larger circuit limit raises the verifier's cost for every proof and allows a shallower tree, and a smaller limit does the reverse.

::: warning The analysis chapter and the code
**Book:** the [analysis chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md?plain=1#L36-L44) attributes the factor of 4 in its $4N$, our $4n$, to "the circuit structure across multiple stages", and it describes one MSM of $2^{13}$ points as the main cost.

**Code at `3219e08`:** the [number of coefficients is $4n$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/polynomials/mod.rs#L29-L37), and [chapter 4](./arithmetization.md#_8-arranging-the-witness) derives that factor from the four wires of each gate, independent of stages. A compressed verifier runs [the checks on each curve](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/verifier.rs#L98-L174), with one MSM per curve and the registry evaluations of Section 7. We read this as more work than the book's single MSM counts, which would raise the crossover, but we did not measure it.

The site follows the code for the structure and quotes the book for the estimates. The code has [benchmarks](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/benches/criterion/compress.rs#L1-L8) for compression and compressed verification, and we did not run them, so we report no timings of our own. The [book lists further analysis](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/analysis.md?plain=1#L89-L97) as future work.
:::

These figures describe verification only. They leave out the prover's costs, which the sources do not quantify, and they compare with Orchard as it runs today, whereas Tachyon [changes what a transaction carries](./scaling-zcash.md). Tachyon has not activated on mainnet, its design is still changing, and it [pins Ragu at `0725b52`](https://github.com/tachyon-zcash/tachyon/blob/7e502548db33845dbaacdc0efe905d1a3c45e626/crates/tachyon/Cargo.toml#L74-L76), a different revision from the `3219e08` this chapter reads.

## 12. Fusing after compression

One part of this design is still moving, and later chapters depend on it. The Ragu Book calls a compressed proof [terminal](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/concepts/pcd.md?plain=1#L126-L127), meaning that it can be verified but not fused further, while the code's [profile comments](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L10-L15) foresee an `Aggregator` profile that verifies a compressed proof in circuit, with an internal [`Decompress` step](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/step/internal/decompress.rs#L1-L5) that outputs its header. The code [says this has not landed](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L720-L736), and [a test pins](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/profile.rs#L2382-L2384) the aggregator's shape to the standard one until it does. Such a circuit would have to run the verifier of Section 7 with gates, which is why the design places it in extra circuits that only aggregators carry. The [chapter on aggregation](./aggregation-and-bundles.md) returns to this.

## 13. Where this chapter leaves us

This chapter took the following steps:

1. The proof at the root still owes the decider's checks, and the decider needs every polynomial. Compression replaces the polynomials with commitments and a few values, and restates those checks over them.
2. The verifier replays the last fuse's transcript over the eight bridge commitments in the instance, so the prover cannot choose $x_f$, $y_f$, $z_f$ or $u_f$, and it recomputes the challenge stage and the `ab` bridge stage from public data.
3. A wire binding turns the decider's comparison of stage wires with registry values into a revdot claim that a verifier can check from commitments.
4. Three reductions run on each curve: a fold and a split take the revdot claims to openings, a batch takes the openings to one claim, and an IPA proves that claim.
5. The compressed verifier pays the deferred linear costs once, as registry evaluations and one MSM per curve, and those costs do not depend on the depth of the tree.
6. Each place where a false claim could hide, whether a target, an error term or the split's constant, is fixed before the challenge that tests it.

<!-- worked:recap-size -->

7. By our count a compressed proof takes $7,264$ bytes, against more than $24,117,248$ uncompressed. Rerandomization and hiding are not yet established, and the comparison with Orchard remains an estimate.

<!-- /worked:recap-size -->

With compression, Ragu is complete as a succinct proof system. Section 9 gave the informal reasons why cheating fails and the assumptions they rest on, and no source yet establishes soundness of the whole protocol. Hiding, unlinkability and further aggregation of a compressed proof remain open, as Sections 10 and 12 found. A tree of fuses proves many steps at once, and one short proof carries the result to any verifier. The next part turns to what Tachyon proves with it, starting with [notes, nullifiers, and tachygrams](./notes-and-nullifiers.md).
