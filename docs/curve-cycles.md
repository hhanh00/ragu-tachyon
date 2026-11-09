# Curve Cycles

The [recursive proofs chapter](./recursive-proofs.md#point-operations) set a problem aside. A circuit that verifies a proof has to add and scale commitments, and the coordinates of those commitments live in a different field from the circuit's wires. The [accumulation chapter](./accumulation.md#one-recursive-step) ignored the same problem, and the [split accumulation chapter](./split-accumulation.md) worked on one curve as if it did not exist. This chapter deals with it.

We first measure what it costs to compute in the wrong field, and the cost turns out to rule that route out. We then introduce a second curve whose coordinates match the first curve's scalars, divide each fold between two circuits so that each one does only native arithmetic, and handle the two problems this division creates. The two circuits have to see the same data, and they have to use the same challenges. The chapters on [staging](./staging.md) and [endoscalars](./endoscalars.md) later give the full mechanisms for these two problems, so here we only explain why each is needed and show the idea on the toy cycle.

::: warning Reconstructed from code at commit 3219e08, not confirmed by the authors
The split fold in Sections 6 to 10 is our own small assembly of what the Ragu Book describes, checked by the script behind this page. Its circuits are short lists of gates that we run and do not prove, because the toy curves have too few points to serve as generators for a full circuit.
:::

::: tip Terminology
For the general construction we follow the book and say **primary** for the circuit over the first field and **secondary** for the circuit over the second. Section 12 gives the code's names, which are native and nested. The book's accumulation chapters use both "fuse" and "merge" for the circuit that folds, and this site says fuse for the operation on a node, [as chapter 02 does](./pcd-intro.md#fusing-in-ragu).
:::

## 1. Two fields in one commitment

Here is the fold from [chapter 08](./batched-openings.md#_7-beta-batching), which a recursive step has to check:

$$
\begin{aligned}
P &= \beta^m \cdot F + \sum_{i=0}^{m-1} \beta^{m-1-i} \cdot C_i, \\
v &= \beta^m f(u) + \sum_{i=0}^{m-1} \beta^{m-1-i}\, p_i(u).
\end{aligned}
$$

These two lines look alike, but they ask for different arithmetic. The polynomials have coefficients in $\F_{43}$, the scalar field of the toy curve $E$. The second line is therefore a computation in $\F_{43}$, and a circuit over $\F_{43}$ can do it with one gate per multiplication. A circuit has to be over this field because its own trace is a polynomial that gets committed on $E$, and commitments on $E$ take scalars in $\F_{43}$.

The first line adds and scales points of $E$, and the addition formula from the [recursive proofs chapter](./recursive-proofs.md#point-operations) works on coordinates, which lie in $\F_{31}$. We can see what happens if we run that formula on the wrong wires:

<!-- worked:wrong-field -->

Take the commitments $(27,\,30)$ and $(6,\,23)$ from [chapter 08](./batched-openings.md#_8-the-complete-protocol). Modulo 31 the slope is $21$ and the sum is $(5,\,29)$, a point on $E$. Run the same three formulas on wires that reduce modulo 43 and the slope becomes $29$, and the result is $(34,\,25)$, which lies on neither curve of the toy cycle.

<!-- /worked:wrong-field -->

The formula fails because each of its multiplications needs a remainder modulo 31, and the wires produce a remainder modulo 43:

<!-- worked:wrap -->

The first gate of that addition checks $\lambda \cdot (x_2 - x_1) = y_2 - y_1$, which here reads $21 \cdot 10 = 24$ modulo 31. As integers, $21 \cdot 10 = 210$, and $210$ leaves remainder $24$ modulo 31. A wire in $\F_{43}$ holds $38$, because that is the remainder modulo 43, and the remainder modulo 43 says nothing about the remainder modulo 31.

<!-- /worked:wrap -->

So a circuit over $\F_{43}$ handles the value $v$ directly but has no direct way to handle the point $P$. On real curves the same mismatch holds, and the two fields have no useful relation between their remainders.

## 2. Emulating the other field

A circuit can still check a multiplication modulo 31 if it treats the numbers as integers. The prover supplies a remainder $r$ and a multiple $t$, and the circuit checks the integer equation

$$a \cdot b = r + 31\,t.$$

If this holds over the integers and $r$ is small, then $r$ is the product modulo 31. The difficulty is that a gate can only check equations modulo 43, and the two sides of this equation are often larger than 43, so a false witness can match:

<!-- worked:one-equation -->

The honest witness for $210$ is $r = 24$ and $t = 6$, since $24 + 31 \cdot 6 = 210$. A single gate can only check this equation modulo 43. Of the $992$ pairs with $r$ below 31 and $t$ below 32, $23$ satisfy it, and $22$ of those have the wrong remainder. One of them is $r = 0$ and $t = 4$, because $0 + 31 \cdot 4 = 124$, which equals $210$ modulo 43.

<!-- /worked:one-equation -->

The way out is to make every equation the circuit checks so small that it cannot wrap around modulo 43, because an equation between small numbers modulo 43 is also an equation between integers. We split $a$, $b$, $r$ and $t$ into pieces called **limbs**. On the toy field each limb is one bit, so $a = \sum_i a_i 2^i$ with five bits, and similarly for the others. We also write $31\,t = 32\,t - t$, which keeps the terms small. Expanding $a b - r - 32\,t + t$ and collecting by powers of 2 gives one column per power:

$$a b - r - 31\,t = \sum_{k} \Big( \sum_{i+j=k} a_i b_j \;-\; r_k \;+\; t_k \;-\; t_{k-5} \Big)\, 2^k.$$

This sum has to be zero, but each column does not have to be zero, since a column can carry into the next one as in ordinary addition. So the circuit takes a witness carry $c_k$ for each column and checks

$$\sum_{i+j=k} a_i b_j - r_k + t_k - t_{k-5} + c_{k-1} = 2\,c_k,$$

with $c_{-1} = 0$ and the last carry equal to 0. Here is the first gate of our addition, written in columns:

<!-- worked:columns -->

| Column $k$ | Sum of $a_i b_j$ | $r_k$ | $t_k$ | $t_{k-5}$ | Carry in | Carry out |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1 | 1 | 0 | 1 | 0 | 0 | 1 |
| 2 | 0 | 0 | 1 | 0 | 1 | 1 |
| 3 | 2 | 1 | 0 | 0 | 1 | 1 |
| 4 | 0 | 1 | 0 | 0 | 1 | 0 |
| 5 | 2 | 0 | 0 | 0 | 0 | 1 |
| 6 | 0 | 0 | 0 | 1 | 1 | 0 |
| 7 | 1 | 0 | 0 | 1 | 0 | 0 |
| 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| 9 | 0 | 0 | 0 | 0 | 0 | 0 |

<!-- /worked:columns -->

<!-- worked:emul-count -->

Here $a = 21$ and $b = 10$. Each row satisfies its equation and the last carry is 0. The gates are $25$ for the products $a_i b_j$, $10$ to show that the bits of $r$ and $t$ are bits, and $18$ for the $9$ carries at $2$ bits each, since an honest carry always lies between $0$ and $3$. That is $53$ gates for one multiplication in $\F_{31}$. We ran the check on all $31^2$ pairs $(a, b)$ against all $32^2$ pairs $(r, t)$. It accepted $961$ inputs, one for each pair $(a, b)$, and each of them had the true remainder.

<!-- /worked:emul-count -->

One native multiplication has become dozens of gates. The cost multiplies through every point operation, since the formulas are built from these multiplications:

<!-- worked:emul-toy-scalar -->

A 6-bit scalar multiplication on $E$ does 5 doublings and 5 additions, or $35$ multiplications in $\F_{31}$ at $53$ gates each. With its selections and scalar bits, it costs $1,911$ gates, where the same operation on $E'$ costs $51$ gates in the [recursive proofs chapter](./recursive-proofs.md#point-operations). That leaves out the extra work to reduce the sums and differences in each formula back into range.

<!-- /worked:emul-toy-scalar -->

A real field has room for larger limbs, which lowers the count per bit. The next estimate is our own plain design and not a gadget that Ragu contains, and better gadgets exist that cut these numbers by some factor:

<!-- worked:emul-real -->

Take the same plain design with 4 limbs of 64 bits. One multiplication then uses $16$ limb products, $510$ bits for $r$ and $t$, and $7$ carries of about $67$ bits, for about $995$ gates. A point addition needs three of these, or about $2,985$ gates, which already exceeds the $2,048$ gates that Ragu allows in one circuit. A 255-bit scalar multiplication needs $1,778$ multiplications, or about $1,769,110$ gates, where the native version costs $2,541$. Apart from the MSM for $\hat{G}$, the verifier of Chapter 09 has $32$ such multiplications, which comes to about $56,611,520$ gates.

<!-- /worked:emul-real -->

The book [calls non-native arithmetic prohibitively expensive](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/prelim/nested_commitment.md?plain=1#L3-L9), and these counts show why. The accumulator's whole purpose was to keep the verifier small, and this one requirement would undo it. We need a way to avoid computing in the wrong field at all.

## 3. A curve for each field

The recursive proofs chapter already used the way out, when it counted gates on the partner curve $E'$, since the coordinates of that curve lie in $\F_{43}$:

<!-- worked:native-add -->

Take the points $(34,\,3)$ and $(40,\,18)$ on $E'$. Their slope and sum are computed modulo 43, so every gate works in the circuit's own field. The addition takes $3$ gates and gives $(29,\,31)$, which we confirmed lies on $E'$.

<!-- /worked:native-add -->

It may look as if we could move everything to $E'$, but $E'$ has 31 points, so its scalars lie in $\F_{31}$. A commitment on $E'$ holds a vector over $\F_{31}$, and it cannot hold the polynomials of a circuit over $\F_{43}$. Those polynomials need $E$, and the points of $E$ need wires in $\F_{31}$. A circuit over $\F_{31}$ would then have its own polynomials, which $E'$ can commit to, and those points need wires in $\F_{43}$. The two curves fit together in this way because of how their numbers of points were chosen:

<!-- worked:cycle-table -->

| Curve | Coordinates in | Scalars in | Polynomials it commits to | Circuit that can do its point arithmetic |
| --- | --- | --- | --- | --- |
| $E$ | $\F_{31}$ | $\F_{43}$ | Over $\F_{43}$ | Wires in $\F_{31}$ |
| $E'$ | $\F_{43}$ | $\F_{31}$ | Over $\F_{31}$ | Wires in $\F_{43}$ |

<!-- /worked:cycle-table -->

We call this a **2-cycle of curves**. It is a pair of prime fields $\F_p$ and $\F_q$, with a curve over $\F_p$ that has $q$ points and a curve over $\F_q$ that has $p$ points. Each circuit can do the point arithmetic for the polynomials of the other. [Ben-Sasson, Chiesa, Tromer and Virza](https://eprint.iacr.org/2014/595) introduced the use of such cycles for recursive proofs.

A single curve whose number of points equals the size of its field would avoid the need for a partner, but such a curve is called **anomalous**, and discrete log on anomalous curves is easy by a known attack due to Smart, Semaev, and Satoh and Araki. So two curves are the smallest arrangement that works.

The Hasse bound says that a curve over $\F_p$ has $p + 1 - t$ points with $|t| \leq 2\sqrt{p}$, which means the two primes of a cycle must be close together:

<!-- worked:hasse -->

For $E$ we have $31 + 1 - 43 = -11$, and $2\sqrt{31}$ is about $11.1$. For $E'$ we have $43 + 1 - 31 = 13$, and $2\sqrt{43}$ is about $13.1$. Both differences fit within the bound.

<!-- /worked:hasse -->

Pairs of curves with this property are uncommon, even among small primes:

<!-- worked:cycle-search -->

We counted the points on every curve $y^2 = x^3 + b$ over each of the $21$ primes below 200 that are congruent to 1 modulo 3. Among the $210$ pairs of these primes, $10$ form a cycle, and the pair $(31, 43)$ is one of them. The same count finds $5$ primes with a curve whose number of points equals its field size, starting with $7$.

<!-- /worked:cycle-search -->

## 4. The Pasta cycle

Ragu uses the [Pasta curves](https://electriccoin.co/blog/the-pasta-curves-for-halo-2-and-beyond/), which [Chapter 01](./scaling-zcash.md) explained are already deployed in Orchard and in hardware wallets. **Pallas** is the curve $y^2 = x^3 + 5$ over $\F_p$ with $q$ points, and **Vesta** is the curve $y^2 = x^3 + 5$ over $\F_q$ with $p$ points, where

<!-- worked:pasta-numbers -->

$$
\begin{aligned}
p &= \texttt{0x40000000000000000000000000000000224698fc094cf91b992d30ed00000001}, \\
q &= \texttt{0x40000000000000000000000000000000224698fc0994a8dd8c46eb2100000001}.
\end{aligned}
$$

Both are primes of 255 bits, and $q - p$ has only 87 bits, which is below the size that $2\sqrt{p}$ allows. We tested the cycle property directly. A point found on $y^2 = x^3 + 5$ over $\F_p$ goes to the identity when multiplied by $q$, a point over $\F_q$ goes to the identity when multiplied by $p$, and only one multiple of each prime lies within the Hasse range, so the two orders must be $q$ and $p$.

<!-- /worked:pasta-numbers -->

The next table lines up the names we will use. The field of the main circuit is $\F_p$, and [the code](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_core/src/lib.rs#L63-L81) commits that circuit's polynomials on Vesta, whose scalars are $\F_p$ and whose coordinates are $\F_q$. The toy cycle plays the same roles, with one difference in size. In the toy cycle the main circuit has the larger field, while in Pasta it has the smaller one, and this does not affect the construction.

<!-- worked:names -->

| Role | Toy cycle | Pasta | Book | Code at `3219e08` |
| --- | --- | --- | --- | --- |
| Field of the main circuit's wires | $\F_{43}$ | $\F_p$ | $\F^{(1)}$, $CS^{(1)}$ | `CircuitField` |
| Curve for that circuit's polynomials | $E$ | Vesta | $\G^{(1)}$, $\G_{host}$ | `HostCurve` |
| Field of the other circuit's wires | $\F_{31}$ | $\F_q$ | $\F^{(2)}$, $CS^{(2)}$ | `ScalarField` |
| Curve for that circuit's polynomials | $E'$ | Pallas | $\G^{(2)}$, $\G_{nested}$ | `NestedCurve` |

<!-- /worked:names -->

The two fields are close in size, but their elements are not interchangeable, because a value can be in range for one and out of range for the other:

<!-- worked:fit -->

In the toy cycle, $12$ of the 43 values of $\F_{43}$ are 31 or larger, so more than a quarter of them have no equal in $\F_{31}$. In the Pasta cycle the fraction is near $2^{-167}$, so a random value of $\F_q$ almost always fits in $\F_p$. A protocol still cannot rely on that for values a prover can choose.

<!-- /worked:fit -->

Section 9 returns to this when challenges have to cross between the circuits.

## 5. Recursion on a cycle

With two curves there are two kinds of circuit, and every recursive step now uses both. The book [calls this a ping-pong pattern](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/index.md?plain=1#L104-L119). There is a primary circuit $CS^{(1)}$ over $\F_p$ and a secondary circuit $CS^{(2)}$ over $\F_q$. Each has its own polynomials, committed on its own curve, so each has its own accumulator. Where the [split accumulation chapter](./split-accumulation.md) had one $\mathsf{acc}_i$, we now have a pair $(\mathsf{acc}_i^{(1)}, \mathsf{acc}_i^{(2)})$.

Each accumulator contains both field elements and points, and the rule for dividing the work follows from Section 1. Field elements are native to the circuit that made the polynomial, and points are native to the other circuit. The book [states the split](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/index.md?plain=1#L186-L192) for the whole accumulator, including the $\bar{A}$, $\bar{B}$ and $c$ that the [revdot folding chapter](./revdot-folding.md) introduces. For the batched claim $(P, u, v)$ it gives:

| Accumulator | Polynomials over | Commitment $P$ lies on | $v$ folded by | $P$ folded by |
| --- | --- | --- | --- | --- |
| $\mathsf{acc}^{(1)}$ | $\F_{43}$, or $\F_p$ | $E$, or Vesta | Primary | Secondary |
| $\mathsf{acc}^{(2)}$ | $\F_{31}$, or $\F_q$ | $E'$, or Pallas | Secondary | Primary |

So the update of each accumulator is [split between the two circuits](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/pcs.md?plain=1#L145-L160), and each circuit updates half of each accumulator.

Timing matters as well. A circuit's commitments do not exist until its trace is complete, so a step cannot fold its own trace. The book's rule is that [the instances produced in step $i$ are folded only in step $i + 1$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/index.md?plain=1#L181-L182). The trace of the primary circuit in step $i$ becomes a commitment on $E$, whose coordinates the secondary circuit can read, so the secondary circuit folds that point in step $i + 1$. The same holds in the other direction:

![Two rows of circuits across two steps. The circuit over F43 folds values over F43 and points on E prime, and the circuit over F31 folds values over F31 and points on E. Arrows cross between steps, carrying each circuit's trace commitment to the other circuit.](./manim/curve-cycle-ping-pong.png)

Everything from the [recursive proofs chapter](./recursive-proofs.md#_8-from-a-chain-to-a-tree) about trees carries over. A node holds two children, each with a pair of accumulators, and it folds both into one new pair.

## 6. A fold split across two circuits

Here is one fold on the toy cycle. We take two claims on each curve. The first side reuses chapter 08's polynomials, and the second side uses two new polynomials over $\F_{31}$ committed with four generators of $E'$.

<!-- worked:fold-inputs -->

| Claim | Coefficients | Point | Value | Commitment |
| --- | --- | --- | --- | --- |
| $p_0$ over $\F_{43}$, on $E$ | $(7, 2, 5, 3)$ | $9$ | $37$ | $(27,\,30)$ |
| $p_1$ over $\F_{43}$, on $E$ | $(3, 1, 8, 4)$ | $5$ | $20$ | $(6,\,23)$ |
| $p'_0$ over $\F_{31}$, on $E'$ | $(4, 9, 2, 6)$ | $5$ | $12$ | $(25,\,25)$ |
| $p'_1$ over $\F_{31}$, on $E'$ | $(8, 3, 7, 5)$ | $3$ | $29$ | $(42,\,7)$ |

<!-- /worked:fold-inputs -->

The prover runs chapter 08's batching on each side, with the same three challenges on both:

<!-- worked:fold-f -->

The challenges are $\alpha = 11$, $u = 13$ and $\beta = 15$, each picked by hand and each below 16, for a reason that Section 9 gives. On the first side, the prover's quotient combination is $f = (20, 36, 37, 0)$ with commitment $F = (28,\,10)$, and the values at $u$ are $30$ and $8$. On the second side, it is $f' = (6, 2, 9, 0)$ with commitment $F' = (13,\,21)$, and the values at $u$ are $1$ and $1$.

<!-- /worked:fold-f -->

Now we assign each output to the circuit where it is native. For a value, the circuit inverts each $u - x_i$, multiplies by the difference $p_i(u) - y_i$, and accumulates with powers of $\alpha$ and then of $\beta$. For a point, it runs the Horner form of the first equation in Section 1, starting from the commitment to $f$ and using the plain double-and-add from the recursive proofs chapter on the 4-bit $\beta$:

<!-- worked:fold-split -->

| Output | Computed in | Operations | Result | Gates |
| --- | --- | --- | --- | --- |
| $v$ over $\F_{43}$ | Circuit over $\F_{43}$ | Field arithmetic | $14$ | 8 |
| $P'$ on $E'$ | Circuit over $\F_{43}$ | Point arithmetic | $(20,\,40)$ | 68 |
| $v'$ over $\F_{31}$ | Circuit over $\F_{31}$ | Field arithmetic | $9$ | 8 |
| $P$ on $E$ | Circuit over $\F_{31}$ | Point arithmetic | $(17,\,24)$ | 68 |

<!-- /worked:fold-split -->

<!-- worked:fold-decide -->

The prover also holds the combined polynomials $p = (7, 4, 23, 6)$ and $p' = (23, 30, 16, 2)$. A decider commits to them and gets $(17,\,24)$ on $E$ and $(20,\,40)$ on $E'$. Evaluating at $u = 13$ gives $14$ in $\F_{43}$ and $9$ in $\F_{31}$. All four numbers match the table.

<!-- /worked:fold-decide -->

The saving is what this arrangement is for:

<!-- worked:fold-compare -->

The tracer that runs these gates refuses any point whose coordinates are not in its own field, and every run above passed that test. The point $P$ took $68$ gates on wires in $\F_{31}$. If the circuit over $\F_{43}$ had computed it by the method of Section 2, the same steps would have cost at least $2,612$ gates.

<!-- /worked:fold-compare -->

The table hides two assumptions. The secondary circuit computed $P$ from the commitments on $E$ and the primary circuit computed $v$ from claims about those same polynomials, but nothing yet connects what the two circuits read. A prover could give each a different set of inputs. The two circuits also used the same $\alpha$, $u$ and $\beta$ only because we typed the same numbers. The book names these problems [input consistency and challenge consistency](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/pcs.md?plain=1#L160-L173). The next three sections address them.

## 7. Committing to coordinates

The primary circuit derives challenges by hashing the transcript, as the [recursive proofs chapter](./recursive-proofs.md#the-hash) required, and the transcript has to contain the commitments that the challenges test. For a commitment on $E$, this means absorbing coordinates from $\F_{31}$ into a sponge over $\F_{43}$. A circuit cannot do that natively, and the book also [rules out](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/pcs.md?plain=1#L189-L192) hashing all the inputs on both sides and comparing the digests, since that needs either non-native arithmetic or bit decompositions of every value.

The cycle gives a neater route. The coordinates of a point on $E$ are elements of $\F_{31}$, and $\F_{31}$ is exactly the scalar field of $E'$. So we can place the coordinates in a vector and make an ordinary Pedersen commitment to it on $E'$. The result is one point on $E'$, whose coordinates lie in $\F_{43}$. The book calls this a [**nested commitment**](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/prelim/nested_commitment.md?plain=1#L20-L39), and it writes $\mathring{A}$ for the nested commitment to data involving $A$:

<!-- worked:nested-run -->

Take $A = (27,\,30)$ and $B = (6,\,23)$. Their coordinates form the vector $(27, 30, 6, 23)$ in $\F_{31}^4$. Each entry is a valid scalar on $E'$, so we commit with four generators of $E'$, namely $(32,\,3), (34,\,3), (35,\,21), (37,\,7)$:

$$\mathring{A} = 27 \cdot G'_0 + 30 \cdot G'_1 + 6 \cdot G'_2 + 23 \cdot G'_3 = (12,\,12).$$

The coordinates of $\mathring{A}$ lie in $\F_{43}$, so the circuit over $\F_{43}$ can hold them as wires and absorb them. The [toy sponge](./statements-and-challenges.md#a-toy-poseidon) over $\F_{43}$ takes those two values and squeezes the output $2$.

<!-- /worked:nested-run -->

In this way, one small point can stand for any number of foreign points. The commitment binds them under the same assumption as any Pedersen commitment, now for the generators of the second curve:

<!-- worked:nested-binding -->

Changing the first coordinate to each of the other $30$ values gives $30$ different points, and $28$ of those change the sponge's output as well. A vector of four entries from $\F_{31}$ has $923,521$ possible values and $E'$ has only 31 points, so collisions must exist. Here is one found by solving a discrete log: since $G'_0 + 26 \cdot G'_1 = \mathcal{O}$, the vector $(28, 25, 6, 23)$ gives the same point.

<!-- /worked:nested-binding -->

Both circuits need to read all of the step's data, which includes four kinds of values. The primary circuit is native to values in $\F_{43}$ and to points on $E'$, and the secondary circuit is native to values in $\F_{31}$ and to points on $E$. The book's [encoding for the primary circuit](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/pcs.md?plain=1#L201-L210) handles them in two layers. The values and points that it can read go directly into a part of its own trace, which gives a commitment $C$ on $E$. Then $C$, the points of $E$ and the values in $\F_{31}$ all form one vector over $\F_{31}$, and the nested commitment to this vector is a point with coordinates in $\F_{43}$. The secondary circuit's encoding mirrors this, so that each circuit holds what it can read as wires and holds the rest behind one commitment.

The prover computes a nested commitment outside the circuit and supplies it as a witness. So at this stage the primary circuit knows that it hashed some point, and it does not yet know that the point contains the coordinates that the secondary circuit used. The next section adds that connection.

## 8. Deferred operations

Suppose the primary circuit's fold needs $s \cdot A$ for some point $A$ on $E$. It holds only $\mathring{A}$, so it cannot compute this. The nested commitment [binds the data without carrying over any operation on it](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/prelim/nested_commitment.md?plain=1#L43-L56). The secondary circuit has the coordinates of $A$ as wires and can do the multiplication, so the work moves there, and we call it a **deferred operation**.

For this to mean anything, the wires that the secondary circuit uses have to be the same values that $\mathring{A}$ commits to. The tool for this is a **staged trace**, which the [staging chapter](./staging.md) covers in full. The prover splits the secondary circuit's trace into two polynomials,

$$r(X) = A(X) + r'(X),$$

where $A(X)$ holds the coordinates in slots reserved for it and $r'(X)$ holds everything else. It commits to each part separately, and the commitment to $A(X)$ is the nested commitment that the transcript absorbed. The book then [requires two checks](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/prelim/nested_commitment.md?plain=1#L70-L78). The commitments must add up to the commitment to the whole trace, and the parts must not overlap.

Here is a shortened trace that stands in for a real one, since the toy curve has too few points for more:

<!-- worked:stage-run -->

The circuit over $\F_{31}$ adds $A$ and $B$. Its stage holds $(27, 30, 6, 23)$ and its later wires hold the slope, the difference of $x$-coordinates and the output, $(21, 10, 5, 29)$, so the full vector is $(27, 30, 6, 23, 21, 10, 5, 29)$. With eight generators of $E'$, the stage commits to $\mathring{A} = (12,\,12)$, the later part to $R' = (29,\,12)$, and the whole vector to $R = (2,\,31)$. The next step's circuit over $\F_{43}$ adds $\mathring{A}$ and $R'$ in $3$ gates, gets $(2,\,31)$, and compares it with $R$.

<!-- /worked:stage-run -->

These are points on $E'$, so the addition is native to the primary circuit and costs only a few gates. The check stops a prover who uses other coordinates:

<!-- worked:stage-sum -->

Suppose the prover traces the circuit with a different $x$-coordinate for $A$ while it leaves $\mathring{A}$ alone. We tried each of the $30$ other values. Each one changes $R$, and all $30$ fail the comparison.

<!-- /worked:stage-sum -->

A commitment sum cannot enforce the second check, however, and the structure of our curve gives a sharp example:

<!-- worked:stage-overlap -->

Let the prover put $15$ in slot 0 of the later part, which is reserved for the stage. The stage still says $x = 27$, but the sum holds $11$ in that slot, so the circuit runs on $(11,\,30)$ in place of $A$. That is a genuine point of $E$, because $5^3 = 1$ modulo 31 and the equation of $E$ only sees $x^3$. The commitment check still passes, since $\mathring{A} + R'$ equals the commitment to the sum. It passes for all $30$ nonzero values in that slot, because a commitment to a sum equals the sum of the commitments however the entries overlap.

<!-- /worked:stage-overlap -->

So a separate check has to show that $r'$ is zero in the stage's slots. In our toy form, the verifier picks a random $z$ and asks for the combination $\sum_{i} z^i r'_i$ over the reserved slots to be zero. This is a linear claim about $r'$ that a circuit can fold, and Ragu expresses such a claim as a [revdot product with a stage mask](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/extensions/staging.md?plain=1#L41-L58).

<!-- worked:stage-mask -->

For the entry above, the combination equals $15$ at every $z$, so all 31 values of $z$ catch it. A prover that uses two reserved slots can cancel at one $z$, and over all $900$ pairs of nonzero entries, no pair passes at more than $1$ value of $z$.

<!-- /worked:stage-mask -->

To summarize, each step leaves [two kinds of work](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/prelim/nested_commitment.md?plain=1#L92-L96) for the next. It has to check that the partial traces are well formed, and it has to check that the deferred group operations were computed correctly. Both are claims about a circuit that the next step folds like any other, which is why deferring them does not make them pile up.

## 9. Sharing one set of challenges

The two circuits must use the same challenges, because the primary circuit folds $v$ and the secondary circuit folds $P$, and these only describe one polynomial if both use one $\beta$. Running a second transcript in the secondary circuit would give different values. The book's answer is called [transcript bridging](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/pcs.md?plain=1#L272-L279). Only the primary circuit hashes, and its challenges serve both circuits. That is safe only together with the input consistency of Section 8, because the secondary circuit's inputs reach the transcript only through the nested commitments, and they have to be fixed before the challenges are.

The difficulty is that a challenge is an element of $\F_{43}$, and the secondary circuit has wires in $\F_{31}$. Section 4 showed that the two fields do not hold the same numbers:

<!-- worked:big-challenge -->

Suppose the challenge is $38$. On $E$, the scalar is a value modulo 43, and $38 \cdot A = (9,\,22)$. A circuit over $\F_{31}$ that holds the number as one wire holds $7$, and $7 \cdot A = (24,\,1)$.

<!-- /worked:big-challenge -->

Two things fix this. First, the challenge is kept short enough that the same integer fits in both fields. In our run we used values below 16, and the code uses [143-bit values](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_primitives/src/endoscalar.rs#L64-L67) called **endoscalars**. Second, the circuit computes with the challenge through its bits, using the curve's endomorphism, in a way that the [endoscalars chapter](./endoscalars.md) explains. In the code the short value maps to a scalar that is not the plain integer, and our toy run does not reproduce that map.

The secondary circuit still has to receive the right short value, and the primary circuit can check this from the outside. The prover puts the values in a stage of the secondary circuit with no blinding. The commitment to that stage is then a fixed combination of generators of $E'$, and those points are native to the primary circuit:

<!-- worked:challenge-bind -->

The stage holds the vector $(11, 13, 15)$ in $\F_{31}$, with no blinding, on the generators $(20,\,3), (21,\,18), (25,\,18)$, and its commitment is $C_s = (21,\,25)$. The circuit over $\F_{43}$ knows the three challenges as wires, so it can break each into bits and compute $\alpha \cdot G'_9 + u \cdot G'_{10} + \beta \cdot G'_{11}$ on $E'$ itself. This takes $99$ gates and gives $(21,\,25)$. If the prover hands the other circuit any of the $30$ other values of $\beta$, the stage commits to a different point, and the comparison fails.

<!-- /worked:challenge-bind -->

A short challenge gives a prover a better chance of hitting a lucky value, since there are fewer values to try:

<!-- worked:short-count -->

Take a cheater who claims $p_0(9) = 38$ and $p_1(5) = 5$ and shifts its values at $u$ by the same amounts, as in [chapter 08](./batched-openings.md#the-cheater-lies-about-a-value-at-u). The error in $v$ is $\beta - 15$, so one value of $\beta$ out of the 43 passes, namely $15$. Since the cheater aimed at a short value, that same one passes among the 16 short challenges, which moves its chance from $1$ in 43 to $1$ in 16.

<!-- /worked:short-count -->

On a real curve that chance is the degree of the error polynomial divided by $2^{143}$, which remains negligible. The book notes that [endoscalars are only for public challenges](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/extensions/endoscalar.md?plain=1#L13-L18), since this shorter range would be unsafe for a secret.

## 10. Two steps of ping-pong

We can now run the whole pattern for two steps. In step 1, each circuit does the work of the table in Section 6. In step 2, each accumulator meets a new claim from the trace of a circuit in step 1. The toy curves cannot hold a full trace, so we use four wires of each circuit's trace as a stand-in polynomial and commit to it on that circuit's curve. The commitment made by the circuit over $\F_{43}$ goes to the circuit over $\F_{31}$ in the next step for its point arithmetic, and the same holds the other way around.

<!-- worked:two-steps -->

|  | Step 1 | Step 2 |
| --- | --- | --- |
| Accumulator on $E$ on entry | Claims $p_0$, $p_1$ above | $((17,\,24),\ 13,\ 14)$ |
| Accumulator on $E'$ on entry | Claims $p'_0$, $p'_1$ above | $((20,\,40),\ 13,\ 9)$ |
| New claim on $E$ on entry | None | $((11,\,1),\ 7,\ 37)$, from step 1's circuit over $\F_{43}$ |
| New claim on $E'$ on entry | None | $((38,\,21),\ 12,\ 20)$, from step 1's circuit over $\F_{31}$ |
| Challenges $\alpha, u, \beta$ | $11, 13, 15$ | $6, 10, 9$ |
| Circuit over $\F_{43}$ outputs | $v = 14$, $P' = (20,\,40)$ | $v = 6$, $P' = (7,\,7)$ |
| Circuit over $\F_{31}$ outputs | $v' = 9$, $P = (17,\,24)$ | $v' = 13$, $P = (8,\,9)$ |
| Gates over $\F_{43}$ / $\F_{31}$ | 76 / 76 | 76 / 76 |

<!-- /worked:two-steps -->

The gate counts do not change between steps, which is the [fixed circuit](./recursive-proofs.md#_6-why-the-circuit-cannot-keep-growing) that recursion requires. At the end, one decider handles both curves:

<!-- worked:two-steps-decide -->

The decider commits to the two final polynomials $p = (32, 41, 33, 20)$ and $p' = (25, 9, 21, 27)$, which gives $(8,\,9)$ on $E$ and $(7,\,7)$ on $E'$, and it evaluates them at $u = 10$ to get $6$ and $13$. That single decision on each curve covers the two claims of step 1 and the two traces it produced. If the value in the accumulator on $E$ had been $15$ at the start of step 2, the circuit would have derived $v = 39$, and the decider would have rejected, since the polynomial still evaluates to $6$.

<!-- /worked:two-steps-decide -->

## 11. Why cheating fails

The division of the fold leaves new places to cheat, so we go through them in the order of the sections above. In each case a check that the honest prover passes without effort catches the cheater, but the catch may come one step later or at the decider.

**A wrong result from a circuit.** A prover cannot report a wrong point, because the gates determine it:

<!-- worked:gates-exact -->

We tried every wrong output for the addition of $A$ and $B$ with every possible slope witness, which makes $1,271$ attempts on the circuit over $\F_{31}$, and none satisfied the three gates. The transcript and the commitments did not enter into that count.

<!-- /worked:gates-exact -->

**Different data for each circuit.** Section 8 showed that the sum check catches a prover who uses other coordinates in a trace, and that the overlap check catches a prover who hides a change in a reserved slot. Changing $\mathring{A}$ itself to match would change the transcript and therefore every later challenge. So the prover has to commit to the secondary circuit's inputs before it learns the challenges, as in [chapter 03's discussion of omitted data](./statements-and-challenges.md#_9-omitting-data-from-the-transcript).

**Different challenges for each circuit.** Section 9 showed that the primary circuit recomputes the challenge stage's commitment on $E'$ from its own transcript, so the secondary circuit cannot use any other values without a commitment mismatch.

**Skipping the deferred work.** Each check above happens in the next step, so the last step's checks have no later step to run them. This is why the decider has to examine both accumulators and the root proof's stages. If a false point or a false stage survives to the end, then one of the claims on $E$ or $E'$ is false, and the decider rejects it by the argument of the [accumulation chapter](./accumulation.md#_8-why-cheating-fails). A verifier that checks only one curve leaves half of every fold unconfirmed, since that half happened on the other side.

The argument rests on these assumptions, and it is informal. The discrete log relation assumption has to hold for the generators of both curves, so both curves have to be secure, which is one more reason an anomalous curve cannot serve. The transcript hash over $\F_p$ has to behave as a random oracle. Challenges have to come after the data they test, and short challenges have to be long enough for the degree of the claims. The decider has to run on both sides.

## 12. Cycles in Ragu

The book describes the design as [inspired by CycleFold](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/index.md?plain=1#L28-L29). We could read only the abstract of [CycleFold](https://eprint.iacr.org/2023/1192), which says that the second curve merely represents a single scalar multiplication in a tiny circuit, and that the first curve folds invocations of that circuit. Ragu's code shares the main feature of that picture, because its application lives on one side only. It differs in having several internal circuits on the other side and not one tiny circuit, and this comparison is our own.

::: warning Reconstructed from code at commit 3219e08, not confirmed by the authors
- **Names.** The code's **native** side is the primary circuit, over `CircuitField`, with commitments on `HostCurve`. Its **nested** side is the secondary circuit, over `ScalarField`, with commitments on `NestedCurve`. Polynomials on the nested side that hold native commitments are called **bridge** stages. A [`Proof`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/proof/mod.rs#L187-L240) lists these three groups of polynomials, and one call to `fuse` produces all of them.
- **Nested commitments.** [`compute_bridge_preamble`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/_02_preamble.rs#L69-L91) places the children's Vesta commitments in a stage over $\F_q$ and commits to it on Pallas. Then [`fuse`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/mod.rs#L105-L108) absorbs that point and squeezes the first challenge, and the [`hashes_1` circuit](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/hashes_1.rs#L242-L248) repeats this with gates. The transcript absorbs only such bridge commitments. Pallas commitments go into [native points stages](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/stages/points.rs#L1-L25), whose Vesta commitments in turn ride in the bridge stages, so they too are fixed before the challenges that test them.
- **Folding the points.** Each side has a walk that performs the Horner sum for the other side's $P$. The [nested walk](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/endoscalar.rs#L337-L338) folds points on Vesta over $\F_q$, and the [native walk](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/endoscaling_step.rs#L148-L149) folds points on Pallas over $\F_p$. A walk does not fit in one circuit of at most $2^{11}$ gates, so the native one spreads across [23 circuits](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/mod.rs#L80), each doing [4 endoscalings](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/mod.rs#L61).
- **Challenges.** The nested side [squeezes nothing](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/mod.rs#L234-L256), and it reads each challenge as a lift of a native one. Its [challenge stage](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/stages/challenges.rs#L1-L22) is committed without blinding, and the [`bind_challenges`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/bind_challenges.rs#L1-L23) circuits, finished by a parent's [`bind_beta`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/bind_beta.rs#L1-L22), recompute its commitment on Pallas. This is the check of Section 9.
- **The decider.** The [uncompressed verifier](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/verify.rs#L397-L407) checks claims on both sides. It also [rederives the root's challenge stage](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/verify.rs#L36-L38), because the root has no parent to bind it, which is the point about the last step in Section 11.
:::

The book and the code differ in several places. We give each difference next to the book's text.

::: warning Application circuits on the secondary side
**Book:** [each side has an application circuit](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/index.md?plain=1#L132-L163), and the application state is [a pair $(z^{(1)}, z^{(2)})$](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/index.md?plain=1#L115-L117).

**Code at `3219e08`:** [every nested circuit is internal](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/pcs.rs#L6-L7), and [a step's headers](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/step/mod.rs#L156-L160) are over `CircuitField` alone. The application lives only on the native side.

This site follows the code. It is also the closer match to the book's own description of the design as CycleFold-inspired.
:::

::: warning Adding the stage commitments
**Book:** the [commitments to the partial traces add up to the trace commitment](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/prelim/nested_commitment.md?plain=1#L70-L78), and the next $\F_p$ circuit checks that in-circuit.

**Code at `3219e08`:** we found no such addition. The only point additions in the internal circuits are in the two walks and the challenge bindings ([`bind_challenges`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/bind_challenges.rs#L203-L226), [`bind_beta`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/bind_beta.rs#L194-L199)). A proof keeps a commitment for each stage and no commitment to the whole trace, each stage's commitment [goes into the batch](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/mod.rs#L48-L53) on its own, and a [circuit's claim uses the sum of its stage polynomials](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/claims.rs#L77-L85). So we read the code as establishing the sum through polynomial claims and not through a point addition. This reading is ours.

Section 8 teaches the book's form, because it shows the purpose of the check on small numbers. The site otherwise follows the code, and the [staging chapter](./staging.md) takes this further. The book's other description of [which circuit runs the checks](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/pcs.md?plain=1#L244-L247) also differs, since it places both stage checks and staged commitment checks in the next step's secondary circuit, while the passage above places the sum in the primary circuit.
:::

::: warning Which challenges are short
**Book:** the [transcript bridging section](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/accumulation/pcs.md?plain=1#L261-L270) sets the next verifier challenge to the endoscalar extracted from the hash output.

**Code at `3219e08`:** on the native side, [$\alpha$ and $u$ are used as full field elements](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/fuse/mod.rs#L226-L245), and only [$\beta$ is extracted to an endoscalar](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/native/circuits/compute_v.rs#L176-L177), because it is the one that scales points. The nested side [lifts every challenge from its low bits](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/internal/nested/mod.rs#L254-L256).

This site follows the code. Our toy run uses short values on both sides to keep one set of numbers.
:::

Earlier chapters recorded related differences. The book's [base case](./recursive-proofs.md#_9-the-base-case) and its [root of initial states](./recursive-proofs.md#_10-tracking-initial-states) appear on each side of its cycle, and the code handles them as described there. The book's single fuse circuit per curve corresponds in the code to [many internal circuits](./recursive-proofs.md#_12-recursion-in-ragu). The [chapter on recursion in Ragu](./ragu-recursion.md) lists them.

All of this applies to the Ragu revision at `3219e08`. Tachyon, which has not activated on mainnet and whose design is still changing, depends on this design through a [different Ragu revision](https://github.com/tachyon-zcash/tachyon/blob/7e502548db33845dbaacdc0efe905d1a3c45e626/crates/tachyon/Cargo.toml#L83).

## 13. Where this chapter leaves us

This chapter took the following steps:

1. A commitment's scalars and coordinates lie in different fields, so a circuit over the scalar field can fold values directly but cannot fold points directly.
2. Emulating the other field with limbs works but multiplies each operation's cost so much that, in our plain design, one point addition already exceeds the size of a Ragu circuit.
3. A 2-cycle of curves gives each field a curve whose points are native to it. Pallas and Vesta form such a cycle, and an anomalous single curve is not an option.
4. Each recursive step has two circuits, and each one folds the values of its own accumulator and the points of the other, which it does for the instances of the previous step.
5. A nested commitment places foreign data behind one point that the transcript's field can absorb.
6. Group operations on foreign points move to the other circuit as deferred operations, and staged traces with sum and overlap checks tie that circuit's wires to the nested commitment.
7. Only the primary circuit hashes. Challenges cross in a short form, and the primary circuit checks the secondary circuit's copy through a commitment on the curve that is native to it.
8. Every check in a step depends on the next step, and the decider has to finish both curves' claims at the end.

So far our accumulators have folded evaluation claims, but a proof also holds the revdot claims of [chapter 05](./polynomial-encoding.md). The [next chapter](./revdot-folding.md) folds those, and the split of this chapter applies to them too.
