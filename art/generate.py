#!/usr/bin/env python3
"""
XOVRATH — Unknown Artifacts. Generative artwork + metadata collection.
2,222 ERC-721 artifacts (#1-2222), BNB Smart Chain Mainnet (56).

SEED SCHEME (the only source of randomness):
  Every token is generated from its token id alone, plus one fixed
  collection salt. No wall-clock, no environment, no external input.
    SALT = 0x584F5652  ("XOVR" in ASCII, fixed constant)
    seed(token_id) = ((token_id * 2654435761) ^ SALT) & 0xFFFFFFFF
    rng = mulberry32(seed)  -- a small deterministic PRNG; the same
    token id always yields the same stream of floats in [0, 1).
  Trait assignment (classification) uses a single fixed balanced shuffle:
  a list with counts 371/371/370/370/370/370 is Fisher-Yates shuffled
  once with mulberry32(SALT), so the assignment is fully reproducible
  from the salt alone and every token id maps to exactly one slot.
  All geometry, colours, accent, background, form family and element
  counts are drawn from that token's own rng stream, in a fixed order,
  so re-running this script regenerates byte-identical files.

USAGE:
    python3 art/generate.py
  Regenerates collection/images/<id>.svg, collection/metadata/<id>.json,
  collection/collection.json and collection/all-tokens.json in place.
  Local only: no deploy, no upload, no IPFS pin, no network, no spend.

    python3 art/generate.py --only 1,56,9,288,13 --out /tmp/preview
  Preview mode: render only the listed token ids as SVGs into --out,
  without touching the collection. Use it to show samples before a
  full regeneration.

STYLE (v2, rebuilt from the reference posters the user sent):
  Flat 2D abstract surreal forms on black (#0a0a0b) or bone white
  (#ece7dc). Charcoal / silver / grey forms, restrained purple/blue/
  silver accent. Every poster is a large central form that dominates
  the canvas: layered translucent smoky masses with hollow voids, a
  big eclipse disc behind, echo outlines, thin orbit rings and
  hairlines ending in dots, scattered satellite dots, and one bold
  accent disc or cloudy wash. Forms are warped by a turbulence
  displacement filter so edges feel organic and smoky, and the whole
  poster carries heavy film grain. No humans, animals, mascots,
  PFP characters, realistic 3D, glossy 3D or excessive gradients.
  Poster furniture is real SVG text: "XOVRATH" top-left, "#NNN"
  top-right, "UNKNOWN FORMS." / "SAME EXISTENCE." bottom-left,
  4-point star bottom-right.
"""
import argparse
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter

SALT = 0x584F5652
TOTAL = 2222
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "collection")
IMG_DIR = os.path.join(OUT, "images")
META_DIR = os.path.join(OUT, "metadata")

CLASSIFICATIONS = ["VOID", "DISTORTION", "ORIGIN", "ANOMALY", "FRACTURE", "UNKNOWN"]
# 2222 = 6*370 + 2, so the first two classifications get one extra token.
CLASS_COUNTS = {"VOID": 371, "DISTORTION": 371, "ORIGIN": 370,
                "ANOMALY": 370, "FRACTURE": 370, "UNKNOWN": 370}
FORMS = ["Hollow Shard Lattice", "Monolith Eclipse", "Fluid Smoke Form",
         "Split Orb Blade", "Spiked Crown Lattice", "Fractured Monolith"]

BG_BLACK, BG_BONE = "#0a0a0b", "#ece7dc"
ACCENT_COLORS = {"Purple": ["#7b5cff", "#8b7bff"],
                 "Blue": ["#5b7cff"],
                 "Silver": ["#c0c0c8", "#9a9aa2"]}

DESCRIPTION = (
    "XOVRATH — Unknown Artifacts. A collection of 2,222 surreal-form "
    "artifacts on BNB Smart Chain: flat, abstract, experimental forms "
    "in black and bone white, touched by charcoal, silver and the "
    "occasional violet. Unknown forms. Same existence. No two artifacts "
    "share the same form."
)


