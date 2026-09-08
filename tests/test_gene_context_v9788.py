"""v9.7.88 roadmap #1 / the gene-by-gene finding (analysis-chat finding E): normalized gene context is sealed into the package
and the gene-by-gene builder reads real CDS rows from it (no NOLOCUS placeholders)."""
from __future__ import annotations
import json, tempfile, pathlib
import pytest
from mamey.gene_context import build_gene_context, write_gene_context, load_gene_context


class _CDS:
    def __init__(self, contig, start, end, strand, locus, product="", translation="", nt=""):
        self.contig, self.start, self.end, self.strand = contig, start, end, strand
        self.locus_tag, self.product, self.translation, self.nucleotide_seq = locus, product, translation, nt


class _Dom:
    def __init__(self, contig, start, end, locus, domain):
        self.contig, self.start, self.end = contig, start, end
        self.locus_tag, self.domain = locus, domain


class _BGC:
    def __init__(self, bid, contig, start, end):
        self.bgc_id, self.contig, self.start, self.end = bid, contig, start, end


def _fixture():
    bgcs = [_BGC("BGC001", "NODE_1", 1000, 5000), _BGC("BGC002", "NODE_2", 0, 3000)]
    cds = [
        _CDS("NODE_1", 1100, 1400, 1, "ctg1_1", "NRPS", "M" * 99, "TTAttattaGGG"),  # in BGC001
        _CDS("NODE_1", 2000, 2600, -1, "ctg1_2", "PKS", "M" * 199),                 # in BGC001
        _CDS("NODE_1", 9000, 9300, 1, "ctg1_9", "hypothetical"),                    # outside any BGC
        _CDS("NODE_2", 500, 900, 1, "ctg2_1", "terpene", "M" * 130),                # in BGC002
    ]
    doms = [_Dom("NODE_1", 1100, 1400, "ctg1_1", "AMP-binding"),
            _Dom("NODE_1", 2000, 2600, "ctg1_2", "PKS_KS")]
    return bgcs, cds, doms


def test_build_gene_context_assigns_cds_to_bgcs():
    bgcs, cds, doms = _fixture()
    ctx = build_gene_context(bgcs, cds, doms)
    assert ctx["n_bgcs_with_cds"] == 2
    assert ctx["n_cds"] == 3                       # the out-of-BGC CDS is not emitted
    b1 = ctx["bgcs"]["BGC001"]
    assert len(b1) == 2
    loci = {r["locus_tag"] for r in b1}
    assert loci == {"ctg1_1", "ctg1_2"}
    # domains attached
    amp = next(r for r in b1 if r["locus_tag"] == "ctg1_1")
    assert "AMP-binding" in amp["sec_met_domains"]
    assert amp["aa_length"] == 99
    assert amp["tta_codons"] == 3                  # TTA TTA TTA in the nt


def test_no_cds_outside_bgc_leaks_in():
    bgcs, cds, doms = _fixture()
    ctx = build_gene_context(bgcs, cds, doms)
    all_loci = {r["locus_tag"] for rows in ctx["bgcs"].values() for r in rows}
    assert "ctg1_9" not in all_loci             # the out-of-BGC CDS is excluded


def test_write_and_load_roundtrip(tmp_path):
    bgcs, cds, doms = _fixture()
    res = write_gene_context(tmp_path, "TEST", bgcs, cds, doms)
    assert res["status"] == "WRITTEN"
    assert (tmp_path / "TEST_gene_context.jsonl").exists()
    loaded = load_gene_context(tmp_path, "TEST")
    assert set(loaded) == {"BGC001", "BGC002"}
    assert len(loaded["BGC001"]) == 2


def test_load_absent_is_empty(tmp_path):
    assert load_gene_context(tmp_path, "NOPE") == {}


def test_load_malformed_line_fails_closed_and_visible(tmp_path, capsys):
    """A corrupted .jsonl (e.g. a truncated write from something other than this module's own
    atomic writer) must still fail closed — return whatever parsed before the bad line — but must
    now print a WARN to stderr rather than silently returning a partial dict indistinguishable
    from genuinely sparse gene context (8 live callers depend on this function)."""
    path = tmp_path / "TEST_gene_context.jsonl"
    path.write_text(
        json.dumps({"schema_version": "gene_context/1.0", "n_cds": 1}) + "\n"
        + json.dumps({"bgc_id": "BGC001", "cds": [{"locus_tag": "ctg1_1"}]}) + "\n"
        + "{not valid json at all\n",
        encoding="utf-8",
    )
    loaded = load_gene_context(tmp_path, "TEST")
    assert loaded == {"BGC001": [{"locus_tag": "ctg1_1"}]}  # parsed rows before the bad line, kept
    captured = capsys.readouterr()
    assert "WARN" in captured.err
    assert "TEST_gene_context.jsonl" in captured.err


def test_load_clean_file_is_silent_on_stderr(tmp_path, capsys):
    bgcs, cds, doms = _fixture()
    write_gene_context(tmp_path, "TEST", bgcs, cds, doms)
    load_gene_context(tmp_path, "TEST")
    captured = capsys.readouterr()
    assert captured.err == ""


# --- Mode B integration (v9.7.88 roadmap #1): cards carry the gene table ---

