"""v9.7.330 (Blue port): emit-modeb-cards — compact per-BGC Mode-B data cards.

Tests the portable card rendering (composition tag, auto-priors with claim-safety, RG-GMCI banner)
and that every external enrichment degrades gracefully to empty when not supplied — so a card always
renders from the sealed package alone, with no hardcoded workbench paths.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mamey.modeb_cards as mc  # noqa: E402
from mamey.series_common import BGCRecord  # noqa: E402


def test_no_hardcoded_user_paths():
    src = open(os.path.join(os.path.dirname(__file__), "..", "mamey", "modeb_cards.py")).read()
    assert "/Users/" not in src  # workbench absolute paths must not ship


def test_external_loaders_degrade_to_empty():
    assert mc.load_gcf(None) == {}
    assert mc.load_blastp_all() == {}          # ENRICHED_BLASTP / BLASTP_ROOT are None
    assert mc.load_strain_meta() == {}          # STRAIN_TABLE is None
    assert mc.load_isolates_meta() == {}        # ISOLATES_TABLE is None
    dd = mc.load_domains_csv("AS-X", pkg="/nonexistent/pkg")
    assert dd["BGC001"] == {"genes": {}, "domains": []}  # missing domains.csv -> empty, not error


def test_composition_tags():
    assert mc.composition({"PKS-core"}, "T1PKS")[0].startswith("core-only")
    assert "orphan core" in mc.composition({"PKS-core"}, "T1PKS")[1].lower()
    assert mc.composition({"tailoring-methylation"}, "other")[0].startswith("tailoring-cassette")
    assert mc.composition({"PKS-core", "tailoring-methylation"}, "T1PKS")[0] == "core + tailoring"


def _rec():
    return BGCRecord(bgc="BGC004", contig="NODE_1", len_kb=46.7, cls="phosphonate",
                     is_edge=False, ab=81, af=32, novelty="MED", lead_tier="High",
                     kcb_top="rhizocticin A")


def test_card_renders_with_claim_safety_and_no_crash_on_empty_enrichment():
    card = mc.card("AS-40", _rec(), dd={}, ref={}, rgg=[], cblast={}, blastp={}, gcf={},
                   meta={}, boards={})
    assert card.startswith("# Mode-B card — AS-40 · BGC004")
    assert "## Auto-priors" in card
    # priors must carry the claim-safety floor (routing, not activity; KCB = similarity)
    assert "not activity" in card.lower()
    assert "similarity" in card.lower()


def test_card_rggmci_banner_on_high_split_link():
    rgg = [{"partner": "BGC020", "confidence": "HIGH_RG_GMCI_CANDIDATE", "score": "40",
            "partner_products": "NRPS", "rescue_class": "core", "terminus": "", "shared_products": "",
            "guard": ""}]
    # an orphan core with a HIGH split link should surface the RGGMCI-rescued banner
    card = mc.card("AS-40", _rec(), dd={}, ref={}, rgg=rgg, cblast={}, blastp={}, gcf={},
                   meta={}, boards={})
    assert "RGGMCI" in card or "RG-GMCI" in card or "split-pathway" in card.lower()
