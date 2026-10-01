"""RG-GMCI reference-guided completion (mamey/ref_completion.py): report-only, synthetic ids only.

The end-to-end test builds a made-up genome: a core contig holding the first half of a reference gene at its end, a
partner contig holding the second half at its start plus one more reference gene, and a decoy contig carrying only a
transposase far from its ends. It runs only when a DIAMOND binary is available ($RGGMCI_DIAMOND or PATH).
"""
import argparse
import importlib.util
import json
import random
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from mamey import ref_completion as rc

ROOT = Path(__file__).resolve().parents[1]
AA = "ACDEFGHIKLMNPQRSTVWY"


def _prot(seed: int, n: int) -> str:
    r = random.Random(seed)
    return "M" + "".join(r.choice(AA) for _ in range(n - 1))


def _gbk(name: str, length: int, cds: list[tuple], definition: str = "") -> str:
    """cds: (start, end, strand, tag, translation, extra qualifier lines)."""
    lines = [f"LOCUS       {name} {length} bp    DNA     linear   BCT 01-JAN-2000",
             f"DEFINITION  {definition or name}.", f"ACCESSION   {name}", f"VERSION     {name}",
             "FEATURES             Location/Qualifiers"]
    for s, e, strand, tag, aa, extra in cds:
        loc = f"{s + 1}..{e}" if strand > 0 else f"complement({s + 1}..{e})"
        lines.append(f"     CDS             {loc}")
        lines.append(f'                     /locus_tag="{tag}"')
        for q in extra:
            lines.append(f"                     {q}")
        lines.append(f'                     /translation="{aa}"')
    lines.append("//")
    return "\n".join(lines) + "\n"


G1, G2, G3, G4 = _prot(1, 400), _prot(2, 400), _prot(3, 300), _prot(4, 300)


def _mibig_dir(tmp: Path) -> Path:
    d = tmp / "mibig_gbk"
    d.mkdir()
    (d / "BGC9999001.gbk").write_text(_gbk("BGC9999001", 9000, [
        (0, 1200, 1, "tstA", G1, ['/gene="tstA"', '/gene_kind="biosynthetic"', '/product="synthase"']),
        (1300, 2500, 1, "tstB", G2, ['/gene="tstB"', '/gene_kind="biosynthetic-additional"', '/product="kinase"']),
        (2600, 3500, 1, "tstC", G3, ['/gene="tstC"', '/gene_kind="biosynthetic-additional"',
                                      '/product="oxidoreductase"']),
        (3600, 4500, 1, "tstT", G4, ['/gene="tstT"', '/gene_kind="other"', '/product="transposase"'])],
        definition="Streptomyces sp. TST-9 testomycin cluster"))
    (d / "BGC9999002.gbk").write_text(_gbk("BGC9999002", 3000, [
        (0, 900, 1, "othA", _prot(9, 300), ['/gene="othA"', '/gene_kind="biosynthetic"'])],
        definition="Streptomyces sp. TST-8 otheromycin cluster"))
    (tmp / "compounds.json").write_text(json.dumps({"entries": [
        {"accession": "BGC9999001", "compounds": ["testomycin A"]},
        {"accession": "BGC9999002", "compounds": ["otheromycin"]}]}))
    return d


N1, N2, N3 = "NODE_1_length_5000_cov_50.0", "NODE_2_length_3000_cov_45.0", "NODE_3_length_60000_cov_48.0"


def _genome_zip(tmp: Path) -> Path:
    """Core contig N1 (first half of tstB at its end), partner N2 (second half of tstB at its start, then tstC),
    decoy N3 (a transposase in the middle). The whole-genome record names are shortened, as a GenBank LOCUS can be."""
    genome = (_gbk("NODE_1_length_5", 5000, [(100, 1300, 1, "c1", G1, []), (4390, 4990, 1, "c2", G2[:200], [])])
              + _gbk("NODE_2_length_3", 3000, [(5, 605, 1, "p1", G2[200:], []), (900, 1800, 1, "p2", G3, [])])
              + _gbk("NODE_3_length_6", 60000, [(30000, 30900, 1, "d1", G4, [])]))
    z = tmp / "TST-1.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("TST-1.gbk", genome)
        zf.writestr("input/TST-1.fasta", f">{N1}\nA\n>{N2}\nA\n>{N3}\nA\n")
        zf.writestr("__MACOSX/._TST-1.gbk", b"\x00\x05\x16\x07\xa2")   # an AppleDouble sidecar is not the genome
    return z


