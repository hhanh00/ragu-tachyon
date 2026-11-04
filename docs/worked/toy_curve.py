"""The toy curve cycle shared by every worked example.

These curves are small enough to print and offer no security: anyone can solve
discrete log on them by counting. Both have j-invariant 0 and prime order, and
each curve's order is the other curve's base field, as with Pallas and Vesta.
"""
P, Q, B = 31, 43, 3     # E: y^2 = x^3 + 3 over F_31, with 43 points
B_DUAL = 7              # E': y^2 = x^3 + 7 over F_43, with 31 points


def curve_points(p=P, b=B):
    return [(x, y) for x in range(p) for y in range(p) if (y * y - x * x * x - b) % p == 0]


def add(a, c, p=P):
    if a is None:
        return c
    if c is None:
        return a
    if a[0] == c[0] and (a[1] + c[1]) % p == 0:
        return None
    if a == c:
        s = 3 * a[0] * a[0] * pow(2 * a[1], -1, p) % p
    else:
        s = (c[1] - a[1]) * pow(c[0] - a[0], -1, p) % p
    x = (s * s - a[0] - c[0]) % p
    return x, (s * (a[0] - x) - a[1]) % p


def mul(k, a, p=P):
    result = None
    for _ in range(k % Q if p == P else k):
        result = add(result, a, p)
    return result


def msm(scalars, points):
    result = None
    for k, a in zip(scalars, points):
        result = add(result, mul(k, a))
    return result


def log(target, base):
    """Solve discrete log by counting, which a real curve makes infeasible."""
    return next(k for k in range(Q) if mul(k, base) == target)


def show(a):
    return r'\mathcal{O}' if a is None else f'({a[0]},\\,{a[1]})'


# Points in order of x-coordinate, taking the first point at each new x.
def _distinct_x():
    seen, out = set(), []
    for a in curve_points():
        if a[0] not in seen:
            seen.add(a[0])
            out.append(a)
    return out


# Spacing the choices across the curve keeps them apart in the chapter's figure.
_points = _distinct_x()
_chosen = [_points[i * len(_points) // 6] for i in range(6)]
G = _chosen[:4]
H = _chosen[4]
U = _chosen[5]

assert len(curve_points()) + 1 == Q and len(curve_points(Q, B_DUAL)) + 1 == P
assert P % 3 == 1 and Q % 3 == 1
