"""Tests for singleton_filter.py — biosynthetic-relevance filter for the singleton metric."""
from __future__ import annotations

import os
import csv
from pathlib import Path
import pytest

from mamey.singleton_filter import (
    classify_singleton,
    filter_singletons,
    filtered_singleton_count,
    SingletonClassification,
)


class TestClassifySingleton:
    # --- housekeeping: should be dropped ---
    def test_ribosomal_protein_dropped(self):
        c = classify_singleton("Ribosomal_S7")
        assert not c.biosynthetic_relevant
        assert "housekeeping" in c.reason

    def test_ef_g_dropped(self):
        assert not classify_singleton("EFG_C").biosynthetic_relevant
        assert not classify_singleton("GTP_EFTU_D3").biosynthetic_relevant

    def test_dna_helicase_dropped(self):
        assert not classify_singleton("UvrD-helicase").biosynthetic_relevant
        assert not classify_singleton("DEAD").biosynthetic_relevant

    def test_crispr_cas_dropped(self):
        assert not classify_singleton("Cas_Cas1").biosynthetic_relevant
        assert not classify_singleton("CRISPR_Cas2").biosynthetic_relevant

    def test_glycogen_enzymes_dropped(self):
        # BGC052 — the all-housekeeping case
        assert not classify_singleton("GlgE_dom_N_S").biosynthetic_relevant
        assert not classify_singleton("Malt_amylase_C").biosynthetic_relevant
        assert not classify_singleton("Phosphorylase").biosynthetic_relevant

    def test_menaquinone_dropped(self):
        # BGC062 — menaquinone misclassified as halogenated
        assert not classify_singleton("VitK2_biosynth").biosynthetic_relevant

    def test_mep_isoprenoid_dropped(self):
        # BGC015 — GcpE is MEP-pathway primary metabolism
        assert not classify_singleton("GcpE").biosynthetic_relevant

    def test_phb_storage_dropped(self):
        assert not classify_singleton("PHB_acc_N").biosynthetic_relevant

    def test_chaperone_dropped(self):
        assert not classify_singleton("AHSA1").biosynthetic_relevant

    # --- biosynthetic: should be kept ---
    def test_hemerythrin_kept(self):
        # BGC063 — non-heme di-iron tailoring, in override list
        c = classify_singleton("Hemerythrin")
        assert c.biosynthetic_relevant
        assert "override" in c.reason

    def test_rhs_toxin_kept(self):
        # ecological weapon, kept via override
        assert classify_singleton("RHS").biosynthetic_relevant
        assert classify_singleton("Ntox30").biosynthetic_relevant

    def test_cell_wall_enzymes_kept(self):
        # BGC064 — LysM + Peptidase_M23 inside an antifungal BGC
        assert classify_singleton("LysM").biosynthetic_relevant
        assert classify_singleton("Peptidase_M23").biosynthetic_relevant

    def test_spermine_synth_kept(self):
        # BGC007 — polyamine incorporation into a RiPP
        assert classify_singleton("Spermine_synth").biosynthetic_relevant

    def test_methyltransferase_kept(self):
        # not on blocklist → retained by default
        assert classify_singleton("Methyltransf_21").biosynthetic_relevant

    def test_sulfotransferase_kept(self):
        # BGC006 — distinctive tailoring
        assert classify_singleton("Sulfotransfer_5").biosynthetic_relevant

    def test_unknown_domain_kept_by_default(self):
        c = classify_singleton("DUF6333")
        assert c.biosynthetic_relevant
        assert "retained" in c.reason

    # --- antiSMASH tag override ---
    def test_biosynthetic_tag_protects_ambiguous_domain(self):
        # A domain that would otherwise be ambiguous, but the gene is tagged biosynthetic
        c = classify_singleton("Aminotran_1_2",
                               "biosynthetic-additional (smcogs) SMCOG1019: aminotransferase")
        assert c.biosynthetic_relevant
        assert "antiSMASH" in c.reason

    def test_blocklist_domain_still_dropped_without_tag(self):
        # Ribosomal protein with no biosynthetic tag → dropped
        c = classify_singleton("Ribosomal_S7", "")
        assert not c.biosynthetic_relevant

    def test_blocklist_beats_biosynthetic_tag_for_ribosomal(self):
        # The housekeeping blocklist runs BEFORE the antiSMASH tag (v2 fix). A ribosomal protein is
        # dropped even if antiSMASH happened to tag its gene biosynthetic — the Pfam identity is
        # authoritative for clear housekeeping families. This is the fix that lets BGC052's
        # saccharide-tagged glycogen enzymes drop correctly.
        c = classify_singleton("Ribosomal_S7", "biosynthetic (rule-based-clusters) nucleoside")
        assert not c.biosynthetic_relevant
        assert "housekeeping" in c.reason