BGCS = [SimpleNamespace(bgc_id="BGC001", contig=N1, start=0, end=5000, region_number=1),
        SimpleNamespace(bgc_id="BGC002", contig=N2, start=0, end=3000, region_number=1)]
REFMAP = {"reference_records": [{"bgc_id": "BGC001", "ref": "BGC9999001.1", "db_kind": "knownclusterblast", "rank": 1},
                                {"bgc_id": "BGC001", "ref": "BGC9999002.1", "db_kind": "knownclusterblast", "rank": 2}]}


def _depth(a: str, b: str):
    from mamey.rggmci import depth_fields
    r = depth_fields(a, b)["depth_ratio"]
    return None if r == "" else float(r)


# ── the database ───────────────────────────────────────────────────────────────────────────────────────────────────
def test_build_mibig_db_writes_proteins_clusters_and_manifest(tmp_path, monkeypatch):
    monkeypatch.delenv("RGGMCI_DIAMOND", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))          # no DIAMOND: FASTA only
    m = rc.build_mibig_db(_mibig_dir(tmp_path), tmp_path / "db", compounds_json=tmp_path / "compounds.json")
    assert (m["clusters"], m["proteins"], m["diamond_db"]) == (2, 5, "")
    db = rc.load_mibig_db(tmp_path / "db")
    assert [g["name"] for g in db["genes"]["BGC9999001"]] == ["tstA", "tstB", "tstC", "tstT"]
    assert db["genes"]["BGC9999001"][1]["id"] == "BGC9999001|2" and db["genes"]["BGC9999001"][1]["aa"] == G2
    assert db["compounds"]["BGC9999001"] == ["testomycin A"]
    assert db["lengths_kb"] == {"BGC9999001": 9.0, "BGC9999002": 3.0} and db["protein_counts"]["BGC9999001"] == 4
    with pytest.raises(FileExistsError):   # never writes into a folder that already holds files
        rc.build_mibig_db(tmp_path / "mibig_gbk", tmp_path / "db")


def test_resolve_mibig_db_never_searches_the_disk(tmp_path, monkeypatch):
    monkeypatch.delenv(rc.MIBIG_DB_ENV, raising=False)
    db = tmp_path / "ws" / "BigSCAPE" / "prot"
    db.mkdir(parents=True)
    (db / rc.DB_FAA).write_text(">BGC9999001|1\nM\n")
    assert rc.resolve_mibig_db() == (None, "not_given")
    assert rc.resolve_mibig_db(db) == (str(db), "explicit")
    assert rc.resolve_mibig_db(tmp_path / "nope")[0] is None
    monkeypatch.setenv(rc.MIBIG_DB_ENV, str(db))
    assert rc.resolve_mibig_db() == (str(db), "env")
    monkeypatch.delenv(rc.MIBIG_DB_ENV)
    (tmp_path / "ws" / "OFFICIAL_DATA").mkdir()
    reg = tmp_path / "ws" / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv"
    bundle = tmp_path / "ws" / "bundle"
    bundle.mkdir()
    reg.write_text("other_asset\tdata\tsomewhere\t1K\tother\n")
    assert rc.resolve_mibig_db(registry_from=bundle) == (None, "not_registered")
    reg.write_text(f"{rc.MIBIG_DB_ASSET}\tdatabase\tBigSCAPE/prot\t1M\tmibig proteins\n")
    assert rc.resolve_mibig_db(registry_from=bundle) == (str(tmp_path / "ws" / "BigSCAPE" / "prot"), "registry")


# ── tiers ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def _pairs():
    return {"ranked_pairs": [{"pair": "BGC001+BGC002", "bgc_a": "BGC001", "contig_a": N1, "bgc_b": "BGC002",
                              "contig_b": N2}]}