# ---------------------------------------------------------------- PRNG ----
def mulberry32(seed):
    a = seed & 0xFFFFFFFF

    def rand():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (t | 61))) & 0xFFFFFFFF
        return (((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0)

    return rand


def seed_for(token_id):
    return ((token_id * 2654435761) ^ SALT) & 0xFFFFFFFF


def balanced_classifications():
    """Fixed balanced shuffle of the classification slots, seeded by SALT."""
    slots = []
    for c in CLASSIFICATIONS:
        slots.extend([c] * CLASS_COUNTS[c])
    rng = mulberry32(SALT)
    for i in range(len(slots) - 1, 0, -1):
        j = int(rng() * (i + 1))
        slots[i], slots[j] = slots[j], slots[i]
    return slots


# ------------------------------------------------------------- helpers ----
def f(v):
    """Compact number formatting: 1 decimal, drop trailing .0."""
    s = "%.1f" % v
    return s[:-2] if s.endswith(".0") else s


def pick(rng, items):
    return items[int(rng() * len(items))]


def _cos(a):
    import math
    return math.cos(a)


def _sin(a):
    import math
    return math.sin(a)


def blob_path(rng, cx, cy, r, points=9, wobble=0.35):
    """Closed wobbly blob path around (cx, cy), smoothed with quadratics."""
    pts = []
    for i in range(points):
        ang = 2 * 3.141592653589793 * i / points + rng() * 0.5
        rr = r * (1 - wobble + rng() * 2 * wobble)
        pts.append((cx + rr * _cos(ang), cy + rr * _sin(ang)))
    d = "M %s %s " % (f(pts[0][0]), f(pts[0][1]))
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        d += "Q %s %s %s %s " % (f(p[0]), f(p[1]), f(mx), f(my))
    return d + "Z"


def shard_points(rng, cx, cy, r, n=5):
    pts = []
    for i in range(n):
        ang = 2 * 3.141592653589793 * i / n + (rng() - 0.5) * 0.9
        rr = r * (0.55 + rng() * 0.65)
        pts.append("%s,%s" % (f(cx + rr * _cos(ang)), f(cy + rr * _sin(ang))))
    return " ".join(pts)


def star_path(cx, cy, r):
    """4-point star (diamond sparkle) centred at (cx, cy)."""
    return ("M %s %s L %s %s L %s %s L %s %s Z"
            % (f(cx), f(cy - r), f(cx + r * 0.28), f(cy - r * 0.28),
               f(cx + r), f(cy), f(cx + r * 0.28), f(cy + r * 0.28)))


def scale_points_str(pts_str, cx, cy, factor):
    """Scale a 'x,y x,y ...' polygon string around (cx, cy)."""
    out = []
    for pair in pts_str.split():
        x, y = pair.split(",")
        out.append("%s,%s" % (f(cx + (float(x) - cx) * factor),
                              f(cy + (float(y) - cy) * factor)))
    return " ".join(out)


def mirror_points_str(pts_str, y_axis):
    """Mirror a 'x,y x,y ...' polygon string across a horizontal axis."""
    out = []
    for pair in pts_str.split():
        x, y = pair.split(",")
        out.append("%s,%s" % (x, f(2 * y_axis - float(y))))
    return " ".join(out)


def add_dots(rng, els, cx, cy, rx, ry, n, color, rmin=1.5, rmax=5.5,
             omin=0.35, omax=0.9):
    """Scatter n small dots inside the ellipse around (cx, cy)."""
    for _ in range(n):
        ang = rng() * 6.283185307179586
        rr = (rng() ** 0.5)
        x = cx + rr * rx * _cos(ang)
        y = cy + rr * ry * _sin(ang)
        els.append('<circle cx="%s" cy="%s" r="%s" fill="%s" opacity="%s"/>'
                   % (f(x), f(y), f(rmin + rng() * (rmax - rmin)), color,
                      f(omin + rng() * (omax - omin))))
    return n


def add_ring(rng, els, cx, cy, rx, ry, color, op=0.6, w=1.2):
    """One thin orbit ellipse, slightly rotated."""
    els.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="none" '
               'stroke="%s" stroke-width="%s" opacity="%s" '
               'transform="rotate(%s %s %s)"/>'
               % (f(cx), f(cy), f(rx), f(ry), color, f(w), f(op),
                  f((rng() - 0.5) * 40), f(cx), f(cy)))
    return 1


def add_hairline_v(rng, els, x, y1, y2, color, op=0.55):
    """Vertical hairline with a dot at each end. Returns 3."""
    els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
               'stroke-width="1" opacity="%s"/>'
               % (f(x), f(y1), f(x), f(y2), color, f(op)))
    for y in (y1, y2):
        els.append('<circle cx="%s" cy="%s" r="%s" fill="%s" opacity="0.9"/>'
                   % (f(x), f(y), f(3 + rng() * 3), color))
    return 3


def add_hairline_diag(rng, els, x1, y1, x2, y2, color, op=0.55):
    """Diagonal hairline with a dot at each end. Returns 3."""
    els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
               'stroke-width="1" opacity="%s"/>'
               % (f(x1), f(y1), f(x2), f(y2), color, f(op)))
    for x, y in ((x1, y1), (x2, y2)):
        els.append('<circle cx="%s" cy="%s" r="%s" fill="%s" opacity="0.9"/>'
                   % (f(x), f(y), f(3 + rng() * 3), color))
    return 3