class TestFilterSingletons:
    def test_mixed_gene_splits_correctly(self):
        # A gene carrying both a real tailoring domain and a housekeeping domain
        keep, drop = filter_singletons(["Methyltransf_21", "Ribosomal_S7"], "")
        assert "Methyltransf_21" in keep
        assert "Ribosomal_S7" in drop

    def test_all_housekeeping(self):
        keep, drop = filter_singletons(["GlgE_dom_N_S", "Malt_amylase_C"], "")
        assert keep == []
        assert len(drop) == 2

    def test_all_biosynthetic(self):
        keep, drop = filter_singletons(["Hemerythrin", "Methyltransf_21"], "")
        assert len(keep) == 2
        assert drop == []


class TestFilteredSingletonCount:
    def test_bgc052_all_housekeeping_filtered_to_zero(self):
        # BGC052 — 7 raw singleton genes, all glycogen enzymes → 0 filtered
        gene_singletons = [
            (["Mak_N_cap"], ""),
            (["Malt_amylase_C", "TIGR02456"], ""),
            (["GlgE_dom_N_S"], ""),
            (["Phosphorylase", "TIGR02094"], ""),
            (["P_proprotein"], ""),
            (["TIGR02100"], ""),
            (["CopD"], ""),
        ]
        raw, filtered = filtered_singleton_count(gene_singletons)
        assert raw == 7
        assert filtered <= 2  # P_proprotein/CopD may survive as "unknown"; glycogen core all drop

    def test_bgc007_mostly_biosynthetic_survives(self):
        # BGC007 — dark RRE-RiPP, should keep most singletons
        gene_singletons = [
            (["Spermine_synth"], ""),
            (["DUF2617"], ""),
            (["Pantocin_Microcin_RRE", "ThiF"], "biosynthetic-additional (rule-based-clusters)"),
            (["Peptidase_M14"], ""),
            (["YbjN"], ""),
            (["AAA", "ClpB_D2-small"], ""),   # this one is housekeeping (Clp)
            (["Peptidase_M43"], ""),
        ]
        raw, filtered = filtered_singleton_count(gene_singletons)
        assert raw == 7
        assert filtered >= 5  # most are kept; only the Clp ATPase gene drops

    def test_empty_input(self):
        assert filtered_singleton_count([]) == (0, 0)


# ---------------------------------------------------------------------------
# Integration: real-package data — verify the filter produces the expected reordering.
# The strain/package is operator-supplied via SINGLETON_REAL_PKG + SINGLETON_REAL_SID (env), so no
# real strain ID is baked into the source (leak-audit clean). Skips unless the package is on disk.
# ---------------------------------------------------------------------------

_REAL_SID = os.environ.get("SINGLETON_REAL_SID", "AS-900")
REAL_PKG = Path(os.environ.get("SINGLETON_REAL_PKG", f"/data/mamey-local/intake/runs_v114/{_REAL_SID}/package"))

