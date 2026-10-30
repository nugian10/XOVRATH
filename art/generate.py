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

STYLE:
  Flat 2D abstract surreal forms on black (#0a0a0b) or bone white
  (#ece7dc). Charcoal / silver / grey forms, restrained purple/blue/
  silver accent, subtle feTurbulence grain. No humans, animals, mascots,
  PFP characters, realistic 3D, glossy 3D or excessive gradients.
  Poster furniture is real SVG text: "XOVRATH" top-left, "#NNN"
  top-right, "UNKNOWN FORMS." / "SAME EXISTENCE." bottom-left,
  4-point star bottom-right.
"""
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


def _cos(a):
    import math
    return math.cos(a)


def _sin(a):
    import math
    return math.sin(a)


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


# ------------------------------------------------------- form families ----
def form_hollow_shard(rng, cx, cy, ink, bg, accent):
    """Overlapping shard outlines with hollow voids, thin orbit lines."""
    els, n = [], 0
    big = shard_points(rng, cx, cy, 210 + rng() * 90)
    els.append('<polygon points="%s" fill="none" stroke="%s" stroke-width="3"/>'
               % (big, ink))
    n += 1
    for _ in range(1):
        sx, sy = cx + (rng() - 0.5) * 260, cy + (rng() - 0.5) * 300
        els.append('<polygon points="%s" fill="%s" fill-opacity="0.85" '
                   'stroke="%s" stroke-width="2"/>'
                   % (shard_points(rng, sx, sy, 90 + rng() * 90), ink, bg))
        n += 1
    # hollow voids punched in background colour
    for _ in range(1):
        vx, vy = cx + (rng() - 0.5) * 220, cy + (rng() - 0.5) * 260
        els.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s"/>'
                   % (f(vx), f(vy), f(45 + rng() * 55), f(30 + rng() * 45), bg))
        n += 1
    # thin orbit arc
    els.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="none" '
               'stroke="%s" stroke-width="1" opacity="0.55" '
               'transform="rotate(%s %s %s)"/>'
               % (f(cx), f(cy), f(260 + rng() * 60), f(90 + rng() * 40),
                  ink, f((rng() - 0.5) * 50), f(cx), f(cy)))
    n += 1
    if accent:
        ax, ay = cx + (rng() - 0.5) * 300, cy + (rng() - 0.5) * 320
        els.append('<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="0.9"/>'
                   % (f(ax), f(ay), f(26 + rng() * 30), accent))
        n += 1
    return els, n


def form_monolith_eclipse(rng, cx, cy, ink, bg, accent):
    """Big eclipse disc behind a tall slab, thin vertical axis, small orb."""
    els, n = [], 0
    disc_r = 150 + rng() * 90
    els.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>'
               % (f(cx + (rng() - 0.5) * 80), f(cy - 60 + rng() * 60),
                  f(disc_r), ink))
    n += 1
    sw, sh = 70 + rng() * 70, 380 + rng() * 220
    sx = cx + (rng() - 0.5) * 120 - sw / 2
    els.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>'
               % (f(sx), f(cy - sh / 2 + rng() * 80), f(sw), f(sh), bg))
    n += 1
    # slab edge line + thin vertical axis through the whole composition
    els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
               'stroke-width="1.5" opacity="0.8"/>'
               % (f(sx), f(cy - sh / 2), f(sx), f(cy + sh / 2), ink))
    n += 1
    els.append('<line x1="%s" y1="150" x2="%s" y2="980" stroke="%s" '
               'stroke-width="1" opacity="0.5"/>'
               % (f(cx + (rng() - 0.5) * 40), f(cx + (rng() - 0.5) * 40), ink))
    n += 1
    ox, oy = cx + (rng() - 0.5) * 320, cy + (rng() - 0.5) * 380
    els.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>'
               % (f(ox), f(oy), f(10 + rng() * 26),
                  accent if accent else ink))
    n += 1
    return els, n


def form_fluid_smoke(rng, cx, cy, ink, bg, accent):
    """Layered wavy smoke blobs, overlapping translucent washes."""
    els, n = [], 0
    tones = [ink, ink, ink]
    for i in range(3):
        bx = cx + (rng() - 0.5) * 220
        by = cy + (rng() - 0.5) * 260
        op = 0.9 - i * 0.22
        els.append('<path d="%s" fill="%s" fill-opacity="%s"/>'
                   % (blob_path(rng, bx, by, 130 + rng() * 110,
                                points=8 + int(rng() * 4)), tones[i], f(op)))
        n += 1
    # a hollow ring drifting through the smoke
    rx, ry = cx + (rng() - 0.5) * 200, cy + (rng() - 0.5) * 240
    els.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" '
               'stroke-width="2" opacity="0.7"/>'
               % (f(rx), f(ry), f(40 + rng() * 60), ink))
    n += 1
    if accent:
        ax, ay = cx + (rng() - 0.5) * 240, cy + (rng() - 0.5) * 280
        els.append('<path d="%s" fill="%s" fill-opacity="0.75"/>'
                   % (blob_path(rng, ax, ay, 70 + rng() * 60, points=7),
                      accent))
        n += 1
    return els, n


def form_split_orb(rng, cx, cy, ink, bg, accent):
    """A large orb cut by a diagonal blade, shards and dots around it."""
    els, n = [], 0
    orr = 150 + rng() * 80
    ox, oy = cx + (rng() - 0.5) * 60, cy + (rng() - 0.5) * 60
    els.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>'
               % (f(ox), f(oy), f(orr), ink))
    n += 1
    # blade: long thin triangle slicing the orb
    ang = (rng() - 0.5) * 1.2
    dx, dy = _cos(ang + 1.5708), _sin(ang + 1.5708)
    L = orr * 2.3
    bx, by = ox + (rng() - 0.5) * 40, oy + (rng() - 0.5) * 40
    w = 14 + rng() * 22
    px, py = -dy * w, dx * w
    els.append('<polygon points="%s,%s %s,%s %s,%s" fill="%s"/>'
               % (f(bx - dx * L + px), f(by - dy * L + py),
                  f(bx + dx * L + px), f(by + dy * L + py),
                  f(bx + dx * L - px), f(by + dy * L - py), bg))
    n += 1
    # counter-slice line
    els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
               'stroke-width="1.5" opacity="0.7"/>'
               % (f(bx - dx * L), f(by - dy * L), f(bx + dx * L),
                  f(by + dy * L), ink))
    n += 1
    for _ in range(2):
        dx2, dy2 = cx + (rng() - 0.5) * 360, cy + (rng() - 0.5) * 420
        els.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>'
                   % (f(dx2), f(dy2), f(5 + rng() * 16),
                      accent if accent and rng() < 0.6 else ink))
        n += 1
    return els, n


def form_spiked_crown(rng, cx, cy, ink, bg, accent):
    """Radial spiked crown lattice with a hollow core and side rings."""
    els, n = [], 0
    spikes = 7 + int(rng() * 4)
    r_out = 200 + rng() * 90
    r_in = r_out * (0.45 + rng() * 0.15)
    pts = []
    for i in range(spikes * 2):
        ang = 3.141592653589793 * i / spikes + (rng() - 0.5) * 0.12
        rr = r_out if i % 2 == 0 else r_in
        pts.append("%s,%s" % (f(cx + rr * _cos(ang)), f(cy + rr * _sin(ang))))
    els.append('<polygon points="%s" fill="%s" fill-opacity="0.92"/>'
               % (" ".join(pts), ink))
    n += 1
    els.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s"/>'
               % (f(cx), f(cy), f(r_in * 0.45), f(r_in * 0.6), bg))
    n += 1
    for side in (-1, 1):
        rx = cx + side * (r_out + 60 + rng() * 60)
        ry = cy + (rng() - 0.5) * 200
        els.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" '
                   'stroke-width="1.5" opacity="0.7"/>'
                   % (f(rx), f(ry), f(34 + rng() * 40), ink))
        n += 1
    if accent:
        els.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>'
                   % (f(cx), f(cy - r_out - 40 + rng() * 40),
                      f(12 + rng() * 14), accent))
        n += 1
    return els, n


def form_fractured_monolith(rng, cx, cy, ink, bg, accent):
    """Stacked fractured slabs with crack lines and one accent block."""
    els, n = [], 0
    y = cy - 260 + rng() * 80
    for i in range(3):
        w = 170 + rng() * 140
        h = 90 + rng() * 110
        x = cx - w / 2 + (rng() - 0.5) * 130
        jag = shard_points(rng, x + w / 2, y + h / 2, w * 0.42, n=4)
        els.append('<polygon points="%s" fill="%s" fill-opacity="%s"/>'
                   % (jag, ink, f(0.95 - i * 0.18)))
        n += 1
        y += h * 0.8
    # crack line
    for _ in range(1):
        x1 = cx + (rng() - 0.5) * 260
        els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
                   'stroke-width="1.5" opacity="0.8"/>'
                   % (f(x1), f(cy - 300), f(x1 + (rng() - 0.5) * 120),
                      f(cy + 300), ink))
        n += 1
    if accent:
        ax = cx + (rng() - 0.5) * 220
        els.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" '
                   'fill-opacity="0.85"/>'
                   % (f(ax), f(cy - 100 + rng() * 120), f(60 + rng() * 60),
                      f(90 + rng() * 90), accent))
        n += 1
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

    els, count = FORM_BUILDERS[form](rng, cx, cy, ink, bg, accent)
    # top up with dust dots / hairlines so every token has 2-5 elements
    target = min(5, max(2, count + int(rng() * 2)))
    while count < target:
        if rng() < 0.5:
            els.append('<circle cx="%s" cy="%s" r="%s" fill="%s" '
                       'opacity="0.8"/>'
                       % (f(120 + rng() * 660), f(180 + rng() * 700),
                          f(2 + rng() * 6), ink2))
        else:
            x = 120 + rng() * 660
            els.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
                       'stroke-width="1" opacity="0.45"/>'
                       % (f(x), f(180 + rng() * 650), f(x + (rng() - 0.5) * 90),
                          f(180 + rng() * 650), ink2))
        count += 1

    grain = (
        '<filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.9" '
        'numOctaves="2" stitchTiles="stitch"/>'
        '<feColorMatrix type="saturate" values="0"/></filter>'
        '<rect width="900" height="1125" filter="url(#g)" opacity="0.06"/>'
    )
    body = "".join(els)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 1125" '
        'width="900" height="1125">'
        '<rect width="900" height="1125" fill="%s"/>'
        '<g transform="rotate(%s 450 545)">%s</g>%s'
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
        % (bg, f(rot), body, grain, text, text, token_id, text, text,
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
    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(META_DIR, exist_ok=True)
    slots = balanced_classifications()
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
