# Arithmetization

A proof system cannot directly reason about a program. Its algebra works with field elements, so the first step in any proof is to rewrite the statement as equations over a field. This rewriting is called **arithmetization**, and every later step depends on its output.

This chapter takes one small computation through the whole process. We start with ordinary arithmetic, express it as a list of multiplications and linear equations, and then compress all of those equations into a single equation with one secret vector. That final equation is the form Ragu proves, and the next chapter turns it into a statement about polynomials.

## 1. What arithmetization produces

We continue with the running example from the [previous chapter](./statements-and-challenges.md#_1-statements-instances-and-witnesses):

> I know a number $x$ such that $x^3 + x + 5 = 35$.

In the terms of that chapter, 35 is the instance and $x$ is the witness. Arithmetization has to produce a fixed set of equations, determined only by the statement's structure, such that a witness satisfies the equations exactly when the statement is true.

All arithmetic in this chapter happens in $\F_{43}$, the scalar field of the toy curve from the [curves appendix](./appendix-curves.md). The statement is an equation in this field, though the small values in our example make it look like ordinary arithmetic.

The equations cannot depend on the secret value, because the verifier must know them in advance. A program with an `if` branch therefore has to compute both branches and select one arithmetically. For example, the equation $s(s - 1) = 0$ restricts a value $s$ to a bit, because only 0 and 1 make the product zero, and the expression $s \cdot p_1 + (1 - s) \cdot p_0$ then selects $p_1$ when $s = 1$ and $p_0$ when $s = 0$.

<!-- worked:bit-select -->

Take $p_1 = 10$ and $p_0 = 20$. The bit $s = 1$ satisfies $1 \cdot 0 = 0$ and selects $10$, and $s = 0$ satisfies $0 \cdot (-1) = 0$ and selects $20$. The value $s = 2$ fails the bit equation, because $2 \cdot 1 = 2$, which is not 0. Without that equation, $s = 2$ would give $2 \cdot 10 + (1 - 2) \cdot 20 = 0$ modulo 43, which is neither of the two values.

<!-- /worked:bit-select -->

Hash functions and signature checks reduce to field equations in the same way, with many more of them.

## 2. Flattening a computation

The expression $x^3 + x + 5$ contains several operations at once, so we first split it into steps that each perform one operation. Each intermediate result gets its own name:

<!-- worked:flatten -->

| Step | Operation | Value for $x = 3$ |
| --- | --- | --- |
| 1 | $w_1 = x \cdot x$ | 9 |
| 2 | $w_2 = w_1 \cdot x$ | 27 |
| 3 | $w_2 + x + 5$ | 35 |

<!-- /worked:flatten -->

The steps have different costs in a proof system. Step 3 only adds values we already have, so it can become one row of coefficients in a linear equation, and it needs no new values. Steps 1 and 2 multiply two unknowns, which no linear equation can express, so each needs its own gate with its own wires (Section 3 defines both). The witness grows in proportion to the number of gates $n$, and later chapters show that the prover's work and the size of the commitments grow with it. A proof system therefore counts multiplications as its main cost, and we keep their number small.

## 3. Gates

Each multiplication becomes a **gate**. A circuit with $n$ gates uses three vectors $\v{a}, \v{b}, \v{c} \in \F_q^n$, and gate $i$ requires

$$a_i \cdot b_i = c_i.$$

The entries of these vectors are called **wires**. Together they form the witness, which also goes by the name **trace** because it records one execution of the computation. In vector form, all the gates together say $\v{a} \circ \v{b} = \v{c}$, where $\circ$ is the entrywise product.

Our computation has two multiplications, so $n = 2$:

<!-- worked:gates -->

| Gate $i$ | $a_i$ | $b_i$ | $c_i$ | Check |
| --- | --- | --- | --- | --- |
| 0 | 3 | 3 | 9 | $3 \cdot 3 = 9$ |
| 1 | 9 | 3 | 27 | $9 \cdot 3 = 27$ |

<!-- /worked:gates -->

## 4. Linear constraints

The gates alone are not enough, because they treat every wire as independent. Nothing yet says that the $a_1$ of gate 1 is the output $c_0$ of gate 0, or that the same $x$ is used everywhere. A separate set of **linear constraints** connects the wires and ties them to the instance. Constraint $j$ has the form

$$\sum_{i=0}^{n-1} u_{j,i}\, a_i + \sum_{i=0}^{n-1} v_{j,i}\, b_i + \sum_{i=0}^{n-1} w_{j,i}\, c_i = k_j,$$

which we can write with inner products as

$$\dot{\v{u}_j}{\v{a}} + \dot{\v{v}_j}{\v{b}} + \dot{\v{w}_j}{\v{c}} = k_j.$$

The vectors $\v{u}_j, \v{v}_j, \v{w}_j$ are public and describe the circuit. The vector $\v{k}$ is the **public input vector**, which holds the instance. The bold $\v{w}_j$ is the coefficient vector of constraint $j$, and it has nothing to do with the intermediate values $w_1$ and $w_2$ of Section 2, which this circuit stores as the wires $c_0$ and $c_1$.

Our statement needs four constraints. The first three connect wires, and the last one checks the output. It moves the constant 5 to the right side, which gives the target value $35 - 5$:

<!-- worked:constraints -->

| $j$ | Constraint | $\v{u}_j$ | $\v{v}_j$ | $\v{w}_j$ | $k_j$ |
| --- | --- | --- | --- | --- | --- |
| 0 | $a_0 - b_0 = 0$ | $(1, 0)$ | $(-1, 0)$ | $(0, 0)$ | 0 |
| 1 | $a_1 - c_0 = 0$ | $(0, 1)$ | $(0, 0)$ | $(-1, 0)$ | 0 |
| 2 | $b_1 - a_0 = 0$ | $(-1, 0)$ | $(0, 1)$ | $(0, 0)$ | 0 |
| 3 | $c_1 + a_0 = 30$ | $(1, 0)$ | $(0, 0)$ | $(0, 1)$ | 30 |

<!-- /worked:constraints -->

Step 3 from Section 2 has disappeared into constraint 3 without adding a gate, as Section 2 predicted.

We write $m$ for the number of constraint rows. Later we will pad the list with rows of zeros up to a length that Section 8 fixes. A zero row says $0 = 0$, which every witness satisfies, so padding changes nothing about which witnesses pass.

The gates and constraints together reject false statements:

<!-- worked:wrong-input -->

Try $x = 4$ instead. Filling in the gates gives $\v{a} = (4, 16)$, $\v{b} = (4, 4)$ and $\v{c} = (16, 21)$, with $4 \cdot 4 = 16$ and $16 \cdot 4 = 21$ modulo 43. Both gates and the first three constraints hold. The last constraint gives $c_1 + a_0 = 25$, which is not 30, so this witness is rejected.

<!-- /worked:wrong-input -->

## 5. Reducing the gates to one equation

The verifier now faces $n$ gate equations and $m$ constraints, and a real circuit has thousands of each. A proof that handled every equation separately would be enormous, so we want to replace them all with one equation that still fails if any of them fails.

Let $e_i = a_i b_i - c_i$ be the error of gate $i$. The previous chapter's [random linear combination](./statements-and-challenges.md#powers-of-one-challenge) does this job, with the errors as the claims and the powers of a random value $z$ as the weights:

$$\sum_{i=0}^{n-1} z^i e_i = \sum_{i=0}^{n-1} z^i (a_i b_i - c_i).$$

This sum is a polynomial in $z$ with the errors as its coefficients, so it is 0 for every $z$ when all the gates hold. If any gate fails, the bound from that section applies, because the prover must fix the witness before seeing $z$. The sum has degree at most $n - 1$, so a uniformly random $z$ hides the failure with probability at most $(n - 1)/|\F_q|$.

<!-- worked:gate-sum -->

For the honest witness both gate errors are 0, so the sum is 0 for every $z$. Now take a dishonest witness with $\v{a} = (3, 8)$, $\v{b} = (3, 3)$ and $\v{c} = (8, 27)$. It satisfies all the linear constraints above, but its gate errors are $a_0 b_0 - c_0 = 1$ and $a_1 b_1 - c_1 = 40$ modulo 43. At $z = 5$ the sum is $1 + 5 \cdot 40 = 29$, which exposes the error. Checking all 43 values of $z$ finds 1 value that hides it, $z = 29$, the root of this degree-1 polynomial.

<!-- /worked:gate-sum -->

On a field of about $2^{255}$ elements, this probability is negligible. We have traded certainty for an overwhelming probability, in exchange for checking only one equation.

## 6. Reducing the constraints to one equation

The constraints collapse in the same way, using a second random value $y$. We multiply constraint $j$ by $y^j$ and add all of them. Because inner products are linear, the powers of $y$ can move inside the inner products and attach to the coefficient vectors, which turns the weighted sum into one linear equation in the witness:

$$\dot{\v{u}(y)}{\v{a}} + \dot{\v{v}(y)}{\v{b}} + \dot{\v{w}(y)}{\v{c}} = \dot{\v{k}}{\v{y^{m}}}.$$

Here $\v{u}(y) = \sum_j y^j \v{u}_j$, and $\v{v}(y)$ and $\v{w}(y)$ are built the same way from the $\v{v}_j$ and $\v{w}_j$. The vector $\v{y^{m}} = (1, y, \ldots, y^{m-1})$ holds the weights. The combined vectors are public once $y$ is known. Our circuit has $m = 4$ real rows, and any zero rows added later contribute nothing to either side.

::: details The weighted sum before rearranging

Multiplying constraint $j$ by $y^j$ and adding gives

$$\sum_{j=0}^{m-1} y^j \Big( \dot{\v{u}_j}{\v{a}} + \dot{\v{v}_j}{\v{b}} + \dot{\v{w}_j}{\v{c}} \Big) = \sum_{j=0}^{m-1} y^j k_j.$$

Linearity gives $\sum_j y^j \dot{\v{u}_j}{\v{a}} = \dot{\sum_j y^j \v{u}_j}{\v{a}} = \dot{\v{u}(y)}{\v{a}}$, and the same holds for the $\v{b}$ and $\v{c}$ terms. The right side is $\dot{\v{k}}{\v{y^{m}}}$ by the definition of the inner product.

:::

<!-- worked:constraint-sum -->

Each entry of a combined vector collects one column of the constraint table, with row $j$ weighted by $y^j$. For example, the coefficient of $a_0$ is $1$, $-1$ and $1$ in rows 0, 2 and 3, so the first entry of $\v{u}(y)$ is $1 - y^2 + y^3$. Reading every column this way gives

$$\v{u}(y) = (1 - y^2 + y^3, y), \qquad \v{v}(y) = (-1, y^2), \qquad \v{w}(y) = (-y, y^3).$$

At $y = 7$, the combined vectors are $\v{u}(y) = (37, 7)$, $\v{v}(y) = (42, 6)$ and $\v{w}(y) = (36, 42)$. The left side for the honest witness is $2 + 15 + 39 = 13$ modulo 43. The right side is $7^3 \cdot 30 = 13$, because only $k_3$ is nonzero.

<!-- /worked:constraint-sum -->

We now have two equations, one quadratic in the witness and one linear. A verifier who could see the witness could check both directly, but the verifier will not see it. Instead, the next chapters have the prover commit to the witness as a single polynomial, and a commitment to one polynomial is only useful if every check reads its witness data from that one polynomial. Those chapters also give the verifier a way to check one coefficient of a product of two committed polynomials without seeing either polynomial. So our task for the rest of this chapter is to put all of $\v{a}$, $\v{b}$ and $\v{c}$ into one vector, and to write both checks as a single claim of the form "this coefficient of a product equals this public value".

## 7. Reading one coefficient of a product

We first need to see which operation on two coefficient vectors produces one coefficient of their product. Take polynomials $f$ and $g$ with coefficient vectors $\v{f}, \v{g} \in \F_q^L$. The coefficient of $X^{\ell}$ in the product $f(X)g(X)$ is the sum of $f_i g_j$ over all pairs with $i + j = \ell$. For the middle exponent $\ell = L - 1$, this sum is

$$\sum_{i=0}^{L-1} f_i\, g_{L-1-i}.$$

Each entry of $\v{f}$ meets the entry of $\v{g}$ at the mirrored position. This is the inner product of $\v{f}$ with the reversal $\rv{g}$ of $\v{g}$, which is called the **revdot product**:

$$\revdot{\v{f}}{\v{g}} = \dot{\v{f}}{\rv{g}} = \sum_{i=0}^{L-1} f_i\, g_{L-1-i}.$$

<!-- worked:product -->

Let $f(X) = 1 + 2X + 3X^2 + 4X^3$ and $g(X) = 5 + 6X + 7X^2 + 8X^3$ over $\F_{43}$. The coefficient of $X^3$ in $f(X)g(X)$ collects every pair of exponents that adds to 3, which gives $1 \cdot 8 + 2 \cdot 7 + 3 \cdot 6 + 4 \cdot 5 = 17$ modulo 43. The revdot product computes the same sum, since $\rv{g} = (8, 7, 6, 5)$ and $\dot{\v{f}}{\rv{g}} = 17$. The full product has coefficients $(5, 16, 34, 17, 18, 9, 32)$, and the entry for $X^3$ is the one in the middle.

<!-- /worked:product -->

So a claim about a revdot product is a claim about one coefficient of a polynomial product. This link is why Ragu writes its checks as revdot products, and our goal for the rest of this chapter is to express both equations as one revdot product involving the witness vector.

## 8. Arranging the witness

Call the single witness vector $\v{r}$. The two kinds of term put different demands on it. The gate products $a_i b_i$ are quadratic, so they have to come from a revdot product of $\v{r}$ with itself. A revdot product over length $L$ pairs position $\ell$ with position $L - 1 - \ell$, so $a_i$ and $b_i$ must sit at mirrored positions. The linear terms are different. Sections 10 and 11 will read each wire through a revdot product of $\v{r}$ with a public vector, and that only works for wires stored in $\v{r}$. So $\v{c}$ must also be in $\v{r}$, even though no product uses it.

A first attempt puts the three blocks side by side as $\v{c} \| \rv{a} \| \v{b}$, a vector of length $3n$. Every position in a revdot product has a partner, and the $\v{c}$ entries get the wrong ones:

<!-- worked:three-blocks -->

With $n = 2$, the arrangement $\v{c} \| \rv{a} \| \v{b}$ gives the six entries $(c_0, c_1, a_1, a_0, b_0, b_1) = (9, 27, 9, 3, 3, 3)$. The partner of position $\ell$ is now $5 - \ell$, so $c_0$ pairs with $b_1$, $c_1$ pairs with $b_0$, and $a_1$ pairs with $a_0$. The revdot product is $2(9 \cdot 3 + 27 \cdot 3 + 9 \cdot 3) = 12$ modulo 43, while $2\dot{\v{a}}{\v{b}} = 29$. No product $a_i b_i$ appears, and stray products such as $c_0 b_1$ take their place.

<!-- /worked:three-blocks -->

Rearranging the three blocks does not help either. Whatever the order, the $\v{c}$ entries end up paired with each other and add products $c_i c_j$ that no gate asked for, and nothing later in the chapter can cancel them. The box below gives the argument.

::: details Why no order of three blocks works

The $\v{a}$ and $\v{b}$ blocks must be mirrors of each other, and together they fill $2n$ positions placed symmetrically about the center. Partnering is symmetric, so once the $\v{a}$ and $\v{b}$ entries pair with each other, the $n$ entries of $\v{c}$ can only pair among themselves, and the revdot product picks up products $c_i c_j$ that no gate asked for. These terms are quadratic in the witness. The public vectors of Sections 10 and 11 can only add terms that are linear in the witness, so nothing later can cancel them.

:::

A fourth block of $n$ entries solves this, because it gives each $c_i$ a partner that the honest prover sets to zero. Call this block $\v{d}$. The vector has length $4n$ and four blocks of length $n$:

$$\v{r} = \v{c} \,\|\, \rv{a} \,\|\, \v{b} \,\|\, \rv{d}.$$

Reversing the $\v{a}$ block places $a_i$ at position $2n - 1 - i$, and $b_i$ sits at position $2n + i$. These two positions add up to $4n - 1$, so they are partners. Reversing the $\v{d}$ block in the same way places $d_i$ at position $4n - 1 - i$, the partner of $c_i$ at position $i$. A vector with this arrangement is called a **structured vector**.

An honest prover sets $\v{d} = \v{0}$. A dishonest prover may put other values there, and Section 12 shows that the final equation forces every product $c_i d_i$ to be zero, so this gains nothing.

With $n = 2$, the positions and their partners are:

<!-- worked:layout -->

| Position $\ell$ | Entry | Value | Partner position $7 - \ell$ | Partner entry |
| --- | --- | --- | --- | --- |
| 0 | $c_0$ | 9 | 7 | $d_0$ |
| 1 | $c_1$ | 27 | 6 | $d_1$ |
| 2 | $a_1$ | 9 | 5 | $b_1$ |
| 3 | $a_0$ | 3 | 4 | $b_0$ |
| 4 | $b_0$ | 3 | 3 | $a_0$ |
| 5 | $b_1$ | 3 | 2 | $a_1$ |
| 6 | $d_1$ | 0 | 1 | $c_1$ |
| 7 | $d_0$ | 0 | 0 | $c_0$ |

<!-- /worked:layout -->

![Eight cells labeled c0, c1, a1, a0, b0, b1, d1, d0, with arcs joining position 3 to 4, 2 to 5, 1 to 6, and 0 to 7.](./manim/revdot-pairing.png)

Each product appears twice in the revdot sum, once from each end of the pair. With $\v{d} = \v{0}$, the $c$ wires contribute nothing, so

$$\revdot{\v{r}}{\v{r}} = 2\sum_{i=0}^{n-1} a_i b_i.$$

<!-- worked:plain-revdot -->

For our witness, $\v{r} = (9, 27, 9, 3, 3, 3, 0, 0)$. Multiplying each entry by its partner and summing gives $\revdot{\v{r}}{\v{r}} = 29$, and $2\dot{\v{a}}{\v{b}} = 2(3 \cdot 3 + 9 \cdot 3) = 29$ modulo 43.

<!-- /worked:plain-revdot -->

Now that $\v{r}$ exists, we can fix the number of constraint rows. We set $m = 4n$, the length of $\v{r}$, and pad the constraint list with zero rows up to that length. Our circuit has four real rows, so it gets four rows of zeros, and $\v{k}$ gets four zero entries after $k_3$. From here on we write $\v{y^{4n}}$ for $\v{y^{m}}$.

::: details Why the padding length is 4n

Nothing in this chapter forces a particular value of $m$, so the padding length is a convention. Every vector we build from here on has length $4n$, and later chapters turn each one into a polynomial with $4n$ coefficients. The [chapter on wiring and the registry](./wiring-and-registry.md) shows that the constraint weights $y^j$ must also fit within $4n$ terms, because the wiring is committed with the same $4n$ generators as the witness. A circuit that needs more than $4n$ constraints therefore does not fit, and Section 13 records that Ragu imposes this limit.

:::

::: warning The Ragu Book's chapters arrange the witness differently
The Ragu Book's [core arithmetization chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/arithmetization.md) uses $\v{c} \| \rv{b} \| \v{a} \| \v{0}$, which swaps the roles of $\v{a}$ and $\v{b}$. Its [local arithmetization chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/local/arithmetization.md) uses the arrangement above, and the [wiring code](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/wiring/mod.rs#L13-L22) at commit `3219e08` matches it. The two arrangements give the same products, because $a_i b_i = b_i a_i$. This site uses the arrangement from the code.
:::

## 9. Weighting each gate

The sum $2\sum_i a_i b_i$ has lost track of which product belongs to which gate, so it cannot check the gates individually. Section 5 solved the same problem by giving each gate its own power of $z$, and we can build this weighting into the revdot product.

Multiply entry $\ell$ of the second vector by $z^\ell$. This operation is called **dilation**, and the result is $\v{r} \circ \v{z^{4n}}$, where $\v{z^{4n}} = (1, z, \ldots, z^{4n-1})$. Each product in the revdot sum now picks up a power of $z$ that depends on where its pair of partners sits in $\v{r}$. Since each gate's wires $a_i$ and $b_i$ sit at their own pair of positions, each gate picks up its own weight. Collecting the terms by gate gives

$$\revdot{\v{r}}{\v{r} \circ \v{z^{4n}}} = \sum_{i=0}^{n-1} a_i b_i \big( z^{2n-1-i} + z^{2n+i} \big) + \sum_{i=0}^{n-1} c_i d_i \big( z^{i} + z^{4n-1-i} \big).$$

Gate $i$ is weighted by $z^{2n-1-i} + z^{2n+i}$, and no other gate uses either of those powers. The second sum comes from the pairs $c_i, d_i$, and for an honest prover it vanishes because $\v{d} = \v{0}$.

<!-- worked:dilation -->

At $z = 5$, gate 0 gets the weight $z^3 + z^4 = 19$ and gate 1 gets $z^2 + z^5 = 11$. The products are $a_0 b_0 = 9$ and $a_1 b_1 = 27$, so the dilated revdot product is $9 \cdot 19 + 27 \cdot 11 = 38$ modulo 43.

<!-- /worked:dilation -->

::: details Grouping the terms by gate, with a term-by-term check

Writing out the dilated revdot product position by position gives

$$\revdot{\v{r}}{\v{r} \circ \v{z^{4n}}} = \sum_{\ell=0}^{4n-1} r_\ell\, r_{4n-1-\ell}\, z^{4n-1-\ell}.$$

Now we group the terms by gate. The wires $a_i$ and $b_i$ occupy positions $2n - 1 - i$ and $2n + i$. Taking $\ell = 2n - 1 - i$ produces $a_i b_i z^{2n + i}$, and taking $\ell = 2n + i$ produces $b_i a_i z^{2n - 1 - i}$. The pair of wires $c_i, d_i$ contributes in the same way at positions $i$ and $4n - 1 - i$, which gives the second sum with the weight $z^{i} + z^{4n-1-i}$.

The table computes the same value for our witness directly from the definition.

<!-- worked:dilation-table -->

At $z = 5$ the powers are $(1, 5, 25, 39, 23, 29, 16, 37)$, so $\v{r} \circ \v{z^{8}} = (9, 6, 10, 31, 26, 1, 0, 0)$. The table multiplies each entry of $\v{r}$ by its partner and by the power of $z$ at the partner position.

| $\ell$ | $r_\ell$ | $r_{7-\ell}$ | $z^{7-\ell}$ | Term |
| --- | --- | --- | --- | --- |
| 0 | 9 | 0 | 37 | 0 |
| 1 | 27 | 0 | 16 | 0 |
| 2 | 9 | 3 | 29 | 9 |
| 3 | 3 | 3 | 23 | 35 |
| 4 | 3 | 3 | 39 | 7 |
| 5 | 3 | 9 | 25 | 30 |
| 6 | 0 | 27 | 5 | 0 |
| 7 | 0 | 9 | 1 | 0 |

The last column sums to 38, the same value as the gate-by-gate formula.

<!-- /worked:dilation-table -->

:::

## 10. Subtracting the gate outputs

For an honest prover $\v{d} = \v{0}$, so the second sum of Section 9 drops out and the dilated revdot product is $\sum_i a_i b_i ( z^{2n-1-i} + z^{2n+i} )$. Section 12 brings the $c_i d_i$ terms back to handle a dishonest prover. This expression contains the products $a_i b_i$, but a gate check needs the differences $a_i b_i - c_i$. We therefore have to subtract $c_i$ with the same weight as its gate:

$$-\sum_{i=0}^{n-1} c_i \big( z^{2n-1-i} + z^{2n+i} \big).$$

This sum is linear in the witness, so it can be written as a revdot product of $\v{r}$ with a public vector $\v{t}$. The wire $c_i$ sits at position $i$, and its partner is position $4n - 1 - i$. Placing the desired coefficient at that partner position gives

$$t_{4n-1-i} = -\big( z^{2n-1-i} + z^{2n+i} \big) \quad \text{for } 0 \le i < n,$$

with all other entries of $\v{t}$ equal to zero. Adding the two revdot products and using linearity gives

$$\revdot{\v{r}}{\v{r} \circ \v{z^{4n}} + \v{t}} = \sum_{i=0}^{n-1} (a_i b_i - c_i) \big( z^{2n-1-i} + z^{2n+i} \big).$$

This expression is the gate check from Section 5 with different weights. It is zero for every $z$ when all the gates hold, and otherwise it is a nonzero polynomial in $z$.

<!-- worked:t-vector -->

At $z = 5$, the partner of $c_0$ is position 7 and the partner of $c_1$ is position 6. Using the gate weights from Section 9, $t_{7} = -(z^{3} + z^{4}) = -19 = 24$ and $t_{6} = -(z^{2} + z^{5}) = -11 = 32$ modulo 43, so $\v{t} = (0, 0, 0, 0, 0, 0, 32, 24)$. Then $\revdot{\v{r}}{\v{t}} = 5$, and adding the dilated term gives $38 + 5 = 0$ modulo 43, as it should for a witness that satisfies its gates.

<!-- /worked:t-vector -->

## 11. Encoding the constraints

The combined constraint equation from Section 6 is linear in the witness, so it fits the same pattern. We want a public vector $\v{s}$ such that $\revdot{\v{r}}{\v{s}}$ equals its left side. Each wire's coefficient goes at the partner of that wire's position:

| Wire | Position in $\v{r}$ | Coefficient | Position in $\v{s}$ |
| --- | --- | --- | --- |
| $a_i$ | $2n - 1 - i$ | $\v{u}(y)_i$ | $2n + i$ |
| $b_i$ | $2n + i$ | $\v{v}(y)_i$ | $2n - 1 - i$ |
| $c_i$ | $i$ | $\v{w}(y)_i$ | $4n - 1 - i$ |

Filling in these entries gives $\revdot{\v{r}}{\v{s}} = \dot{\v{k}}{\v{y^{4n}}}$ for a witness that satisfies the constraints.

<!-- worked:s-vector -->

At $y = 7$, placing the vectors from Section 6 at the partner positions gives $\v{s} = (0, 0, 6, 42, 37, 7, 42, 36)$, and $\revdot{\v{r}}{\v{s}} = 13$. This equals $\dot{\v{k}}{\v{y^{8}}} = 13$.

<!-- /worked:s-vector -->

The vector $\v{s}$ contains the whole circuit structure, compressed by $y$. The chapter on [wiring and the registry](./wiring-and-registry.md) studies how a verifier can check $\v{s}$ without computing it from scratch.

## 12. The consolidated equation

Both checks are now revdot products with the same left vector $\v{r}$. The revdot product is linear in its second argument, so we can add them into one equation:

$$\boxed{\revdot{\v{r}}{\v{r} \circ \v{z^{4n}} + \v{t} + \v{s}} = \dot{\v{k}}{\v{y^{4n}}}}$$

This is the output of arithmetization. It contains one secret vector, $\v{r}$. The notation hides where the challenges enter, so we list them. The challenge $z$ appears in the powers $\v{z^{4n}}$ and in $\v{t}$, whose entries are sums of powers of $z$. The challenge $y$ appears in $\v{s}$, which holds the combined constraint vectors $\v{u}(y)$, $\v{v}(y)$ and $\v{w}(y)$, and in the powers $\v{y^{4n}}$. Everything else is fixed by the circuit and the instance.

<!-- worked:combined -->

At $z = 5$ and $y = 7$, the combined right vector is $\v{r} \circ \v{z^{8}} + \v{t} + \v{s} = (9, 6, 16, 30, 20, 8, 31, 17)$. Its revdot product with $\v{r} = (9, 27, 9, 3, 3, 3, 0, 0)$ is 13, and $\dot{\v{k}}{\v{y^{8}}} = 13$. Checking the equation at all $43^2 = 1849$ pairs $(z, y)$ confirms that the honest witness passes at every pair.

<!-- /worked:combined -->

### Why a false witness fails

The argument has to cover every vector $\v{r}$ a prover might choose, including one with a nonzero $\v{d}$ block. Subtract the right side from the left side and treat the difference as a polynomial in the two variables $z$ and $y$. It has three parts, and each kind of error lands in its own set of monomials:

- the gate errors $a_i b_i - c_i$ appear with the middle powers of $z$, from $z^{n}$ through $z^{3n-1}$;
- the products $c_i d_i$, which Section 10 set aside by assuming $\v{d} = \v{0}$, appear with the outer powers $z^0$ through $z^{n-1}$ and $z^{3n}$ through $z^{4n-1}$;
- the constraint errors appear with powers of $y$ alone.

<!-- worked:exponents -->

For our circuit with $n = 2$, the gate part uses the powers $z^{2}$ through $z^{5}$, and the $\v{d}$ part uses $z^{0}$, $z^{1}$, $z^{6}$ and $z^{7}$.

<!-- /worked:exponents -->

Because the parts occupy different monomials, an error in one part cannot cancel an error in another. They overlap only in the constant term, and the box below shows that this overlap does no harm. So a witness with any failing gate, any nonzero product $c_i d_i$, or any failing constraint leaves a nonzero polynomial. That polynomial has total degree at most $4n - 1$. The verifier draws $z$ and $y$ independently and uniformly from $\F_q$, and the prover has to fix $\v{r}$ before seeing them, so a random pair passes with probability at most $(4n - 1)/|\F_q|$. This bound is the two-variable [Schwartz–Zippel lemma](./statements-and-challenges.md#_5-polynomials-in-several-variables) from the previous chapter.

::: details The three parts and why they cannot cancel

Restoring the products $c_i d_i$ in the dilated term and subtracting the right side from the left side splits the equation into three parts:

$$\underbrace{\sum_{i=0}^{n-1} (a_i b_i - c_i) \big( z^{2n-1-i} + z^{2n+i} \big)}_{E_g(z)} + \underbrace{\sum_{i=0}^{n-1} c_i d_i \big( z^{i} + z^{4n-1-i} \big)}_{E_d(z)} + \underbrace{\Big( \revdot{\v{r}}{\v{s}} - \dot{\v{k}}{\v{y^{4n}}} \Big)}_{E_c(y)} = 0.$$

The first part combines the dilated gate products with $\revdot{\v{r}}{\v{t}}$, as in Section 10. The last part is the constraint check of Section 6 written as $\sum_j y^j \epsilon_j$, where $\epsilon_j$ is the error of constraint $j$, its left side minus $k_j$. The vector $\v{d}$ appears only in the middle part, because $\v{t}$ and $\v{s}$ have zeros at the partner positions of $\v{d}$.

The gate part uses the powers $z^{n}$ through $z^{3n-1}$, since $2n - 1 - i$ runs from $2n - 1$ down to $n$ and $2n + i$ runs from $2n$ up to $3n - 1$. The $\v{d}$ part uses $z^0$ through $z^{n-1}$ (from $z^i$) and $z^{3n}$ through $z^{4n-1}$ (from $z^{4n-1-i}$). The constraint part contains only powers of $y$.

The gate part therefore shares no monomial with either of the others. The $\v{d}$ part and the constraint part share exactly one, the constant term $z^0 y^0$. The $\v{d}$ part contains it through the term $c_0 d_0 z^0$, and the constraint part contains it through $\epsilon_0$.

Suppose the whole left side is the zero polynomial. Then every monomial has coefficient zero. The coefficient of $z^{2n+i}$ is the gate error $a_i b_i - c_i$, so every gate holds. The coefficient of $z^{4n-1-i}$ is $c_i d_i$, so every product $c_i d_i$ is zero, and this includes $c_0 d_0$, the one product that also reaches the constant. With the first two parts gone, $E_c(y)$ must be the zero polynomial, so every constraint error $\epsilon_j$ is zero. An error of any kind therefore leaves a nonzero polynomial.

That nonzero polynomial has total degree at most $4n - 1$ in $(z, y)$, because its highest power of $z$ is $z^{4n-1}$, its highest power of $y$ is $y^{4n-1}$, and no monomial contains both variables.

:::

On the toy field we can count the exact number of passing challenges for several dishonest witnesses. The last one leaves the gates and constraints honest and puts a nonzero value in $\v{d}$:

<!-- worked:cheats -->

| Dishonest witness | $\v{a}$ | $\v{b}$ | $\v{c}$ | $\v{d}$ | Passing pairs $(z, y)$ | Fraction |
| --- | --- | --- | --- | --- | --- | --- |
| Gates fail, constraints hold | $(3, 8)$ | $(3, 3)$ | $(8, 27)$ | $(0, 0)$ | 172 of 1849 | 0.093 |
| Gates hold, last constraint fails | $(4, 16)$ | $(4, 4)$ | $(16, 21)$ | $(0, 0)$ | 43 of 1849 | 0.023 |
| Both fail | $(4, 8)$ | $(4, 4)$ | $(8, 21)$ | $(0, 0)$ | 40 of 1849 | 0.022 |
| Honest $\v{a}, \v{b}, \v{c}$, nonzero $\v{d}$ | $(3, 9)$ | $(3, 3)$ | $(9, 27)$ | $(1, 0)$ | 301 of 1849 | 0.163 |

The bound for this circuit is $(4n - 1)/|\F_q| = 7/43 \approx 0.163$, and no row exceeds it. Two of the counts can be predicted by hand. In the second row the gates hold and $\v{d} = \v{0}$, so only the constraint check can fail, and constraint 3 is the only one that fails, with error $-5$. The combined constraint check is then $-5y^3$, which is zero only at $y = 0$, and that one value of $y$ passes with all 43 values of $z$. The last row keeps the honest gates and constraints and sets $d_0 = 1$. Only the term $c_0 d_0 (1 + z^{7}) = 9(1 + z^7)$ survives, and it vanishes at the 7 values of $z$ with $z^7 = -1$, for any $y$. That gives $7 \cdot 43 = 301$ passing pairs, which reaches the bound exactly.

<!-- /worked:cheats -->

<!-- worked:large-field -->

Those rates are large only because the field has 43 elements. Take $n = 2^{11}$ gates on a 255-bit field, which has more than $2^{254}$ elements. The bound is then $(4n - 1)/|\F_q| < 2^{13}/2^{254} = 2^{-241}$, since $4n - 1 = 8191$ is below $2^{13}$.

<!-- /worked:large-field -->

The argument depends on the prover fixing $\v{r}$ before it learns $z$ and $y$. A prover who knew the challenges first could look for a vector that satisfies this one equation without satisfying the gates and constraints. The [chapter on polynomial commitments](./polynomial-commitments.md), two chapters ahead, provides the tool that fixes $\v{r}$ first.

## 13. The arithmetization in Ragu

::: warning Reconstructed from code at commit 3219e08, not confirmed by the authors
Our toy circuit sets $\v{d} = \v{0}$ and moves constants into $\v{k}$. Ragu's implementation differs in the following ways:

- **Four wires per gate.** The [local arithmetization chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/local/arithmetization.md) gives each gate the two equations $a_i b_i = c_i$ and $c_i d_i = 0$. Section 12 showed that the consolidated equation already enforces the second one, through the $\v{d}$ part of the dilated term. At a gate with $c_i = 0$, the wire $d_i$ is free to hold extra witness data.
- **A wire that holds the constant 1.** The [circuit setup code](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/raw.rs#L19-L33) reserves gate 0 as a system gate, with $d_0 = 1$ as the `ONE` wire and a random value in $a_0$, whose purpose [the chapter on the complete proof](./nark.md#_15-the-constant-wire) explains. Because $d_0 = 1$, the gate equation $c_0 d_0 = 0$ forces $c_0 = 0$, and $a_0 b_0 = c_0$ with a nonzero $a_0$ then forces $b_0 = 0$. A constraint ties $d_0$ to $k_0$, the first entry of the public input vector, and a [comment in the circuit code](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/lib.rs#L321-L323) says that the verifier sets $k_0 = 1$. Constants such as our 5 can then appear in constraints as multiples of `ONE`, instead of being moved to $\v{k}$.
- **At most $4n$ constraints.** The book's [local wiring chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/local/wiring.md?plain=1#L20-L27) states that a circuit has only $4n$ possible constraints, which is the padded length we chose in Section 8. The [chapter on wiring and the registry](./wiring-and-registry.md) explains the reason, which comes from the degree of the polynomial that holds the wiring.
- **Virtual wires.** Ragu's [`Driver` interface](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_core/src/drivers.rs#L299-L341) has `mul` for gates, `enforce_zero` for constraints, and `add` for a virtual wire, which is a named linear combination of existing wires. A virtual wire adds no gate, which matches the cost of addition we saw in Sections 2 and 4.

The core chapter of the Ragu Book describes the simpler form with $\v{d} = \v{0}$, and this chapter follows that form for its example.
:::

## 14. Comparison with R1CS and PLONK

Other proof systems make different choices at this stage. Two of them are worth knowing, and the first is needed for the next chapter.

**R1CS** (rank-1 constraint system) uses one vector $\v{w}$ containing the constant 1, the instance, and the witness. This bold $\v{w}$ is a third use of the letter, separate from the coefficient vectors $\v{w}_j$ of Section 4 and the intermediate values $w_1, w_2$ of Section 2, which appear here as entries of $\v{w}$. Three public matrices define the constraints:

$$A\v{w} \circ B\v{w} = C\v{w}.$$

Each row is one constraint that multiplies two linear combinations of $\v{w}$ and compares the result with a third. Our statement fits in three rows:

<!-- worked:r1cs -->

With $\v{w} = (1, 35, 3, 9, 27)$, holding the constant 1, the public output, $x$, $w_1$ and $w_2$, the three matrices are

$$A = \begin{bmatrix}0 & 0 & 1 & 0 & 0 \\ 0 & 0 & 0 & 1 & 0 \\ 5 & 0 & 1 & 0 & 1\end{bmatrix},\quad B = \begin{bmatrix}0 & 0 & 1 & 0 & 0 \\ 0 & 0 & 1 & 0 & 0 \\ 1 & 0 & 0 & 0 & 0\end{bmatrix},\quad C = \begin{bmatrix}0 & 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 0 & 1 \\ 0 & 1 & 0 & 0 & 0\end{bmatrix}.$$

The products are $A\v{w} = (3, 9, 35)$ and $B\v{w} = (3, 3, 1)$. Their entrywise product is $(9, 27, 35)$, which equals $C\v{w}$.

<!-- /worked:r1cs -->

R1CS and Ragu's system have the same expressive power, and each can be converted to the other with a linear increase in size.

::: details Converting between R1CS and Ragu's system

An R1CS row becomes one gate plus three linear constraints that set $a_i$, $b_i$ and $c_i$ equal to the row's three linear combinations. In the other direction, a gate becomes an R1CS row whose three combinations each select one wire, and a linear constraint becomes a row that multiplies its linear combination by the constant 1.

:::

R1CS merges the wiring into its multiplication rows, while Ragu's system keeps gates and linear constraints apart. The Ragu Book's [core arithmetization chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/arithmetization.md?plain=1#L22-L26) at commit `3219e08` calls this system Bootle16, after the [2016 paper by Bootle, Cerulli, Chaidos, Groth and Petit](https://eprint.iacr.org/2016/263) that introduced it. The separation is what gives the revdot form above its shape. The gates become one fixed revdot product of $\v{r}$ with its own dilation, the same for every circuit of size $n$, and all the circuit-specific wiring moves into the single public vector $\v{s}$.

**PLONK** uses gates with selectable coefficients, of the form $q_L a + q_R b + q_O c + q_M ab + q_C = 0$, and adds separate copy constraints to connect wires. Later variants add custom gates and lookup tables that reduce the number of gates for certain operations. Ragu [deliberately avoids these features](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/index.md). It uses a simple circuit model and splits large computations into many small circuits that communicate along the PCD tree.

## 15. Where this chapter leaves us

This chapter took the following steps:

1. A computation becomes a list of multiplication gates and linear constraints over a field.
2. Random powers of $z$ and $y$ reduce all gates and constraints to two equations, at the cost of a small failure probability.
3. A revdot product corresponds to one coefficient of a polynomial product.
4. A structured vector $\v{r}$ places each $a_i$ and $b_i$ at mirrored positions, and dilation by $z$ weights each gate separately.
5. The public vectors $\v{t}$ and $\v{s}$ add the gate outputs and the wiring, which gives one equation.

The prover still has to convince the verifier of this equation without revealing $\v{r}$. The next chapter starts from the R1CS form to derive the standard QAP reduction, and then uses Section 7 to reach a polynomial test for the consolidated equation.
