"""v9.7.89 domain-level Mode B: role mapping, complexity, claim safety, schema, fallbacks."""
from __future__ import annotations
import json, csv, tempfile, os
import pytest
from mamey.domain_level import (load_rules, role_for_domain, build_domain_rows,
                                build_complexity_metrics, build_claim_rows, run_domain_level)


# --- taxonomy / role mapping ---

def test_rules_load():
    tax, claim = load_rules()
    assert tax["_meta"]["schema_version"].startswith("domain_role_taxonomy")
    assert claim["_meta"]["schema_version"].startswith("domain_claim_safety")
    assert len(tax["categories"]) >= 15


def test_core_domain_roles():
    tax, _ = load_rules()
    assert role_for_domain("PKS_KS", tax) == "PKS ketosynthase"
    assert role_for_domain("AMP-binding", tax) == "NRPS A-domain / loading"
    assert role_for_domain("Condensation_LCL", tax) == "NRPS condensation"
    assert role_for_domain("PCP", tax) == "Carrier protein / PP-binding"
    assert role_for_domain("LANC_like", tax) == "Lanthipeptide maturation"
    assert role_for_domain("IucA_IucC", tax) == "Siderophore uptake/export"


def test_evalue_suffix_stripped():
    tax, _ = load_rules()
    # the upstream table appends "(e=...)" — must still map
    assert role_for_domain("Beta-lactamase (e=2.10E-52)", tax) == "Resistance/self-protection"
    assert role_for_domain("Methyltransf_23 (e=1E-9)", tax) == "Methylation/alkylation"


def test_bare_tigr_to_unknown():
    tax, _ = load_rules()
    assert role_for_domain("TIGR03891", tax) == "Unknown/repeat/accessory"


def test_duf_to_unknown():
    tax, _ = load_rules()
    assert role_for_domain("DUF881", tax) == "Unknown/repeat/accessory"


# --- complexity + claims ---

def _fixture_bgcs_and_domains():
    bgcs = [
        {"bgc_id": "BGC001", "strain": "AS-901", "assembly_locator": "NODE_1 region001",
         "products": "NRPS; PKS; T1PKS", "kcb_top": "x", "ab_score": 50, "af_score": 40,
         "contig": "NODE_1", "start": 0, "end": 50000},
        {"bgc_id": "BGC002", "strain": "AS-901", "assembly_locator": "NODE_2 region001",
         "products": "RiPP; lanthipeptide-class-i", "kcb_top": "y", "ab_score": 30, "af_score": 20,
         "contig": "NODE_2", "start": 0, "end": 30000},
    ]
    domains = {
        "BGC001": [{"locus_tag": "c1", "start": 100, "end": 2000, "strand": 1,
                    "domain_name": "PKS_KS", "domain_description": "", "evalue": "1e-50"},
                   {"locus_tag": "c1", "start": 2100, "end": 3000, "strand": 1,
                    "domain_name": "PKS_AT", "domain_description": "", "evalue": "1e-40"},
                   {"locus_tag": "c2", "start": 4000, "end": 5000, "strand": 1,
                    "domain_name": "AMP-binding", "domain_description": "", "evalue": "1e-30"},
                   {"locus_tag": "c2", "start": 5100, "end": 5500, "strand": 1,
                    "domain_name": "PCP", "domain_description": "", "evalue": "1e-20"}],
        "BGC002": [{"locus_tag": "c3", "start": 100, "end": 2000, "strand": 1,
                    "domain_name": "LANC_like", "domain_description": "", "evalue": "1e-50"},
                   {"locus_tag": "c4", "start": 3000, "end": 4000, "strand": 1,
                    "domain_name": "DUF4135", "domain_description": "", "evalue": "1e-30"}],
    }
    return bgcs, domains


def test_complexity_separates_core_from_accessory():
    tax, _ = load_rules()
    bgcs, domains = _fixture_bgcs_and_domains()
    rows = build_domain_rows(bgcs, domains, tax)
    cx = build_complexity_metrics(bgcs, rows)
    b1 = next(c for c in cx if c["BGC_ID"] == "BGC001")
    assert b1["Domain_total"] == 4
    assert b1["Biosynthetic_core_domain_count"] == 4   # KS, AT, AMP, PCP all core