def add_ticks(rng, els, x, y, n, color, vertical=True, gap=14):
    """A barcode-like row of short ticks. Returns n."""
    for i in range(n):
        ln = 6 + rng() * 18
        if vertical:
            els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
                       'stroke-width="1.5" opacity="0.75"/>'
                       % (f(x), f(y + i * gap), f(x + ln), f(y + i * gap),
                          color))
        else:
            els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
                       'stroke-width="1.5" opacity="0.75"/>'
                       % (f(x + i * gap), f(y), f(x + i * gap), f(y + ln),
                          color))
    return n


# ------------------------------------------------------- form families ----
# v2: each builder echoes one reference poster — a large layered central
# form (25-45 elements) instead of the v1 handful of flat shapes.
# Signature: (rng, cx, cy, ink, ink2, bg, accent) -> (elements, count).
def form_hollow_shard(rng, cx, cy, ink, ink2, bg, accent):
    """Reference #001: smoky lattice veil with hollow voids, eclipse
    disc behind, orbit arcs, moon dot, hairline with end dots."""
    els, n = [], 0
    # eclipse disc behind the veil + echo outline
    dx, dy = cx + (rng() - 0.5) * 140, cy - 60 + (rng() - 0.5) * 140
    disc_r = 165 + rng() * 75
    els.append('<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="0.92"/>'
               % (f(dx), f(dy), f(disc_r), ink))
    n += 1
    els.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" '
               'stroke-width="1.5" opacity="0.5"/>'
               % (f(dx), f(dy), f(disc_r + 26), ink))
    n += 1
    # main veil: layered translucent blobs
    for i, op in enumerate((0.95, 0.7, 0.5)):
        bx = cx + (rng() - 0.5) * 150
        by = cy + (rng() - 0.5) * 180
        els.append('<path d="%s" fill="%s" fill-opacity="%s"/>'
                   % (blob_path(rng, bx, by, 185 - i * 30 + rng() * 60,
                                points=9), ink, f(op)))
        n += 1
    # hollow voids punched in background colour
    for _ in range(3):
        vx, vy = cx + (rng() - 0.5) * 220, cy + (rng() - 0.5) * 260
        els.append('<path d="%s" fill="%s"/>'
                   % (blob_path(rng, vx, vy, 55 + rng() * 55, points=7), bg))
        n += 1
    # shard lattice outlines over the veil
    big = shard_points(rng, cx, cy, 215 + rng() * 80)
    els.append('<polygon points="%s" fill="none" stroke="%s" stroke-width="2.5"/>'
               % (big, ink2))
    n += 1
    els.append('<polygon points="%s" fill="none" stroke="%s" stroke-width="1" '
               'opacity="0.6"/>'
               % (scale_points_str(big, cx, cy, 0.7), ink))
    n += 1
    # orbit arcs + moon dot
    n += add_ring(rng, els, cx, cy, 265 + rng() * 50, 95 + rng() * 40, ink, 0.5)
    n += add_ring(rng, els, cx, cy, 300 + rng() * 40, 130 + rng() * 40, ink2, 0.35)
    els.append('<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="0.85"/>'
               % (f(cx + 250 + rng() * 60), f(cy - 260 + rng() * 70),
                  f(16 + rng() * 16), ink2))
    n += 1
    # hairline with end dots, left side
    n += add_hairline_v(rng, els, 110 + rng() * 60, 300 + rng() * 80,
                        700 + rng() * 120, ink2, 0.5)
    # scattered satellite dots
    n += add_dots(rng, els, cx, cy, 330, 380, 9, ink2, 1.5, 5, 0.35, 0.85)
    # accent: one bold disc + a small echo
    if accent:
        ax, ay = cx + (rng() - 0.5) * 300, cy + (rng() - 0.5) * 320
        els.append('<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="0.9"/>'
                   % (f(ax), f(ay), f(22 + rng() * 26), accent))
        n += 1
        els.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" '
                   'stroke-width="1" opacity="0.6"/>'
                   % (f(ax), f(ay), f(34 + rng() * 20), accent))
        n += 1
    return els, n


