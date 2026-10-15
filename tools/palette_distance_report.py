#!/usr/bin/env python3
"""Colour-difference report for the genus colours one figure set uses (CIEDE2000, sRGB D65), optionally also as seen
with colour-vision deficiencies.

For each genus: its colour, where it comes from (the named set, else the house default, else the fallback), CIELAB
lightness and chroma. Then every pair, closest first. Fails (exit 1) when a genus falls back to the fallback colour,
when a colour is grey-like (chroma below --min-chroma) and not listed in --grey-ok, or when two genera are closer than
--min-de. --grey-ok names keys meant to be grey, e.g. the "no 16S genus on record" key.

--cvd protan deutan tritan adds each pair's difference as seen with those deficiencies (Machado, Oliveira & Fernandes
2009, severity 1.0). These are reported, not failed, unless --min-de-cvd is given; --cvd-pair A,B then limits that
threshold to the named pairs, so a figure's key neighbours can be held apart without failing every distant pair.

  python tools/palette_distance_report.py --set attine --genera Streptomyces,Pseudonocardia,... --out report.tsv
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path

try:  # CSV formula-cell guard (mamey/csv_safety.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

PALETTE = Path(__file__).resolve().parents[1] / "mamey" / "data" / "genus_palette.json"


def lab(hexcol: str) -> tuple[float, float, float]:
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = lambda c: ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92  # noqa: E731
    r, g, b = lin(r), lin(g), lin(b)
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
    f = lambda v: v ** (1 / 3) if v > 0.008856 else 7.787 * v + 16 / 116  # noqa: E731
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


# colour-vision deficiency simulation (Machado, Oliveira & Fernandes 2009, severity 1.0), applied in linear sRGB
CVD = {"protan": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
       "deutan": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
       "tritan": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900))}


def simulate(hexcol: str, kind: str) -> str:
    """The colour as seen with a colour-vision deficiency (protan, deutan or tritan), as hex."""
    lin = lambda c: ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92  # noqa: E731
    enc = lambda c: 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055  # noqa: E731
    rgb = [lin(int(hexcol[i:i + 2], 16) / 255) for i in (1, 3, 5)]
    out = [min(1.0, max(0.0, sum(m * v for m, v in zip(row, rgb)))) for row in CVD[kind]]
    return "#" + "".join(f"{round(enc(c) * 255):02X}" for c in out)


def chroma(hexcol: str) -> float:
    _, a, b = lab(hexcol)
    return math.hypot(a, b)


def de2000(h1: str, h2: str) -> float:
    """CIEDE2000 colour difference of two hex colours (Sharma, Wu & Dalal 2005)."""
    (L1, a1, b1), (L2, a2, b2) = lab(h1), lab(h2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p, h2p = math.degrees(math.atan2(b1, a1p)) % 360, math.degrees(math.atan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dh = 0.0
    elif abs(h2p - h1p) <= 180:
        dh = h2p - h1p
    else:
        dh = h2p - h1p - 360 if h2p > h1p else h2p - h1p + 360
    dH = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lb, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hb = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hb = (h1p + h2p) / 2
    else:
        hb = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hb - 30)) + 0.24 * math.cos(math.radians(2 * hb))
         + 0.32 * math.cos(math.radians(3 * hb + 6)) - 0.20 * math.cos(math.radians(4 * hb - 63)))
    SL = 1 + 0.015 * (Lb - 50) ** 2 / math.sqrt(20 + (Lb - 50) ** 2)
    SC, SH = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    RT = -2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-((hb - 275) / 25) ** 2)))
    return math.sqrt((dL / SL) ** 2 + (dC / SC) ** 2 + (dH / SH) ** 2 + RT * (dC / SC) * (dH / SH))


def resolve(palette: dict, set_name: str | None, genera, extra: dict | None = None) -> list[dict]:
    """One row per genus: colour and its source (set, house default, fallback)."""
    s = (palette.get("sets") or {}).get(set_name or "", {})
    rows = []
    for g in genera:
        if extra and g in extra:
            c, src = extra[g], "given"
        elif g in s:
            c, src = s[g], f"set:{set_name}"
        elif g in palette["default"]:
            c, src = palette["default"][g], "house"
        else:
            c, src = palette["fallback"], "FALLBACK"
        L, _, _ = lab(c)
        rows.append({"genus": g, "colour": c.upper(), "source": src, "L": round(L, 1), "chroma": round(chroma(c), 1)})
    return rows


def check(rows, min_de: float = 10.0, min_chroma: float = 25.0, grey_ok=(), cvd=(), min_de_cvd=None,
          cvd_pairs=None) -> tuple[list[dict], list[str]]:
    """-> (pairs closest first, failures). cvd: deficiency kinds to simulate; each pair also gets its difference as seen
    with each, and min_de_cvd (when given) fails a pair below it, for every pair or only the cvd_pairs named."""
    pairs = []
    for x, y in itertools.combinations(rows, 2):
        p = {"a": x["genus"], "b": y["genus"], "dE00": round(de2000(x["colour"], y["colour"]), 1)}
        for k in cvd:
            p[f"dE00_{k}"] = round(de2000(simulate(x["colour"], k), simulate(y["colour"], k)), 1)
        pairs.append(p)
    pairs.sort(key=lambda p: p["dE00"])
    fails = [f'{r["genus"]}: fallback colour' for r in rows if r["source"] == "FALLBACK"]
    fails += [f'{r["genus"]}: grey-like (chroma {r["chroma"]} < {min_chroma})' for r in rows
              if r["chroma"] < min_chroma and r["genus"] not in grey_ok]
    fails += [f'{p["a"]} / {p["b"]}: dE00 {p["dE00"]} < {min_de}' for p in pairs if p["dE00"] < min_de]
    if cvd and min_de_cvd is not None:
        named = {frozenset(q) for q in (cvd_pairs or [])}
        for p in pairs:
            if named and frozenset((p["a"], p["b"])) not in named:
                continue
            for k in cvd:
                if p[f"dE00_{k}"] < min_de_cvd:
                    fails.append(f'{p["a"]} / {p["b"]}: dE00 as seen with {k} {p[f"dE00_{k}"]} < {min_de_cvd}')
    return pairs, fails


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--palette", type=Path, default=PALETTE)
    ap.add_argument("--set", default=None, help="palette set, e.g. attine")
    ap.add_argument("--genera", required=True, help="comma-separated genera (and family labels) the figures use")
    ap.add_argument("--key", action="append", default=[], help="extra key NAME=#hex drawn by the figures (e.g. a no-genus key)")
    ap.add_argument("--grey-ok", default="", help="comma-separated keys allowed to be grey")
    ap.add_argument("--min-de", type=float, default=10.0)
    ap.add_argument("--min-chroma", type=float, default=25.0)
    ap.add_argument("--cvd", nargs="*", default=[], choices=sorted(CVD), help="also report each pair as seen with these "
                    "colour-vision deficiencies (Machado et al. 2009)")
    ap.add_argument("--min-de-cvd", type=float, default=None, help="with --cvd: fail a pair below this simulated dE00")
    ap.add_argument("--cvd-pair", action="append", default=[], help="with --min-de-cvd: check only these pairs, A,B "
                    "(repeat); default every pair")
    ap.add_argument("--out", type=Path, required=True, help="report TSV; a .md summary is written beside it")
    a = ap.parse_args(argv)
    extra = dict(k.split("=", 1) for k in a.key)
    genera = [g.strip() for g in a.genera.split(",") if g.strip()] + list(extra)
    rows = resolve(json.loads(a.palette.read_text()), a.set, genera, extra)
    pairs, fails = check(rows, a.min_de, a.min_chroma, {g.strip() for g in a.grey_ok.split(",") if g.strip()}, a.cvd,
                         a.min_de_cvd, [tuple(q.split(",", 1)) for q in a.cvd_pair])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=["genus", "colour", "source", "L", "chroma"], delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(rows)
        fh.write("\n")
        w = _SafeDictWriter(fh, fieldnames=["a", "b", "dE00"] + [f"dE00_{k}" for k in a.cvd], delimiter="\t",
                            lineterminator="\n")
        w.writeheader(); w.writerows(pairs)
    md = [f"# Colour-difference report ({a.set or 'house'} set, CIEDE2000)", "",
          f"{len(rows)} keys; thresholds dE00 >= {a.min_de}, chroma >= {a.min_chroma} (grey allowed: {a.grey_ok or 'none'}).", "",
          "| Key | Colour | Source | L | Chroma |", "|---|---|---|---|---|"]
    md += [f'| {r["genus"]} | {r["colour"]} | {r["source"]} | {r["L"]} | {r["chroma"]} |' for r in rows]
    md += ["", "Closest pairs: " + "; ".join(f'{p["a"]} / {p["b"]} {p["dE00"]}' for p in pairs[:8]) + "."]
    for k in a.cvd:
        worst = sorted(pairs, key=lambda p: p[f"dE00_{k}"])[:8]
        md += ["", f"Closest pairs as seen with {k}: " + "; ".join(f'{p["a"]} / {p["b"]} {p[f"dE00_{k}"]}' for p in worst) + "."]
    md += ["",
           "Result: " + ("PASS." if not fails else "FAIL: " + "; ".join(fails) + ".")]
    a.out.with_suffix(".md").write_text("\n".join(md) + "\n")
    print("\n".join(md[-3:]))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