def test_claim_safety_nrps_pks_and_lanthipeptide():
    tax, claim = load_rules()
    bgcs, domains = _fixture_bgcs_and_domains()
    rows = build_domain_rows(bgcs, domains, tax)
    claims = build_claim_rows(bgcs, rows, claim)
    b1 = next(c for c in claims if c["BGC_ID"] == "BGC001")
    assert "assembly-line" in b1["Safe_domain_claims"].lower()
    assert "product" in b1["Unsafe_domain_claims"].lower()
    b2 = next(c for c in claims if c["BGC_ID"] == "BGC002")
    assert "lanthipeptide" in b2["Safe_domain_claims"].lower()
    # SapB caution must be present in the lanthipeptide unsafe claim
    assert "sapb" in b2["Unsafe_domain_claims"].lower() or "morphogen" in b2["Unsafe_domain_claims"].lower()


def test_claims_never_assert_product_identity():
    tax, claim = load_rules()
    bgcs, domains = _fixture_bgcs_and_domains()
    rows = build_domain_rows(bgcs, domains, tax)
    claims = build_claim_rows(bgcs, rows, claim)
    for c in claims:
        # every ceiling is architecture/family-level, never identity
        assert "not product" in c["Domain_claim_ceiling"].lower() or \
               "family" in c["Domain_claim_ceiling"].lower() or \
               "comparator" in c["Domain_claim_ceiling"].lower() or \
               "architecture" in c["Domain_claim_ceiling"].lower()


# --- command smoke + fallback (uses a public reference) ---

REF = next((p for p in ["/mnt/user-data/uploads/BGC0000093.zip"] if os.path.exists(p)), None)


@pytest.mark.skipif(REF is None, reason="no public reference present")
def test_command_writes_outputs_limited_mode():
    import subprocess, glob
    out = tempfile.mkdtemp(prefix="dl_")
    env = dict(os.environ, PYTHONPATH=".")
    subprocess.run(
        ["python3", "-m", "mamey", "run", "--strain", "DLSMOKE", "--display", "ref",
         "--input-zip", REF, "--taxonomy", "Streptomyces", "--source", "test",
         "--outdir", out, "--mode", "standard", "--release", "PUBLIC",
         "--json-evidence", "bounded", "--brief", "none"],
        check=True, capture_output=True, timeout=300, env=env)
    pkg = glob.glob(os.path.join(out, "**", "package"), recursive=True)[0]
    # limited mode (no source zip) — should still write tables from the gene context
    receipt = run_domain_level(pkg, top_n=3)
    assert receipt["status"] == "OK"
    assert receipt["mode"] == "limited_gene_context"
    for f in ["domain_rows_long.csv", "domain_complexity_metrics_by_bgc.csv",
              "domain_safe_unsafe_claims.csv", "domain_role_counts_by_bgc.csv"]:
        assert os.path.exists(os.path.join(pkg, "domain_level", f)), f
    # receipt records the rule versions (auditable schema drift)
    assert "taxonomy_version" in receipt and "claim_safety_version" in receipt


def test_missing_package_writes_failure_receipt_not_crash(tmp_path):
    # a package dir with no manifest -> SKIPPED, core stays valid, no exception
    receipt = run_domain_level(tmp_path, top_n=3)
    assert receipt["status"] == "SKIPPED"
    assert receipt["core_package_valid"] is True


def test_receipt_lists_optional_architecture_and_module_tables(tmp_path, monkeypatch):
    """Every emitted evidence CSV must be named in the domain-level receipt."""
    import mamey.domain_level as dl

    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text("{}", encoding="utf-8")
    bgc = {
        "bgc_id": "BGC001", "strain": "TEST", "assembly_locator": "NODE_1 region001",
        "products": "NRPS", "contig": "NODE_1", "start": 0, "end": 5000,
        "rank": 1, "kcb_top": "", "ab_score": 0, "af_score": 0,
    }
    domains = {"BGC001": [{
        "locus_tag": "ctg1_1", "start": 100, "end": 900, "strand": 1,
        "domain_name": "AMP-binding", "domain_description": "", "evalue": "1e-20",
    }]}
    monkeypatch.setattr(dl, "_top_bgcs_from_package", lambda *_a, **_k: ("TEST", [bgc]))
    monkeypatch.setattr(dl, "domains_from_gene_context", lambda *_a, **_k: domains)

    out = tmp_path / "domain_level"
    receipt = dl.run_domain_level(pkg, top_n=1, outdir=out)
    expected = {
        "domain_rows_long.csv",
        "domain_complexity_metrics_by_bgc.csv",
        "domain_safe_unsafe_claims.csv",
        "domain_role_counts_by_bgc.csv",
        "ordered_domain_architectures_by_bgc.csv",
        "antismash_module_summary_by_bgc.csv",
    }
    assert expected <= set(receipt["files"])
    assert all((out / name).is_file() for name in expected)


