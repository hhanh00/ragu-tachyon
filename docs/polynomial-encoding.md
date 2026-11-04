# QAP and Polynomial Encoding

This chapter is a stub. It will start from the R1CS example in Chapter 04 and derive the quadratic arithmetic program (QAP): interpolating the constraint matrices into polynomials, and proving that the constraints hold by showing that one polynomial divides another through a quotient. It will then show how Ragu reaches a polynomial check without a QAP reduction, using coefficient extraction and the decomposition trick.

Primary sources:

- [QAP-based SNARKs, Groth16](https://eprint.iacr.org/2016/260)
- [Ragu protocol overview, simple circuit model](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/index.md)
- [Revdot products to polynomial predicates](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/core/nark.md)
- [Structured vectors](https://github.com/tachyon-zcash/ragu/blob/3219e0865e8bff1f9d817bfe3850d9e94b64338c/book/src/protocol/prelim/structured_vectors.md)
