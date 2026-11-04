# Polynomial Commitments

Ragu represents a prover's secret data as polynomials, and its verifier must check claims about those polynomials without receiving them. A polynomial with thousands of coefficients is too large to send in every recursive step, and sending it would also expose secret data. A polynomial commitment solves both problems by replacing the polynomial with one short value that the prover cannot later change.

This chapter builds the commitment Ragu uses. We start with a commitment to a vector, read a polynomial as its vector of coefficients, and then rewrite an evaluation $p(x) = y$ as a statement about an inner product. The next chapter proves that statement with a short argument.

## 1. What a polynomial commitment provides

Suppose a prover holds a polynomial $p$ and a verifier holds nothing. The two parties want to run the following exchange:

1. The prover sends a short commitment $C$ to $p$.
2. The verifier later picks a point $x$.
3. The prover sends $y = p(x)$ along with a proof that $y$ is correct for the polynomial behind $C$.

The verifier gets evidence about $p$ from one evaluation because, as Section 9 shows, two different low-degree polynomials rarely agree at a random point. This exchange only works if the prover fixes $p$ before seeing $x$, so the commitment must be **binding**: the prover must not be able to open $C$ to a second polynomial. When $p$ contains secrets, the commitment should also be **hiding**, which means $C$ reveals nothing about $p$.

A hash of the coefficients is binding and short, which makes it a natural first candidate. Hashes have no algebraic structure, however, so the only way to prove something about $p$ from its hash is to run the entire hash computation inside a proof. Ragu's accumulation scheme also needs to combine commitments directly, and the hash of a sum has no relation to the hashes of its parts. Elliptic curve points provide the missing structure, because adding two commitments gives a commitment to the sum.

## 2. The toy curve

The curve groups used in real systems have about $2^{255}$ elements, which makes their arithmetic unreadable on a page. Every worked example on this site uses a much smaller curve instead:

$$E: y^2 = x^3 + 3 \quad \text{over } \F_{31}.$$

This curve has 43 points including the identity $\mathcal{O}$. Since 43 is prime, every point other than $\mathcal{O}$ generates the whole group, and scalars live in $\F_{43}$. Coordinates are therefore computed modulo 31, and scalars are computed modulo 43. The [curves appendix](./appendix-curves.md) lists the parameters.

![All 42 affine points of the toy curve in a 31 by 31 grid, with the generators G0 to G3, H, and U highlighted.](./manim/toy-curve-points.png)

We fix six points as public parameters. A real system derives such points by hashing, so that no one knows a relation among them. The next table picks points spaced across the $x$-coordinates instead, which keeps the example readable.

<!-- worked:generators -->

| Name | Point |
| --- | --- |
| $G_0$ | $(1,\,2)$ |
| $G_1$ | $(6,\,8)$ |
| $G_2$ | $(11,\,1)$ |
| $G_3$ | $(17,\,7)$ |
| $H$ | $(23,\,7)$ |
| $U$ | $(26,\,8)$ |

<!-- /worked:generators -->

The toy curve is deliberately insecure. Anyone can compute its discrete logs by counting, and Section 4 uses this weakness to show what goes wrong when a discrete log is known.

## 3. Committing to a vector

To commit to one scalar $a$, the prover could send $a \cdot G$ for a public generator $G$. Recovering $a$ from this point requires solving discrete log, and the prover cannot find a second scalar that produces the same point because the group has prime order and $a \cdot G$ determines $a$.

A vector needs more than this, since sending one point per entry would produce a commitment as long as the vector. Adding those points into one point keeps the size constant. If we used the same generator for every entry, the sum would be $(\sum_i a_i) \cdot G$, which depends only on the sum of the entries and loses their positions. A separate generator for each position avoids this collision. For $\v{a} \in \F_q^n$ and public generators $\v{G} = (G_0, \ldots, G_{n-1})$, this gives the **Pedersen vector commitment**

$$C = \dot{\v{a}}{\v{G}} = \sum_{i=0}^{n-1} a_i \cdot G_i.$$

