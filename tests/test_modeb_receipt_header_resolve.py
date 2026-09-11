"""v9.7.198 regression: ingest-receipts must resolve the BGC ID from BOTH the emit-modeb-template
keyed header and the judgment_store canonical header."""
from mamey.mode_b_receipt import _parse_card_bgc_id


def test_parse_bgc_id_from_emitter_template_header():
    hdr = ("<!-- MODE B TEMPLATE | bgc: BGC008 | node: NODE_162 | "
           "strain: AS-705 | contract: modeb_corrective_full30_v1 -->")
    assert _parse_card_bgc_id(hdr) == "BGC008"


def test_parse_bgc_id_from_canonical_header_unchanged():
    hdr = "<!-- MODE B: BGC008 | strain: AS-705 | session: s1 -->"
    assert _parse_card_bgc_id(hdr) == "BGC008"


def test_parse_bgc_id_no_header_returns_empty():
    assert _parse_card_bgc_id("# Mode B - no header comment") == ""
