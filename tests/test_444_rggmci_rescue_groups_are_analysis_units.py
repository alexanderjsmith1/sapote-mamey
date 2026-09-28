"""RG-GMCI candidate groups are one analysis unit: one GenBank file per group, read fragment by fragment.

Before, every gene-reading tool took one antiSMASH region at a time. A rescued fragment measured alone had the genes on
its partner reported as missing, and read as "a genuine biological difference" (Alex, 2026-09-27: clinker pages show
half of a pathway). The engine now writes each group's regions into one file, and `cluster_completeness` reads such a
file per fragment and together.
"""
import csv
import importlib.util
import json
import random
import subprocess
import sys
import zipfile
from pathlib import Path

from mamey.rescue_groups import GROUP_LABEL, candidate_groups, read_members, write_group_genbanks

ROOT = Path(__file__).resolve().parents[1]


def _pair(a, ca, b, cb, conf="HIGH_RG_GMCI_RESCUE"):
    return {"pair": f"{a}+{b}", "bgc_a": a, "bgc_b": b, "contig_a": ca, "contig_b": cb, "edge_a": "Edge",
            "edge_b": "Full-contig", "products_a": "NRPS", "products_b": "NRPS", "rggmci_confidence": conf}


def test_groups_join_high_cross_contig_pairs_and_carry_the_label():
    groups = candidate_groups([_pair("A", "c1", "B", "c2"), _pair("B", "c2", "C", "c3"),
                               _pair("C", "c3", "D", "c4", "MODERATE_RG_GMCI_CANDIDATE")])
    assert len(groups) == 1
    g = groups[0]
    assert [r["bgc_id"] for r in g["regions"]] == ["A", "B", "C"]
    assert g["possible_moderate_links"] == ["C+D"]
    assert g["label"] == GROUP_LABEL.format(n=3) and "not a contig join" in g["label"]


def test_the_package_ships_the_engine_group_code_unchanged(tmp_path):
    out = tmp_path / "pkg"
    subprocess.run([sys.executable, str(ROOT / "packaging/rggmci/build_rggmci_package.py"), "--bundle", str(ROOT),
                    "--out", str(out)], check=True, capture_output=True)
    shipped = out / "src/rggmci/groups.py"
    assert shipped.read_bytes() == (ROOT / "mamey/rescue_groups.py").read_bytes()
    assert not (ROOT / "packaging/rggmci/templates/src/rggmci/groups.py").exists()


AA = "ACDEFGHIKLMNPQRSTVWY"


def _protein(seed, n=180):
    rnd = random.Random(seed)
    return "M" + "".join(rnd.choice(AA) for _ in range(n))


def _gbk(name, genes, edge="True"):
    """A minimal GenBank record: one region feature and one CDS per (label, protein)."""
    length = 1000 * (len(genes) + 1)
    lines = [f"LOCUS       {name:<16}{length:>12} bp    DNA     linear   UNK 01-JAN-1980",
             f"DEFINITION  test organism strain X {name}, whole genome shotgun sequence.",
             f"ACCESSION   {name}", f"VERSION     {name}", "FEATURES             Location/Qualifiers",
             f"     region          1..{length}", f'                     /contig_edge="{edge}"']
    for i, (label, aa) in enumerate(genes):
        lines += [f"     CDS             {i * 1000 + 1}..{i * 1000 + 900}", f'                     /gene="{label}"',
                  f'                     /locus_tag="{name}_{i}"', f'                     /translation="{aa}"']
    lines.append("ORIGIN")
    for start in range(0, length, 60):
        chunk = "a" * min(60, length - start)
        lines.append(f"{start + 1:>9} " + " ".join(chunk[i:i + 10] for i in range(0, len(chunk), 10)))
    lines.append("//")
    return "\n".join(lines) + "\n"


REF = [(f"ref{i}", _protein(i)) for i in range(1, 7)]   # a six-gene reference cluster


def _archive(tmp_path, files):
    z = tmp_path / "genome.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for name, text in files.items():
            zf.writestr(name, text)
    return z


def _regions():
    return {"A": {"strain": "Test", "contig": "ctg1", "antismash_region": "region001", "source_gbk": "ctg1.region001.gbk",
                  "products": ["NRPS"], "edge_status": "Edge"},
            "B": {"strain": "Test", "contig": "ctg2", "antismash_region": "region001", "source_gbk": "ctg2.region001.gbk",
                  "products": ["NRPS"], "edge_status": "Full-contig"}}


def test_group_file_holds_every_member_record_and_names_them(tmp_path):
    z = _archive(tmp_path, {"ctg1.region001.gbk": _gbk("ctg1", REF[:4]), "ctg2.region001.gbk": _gbk("ctg2", REF[4:])})
    groups = candidate_groups([_pair("A", "ctg1", "B", "ctg2")])
    status = write_group_genbanks(z, groups, _regions(), tmp_path / "out", "Test_RGGMCI")
    assert status[0]["status"] == "WRITTEN"
    gbk = tmp_path / "out" / "Test_RGGMCI_G01.gbk"
    assert gbk.read_text().count("\nLOCUS") + gbk.read_text().startswith("LOCUS") == 2
    members = read_members(gbk)
    assert [m["identity"] for m in members] == ["Test / ctg1 / region001 / A", "Test / ctg2 / region001 / B"]
    assert members[1]["definition"].startswith("test organism strain X ctg2")