The result is one curve point regardless of $n$. Here is the computation for a vector of four entries:

<!-- worked:commit -->

Take $\v{a} = (7, 2, 5, 3)$. Scalars live in $\F_{43}$, and each point sum follows the curve addition law over $\F_{31}$.

| Term | Point | Running sum |
| --- | --- | --- |
| $7\cdot G_0$ | $(25,\,29)$ | $(25,\,29)$ |
| $2\cdot G_1$ | $(20,\,6)$ | $(27,\,30)$ |
| $5\cdot G_2$ | $(14,\,22)$ | $(30,\,23)$ |
| $3\cdot G_3$ | $(14,\,9)$ | $(27,\,30)$ |

The commitment is the single point $C = (27,\,30)$.

<!-- /worked:commit -->

## 4. Why a prover cannot change the vector

Suppose a prover opens the same commitment to two different vectors $\v{a}$ and $\v{a}'$. Subtracting the two expressions for $C$ gives

$$\sum_{i=0}^{n-1} (a_i - a_i') \cdot G_i = \mathcal{O},$$

where at least one coefficient is nonzero. A second opening therefore requires a nontrivial linear relation among the generators. Finding such a relation is as hard as computing a discrete log between them, assuming nobody knows one in advance. Binding rests on exactly this assumption, called the **discrete log relation assumption**, and it is why real generators come from a hash rather than from multiples of a known point.

On the toy curve we can compute such a relation directly, so we can run the argument above in reverse to produce a forgery:

<!-- worked:forgery -->

Counting multiples of $G_0$ shows that $G_1 = 30\cdot G_0$, so $30\cdot G_0 - G_1 = \mathcal{O}$. Adding this relation to the honest vector gives $\v{a}' = (7+30,\ 2-1,\ 5,\ 3) = (37, 1, 5, 3)$ with scalars reduced modulo 43. Computing $\dot{\v{a}'}{\v{G}}$ gives $(27,\,30)$, the same point as $C$, so this commitment now has two valid openings.

<!-- /worked:forgery -->

A prover who can do this on a real curve could change the committed polynomial after seeing the challenge. On a curve of 255 bits, no known method finds such a relation in practice.

## 5. Adding commitments

Rearranging the sum in the definition of $C$ gives two identities that hold for any vectors $\v{a}, \v{b}$ and any scalar $r$:

$$\dot{\v{a}}{\v{G}} + \dot{\v{b}}{\v{G}} = \dot{\v{a} + \v{b}}{\v{G}}, \qquad r \cdot \dot{\v{a}}{\v{G}} = \dot{r\v{a}}{\v{G}}.$$

Pedersen commitments are therefore **linearly homomorphic**, meaning anyone can compute a commitment to a linear combination of vectors from the commitments alone, without seeing the vectors. The toy curve confirms both identities:

<!-- worked:homomorphism -->

With $\v{b} = (3, 1, 8, 4)$, the commitment is $C_b = (6,\,23)$. Adding points gives $C + C_b = (5,\,29)$. Committing directly to the sum $\v{a} + \v{b} = (10, 3, 13, 7)$ gives $(5,\,29)$, the same point. Scaling works the same way: $6\cdot C = (11,\,30)$, and committing to $6\v{a} = (42, 12, 30, 18)$ gives $(11,\,30)$.

<!-- /worked:homomorphism -->

Much of the later construction depends on this property. Batched openings and accumulation both replace many committed polynomials with one random linear combination, and the verifier can compute the combined commitment using only group operations.

## 6. Hiding the vector

The commitment above is deterministic, so anyone who can guess $\v{a}$ can recompute $C$ and test the guess. This matters whenever the vector comes from a small set of likely values. Adding a term with a random **blinding factor** $\gamma$ and one more generator $H$ prevents this test:

$$\bar{C} = \dot{\v{a}}{\v{G}} + \gamma \cdot H.$$

For each candidate vector, some value of $\gamma$ produces any given point, so $\bar{C}$ alone gives no information about $\v{a}$. Binding still holds under the same assumption once $H$ joins the list of generators, and the identities from Section 5 still hold if the blinding factors combine in the same way as the vectors.

