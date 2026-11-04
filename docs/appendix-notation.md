# Notation

The first table lists symbols used across the site. The later tables list symbols that belong to one part of the site, and each chapter defines them when they first appear.

| Symbol | Meaning |
| --- | --- |
| $\F_q$ | The field of integers modulo a prime $q$ |
| $\G$ | A group of elliptic curve points with prime order $q$ |
| $\mathcal{O}$ | The identity element of $\G$, also called the point at infinity |
| $a, b, x, y, \gamma$ | Scalars in $\F_q$, written in lowercase |
| $G, H, U, C, P$ | Group elements, written in uppercase |
| $\v{a}$ | A vector of scalars, written in bold and indexed from zero |
| $\v{G}$ | A vector of group elements |
| $\dot{\v{a}}{\v{b}}$ | The inner product $\sum_i a_i b_i$ of two scalar vectors |
| $\dot{\v{a}}{\v{G}}$ | The multi-scalar multiplication $\sum_i a_i \cdot G_i$ |
| $\v{x^n}$ | The power vector $(1, x, x^2, \ldots, x^{n-1})$ |
| $\bar{C}$ | A hiding commitment, which includes a blinding factor |
| $\v{a} \circ \v{b}$ | The entrywise product of two vectors |
| $\v{a} \| \v{b}$ | The concatenation of two vectors |
| $\rv{a}$ | The vector $\v{a}$ with its entries in reverse order |
| $\revdot{\v{a}}{\v{b}}$ | The revdot product $\dot{\v{a}}{\rv{b}}$ |

## Proof structure

| Symbol | Meaning |
| --- | --- |
| $r(X)$ | The trace polynomial, whose coefficients are the structured witness |
| $s(X, Y)$ | The wiring polynomial |
| $t(X, Z)$ | The gate polynomial |
| $k(Y)$ | The public input polynomial |
| $c_1(X), c_2(X)$ | The two parts of a product polynomial after decomposition |
| $V(X), h(X)$ | The vanishing polynomial and the quotient in a QAP |
| $L_j, R_j, u_j$ | The cross terms and challenge of IPA round $j$ |
| $\hat{a}, \hat{b}, \hat{G}$ | The final folded values of an IPA |
| $g(X)$ | The succinct polynomial whose coefficients form the IPA's vector $\v{s}$ |
| $\alpha, \beta, u$ | The challenges of a batched opening |
| $q_i(X), f(X)$ | The quotient of claim $i$ and the combined quotient |

## Recursion and Ragu

| Symbol | Meaning |
| --- | --- |
| $z_i, F, \pi_i$ | The state at step $i$, the step function, and the proof at step $i$ |
| $\mathsf{acc}$ | An accumulator, with parts $\mathsf{acc.inst}$ and $\mathsf{acc.wit}$ |
| $\mathsf{Acc.P}, \mathsf{Acc.V}, \mathsf{Acc.Decide}$ | The accumulation prover, verifier, and decider |
| $g_{\v{u}}$ | The succinct polynomial defined by the IPA challenges $\v{u}$ |
| $E, E'$ | The two toy curves |
| $CS^{(1)}, CS^{(2)}$ | The circuits over each field of a cycle |
| $\mathring{A}$ | A nested commitment |
| $\zeta, \lambda, \phi$ | The cube root of unity in the base field, the eigenvalue, and the endomorphism |
| $m(W, X, Y)$ | The registry polynomial |
| $r'(X)$ | The final trace after stages are separated |

## Tachyon

| Symbol | Meaning |
| --- | --- |
| $\mathsf{sk}, \mathsf{ask}, \mathsf{ak}, \mathsf{nk}, \mathsf{pk}, \mathsf{pak}$ | The keys of the Tachyon key hierarchy |
| $\psi, \mathsf{rcm}, \mathsf{cm}$ | A note's trapdoors and its commitment |
| $\mathsf{mk}, \mathsf{nf}_e$ | A note's master key and its nullifier for epoch $e$ |
| $\mathsf{tg}, \mathsf{tg}_\bot$ | A tachygram and a padding tachygram |
| $\mathsf{entry}(e), \mathsf{final}(e)$ | The first and last anchors of epoch $e$ |
| $\Delta(X), N(X), C(X)$ | The polynomials of a delegated absence proof |
| $\mathsf{cv}, \mathsf{bsk}, \mathsf{bvk}$ | A value commitment and the binding signature keys |
