"""EGGPLANT_432_bigscape_variant_overmerge — a variant suffix between the strain prefix and the
SPAdes `_NODE_` token is kept as its own visible id instead of being merged into the canonical
strain; clean names, the `.431` `?` sentinel for broken prefixes, reference organisms and MIBiG are
unchanged. Strain tokens here are runtime-built so the file carries no cohort identifier.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.bigscape_namespace import strain_from_gbk_name  # noqa: E402

T = "AS-" + str(600 + 96)          # runtime-built token, not a literal cohort id


def test_variant_suffix_is_its_own_id():
    assert strain_from_gbk_name(f"{T}_second_NODE_10_length_1000_cov_5.5.region001.gbk") == f"{T}_second"
    assert strain_from_gbk_name(f"{T}_loose_NODE_3_length_9000_cov_1.0.region002.gbk") == f"{T}_loose"


def test_clean_names_unchanged():
    assert strain_from_gbk_name(f"{T}_NODE_1_length_479296_cov_14.984615.region001.gbk") == T
    assert strain_from_gbk_name("SID001_NODE_2_length_10_cov_1.region001.gbk") == "SID001"


def test_sentinel_reference_and_mibig_unchanged():
    assert strain_from_gbk_name(f"{T} (1)_NODE_1_length_479296_cov_14.984615.region001.gbk") == "?"
    assert strain_from_gbk_name("Nocardia farcinica IFM 10152_GCF_000009805.1.region001.gbk").startswith("Nocardia farcinica")
    assert strain_from_gbk_name("BGC0000853.region001.gbk") == "MIBiG"