def test_without_a_database_the_tier_is_the_same_whatever_aligner_is_installed(tmp_path, monkeypatch):
    for found in (("diamond", "/usr/bin/diamond"), ("", "")):
        monkeypatch.setattr(rc, "find_aligner", lambda d=None, f=found: f)
        res = _pairs()
        rc.complete(res, tmp_path / "x.zip", BGCS, REFMAP, {"BGC001"}, mibig_db=None)
        assert res["reference_completion"]["completion_tier"] == "NO_MIBIG_PROTEINS"
        assert res["ranked_pairs"][0]["completion_tier"] == "NO_MIBIG_PROTEINS"
        assert res["ranked_pairs"][0]["split_gene_links"] == ""


def test_a_database_without_an_aligner_is_no_aligner_and_off_runs_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "find_aligner", lambda d=None: ("", ""))
    (tmp_path / rc.DB_FAA).write_text(">BGC9999001|1\nM\n")
    res = _pairs()
    rc.complete(res, tmp_path / "x.zip", BGCS, REFMAP, {"BGC001"}, mibig_db=tmp_path)
    assert res["reference_completion"]["completion_tier"] == "NO_ALIGNER"
    res = _pairs()
    rc.complete(res, tmp_path / "x.zip", BGCS, REFMAP, {"BGC001"}, mibig_db=tmp_path, mode="off")
    assert res["ranked_pairs"][0]["completion_tier"] == "OFF"
    with pytest.raises(ValueError):
        rc.complete(_pairs(), tmp_path / "x.zip", BGCS, REFMAP, set(), sensitivity="fastest")


# ── recurrence, partners, the join ─────────────────────────────────────────────────────────────────────────────────
def _split(ref, core, pieces, piece_bgcs, call="CLEAR"):
    return {"reference": ref, "_core_bgc": core, "_pieces": pieces, "_piece_bgcs": set(piece_bgcs),
            "split_call": call, "reference_gene": 2}


COMP = {"BGC9999001": ["testomycin A"], "BGC9999003": ["testomycin B"], "BGC9999002": ["otheromycin"]}


def test_two_cores_that_each_hold_a_piece_are_a_real_split_not_recurrence():
    s = [_split("BGC9999001", "BGC001", ("q1", "q2"), {"BGC001", "BGC002"}),
         _split("BGC9999002", "BGC002", ("q1", "q2"), {"BGC001", "BGC002"})]
    assert rc.mark_recurrent_splits(s, COMP) == 0 and {x["split_call"] for x in s} == {"CLEAR"}


def test_a_piece_pair_splitting_for_an_unrelated_foreign_core_is_a_recurrent_common_gene():
    s = [_split("BGC9999001", "BGC001", ("q1", "q2"), {"BGC001", "BGC002"}),
         _split("BGC9999002", "BGC007", ("q1", "q2"), {"BGC001", "BGC002"})]
    assert rc.mark_recurrent_splits(s, COMP) == 2
    assert {x["split_call"] for x in s} == {"RECURRENT_COMMON_GENE"}
    assert s[0]["split_call_before_recurrence"] == "CLEAR"


def test_one_compound_family_is_never_recurrence():
    s = [_split("BGC9999001", "BGC001", ("q1", "q2"), {"BGC001"}),
         _split("BGC9999003", "BGC007", ("q1", "q2"), {"BGC001"})]
    assert rc.mark_recurrent_splits(s, COMP) == 0


def test_mobile_elements_are_named_from_product_or_name():
    assert rc.is_mobile_gene({"product": "transposase", "name": "x"})
    assert rc.is_mobile_gene({"product": "", "name": "IS110 family"})
    assert not rc.is_mobile_gene({"product": "glucokinase", "name": "tstB"})


def test_one_broken_gene_counts_once_however_many_references_see_it():
    prots = {"q1": {"contig": N1}, "q2": {"contig": N2}}
    splits = [dict(_split("BGC9999001", "BGC001", ("q1", "q2"), {"BGC001", "BGC002"}), reference_gene=2),
              dict(_split("BGC9999003", "BGC002", ("q1", "q2"), {"BGC001", "BGC002"}), reference_gene=5)]
    partners = [{"_core_bgc": "BGC001", "partner_contig": N2, "accepted": True}]
    res = _pairs()
    rc.join_pairs(res["ranked_pairs"], "FULL", {"BGC001": "BGC9999001"}, splits, partners, prots)
    assert res["ranked_pairs"][0]["split_gene_links"] == 1
    assert res["ranked_pairs"][0]["ref_completion_partner"] == "yes"


