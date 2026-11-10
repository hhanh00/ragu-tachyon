# QAP and Polynomial Encoding

The [arithmetization chapter](./arithmetization.md) ended with two ways to write the same statement, a list of R1CS rows and Ragu's single consolidated equation. Neither form helps the verifier yet, because checking either one means looking at the whole witness. This chapter turns those equations into statements about polynomials, which a verifier can test at a single random point.

There are two routes, and we take them in order. The first is the **quadratic arithmetic program** (QAP), the standard reduction behind systems such as Groth16, which ends in a divisibility test with a quotient polynomial. The second is the route Ragu takes, which reads the claim from one coefficient of a product and needs no division. Ragu uses this second encoding where it needs a short proof. The [complete proof chapter](./nark.md#_3-choosing-how-to-check-the-revdot-product) also shows a cheaper check that gives up short proofs, and Section 16 explains when Ragu uses each. We run both routes on the statement $x^3 + x + 5 = 35$ over $\F_{43}$, the scalar field of the toy curve that the next chapter builds. Apart from a sketch of Groth16 in Section 8, no curve points appear in this chapter, because commitments come in the next one.

## 1. What polynomials provide

Suppose two polynomials of degree at most $d$ differ. Their difference is a nonzero polynomial of degree at most $d$, so it has at most $d$ roots, and the two polynomials agree on at most $d$ points. This is the one-variable case of the Schwartz–Zippel lemma from [Statements and Challenges](./statements-and-challenges.md#testing-at-a-random-point). So a check at one random point says something about every coefficient at once, and a verifier can learn whether two large polynomials are equal without reading either of them.

To use this fact, we have to express "all the constraints hold" as an equality of polynomials. Each route does this differently. A QAP assigns each constraint row to its own point of the field, so a true statement makes a polynomial vanish at all of those points. Ragu has already merged its constraints into one scalar equation, so it only has to place that scalar where a verifier can reach it.

Both routes also need a way for the verifier to learn the value of a polynomial it does not hold. In a deployed system this comes from a polynomial commitment, which the [next chapter](./polynomial-commitments.md) builds. To keep the reasoning of this chapter separate from the cryptography, we pretend for now that the verifier has an **oracle** for each polynomial the prover sends. An oracle is a black box that fixes a polynomial at the moment the prover sends it, and afterward answers any question of the form "what is the value at this point?" The verifier never sees the coefficients, and the prover cannot change the polynomial once it has been sent. A protocol written this way is called a **polynomial interactive oracle proof**, or polynomial IOP.

Each oracle also has a **degree bound**, a maximum degree agreed in advance, and it refuses any polynomial above that degree. The bound is what makes root counting useful, because the argument above only limits the number of roots when the degree is limited. The next example shows what goes wrong without a bound.

<!-- worked:no-bound -->

On $\F_{43}$, the polynomial $X^{42} - 1$ has degree 42. By Fermat's little theorem $a^{42} = 1$ for every nonzero $a$, so this polynomial is zero at all 42 nonzero points of the field. If a cheater's error could take this form, a check at a random nonzero point would never see it. With a degree bound of 7, which is the bound in the toy run of Section 14, the same error polynomial is not allowed, and any nonzero polynomial the prover can send is zero at no more than 7 of the 43 points.

<!-- /worked:no-bound -->

The commitment of the next chapter supplies this bound. Its public parameters contain a fixed number of curve points, one for each coefficient, so parameters with $N$ points can hold a polynomial with at most $N$ coefficients, which means degree at most $N - 1$. We take this capacity as a premise here, and the next chapter shows where it comes from. Each protocol below states the bounds it uses.

Three symbols need care in this chapter. In the arithmetization chapter, $x$ was the secret input, and we keep that meaning in Sections 2 to 7 when we write "the witness with $x = 3$". From Section 12 onward, $x$ names a random evaluation point instead, so there we call the witnesses "the witness with secret input 3" and "the false witness with secret input 4". The random point of the QAP test is called $\tau$. Finally, $\v{w}$ is the R1CS vector, and we write its entries in bold as $\v{w}_\ell$, so that they stay separate from the wires $w_1$ and $w_2$ of the flattened computation.

## 2. The R1CS starting point

We start from the R1CS form of our statement, as built in [Section 14 of the arithmetization chapter](./arithmetization.md#_14-comparison-with-r1cs-and-plonk). Three public matrices with $m$ rows define the constraints, and row $i$ requires

$$\Big(\sum_\ell A_{i\ell}\,\v{w}_\ell\Big)\Big(\sum_\ell B_{i\ell}\,\v{w}_\ell\Big) = \sum_\ell C_{i\ell}\,\v{w}_\ell.$$

Our statement has $m = 3$ rows, with the matrices from that chapter:

<!-- worked:r1cs-start -->

$$A = \begin{bmatrix}0 & 0 & 1 & 0 & 0 \\ 0 & 0 & 0 & 1 & 0 \\ 5 & 0 & 1 & 0 & 1\end{bmatrix},\quad B = \begin{bmatrix}0 & 0 & 1 & 0 & 0 \\ 0 & 0 & 1 & 0 & 0 \\ 1 & 0 & 0 & 0 & 0\end{bmatrix},\quad C = \begin{bmatrix}0 & 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 0 & 1 \\ 0 & 1 & 0 & 0 & 0\end{bmatrix},$$

with $\v{w} = (1, 35, 3, 9, 27)$ holding the constant 1, the public output, $x$, $w_1$ and $w_2$.

<!-- /worked:r1cs-start -->

These $m$ equations are what we have to compress. In a real circuit $m$ can be many thousands, so the verifier should not have to examine them one by one.

## 3. Interpolating the rows

We want one polynomial that carries all the rows. A polynomial can store one value at each point of the field, so we can give each row its own point. Fix a set of $m$ distinct points $D = \{\rho_0, \ldots, \rho_{m-1}\}$, called the **domain**, and let row $i$ live at $\rho_i$. Our example uses $D = \{1, 2, 3\}$.

The most direct idea is to interpolate the vector $A\v{w}$ itself, finding a polynomial whose value at $\rho_i$ is entry $i$ of $A\v{w}$. That polynomial would hold the right values, but nothing about it would show that it came from the matrix $A$ and a real witness. If the prover could hand over any polynomial as its $A(X)$, it could pick one that satisfies the final test without coming from any witness. Building $A(X)$ from fixed polynomials that describe the matrix gives a structure to check, namely that the prover's polynomial is a combination of those fixed pieces. The oracle model of Section 1 cannot check this structure by itself, because an oracle accepts any polynomial within its degree bound, and Section 8 shows how Groth16's setup makes it checkable. So we interpolate the matrix alone. Each column of $A$ belongs to one wire, so we build one polynomial per column:

$$A_\ell(\rho_i) = A_{i\ell} \quad \text{for every row } i.$$

The polynomials $B_\ell$ and $C_\ell$ come from the columns of $B$ and $C$ in the same way. Since $m$ points determine a unique polynomial of degree at most $m - 1$, these polynomials exist and depend only on the circuit.

To construct them, we first build a polynomial $L_i(X)$ for each domain point $\rho_i$ that equals 1 at that point and 0 at the others. These are the **Lagrange basis polynomials** for $D$. A column is then a sum of basis polynomials, each weighted by that column's entry for the row. For example, the column $(0, 0, 5)$ of $A$ becomes $5L_2(X)$, which is 0 at the points 1 and 2 and 5 at the point 3. The box below gives the formula for $L_i$ and works out the three basis polynomials of our domain.

::: details Building the Lagrange basis

A product of factors $(X - \rho_j)$ over all $j \neq i$ is zero at every other point, and dividing by its value at $\rho_i$ scales it to 1 there:

$$L_i(X) = \prod_{j \neq i} \frac{X - \rho_j}{\rho_i - \rho_j}.$$

For our domain these are

<!-- worked:lagrange -->

$$\begin{aligned}
L_0(X) &= \frac{(X-2)(X-3)}{(1-2)(1-3)} = \frac{X^2 - 5X + 6}{2} = 3 + 19X + 22X^2,\\
L_1(X) &= \frac{(X-1)(X-3)}{(2-1)(2-3)} = \frac{X^2 - 4X + 3}{-1} = 40 + 4X + 42X^2,\\
L_2(X) &= \frac{(X-1)(X-2)}{(3-1)(3-2)} = \frac{X^2 - 3X + 2}{2} = 1 + 20X + 22X^2.
\end{aligned}$$

Dividing by 2 modulo 43 means multiplying by 22, and dividing by $-1$ means negating. As a spot check, $L_0(1) = 1$, $L_0(2) = 0$ and $L_0(3) = 0$.

<!-- /worked:lagrange -->

Any column can now be written as a sum of basis polynomials, each weighted by that column's entry for the row:

$$A_\ell(X) = \sum_{i=0}^{m-1} A_{i\ell}\, L_i(X).$$

At $X = \rho_i$ only the term with $L_i$ survives, which gives $A_{i\ell}$ as required.

:::

The nonzero columns of our three matrices produce the following polynomials, and every column not listed is all zeros and gives the zero polynomial.

<!-- worked:columns -->

| Polynomial | Column entries | In the basis | Coefficients |
| --- | --- | --- | --- |
| $A_0$ | $(0, 0, 5)$ | $5L_2$ | $5 + 14X + 24X^2$ |
| $A_2$ | $(1, 0, 1)$ | $L_0 + L_2$ | $4 + 39X + X^2$ |
| $A_3$ | $(0, 1, 0)$ | $L_1$ | $40 + 4X + 42X^2$ |
| $A_4$ | $(0, 0, 1)$ | $L_2$ | $1 + 20X + 22X^2$ |
| $B_0$ | $(0, 0, 1)$ | $L_2$ | $1 + 20X + 22X^2$ |
| $B_2$ | $(1, 1, 0)$ | $L_0 + L_1$ | $23X + 21X^2$ |
| $C_1$ | $(0, 0, 1)$ | $L_2$ | $1 + 20X + 22X^2$ |
| $C_3$ | $(1, 0, 0)$ | $L_0$ | $3 + 19X + 22X^2$ |
| $C_4$ | $(0, 1, 0)$ | $L_1$ | $40 + 4X + 42X^2$ |

<!-- /worked:columns -->

## 4. Adding the witness

The column polynomials describe the circuit, so we now bring in the witness. Multiply each column polynomial by its wire value and add:

$$A(X) = \sum_\ell \v{w}_\ell\, A_\ell(X), \qquad B(X) = \sum_\ell \v{w}_\ell\, B_\ell(X), \qquad C(X) = \sum_\ell \v{w}_\ell\, C_\ell(X).$$

To see what these sums hold, evaluate $A(X)$ at a domain point and use the defining property of the column polynomials:

$$A(\rho_i) = \sum_\ell \v{w}_\ell\, A_\ell(\rho_i) = \sum_\ell \v{w}_\ell\, A_{i\ell} = (A\v{w})_i.$$

So $A(X)$ takes the value of row $i$ of $A\v{w}$ at the point $\rho_i$, and the same holds for $B$ and $C$. Row $i$ of the R1CS is therefore the equation $A(\rho_i)B(\rho_i) = C(\rho_i)$, and the $m$ rows hold exactly when this equation holds at all $m$ domain points.

<!-- worked:combine -->

For $\v{w} = (1, 35, 3, 9, 27)$, the sums come out as

$$\begin{aligned}
A(X) &= 17 + 19X + 10X^2,\\
B(X) &= 1 + 3X + 42X^2,\\
C(X) &= 24 + 33X + 38X^2.
\end{aligned}$$

| $\rho_i$ | $A(\rho_i)$ | $B(\rho_i)$ | $C(\rho_i)$ | $A(\rho_i)B(\rho_i) - C(\rho_i)$ |
| --- | --- | --- | --- | --- |
| 1 | 3 | 3 | 9 | 0 |
| 2 | 9 | 3 | 27 | 0 |
| 3 | 35 | 1 | 35 | 0 |

Read down, the columns for $A$, $B$ and $C$ are the vectors $A\v{w} = (3, 9, 35)$, $B\v{w} = (3, 3, 1)$ and $C\v{w} = (9, 27, 35)$, and the last column shows that every row of the R1CS holds.

<!-- /worked:combine -->

## 5. The vanishing polynomial and the quotient

Define $P(X) = A(X)B(X) - C(X)$. The rows hold exactly when $P$ is zero at every point of $D$. That is still $m$ separate facts, and a check at one random point would not capture them, because a random point is almost never in $D$. We need an equivalent statement that holds as an identity across the whole field.

The factor theorem provides it. If a polynomial is zero at $\rho$, then $X - \rho$ divides it. Since the points of $D$ are distinct, $P$ is zero on all of $D$ exactly when $P$ is divisible by the product of those factors. This product is the **vanishing polynomial** of the domain:

$$V(X) = \prod_{i=0}^{m-1} (X - \rho_i).$$

The rows therefore hold exactly when there is a polynomial $h(X)$, called the **quotient**, with

$$A(X)B(X) - C(X) = h(X)\,V(X).$$

The factors $A$ and $B$ each have degree at most $m - 1$, so $P$ has degree at most $2(m - 1)$. Since $V$ has degree $m$, the quotient has degree at most $m - 2$. The column polynomials and $V$ together make up the QAP. A witness satisfies the QAP when the quotient exists, and this equation is the polynomial form of the R1CS.

<!-- worked:p-poly -->

With $m = 3$ rows, the degree of $P$ is at most 4, and multiplying and subtracting gives $P(X) = 36 + 37X + 12X^2 + 11X^3 + 33X^4$. Substituting gives $P(1) = 0$, $P(2) = 0$ and $P(3) = 0$, even though the coefficients of $P$ are not zero.

<!-- /worked:p-poly -->

The next step divides $P$ by $V$. The division is exact, so the quotient exists, and it has degree $m - 2$, as predicted. The box shows the long division.

::: details Long division by V(X)

<!-- worked:division -->

Expanding the product gives $V(X) = (X-1)(X-2)(X-3) = X^3 - 6X^2 + 11X - 6$, which is $37 + 11X + 37X^2 + X^3$ modulo 43. Long division removes one leading term at a time:

| Current polynomial | Next term of $h$ | Subtract | Result |
| --- | --- | --- | --- |
| $36 + 37X + 12X^2 + 11X^3 + 33X^4$ | $33X$ | $17X + 19X^2 + 17X^3 + 33X^4$ | $36 + 20X + 36X^2 + 37X^3$ |
| $36 + 20X + 36X^2 + 37X^3$ | $37$ | $36 + 20X + 36X^2 + 37X^3$ | $0$ |

The last column ends at 0, so the division is exact and $h(X) = 37 + 33X$, which has degree $m - 2 = 1$ as predicted.

<!-- /worked:division -->

:::

## 6. Testing the identity at one point

The equation $P(X) = h(X)V(X)$ is now an equality of polynomials, so Section 1 applies. In oracle form, the prover sends oracles for $A$, $B$ and $C$ with degree bound $m - 1$, and an oracle for $h$ with degree bound $m - 2$. The verifier then picks a random $\tau$, queries the four oracles at $\tau$, computes $V(\tau)$ itself because $V$ is public, and compares $A(\tau)B(\tau) - C(\tau)$ with $h(\tau)V(\tau)$.

The degree bounds limit how often a false identity can pass. Both sides have degree at most $2(m-1)$, so two different sides agree on at most that many points, and the chance that a false identity passes at a random $\tau$ is at most $2(m - 1)/|\F_q|$.

::: details The degree count

The left side has degree at most $(m-1) + (m-1) = 2(m-1)$, because $A$ and $B$ each have degree at most $m - 1$ and $C$ has lower degree than their product. The right side has degree at most $(m - 2) + m = 2(m-1)$, from the bound on $h$ and the degree of $V$. So if the two sides are different polynomials, their difference has degree at most $2(m - 1)$, and it has at most that many roots.

:::

<!-- worked:qap-test -->

Take $\tau = 11$. The prover has already fixed its polynomials, so the two sides are

| Value | At $\tau$ |
| --- | --- |
| $A(\tau)$ | 17 |
| $B(\tau)$ | 42 |
| $C(\tau)$ | 40 |
| $A(\tau)B(\tau) - C(\tau)$ | 29 |
| $h(\tau)$ | 13 |
| $V(\tau)$ | 32 |
| $h(\tau)V(\tau)$ | 29 |

The fourth and last rows agree. Checking every one of the 43 values of $\tau$ confirms that the honest polynomials pass at all of them, as an identity should.

<!-- /worked:qap-test -->

This test replaces all $m$ rows with one comparison of field elements, because the domain and the vanishing polynomial packed the rows into a single identity.

## 7. Why a cheater's quotient does not exist

Take a statement the witness does not satisfy, and follow what happens to the quotient.

<!-- worked:no-quotient -->

Keep the public value 35 and try $x = 4$, which gives $\v{w} = (1, 35, 4, 16, 21)$. Now $A\v{w} = (4, 16, 30)$, $B\v{w} = (4, 4, 1)$ and $C\v{w} = (16, 21, 35)$. The first two rows hold, and the last gives $30 \cdot 1 = 30$ against 35. The polynomial built from this witness is $P'(X) = 17 + 12X + 3X^2 + 34X^3 + 20X^4$, with $P'(1) = 0$ and $P'(2) = 0$ but $P'(3) = 38$. Dividing by $V(X)$ leaves the quotient $25 + 20X$ and the remainder $38 + 29X + 19X^2$. The remainder is not zero, so no polynomial $h$ satisfies $P'(X) = h(X)V(X)$.

<!-- /worked:no-quotient -->

A failing row at $\rho_i$ means $P'(\rho_i) \neq 0$, while any multiple of $V$ is zero there. This mismatch is why no $h$ can work, whatever the prover tries. The prover can still send an oracle for some polynomial of degree at most 1 as its quotient and hope that the test at $\tau$ misses the difference. On the toy field we can count every such attempt. We leave the domain points out of the count, because $V$ is zero there and a test at such a point says nothing about the quotient. A real field has so many elements that a random $\tau$ lands in $D$ with negligible probability.

<!-- worked:guess-h -->

| Values of $\tau$ where the guess passes | Number of candidate quotients |
| --- | --- |
| 0 | 909 |
| 1 | 160 |
| 2 | 780 |

The table covers all $43^2 = 1849$ candidate polynomials $h$ of degree at most 1, each tried at the 40 values of $\tau$ outside the domain. No candidate passes at more than 2 of them, which is 2/40. Averaged over all candidates, a random guess passes at a rate of 1 in 43.

<!-- /worked:guess-h -->

The degree bound explains the maximum. A guess passes at $\tau$ exactly when $\tau$ is a root of the nonzero polynomial $P' - hV$, and the degree bounds limit how many roots that polynomial can have. Part of that budget is always used up inside the domain, which leaves the small number of passing points seen in the table. The box counts the roots.

::: details Counting the passing points

A guess passes at $\tau$ exactly when $P'(\tau) - h(\tau)V(\tau) = 0$, so the passing points are roots of $P' - hV$. This polynomial is nonzero, because $P'$ is not a multiple of $V$, and the degree bounds limit its degree.

<!-- worked:guess-h-bound -->

Here $P'$ has degree 4 and $hV$ has degree at most 4, so $P' - hV$ has degree at most 4 and at most 4 roots. Some of those roots are always spent inside the domain. Since $P'(1) = P'(2) = 0$ and every multiple of $V$ is also zero at 1 and 2, the difference has the 2 roots 1 and 2 inside $D$, whatever $h$ the prover chooses. That leaves at most $4 - 2 = 2$ roots among the points outside the domain, which is the maximum in the table.

<!-- /worked:guess-h-bound -->

:::

This argument only works if the oracles are fixed before the verifier picks $\tau$, and the next example shows what happens otherwise.

<!-- worked:known-tau -->

Suppose the prover with $x = 4$ learns $\tau = 11$ before answering. It computes $P'(11) = 4$ and $V(11) = 32$, divides to get 27, and presents the constant polynomial $h(X) = 27$. The check at $\tau = 11$ passes because $27 \cdot 32 = 4$ modulo 43. At $\tau = 12$ the same $h$ gives $27$ against $P'(12) = 33$, so this forgery only works at the point the prover knew in advance.

<!-- /worked:known-tau -->

The test also assumes that $A$, $B$ and $C$ really are combinations of the column polynomials with one shared witness. If the prover could present any three polynomials, it could set all of them to zero, and the identity would hold with $h = 0$ for any statement. A plain oracle does not prevent this, because it accepts any polynomial within the degree bound. A complete QAP-based system therefore has to enforce three things. The prover's polynomials must be fixed before $\tau$ is known, each of $A$, $B$ and $C$ must be a combination of the column polynomials, and all three must use the same $\v{w}$.

## 8. Enforcing the test in Groth16

[Groth16](https://eprint.iacr.org/2016/260) enforces these requirements by keeping $\tau$ secret from everyone, including the prover. Section 7 showed why the prover must not know $\tau$, so the question is how the prover can evaluate its polynomials at a point it does not know.

The answer uses an elliptic curve with a generator $G$. A setup ceremony picks a secret $\tau$, publishes the points $\tau^i \cdot G$ for each power $i$ up to the degree it needs, and then destroys $\tau$. For a polynomial $p(X) = \sum_i a_i X^i$, the prover can combine these points with its own coefficients:

$$\sum_i a_i \cdot (\tau^i \cdot G) = \Big(\sum_i a_i \tau^i\Big) \cdot G = p(\tau) \cdot G.$$

The prover obtains $p(\tau)$ hidden inside a curve point without ever learning $\tau$, because recovering $\tau$ from $\tau \cdot G$ is a discrete log problem. The ceremony also publishes points built from the column polynomials evaluated at $\tau$, together with further secret values. Since the prover can only form linear combinations of published points, these extra points restrict it to polynomials of the required form, and the further secret values force a single shared witness into all three.

The verifier still has to check a multiplication, $A(\tau)B(\tau)$, between two values it only holds as $A(\tau)\cdot G$ and $B(\tau)\cdot G$. Adding curve points cannot multiply the hidden scalars, so Groth16 uses a **pairing**. A pairing is a map $e(P, Q)$ from two curve points to an element of another group, with the property $e(a \cdot P, b \cdot Q) = e(P, Q)^{ab}$. Applied to the two hidden values, it gives $e(G, G)^{A(\tau)B(\tau)}$, which the verifier can compare against a similar pairing of the other side. Only some curves have an efficiently computable pairing, and they are called pairing-friendly.

The resulting proof is three group elements, and verification uses three pairings. We do not need the rest of the construction here, only the list of things it relies on, which the next section examines.

## 9. The cost of QAP

Each ingredient of the QAP route has a cost, and several of those costs conflict with what Ragu needs.

**The prover works over a special domain.** Interpolating and multiplying term by term, as we did above, takes time quadratic in $m$. Real provers use the fast Fourier transform (FFT), which requires the domain to be a set of roots of unity. This choice also gives $V$ a compact form.

<!-- worked:unity -->

In $\F_{43}$ the value $\omega = 6$ satisfies $6^3 = 216 = 1$ modulo 43, so its powers form the domain $\{1, 6, 36\}$, and the vanishing polynomial collapses to $V(X) = X^3 - 1$. Repeating the construction on this domain with the same witness gives different polynomials, for example $A(X) = 30 + 7X + 9X^2$, and the exact quotient $h(X) = 11 + 42X$. The same field has no domain of size 4, because 4 does not divide $43 - 1 = 42$. Real proof systems pick fields whose multiplicative group has a large power of two in its order for this reason.

<!-- /worked:unity -->

The product is also larger than the circuit, because $A(X)B(X)$ has about twice the degree of its factors. Holding $P$ by its values therefore takes a domain about twice the size of $D$.

<!-- worked:scale -->

For a circuit of $m = 2^{16} = 65,536$ rows, $P(X)$ has degree up to $2(m-1) = 131,070$. Representing it requires a domain with more than 131,070 points, and the next power of two is $2^{17} = 131,072$.

<!-- /worked:scale -->

Groth16 provers avoid the larger domain by working on a shifted copy of the domain, where $V$ takes the same nonzero value at every point. Dividing by that one constant gives the quotient's values directly, so every FFT stays at size $m$. The prover still runs several FFTs, over a field with the required roots of unity.

::: details How the shifted domain avoids the larger FFT

The shifted copy is $gD$, for some $g$ outside $D$. When $D$ is the set of $m$-th roots of unity, $V(X) = X^m - 1$ takes the same nonzero value $g^m - 1$ at every point of $gD$, so the prover can get $h$ at each of those points by dividing the value of $P$ there by that constant. The quotient has degree below $m$, so its $m$ values determine it, and every FFT stays at size $m$.

:::

**The setup requires trust.** Anyone who learns $\tau$ or the other secret values can forge proofs, as Section 7 showed on a small scale. Groth16 also ties its setup to one circuit, because the ceremony publishes points built from that circuit's column polynomials, so a new circuit needs a new ceremony. Ragu's [overview](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/index.md) sets out to avoid a trusted setup altogether.

**The verifier needs pairings.** The pairing check is what makes the secret $\tau$ usable. Ragu works over the Pasta curves, which are not pairing-friendly, so this check is not available to it.

**The circuit description has to exist as polynomials.** Before any proof, someone has to compute the column polynomials $A_\ell$, $B_\ell$ and $C_\ell$ and, in Groth16, fold them into the setup. This work is repeated for every circuit, which matters for Ragu because it uses many circuits. A PCD tree, as described in the [proof-carrying data chapter](./pcd-intro.md), runs many different small steps, and Ragu splits large computations into many small circuits rather than one large one. A per-circuit setup with precomputed column polynomials would have to be repeated for every one of them. The same overview lists the QAP reduction among the things its construction avoids.

Ragu therefore has to reach a polynomial test some other way. It has no secret point and no pairing, so its verifier can only use plain oracles with degree bounds, which the commitments of the next chapter provide.

## 10. The consolidated equation as a coefficient

Ragu starts from a different place. A QAP keeps the rows separate until the very end and uses the domain to pack them together. Ragu has already combined its gates and constraints using the challenges $z$ and $y$, which left one scalar equation in [Section 12 of the arithmetization chapter](./arithmetization.md):

$$\revdot{\v{r}}{\v{r} \circ \v{z^{4n}} + \v{t} + \v{s}} = \dot{\v{k}}{\v{y^{4n}}}.$$

No domain and no vanishing polynomial are needed, since there are no separate rows left to pack. The remaining job is to let the verifier check this one equation without seeing $\v{r}$. Section 7 of that chapter already supplied the link to polynomials, because the revdot product of two vectors of length $4n$ is the coefficient of $X^{4n-1}$ in the product of the polynomials with those coefficient vectors. So we read every vector in the equation as a list of coefficients.

The witness vector becomes the **trace polynomial**. With $\v{d} = \v{0}$ and the layout from the arithmetization chapter, it is

$$r(X) = \sum_{i=0}^{n-1} \big( c_i X^i + a_i X^{2n-1-i} + b_i X^{2n+i} \big).$$

The dilated vector $\v{r} \circ \v{z^{4n}}$ multiplies coefficient $k$ by $z^k$, which is the effect of substituting $zX$ for $X$, because $r_k (zX)^k = (r_k z^k) X^k$. So the dilated vector is the coefficient vector of $r(zX)$, and no new data is involved.

The public vectors $\v{s}$ and $\v{t}$ depend on the challenges, and the circuit is fixed before the challenges exist. We therefore describe them with polynomials in two variables, the **wiring polynomial** $s(X, Y)$ and the **gate polynomial** $t(X, Z)$, and substitute a challenge for the second variable once it is known. The vector $\v{s}$ is the coefficient vector of $s(X, y)$, and $\v{t}$ is the coefficient vector of $t(X, z)$. Each coefficient of a constraint or gate sits at the partner of its wire's position in $r(X)$, where two powers of $X$ are partners when their exponents add up to $4n - 1$. On the right side of the equation, the **public input polynomial** $k(Y) = \sum_j k_j Y^j$ gives $\dot{\v{k}}{\v{y^{4n}}} = k(y)$. The box below writes out $s$ and $t$ in full.

::: details The formulas for s(X, Y) and t(X, Z)

The entries of these vectors come from Sections 10 and 11 of the arithmetization chapter. Recall from [Section 4 of that chapter](./arithmetization.md#_4-linear-constraints) that $u_{j,i}$, $v_{j,i}$ and $w_{j,i}$ are the coefficients of $a_i$, $b_i$ and $c_i$ in linear constraint $j$ (these $w_{j,i}$ carry two indices and are unrelated to the R1CS vector $\v{w}$). The wire $a_i$ sits at $X^{2n-1-i}$, so its partner is $X^{4n-1-(2n-1-i)} = X^{2n+i}$. In the same way, $b_i$ at $X^{2n+i}$ has its partner at $X^{2n-1-i}$, and $c_i$ at $X^i$ has its partner at $X^{4n-1-i}$. Weighting constraint $j$ by $Y^j$ and the gate terms by powers of $Z$ as in that chapter gives the wiring polynomial and the gate polynomial:

$$s(X, Y) = \sum_{j=0}^{4n-1} Y^j \sum_{i=0}^{n-1} \big( u_{j,i} X^{2n+i} + v_{j,i} X^{2n-1-i} + w_{j,i} X^{4n-1-i} \big),$$

$$t(X, Z) = -\sum_{i=0}^{n-1} \big( Z^{2n-1-i} + Z^{2n+i} \big) X^{4n-1-i}.$$

:::

::: warning The Ragu Book's NARK chapter uses the other layout
The NARK chapter writes $r(X) = \sum_i (c_i X^i + b_i X^{2n-1-i} + a_i X^{2n+i})$ and puts $u_{j,i}$ at $X^{2n-1-i}$ and $v_{j,i}$ at $X^{2n+i}$ in $s(X, Y)$. The [wiring code](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/wiring/mod.rs#L13-L22) at commit `3219e08` puts the coefficients of the $a$ wires at $X^{2n+i}$ in $s(X, Y)$, as in the box above. The two forms differ only by swapping the names $\v{a}$ and $\v{b}$. This site follows the code, as the arithmetization chapter did.
:::

Now collect the second factor into one polynomial,

$$f(X) = r(zX) + s(X, y) + t(X, z).$$

The name $f$ is local to this chapter, and the [complete proof chapter](./nark.md#_5-building-the-two-multiplicands) calls the same polynomial $b(X)$. Here $f(X)$ is the right vector of the consolidated equation in polynomial form. By the coefficient rule, the equation now reads

$$\text{the coefficient of } X^{4n-1} \text{ in } r(X)f(X) \text{ equals } k(y).$$

Here are the polynomials for our witness at $z = 5$ and $y = 7$, the challenges from the arithmetization chapter:

<!-- worked:right-factor -->

| Polynomial | Coefficients of $X^0, \ldots, X^7$ |
| --- | --- |
| $r(X)$ | $(9, 27, 9, 3, 3, 3, 0, 0)$ |
| $r(5X)$ | $(9, 6, 10, 31, 26, 1, 0, 0)$ |
| $s(X, 7)$ | $(0, 0, 6, 42, 37, 7, 42, 36)$ |
| $t(X, 5)$ | $(0, 0, 0, 0, 0, 0, 32, 24)$ |
| $f(X)$ | $(9, 6, 16, 30, 20, 8, 31, 17)$ |

The vector for $f(X)$ is the combined right vector from Section 12 of the arithmetization chapter, now read as coefficients.

<!-- /worked:right-factor -->

Each entry of the middle three rows comes from the formulas for $r$, $s$ and $t$. The box traces one entry from each row back to its source.

::: details Where three of the coefficients come from

<!-- worked:coefficient-sources -->

For $r(5X)$, the coefficient of $X^1$ is $r_1 \cdot 5 = 27 \cdot 5 = 135 = 6$ modulo 43. For $t(X, 5)$, the coefficient of $X^7$ belongs to $i = 0$, the partner of $c_0$, and equals $-(5^3 + 5^4) = -750 = 24$ modulo 43. For $s(X, 7)$, the wire $a_0$ sits at $X^3$ in $r$, so its partner is $X^4$, and the coefficient of $X^4$ collects $u_{j,0} 7^j$ from every constraint $j$ that uses $a_0$. Constraints 0, 2 and 3 use it with coefficients $1$, $-1$ and $1$, which gives $1 - 7^2 + 7^3 = 295 = 37$ modulo 43.

<!-- /worked:coefficient-sources -->

:::

The coefficient of $X^7$ in the product collects every pair of exponents that adds to 7:

<!-- worked:middle -->

| $i$ | Coefficient of $X^i$ in $r$ | $7 - i$ | Coefficient of $X^{7-i}$ in $f$ | Product |
| --- | --- | --- | --- | --- |
| 0 | 9 | 7 | 17 | 24 |
| 1 | 27 | 6 | 31 | 20 |
| 2 | 9 | 5 | 8 | 29 |
| 3 | 3 | 4 | 20 | 17 |
| 4 | 3 | 3 | 30 | 4 |
| 5 | 3 | 2 | 16 | 5 |
| 6 | 0 | 1 | 6 | 0 |
| 7 | 0 | 0 | 9 | 0 |

The last column sums to 13 modulo 43. On the other side, $k(Y) = 30Y^3$ because only $k_3$ is nonzero, so $k(7) = 30 \cdot 7^3 = 13$ modulo 43.

<!-- /worked:middle -->

## 11. Why the coefficient is out of reach

We can expand the whole product to see where this coefficient sits.

<!-- worked:product -->

The full product has 15 coefficients:

| Power of $X$ | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Coefficient | 38 | 39 | 0 | 9 | 18 | 29 | 14 | **13** | 9 | 29 | 39 | 15 | 8 | 0 | 0 |

The entry for $X^7$ is 13, the value the consolidated equation requires. Every other entry is a by-product of the multiplication that the check does not constrain. The two highest coefficients are zero in this example because $\v{d} = \v{0}$ leaves $r$ with degree 5.

<!-- /worked:product -->

In general, $r$ and $f$ each have $4n$ coefficients, so the product has degree up to $(4n - 1) + (4n - 1) = 8n - 2$ and needs $8n - 1$ coefficients. Two obstacles keep the verifier from checking the coefficient directly.

The first is that an oracle answers evaluations, and one coefficient in the middle of a polynomial is not an evaluation at any point. The second is size. Ragu's oracles have degree bound $4n - 1$, because its commitment parameters contain $4n$ points and so hold at most $4n$ coefficients (the capacity premise from Section 1). The product needs almost twice as many, so it does not fit in a single oracle. Doubling the number of points would fix the second obstacle, but it would make every commitment in the system about twice as expensive, and all of that would serve to expose one coefficient.

## 12. Splitting the product

A single reshaping of the product removes both obstacles. For the size problem, cut the product into a lower half with the $4n$ coefficients of $X^0$ through $X^{4n-1}$, and an upper half with the rest:

$$r(X)f(X) = c_{\mathrm{lo}}(X) + X^{4n}\, c_{\mathrm{hi}}(X).$$

Both pieces have degree below $4n$, so each fits within a single oracle. The coefficient we want is the top coefficient of $c_{\mathrm{lo}}$, which is still not an evaluation.

The one coefficient of a polynomial that evaluation can reach is the constant term, because substituting $X = 0$ removes all the others. So we reverse the coefficients of the lower half, which moves the top coefficient to the bottom:

$$c_1(X) = X^{4n-1}\, c_{\mathrm{lo}}(X^{-1}), \qquad c_2(X) = c_{\mathrm{hi}}(X).$$

Substituting $X^{-1}$ turns each power $X^k$ into $X^{-k}$, and multiplying by $X^{4n-1}$ shifts it to $X^{4n-1-k}$, so $c_1$ holds the coefficients of $c_{\mathrm{lo}}$ in reverse order. Its constant term is therefore the top coefficient of $c_{\mathrm{lo}}$, and the consolidated equation has become

$$c_1(0) = k(y).$$

::: details The reversal written out

Write $c_{\mathrm{lo}}(X) = \sum_{k=0}^{4n-1} \lambda_k X^k$ and multiply through:

$$c_1(X) = X^{4n-1} \sum_{k=0}^{4n-1} \lambda_k X^{-k} = \sum_{k=0}^{4n-1} \lambda_k X^{4n-1-k}.$$

The coefficient $\lambda_{4n-1}$ is attached to $X^0$, so $c_1(0) = \lambda_{4n-1}$.

:::

![Fifteen cells for the powers X^0 to X^14 of the product. The lower eight cells appear in reverse order as c_1, with X^7 in position 0, and the upper seven appear in the same order as c_2.](./manim/product-split.png)

<!-- worked:split -->

For our product, $c_{\mathrm{lo}}$ has coefficients $(38, 39, 0, 9, 18, 29, 14, 13)$ and $c_{\mathrm{hi}}$ has coefficients $(9, 29, 39, 15, 8, 0, 0)$. Reversing the lower half gives $c_1(X)$ with coefficients $(13, 14, 29, 18, 9, 0, 39, 38)$, so $c_1(0) = 13$, which is the required value $k(7)$. We set $c_2 = c_{\mathrm{hi}}$.

<!-- /worked:split -->

The notation is close to the wires of the arithmetization chapter, but the meaning is different. The polynomials $c_1(X)$ and $c_2(X)$ are unrelated to the wire values $c_0, c_1, \ldots$, and we will always write the polynomials with their argument. The wires now appear only inside $r(X)$.

The verifier also needs a way to know that $c_1$ and $c_2$ really came from the product. Reversing twice restores the original, so $X^{4n-1} c_1(X^{-1})$ is the lower half $c_{\mathrm{lo}}(X)$ again. Putting this back into the cut gives one equation that ties the two new polynomials to the product:

$$r(X)f(X) = X^{4n-1} c_1(X^{-1}) + X^{4n} c_2(X).$$

::: details Undoing the reversal

Substitute $X^{-1}$ into the definition of $c_1$ and multiply by $X^{4n-1}$:

$$X^{4n-1} c_1(X^{-1}) = X^{4n-1} \cdot X^{-(4n-1)}\, c_{\mathrm{lo}}(X) = c_{\mathrm{lo}}(X).$$

Replacing $c_{\mathrm{lo}}(X)$ in the cut $r(X)f(X) = c_{\mathrm{lo}}(X) + X^{4n} c_{\mathrm{hi}}(X)$ with this expression, and $c_{\mathrm{hi}}$ with $c_2$, gives the equation above.

:::

The verifier has to evaluate this at a nonzero point $x$, since it uses $X^{-1}$.

<!-- worked:reversal-check -->

At $x = 9$, the inverse is $x^{-1} = 24$, because $9 \cdot 24 = 216 = 1$ modulo 43. Then $c_1(24) = 6$, $x^7 = 36$, and $36 \cdot 6 = 1$ modulo 43, which equals $c_{\mathrm{lo}}(9)$ computed directly.

<!-- /worked:reversal-check -->

## 13. Polynomial oracles

We can now write Ragu's encoding as a protocol with the oracles of Section 1. Every oracle in it has degree bound $4n - 1$. The trace $r(X)$ fits by construction, and the split of Section 12 exists so that $c_1(X)$ and $c_2(X)$ fit as well.

The order of messages carries much of the protocol's soundness. The prover fixes $r(X)$ before seeing the challenges $z$ and $y$, as the argument in the arithmetization chapter required. It fixes $c_1(X)$ and $c_2(X)$ before seeing $x$, because the split check is a random test of those polynomials.

```mermaid
sequenceDiagram
    participant P as Prover
    participant V as Verifier
    Note over P,V: Shared: s(X,Y), t(X,Z), k(Y)
    P->>V: Oracle r(X)
    V->>P: Challenges z, y
    Note over P: Compute r(X)f(X), then split it
    P->>V: Oracles c1(X), c2(X)
    V->>P: Challenge x
    Note over V: Query oracles and check both equations
```

In the protocol, $x$ is this random evaluation point, and the verifier picks it nonzero. The verifier asks the oracles for $r(x)$ and $r(xz)$, then for $c_1(x^{-1})$ and $c_1(0)$, then for $c_2(x)$. It computes $s(x, y)$, $t(x, z)$ and $k(y)$ by itself, because these polynomials are public. Then it checks two equations:

$$r(x)\big(r(xz) + s(x, y) + t(x, z)\big) = x^{4n-1} c_1(x^{-1}) + x^{4n} c_2(x),$$

$$c_1(0) = k(y).$$

The first is the **split check**, and the second is the **target check**. The dilation helps in the first check, because the verifier gets the value of $r(zX)$ at $x$ by asking the same oracle about the point $xz$. No separate polynomial is involved, so the prover cannot substitute a different trace in the second factor.

The verifier's local work differs among the three public polynomials. The value $t(x, z)$ has a [short closed form](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/local/arithmetization.md), since each of its sums is a geometric series, and $k(y)$ is cheap when the public input vector is sparse. Computing $s(x, y)$ directly costs time linear in the circuit size, and the chapter on [wiring and the registry](./wiring-and-registry.md) studies how to avoid this.

## 14. A complete run

Here is the whole protocol on the witness with secret input 3, with the oracles written out so that we can follow them. The secret input now sits inside $r(X)$, and the $x$ in the table is the random point. Every oracle has degree bound $4n - 1$, so each polynomial in the table has at most $4n$ coefficients.

<!-- worked:run -->

| Step | Party | Value or check |
| --- | --- | --- |
| 1 | Both | Hold $s(X, Y)$, $t(X, Z)$ and $k(Y) = 30Y^3$ |
| 2 | Prover sends oracle | $r(X) = 9 + 27X + 9X^2 + 3X^3 + 3X^4 + 3X^5$ |
| 3 | Verifier sends challenges | $z = 5$, $y = 7$ |
| 4 | Prover computes | $f(X) = r(5X) + s(X, 7) + t(X, 5)$ and the product $r(X)f(X)$ |
| 5 | Prover sends oracles | $c_1(X) = 13 + 14X + 29X^2 + 18X^3 + 9X^4 + 39X^6 + 38X^7$ and $c_2(X) = 9 + 29X + 39X^2 + 15X^3 + 8X^4$ |
| 6 | Verifier sends challenge | $x = 9$, so $xz = 2$ and $x^{-1} = 24$ |
| 7 | Verifier queries $r$ | $r(9) = 5$ and $r(2) = 9$ |
| 8 | Verifier queries $c_1$ | $c_1(24) = 6$ and $c_1(0) = 13$ |
| 9 | Verifier queries $c_2$ | $c_2(9) = 30$ |
| 10 | Verifier computes locally | $s(9, 7) = 23$, $t(9, 5) = 3$, $k(7) = 13$ |
| 11 | Verifier checks the split | $5 \cdot (9 + 23 + 3) = 3$ and $36 \cdot 6 + 23 \cdot 30 = 3$ |
| 12 | Verifier checks the target | $c_1(0) = 13 = k(7)$ |

Both checks pass. Repeating step 11 at all 42 nonzero values of $x$ shows that the honest polynomials pass at every one.

<!-- /worked:run -->

## 15. Why cheating fails

The argument assumes that oracles are fixed when sent and respect their degree bound, and that the challenges are uniform and arrive after the messages they test. The commitments of the next chapter provide the first assumption. They rely on the discrete log relation assumption, which the next chapter states and which says roughly that nobody can find a nontrivial linear relation among the public curve points. [Fiat–Shamir](./statements-and-challenges.md#_7-removing-the-verifier-with-fiat–shamir) provides the second in a non-interactive proof, treating its hash as a random oracle. Inside this model, the argument only counts roots of polynomials.

A prover with a false witness has to send some $r'(X)$ before seeing $z$ and $y$. The arithmetization chapter showed that a random pair $(z, y)$ rarely makes the true coefficient equal to $k(y)$.

<!-- worked:lucky -->

For the false witness with secret input 4, counting all pairs finds 43 of the 1849 that do so.

<!-- /worked:lucky -->

Outside those lucky pairs, the honest split fails the target check, so the prover has to lie about the split. The most direct lie changes only the coefficient the target check reads.

<!-- worked:cheat-naive -->

Take the false witness with secret input 4 from Section 7, so $r'(X) = 16 + 21X + 16X^2 + 4X^3 + 4X^4 + 4X^5$, at the same $z = 5$ and $y = 7$. The coefficient of $X^7$ in $r'(X)f'(X)$ is 18, while $k(7) = 13$, so the honest split would fail the target check. The prover can change the constant term of $c_1$ to 13 and leave everything else alone, which fixes the target check. The two sides of the split check then differ by $5X^7$, and the verifier rejects at all 42 nonzero values of $x$.

<!-- /worked:cheat-naive -->

This lie is the easiest to catch, since the error sits on one power of $X$. A cleverer prover still cannot make the split check an identity. In the right side of the split check, only the reversed $c_1$ contributes to the coefficient of $X^{4n-1}$, and that coefficient is $c_1(0)$. The target check forces $c_1(0) = k(y)$, while the true coefficient in $r'(X)f'(X)$ differs from $k(y)$. So whatever $c_1$ and $c_2$ the prover sends, the two sides of the split check are different polynomials, and the prover's best option is to give their difference as many roots as possible. The degree bounds of Section 13 cap that number at $8n - 1$, which the box below derives.

::: details Where the coefficient and the degree cap come from

The right side of the split check is $X^{4n-1}c_1(X^{-1}) + X^{4n}c_2(X)$. The term with $c_2$ starts at $X^{4n}$, so the coefficient of $X^{4n-1}$ comes only from the first term, and Section 12 showed that this coefficient is $c_1(0)$.

The degree bounds cap the number of roots of the difference. The left side $r'(x)f'(x)$ has degree at most $8n - 2$. On the right side, $c_1$ has degree at most $4n - 1$, so $x^{4n-1}c_1(x^{-1})$ is a polynomial of degree at most $4n - 1$, and $x^{4n}c_2(x)$ has degree at most $4n + (4n - 1) = 8n - 1$. The honest $c_2$ uses only $4n - 1$ coefficients, but its oracle has room for $4n$, so a cheater can fill the last one. The difference therefore has degree at most $8n - 1$, and it can have at most that many roots.

:::

<!-- worked:cheat-best -->

The prover can do better by spreading the difference over many powers of $X$. Let $\Delta(X)$ be a polynomial of degree 15 whose coefficient of $X^7$ is 5, which is the amount the true coefficient must change by. The product $(X-1)(X-2)\cdots(X-15)$ has the 15 roots $1, \ldots, 15$, and its coefficient of $X^7$ is 41, which is nonzero modulo 43. So the prover sets $\Delta(X) = \lambda (X-1)(X-2)\cdots(X-15)$ with $\lambda = 5 / 41 = 19$, which keeps the 15 roots and makes the coefficient of $X^7$ equal to $41 \cdot 19 = 5$ modulo 43. The prover then splits $r'(X)f'(X) - \Delta(X)$ instead of the true product, and the new $c_1$ has $c_1(0) = 13$, as the target check requires. The split check now compares $r'(x)f'(x)$ with $r'(x)f'(x) - \Delta(x)$, so it passes exactly where $\Delta(x) = 0$. Testing every nonzero $x$ finds 15 passing values out of 42, which is the most a polynomial of degree 15 allows. For $n = 2^{11}$ on a field of about $2^{255}$ elements, the same limit of $8n - 1$ roots gives a probability below $2^{-240}$.

<!-- /worked:cheat-best -->

The two failure points add up to one bound. A cheating prover gets through either by drawing a lucky pair $(z, y)$, which happens with probability at most $(4n - 1)/|\F_q|$ by the arithmetization chapter, or, after an unlucky pair, by drawing an $x$ that is a root of the split check's difference, which happens with probability at most $(8n - 1)/|\F_q|$. So the chance that a false witness passes both checks is at most $(12n - 2)/|\F_q|$.

As with the QAP, the order of messages is essential.

<!-- worked:cheat-early -->

Suppose the prover also knows $x = 9$ before sending $c_1$ and $c_2$. Changing the constant term of $c_1$ moved the split check by $5x^7$, and adding a constant $e$ to $c_2$ moves it by $ex^8$ in the other direction. Choosing $e = 5 / 9 = 34$ cancels the two at this one point. The forged pair passes both checks at $x = 9$, and testing the other nonzero values confirms that it passes at no other point.

<!-- /worked:cheat-early -->

## 16. Comparing the two routes

Both routes turn many constraints into one polynomial test at a random point, and they differ in how they reach that test.

| | QAP | Ragu's encoding |
| --- | --- | --- |
| How the rows combine | One point of the domain per row | Powers of the challenges $z$ and $y$ |
| Form of the claim | $P(X)$ is divisible by $V(X)$ | One coefficient of $r(X)f(X)$ equals $k(y)$ |
| Extra polynomials from the prover | The quotient $h(X)$ | The pieces $c_1(X)$ and $c_2(X)$ |
| How the verifier reaches the claim | Compares $P(\tau)$ with $h(\tau)V(\tau)$ | Reads $c_1(0)$ and tests the split at $x$ |
| Witness encoding | Values at domain points | Coefficients of $r(X)$ |
| Random values | One point $\tau$, secret in Groth16 | $z$, $y$ and $x$, all public |
| Tying factors to one witness | Secret setup values in Groth16 | One oracle $r$, queried at $x$ and $xz$ |

The central difference is division against extraction. The QAP has to show that a whole polynomial vanishes across a domain, and a quotient is the evidence for that. Ragu's claim concerns one number, so the prover has no quotient to compute and only has to move that number to a place evaluation can reach.

This does not make the multiplication free. Splitting the product still requires the prover to compute it, and for large polynomials that takes FFTs on a domain of about $8n$ points. Ragu does not always pay this cost. Its uncompressed proofs send the two vectors of the revdot product themselves, and the verifier recomputes the product with one multiplication per entry. Such a proof is larger and not succinct, but nobody runs an FFT to build it. The [complete proof](./nark.md#_3-choosing-how-to-check-the-revdot-product) chapter explains when that trade is acceptable. The Ragu Book's [structured vectors chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/prelim/structured_vectors.md) places the split at the points in the PCD tree where succinctness is required, which is the compression step of Section 17.

## 17. The encoding in Ragu

The split appears in the compression step of the code as a short function, here from [`crates/ragu_pcd/src/compress/revdot/prover.rs`](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/revdot/prover.rs#L51-L70) at commit `3219e08`. Its $n$ counts all the coefficients, so it plays the role of our $4n$:

```rust
let q = c.split_off(n);
c.reverse();
(c, q)
```

The [verifier](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/revdot/verifier.rs#L123-L127) recomputes the right side of the split check from the claimed evaluations and rejects on a mismatch.

::: warning Naming differs across the Ragu Book and the code
The Book's NARK chapter calls the two pieces $c_1$ and $c_2$ and the evaluation point $x$. Its structured vectors chapter and the code call the pieces $p$ and $q$, and the [compression chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/recursion/compression.md) and the code call the point $r$. This site uses $c_1$, $c_2$ and $x$ here, because $r$ already names the trace polynomial and $p$ is used for other polynomials.
:::

::: warning The Ragu Book and the code differ on the public constant
The Book's [NARK chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/nark.md) puts the constant `ONE` at the start of the witness and adds a check $r(0) = 1$, while its [wiring chapter](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/local/wiring.md) and the [trace assembly code](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_circuits/src/trace.rs#L140-L143) at commit `3219e08` keep $c_0 = 0$, so that $r(0) = 0$, and put `ONE` in the wire $d_0$. This site follows the code, and the complete proof chapter adds this wire to the toy circuit in [The constant wire](./nark.md#_15-the-constant-wire).

<!-- worked:toy-one -->

Our toy circuit has no `ONE` wire. Its $r(0) = c_0$ is the wire value 9 and its $k(0)$ is 0, so the run in Section 14 has no check on the constant term of $r$.

<!-- /worked:toy-one -->

:::

::: warning Reconstructed from code at commit 3219e08, not confirmed by the authors
The [uncompressed verifier](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/verify.rs#L175-L180) recomputes the revdot product from the two vectors, as Section 16 describes. The split appears only in compression, where the [prover](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/crates/ragu_pcd/src/compress/revdot/prover.rs#L331-L345) applies it to a random combination of folded claims instead of a single product. We return to folded claims in [revdot folding](./revdot-folding.md).
:::

## 18. Where this chapter leaves us

This chapter took the following steps:

1. A QAP interpolates each column of the R1CS matrices over a domain, so that row $i$ becomes an equation at the point $\rho_i$.
2. The rows hold exactly when $A(X)B(X) - C(X)$ is divisible by the vanishing polynomial $V(X)$, which reduces them to one identity with a quotient $h(X)$.
3. A false witness has no quotient, so a prover can only pass by luck, or by knowing the test point in advance.
4. Groth16 enforces the QAP test with a secret $\tau$, a trusted setup and pairings, and Ragu uses none of those.
5. Ragu reads its consolidated equation as the coefficient of $X^{4n-1}$ in $r(X)\big(r(zX) + s(X, y) + t(X, z)\big)$.
6. Splitting the product and reversing the lower half turns that coefficient into the constant term $c_1(0)$, and a split check at a random $x$ ties $c_1$ and $c_2$ to the product.
7. Written with oracles that have degree bounds, the protocol is a polynomial IOP whose soundness depends on those bounds and on the order of its messages.

Every oracle in this protocol is still an assumption. The [next chapter](./polynomial-commitments.md) builds the commitment that replaces each oracle with one curve point.