<!-- worked:hiding -->

Committing to $\v{a}$ with blinding factors $\gamma = 17$ and $\gamma = 29$ gives $(5,\,29)$ and $(18,\,21)$. Both differ from the unblinded $C = (27,\,30)$, and without the blinding factor an observer cannot test a guessed vector against either point.

<!-- /worked:hiding -->

::: warning The Ragu Book and the code differ here
The [Ragu Book's NARK chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/nark.md) describes hiding commitments with blinding factors. The [IPA module](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/ipa/mod.rs#L1-L16) at commit `3219e08` states that "Pedersen blinding with generator `W` is omitted for now because compression currently proves unblinded relations", and its `commit` function has no blinding term. This site reads the book as the intended design and the code as the current state of the implementation. The authors have not confirmed this reading.
:::

## 7. Committing to a polynomial

A polynomial of degree less than $n$ is determined by its coefficients, which gives a direct route from vectors to polynomials:

$$p(X) = \sum_{i=0}^{n-1} a_i X^i \quad\longleftrightarrow\quad \v{a} = (a_0, \ldots, a_{n-1}).$$

A commitment to $p$ is the Pedersen commitment to $\v{a}$. Adding commitments now corresponds to adding polynomials, because adding polynomials adds their coefficients. The degree bound comes from the number of generators, so a set of $n$ generators can commit only to polynomials of degree below $n$. The argument in the next chapter halves the vector in each round, which is why $n$ is a power of two.

## 8. Writing an evaluation as an inner product

Next we need a way to express $p(x) = y$ in terms of the committed vector. Expanding the definition of $p$ at a point $x$ gives

$$p(x) = \sum_{i=0}^{n-1} a_i x^i = \dot{\v{a}}{\v{x^n}}, \qquad \text{where } \v{x^n} = (1, x, x^2, \ldots, x^{n-1}).$$

An evaluation is therefore an inner product between the secret coefficient vector and a public vector, since anyone can compute the powers of $x$. This turns the evaluation claim into a linear statement about $\v{a}$.

<!-- worked:evaluation -->

Let $p(X) = 7 + 2X + 5X^2 + 3X^3$ over $\F_{43}$, whose coefficient vector is the $\v{a}$ from Section 3, and take $x = 9$.

| $i$ | $a_i$ | $x^i$ | $a_i x^i$ |
| --- | --- | --- | --- |
| 0 | 7 | 1 | 7 |
| 1 | 2 | 9 | 18 |
| 2 | 5 | 38 | 18 |
| 3 | 3 | 41 | 37 |

The last column sums to $y = 37$ modulo 43. Direct substitution into $p$ gives $p(9) = 37$, the same value.

<!-- /worked:evaluation -->

## 9. Combining the commitment and the claim

The prover must now show two facts about one vector at once: $\v{a}$ opens the commitment $C$, and $\dot{\v{a}}{\v{x^n}} = y$. We can package both facts into a single point. Taking the extra generator $U$, the prover and verifier both compute

$$P = C + y \cdot U,$$

and the prover claims to know $\v{a}$ satisfying

$$P = \dot{\v{a}}{\v{G}} + \dot{\v{a}}{\v{x^n}} \cdot U.$$

This form works because $P$ is a Pedersen commitment to the $n + 1$ entries $(a_0, \ldots, a_{n-1}, y)$ under the generators $(G_0, \ldots, G_{n-1}, U)$. The binding argument from Section 4 now applies to the longer list. If the last entry is anything other than the true inner product, the prover must know a relation among these generators, including $U$. That is why $U$ must have no known relation to $\v{G}$.

<!-- worked:claim -->

The statement point is $P = C + 37\cdot U = (5,\,29)$. Treating it as a five-entry commitment to $(7, 2, 5, 3,\ 37)$ under the generators $(G_0, G_1, G_2, G_3, U)$ gives $(5,\,29)$, the same point. A prover claiming $y = 38$ instead has the statement point $C + 38\cdot U = (1,\,29)$, which does not match the honest computation from the coefficients.

<!-- /worked:claim -->

The verifier also has to choose $x$ after the prover commits. The difference between two distinct polynomials of degree at most $d$ is a nonzero polynomial with at most $d$ roots, so the two polynomials agree on at most $d$ points. This count is the one-variable case of the **Schwartz–Zippel lemma**. A prover who commits to one polynomial and hopes it matches a different one at $x$ has at most a $d / |\F_q|$ chance of success.

<!-- worked:agreement -->

Take the different polynomial $q(X) = p(X) + 2(X-1)(X-2)(X-3) = 38 + 24X + 36X^2 + 5X^3$. Evaluating $p$ and $q$ at all 43 points of $\F_{43}$ finds agreement only at $x \in \{1, 2, 3\}$. A uniformly random challenge therefore misses the difference with probability $3/43$, which is the Schwartz–Zippel bound for degree 3. On a curve the size of Pallas, the same bound is below $2^{-240}$ for any polynomial of the degree Ragu uses.

<!-- /worked:agreement -->

If the prover revealed $\v{a}$ at this point, the verifier could check the equation for $P$ directly. That check would confirm the claim, but it would send all $n$ coefficients, which removes the benefit of the commitment. The next chapter replaces this reveal with an argument with about $2\log_2 n$ group elements. We can now state exactly what that argument must prove:

$$\text{given } \v{G},\ U,\ P,\ x, \text{ the prover knows } \v{a} \text{ such that } P = \dot{\v{a}}{\v{G}} + \dot{\v{a}}{\v{x^n}} \cdot U.$$

## 10. Comparison with KZG

The most widely known alternative is **KZG**, which takes a different route to the same interface. KZG requires a setup that publishes the points $G, \tau G, \tau^2 G, \ldots$ for a secret scalar $\tau$, and the commitment to $p$ is the point $p(\tau) \cdot G$. To open at $x$, the prover sends a commitment to the quotient $(p(X) - y)/(X - x)$, which is a polynomial exactly when $p(x) = y$. The verifier checks this relation at $\tau$ with a pairing, a special bilinear map between curve groups.

KZG proofs are one group element, and their verification cost does not depend on $n$. In exchange, KZG requires pairing-friendly curves and a trusted setup, because anyone who learns $\tau$ can forge openings. Ragu avoids a trusted setup and uses the Pasta curves, which Zcash already deploys in Orchard. The cost of that choice is a verifier whose work grows linearly with $n$, and most of the recursion chapters exist to manage this cost.

## 11. The commitment in Ragu

The core of Ragu's commitment function matches the definition from Section 3. The function asserts that the coefficient count is exactly $n = 2^k$ and then runs a multi-scalar multiplication over the generators, here from [`crates/ragu_pcd/src/ipa/mod.rs`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/ipa/mod.rs#L116-L125) at commit `3219e08`:

```rust
pub fn commit<B: SelectableBackend>(&self, poly: &[C::Scalar]) -> C::Projective {
    assert_eq!(poly.len(), self.n as usize);
    msm::multiexp::<C, B>(poly, &self.g)
}
```

::: warning Reconstructed from code at commit 3219e08, not confirmed by the authors
The Ragu Book writes the opening relation as in Section 9, with a generator $Q$ in place of $U$. The [prover code](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/ipa/prover.rs#L65-L73), adapted from `halo2`, first adds a random multiple of a masking polynomial's commitment and subtracts the claimed value from the constant coefficient, then proves that the resulting polynomial has a root at $x$. Its generator $U$ enters during the rounds of the argument. Both forms establish the same evaluation claim, and we compare them step by step in the next chapter.
:::

## 12. Where this chapter leaves us

A prover can now commit to a polynomial with one curve point and add such commitments without opening them. An evaluation claim has become one equation in a single statement point $P$, with the secret coefficients appearing in both terms. Nothing yet makes the proof of that equation short, and the next chapter supplies that step by halving the vector repeatedly.
