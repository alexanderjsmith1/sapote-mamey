"""Tests for blastp_online — the NCBI web BLASTp runner + interpreter.

The parse + reconcile + chunk core is offline-unit-tested against a recorded NCBI XML fixture
(the BGC006 ctg12_38 hit). The live submit/poll path is fail-closed: with NCBI unreachable it
returns ok=False and NO fabricated hits — that safety property is tested here directly."""
import os

import pytest

from mamey import blastp_online as bo

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "blast_online_sample.xml")


def test_chunk_giants_solo_rest_batched():
    prots = [("g1", "M" * 3000)] + [(f"s{i}", "M" * 100) for i in range(23)]
    batches = bo.chunk_proteins(prots, 10)
    assert len(batches[0]) == 1 and len(batches[0][0][1]) > bo.GIANT_AA  # giant solo
    assert all(len(b) <= 10 for b in batches)
    assert sum(len(b) for b in batches) == 24


def test_chunk_hard_cap_30():
    """v9.7.240: cap raised 10 -> 30. The 10-cap was a conservative reading of the URLAPI guidance;
    a real 878-protein AS-421 campaign completed at 30/batch (30 RIDs). Giants still run solo."""
    prots = [(f"s{i}", "M" * 50) for i in range(50)]
    batches = bo.chunk_proteins(prots, batch_size=99)  # request 99, must clamp to MAX_BATCH
    assert all(len(b) <= 30 for b in batches) and bo.MAX_BATCH == 30
    assert len(bo.chunk_proteins(prots, batch_size=10)[0]) == 10   # explicit smaller batch still honored


def test_parse_xml_fixture_matches_bgc006():
    pytest.importorskip("Bio")  # parse_blast_xml lazy-imports Bio.Blast.NCBIXML
    xml = open(FIX).read()
    hits = bo.parse_blast_xml(xml, [("ctg12_38", "M" * 350)])
    assert len(hits) == 1
    h = hits[0]
    assert h.blastp_organism.startswith("Amycolatopsis")
    assert h.pct_identity == 95.1
    assert h.query_coverage == 100.0
    assert h.locus_tag == "ctg12_38"


def test_reconcile_confirm_and_review():
    assert bo.reconcile("MbtH", "MbtH family protein [Amycolatopsis]") == "CONFIRM"
    # antiSMASH Beta-lactamase vs an esterase hit must NOT auto-confirm (the real overturn case)
    assert bo.reconcile("Beta-lactamase", "EstA serine hydrolase esterase") == "REVIEW"
    assert bo.reconcile("PKS_KS", "") == "NO_HIT"


def test_run_batch_online_fails_closed_without_network():
    # NCBI unreachable in the sandbox -> ok=False, clear reason, ZERO fabricated hits.
    res = bo.run_batch_online([("x", "MKV")], poll_seconds=1, max_wait_seconds=2)
    assert res.ok is False
    assert res.hits == []


def test_run_batch_online_rejects_oversized():
    big = [(f"s{i}", "M" * 10) for i in range(31)]   # v9.7.240: >MAX_BATCH(30) still fails closed
    res = bo.run_batch_online(big)
    assert res.ok is False and "30" in res.reason


def test_reconcile_against_real_bgc006_run():
    """Regression: validate reconcile() against the real 61-gene AS-424/BGC006 BLASTp run
    (RID 4E4J591J016 lineage). The two known antiSMASH overturns — ctg12_21 (Phenol_Hydrox ->
    ferritin) and ctg12_71 (Beta-lactamase -> EstA esterase) — must NOT auto-CONFIRM; they are
    flagged REVIEW for author judgment, which is the whole claim-safety point of the channel."""
    import csv
    fix = os.path.join(os.path.dirname(__file__), "fixtures", "bgc006_online_blastp.csv")
    rows = list(csv.DictReader(open(fix)))
    assert len(rows) == 61
    by_lt = {r["locus_tag"]: r for r in rows}
    for lt in ("ctg12_21", "ctg12_71"):
        r = by_lt[lt]
        assert bo.reconcile(r["antismash_domains"], r["blastp_top_def"]) == "REVIEW", \
            f"{lt} is a known overturn; must be REVIEW, never auto-CONFIRM"
    # a clean core PKS gene whose hit echoes the domain should CONFIRM
    confirms = sum(1 for r in rows if bo.reconcile(r["antismash_domains"], r["blastp_top_def"]) == "CONFIRM")
    assert confirms >= 15  # ~24 in practice; lock a floor