def form_monolith_eclipse(rng, cx, cy, ink, ink2, bg, accent):
    """Reference #042: black eclipse disc, jagged rock spire, mirrored
    reflection, wide orbit ring, full-height axis with end dots."""
    els, n = [], 0
    # eclipse disc + echo outline, upper third
    disc_r = 120 + rng() * 70
    dx, dy = cx + (rng() - 0.5) * 70, cy - 190 + rng() * 60
    els.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>'
               % (f(dx), f(dy), f(disc_r), ink))
    n += 1
    els.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" '
               'stroke-width="1" opacity="0.45"/>'
               % (f(dx), f(dy), f(disc_r + 20), ink))
    n += 1
    # full-height vertical axis + end dots
    ax = cx + (rng() - 0.5) * 50
    n += add_hairline_v(rng, els, ax, 130, 1000, ink, 0.5)
    # jagged spire: three stacked shard masses, darker toward the base
    base_y = cy - 40
    for i, op in enumerate((0.95, 0.8, 0.62)):
        sp = shard_points(rng, cx + (rng() - 0.5) * 60,
                          base_y - i * 70, 130 - i * 18, n=6)
        els.append('<polygon points="%s" fill="%s" fill-opacity="%s"/>'
                   % (sp, ink, f(op)))
        n += 1
    # mirrored reflection below the waterline
    axis_y = cy + 130
    for i, op in enumerate((0.45, 0.32, 0.22)):
        sp = shard_points(rng, cx + (rng() - 0.5) * 60,
                          base_y - i * 70, 130 - i * 18, n=6)
        els.append('<polygon points="%s" fill="%s" fill-opacity="%s"/>'
                   % (mirror_points_str(sp, axis_y), ink, f(op)))
        n += 1
    # waterlines: horizontal hairlines of shrinking length
    for i in range(4):
        w = 300 - i * 55 + rng() * 40
        y = axis_y - 12 + i * 26
        els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
                   'stroke-width="1" opacity="%s"/>'
                   % (f(cx - w / 2), f(y), f(cx + w / 2), f(y), ink,
                      f(0.7 - i * 0.15)))
        n += 1
    # wide orbit ring around the middle
    n += add_ring(rng, els, cx, axis_y - 10, 250 + rng() * 60,
                  42 + rng() * 22, ink, 0.55)
    # barcode ticks, right edge
    n += add_ticks(rng, els, 790 + rng() * 30, 620 + rng() * 80, 5, ink2)
    # scattered dots
    n += add_dots(rng, els, cx, cy, 320, 380, 7, ink2, 1.5, 5, 0.35, 0.85)
    if accent:
        ox, oy = cx + (rng() - 0.5) * 320, cy + (rng() - 0.5) * 380
        els.append('<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="0.9"/>'
                   % (f(ox), f(oy), f(12 + rng() * 16), accent))
        n += 1
    return els, n


def form_fluid_smoke(rng, cx, cy, ink, ink2, bg, accent):
    """Reference #087: twisting smoke ribbon, bold accent disc behind,
    diagonal hairline, drifting rings, satellite dots."""
    els, n = [], 0
    # bold accent disc behind the smoke (or a large ink outline disc)
    if accent:
        ax, ay = cx - 90 + rng() * 120, cy - 130 + rng() * 120
        els.append('<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="0.92"/>'
                   % (f(ax), f(ay), f(85 + rng() * 45), accent))
        n += 1
    else:
        els.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" '
                   'stroke-width="1.5" opacity="0.5"/>'
                   % (f(cx - 60), f(cy - 120), f(110 + rng() * 40), ink))
        n += 1
    # smoke ribbon: layered translucent blobs along a diagonal drift
    for i, op in enumerate((0.95, 0.72, 0.52, 0.35)):
        bx = cx + (i - 1.5) * (60 + rng() * 40) + (rng() - 0.5) * 60
        by = cy + (i - 1.5) * (70 + rng() * 40) + (rng() - 0.5) * 60
        els.append('<path d="%s" fill="%s" fill-opacity="%s"/>'
                   % (blob_path(rng, bx, by, 120 + rng() * 90, points=9),
                      ink, f(op)))
        n += 1
    # hollow voids inside the smoke
    for _ in range(2):
        vx, vy = cx + (rng() - 0.5) * 220, cy + (rng() - 0.5) * 260
        els.append('<path d="%s" fill="%s"/>'
                   % (blob_path(rng, vx, vy, 45 + rng() * 45, points=7), bg))
        n += 1
    # drifting rings
    n += add_ring(rng, els, cx + (rng() - 0.5) * 160, cy + (rng() - 0.5) * 200,
                  55 + rng() * 45, 55 + rng() * 45, ink, 0.65)
    n += add_ring(rng, els, cx + (rng() - 0.5) * 200, cy + (rng() - 0.5) * 240,
                  80 + rng() * 50, 40 + rng() * 30, ink2, 0.4)
    # diagonal hairline across the whole canvas + end dots
    x1, y1 = 140 + rng() * 80, 180 + rng() * 120
    x2, y2 = 700 + rng() * 60, 900 + rng() * 80
    n += add_hairline_diag(rng, els, x1, y1, x2, y2, ink2, 0.5)
    # satellite dots
    n += add_dots(rng, els, cx, cy, 330, 390, 9, ink2, 1.5, 5, 0.35, 0.85)
    # small accent blob inside the smoke
    if accent:
        bx, by = cx + (rng() - 0.5) * 200, cy + (rng() - 0.5) * 240
        els.append('<path d="%s" fill="%s" fill-opacity="0.8"/>'
                   % (blob_path(rng, bx, by, 55 + rng() * 45, points=7),
                      accent))
        n += 1
    return els, n


