"""Static teaching diagrams. Render through npm run docs:manim.

All positions use a 16 x 9 frame. No animations or runtime dependencies
are required by the website; the generated PNGs are committed assets.
"""
from manim import *
import numpy as np

config.background_color = WHITE
config.frame_width = 16
config.frame_height = 9
INK = '#172b4d'
MUTED = '#526477'
BLUE = '#2563eb'
TEAL = '#008577'
ORANGE = '#c66a08'
PURPLE = '#8052bd'
PALE = '#eef3fa'


def label(s, x, y, size=26, color=INK, width=None):
    replacements = {
        '\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
        '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
        '~': r'\textasciitilde{}', '^': r'\textasciicircum{}',
        '³': r'\textsuperscript{3}', '×': r'\ensuremath{\times}',
        'θ': r'\ensuremath{\theta}', 'Λ': r'\ensuremath{\Lambda}',
        'μ': r'\ensuremath{\mu}', 'π': r'\ensuremath{\pi}',
        'ψ': r'\ensuremath{\psi}', 'φ': r'\ensuremath{\phi}',
        'Δ': r'\ensuremath{\Delta}', 'ℳ': r'\ensuremath{\mathcal{M}}',
        'ℓ': r'\ensuremath{\ell}', 'ε': r'\ensuremath{\varepsilon}',
        'ν': r'\ensuremath{\nu}', 'γ': r'\ensuremath{\gamma}',
        'ω': r'\ensuremath{\omega}', 'χ': r'\ensuremath{\chi}',
        'λ': r'\ensuremath{\lambda}', '∑': r'\ensuremath{\sum}',
        'ℏ': r'\ensuremath{\hbar}', '½': r'\ensuremath{\frac12}',
        '₀': r'\ensuremath{{}_0}', '²': r'\ensuremath{{}^{2}}',
        '−': '-', '′': "'", '…': r'\ldots',
        '’': "'", '“': '``', '”': "''", '–': '--', '—': '---',
    }
    def escape(line):
        return ''.join(replacements.get(char, char) for char in line)
    lines = [Tex(r'\text{' + escape(line) + '}', font_size=size, color=color)
             for line in s.split('\n')]
    obj = VGroup(*lines).arrange(DOWN, buff=0.08)
    if width and obj.width > width:
        obj.scale_to_fit_width(width)
    return obj.move_to([x, y, 0])


def math(s, x, y, size=34, color=INK, width=None):
    obj = MathTex(s, font_size=size, color=color)
    if width and obj.width > width:
        obj.scale_to_fit_width(width)
    return obj.move_to([x, y, 0])


def arrow(a, b, color=MUTED, width=3):
    return Arrow([*a, 0], [*b, 0], buff=0.08, color=color,
                 stroke_width=width, max_tip_length_to_length_ratio=0.12)


def box(x, y, w, h, color=BLUE):
    return RoundedRectangle(width=w, height=h, corner_radius=0.18,
                            stroke_color=color, stroke_width=2,
                            fill_color=PALE, fill_opacity=0.6).move_to([x, y, 0])


def heading(scene, title, subtitle):
    scene.add(label(title, 0, 3.7, 36), label(subtitle, 0, 3.03, 23, MUTED, 14.5))