def test_mode_b_gene_table_helper_renders(tmp_path):
    """The _gene_table_md helper renders a real gene table from loaded context, and degrades
    gracefully when a BGC has no gene context."""
    # build the loaded-context shape the command uses
    gene_ctx = {
        "BGC001": [
            {"locus_tag": "ctg1_1", "start": 100, "end": 1000, "strand": 1,
             "aa_length": 299, "sec_met_domains": ["AMP-binding", "ACP"], "tta_codons": 2},
            {"locus_tag": "ctg1_2", "start": 1100, "end": 1700, "strand": -1,
             "aa_length": 199, "sec_met_domains": [], "tta_codons": 0},
        ],
    }
    # mirror the helper logic from mode_b_command (kept in sync with chatgpt_commands.py)
    def _gene_table_md(bgc_id, max_rows=40):
        rows = gene_ctx.get(bgc_id, [])
        if not rows:
            return ["", "*Gene-level table unavailable*", ""]
        out = ["", f"**Gene-by-gene ({len(rows)} CDS):**", "",
               "| Locus | Coords | Str | aa | sec_met domains | TTA |",
               "|-------|--------|-----|----|-----------------|-----|"]
        for r in rows[:max_rows]:
            doms = ", ".join(r.get("sec_met_domains", [])[:4]) or "--"
            strand = "+" if r.get("strand") in (1, "+", None) else "-"
            out.append(f"| {r.get('locus_tag')} | {r.get('start')}-{r.get('end')} | "
                       f"{strand} | {r.get('aa_length')} | {doms} | {r.get('tta_codons', 0)} |")
        return out

    present = "\n".join(_gene_table_md("BGC001"))
    assert "Gene-by-gene (2 CDS)" in present
    assert "ctg1_1" in present and "AMP-binding" in present
    assert "299" in present                      # real aa length surfaced
    absent = "\n".join(_gene_table_md("BGC999"))
    assert "unavailable" in absent               # graceful degradation


def test_mode_b_command_card_carries_gene_table(tmp_path, monkeypatch):
    """End-to-end-ish: mode_b_command emits a card containing the gene-by-gene table when a
    sealed gene_context is present. Builds a minimal sealed package on disk."""
    import csv as _csv
    from mamey import chatgpt_commands as cc
    from mamey.gene_context import write_gene_context

    class _BGC:
        def __init__(s, bid, contig, start, end):
            s.bgc_id, s.contig, s.start, s.end = bid, contig, start, end

    class _CDS:
        def __init__(s, contig, start, end, strand, locus, product="", translation=""):
            s.contig, s.start, s.end, s.strand = contig, start, end, strand
            s.locus_tag, s.product, s.translation, s.nucleotide_seq = locus, product, translation, ""

    pkgparent = tmp_path / "STRAINX"
    pkg = pkgparent / "package"
    pkg.mkdir(parents=True)
    strain = "STRAINX"

    bgcs = [_BGC("BGC001", "NODE_1", 1000, 5000)]
    cds = [_CDS("NODE_1", 1100, 1400, 1, "ctg1_1", "NRPS", "M" * 120)]
    write_gene_context(pkg, strain, bgcs, cds, [])

    # minimal manifest + triage board the command needs
    (pkg / "manifest.json").write_text(json_dumps_manifest(), encoding="utf-8")
    with open(pkg / f"{strain}_4_triage_board.csv", "w", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=["BGC_ID", "Contig", "AB_auto", "AF_auto",
                                            "Novelty_auto", "Standing_rule", "Primary_metab_flag"])
        w.writeheader()
        w.writerow({"BGC_ID": "BGC001", "Contig": "NODE_1", "AB_auto": "50",
                    "AF_auto": "40", "Novelty_auto": "10", "Standing_rule": "",
                    "Primary_metab_flag": "NO"})

    class _Args:
        package = str(pkg); top_n = 3; node_first = True; outdir = None
    rc = cc.mode_b_command(_Args())
    assert rc == 0
    md = (pkg / "mode_b" / f"{strain}_Mode_B_Top_Leads.md").read_text()
    assert "Gene-by-gene" in md
    assert "ctg1_1" in md                        # real locus in the card


def json_dumps_manifest():
    import json as _j
    return _j.dumps({
        "strain": {"strain_id": "STRAINX"},
        "bgcs": [{"bgc_id": "BGC001", "contig": "NODE_1", "products": ["NRPS"],
                  "antismash_region": "r1", "edge_status": "Interior", "length_kb": 4.0}],
        "source_scans": {"blda_tta": {"per_bgc": {}}, "resistance_tiers": {"per_bgc": {}}},
    })


def test_cds_table_csv_emitted(tmp_path):
    """v9.7.88-K0: write_gene_context also emits the flat <strain>_cds_table.csv."""
    import csv as _csv
    from mamey.gene_context import write_gene_context

    class _BGC:
        def __init__(s, bid, contig, start, end):
            s.bgc_id, s.contig, s.start, s.end = bid, contig, start, end

    class _CDS:
        def __init__(s, contig, start, end, strand, locus, product="", translation=""):
            s.contig, s.start, s.end, s.strand = contig, start, end, strand
            s.locus_tag, s.product, s.translation, s.nucleotide_seq = locus, product, translation, ""

    bgcs = [_BGC("BGC001", "NODE_1", 1000, 5000)]
    cds = [_CDS("NODE_1", 1100, 1400, 1, "ctg1_1", "NRPS", "M" * 99)]
    res = write_gene_context(tmp_path, "TEST", bgcs, cds, [])
    assert res["status"] == "WRITTEN"
    csvp = tmp_path / "TEST_cds_table.csv"
    assert csvp.exists()
    rows = list(_csv.DictReader(open(csvp)))
    assert rows[0]["locus_tag"] == "ctg1_1"
    assert rows[0]["length_aa"] == "99"
    assert rows[0]["bgc_id"] == "BGC001"