def form_split_orb(rng, cx, cy, ink, ink2, bg, accent):
    """Reference #126: big textured orb, vertical blade slicing it, bold
    accent wash inside the slice, spike above, hairlines, top dot."""
    els, n = [], 0
    orr = 175 + rng() * 60
    ox, oy = cx + (rng() - 0.5) * 50, cy + (rng() - 0.5) * 50
    # orb + cloudy texture blobs on it
    els.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>'
               % (f(ox), f(oy), f(orr), ink))
    n += 1
    for op, col in ((0.3, ink2), (0.22, bg), (0.35, ink2)):
        tx, ty = ox + (rng() - 0.5) * 160, oy + (rng() - 0.5) * 160
        els.append('<path d="%s" fill="%s" fill-opacity="%s"/>'
                   % (blob_path(rng, tx, ty, 70 + rng() * 60, points=8),
                      col, f(op)))
        n += 1
    # echo ring around the orb
    els.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" '
               'stroke-width="1" opacity="0.5"/>'
               % (f(ox), f(oy), f(orr + 18), ink))
    n += 1
    # blade: long thin triangle slicing the orb, background-filled
    ang = (rng() - 0.5) * 0.5
    dx, dy = _cos(ang + 1.5708), _sin(ang + 1.5708)
    L = orr * 2.4
    bx, by = ox + (rng() - 0.5) * 30, oy + (rng() - 0.5) * 30
    w = 16 + rng() * 20
    px, py = -dy * w, dx * w
    els.append('<polygon points="%s,%s %s,%s %s,%s" fill="%s"/>'
               % (f(bx - dx * L + px), f(by - dy * L + py),
                  f(bx + dx * L + px), f(by + dy * L + py),
                  f(bx + dx * L - px), f(by + dy * L - py), bg))
    n += 1
    # blade edge hairlines
    els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
               'stroke-width="1" opacity="0.7"/>'
               % (f(bx - dx * L), f(by - dy * L), f(bx + dx * L),
                  f(by + dy * L), ink))
    n += 1
    els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
               'stroke-width="1" opacity="0.45"/>'
               % (f(bx - dx * L + px * 2), f(by - dy * L + py * 2),
                  f(bx + dx * L + px * 2), f(by + dy * L + py * 2), ink2))
    n += 1
    # bold accent wash inside the slice (or a grey wash without accent)
    wash = accent if accent else ink2
    wop = 0.6 if accent else 0.35
    els.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" '
               'fill-opacity="%s" transform="rotate(%s %s %s)"/>'
               % (f(bx - 34), f(by - 190), f(68 + rng() * 30),
                  f(380 + rng() * 60), wash, f(wop), f(ang * 57.3),
                  f(bx), f(by)))
    n += 1
    # spike above the orb
    els.append('<polygon points="%s,%s %s,%s %s,%s" fill="%s"/>'
               % (f(ox - 12), f(oy - orr - 130), f(ox + 12),
                  f(oy - orr - 130), f(ox), f(oy - orr + 30), ink))
    n += 1
    # top dot + side hairlines with end dots
    els.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>'
               % (f(ox + 190 + rng() * 60), f(oy - 240 + rng() * 60),
                  f(15 + rng() * 12), ink))
    n += 1
    n += add_hairline_v(rng, els, 120 + rng() * 50, 260 + rng() * 60,
                        880 + rng() * 60, ink2, 0.5)
    n += add_hairline_v(rng, els, 780 + rng() * 40, 300 + rng() * 80,
                        850 + rng() * 80, ink2, 0.45)
    # satellite dots
    n += add_dots(rng, els, cx, cy, 330, 380, 6, ink2, 1.5, 5, 0.35, 0.85)
    return els, n


