# Curves

## The toy cycle

Every worked example on this site uses the following pair of curves. Each curve has prime order, and each curve's order equals the other curve's base field size. Solving discrete log on these curves takes a few dozen additions, so they demonstrate the arithmetic and provide no security.

<!-- worked:toy-cycle -->

| Curve | Equation | Base field | Number of points | Scalar field |
| --- | --- | --- | --- | --- |
| $E$ | $y^2 = x^3 + 3$ | $\F_{31}$ | 43 | $\F_{43}$ |
| $E'$ | $y^2 = x^3 + 7$ | $\F_{43}$ | 31 | $\F_{31}$ |

<!-- /worked:toy-cycle -->

Both curves have the form $y^2 = x^3 + b$, and both field sizes are congruent to 1 modulo 3. The Pasta curves share these properties, which later chapters use for curve cycles and endoscalars.

## The Pasta cycle

Ragu uses the [Pasta curves](https://electriccoin.co/blog/the-pasta-curves-for-halo-2-and-beyond/), Pallas and Vesta, which also appear in Zcash's Orchard protocol. Both have the equation $y^2 = x^3 + 5$. Pallas is defined over $\F_p$ and has $q$ points, while Vesta is defined over $\F_q$ and has $p$ points, where $p$ and $q$ are primes of about 255 bits.
