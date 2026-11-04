# Glossary

Each entry gives a one-line reminder and links to the chapter that teaches the term. Entries marked as planned link to stubs.

- **Accumulator:** a running object that carries deferred checks from one recursive step to the next. Planned for [Accumulation](./accumulation.md).
- **Binding:** the property that a prover cannot open one commitment to two different values. See [Polynomial Commitments](./polynomial-commitments.md#_4-why-a-prover-cannot-change-the-vector).
- **Endoscalar:** a short challenge that the curve's endomorphism makes cheap to apply on either side of the cycle. Planned for [Endoscalars](./endoscalars.md).
- **Gate:** one multiplication check $a_i b_i = c_i$ on the witness. See [Arithmetization](./arithmetization.md#_3-gates).
- **Hiding:** the property that a commitment reveals nothing about the committed value. See [Polynomial Commitments](./polynomial-commitments.md#_6-hiding-the-vector).
- **Inner product argument (IPA):** a short proof of a claim about the inner product of committed vectors. Planned for [The Inner Product Argument](./inner-product-argument.md).
- **Pedersen vector commitment:** the point $\dot{\v{a}}{\v{G}}$, optionally with a blinding term. See [Polynomial Commitments](./polynomial-commitments.md#_3-committing-to-a-vector).
- **Polynomial commitment scheme (PCS):** a commitment to a polynomial, together with a way to prove its evaluations. See [Polynomial Commitments](./polynomial-commitments.md).
- **Proof-carrying data (PCD):** a computation structured as a tree of steps, where each step's data carries a proof of all the work behind it. Planned for [An Introduction to Proof-Carrying Data](./pcd-intro.md).
- **QAP (quadratic arithmetic program):** a polynomial form of R1CS in which the constraints hold when one polynomial divides another. Planned for [QAP and Polynomial Encoding](./polynomial-encoding.md).
- **R1CS (rank-1 constraint system):** constraints of the form $A\v{w} \circ B\v{w} = C\v{w}$. See [Arithmetization](./arithmetization.md#_14-comparison-with-r1cs-and-plonk).
- **Revdot product:** the inner product of one vector with the reversal of another, written $\revdot{\v{a}}{\v{b}}$. See [Arithmetization](./arithmetization.md#_7-reading-one-coefficient-of-a-product).
- **Split accumulation:** accumulation in which the verifier handles only public instances, while the prover keeps a separate witness. Planned for [Split Accumulation](./split-accumulation.md).
- **Structured vector:** a vector arranged so that the revdot product pairs each gate's $a$ and $b$ wires. See [Arithmetization](./arithmetization.md#_8-arranging-the-witness).
- **Witness:** the secret values that satisfy a circuit, also called the trace. See [Arithmetization](./arithmetization.md#_3-gates).