def form_spiked_crown(rng, cx, cy, ink, ink2, bg, accent):
    """Reference #203: symmetrical spiky crown lattice, hollow core,
    radial hairlines, side orbit rings, tip dots, axis dots."""
    els, n = [], 0
    spikes = 8 + int(rng() * 3)
    r_out = 195 + rng() * 70
    r_in = r_out * (0.45 + rng() * 0.12)
    pts, tips = [], []
    for i in range(spikes * 2):
        ang = 3.141592653589793 * i / spikes - 1.5708 + (rng() - 0.5) * 0.1
        rr = r_out if i % 2 == 0 else r_in
        x, y = cx + rr * _cos(ang), cy + rr * _sin(ang)
        pts.append("%s,%s" % (f(x), f(y)))
        if i % 2 == 0:
            tips.append((x, y))
    els.append('<polygon points="%s" fill="%s" fill-opacity="0.93"/>'
               % (" ".join(pts), ink))
    n += 1
    # inner echo crown
    els.append('<polygon points="%s" fill="none" stroke="%s" stroke-width="1.5" '
               'opacity="0.65"/>'
               % (scale_points_str(" ".join(pts), cx, cy, 0.68), ink2))
    n += 1
    # hollow core voids
    els.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s"/>'
               % (f(cx), f(cy), f(r_in * 0.42), f(r_in * 0.58), bg))
    n += 1
    els.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="none" '
               'stroke="%s" stroke-width="1" opacity="0.6"/>'
               % (f(cx), f(cy), f(r_in * 0.62), f(r_in * 0.78), bg))
    n += 1
    # radial hairlines from the core outward
    for _ in range(6):
        ang = rng() * 6.283185307179586
        x1, y1 = cx + r_in * 0.5 * _cos(ang), cy + r_in * 0.5 * _sin(ang)
        x2, y2 = cx + (r_out + 55) * _cos(ang), cy + (r_out + 55) * _sin(ang)
        els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
                   'stroke-width="1" opacity="0.45"/>'
                   % (f(x1), f(y1), f(x2), f(y2), ink2))
        n += 1
    # side orbit rings
    for side in (-1, 1):
        rx = cx + side * (r_out + 95 + rng() * 40)
        ry = cy + (rng() - 0.5) * 160
        els.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" '
                   'stroke-width="1.5" opacity="0.7"/>'
                   % (f(rx), f(ry), f(36 + rng() * 30), ink))
        n += 1
    # dots on the spike tips
    for tx, ty in tips[:5]:
        els.append('<circle cx="%s" cy="%s" r="%s" fill="%s" opacity="0.9"/>'
                   % (f(tx), f(ty), f(3 + rng() * 3), bg))
        n += 1
    # vertical axis with end dots
    n += add_hairline_v(rng, els, cx + (rng() - 0.5) * 30, 150, 990, ink2, 0.45)
    # satellite dots
    n += add_dots(rng, els, cx, cy, 330, 380, 6, ink2, 1.5, 5, 0.35, 0.85)
    if accent:
        els.append('<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="0.9"/>'
                   % (f(cx), f(cy - r_out - 45 + rng() * 40),
                      f(11 + rng() * 12), accent))
        n += 1
    return els, n


def form_fractured_monolith(rng, cx, cy, ink, ink2, bg, accent):
    """Reference #318: rocky fractured mass, tall black slabs, bold
    cloudy accent block, ticked hairline, barcode ticks, dots."""
    els, n = [], 0
    # rocky mass: overlapping translucent blobs, left of centre
    for i, op in enumerate((0.95, 0.72, 0.5)):
        bx = cx - 90 + (rng() - 0.5) * 120
        by = cy + (i - 1) * 130 + (rng() - 0.5) * 60
        els.append('<path d="%s" fill="%s" fill-opacity="%s"/>'
                   % (blob_path(rng, bx, by, 130 + rng() * 70, points=9),
                      ink, f(op)))
        n += 1
    # tall black slabs
    for i in range(2):
        w = 95 + rng() * 55
        h = 430 + rng() * 180
        x = cx - 40 + i * 110 + (rng() - 0.5) * 40
        els.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>'
                   % (f(x), f(cy - h / 2 + rng() * 60), f(w), f(h),
                      ink if i == 0 else ink2))
        n += 1
        els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
                   'stroke-width="1" opacity="0.6"/>'
                   % (f(x), f(cy - h / 2), f(x), f(cy + h / 2), ink2))
        n += 1
    # crack lines across the slabs
    for _ in range(3):
        x1 = cx + (rng() - 0.5) * 260
        els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
                   'stroke-width="1.5" opacity="0.8"/>'
                   % (f(x1), f(cy - 300), f(x1 + (rng() - 0.5) * 130),
                      f(cy + 300), ink2))
        n += 1
    # bold cloudy accent block (or a grey block without accent)
    wash = accent if accent else ink2
    wop = 0.72 if accent else 0.4
    ax = cx + 60 + (rng() - 0.5) * 80
    ay = cy - 60 + (rng() - 0.5) * 120
    els.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" '
               'fill-opacity="%s"/>'
               % (f(ax), f(ay), f(150 + rng() * 60), f(240 + rng() * 90),
                  wash, f(wop)))
    n += 1
    for _ in range(2):
        bx, by = ax + rng() * 150, ay + rng() * 200
        els.append('<path d="%s" fill="%s" fill-opacity="0.55"/>'
                   % (blob_path(rng, bx, by, 60 + rng() * 50, points=7),
                      wash))
        n += 1
    # ticked hairline, left edge
    tx = 110 + rng() * 50
    els.append('<line x1="%s" y1="220" x2="%s" y2="900" stroke="%s" '
               'stroke-width="1" opacity="0.5"/>'
               % (f(tx), f(tx), ink2))
    n += 1
    n += add_ticks(rng, els, tx - 8, 300 + rng() * 60, 5, ink2)
    # barcode ticks, right edge
    n += add_ticks(rng, els, 790 + rng() * 30, 620 + rng() * 80, 5, ink2)
    # satellite dots
    n += add_dots(rng, els, cx, cy, 330, 380, 7, ink2, 1.5, 5, 0.35, 0.85)
    return els, n