# --- Mode B integration (request §9): cards carry the domain block when --with-domain-level ---

def test_mode_b_with_domain_level_injects_block(tmp_path):
    """mode_b_command with --with-domain-level injects a domain-evidence block into each card;
    without the flag, no domain block appears."""
    import csv as _csv
    from mamey import chatgpt_commands as cc
    from mamey.gene_context import write_gene_context

    class _BGC:
        def __init__(s, bid, contig, start, end):
            s.bgc_id, s.contig, s.start, s.end = bid, contig, start, end

    class _CDS:
        def __init__(s, contig, start, end, strand, locus, product=""):
            s.contig, s.start, s.end, s.strand = contig, start, end, strand
            s.locus_tag, s.product, s.translation, s.nucleotide_seq = locus, product, "M" * 120, ""

    class _Dom:
        def __init__(s, contig, start, end, locus, domain):
            s.contig, s.start, s.end, s.locus_tag, s.domain = contig, start, end, locus, domain

    pkg = tmp_path / "STRAINX" / "package"
    pkg.mkdir(parents=True)
    strain = "STRAINX"
    bgcs = [_BGC("BGC001", "NODE_1", 1000, 5000)]
    cds = [_CDS("NODE_1", 1100, 1400, 1, "ctg1_1", "NRPS"),
           _CDS("NODE_1", 1500, 1900, 1, "ctg1_2", "PKS")]
    doms = [_Dom("NODE_1", 1100, 1400, "ctg1_1", "AMP-binding"),
            _Dom("NODE_1", 1100, 1400, "ctg1_1", "Condensation_LCL"),
            _Dom("NODE_1", 1500, 1900, "ctg1_2", "PKS_KS")]
    write_gene_context(pkg, strain, bgcs, cds, doms)

    (pkg / "manifest.json").write_text(json.dumps({
        "strain_id": strain,
        "bgcs": [{"bgc_id": "BGC001", "contig": "NODE_1", "products": ["NRPS", "PKS"],
                  "antismash_region": "r1", "edge_status": "Interior", "length_kb": 4.0,
                  "start": 1000, "end": 5000, "region_number": 1}],
        "source_scans": {"blda_tta": {"per_bgc": {}}, "resistance_tiers": {"per_bgc": {}}},
    }), encoding="utf-8")
    with open(pkg / f"{strain}_4_triage_board.csv", "w", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=["BGC_ID", "Contig", "AB_auto", "AF_auto",
                                            "Novelty_auto", "Standing_rule", "Primary_metab_flag"])
        w.writeheader()
        w.writerow({"BGC_ID": "BGC001", "Contig": "NODE_1", "AB_auto": "50",
                    "AF_auto": "40", "Novelty_auto": "10", "Standing_rule": "",
                    "Primary_metab_flag": "NO"})

    class _Args:
        package = str(pkg); top_n = 3; node_first = True; outdir = None
        with_domain_level = True; source_antismash = None
    assert cc.mode_b_command(_Args()) == 0
    md = (pkg / "mode_b" / f"{strain}_Mode_B_Top_Leads.md").read_text()
    assert "Domain-level evidence" in md
    assert "Biosynthetic core" in md
    assert "claim ceiling" in md.lower()

    # without the flag: no domain block
    import shutil
    shutil.rmtree(pkg / "mode_b")
    class _Args2(_Args):
        with_domain_level = False
    assert cc.mode_b_command(_Args2()) == 0
    md2 = (pkg / "mode_b" / f"{strain}_Mode_B_Top_Leads.md").read_text()
    assert "Domain-level evidence" not in md2


# --- v9.7.90: architecture templates ---

