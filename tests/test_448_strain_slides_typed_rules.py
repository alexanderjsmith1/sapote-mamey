"""Typed class rules (T3PKS, fatty_acid, RiPP-like, quinone, butyrolactone, nucleoside) add family-evidence lines to
"What the genes show"; a product with no typed rule adds nothing."""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import strain_slides as ss  # noqa: E402
import typed_class_rules  # noqa: E402

RULES = Path(__file__).resolve().parents[1] / "tools" / "typed_class_rules.json"


def _D(product):
    dom = defaultdict(list)
    dom["ctg1_1"] = [(1e-40, "Chal_sti_synt_N", "", "PFAM_domain"), (1e-30, "Chal_sti_synt_C", "", "PFAM_domain")]
    return {"genes": {"BGC001": [{"locus_tag": "ctg1_1", "sec_met_domains": "", "product_qualifier": ""}]},
            "dom": dom, "inv": {"BGC001": {"Products": product}}, "typed_rules": typed_class_rules.load_rules(RULES)}


def _text(paras):
    return "\n".join("".join(r[0] for r in p) for p in paras)


def test_t3pks_gets_a_family_line_naming_the_gene():
    t = _text(ss.typed_paras(_D("T3PKS"), "BGC001"))
    assert t.startswith("T3PKS: ") and "ctg1_1" in t


def test_a_product_without_a_typed_rule_adds_nothing():
    assert ss.typed_paras(_D("NRPS"), "BGC001") == []