FORM_BUILDERS = {
    "Hollow Shard Lattice": form_hollow_shard,
    "Monolith Eclipse": form_monolith_eclipse,
    "Fluid Smoke Form": form_fluid_smoke,
    "Split Orb Blade": form_split_orb,
    "Spiked Crown Lattice": form_spiked_crown,
    "Fractured Monolith": form_fractured_monolith,
}


# ------------------------------------------------------------ token build ----
def build_token(token_id, classification):
    rng = mulberry32(seed_for(token_id))
    background = "Black" if rng() < 0.55 else "Bone White"
    dark = background == "Black"
    bg = BG_BLACK if dark else BG_BONE
    ink = "#c9c9c2" if dark else "#1c1c1a"      # main form colour
    ink2 = "#8f8f88" if dark else "#555550"     # secondary grey
    text = "#b5b5ae" if dark else "#3d3d39"
    # accent roll: None 55% / Purple 25% / Blue 12% / Silver 8%
    a = rng()
    if a < 0.55:
        accent_name, accent = "None", None
    elif a < 0.80:
        accent_name, accent = "Purple", pick(rng, ACCENT_COLORS["Purple"])
    elif a < 0.92:
        accent_name, accent = "Blue", pick(rng, ACCENT_COLORS["Blue"])
    else:
        accent_name, accent = "Silver", pick(rng, ACCENT_COLORS["Silver"])
    form = pick(rng, FORMS)

    # asymmetric composition centre + slight rotation
    cx = 450 + (rng() - 0.5) * 220
    cy = 545 + (rng() - 0.5) * 170
    rot = (rng() - 0.5) * 24

    els, count = FORM_BUILDERS[form](rng, cx, cy, ink, ink2, bg, accent)
    # top up with dust dots / hairlines / rings so every token is dense
    target = min(56, max(26, count + int(rng() * 4)))
    while count < target:
        r = rng()
        if r < 0.5:
            count += add_dots(rng, els, cx, cy, 330, 380, 1, ink2, 1.5, 5,
                              0.35, 0.85)
        elif r < 0.8:
            x = 120 + rng() * 660
            els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
                       'stroke-width="1" opacity="0.45"/>'
                       % (f(x), f(180 + rng() * 650),
                          f(x + (rng() - 0.5) * 90), f(180 + rng() * 650),
                          ink2))
            count += 1
        else:
            count += add_ring(rng, els, cx + (rng() - 0.5) * 200,
                              cy + (rng() - 0.5) * 240, 60 + rng() * 80,
                              30 + rng() * 40, ink2, 0.35)

    # turbulence displacement warps the form edges so they feel organic
    # and smoky, like the reference posters; seed is token-derived.
    defs = (
        '<defs>'
        '<filter id="warp" x="-20%%" y="-20%%" width="140%%" height="140%%">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.012 0.02" '
        'numOctaves="3" seed="%d" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="55"/>'
        '</filter>'
        '<filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.9" '
        'numOctaves="2" stitchTiles="stitch"/>'
        '<feColorMatrix type="saturate" values="0"/></filter>'
        '<filter id="g2"><feTurbulence type="fractalNoise" baseFrequency="0.02" '
        'numOctaves="4" seed="3" stitchTiles="stitch"/>'
        '<feColorMatrix type="saturate" values="0"/></filter>'
        '</defs>'
        % (token_id % 97)
    )
    grain = (
        '<rect width="900" height="1125" filter="url(#g)" opacity="0.07"/>'
        '<rect width="900" height="1125" filter="url(#g2)" opacity="0.06"/>'
    )
    body = "".join(els)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 1125" '
        'width="900" height="1125">%s'
        '<rect width="900" height="1125" fill="%s"/>'
        '<g transform="rotate(%s 450 545)"><g filter="url(#warp)">%s</g></g>%s'
        '<text x="48" y="64" font-family="Helvetica, Arial, sans-serif" '
        'font-size="20" letter-spacing="5" fill="%s">XOVRATH</text>'
        '<text x="852" y="64" text-anchor="end" font-family="Helvetica, Arial, '
        'sans-serif" font-size="20" letter-spacing="4" fill="%s">#%03d</text>'
        '<text x="48" y="1008" font-family="Helvetica, Arial, sans-serif" '
        'font-size="15" letter-spacing="3" fill="%s">UNKNOWN FORMS.</text>'
        '<text x="48" y="1034" font-family="Helvetica, Arial, sans-serif" '
        'font-size="15" letter-spacing="3" fill="%s">SAME EXISTENCE.</text>'
        '<path d="%s" fill="%s"/>'
        '</svg>'
        % (defs, bg, f(rot), body, grain, text, text, token_id, text, text,
           star_path(846, 1020, 16), text)
    )
    record = {
        "id": token_id,
        "classification": classification,
        "background": background,
        "form": form,
        "accent": accent_name,
        "elements": count,
        "svg": svg,
    }
    return record


