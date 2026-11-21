"""Renders a captcha code as a small distorted SVG (no imaging dependency)."""

from __future__ import annotations

import base64
import random

WIDTH, HEIGHT = 120, 40
_COLORS = ("#1f6feb", "#8250df", "#bf3989", "#1a7f37", "#9a6700", "#cf222e")


def render_svg(code: str, rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#f6f8fa"/>',
    ]
    for _ in range(5):  # noise lines
        x1, y1, x2, y2 = rng.randint(0, WIDTH), rng.randint(0, HEIGHT), rng.randint(0, WIDTH), rng.randint(0, HEIGHT)
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{rng.choice(_COLORS)}" stroke-opacity="0.45"/>'
        )
    step = WIDTH / (len(code) + 1)
    for i, ch in enumerate(code):
        x, y = step * (i + 1) + rng.randint(-3, 3), 27 + rng.randint(-4, 4)
        angle, size = rng.randint(-25, 25), rng.randint(22, 28)
        parts.append(
            f'<text x="{x:.0f}" y="{y}" font-family="monospace" font-weight="bold" font-size="{size}" '
            f'fill="{rng.choice(_COLORS)}" transform="rotate({angle} {x:.0f} {y})">{ch}</text>'
        )
    for _ in range(25):  # noise dots
        parts.append(
            f'<circle cx="{rng.randint(0, WIDTH)}" cy="{rng.randint(0, HEIGHT)}" r="1" fill="{rng.choice(_COLORS)}"/>'
        )
    parts.append("</svg>")
    return "".join(parts)


def data_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