def test_the_gap_rescue_tool_runs_the_same_code():
    spec = importlib.util.spec_from_file_location("gdr_shared", ROOT / "tools/gap_directed_rescue.py")
    gdr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gdr)
    assert gdr.split_genes is rc.split_genes and gdr.search is rc.search and gdr.MIN_ID == rc.MIN_ID
    assert gdr._pfam_names is rc._pfam_names and gdr.PARTNER_CHECK_COLS is rc.PARTNER_CHECK_COLS
    # the partner checks and discovery are thin wrappers that pass the tool's own search to the shared code
    assert "_rc.partner_checks(" in Path(ROOT / "tools/gap_directed_rescue.py").read_text()
    assert not hasattr(gdr, "HOUSEKEEPING_PFAM") or gdr.HOUSEKEEPING_PFAM is rc.HOUSEKEEPING_PFAM


def test_partner_column_names_and_verdicts_are_the_tools():
    assert rc.PARTNER_CHECK_COLS[:8] == ["partner_verdict", "reciprocal_best_mibig", "reciprocal_best_identity",
                                         "reciprocal_reference_identity", "paralogs_in_genome", "adjacent_finds",
                                         "housekeeping_neighbours", "neighbour_pfams"]
    assert rc.PARTNER_CHECK_COLS[8:] == ["reciprocal_family_ratio"]


def _prot_at(tag, contig, start, clen=60000, aa=None):
    return {"tag": tag, "contig": contig, "shown": f"TST-1 / {contig}", "start": start, "end": start + 900, "strand": 1,
            "contig_len": clen, "aa": aa or "M" + "A" * 400, "kind": "", "modular": False}


def test_the_reciprocal_search_uses_the_aligned_stretch_and_the_family_score_ratio():
    prots = {"c1": _prot_at("c1", "core", 100), "y1": _prot_at("y1", "ctgY", 100, aa="M" + "C" * 99 + "W" * 300)}
    rows = [{"reference_gene": 1, "name": "r1", "status": "PRESENT_IN_CORE", "best_protein": "c1"},
            {"reference_gene": 2, "name": "r2", "status": "MISSING_FOUND_CLEAR", "best_protein": "y1"}]
    ref = [{"i": 1, "id": "BGC9999001|1"}, {"i": 2, "id": "BGC9999001|2"}]
    hits = [{"qseqid": "BGC9999001|2", "sseqid": "y1", "pident": 60.0, "qcovhsp": 90.0, "bitscore": 300.0,
             "sstart": 101, "send": 400}]
    seen = {}

    def fake(query_fasta, db, **kw):
        seen["seq"] = open(query_fasta).read().split("\n")[1]
        return {"ok": True, "hits": [
            {"qseqid": "y1", "sseqid": "BGC9999002|4", "pident": 70.0, "qcovhsp": 90.0, "bitscore": 330.0},
            {"qseqid": "y1", "sseqid": "BGC9999003|2", "pident": 62.0, "qcovhsp": 90.0, "bitscore": 310.0}]}
    core = {"contig": "core", "start": 0, "end": 5000}
    rc.partner_checks(rows, prots, hits, core, "BGC9999001", mibig_db="db", search=fake, compounds=COMP, ref=ref)
    assert seen["seq"] == "W" * 300                     # the stretch the reference aligned to, not the whole protein
    # the best family member (BGC9999003, testomycin B) scores 310/330 = 0.94 of the best: not a paralog
    assert rows[1]["reciprocal_family_ratio"] == 0.939 and rows[1]["partner_verdict"] == "SINGLE_GENE"
    assert rows[1]["reciprocal_best_mibig"] == "BGC9999002"