@pytest.mark.skipif(not REAL_PKG.exists(), reason="real package not on disk (set SINGLETON_REAL_PKG)")
class TestRealDataReordering:
    def _load(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from mamey.enrichment_sections import parse_genes, genome_domain_frequency

        gene_rows = {}
        with (REAL_PKG / f"{_REAL_SID}_gene_by_gene_all_bgcs.csv").open() as f:
            for row in csv.DictReader(f):
                gene_rows.setdefault(row["bgc_id"], []).append(row)
        genes_by_bgc = {b: parse_genes(r) for b, r in gene_rows.items()}
        freq = genome_domain_frequency(genes_by_bgc)

        cds_fn = {}
        with (REAL_PKG / f"{_REAL_SID}_cds_table.csv").open() as f:
            for row in csv.DictReader(f):
                cds_fn[(row["bgc_id"], row["locus_tag"])] = (row.get("gene_functions") or "").strip()
        return genes_by_bgc, freq, cds_fn

    def _counts(self, bgc, genes_by_bgc, freq, cds_fn):
        gene_singletons = []
        for g in genes_by_bgc[bgc]:
            uniq = [d for d in g.domains if freq.get(d, 0) == 1]
            if uniq:
                gene_singletons.append((uniq, cds_fn.get((bgc, g.locus), "")))
        return filtered_singleton_count(gene_singletons)

    def test_bgc015_drops_sharply(self):
        # BGC015 — 11 raw, mostly housekeeping → should drop well below raw
        genes_by_bgc, freq, cds_fn = self._load()
        raw, filtered = self._counts("BGC015", genes_by_bgc, freq, cds_fn)
        assert raw >= 10
        assert filtered < raw * 0.6  # at least 40% filtered out

    def test_bgc052_drops_to_near_zero(self):
        # BGC052 — all glycogen → near zero
        genes_by_bgc, freq, cds_fn = self._load()
        raw, filtered = self._counts("BGC052", genes_by_bgc, freq, cds_fn)
        assert raw >= 6
        assert filtered <= 2

    def test_bgc007_largely_survives(self):
        # BGC007 — dark RiPP, should retain most
        genes_by_bgc, freq, cds_fn = self._load()
        raw, filtered = self._counts("BGC007", genes_by_bgc, freq, cds_fn)
        assert filtered >= raw - 2

    def test_bgc028_lasso_survives(self):
        # BGC028 — Asn_synthase + TrwC; TrwC is mobile (drops), Asn_synthase biosynthetic (keeps)
        genes_by_bgc, freq, cds_fn = self._load()
        raw, filtered = self._counts("BGC028", genes_by_bgc, freq, cds_fn)
        assert filtered >= 1  # the lasso cyclase must survive


class TestSubstringContainmentFix:
    """v9.7.116: the original module matched stems as bare substrings (`stem in domain`), which
    SILENTLY DROPPED genuine biosynthetic domains whose names contain a short housekeeping stem.
    These pin the token-boundary fix — every domain here is biosynthetic and must be KEPT."""

    def test_trans_at_s1_kept(self):
        # 'S1' (ribosomal) bare-substring-matched 'Trans_AT_S1' (a trans-AT PKS domain)
        assert classify_singleton("Trans_AT_S1").biosynthetic_relevant

    def test_pks_docking_s1_kept(self):
        assert classify_singleton("PKS_Docking_S1").biosynthetic_relevant

    def test_peptidase_s1_kept(self):
        # Peptidase S1 family — a tailoring protease, not ribosomal S1
        assert classify_singleton("Peptidase_S1").biosynthetic_relevant
        assert classify_singleton("Peptidase_S15").biosynthetic_relevant

    def test_nadhpyr_redox_kept(self):
        # 'NADH' bare-matched 'NADHpyr_redox' (a redox tailoring domain)
        assert classify_singleton("NADHpyr_redox").biosynthetic_relevant

    def test_gtra_like_kept_but_bare_gtra_dropped(self):
        assert classify_singleton("GtrA_like").biosynthetic_relevant   # distinct domain — keep
        assert not classify_singleton("GtrA").biosynthetic_relevant     # bare flippase — drop

    def test_abc1_kinase_kept_but_bare_abc1_dropped(self):
        assert classify_singleton("ABC1_kinase").biosynthetic_relevant
        assert not classify_singleton("ABC1").biosynthetic_relevant

    def test_ribosomal_prefix_still_catches_inflected_forms(self):
        # the prefix tier must still catch the real ribosomal proteins
        assert not classify_singleton("Ribosomal_S7").biosynthetic_relevant
        assert not classify_singleton("Ribosomal_S1").biosynthetic_relevant
        assert not classify_singleton("Ribosom_S12_S23").biosynthetic_relevant
