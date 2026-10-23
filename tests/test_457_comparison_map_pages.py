"""Card 018c0f08_457_comparison_map_pages: batch comparison maps on one kb scale, the region-folder builder, pinned
rows (other isolate loci, MIBiG clusters) and page stacking. Synthetic data only; no DIAMOND, network or private data."""
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "comparison_map_pages.py"


def _load():
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("comparison_map_pages_under_test", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _region_gbk(organism, definition="Genus sp. X1 contig_1, whole genome shotgun sequence."):
    return (f"LOCUS       rec1   1000 bp    DNA     linear   UNK 01-JAN-1980\nDEFINITION  {definition}\n"
            f"SOURCE      x\n  ORGANISM  {organism}\n            Bacteria.\nFEATURES             Location/Qualifiers\n//\n")


def _zip(path, files):
    with zipfile.ZipFile(path, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return path


# ------------------------------------------------------------------------------------- names and region folders

def test_clean_name_drops_record_accession_and_contig_token():
    t = _load()
    assert t.clean_name("NZ_ABCD01000001.1 Genus sp. M39 ABC44_contig000001") == "Genus sp. M39"
    assert t.clean_name("Genus alba DSM 1 scaffold_3, whole genome shotgun sequence.") == "Genus alba DSM 1"
    assert t.label_of([_region_gbk("Genus beta K-7")]) == "Genus beta K-7"
    assert t.label_of([_region_gbk("NZ_ABCD01000001.1 Genus sp. M39 ABC44_contig000001")]) == "Genus sp. M39"
    assert t.label_of([_region_gbk(".")]) == "Genus sp. X1"


def test_stage_regions_one_row_label_per_genome_duplicates_once(tmp_path):
    t = _load()
    a = _zip(tmp_path / "Genus_alba_A1_ABCD00000000.zip", {"r/c1.region001.gbk": _region_gbk("Genus alba"),
                                                         "r/c1.region002.gbk": _region_gbk("Genus alba"),
                                                         "r/c1.gbk": "whole genome, not staged"})
    b = _zip(tmp_path / "Genus_alba_B2_EFGH00000000.zip", {"c9.region001.gbk": _region_gbk("Genus alba")})
    dup = _zip(tmp_path / "NZ_Genus_alba_A1_ABCD00000000.zip", {"c1.region001.gbk": _region_gbk("Genus alba")})
    out = tmp_path / "regions"
    tab = t.stage_regions([(a, "s1", "index"), (b, "s2", "index"), (dup, "s1b", "index")], out)
    assert len(tab) == 2                                            # the second filing of one accession is skipped
    files = sorted(p.name for p in out.glob("*.gbk"))
    assert files == ["Genus_alba_A1_ABCD00000000__c1.region001.gbk", "Genus_alba_A1_ABCD00000000__c1.region002.gbk",
                     "Genus_alba_B2_EFGH00000000__c9.region001.gbk"]
    labels = {r["zip"]: r["row_label"] for r in tab}
    assert labels[a.name] == "Genus alba ABCD00000000" and labels[b.name] == "Genus alba EFGH00000000"
    assert "  ORGANISM  Genus alba ABCD00000000" in (out / files[0]).read_text()
    assert (out / "_genomes.tsv").read_text().splitlines()[0] == "zip\tsha256\tsha256_source\tregions\trow_label"
    named = t.stage_regions([(b, "s2", "index")], tmp_path / "named", {b.name: "Genus alba B2"})
    assert named[0]["row_label"] == "Genus alba B2"


def test_library_rows_filters_genus_strictness_and_repeats(tmp_path):
    t = _load()
    lib = tmp_path / "LIB"
    lib.mkdir()
    (lib / "INDEX.tsv").write_text("genus\tstrictness\tsha256\tlibrary_path\n"
                                   "Genus\tloose\taa\tLIB/x.zip\nGenus\tloose\taa\tLIB/x_copy.zip\n"
                                   "Genus\tstrict\tbb\tLIB/y.zip\nOther\tloose\tcc\tLIB/z.zip\n")
    (lib / "x.zip").write_bytes(b"")
    rows = t.library_rows(lib / "INDEX.tsv", "Genus")
    assert [(p.name, s) for p, s, _ in rows] == [("x.zip", "aa")]
    assert rows[0][0] == tmp_path / "LIB" / "x.zip"                 # library_path resolved against the index's parent


# ------------------------------------------------------------------------------------- spec and selection

def test_read_spec_refuses_bad_rows(tmp_path):
    t = _load()
    head = "map_id\tzip\tlabel\tbgc\trescue\n"
    for body, word in (("m1\tz.zip\tISO-1\t\t\n", "exactly one"), ("m1\tz.zip\tISO-1\tBGC001\t\nm1\tz.zip\tISO-1\tBGC002\t\n", "unique"),
                       ("bad id\tz.zip\tISO-1\tBGC001\t\n", "unique"), ("m1\t\tISO-1\tBGC001\t\n", "'zip' is empty")):
        (tmp_path / "s.tsv").write_text(head + body)
        with pytest.raises(t.InputError, match=word):
            t.read_spec(tmp_path / "s.tsv")
    (tmp_path / "s.tsv").write_text("map_id\tzip\tlabel\tbgc\tcolour\nm1\tz.zip\tISO-1\tBGC001\tred\n")
    with pytest.raises(t.InputError, match="unknown columns"):
        t.read_spec(tmp_path / "s.tsv")


def test_pinned_rows_are_kept_past_top_in_rank_order():
    t = _load()
    refs = [{"accession": a} for a in ("p1", "p2", "LOCUS__ISO-2__BGC042", "p3", "MIBiG__BGC0000001")]
    kept, missing = t.select_refs(refs, {"LOCUS__ISO-2__BGC042", "MIBiG__BGC0000001", "MIBiG__BGC0000002"}, top=1)
    assert [r["accession"] for r in kept] == ["p1", "LOCUS__ISO-2__BGC042", "MIBiG__BGC0000001"]
    assert missing == ["MIBiG__BGC0000002"]


def test_shared_scale_modes():
    t = _load()
    spans = {"a": (0, 40000), "b": (5000, 15000), "c": (0, 20000)}
    groups = {"a": "g1", "b": "g1", "c": "g2"}
    one = t.shared_scales(spans, groups, "batch", 6.7, None, None)
    assert one["a"] == one["b"] == one["c"] and one["a"][0] == pytest.approx(40 * 1.0201 / 6.7)
    per = t.shared_scales(spans, groups, "group", 6.7, None, None)
    assert per["a"] == per["b"] != per["c"]
    assert t.shared_scales(spans, groups, "none", 6.7, None, None)["a"] == (None, None)
    assert t.shared_scales(spans, groups, "batch", 6.7, 9.0, 5.0)["b"] == (9.0, 5.0)


def test_global_pair_alignment_numbers():
    pytest.importorskip("Bio")
    t = _load()
    same = t.global_pair("MKTAYIAKQR", "MKTAYIAKQR*")
    assert same["identity_pct"] == 100.0 and same["gap_columns"] == 0 and same["alignment_length"] == 10
    short = t.global_pair("MKTAYIAKQRQISFVKSHFSRQ", "MKTAYIAKQR")
    assert short["identity_over_shorter_pct"] == 100.0 and short["gap_columns"] == 12


# ------------------------------------------------------------------------------------- drawing and pages

def _gene(i, s, e, st, aa="MKT"):
    return {"i": i, "id": f"g{i:03d}", "start": s, "end": e, "strand": st, "name": f"r{i}", "aa": aa}


def _model(gbks, zip_path, k=1.0):
    """Two contig-free references over one locus contig; k stretches every coordinate."""
    prots = {f"a{j}": {"contig": "cA", "start": int(j * 1000 * k), "end": int((j + 1) * 1000 * k), "strand": 1, "tag": f"a{j}",
                       "aa": "MKTAYIAKQR", "kind": "biosynthetic"} for j in range(4)}
    refs = []
    for n, (stem, name) in enumerate(gbks):
        refs.append({"accession": stem, "display_id": stem, "compound": name, "description": "", "also": [],
                     "genes": [_gene(i, int((i - 1) * 1000 * k), int(i * 1000 * k), 1, "MKTAYIAKQR") for i in range(1, 6)],
                     "pairs": [(f"a{j}", j + 1, 90.0 - n, 400.0 - j) for j in range(4)], "gbk": str(gbks and zip_path)})
    return {"label": "ISO-1", "bgc": "BGC001", "prots": prots, "names": {}, "zip": str(zip_path), "sources": [zip_path],
            "segments": [("cA · BGC001", list(prots))], "regions": [{"contig": "cA", "identity": "ISO-1 / cA / region001 / BGC001"}],
            "source": "reference-genome antiSMASH regions", "refs": refs, "skipped": [], "min_fraction": 0.0, "n_hits": 8}


def test_draw_aligned_shared_scale_and_refusal(tmp_path):
    pytest.importorskip("matplotlib")
    t = _load()
    mrc = t._mrc()
    z = tmp_path / "q.zip"
    z.write_bytes(b"x")
    wide, narrow = _model([("p1", "Genus alpha"), ("p2", "Genus beta")], z), _model([("p1", "Genus alpha")], z, k=.5)
    kpi = (mrc.aligned_span_bp(mrc.aligned_layout(wide))[1] - mrc.aligned_span_bp(mrc.aligned_layout(wide))[0]) / 1000 * 1.0201 / 6.7
    for name, m in (("wide", wide), ("narrow", narrow)):
        mrc.draw_aligned(m, mrc.aligned_layout(m), tmp_path / name, width_in=9.6, dpi=60, kb_per_in=kpi, scale_kb=1)
        assert m["aligned_layout"]["kb_per_in"] == pytest.approx(kpi, rel=1e-3) and m["scale_kb"] == 1
    with pytest.raises(ValueError, match="does not fit"):
        mrc.draw_aligned(wide, mrc.aligned_layout(wide), tmp_path / "tight", width_in=9.6, dpi=60, kb_per_in=kpi / 3)


def _png(path, h_in, dpi=50):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(3, h_in))
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    return path


def test_pages_stack_in_order_without_resampling(tmp_path):
    pytest.importorskip("matplotlib")
    t = _load()
    sys.path.insert(0, str(ROOT / "tools"))
    import check_figure_provenance as cfp
    maps = [(f"m{k}", _png(tmp_path / f"m{k}.png", h)) for k, h in enumerate((1.0, 1.5, 2.5, 4.0))]
    pages = t.stack_pages(maps, height_in=3.0, gap_in=.2, dpi=50)
    assert [[m for m, _ in p] for p in pages] == [["m0", "m1"], ["m2"], ["m3"]]   # m3 is taller than a page: alone
    files = t.draw_page(pages[0], tmp_path / "pages" / "page_01", gap_in=.2, dpi=50)
    from matplotlib import image as mpimg
    img = mpimg.imread(files[0])
    assert img.shape[0] == 50 + 75 + 10 and img.shape[1] == 150
    assert {f.suffix for f in files} == {".png", ".pdf"}
    assert all(cfp.stamp(f)[0] == "PASS" for f in files)


def test_run_end_to_end_with_a_pinned_mibig_row(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")
    t = _load()
    mrc = t._mrc()
    z = tmp_path / "q.zip"
    z.write_bytes(b"x")
    pub = tmp_path / "pub"
    pub.mkdir()
    for n in ("p1", "p2"):
        (pub / f"{n}.gbk").write_text(_region_gbk(f"Genus {n}"))
    (tmp_path / "BGC0000001.gbk").write_text(_region_gbk("Genus producer K1"))
    monkeypatch.setattr(mrc.gdr, "load_genome", lambda zp, label: ({}, []))

    def fake_build(zip_path, label, rescue, mibig_db, mibig_dir, top=6, ref_gbk_dir=None, bgc=None, **kw):
        ref = Path(ref_gbk_dir)
        assert sorted(p.name for p in ref.glob("*.gbk")) == ["MIBiG__BGC0000001.gbk", "p1.gbk", "p2.gbk"]
        k = 1.0 if bgc == "BGC001" else .5
        m = _model([("p1", "Genus p1"), ("p2", "Genus p2"), ("MIBiG__BGC0000001", "Genus producer K1")], zip_path, k)
        for r in m["refs"]:
            r["gbk"] = str(ref / f"{r['accession']}.gbk")
        m["bgc"] = bgc
        return m
    monkeypatch.setattr(mrc, "build", fake_build)
    (tmp_path / "spec.tsv").write_text("# two maps, one scale\nmap_id\tzip\tlabel\tbgc\tref_gbk_dirs\tmibig\n"
                                       "first\tq.zip\tISO-1\tBGC001\tpub\tBGC0000001.gbk\n"
                                       "second\tq.zip\tISO-1\tBGC002\tpub\tBGC0000001.gbk\n")
    out = tmp_path / "out"
    rc = t.main(["run", str(tmp_path / "spec.tsv"), "--out", str(out), "--top", "1", "--dpi", "60", "--page-height-in", "20"])
    assert rc == 0
    maps = (out / "MAPS.tsv").read_text().splitlines()
    assert maps[1].split("\t")[:2] == ["first", "drawn"] and maps[2].split("\t")[:2] == ["second", "drawn"]
    assert maps[1].split("\t")[4] == maps[2].split("\t")[4]                     # one kb per inch for both maps
    rows = (out / "first" / "rows.tsv").read_text().splitlines()
    assert [r.split("\t")[1] for r in rows[1:]] == ["p1", "MIBiG__BGC0000001"]  # top 1 plus the pinned MIBiG row
    assert rows[2].split("\t")[2:4] == ["MIBiG reference", "yes"]
    cap = (out / "first" / "CAPTION.md").read_text()
    assert "MIBiG reference rows: MIBiG BGC0000001." in cap and "share one scale" in cap
    assert (out / "pages" / "page_01.png").exists() and not (out / "pages" / "page_02.png").exists()
    assert "## 2. second" in (out / "pages" / "page_01_CAPTION.md").read_text()
    rec = json.loads((out / "receipt.json").read_text())
    assert rec["settings"]["shared_scale"] == "batch" and "first/comparison.png" in rec["outputs_sha256"]
    assert str((tmp_path / "spec.tsv").resolve()) in rec["inputs_sha256"]
    src = (out / "first" / "_references" / "_sources.tsv").read_text()
    assert "MIBiG__BGC0000001\tMIBiG reference\tyes" in src


def test_help_runs_from_a_foreign_directory(tmp_path):
    import subprocess
    r = subprocess.run([sys.executable, str(TOOL), "run", "--help"], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0 and "--shared-scale" in r.stdout
