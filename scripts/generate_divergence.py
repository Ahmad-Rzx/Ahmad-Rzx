#!/usr/bin/env python3
"""
Future Gadget Laboratory — Divergence Meter SVG Generator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generates a nixie-tube-style divergence meter SVG for GitHub README display.
Inspired by TriggersTools.SteinsGate (https://github.com/trigger-death/TriggersTools.SteinsGate)
Web tool: https://trigger-testing.github.io/pwa-examples/divergence-meter/

Usage:
    python generate_divergence.py [reading] [output_path]

    reading     Divergence reading string  (default: "0.571046")
    output_path Path to write SVG file     (default: "assets/divergence_meter.svg")

Example:
    python generate_divergence.py "1.048596" "assets/divergence_meter.svg"

El Psy Kongroo.
"""

import sys
import os
from datetime import datetime, timezone


# ─── Tube geometry ────────────────────────────────────────────────────────────
TW  = 78    # tube width  (px)
TH  = 152   # tube height (px)
GAP = 9     # gap between tubes
PX  = 30    # horizontal padding (device casing)
PY  = 32    # vertical padding


def _defs() -> str:
    return """  <defs>
    <!-- Warm nixie glow: two-pass blur + merge -->
    <filter id="glow" x="-40%" y="-40%" width="180%" height="180%"
            color-interpolation-filters="sRGB">
      <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="blur1"/>
      <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur2"/>
      <feMerge>
        <feMergeNode in="blur1"/>
        <feMergeNode in="blur2"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <!-- Small sharp glow for dot indicator -->
    <filter id="dot-glow" x="-60%" y="-60%" width="220%" height="220%"
            color-interpolation-filters="sRGB">
      <feGaussianBlur in="SourceGraphic" stdDeviation="3.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <!-- Glass tube interior: warm dark radial gradient -->
    <radialGradient id="glass" cx="36%" cy="26%" r="80%" fx="32%" fy="22%">
      <stop offset="0%"   stop-color="#2e1600"/>
      <stop offset="40%"  stop-color="#170a00"/>
      <stop offset="100%" stop-color="#080400"/>
    </radialGradient>

    <!-- Subtle left-edge shine (like light refracting through glass) -->
    <linearGradient id="shine" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%"   stop-color="#ffffff" stop-opacity="0.11"/>
      <stop offset="22%"  stop-color="#ffffff" stop-opacity="0.05"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0.00"/>
    </linearGradient>

    <!-- Ambient orange haze filling the tube -->
    <linearGradient id="haze" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%"   stop-color="#ff6200" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#cc3300" stop-opacity="0.05"/>
    </linearGradient>
  </defs>"""


def _tube(x: int, y: int) -> str:
    """Draw the glass tube body (background, haze, shine)."""
    parts = []
    # Outer glass
    parts.append(
        f'  <rect x="{x}" y="{y}" width="{TW}" height="{TH}" rx="6" ry="6" '
        f'fill="url(#glass)" stroke="#5a2d00" stroke-width="1.6"/>'
    )
    # Ambient orange haze
    parts.append(
        f'  <rect x="{x+3}" y="{y+3}" width="{TW-6}" height="{TH-6}" rx="4" ry="4" '
        f'fill="url(#haze)"/>'
    )
    # Left-edge glass shine
    parts.append(
        f'  <rect x="{x+4}" y="{y+4}" width="{TW//3}" height="{TH-8}" rx="3" ry="3" '
        f'fill="url(#shine)"/>'
    )
    return "\n".join(parts)


def _digit(ch: str, x: int, y: int) -> str:
    """Draw a digit (or symbol) inside the tube."""
    cx = x + TW // 2
    # Baseline sits roughly 62% down the tube
    ty = y + int(TH * 0.64)

    # Outer halo (large blur, low opacity) — warm corona
    halo = (
        f'  <text x="{cx}" y="{ty}" text-anchor="middle" '
        f'font-family="&quot;Courier New&quot;, Courier, monospace" '
        f'font-size="90" font-weight="bold" '
        f'fill="#ff5500" opacity="0.30" filter="url(#glow)">{ch}</text>'
    )
    # Core digit
    core = (
        f'  <text x="{cx}" y="{ty}" text-anchor="middle" '
        f'font-family="&quot;Courier New&quot;, Courier, monospace" '
        f'font-size="90" font-weight="bold" '
        f'fill="#ff8c00" opacity="0.95">{ch}</text>'
    )
    # Bright highlight (the hottest part of the filament)
    highlight = (
        f'  <text x="{cx}" y="{ty}" text-anchor="middle" '
        f'font-family="&quot;Courier New&quot;, Courier, monospace" '
        f'font-size="90" font-weight="bold" '
        f'fill="#ffd080" opacity="0.38">{ch}</text>'
    )
    return "\n".join([halo, core, highlight])