def test_a_missing_region_file_blocks_the_group_file(tmp_path):
    z = _archive(tmp_path, {"ctg1.region001.gbk": _gbk("ctg1", REF[:4])})
    status = write_group_genbanks(z, candidate_groups([_pair("A", "ctg1", "B", "ctg2")]), _regions(),
                                  tmp_path / "out", "Test_RGGMCI")
    assert status[0]["status"] == "NOT_WRITTEN_REGION_FILE_MISSING" and status[0]["missing_region_files"] == "B"
    assert not (tmp_path / "out" / "Test_RGGMCI_G01.gbk").exists()


def _completeness(tmp_path, query, label):
    spec = importlib.util.spec_from_file_location("cluster_completeness", ROOT / "tools/cluster_completeness.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ref = tmp_path / "ref.gbk"
    ref.write_text(_gbk("refclu", REF, edge="False"))
    out = tmp_path / f"cc_{label}"
    mod.main(["--query", f"{label}:{query}", "--reference", f"MIBIG:{ref}", "--outdir", str(out)])
    return json.loads((out / f"{label}_completeness.json").read_text()), out


def test_completeness_reads_a_group_fragment_by_fragment(tmp_path):
    # fragment 1 carries reference genes 1-3, fragment 2 genes 4-5; gene 6 is on neither
    z = _archive(tmp_path, {"ctg1.region001.gbk": _gbk("ctg1", REF[:3]), "ctg2.region001.gbk": _gbk("ctg2", REF[3:5])})
    write_group_genbanks(z, candidate_groups([_pair("A", "ctg1", "B", "ctg2")]), _regions(), tmp_path / "g", "T")
    rep, out = _completeness(tmp_path, tmp_path / "g" / "T_G01.gbk", "G01")
    assert rep["completeness_pct"] == 83.3
    assert [f["completeness_pct"] for f in rep["fragments"]] == [50.0, 33.3]
    assert rep["rggmci_group"] is True
    text = rep["interpretation"]
    assert "not a contig join" in text and "Test / ctg1 / region001 / A alone: 3/6" in text
    assert "33.3 percentage points above the strongest single fragment" in text
    assert "present in the group, not missing" in text
    assert "not read as a biological difference" in text and "genuine biological difference" not in text
    rows = list(csv.reader(open(out / "G01_genes_by_fragment.csv")))
    assert rows[0][3:] == ["Test / ctg1 / region001 / A", "Test / ctg2 / region001 / B"]


def test_single_region_queries_read_as_before(tmp_path):
    q = tmp_path / "one.gbk"
    q.write_text(_gbk("ctg1", REF[:3]))
    rep, out = _completeness(tmp_path, q, "one")
    assert rep["completeness_pct"] == 50.0 and len(rep["fragments"]) == 1
    assert "rggmci_group" not in rep and not (out / "one_genes_by_fragment.csv").exists()
    assert "RG-GMCI candidate group" not in rep["interpretation"]


def test_engine_package_writes_one_group_file_per_group(tmp_path):
    """The engine lists every candidate group with full identities and writes its GenBank file and members table."""
    import os
    # four regions of public WGS MTQP00000000.1 (Saccharothrix sp. ALI_22_I) forming two two-region groups
    fixture = ROOT / "tests" / "fixtures" / "rggmci_public_MTQP00000000.1_groups_subset.zip"
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONHASHSEED="0")
    subprocess.run([sys.executable, "-m", "mamey", "run", "--strain", "GRP_T", "--input-zip", str(fixture),
                    "--taxonomy", "Saccharothrix sp.", "--source", "public test fixture", "--outdir", str(tmp_path),
                    "--mode", "standard", "--release", "PUBLIC", "--brief", "none", "--json-evidence", "off"],
                   check=True, capture_output=True, timeout=600, env=env, text=True)
    pkg = next(tmp_path.rglob("GRP_T_4A_RGGMCI_groups.csv")).parent
    groups = list(csv.DictReader(open(pkg / "GRP_T_4A_RGGMCI_groups.csv", encoding="utf-8")))
    full = json.loads((pkg / "GRP_T_4A_RGGMCI_full.json").read_text())
    assert len(groups) == len(full["candidate_groups"]) == 2
    for g in groups:
        assert g["gbk_status"] == "WRITTEN"
        regions = g["regions"].split("; ")
        assert len(regions) == int(g["n_regions"])
        assert all(r.startswith("GRP_T / ") and len(r.split(" / ")) == 4 for r in regions)
        gbk = pkg / g["group_gbk"]
        text = gbk.read_text()
        assert sum(1 for line in text.splitlines() if line.startswith("LOCUS")) == int(g["n_regions"])
        assert [m["identity"] for m in read_members(gbk)] == regions
        assert "not a contig join" in g["label"]