def test_architecture_archetype_assignment():
    from mamey.domain_level import load_architecture_templates, architecture_for_roles
    t = load_architecture_templates()
    assert t, "architecture templates should load"
    # canonical NRPS: A + condensation + carrier, no PKS KS
    nrps = {"NRPS A-domain / loading", "NRPS condensation", "Carrier protein / PP-binding"}
    assert architecture_for_roles(nrps, t) == "canonical NRPS"
    # canonical PKS: KS + AT + carrier, no NRPS condensation
    pks = {"PKS ketosynthase", "PKS acyltransferase/loading", "Carrier protein / PP-binding"}
    assert architecture_for_roles(pks, t) == "canonical type-I PKS"
    # hybrid: both KS and NRPS condensation
    hybrid = {"PKS ketosynthase", "NRPS condensation", "Carrier protein / PP-binding"}
    assert architecture_for_roles(hybrid, t) == "hybrid NRPS-PKS"
    # lanthipeptide
    assert architecture_for_roles({"Lanthipeptide maturation"}, t) == "class-I/II lanthipeptide"


def test_complexity_carries_architecture():
    from mamey.domain_level import load_rules, build_domain_rows, build_complexity_metrics
    tax, _ = load_rules()
    bgcs = [{"bgc_id": "BGC001", "strain": "AS-901", "assembly_locator": "NODE_1 r1",
             "products": "NRPS", "contig": "NODE_1", "start": 0, "end": 5000}]
    domains = {"BGC001": [
        {"locus_tag": "c1", "start": 100, "end": 900, "strand": 1, "domain_name": "AMP-binding"},
        {"locus_tag": "c1", "start": 910, "end": 1200, "strand": 1, "domain_name": "Condensation_LCL"},
        {"locus_tag": "c2", "start": 1300, "end": 1600, "strand": 1, "domain_name": "PCP"}]}
    rows = build_domain_rows(bgcs, domains, tax)
    cx = build_complexity_metrics(bgcs, rows)
    assert cx[0]["Architecture_archetype"] == "canonical NRPS"


# --- v9.7.90 c1/c2: architecture templates + aSModule summary ---

def test_architecture_template_classification():
    from mamey.domain_level import load_architecture_templates, classify_architecture
    t = load_architecture_templates()
    # NRPS roles -> canonical NRPS (no PKS)
    nrps = {"NRPS A-domain / loading", "NRPS condensation", "Carrier protein / PP-binding"}
    arch, _ = classify_architecture(nrps, t)
    assert "NRPS" in arch
    # NRPS + PKS -> hybrid
    hybrid = nrps | {"PKS ketosynthase", "PKS acyltransferase/loading"}
    arch2, _ = classify_architecture(hybrid, t)
    assert "hybrid" in arch2.lower() or "PKS" in arch2
    # nothing recognizable -> accessory-only template (or fallback if even that misses)
    arch3, _ = classify_architecture({"Unknown/repeat/accessory"}, t)
    assert "accessory" in arch3.lower() or arch3 == t["fallback_archetype"]
    # a truly empty role set -> fallback
    arch4, _ = classify_architecture(set(), t)
    assert arch4 == t["fallback_archetype"]


def test_architecture_rows_built():
    from mamey.domain_level import load_rules, load_architecture_templates, build_domain_rows, build_architecture_rows
    tax, _ = load_rules()
    tmpl = load_architecture_templates()
    bgcs = [{"bgc_id": "BGC001", "strain": "AS-901", "assembly_locator": "NODE_1 r1",
             "products": "NRPS", "contig": "NODE_1", "start": 0, "end": 9999}]
    doms = {"BGC001": [
        {"locus_tag": "c1", "start": 100, "end": 500, "strand": 1, "domain_name": "AMP-binding",
         "domain_description": "", "evalue": ""},
        {"locus_tag": "c1", "start": 510, "end": 900, "strand": 1, "domain_name": "Condensation_LCL",
         "domain_description": "", "evalue": ""},
        {"locus_tag": "c2", "start": 1000, "end": 1400, "strand": 1, "domain_name": "PCP",
         "domain_description": "", "evalue": ""}]}
    rows = build_domain_rows(bgcs, doms, tax)
    arch = build_architecture_rows(bgcs, rows, tmpl)
    assert len(arch) == 1
    assert "NRPS" in arch[0]["architecture_archetype"]
    assert arch[0]["domain_architecture_string"].startswith("AMP-binding")
    assert arch[0]["n_domains"] == 3


def test_module_summary_handles_no_modules():
    from mamey.domain_level import build_module_summary
    bgcs = [{"bgc_id": "BGC001", "strain": "AS-901", "assembly_locator": "NODE_1 r1", "products": "NRPS"}]
    rows = build_module_summary(bgcs, {})  # no modules
    assert rows[0]["aSModule_count"] == 0
    assert rows[0]["monomer_pairings"] == "not_computed"
