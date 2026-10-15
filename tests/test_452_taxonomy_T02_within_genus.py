"""T02 within-genus pairwise 16S identity: pair table method and the two layouts (synthetic data only)."""
import csv
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "taxonomy_T02_within_genus.py"


def run(*args, ok=True):
    p = subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True)
    if ok:
        assert p.returncode == 0, p.stderr
    return p


def write(path, text):
    path.write_text(text)
    return path


def base_seq(n=900, seed=1):
    rng = random.Random(seed)
    return "".join(rng.choice("ACGT") for _ in range(n))


def mutate(seq, positions):
    s = list(seq)
    for i in positions:
        s[i] = {"A": "C", "C": "G", "G": "T", "T": "A"}[s[i]]
    return "".join(s)


def pairs_table(tmp, seqs, genera, extra=()):
    fa = write(tmp / "in.fasta", "".join(f">{k}\n{v}\n" for k, v in seqs.items()))
    gt = write(tmp / "genera.tsv", "strain\tgenus\n" + "".join(f"{k}\t{v}\n" for k, v in genera.items()))
    out = tmp / "pairs.tsv"
    run("pairs", "--fasta", fa, "--genera", gt, "--out", out, *extra)
    return {(r["a"], r["b"]): r for r in csv.DictReader(out.open(), delimiter="\t")}


def test_identity_counts_mismatches_and_skips_ambiguous_columns(tmp_path):
    s = base_seq()
    amb = list(s); amb[100] = "N"; amb[200] = "R"
    seqs = {"SYN-970": s, "SYN-971": mutate(s, [10, 20, 30]), "SYN-972": "".join(amb)}
    rows = pairs_table(tmp_path, seqs, {k: "Genus_a" for k in seqs})
    assert rows[("SYN-970", "SYN-971")]["identical"] == "897"
    assert rows[("SYN-970", "SYN-971")]["percent_identity"] == "99.667"
    r = rows[("SYN-970", "SYN-972")]
    assert (r["compared"], r["identical"], r["percent_identity"]) == ("898", "898", "100.000")


def test_identity_is_over_the_overlap_only(tmp_path):
    s = base_seq(1200)
    seqs = {"SYN-973": s, "SYN-974": s[300:1000]}
    r = pairs_table(tmp_path, seqs, {k: "Genus_a" for k in seqs})[("SYN-973", "SYN-974")]
    assert (r["overlap_columns"], r["compared"], r["percent_identity"], r["short_overlap"]) == ("700", "700", "100.000", "0")


def test_short_overlap_is_flagged_not_dropped(tmp_path):
    s = base_seq(1200)
    seqs = {"SYN-975": s, "SYN-976": s[:400]}
    r = pairs_table(tmp_path, seqs, {k: "Genus_a" for k in seqs})[("SYN-975", "SYN-976")]
    assert r["short_overlap"] == "1" and r["percent_identity"] == "100.000"


def test_same_genus_only_and_receipt(tmp_path):
    s = base_seq()
    seqs = {"SYN-977": s, "SYN-978": s, "SYN-979": s}
    rows = pairs_table(tmp_path, seqs, {"SYN-977": "Genus_a", "SYN-978": "Genus_a", "SYN-979": "Genus_b"}, ["--same-genus-only"])
    assert list(rows) == [("SYN-977", "SYN-978")]
    rec = json.loads((tmp_path / "pairs.tsv.run.json").read_text())
    assert rec["pairs"] == 1 and len(rec["inputs"]) == 3


def test_pairs_refuses_missing_sequence_and_overwrite(tmp_path):
    fa = write(tmp_path / "in.fasta", ">SYN-980\nACGT\n")
    gt = write(tmp_path / "g.tsv", "strain\tgenus\nSYN-980\tGenus_a\nSYN-981\tGenus_a\n")
    p = run("pairs", "--fasta", fa, "--genera", gt, "--out", tmp_path / "o.tsv", ok=False)
    assert p.returncode == 2 and "SYN-981" in p.stderr
    write(tmp_path / "o2.tsv", "x")
    gt2 = write(tmp_path / "g2.tsv", "strain\tgenus\nSYN-980\tGenus_a\n")
    p = run("pairs", "--fasta", fa, "--genera", gt2, "--out", tmp_path / "o2.tsv", ok=False)
    assert p.returncode == 2 and "overwrite" in p.stderr


def synthetic_pairs(tmp):
    rows = ["a\tb\tgenus_a\tgenus_b\tpercent_identity\tshort_overlap"]
    rng = random.Random(3)
    big = [f"SYN-{990 + i}" for i in range(8)]
    for i in range(len(big)):
        for j in range(i + 1, len(big)):
            rows.append(f"{big[i]}\t{big[j]}\tStreptomyces\tStreptomyces\t{rng.uniform(96, 100):.3f}\t0")
    rows += ["SYN-1000\tSYN-1001\tGenus_b\tGenus_b\t94.500\t0", "SYN-1000\tSYN-1002\tGenus_b\tGenus_b\t97.000\t0",
             "SYN-1001\tSYN-1002\tGenus_b\tGenus_b\t88.000\t1", "SYN-990\tSYN-1000\tStreptomyces\tGenus_b\t85.000\t0"]
    return write(tmp / "pairs.tsv", "\n".join(rows) + "\n")


def test_render_refuses_hiding_pairs(tmp_path):
    p = run("render", "--pairs", synthetic_pairs(tmp_path), "--out", tmp_path / "f", "--x-min", "95", ok=False)
    assert p.returncode == 2 and "hide" in p.stderr


def test_render_refuses_duplicate_pairs(tmp_path):
    t = write(tmp_path / "p.tsv", "a\tb\tgenus_a\tgenus_b\tpercent_identity\tshort_overlap\n"
              "SYN-990\tSYN-991\tG\tG\t99\t0\nSYN-991\tSYN-990\tG\tG\t99\t0\n")
    p = run("render", "--pairs", t, "--out", tmp_path / "f", ok=False)
    assert p.returncode == 2 and "duplicate" in p.stderr


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
@pytest.mark.parametrize("layout", ["facets", "overlay"])
def test_render_layouts_counts_and_8pt(tmp_path, layout):
    out = tmp_path / f"T02_{layout}"
    run("render", "--pairs", synthetic_pairs(tmp_path), "--out", out, "--layout", layout, "--print-width", "3.5")
    for suffix in (".png", ".pdf"):
        assert out.with_suffix(suffix).exists()
    nums = dict(csv.reader(out.with_name(out.name + "_numbers.tsv").open(), delimiter="\t"))
    assert nums["genus:Streptomyces:pairs"] == "28" and nums["genus:Streptomyces:isolates"] == "8"
    assert nums["genus:Genus_b:pairs"] == "2" and nums["dropped:short_overlap"] == "1"
    assert nums["dropped:different_genus"] == "1" and nums["x_min"] == "94.25"
    check = json.loads(out.with_name(out.name + "_min_text_check.json").read_text())
    assert check["status"] == "PASS" and check["smallest_pt"] >= 8
    p = run("render", "--pairs", tmp_path / "pairs.tsv", "--out", out, "--layout", layout, ok=False)
    assert p.returncode == 2 and "overwrite" in p.stderr
