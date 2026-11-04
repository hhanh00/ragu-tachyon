"""Curve parameters for appendix-curves.md. Prints fragments as JSON."""
import json
from toy_curve import B, B_DUAL, P, Q, curve_points

print(json.dumps({'toy-cycle': '\n'.join([
    '| Curve | Equation | Base field | Number of points | Scalar field |',
    '| --- | --- | --- | --- | --- |',
    f'| $E$ | $y^2 = x^3 + {B}$ | $\\F_{{{P}}}$ | {len(curve_points()) + 1} | $\\F_{{{Q}}}$ |',
    f"| $E'$ | $y^2 = x^3 + {B_DUAL}$ | $\\F_{{{Q}}}$ | {len(curve_points(Q, B_DUAL)) + 1} | $\\F_{{{P}}}$ |",
])}))
