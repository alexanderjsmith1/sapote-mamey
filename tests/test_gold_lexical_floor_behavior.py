"""Exercise the real gold-completeness path, not a copy of its formula."""
import hashlib

import pytest

from mamey.validate import validate_package
from tests.test_v9_7_335_tier1_gates_known_bad_input import (
    _make_min_package, _seal04_write_manifest,
)


AUTHOR_MINIMAL = (
    "## §1 Identity\n\nExact locus bound to node and region; class-level read only.\n\n"
    "## §2 Boundary\n\nInterior placement, both flanks present on this contig.\n\n"
    "## §3 Evidence\n\nDomain census recorded; comparator similarity is not identity.\n\n"
)
GOOD = AUTHOR_MINIMAL + "Evidence provenance remains explicitly recorded.\n"
FILLER = "".join(f"## §{i} Section {i}\n\n" + "x " * 120 + "\n" for i in range(1, 5))


@pytest.mark.parametrize("text,expected", [
    (FILLER, "JUDGMENT_PENDING"),
    (AUTHOR_MINIMAL, "JUDGMENT_PENDING"),  # 190 non-whitespace chars: below existing 200 floor
    (GOOD, "PASS"),
])
def test_real_validator_credits_only_control_card(tmp_path, text, expected):
    pkg = _make_min_package(tmp_path)
    for number in (1, 2):
        (pkg / f"AS-TEST__NODE_1_length_10000_cov_1__region00{number}__BGC00{number}__mode_b.md").write_text(text)
    _seal04_write_manifest(pkg)
    result = validate_package(pkg, write_status_receipt=False)
    assert result["gold_completeness"] == expected, result
    assert result["checksum_integrity"] == "PASS", result
    assert result["status"] == ("PASS" if expected == "PASS" else "MAMEY_COMPLETE"), result
    expected_seals = {f"BGC00{n}": hashlib.sha256(text.encode()).hexdigest() for n in (1, 2)} if expected == "PASS" else {}
    assert result["mode_b_card_seals"] == expected_seals


def test_missing_sections_not_rescued_by_varied_body(tmp_path):
    pkg = _make_min_package(tmp_path)
    text = '\n'.join(line for line in GOOD.splitlines() if not line.startswith('##')) * 3
    for number in (1, 2):
        (pkg / f"AS-TEST__NODE_1_length_10000_cov_1__region00{number}__BGC00{number}__mode_b.md").write_text(text)
    _seal04_write_manifest(pkg)
    assert validate_package(pkg, write_status_receipt=False)['gold_completeness'] == 'JUDGMENT_PENDING'
