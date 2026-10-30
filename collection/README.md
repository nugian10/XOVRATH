# XOVRATH — Unknown Artifacts — Collection

2,222 generative SVG artworks + ERC-721 metadata, built locally.
No contract is deployed, nothing is pushed to GitHub yet, nothing is minted.
Storage is GitHub (chosen 30 Okt 2026), not IPFS.

## What was built

- `images/<id>.svg` — 2,222 portrait posters (viewBox `0 0 900 1125`),
  flat 2D abstract surreal forms on black or bone-white backgrounds,
  charcoal/silver/grey with restrained purple/blue/silver accent,
  subtle `feTurbulence` grain, and real SVG poster furniture:
  `XOVRATH` top-left, `#NNN` top-right, `UNKNOWN FORMS.` /
  `SAME EXISTENCE.` bottom-left, 4-point star bottom-right.
- `metadata/<id>.json` — ERC-721 metadata per token. Name
  `XOVRATH — Artifact #0001`, fixed collection description, image
  `https://raw.githubusercontent.com/nugian10/XOVRATH/main/collection/images/<id>.svg`
  (public GitHub repo storage).
  Attributes (Classification, Background, Form, Accent, Elements) are
  derived from the same seeded record as the SVG, so they always match.
- `collection.json` — totals and exact trait distributions.
- `all-tokens.json` — all 2,222 tokens with traits + SHA-256 of each SVG.

## Regenerate (one command)

```bash
python3 ~/workspace/projects/xovrath/art/generate.py
```

Python 3, standard library only. Re-running regenerates byte-identical
files (verified: two runs produce identical SHA-256 sums for all files).

Verify with:

```bash
python3 ~/workspace/projects/xovrath/art/verify.py
```

## Seed scheme

Deterministic, seeded only by token id plus one fixed collection salt:

- `SALT = 0x584F5652` ("XOVR")
- `seed(token_id) = ((token_id * 2654435761) ^ SALT) & 0xFFFFFFFF`
- `rng = mulberry32(seed)` — all geometry, colours, background, accent,
  form family and element counts come from that token's own stream.
- Classification slots are a single fixed balanced shuffle (counts
  371/371/370/370/370/370) made once with `mulberry32(SALT)`.

## Counts (verified)

- Classifications: VOID 371, DISTORTION 371, ORIGIN 370, ANOMALY 370,
  FRACTURE 370, UNKNOWN 370 (total 2,222)
- Backgrounds: Black 1,205 (54.2%), Bone White 1,017 (45.8%)
- Accents: None 1,238 (55.7%), Purple 536 (24.1%), Blue 258 (11.6%),
  Silver 190 (8.6%)
- Forms: Hollow Shard Lattice 371, Split Orb Blade 408,
  Fluid Smoke Form 386, Spiked Crown Lattice 362,
  Monolith Eclipse 355, Fractured Monolith 340
- 2,222 distinct SVG SHA-256 hashes (no duplicates)
- Largest SVG 2,388 bytes; total collection size 18 MB
- No price strings anywhere in the collection files

## Still missing (not done here, by design)

- **GitHub push** of this collection to public repo `nugian10/XOVRATH`
  — metadata `image` fields already point at the raw GitHub URLs.
- **Smart contract deploy** — contract exists at
  `contracts/XovrathNFT.sol`, status `not deployed`, no address.
  After deploy, set the contract's baseURI to the GitHub metadata folder:
  `https://raw.githubusercontent.com/nugian10/XOVRATH/main/collection/metadata/`
- **Website** — built separately in `site/`; it reads `collection.json`
  and `all-tokens.json` from this folder.