def _dot(x: int, y: int) -> str:
    """Draw a decimal point tube."""
    cx  = x + TW // 2
    cy  = y + int(TH * 0.72)
    parts = [
        # Corona
        f'  <circle cx="{cx}" cy="{cy}" r="14" fill="#ff5500" opacity="0.20" filter="url(#dot-glow)"/>',
        # Main circle
        f'  <circle cx="{cx}" cy="{cy}" r="9"  fill="#ff8c00" opacity="0.95" filter="url(#dot-glow)"/>',
        # Hotspot
        f'  <circle cx="{cx}" cy="{cy}" r="5"  fill="#ffd080" opacity="0.85"/>',
    ]
    return "\n".join(parts)


def _connector_pins(x: int, y: int) -> str:
    """Decorative bottom connector pins (like real nixie tube base)."""
    pins = []
    n_pins = 4
    pin_r  = 2.4
    start_x = x + (TW - (n_pins - 1) * 12) // 2
    pin_y  = y + TH - 8
    for i in range(n_pins):
        px_ = start_x + i * 12
        pins.append(
            f'  <circle cx="{px_}" cy="{pin_y}" r="{pin_r}" '
            f'fill="#1e0e00" stroke="#6b3800" stroke-width="0.8"/>'
        )
    return "\n".join(pins)


def build_svg(reading: str) -> str:
    """Build a complete nixie-tube divergence meter SVG for the given reading string."""
    chars = list(reading)
    n     = len(chars)

    W = PX * 2 + n * TW + (n - 1) * GAP
    H = PY * 2 + TH

    now_utc = datetime.now(timezone.utc)
    sync_label = now_utc.strftime("%d %b %Y").upper()

    lines: list[str] = []

    # ── SVG root ──────────────────────────────────────────────────────────
    lines.append(
        f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Divergence Meter: {reading}">'
    )
    lines.append(f'  <!-- Generated {now_utc.isoformat()} by Future Gadget Lab -->')
    lines.append(f'  <!-- TriggersTools.SteinsGate: https://github.com/trigger-death/TriggersTools.SteinsGate -->')
    lines.append("")

    # ── Defs ──────────────────────────────────────────────────────────────
    lines.append(_defs())
    lines.append("")

    # ── Device casing ─────────────────────────────────────────────────────
    lines.append(f'  <!-- Device casing -->')
    lines.append(f'  <rect width="{W}" height="{H}" rx="12" ry="12" fill="#060401"/>')
    # Outer border
    lines.append(
        f'  <rect x="1" y="1" width="{W-2}" height="{H-2}" rx="11" ry="11" '
        f'fill="none" stroke="#4a2200" stroke-width="1.5" opacity="0.8"/>'
    )
    # Inner subtle groove
    lines.append(
        f'  <rect x="3" y="3" width="{W-6}" height="{H-6}" rx="9" ry="9" '
        f'fill="none" stroke="#2a1200" stroke-width="1" opacity="0.5"/>'
    )
    lines.append("")

    # ── Top label ─────────────────────────────────────────────────────────
    lines.append(f'  <!-- Top label -->')
    lines.append(
        f'  <text x="{W//2}" y="17" text-anchor="middle" '
        f'font-family="&quot;Courier New&quot;, Courier, monospace" '
        f'font-size="7.5" fill="#9a5500" letter-spacing="3.5" opacity="0.85">'
        f'DIVERGENCE  METER</text>'
    )
    lines.append("")

    # ── Nixie tubes ───────────────────────────────────────────────────────
    lines.append(f'  <!-- Nixie tubes -->')
    for i, ch in enumerate(chars):
        tx = PX + i * (TW + GAP)
        ty = PY

        lines.append(f'  <!-- Tube {i}: {ch!r} -->')
        lines.append(_tube(tx, ty))

        if ch == '.':
            lines.append(_dot(tx, ty))
        else:
            lines.append(_digit(ch, tx, ty))

        lines.append(_connector_pins(tx, ty))
        lines.append("")

    # ── Bottom sync timestamp ──────────────────────────────────────────────
    lines.append(f'  <!-- Sync timestamp -->')
    lines.append(
        f'  <text x="{W//2}" y="{H - 8}" text-anchor="middle" '
        f'font-family="&quot;Courier New&quot;, Courier, monospace" '
        f'font-size="7" fill="#7a4200" letter-spacing="2" opacity="0.7">'
        f'LAST SYNC : {sync_label}</text>'
    )

    lines.append('</svg>')
    return "\n".join(lines)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    reading  = sys.argv[1] if len(sys.argv) > 1 else "0.571046"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "assets/divergence_meter.svg"

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    svg = build_svg(reading)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"[FGL] Divergence meter  :  {reading!r}")
    print(f"[FGL] Output path       :  {out_path}")
    print(f"[FGL] El Psy Kongroo.")