def test_a_conserved_gene_whose_family_hit_ranks_low_is_not_failed_by_a_target_cap():
    """A regulator family matches many MIBiG clusters almost equally; the reference family's own hit can rank 30th.
    The reciprocal search asks for every target, so that hit is seen and the ratio is judged, not read as 0."""
    prots = {"c1": _prot_at("c1", "core", 100), "y1": _prot_at("y1", "ctgY", 100)}
    rows = [{"reference_gene": 1, "name": "r1", "status": "PRESENT_IN_CORE", "best_protein": "c1"},
            {"reference_gene": 2, "name": "r2", "status": "MISSING_FOUND_CLEAR", "best_protein": "y1"}]
    asked = {}

    def fake(query_fasta, db, **kw):
        asked.update(kw)
        hits = [{"qseqid": "y1", "sseqid": f"BGC80000{i:02d}|1", "pident": 50.0, "qcovhsp": 90.0,
                 "bitscore": 300.0 - i} for i in range(29)]
        hits.append({"qseqid": "y1", "sseqid": "BGC9999001|2", "pident": 49.0, "qcovhsp": 90.0, "bitscore": 271.0})
        n = kw.get("max_target_seqs") or len(hits)
        return {"ok": True, "hits": hits[:n]}
    rc.partner_checks(rows, prots, [], {"contig": "core", "start": 0, "end": 5000}, "BGC9999001", mibig_db="db",
                      search=fake)
    assert asked["max_target_seqs"] == 0
    assert rows[1]["reciprocal_family_ratio"] == 0.903 and rows[1]["partner_verdict"] == "SINGLE_GENE"


def test_a_contig_of_lone_or_paralog_finds_is_not_a_partner_but_two_adjacent_finds_are():
    ref = [{"i": i, "id": f"BGC9999001|{i}", "name": f"r{i}", "kind": "biosynthetic", "product": ""} for i in (1, 2, 3, 4)]
    prots = {"x1": _prot_at("x1", "ctgX", 100), "x2": _prot_at("x2", "ctgX", 3000),
             "y1": _prot_at("y1", "ctgY", 100), "z1": _prot_at("z1", "ctgZ", 100)}
    mk = lambda i, pid, c, v: {"reference_gene": i, "status": "MISSING_FOUND_CLEAR", "best_protein": pid,
                               "best_contig": c, "partner_verdict": v}
    rows = [mk(1, "x1", "ctgX", "SUPPORTED"), mk(2, "x2", "ctgX", "SUPPORTED"), mk(3, "y1", "ctgY", "SINGLE_GENE"),
            mk(4, "z1", "ctgZ", "PARALOG_FAMILY")]
    core = {"contig": "core", "start": 0, "end": 5000}
    got = {p["partner_contig"]: p for p in rc.partner_tests(core, ref, rows, [], prots, [], [], lambda a, b: 0.9)}
    assert got["ctgX"]["accepted"] and not got["ctgY"]["accepted"] and not got["ctgZ"]["accepted"]
    assert got["ctgZ"]["reason"] == "no passing finds" and got["ctgX"]["partner_verdicts"] == "SUPPORTED:2"
    low = rc.partner_tests(core, ref, rows[:2], [], prots, [], [], lambda a, b: 0.4)
    assert low[0]["accepted"] is False and low[0]["reason"] == "depth"


def test_discovery_judges_size_by_length_or_else_by_protein_count():
    prots = {"a": _prot_at("a", "core", 1), "d": _prot_at("d", "core", 6000)}
    prots["a"]["kind"] = "biosynthetic"
    hits = [{"qseqid": f"k0|{x}", "sseqid": f"{acc}|1", "pident": 60.0, "qcovhsp": 90.0, "bitscore": b}
            for x in "ad" for acc, b in (("BGC9999002", 900.0), ("BGC9999001", 300.0))]
    by_len = rc.discover_references({"R": ["a", "d"]}, prots, None, hits=hits,
                                    lengths_kb={"BGC9999002": 4150.0, "BGC9999001": 40.0})["R"]
    assert (by_len["accession"], by_len["size_check"]) == ("BGC9999001", "length")
    by_count = rc.discover_references({"R": ["a", "d"]}, prots, None, hits=hits,
                                      protein_counts={"BGC9999002": 3800, "BGC9999001": 30})["R"]
    assert (by_count["accession"], by_count["size_check"]) == ("BGC9999001", "protein_count")