def metadata_for(rec):
    return {
        "name": "XOVRATH — Artifact #%04d" % rec["id"],
        "description": DESCRIPTION,
        # Storage is GitHub (chosen 30 Okt 2026), NOT IPFS: the image
        # field points at the public repo's raw file URL.
        "image": "https://raw.githubusercontent.com/nugian10/XOVRATH/main/collection/images/%d.svg" % rec["id"],
        "attributes": [
            {"trait_type": "Classification", "value": rec["classification"]},
            {"trait_type": "Background", "value": rec["background"]},
            {"trait_type": "Form", "value": rec["form"]},
            {"trait_type": "Accent", "value": rec["accent"]},
            {"trait_type": "Elements", "value": rec["elements"]},
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="",
                    help="comma-separated token ids: preview mode, SVGs only")
    ap.add_argument("--out", default="",
                    help="preview output dir for --only (default: ./preview)")
    args = ap.parse_args()
    slots = balanced_classifications()
    if args.only:
        ids = [int(s) for s in args.only.split(",") if s.strip()]
        out_dir = args.out or os.path.join(BASE, "preview")
        os.makedirs(out_dir, exist_ok=True)
        for token_id in ids:
            rec = build_token(token_id, slots[token_id - 1])
            path = os.path.join(out_dir, "%d.svg" % token_id)
            with open(path, "w") as fh:
                fh.write(rec["svg"])
            try:
                ET.fromstring(rec["svg"])
                xml_ok = "XML ok"
            except ET.ParseError as e:
                xml_ok = "XML FAIL: %s" % e
            print("#%d %s / %s / %s / %d elements / %d bytes / %s"
                  % (token_id, rec["form"], rec["background"], rec["accent"],
                     rec["elements"], len(rec["svg"]), xml_ok))
        print("Preview SVGs in %s" % out_dir)
        return
    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(META_DIR, exist_ok=True)
    tokens = []
    for token_id in range(1, TOTAL + 1):
        rec = build_token(token_id, slots[token_id - 1])
        sha = hashlib.sha256(rec["svg"].encode("utf-8")).hexdigest()
        with open(os.path.join(IMG_DIR, "%d.svg" % token_id), "w") as fh:
            fh.write(rec["svg"])
        with open(os.path.join(META_DIR, "%d.json" % token_id), "w") as fh:
            json.dump(metadata_for(rec), fh, indent=2)
            fh.write("\n")
        tokens.append({
            "id": rec["id"],
            "classification": rec["classification"],
            "background": rec["background"],
            "form": rec["form"],
            "accent": rec["accent"],
            "elements": rec["elements"],
            "sha256": sha,
        })
    with open(os.path.join(OUT, "all-tokens.json"), "w") as fh:
        json.dump(tokens, fh, indent=2)
        fh.write("\n")
    summary = {
        "total": TOTAL,
        "classifications": dict(Counter(t["classification"] for t in tokens)),
        "backgrounds": dict(Counter(t["background"] for t in tokens)),
        "accents": dict(Counter(t["accent"] for t in tokens)),
        "forms": dict(Counter(t["form"] for t in tokens)),
        "generator": "art/generate.py",
        "seed": ("token id only — mulberry32(seed = "
                 "((token_id * 2654435761) ^ 0x584F5652) & 0xFFFFFFFF); "
                 "classification slots are a fixed balanced shuffle "
                 "seeded by the same salt 0x584F5652"),
        "contract": {"status": "not deployed", "address": ""},
    }
    with open(os.path.join(OUT, "collection.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")
    print("Generated %d tokens." % TOTAL)
    print("classifications:", summary["classifications"])
    print("backgrounds:", summary["backgrounds"])
    print("accents:", summary["accents"])
    print("forms:", summary["forms"])
    print("distinct SVG hashes:", len({t["sha256"] for t in tokens}))


if __name__ == "__main__":
    main()
