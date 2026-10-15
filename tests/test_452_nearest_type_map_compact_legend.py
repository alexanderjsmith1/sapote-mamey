"""nearest_type_strain_map.py layout (card 018c0f08_452_nearest_type_map_compact_legend): page height from the tip
count, genera without a palette colour pooled as one 'Other genera' legend entry (named in RUN_INFO), italic genus
names in the legend, 8 pt. Synthetic five-tip and forty-tip trees."""
import json
from pathlib import Path
from pypdf import PdfReader
from tools import nearest_type_strain_map as m


def write(tmp_path, n, names):
    tips = [f"t{i}" for i in range(n)]
    nwk = "(" + ",".join(f"{t}:0.{(i % 9) + 1}" for i, t in enumerate(tips)) + ");\n"
    tree = tmp_path / "a.contree"; tree.write_text(nwk)
    anchors = tmp_path / "a.tsv"
    anchors.write_text("tip\tdeposited_organism_name\n" + "".join(f"{t}\t{names[i % len(names)]} sp{i}\n" for i, t in enumerate(tips)))
    mp = tmp_path / "m.tsv"
    mp.write_text("isolate\tanchor_tip\thost_as_recorded\n" + "".join(f"SYN-{970 + i}\t{t}\tHost {i % 2}\n" for i, t in enumerate(tips)))
    return tree, anchors, mp


def render(tmp_path, n, names):
    t, a, mp = write(tmp_path, n, names)
    out = tmp_path / "out"
    assert m.main(["--tree", str(t), "--anchors", str(a), "--isolate-map", str(mp), "--out", str(out)]) == 0
    return out


def test_height_follows_tip_count(tmp_path):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    out5 = render(tmp_path / "a", 5, ["Streptomyces"])
    out40 = render(tmp_path / "b", 40, ["Streptomyces"])
    h = lambda o: float(PdfReader(o / "nearest_type_strain_map.pdf").pages[0].mediabox.height) / 72
    assert h(out40) <= 40 * 0.17 + 0.45 + 0.5 + 5 * 0.19 + 0.12 + 0.01   # rows + axis + legend + top, no slack
    assert h(out5) >= 3.8 - 0.01


def test_unpaletted_genera_pool_as_other(tmp_path):
    out = render(tmp_path, 6, ["Streptomyces", "Zzgenusone", "Zzgenustwo"])
    info = json.loads((out / "RUN_INFO.json").read_text())
    assert info["other_genera"] == ["Zzgenusone", "Zzgenustwo"]
    page = PdfReader(out / "nearest_type_strain_map.pdf").pages[0]
    sizes = []
    text = page.extract_text(visitor_text=lambda t, cm, tm, f, s: sizes.append(s) if t.strip() else None)
    assert "Other genera" in text and min(sizes) >= 8