def test_capped_sessions_run_completion_and_off_skips_it():
    from mamey.cli import _completion_mode
    ns = lambda **k: argparse.Namespace(**k)
    assert _completion_mode(ns(reference_completion="auto", chatgpt_safe=True)) == "auto"
    assert _completion_mode(ns(reference_completion="on", chatgpt_safe=True)) == "auto"
    assert _completion_mode(ns(reference_completion="off", chatgpt_safe=True)) == "off"


def test_resolve_pfam_hmm_explicit_then_env_then_registry(tmp_path, monkeypatch):
    monkeypatch.delenv(rc.PFAM_ENV, raising=False)
    hmm = tmp_path / "ws" / "BigSCAPE" / "Pfam-A.hmm"
    hmm.parent.mkdir(parents=True)
    hmm.write_text("HMMER3/f\n")
    assert rc.resolve_pfam_hmm() == (None, "not_given")
    assert rc.resolve_pfam_hmm(hmm) == (str(hmm), "explicit")
    assert rc.resolve_pfam_hmm(tmp_path / "none.hmm") == (None, "explicit_path_missing")
    monkeypatch.setenv(rc.PFAM_ENV, str(hmm))
    assert rc.resolve_pfam_hmm() == (str(hmm), "env")
    monkeypatch.delenv(rc.PFAM_ENV)
    (tmp_path / "ws" / "OFFICIAL_DATA").mkdir()
    (tmp_path / "ws" / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv").write_text(
        f"{rc.PFAM_ASSET}\thmm_db\tBigSCAPE/Pfam-A.hmm\t2.1G\tpfam\n")
    (tmp_path / "ws" / "bundle").mkdir()
    assert rc.resolve_pfam_hmm(registry_from=tmp_path / "ws" / "bundle") == (str(hmm), "registry")


def test_tables_are_written_even_when_completion_did_not_run(tmp_path):
    paths = rc.write_tables({"completion_tier": "NO_MIBIG_PROTEINS"}, tmp_path, "TST-1_")
    assert [p.name for p in paths] == ["TST-1_reference_completion.tsv", "TST-1_split_genes.tsv",
                                       "TST-1_partner_contigs.tsv"]
    assert paths[0].read_text().splitlines()[1].startswith("NO_MIBIG_PROTEINS")


def test_genome_contigs_take_the_bound_names_when_records_are_shortened(tmp_path):
    prots, regions = rc.genome_from_zip(_genome_zip(tmp_path), "TST-1", BGCS, {"BGC001"})
    assert {p["contig"] for p in prots.values()} == {N1, N2, N3}
    assert regions[0]["identity"] == f"TST-1 / {N1} / region001 / BGC001" and regions[0]["edge"] == "True"


# ── end to end with DIAMOND ────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.skipif(not rc.find_diamond(), reason="no diamond binary ($RGGMCI_DIAMOND or PATH)")
def test_a_split_gene_and_its_partner_are_found_and_a_transposase_decoy_is_not(tmp_path):
    rc.build_mibig_db(_mibig_dir(tmp_path), tmp_path / "db", compounds_json=tmp_path / "compounds.json")
    res = _pairs()
    block = rc.complete(res, _genome_zip(tmp_path), BGCS, REFMAP, {"BGC001"}, label="TST-1",
                        mibig_db=tmp_path / "db", depth_of=_depth, threads=1)
    assert block["completion_tier"] == "FULL" and block["aligner"] == "diamond"
    split = [s for s in block["splits"] if s["name"] == "tstB"]
    assert len(split) == 1 and split[0]["split_call"] == "CLEAR"
    assert split[0]["piece1_region_identity"] == f"TST-1 / {N1} / region001 / BGC001"
    parts = {p["partner_contig"]: p for p in block["partners"]}
    assert parts[N2]["accepted"] is True and parts[N2]["depth_ratio"] == 0.9
    assert parts[N3]["accepted"] is False and "[mobile element]" in parts[N3]["genes"]
    pr = res["ranked_pairs"][0]
    assert (pr["completion_tier"], pr["ref_completion_partner"], pr["split_gene_links"]) == ("FULL", "yes", 1)
    genes = {g["name"]: g["status"] for g in block["genes"]}
    assert genes["tstA"] == "PRESENT_IN_CORE" and genes["tstC"] == "MISSING_FOUND_CLEAR"
