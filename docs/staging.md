# Staging

Up to now a circuit's trace has been one polynomial $r(X)$, committed all at once. The [curve cycles chapter](./curve-cycles.md#_8-deferred-operations) already had to break that habit, because a nested commitment only works if it covers part of a trace that some other circuit runs on. That chapter showed the idea on a short vector and promised the full mechanism here.

We split a trace into pieces that are committed separately, find out what can go wrong when the pieces are added back together, and build the check that prevents it. Then we use the pieces for the two jobs Ragu needs them for, which are sharing data between circuits and committing to data before a challenge. The chapter closes with a difference that chapter 13 left open, because the book adds the commitments of the pieces and we found no such addition in the code.

::: warning Reconstructed from code at commit 3219e08, not confirmed by the authors
The trace layout, the masks and their closed form below follow the code. The small circuits are our own, because the toy curves have too few points to serve as generators for one of Ragu's real circuits. The script behind this page runs each of them with the real gate and wiring equations.
:::

::: tip Terminology
The book's [staging chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/extensions/staging.md?plain=1#L21-L34) calls the pieces **stage polynomials**, or partial traces, and calls the remainder the **final trace** $r'(X)$. The [code's module documentation](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/mod.rs#L34-L44) says staging polynomials and writes the remainder as $f(X)$, while [`builder.rs`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/builder.rs#L8-L10) in the same directory writes $r'(X)$. This site says stage polynomial and $r'(X)$, because $f$ already means the combined quotient of [chapter 08](./batched-openings.md). We say primary and secondary for the two circuits of a cycle until Section 15, which uses the code's native and nested, [as chapter 13 explained](./curve-cycles.md#_12-cycles-in-ragu).
:::

## 1. Two jobs for a partial commitment

Two situations in a recursive step call for committing to only part of a trace.

The first is a challenge in the middle of a circuit. Suppose a circuit holds many wires and would like to check something about them with a [random linear combination](./statements-and-challenges.md#_7-random-linear-combinations). The challenge must depend on those wires, or the prover could pick the wires to suit the challenge. So the circuit has to hash them, and hashing inside a circuit is expensive. A commitment offers a cheaper route, since it binds all the wires under the same assumption as any Pedersen commitment and takes only two coordinates to hash:

<!-- worked:hash-cost -->

The toy sponge from [chapter 03](./statements-and-challenges.md#a-toy-poseidon) has rate 2, and one permutation applies $8 \cdot 3 + 8 = 32$ S-boxes of $3$ multiplications each, or $96$ gates before counting anything else. Hashing $8$ wires takes $4$ permutations and $384$ gates. Hashing the two coordinates of a commitment to those same $8$ wires takes $1$ permutation and $96$ gates, and that cost stays the same however many wires the commitment covers.

<!-- /worked:hash-cost -->

The same trade appears in Ragu itself. The first transcript circuit [absorbs three bridge commitments with three permutations](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_1.rs#L5-L17), and the stages behind those commitments hold many more wires than the two coordinates of each point:

<!-- worked:code-preamble -->

The native preamble stage reserves [$2(3h + 1 + 37)$ values](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/preamble.rs#L358-L362) for a header of $h$ elements, which is at least $76$ even for an empty header.

<!-- /worked:code-preamble -->

The second situation is data that several circuits have to read. The [recursive proofs chapter](./recursive-proofs.md#_12-recursion-in-ragu) noted that Ragu divides its verifier into many small circuits, and these circuits work on the same child proofs. Passing the shared data through public inputs would make every shared wire a term of $k(Y)$ that a verifier has to evaluate, and it would also publish any wire that is meant to stay secret. It would be better for each circuit to read the data as if it were part of its own witness.

Both jobs need the same thing, which is a commitment to some of the wires of a trace, made before the rest of the trace exists.

## 2. Splitting a trace

Commitments add, so a trace can be divided into parts that each get their own commitment. We write

$$r(X) = a(X) + r'(X),$$

where $a(X)$ is a stage polynomial and $r'(X)$ is the final trace. With a second stage this becomes $r(X) = a(X) + b(X) + r'(X)$, and so on. The prover commits to $a(X)$ and $r'(X)$ and does not need to commit to their sum, because the commitment to a sum is the sum of the commitments.

We need a small circuit to work with. Keep the secret $x = 3$ from the [arithmetization chapter](./arithmetization.md), and start with the statement $x^2 + 1 = 10$, which takes one multiplication. The trace uses the layout from [Section 8 of that chapter](./arithmetization.md#_8-arranging-the-witness), including the system gate at index 0 that [chapter 09](./nark.md#_14-the-constant-wire) introduced. We take $n = 4$ gates, and we reserve gate 1 for the stage. The stage holds $x$, and it also holds $v = x^2$, which the next circuits will use.

<!-- worked:gens -->

A vector of $4n = 16$ entries needs 16 generators. We use the twelve from [chapter 09](./nark.md#_14-the-constant-wire), followed by $(7,\,6), (8,\,9), (16,\,10), (18,\,10)$. This chapter never uses the blinding generator $H$, for a reason Section 3 gives.

<!-- /worked:gens -->

Here are the two parts and their sum:

<!-- worked:split -->

| Polynomial | Coefficients of $X^0, \ldots, X^{15}$ | Commitment |
| --- | --- | --- |
| Stage $a(X)$ | $(0, 0, 0, 0, 0, 0, 3, 10, 0, 0, 0, 0, 0, 0, 9, 0)$ | $\bar{A} = (22,\,24)$ |
| Final trace $r'(X)$ | $(0, 0, 9, 0, 0, 3, 0, 25, 0, 0, 3, 0, 0, 0, 0, 1)$ | $\bar{R}' = (24,\,30)$ |
| Sum $r(X)$ | $(0, 0, 9, 0, 0, 3, 3, 35, 0, 0, 3, 0, 0, 0, 9, 1)$ | $\bar{R} = (25,\,29)$ |

<!-- /worked:split -->

Read gate by gate, with the stage's entry first and the final trace's entry second in each cell, the same numbers show which part supplies each wire:

<!-- worked:gate-table -->

| Gate $i$ | Reserved for | $a_i$ | $b_i$ | $c_i$ | $d_i$ |
| --- | --- | --- | --- | --- | --- |
| 0 | System gate | 10 + 25 | 0 + 0 | 0 + 0 | 0 + 1 |
| 1 | Stage | 3 + 0 | 0 + 0 | 0 + 0 | 9 + 0 |
| 2 | Final trace | 0 + 3 | 0 + 3 | 0 + 9 | 0 + 0 |
| 3 | Final trace (unused) | 0 + 0 | 0 + 0 | 0 + 0 | 0 + 0 |

<!-- /worked:gate-table -->

Gate 2 is the multiplication $x \cdot x = v$. Its copies of $x$ come from the wiring, with rows $a_2 - a_1 = 0$ and $b_2 - a_1 = 0$, so the circuit's constraints reach across into the wires of the stage. That reach is the purpose of the arrangement, since the final trace never has to hold $x$ in the reserved slot.

## 3. Gates that hold free values

The consolidated equation from the [arithmetization chapter](./arithmetization.md#_12-the-consolidated-equation) applies to the sum $r(X)$, and it includes a gate check for every gate. A stage's gate has to pass that check for whatever values the stage holds, because the stage is committed before anything else is known about the circuit.

The [wire allocator](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_primitives/src/allocator.rs#L107-L116) achieves this by writing each value to the $a$ wire of a new gate with $b_i = c_i = 0$, and it writes the next value to that gate's spare $d$ wire. So the gate has the form $(a_i, 0, 0, d_i)$, which is why a [stage carries two values per gate](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/layout.rs#L136-L149). The two gate equations from [chapter 04](./arithmetization.md#_13-the-arithmetization-in-ragu) then read $a_i \cdot 0 = 0$ and $0 \cdot d_i = 0$, and they hold for any values:

<!-- worked:free-gate -->

We tried all $1,849$ pairs of values for $(a_1, d_1)$, with $b_1 = c_1 = 0$. Every pair satisfies both equations of gate 1.

<!-- /worked:free-gate -->

So a stage's gates do no checking of their own. They are storage, and any meaning the values have comes from constraints in the circuits that read them.

The system gate needs separate care. A real circuit has $d_0 = 1$, but a stage [has no such wire](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/mod.rs#L385-L394), so a stage that held only zeros would commit to the identity point, and a stage with predictable entries could cancel in a combination of commitments. The prover therefore places a random value $\alpha$ at $a_0$ of each stage, which is the first number in the $a_i$ column of gate 0 above. This entry takes the place of $H$ in this chapter. It is not there for hiding, as [chapter 09](./nark.md#_13-hiding-commitments-and-what-the-proof-reveals) recorded. The final trace has its own $a_0$ and supplies $d_0 = 1$. Gate 0 passes because its $b_0$ and $c_0$ are zero.

With those two points settled, the consolidated equation applies to the sum as it does to any trace:

<!-- worked:sum-holds -->

The right vector at $z = 5$ and $y = 7$ gives $\langle\!\langle \v{r}, \v{r} \circ \v{z^{16}} + \v{t} + \v{s} \rangle\!\rangle = 28$, and $k(7) = 1 + 10 \cdot 7 = 28$. The two sides agree at all $1,849$ pairs $(z, y)$. The final trace alone fails at $1,763$ of those pairs, which shows that the circuit reads its input from the stage polynomial, not from $r'(X)$.

<!-- /worked:sum-holds -->

## 4. Overlapping the stage

The split has a weakness. Adding polynomials adds their coefficients in every position, so nothing so far stops the final trace from putting a value in a slot reserved for the stage. To see what that buys a cheater, consider three equations:

<!-- worked:roots -->

Over $\F_{43}$, the equation $x^3 + x + 5 = 35$ has the single solution $3$. The equation $x^2 + 1 = 10$ has the solutions $3, 40$, and they share $x = 3$. The equation $x^2 + 1 = 17$ has the solutions $4, 39$, neither of which solves the first equation.

<!-- /worked:roots -->

Suppose a stage holds $x = 3$, which the cubing statement of [chapter 04](./arithmetization.md) needs, and a cheater wants to claim $x^2 + 1 = 17$ about that same stage. No single $x$ makes both true, but a stray entry can change what the second circuit reads:

<!-- worked:overlap -->

Let the prover leave $\bar{A} = (22,\,24)$ alone, so the stage still says $x = 3$, and put $1$ in slot $a_1$ of the final trace, whose gate 2 now holds $4 \cdot 4 = 16$. The sum then holds $a_1 = 4$, and the circuit for $x^2 + 1 = 17$ accepts it at all $1,849$ challenge pairs, while the commitments still add up: $\bar{A} + (27,\,1) = (23,\,24)$. The commitment says one input and the circuit ran on another.

<!-- /worked:overlap -->

Chapter 13 [saw the same effect](./curve-cycles.md#_8-deferred-operations) on a shorter vector. A commitment check cannot find the problem, because a commitment to a sum equals the sum of the commitments however the entries overlap. We need a check that looks at where a polynomial's nonzero entries sit.

## 5. The stage mask

The requirement is linear in the polynomial's entries. A stage must be zero at every wire of every gate outside its reserved range, apart from the system gate. Let $F$ be that set of forbidden positions. Requiring many values to be zero is the task that a random combination handles, so we could ask for

$$\sum_{p \in F} a_p\, y^{4n-1-p} = 0$$

at a random $y$. If all the forbidden entries are zero, this holds for every $y$. If any of them is nonzero, the left side is a nonzero polynomial in $y$ of degree at most $4n - 1$, which has few roots.

This combination can be written as a revdot product, and that matters because revdot products are the claims that [Ragu's accumulators fold](./revdot-folding.md). The revdot product pairs position $p$ with position $4n - 1 - p$, so we define a public vector $\v{s}$ with

$$s_k = \begin{cases} y^k & \text{if } 4n - 1 - k \in F, \\ 0 & \text{otherwise.} \end{cases}$$

Then

$$\revdot{\v{a}}{\v{s}} = \sum_{p=0}^{4n-1} a_p\, s_{4n-1-p} = \sum_{p \in F} a_p\, y^{4n-1-p},$$

which is the combination we wanted. This $\v{s}$ is called the **stage mask**.

The mask is an ordinary wiring polynomial, for a circuit with an unusual shape. Take one constraint per forbidden wire, saying that the wire is zero. [Section 11 of chapter 04](./arithmetization.md#_11-encoding-the-constraints) places each coefficient at the wire's partner position and weights row $j$ by $y^j$. The [code's test version of this circuit](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/mask.rs#L306-L311) numbers the rows so that row $k$ is the constraint whose partner position is $k$. The result is

$$s(X, Y) = \sum_{k \,:\, 4n-1-k \in F} X^k Y^k.$$

Notice what is missing compared with the consolidated equation. A stage polynomial does not satisfy gates or the circuit's constraints on its own, so the claim has no dilation and no $\v{t}$, and it has no public inputs, so its target is 0. The full claim is $\revdot{\v{a}}{\v{s}} = 0$, in place of $\revdot{\v{r}}{\v{r} \circ \v{z^{4n}} + \v{t} + \v{s}} = k(y)$.

For stage $a(X)$, which reserves gate 1, the forbidden wires are those of gates 2 and 3:

<!-- worked:mask-degrees -->

| Gate | Wire | Position $p$ in the trace | Degree $4n - 1 - p$ in the mask |
| --- | --- | --- | --- |
| 2 | $a_2$ | 5 | 10 |
| 2 | $b_2$ | 10 | 5 |
| 2 | $c_2$ | 2 | 13 |
| 2 | $d_2$ | 13 | 2 |
| 3 | $a_3$ | 4 | 11 |
| 3 | $b_3$ | 11 | 4 |
| 3 | $c_3$ | 3 | 12 |
| 3 | $d_3$ | 12 | 3 |

<!-- /worked:mask-degrees -->

<!-- worked:mask-run -->

At $y = 7$ the mask for stage $a(X)$ has coefficients $(0, 0, 6, 42, 36, 37, 0, 0, 0, 0, 36, 37, 1, 7, 0, 0)$. The stage has nonzero entries only at positions 6, 7 and 14, whose partners are 9, 8 and 1, and those are the positions where the mask has zeros. So the product is $0$. The result is 0 at all 43 values of $y$.

<!-- /worked:mask-run -->

The final trace has its own mask, which forbids gate 1. Section 7 gives the details, but we can already apply it to the attack of the previous section:

<!-- worked:mask-catch -->

The final trace from Section 4 has the stray entry at position 6, the partner of degree 9. Its product with the final mask is therefore $1 \cdot y^9$, which equals $42$ at $y = 7$. It is zero only at $y = 0$, so 42 of the 43 values of $y$ catch it.

<!-- /worked:mask-catch -->

<!-- worked:mask-best -->

The cheater has more freedom than this, because the other three wires of gate 1 are also forbidden entries, and it can fill them in the hope of building roots. The product becomes $y^9 + e\,y + f\,y^6 + g\,y^{14}$, where $e$, $f$ and $g$ are the entries it adds to $d_1$, $b_1$ and $c_1$. Trying all $79,507$ choices, the best one has $5$ nonzero roots, out of the 42 nonzero values of $y$. Only $85$ of the choices also leave gate 1 satisfied, as the circuit needs, and the best of those has $4$ nonzero roots, at $(e, f, g) = (34, 7, 28)$.

<!-- /worked:mask-best -->

<!-- worked:mask-bound -->

For $n = 4$ the mask has degree at most $4n - 1 = 15$ in $y$, so the bound is $15/43 \approx 0.349$ and the best rate we found is $5/43 \approx 0.116$, counting $y = 0$. On a field of about $2^{254}$ elements with $4n = 2^{13}$, the same bound falls below $2^{-240}$.

<!-- /worked:mask-bound -->

::: warning The book's description of the mask
**Book:** the [staging chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/extensions/staging.md?plain=1#L44-L47) first says that wires outside the reserved range should be zero, and then says the mask enforces that everything must be nonzero inside the range.

**Code at `3219e08`:** the [mask forces wires to zero outside the range](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/mask.rs#L96-L102) and says nothing about wires inside it.

This site follows the code, and it reads "nonzero" in the book as a slip for "zero outside".
:::

## 6. A closed form for the mask

The verifier's two linear costs from [chapter 09](./nark.md#_17-a-short-proof-from-the-same-parts) included evaluating the wiring polynomial $s(x, y)$, since an arbitrary circuit has no structure to exploit. A mask does have structure, because it depends only on the product $t = XY$, and that makes it far cheaper. We derive the form the [code uses](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/mask.rs#L184-L209).

Start from all $4n$ degrees and remove the ones that are not forbidden. Let the stage reserve the $m$ gates starting at gate $g$. The partner degrees of the wires of gate $j$ are $j$ for $d_j$, $2n - 1 - j$ for $b_j$, $2n + j$ for $a_j$, and $4n - 1 - j$ for $c_j$.

For the system gate, $j = 0$ gives the degrees $0$, $2n - 1$, $2n$ and $4n - 1$, whose powers of $t$ sum to

$$1 + t^{2n-1} + t^{2n} + t^{4n-1} = (1 + t^{2n})(1 + t^{2n-1}).$$

For the reserved gates, group the $d$ and $a$ wires, and then the $b$ and $c$ wires:

$$\sum_{j=g}^{g+m-1} \big(t^{j} + t^{2n+j}\big) = (1 + t^{2n})\, t^{g} \sum_{i=0}^{m-1} t^i,$$

$$\sum_{j=g}^{g+m-1} \big(t^{2n-1-j} + t^{4n-1-j}\big) = (1 + t^{2n})\, t^{2n-g-m} \sum_{i=0}^{m-1} t^i,$$

where the second line substitutes $i = g + m - 1 - j$. Subtracting both groups from the full sum gives

$$s(x, y) = \sum_{i=0}^{4n-1} t^i \;-\; (1 + t^{2n})(1 + t^{2n-1}) \;-\; (1 + t^{2n})\big(t^{g} + t^{2n-g-m}\big) \sum_{i=0}^{m-1} t^i.$$

The first two terms do not depend on the stage, and the code calls them the [global mask](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/mask.rs#L9-L40). The last term is the **notch** for this stage. Each geometric sum has a closed form that takes $O(\log n)$ multiplications, as in [chapter 09](./nark.md#_16-what-the-verifier-pays).

<!-- worked:closed-run -->

Take $x = 9$ and $y = 7$, so $t = xy = 20$, and the mask of stage $a(X)$, for which $g = 1$ and $m = 1$. The global term is $18$ and the notch is $25$, so the formula gives $36$. Adding $t^k$ over the eight forbidden degrees gives the same value. We checked the formula against the direct sum for every mask of this chapter at all 42 nonzero values of $t$.

<!-- /worked:closed-run -->

<!-- worked:closed-size -->

For a circuit with $n = 2^{11}$ gates and a stage of $100$ gates, the mask has $4(n - 1 - m) = 7,788$ nonzero coefficients. The closed form needs only a few powers of $t$ and two geometric sums.

<!-- /worked:closed-size -->

The registry computes the shared global term [once](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/registry.rs#L768-L775), and each mask contributes only its notch. The chapter on [wiring and the registry](./wiring-and-registry.md) covers the registry itself.

## 7. A mask for every polynomial

Masks have to cover the final trace as well, because Section 4's attack put the stray entry there. The final trace has the same kind of mask, with the reserved range running from the end of the last stage to the top of the trace. In the code this is [`final_mask`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/mod.rs#L469-L480), and it uses the [same type](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/mask.rs#L120-L142) as a stage's mask with a larger count.

Stages also stack. A stage names its parent, and it [starts where the parent ends](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/mod.rs#L224-L230), with a stage of $k$ values taking $\lceil k/2 \rceil$ gates. Section 12 adds a second stage $b(X)$ at gate 2, and with it our small circuits need these four masks:

<!-- worked:mask-table -->

| Polynomial | $g$ | $m$ | Gates it may use | Gates it must leave zero |
| --- | --- | --- | --- | --- |
| $a(X)$ | 1 | 1 | 1 | 2, 3 |
| $b(X)$ | 2 | 1 | 2 | 1, 3 |
| Final trace after $a(X)$ | 2 | 2 | 2, 3 | 1 |
| Final trace after $b(X)$ | 3 | 1 | 3 | 1, 2 |

<!-- /worked:mask-table -->

![Four rows and four columns. Stage a uses gate 1, stage b uses gate 2, the final trace after a uses gates 2 and 3, the final trace after b uses gate 3. Gate 0 holds blinding in every row, and all other cells are zero.](./manim/staging-slots.png)

The system gate column is outside every mask, which is why each polynomial can have its own $a_0$. The stage values fill only reserved gates, and [the builder](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/builder.rs#L238-L249) writes zeros in those slots of the final trace, so that the sum places each value in one spot.

A mask covers all four wires of its reserved gates, so a stage could in principle put values in its $b_i$ and $c_i$. That gains nothing, because the gate equations on the sum still apply to that gate, and circuits read stage data only from the $a$ and $d$ wires.

## 8. Sharing one mask claim

A recursive step has two children, so it inherits the same stage twice, once from each. Each stage needs its mask claim checked. These claims can be combined, because the mask claim is linear in the polynomial:

$$\revdot{z\,\v{a}_L + \v{a}_R}{\v{s}} = z\,\revdot{\v{a}_L}{\v{s}} + \revdot{\v{a}_R}{\v{s}} = 0.$$

The target stays 0, because mask claims [have no public inputs](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/extensions/staging.md?plain=1#L62-L68) that would need combining too.

<!-- worked:fold-run -->

Take the stage above as the left child's, and a right child's stage holding $(x, v) = (5, 25)$ with $a_0 = 8$. At $z = 5$ the fold $z \cdot a_L(X) + a_R(X)$ has coefficients $(0, 0, 0, 0, 0, 0, 20, 15, 0, 0, 0, 0, 0, 0, 27, 0)$, and its product with the mask is 0, as it is at all $1,849$ pairs $(z, y)$. One claim did the work of two.

<!-- /worked:fold-run -->

The folded claim still catches a bad stage:

<!-- worked:fold-catch -->

Put a stray $11$ in gate 3 of the right stage. Among all $1,849$ pairs $(z, y)$, the folded claim passes at $43$, which are the 43 pairs with $y = 0$. Two stray entries at one position, one per child, can cancel each other at a single $z$, since $z\,\delta_L + \delta_R$ is a degree-1 polynomial in $z$. Over all $1,764$ pairs of nonzero entries, no pair cancels at more than $1$ value of $z$.

<!-- /worked:fold-catch -->

The same step does not work for a circuit's own claim, because $\v{r}$ appears twice in that equation. Substituting $\v{r} = \rho\,\v{r}_1 + \v{r}_2$ into the quadratic part gives

$$\revdot{\v{r}}{\v{r} \circ \v{z^{4n}}} = \rho^2 \revdot{\v{r}_1}{\v{r}_1 \circ \v{z^{4n}}} + \rho \Big( \revdot{\v{r}_1}{\v{r}_2 \circ \v{z^{4n}}} + \revdot{\v{r}_2}{\v{r}_1 \circ \v{z^{4n}}} \Big) + \revdot{\v{r}_2}{\v{r}_2 \circ \v{z^{4n}}},$$

and the middle term has nothing to match it on the target side:

<!-- worked:fold-quadratic -->

Fold two honest traces of the squaring circuit, with $x = 3$ and with $x = 5$, in the same way at $\rho = 2$, $z = 5$ and $y = 7$. The two claims are both true, but the folded product is $30$ while the folded target is $24$. The terms with $\rho^2$ and $\rho$ do not match the target, and the two sides agree at only $2$ of the 43 values of $\rho$.

<!-- /worked:fold-quadratic -->

Circuit claims therefore go through the error terms of the [revdot folding chapter](./revdot-folding.md), and each one stays a separate entry going into that fold. Mask claims skip that cost, which the code's documentation [lists as a property of gate-free claims](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/lib.rs#L314-L320).

The code also folds across circuits. Any polynomials with the same reserved range can share a mask, so the final traces of all the circuits that end on the same last stage fold into one claim. Section 15 shows this.

::: warning The order of the weights
**Book:** the [combined claim](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/extensions/staging.md?plain=1#L62-L64) is $\v{a} + z\,\v{b}$.

**Code at `3219e08`:** the [fold](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/claims.rs#L133-L150) gives entry $i$ of $n$ the weight $z^{n-1-i}$, so the first polynomial takes the highest power, as [its module documentation](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/mod.rs#L82-L97) also shows.

This site follows the code. The two orders are equally sound.
:::

## 9. Two circuits on one stage

We can now do the second job from Section 1. Two circuits read the same stage by having the same polynomial $a(X)$ inside their traces. The cubing circuit is the [statement of chapter 04](./arithmetization.md), with $x$ and $v$ read from the stage, and with one gate checking $x \cdot x = v$ and another computing $v \cdot x$. Each circuit has its own final trace and its own wiring.

<!-- worked:two-circuits -->

| Circuit | Statement | Trace | Commitment to its final trace | Consolidated equation |
| --- | --- | --- | --- | --- |
| Squaring | $x^2 + 1 = 10$ | $a(X) + r'_1(X)$ | $(24,\,30)$ | Holds at all $1,849$ pairs |
| Cubing | $x^3 + x + 5 = 35$ | $a(X) + r'_2(X)$ | $(24,\,1)$ | Holds at all $1,849$ pairs |

<!-- /worked:two-circuits -->

The verifier holds three commitments and not four, because $\bar{A}$ appears once and serves both traces. Neither statement mentions $x$ in its public inputs, and yet the shared commitment ties the two statements to one value. The difference shows when a prover tries the false pair of claims from Section 4:

<!-- worked:two-statements -->

With separate traces, the prover can use $x = 3$ for the cubing circuit and $x = 4$ for the circuit of $x^2 + 1 = 17$, and each trace passes its own consolidated equation at every challenge pair. The verifier has no way to see that the inputs differ. With one shared stage the prover has to pick one $x$, and the lists above show that no single value satisfies both equations.

<!-- /worked:two-statements -->

Section 4's overlap was the only way around this, and the final mask closes it.

A circuit does not have to read every stage below its own. The builder can [skip a stage](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/builder.rs#L279-L289), which keeps the layout the same but leaves those wires out of the circuit's constraints. The polynomial then does not join the circuit's sum at all.

## 10. Linking stages with a bonding polynomial

Sometimes the same value sits in two different stages, and the two copies need a check. In Section 12, stage $b(X)$ carries a copy of $v$ that a circuit reads, and something has to tie it to the $v$ in stage $a(X)$. A circuit with one gate could do this, but the requirement is only a linear equation between wires, so it needs no gates at all.

The code provides for this case. A **bonding polynomial** is the wiring polynomial of a [circuit that has only constraints](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/lib.rs#L305-L327), with no gates and an empty instance, and its claim has the same shape as a mask claim. A stage mask is the special case whose constraints each say that one wire is zero. The general case can [compare stage wires](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/bonding.rs#L1-L14) with each other, and it is applied to the sum of the stages involved:

$$\revdot{\v{a} + \v{b}}{\v{s}} = 0.$$

Such a polynomial is [not allowed to reference the constant wire](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/bonding.rs#L39-L51), so $s(X, 0) = 0$. That is why the row numbering below starts at 1.

<!-- worked:bond-run -->

The two stages hold $v = 9$ in $d_1$ and $d_2$. The only row of the polynomial is $d_1 - d_2 = 0$, placed at $Y^1$, because the $Y^0$ position is empty in a polynomial of this kind. Then $\langle\!\langle \v{a} + \v{b}, \v{s} \rangle\!\rangle = y\,(d_1 - d_2)$, which is 0 at all 43 values of $y$. If stage $b(X)$ holds $20$ in $d_2$, the product at $y = 7$ is $9$, and only $y = 0$ hides the difference.

<!-- /worked:bond-run -->

Apart from the masks, Ragu's one such polynomial comes from the nested [loading circuit](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/circuits/loading.rs#L126-L150), which requires each point used by the nested walk to equal the same point in the bridge stage that brought it in. Because the claim is linear, a [grouped fold](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/claims.rs#L249-L262) sums the stages within each child and combines the two children with $z$.

## 11. What a mask does not check

A mask looks only at where entries sit, and it ignores their values. A stage whose wires are supposed to form a curve point or a bit passes its mask for any value:

<!-- worked:content -->

A stage over $\F_{31}$ that is supposed to hold a point of $E$ passes its mask for all $961$ pairs of coordinates, and only $42$ of those pairs lie on $E$.

<!-- /worked:content -->

Constraints written while a stage is being built do not help, because the framework [discards them](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/implementation/staging.md?plain=1#L66-L75). So some circuit that reads the stage has to state those constraints as its own. The code gives each reader a choice. Loading a stage [`enforced`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/builder.rs#L137-L162) emits the checks in that circuit, and loading it `unenforced` relies on some other circuit to do so. Since the circuits read the same stage polynomial, one reader's check protects them all. For example, [`compute_v` enforces the preamble](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/compute_v.rs#L159-L164) while the other circuits load it unenforced, and [`bind_endoscalar` enforces curve membership](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/points.rs#L43) for the points stages.

## 12. Stages across the cycle

Now the first job from Section 1, a challenge that depends on the stage. Chapter 13 explained the difficulty. The commitment $\bar{A}$ is a point on $E$, so its coordinates lie in $\F_{31}$, and the sponge that derives challenges has wires in $\F_{43}$. The fix was a [nested commitment](./curve-cycles.md#_7-committing-to-coordinates), and we can now say exactly what that object is. It is a commitment to a stage of the circuit over $\F_{31}$, and the book calls this a [**nested staged commitment**](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/pcs.md?plain=1#L238-L247). Its stage holds foreign coordinates as ordinary wires, so it follows every rule above, including the layout, the $\alpha$ and the mask.

<!-- worked:nested-run -->

| Step | Field | Result |
| --- | --- | --- |
| Commit to stage $a(X)$ on $E$ | $\F_{43}$ scalars | $\bar{A} = (22,\,24)$ |
| Place its coordinates in a stage of the other circuit, gate 1 | $\F_{31}$ wires | $a_1 = 22$, $d_1 = 24$, with $a_0 = 8$ |
| Commit to that stage on $E'$ | $\F_{31}$ scalars | $\mathring{A} = (21,\,25)$ |
| Absorb the coordinates of $\mathring{A}$ and squeeze | $\F_{43}$ wires | $w = 11$ |

<!-- /worked:nested-run -->

In this way the challenge $w$ depends on $x$ and $v$ through two commitments, and the sponge absorbed only two wires. The circuit over $\F_{31}$ reads the coordinates as its own witness, so it can run the [deferred group operations](./curve-cycles.md#_8-deferred-operations) on them:

<!-- worked:deferred-run -->

The circuit over $\F_{31}$ has $n = 3$ gates, so it uses the twelve generators of $E'$ from [chapter 13](./curve-cycles.md#_8-deferred-operations). Its gate 2 is the first gate of adding $\bar{A}$ to the fixed point $(11,\,1)$. Holding $\lambda = 19$, it checks $19 \cdot 20 = 8$ modulo 31, with both differences written as linear rows over the stage wires. Its consolidated equation holds at all $961$ pairs $(z, y)$, and both of its masks return 0 at all 31 values of $y$. The toy curve has too few points for the two remaining gates of the addition, so we stop there.

<!-- /worked:deferred-run -->

The mask gives input consistency across the cycle in the same way as Section 5, so a prover cannot run this circuit on other coordinates than the ones the transcript absorbed:

<!-- worked:nested-catch -->

Suppose the prover adds $7$ to slot $a_1$ in the final trace of this circuit, so that its gates run on the $x$-coordinate $29$ while $\mathring{A}$ still holds $22$. The final mask returns $4$ at $y = 5$, and only $y = 0$ hides the entry. The same holds for all 30 nonzero amounts.

<!-- /worked:nested-catch -->

Back on the $\F_{43}$ side, the challenge lets the prover commit to the next stage and finish the trace. Here we use $w$ to compress two wires of the stage into one value $e = x + w\,v$. Two wires make a small example, and the same reduction applies however many wires the stage holds:

<!-- worked:combine-run -->

With $w = 11$, the prover computes $e = x + w\,v = 3 + 11 \cdot 9 = 16$ and commits to stage $b(X)$, which holds $(e, v) = (16, 9)$ at gate 2, giving $\bar{B} = (5,\,29)$. The final trace holds one gate, $a_3 = 11$, $b_3 = 9$ and $c_3 = 13$. Rows of the wiring make $a_3$ and $a_2$ public, tie $b_3$ to $d_2$, and require $c_3 + a_1 - a_2 = 0$. The trace $a(X) + b(X) + r'(X)$ satisfies the consolidated equation at all $1,849$ pairs, with $k(Y) = 1 + 11Y + 16Y^2$.

<!-- /worked:combine-run -->

The combining circuit reads $v$ from stage $b(X)$, so it relies on the bonding polynomial of Section 10 to tie that copy to stage $a(X)$. The order of the commitments is what makes $e$ meaningful, as a target value shows:

<!-- worked:grind -->

Suppose the prover wants $e = 4$. With the stage fixed at $(x, v) = (3, 9)$, only one of the 43 values of $w$ gives that result, namely $w = 24$. If the prover could see $w = 11$ before fixing the stage, it would set $v = 4$ and reach the target for certain. Instead, every new $v$ changes $\bar{A}$, then $\mathring{A}$, then $w$. We ran that whole chain for the $42$ values of $v$ that give a usable commitment, and one of them, $v = 39$, reaches the target. A search of about 43 tries succeeds on a field of 43 elements, which is the [repeated-trials problem from chapter 03](./statements-and-challenges.md#_10-repeated-trials), and the same search has no realistic chance on a 255-bit field.

<!-- /worked:grind -->

The challenge itself reaches the secondary circuit by the route of [chapter 13](./curve-cycles.md#_9-sharing-one-set-of-challenges) and the [endoscalars chapter](./endoscalars.md). In the code, that route is one more stage, [committed with $\alpha = 0$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/stages/challenges.rs#L1-L15), so that the primary circuit can recompute its commitment from the challenges.

::: warning Encoding the inputs on each side
**Book:** the [PCS chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/pcs.md?plain=1#L194-L247) gives two mirrored encodings, $\mathring{C}_1$ for the primary circuit and $\mathring{C}_2$ for the secondary, and treats them by symmetry. It places $\mathring{C}_1$ in the preamble stage as an advice wire and the rest of the tuple on public input wires.

**Code at `3219e08`:** the design is not symmetric, because only the native side has a transcript. The [native preamble](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/_02_preamble.rs#L45-L67) and the [points stages](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/points.rs#L14-L20) play the part of the book's $C$, and their commitments go into [bridge stages](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/_02_preamble.rs#L69-L91) that play the part of $\mathring{C}_1$. We found no separate $\mathring{C}_2$ absorbed on the nested side, which [squeezes nothing](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/mod.rs#L235-L247). The roles of the wires are also reversed from the book's. The bridge commitment is a [public value in the unified instance](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_1.rs#L242-L249), and [stage outputs stay private to the prover](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/staging/mod.rs#L194-L200). The book's own [public inputs chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/public_inputs.md?plain=1#L64-L68) agrees with the code on that last point.

This site follows the code.
:::

## 13. Adding the stage commitments

Chapter 13 [recorded a difference](./curve-cycles.md#_12-cycles-in-ragu) that we can now settle. The book asks for two things about staged traces, that the parts do not overlap and that [their commitments add up](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/prelim/nested_commitment.md?plain=1#L70-L78) to the commitment to the overall trace. Sections 5 and 7 handled the first. In the book's form, the second looks like this:

<!-- worked:book-sum -->

In the circuit above, $\mathring{A} = (21,\,25)$ and the final trace commits to $\bar{R}' = (2,\,31)$. The whole trace commits to $\bar{R} = (12,\,31)$. These are points on $E'$, so the next circuit over $\F_{43}$ can add them with the $3$ gates of [chapter 13](./curve-cycles.md#_3-a-curve-for-each-field), and the sum matches.

<!-- /worked:book-sum -->

The purpose of this check is to tie the trace that the circuit's claim is about to the stage commitments that the transcript absorbed. A prover who committed to one $\bar{R}$ and to unrelated stages would fail it.

The code reaches the same goal without a separate $\bar{R}$. A proof stores a commitment per stage and none for the whole trace, so there is no second object to compare. The [circuit's claim is defined on the sum](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/claims.rs#L29-L48) of its polynomials. Here is the line that lists the parts for `compute_v`, from [`crates/ragu_pcd/src/internal/native/claims.rs`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L221-L231) at commit `3219e08`:

```rust
// compute_v: ComputeV + Preamble + Query + Eval
ComputeVCircuit => {
    for (((cv, pre), q), e) in source
        .rx(Rx(ComputeV))
        .zip(source.rx(Rx(Preamble)))
        .zip(source.rx(Rx(Query)))
        .zip(source.rx(Rx(Eval)))
    {
        processor.internal_circuit_claim(id, [cv, pre, q, e].into_iter());
    }
}
```

These claims then fold into one polynomial $A(X) = \sum_i \lambda_i\, r_i(X)$ by the method of the [revdot folding chapter](./revdot-folding.md). Two things follow. The prover can compute the commitment to $A(X)$ with [a small MSM over the stored commitments](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/_06_ab.rs#L155-L178), and the verifying circuit [recomputes the value of $A$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/compute_v.rs#L441-L459) at a random point from the values of its parts. [Each stored polynomial is opened at that point](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/compute_v.rs#L548-L553), and so is $A(X)$.

<!-- worked:code-sum-intro -->

That gives the following run for our two circuits, with $\lambda_1 = 5$, $\lambda_2 = 8$ and the opening point $xz = 2$ from $x = 9$ and $z = 5$:

<!-- /worked:code-sum-intro -->

<!-- worked:code-sum -->

| Polynomial | Commitment | Value at the opening point $2$ | Weight in $A(X)$ |
| --- | --- | --- | --- |
| $a(X)$ | $(22,\,24)$ | 19 | $\lambda_1 + \lambda_2 = 13$ |
| $r'_1(X)$ | $(24,\,30)$ | 42 | $\lambda_1 = 5$ |
| $r'_2(X)$ | $(24,\,1)$ | 21 | $\lambda_2 = 8$ |
| $A(X)$ | $(7,\,25)$ | 23 | Derived from the three rows above |

<!-- /worked:code-sum -->

<!-- worked:code-sum-text -->

The prover gets the commitment to $A(X)$ from three scalar multiplications, $13 \cdot \bar{A} + 5 \cdot \bar{R}'_1 + 8 \cdot \bar{R}'_2$, and a commitment to the full polynomial gives the same point. The verifying circuit computes the expected value $5 \cdot (19 + 42) + 8 \cdot (19 + 21) = 23$ with field arithmetic and compares it with the opening of $A(X)$ at that point.

<!-- /worked:code-sum-text -->

A polynomial identity checked at a random point is enough, as in the [encoding chapter](./polynomial-encoding.md#_1-what-polynomials-provide), and the addition is linear, so it costs no gates. Evaluating at the shared point also means that a stage read by several circuits needs only one opening. A cheater who breaks the tie between stage and claim gets caught here:

<!-- worked:code-sum-catch -->

Suppose the prover folds a squaring trace with stage input $x = 4$ into $A(X)$, while the commitment $\bar{A}$ in the proof still holds $x = 3$. The polynomial it commits to as $A(X)$ then differs from the expected combination by a nonzero polynomial of degree $14$. Of the 43 opening points, $2$ hide the difference.

<!-- /worked:code-sum-catch -->

::: warning Reconstructed from code at commit 3219e08, not confirmed by the authors
**Book:** the sum $\bar{R} = \mathring{A} + \mathring{B}$ is [checked in-circuit by the next $\F_p$ circuit](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/prelim/nested_commitment.md?plain=1#L75-L90). The [PCS chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/pcs.md?plain=1#L244-L247) puts both kinds of check in the next secondary circuit.

**Code at `3219e08`:** we found no such addition of points. The sum holds by definition of each claim, and the openings at $xz$ tie the stored commitments to the folded claim. The stage checks are revdot claims on [the native side](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L338-L400) and on [the nested side](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/claims.rs#L206-L262), each folded by the parent with the rest of that side's claims.

This reading is ours, and the authors have not confirmed it. The site follows the code. The book's version remains a good way to understand the requirement, which is why this section and chapter 13 show it.
:::

## 14. Why cheating fails

The sections above each counted one attack, so here we list what the protection rests on and add one more attack.

A prover can try to overlap the parts, and the stage and final masks catch that. It can try to give circuits different inputs, but they read the same stage polynomial, and the opening check ties the folded claim to the stored commitments. It can try to change a stage after seeing a challenge, but the commitment fixes the stage first, and through the bridge stage the commitment fixes the challenge. It can also try to supply a mask that suits its polynomial, but the mask for each stage is fixed in the registry, so it cannot select a different range. Checking against the wrong range fails in any case:

<!-- worked:wrong-mask -->

Check stage $a(X)$ against the mask of $b(X)$, which forbids gate 1. The product is $3\,y^{9} + 9\,y^{1}$, or $17$ at $y = 7$, and it vanishes at only $3$ of the 43 values of $y$.

<!-- /worked:wrong-mask -->

The bonding polynomials also differ from circuit wiring in a way that blocks a substitution. Since $s(X, 0) = 0$ for a bonding polynomial and $s(X, 0) = 1$ for a circuit, a verifier that fixes $k_0 = 1$ for a circuit claim [cannot be satisfied](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/lib.rs#L321-L327) by a bonding polynomial in its place.

None of these claims is checked in the step that makes it. They join the accumulator, so a false stage leaves a false claim that [the next step folds](./curve-cycles.md#_11-why-cheating-fails), and the decider rejects it at the end. The last step has no parent to do the checking, so the uncompressed verifier [checks the root's own revdot claims](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/verify.rs#L169-L180), which include its mask claims with target 0.

The argument rests on these assumptions, and it is informal. Nobody knows a relation among the generators of either curve, so the commitments bind. The transcript hash behaves as a random oracle, each challenge comes after the commitments it depends on, and $y$ and $z$ come after the stage polynomials they test. A mask's check is only as strong as the degree over the field size, which is negligible for real parameters.

## 15. Staging in Ragu

The small circuits above match the structure of the real ones. The application's own circuit has a [single trace with no stages](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L172-L175), and the internal circuits are where staging happens.

::: warning Reconstructed from code at commit 3219e08, not confirmed by the authors
**Native stages.** They form a tree [rooted at the points binding stage](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/points.rs#L27-L35). One branch runs through the [other points stages](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/points.rs#L14-L20) to the walk stage. The other runs to the preamble, which splits into [outer error then inner error](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/inner_error.rs#L56), and into [query](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/query.rs#L303) then [eval](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/eval.rs#L342).

**Native circuits.** Each circuit's [claim](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L177-L296) sums its own trace with the stages it reads, and each [final mask](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L373-L400) covers all the circuits ending on one stage.

| Circuit | Stages in its sum | Final mask |
| --- | --- | --- |
| `hashes_1` | Preamble, outer error | Outer error |
| `hashes_2` | Outer error | Outer error |
| `collapse` | Preamble, inner error, outer error | Inner error |
| `compute_v`, `bind_challenges` | Preamble, query, eval | Eval |
| `bind_beta` | Points binding, preamble | Preamble |
| `bind_endoscalar`, `endoscaling_step` | The five input points stages, walk | Walk |

**Nested stages.** They form [one chain](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/claims.rs#L137-L155), from the endoscalar and points stages through the bridge stages to the challenge stage. Each endoscaling step sums the first two. The nested `collapse` and `compute_v` circuits hold every stage. The loading polynomial of Section 10 covers the points stage and six of the bridges. The [prover randomizes each ordinary stage's $\alpha$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/_02_preamble.rs#L59-L62), as Section 3 required.

**Mask claims.** Every stage and final mask is one [claim across both children](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/claims.rs#L338-L400), [with no dilation and target 0](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/claims.rs#L125-L131). The saving is visible in the claim count:

<!-- worked:code-count -->

In the standard profile, the native side has $33$ internal circuits, of which $23$ are endoscaling steps, along with $11$ stage masks and $5$ final masks. The [count of revdot claims per fuse](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/mod.rs#L151-L166) is $2 + 2 + 2 \cdot 33 + 16 = 86$. Each internal circuit counts once per child, and each mask counts once across both children, which saves $16$ claims.

<!-- /worked:code-count -->
:::

The warnings in this chapter list where the book and the code differ. The [chapter on recursion in Ragu](./ragu-recursion.md) walks through what these circuits compute. All of this applies to the Ragu revision at `3219e08`. Tachyon, which has not activated on mainnet and whose design is still changing, depends on staging through a [different Ragu revision](https://github.com/tachyon-zcash/tachyon/blob/7e502548db33845dbaacdc0efe905d1a3c45e626/crates/tachyon/Cargo.toml#L83).

## 16. Where this chapter leaves us

This chapter took the following steps:

1. A trace can be split into stage polynomials and a final trace, each with its own commitment, so that some wires are fixed before the others exist.
2. Stage values sit in gates of the form $(a_i, 0, 0, d_i)$, which satisfy the gate equations for any values, so meaning comes only from circuits that read them.
3. Adding parts can hide an overlap that no commitment check sees, so each part has a mask, which is a gate-free revdot claim that forbidden wires are zero.
4. A mask depends only on $XY$, has a closed form, and folds across polynomials without error terms because its claim is linear with target 0.
5. Circuits share data by including the same stage polynomial in their sums, and bonding polynomials compare wires between stages.
6. A mask checks where values sit and not what they mean, so one reading circuit has to enforce the meaning.
7. A nested staged commitment holds a commitment's coordinates in a stage of the other circuit, which lets the transcript absorb them and lets that circuit operate on them.
8. The book adds stage commitments to reach a trace commitment. The code has no trace commitment, defines each claim on the sum of polynomials, and ties the result to the stored commitments by openings at a random point.

We now hold every part that the internal circuits use, namely folding, the registry, endoscalars and stages. The [next chapter](./ragu-recursion.md) assembles them into the recursive step that Ragu runs.