def test_plan_round_full_top_plus_sampling(monkeypatch):
    """Round-1 shape: FULL proteins for top-N BGCs + one representative for every other BGC
    (saccharides included). This is the phased prioritization the standing model requires."""
    import mamey.modeb_template_emitter as emit
    monkeypatch.setattr(emit, "_read_triage", lambda pkg: [{"BGC_ID": f"BGC00{i}"} for i in range(1, 6)])
    monkeypatch.setattr(emit, "_select_scope", lambda pkg, tr, scope, n: [f"BGC00{i}" for i in range(1, 6)])
    monkeypatch.setattr(emit, "_gene_rows_for_bgc",
                        lambda pkg, bid: [{"locus_tag": f"{bid}_g{j}", "translation": "M" * (100 + j * 40)}
                                          for j in range(4)])
    p = bo.plan_round("/tmp/pkgX/pkg", full_top=3, sample_per_bgc=1)
    assert p["full_bgcs"] == ["BGC001", "BGC002", "BGC003"]     # top-3 full
    assert p["sampled_bgcs"] == ["BGC004", "BGC005"]            # rest sampled
    assert p["n_proteins"] == 3 * 4 + 2 * 1                     # 12 full + 2 sampled = 14


def test_plan_round_samples_every_remaining_bgc_including_saccharide(monkeypatch):
    """Even a saccharide BGC (last in rank) must get its 1 representative protein — a
    representative BLASTp is what can promote a saccharide the scanners would downgrade."""
    import mamey.modeb_template_emitter as emit
    monkeypatch.setattr(emit, "_read_triage", lambda pkg: [{"BGC_ID": "BGC001"}, {"BGC_ID": "SACC"}])
    monkeypatch.setattr(emit, "_select_scope", lambda pkg, tr, scope, n: ["BGC001", "SACC"])
    monkeypatch.setattr(emit, "_gene_rows_for_bgc",
                        lambda pkg, bid: [{"locus_tag": f"{bid}_g0", "translation": "M" * 200}])
    p = bo.plan_round("/tmp/pkgY/pkg", full_top=1, sample_per_bgc=1)
    assert "SACC" in p["sampled_bgcs"]     # saccharide is NOT skipped
    assert p["n_proteins"] == 2


def test_plan_round_no_triage_is_graceful(monkeypatch):
    import mamey.modeb_template_emitter as emit
    monkeypatch.setattr(emit, "_read_triage", lambda pkg: [])
    p = bo.plan_round("/tmp/pkgZ/pkg")
    assert p["n_proteins"] == 0 and "note" in p


def _load_bgc006_hits():
    import csv
    from mamey.blastp_online import BlastpHit
    fix = os.path.join(os.path.dirname(__file__), "fixtures", "bgc006_online_blastp.csv")
    hits = []
    for r in csv.DictReader(open(fix)):
        h = BlastpHit(locus_tag=r["locus_tag"], aa_length=0, antismash_domains=r["antismash_domains"],
                      blastp_top_def=r["blastp_top_def"], blastp_organism=r["organism"],
                      pct_identity=float(r["pct_identity"]) if r["pct_identity"] else None)
        h.top_hits = [{"hit_def": r["blastp_top_def"], "organism": r["organism"],
                       "pct_identity": h.pct_identity,
                       "query_coverage": float(r["query_coverage"]) if r.get("query_coverage") else None}]
        hits.append(h)
    return hits


