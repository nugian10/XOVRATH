#!/usr/bin/env python3
"""Verify the XOVRATH collection. Exit non-zero on any failure."""
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "collection")
IMG_DIR = os.path.join(OUT, "images")
META_DIR = os.path.join(OUT, "metadata")
fails = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


imgs = sorted(os.listdir(IMG_DIR), key=lambda s: int(s[:-4]))
metas = sorted(os.listdir(META_DIR), key=lambda s: int(s[:-5]))
check(len(imgs) == 2222, "images count == 2222 (got %d)" % len(imgs))
check(len(metas) == 2222, "metadata count == 2222 (got %d)" % len(metas))
check(imgs == ["%d.svg" % i for i in range(1, 2223)], "image filenames 1..2222.svg")
check(metas == ["%d.json" % i for i in range(1, 2223)], "metadata filenames 1..2222.json")

hashes, tokens = set(), []
max_size = 0
for i in range(1, 2223):
    path = os.path.join(IMG_DIR, "%d.svg" % i)
    data = open(path, "rb").read()
    max_size = max(max_size, len(data))
    hashes.add(hashlib.sha256(data).hexdigest())
    try:
        ET.fromstring(data)
    except ET.ParseError as e:
        fails.append("SVG %d not valid XML: %s" % (i, e))
    if ("#%03d" % i) not in data.decode("utf-8"):
        fails.append("SVG %d missing its own token number" % i)
    if b'viewBox="0 0 900 1125"' not in data:
        fails.append("SVG %d missing viewBox 0 0 900 1125" % i)
    for needle in (b"XOVRATH", b"UNKNOWN FORMS.", b"SAME EXISTENCE."):
        if needle not in data:
            fails.append("SVG %d missing furniture %r" % (i, needle))
    m = json.load(open(os.path.join(META_DIR, "%d.json" % i)))
    if m["name"] != "XOVRATH — Artifact #%04d" % i:
        fails.append("metadata %d bad name" % i)
    if m["image"] != "https://raw.githubusercontent.com/nugian10/XOVRATH/main/collection/images/%d.svg" % i:
        fails.append("metadata %d bad image field" % i)
    attrs = {a["trait_type"]: a["value"] for a in m["attributes"]}
    tokens.append({"id": i, "classification": attrs["Classification"],
                   "background": attrs["Background"], "form": attrs["Form"],
                   "accent": attrs["Accent"], "elements": attrs["Elements"],
                   "sha256": hashlib.sha256(data).hexdigest()})
    if not (10 <= attrs["Elements"] <= 70):
        fails.append("token %d elements out of range: %s" % (i, attrs["Elements"]))

check(len(hashes) == 2222, "2222 distinct SVG SHA-256 hashes (got %d)" % len(hashes))
check(max_size < 30 * 1024, "largest SVG under 30 KB (%d bytes)" % max_size)

coll = json.load(open(os.path.join(OUT, "collection.json")))
alltok = json.load(open(os.path.join(OUT, "all-tokens.json")))
check(coll["total"] == 2222, "collection.json total == 2222")
check(coll["contract"] == {"status": "not deployed", "address": ""},
      "contract status not deployed, address empty")
for key, field in (("classifications", "classification"),
                   ("backgrounds", "background"), ("accents", "accent"),
                   ("forms", "form")):
    got = dict(Counter(t[field] for t in tokens))
    check(coll[key] == got, "collection.json %s matches metadata (%s)" % (key, got))
    check(sum(got.values()) == 2222, "%s sums to 2222" % key)
check([t["id"] for t in alltok] == list(range(1, 2223)), "all-tokens.json ids 1..2222 sorted")
check(alltok == tokens, "all-tokens.json matches generated records")

# banned strings anywhere in the collection
banned = ["0.0002", "0.0008"]
hits = []
for root, _, files in os.walk(OUT):
    for fn in files:
        p = os.path.join(root, fn)
        data = open(p, "rb").read()
        for b in banned:
            if b.encode() in data:
                hits.append((p, b))
check(not hits, "banned price strings absent (hits: %s)" % hits)

print("XML/metadata parse failures: %d" % len(fails))
if fails:
    for f_ in fails[:20]:
        print("  FAIL:", f_)
    sys.exit(1)
print("ALL CHECKS PASSED")