def test_cluster_coherence_bgc006_ground_truth():
    """§9 reads validate against the real BGC006 run: low genome-span (vertically inherited,
    NOT recent HGT), higher-id core than periphery, Amycolatopsis consensus, and the flagged
    Streptomyces mosaic island near ctg12_64-66."""
    c = bo.cluster_coherence(_load_bgc006_hits())
    assert c["genome_span"]["fraction"] <= 0.15
    assert "genus-wide" in c["genome_span"]["read"]
    assert c["identity_distribution"]["core_mean"] >= c["identity_distribution"]["periphery_mean"]
    assert c["consensus_genus"] == "Amycolatopsis"
    assert any(b["genus"] == "Streptomyces" for b in c["genus_breaks"])


def test_function_and_novelty_bgc006_two_axes():
    """The whole BGC006 correction in one call, with the two novelty axes kept separate:
    genes are CONSERVED (high mean id, mostly characterized functions) yet the product is NOVEL
    because the KCB anchor (colibrimycin) shares only a handful of genes -> not a product match.
    This is the §10.2 lesson: gene conservation does NOT make the compound known."""
    hits = _load_bgc006_hits()
    fn = bo.function_and_novelty(hits, kcb_top="colibrimycin", kcb_coverage_genes=4)
    # product axis: NOVEL (few shared genes, fail-safe toward novelty)
    assert fn["product_novelty"]["tier"] == "NOVEL"
    # gene axis: conserved (this is what makes the two-axis separation the whole point)
    assert fn["gene_novelty"]["mean_top_hit_identity"] > 80
    # function: mostly characterizable, with core + resistance roles detected
    assert fn["function"]["characterized_fraction"] > 0.5
    assert fn["function"]["role_counts"].get("resistance")
    assert any(r.startswith("core_") for r in fn["function"]["role_counts"])


def test_product_novelty_gate_fires_only_on_substantial_overlap():
    """KNOWN_COMPOUND requires substantial cluster overlap, not a high KCB score with few genes."""
    hits = _load_bgc006_hits()
    assert bo.function_and_novelty(hits, kcb_top="x", kcb_coverage_genes=4)["product_novelty"]["tier"] == "NOVEL"
    assert bo.function_and_novelty(hits, kcb_top="x", kcb_coverage_genes=25)["product_novelty"]["tier"] == "KNOWN_COMPOUND"


def test_novelty_high_divergence_when_ids_low():
    from mamey.blastp_online import BlastpHit
    hits = [BlastpHit(locus_tag=f"g{i}", aa_length=300, antismash_domains="PKS_KS",
                      blastp_top_def="hypothetical protein", blastp_organism="Streptomyces sp.",
                      pct_identity=40.0, top_hits=[{"organism": "Streptomyces sp.", "pct_identity": 40.0}])
            for i in range(6)]
    fn = bo.function_and_novelty(hits)
    # low identity across all genes -> highly-divergent GENE novelty
    assert fn["gene_novelty"]["mean_top_hit_identity"] < 55
    # v9.7.335: this used to assert product_novelty == "NOVEL". It was codifying the defect: no
    # kcb_top / kcb_coverage_genes is passed here, so the assertion was really "absence of a
    # characterised-reference cross-check proves the product is novel". Low BLASTp identity is
    # GENE-level divergence; product novelty needs the cluster-level comparison, which was never
    # made. Absence of a test is not a negative result — the honest tier is UNDETERMINED.
    assert fn["product_novelty"]["tier"] == "UNDETERMINED"
    # and with the cross-check actually supplied, the real call still works:
    known = bo.function_and_novelty(hits, kcb_top="BGC0000001", kcb_coverage_genes=8)
    assert known["product_novelty"]["tier"] != "UNDETERMINED"
