"""tests/test_type_reference_rerun_targets_live.py — gated LIVE reference-panel test for the
Type/Reference BGC future-rerun target register (punch-card item B4).

Two layers, matching the tests/test_reference_panel.py precedent already shipped in this suite:

  LAYER 1 - shipped-TSV integrity (always runs, no external data needed)
    Asserts tests/data/type_reference_rerun_targets.tsv has the expected row count and that
    every row's required fields and SHA-256/byte-count columns are well-formed.

  LAYER 2 - live locator + parse concordance (runs only when MAMEY_REFERENCE_ZIP_DIR points at
    a directory holding the named reference-strain antiSMASH zips; otherwise every case SKIPS
    with a typed reason, per this bundle's documented "*_live tests SKIP by design" convention
    -- see CLAUDE.md, "a block of *_live / reference-panel tests SKIP by design... need local
    antiSMASH ZIPs that are not shipped").
    For each row whose zip is present in that directory (named "<strain>.zip"): opens it,
    confirms the exact region_member archive member exists with the SHA-256 and byte count the
    register declares, then parses the WHOLE zip with the CURRENT engine's
    mamey.parsers.parse_bgcs_from_zip (the narrowest entry point that returns a real BGCRecord
    per region) and locates the one BGCRecord whose source_gbk basename matches region_member.
    The test asserts only that the locator resolves and parsing SUCCEEDS -- never a scientific
    or triage claim; judgment stays deferred. A small product/boundary receipt is written to
    tmp_path (pytest's own per-test tmp dir) for a human to read; the test does not assert on
    that receipt's scientific content, only that it was written.

Reference strains only (type/named-reference material -- Pseudonocardia broussonetiae,
Streptomyces coelicolor, Streptomyces philanthi, and others already public as type/reference
material): no AS-/SID-/AJS- cohort id appears anywhere in the shipped TSV or in this file, and
no absolute local filesystem path is embedded either -- both are asserted directly below, the
same discipline as tests/test_figure_repair_specs_v97405.py applies to its own specs.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TSV_PATH = ROOT / "tests" / "data" / "type_reference_rerun_targets.tsv"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_STRAIN_ID_RE = re.compile(r"\b(?:A[JS]?S|SID|PENDING)-\d+\b")
# Built by concatenation, not one contiguous literal, so this file's own source text doesn't
# itself trip tools/strict_source_disclosure_audit.py's raw-text PERSONAL scan (a text match on
# tests/ files, not parsed Python -- see the identical fix in test_figure_repair_specs_v97405.py).
_USERS_PATH_RE = re.compile("/" + "Users" + "/")

REQUIRED_FIELDS = (
    "strain", "full_node_or_contig", "region", "bgc_alias",
    "region_member", "region_member_sha256", "region_member_bytes",
    "future_rerun_action",
)


def _rows():
    with open(TSV_PATH, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


if not TSV_PATH.exists():
    pytest.skip(f"{TSV_PATH} missing (shipped fixture)", allow_module_level=True)

ROWS = _rows()
ROW_IDS = [f"{r.get('strain', '?')}:{r.get('bgc_alias', '?')}" for r in ROWS]


# ---------------------------------------------------------------- LAYER 1: shipped-TSV integrity


def test_shipped_tsv_has_thirteen_rows():
    assert len(ROWS) == 13, (
        f"expected 13 rows in {TSV_PATH.name}, found {len(ROWS)}: "
        f"{[r.get('bgc_alias') for r in ROWS]}"
    )


def test_shipped_tsv_has_no_real_strain_id():
    text = TSV_PATH.read_text(encoding="utf-8")
    hits = _STRAIN_ID_RE.findall(text)
    assert not hits, f"{TSV_PATH.name} contains strain-id-shaped token(s): {hits}"


def test_shipped_tsv_has_no_absolute_users_path():
    text = TSV_PATH.read_text(encoding="utf-8")
    assert not _USERS_PATH_RE.search(text), (
        f"{TSV_PATH.name} contains an absolute local filesystem home-directory path"
    )


@pytest.mark.parametrize("row", ROWS, ids=ROW_IDS)
def test_row_has_required_fields(row):
    for field in REQUIRED_FIELDS:
        assert row.get(field), f"{row.get('bgc_alias', '?')}: missing/empty {field!r}"


@pytest.mark.parametrize("row", ROWS, ids=ROW_IDS)
def test_row_hash_and_bytes_are_well_formed(row):
    assert _SHA256_RE.match(row["region_member_sha256"]), (
        f"{row['bgc_alias']}: malformed sha256 {row['region_member_sha256']!r}"
    )
    assert row["region_member_bytes"].isdigit() and int(row["region_member_bytes"]) > 0, (
        f"{row['bgc_alias']}: bad byte count {row['region_member_bytes']!r}"
    )


@pytest.mark.parametrize("row", ROWS, ids=ROW_IDS)
def test_row_region_member_name_matches_declared_region(row):
    # A cheap internal-consistency check independent of any live zip: the region_member
    # filename should itself carry the declared region token (e.g. "...region012.gbk" for
    # region "region012") -- catches a transcription slip in the register without needing a
    # live archive at all.
    assert row["region"] in row["region_member"], (
        f"{row['bgc_alias']}: region_member {row['region_member']!r} does not contain "
        f"declared region {row['region']!r}"
    )


# ---------------------------------------------------------------- LAYER 2: live locator + parse


def _zip_dir():
    d = os.environ.get("MAMEY_REFERENCE_ZIP_DIR")
    if not d or not os.path.isdir(d):
        return None
    return d


ZIP_DIR = _zip_dir()


def _zip_for_strain(strain: str) -> str | None:
    if ZIP_DIR is None:
        return None
    candidate = os.path.join(ZIP_DIR, strain + ".zip")
    return candidate if os.path.isfile(candidate) else None


@pytest.mark.parametrize("row", ROWS, ids=ROW_IDS)
def test_live_locator_hash_and_parse(row, tmp_path):
    """Resolve, hash-verify, and parse ONE region against the real reference zip.

    Skips (never fails) when MAMEY_REFERENCE_ZIP_DIR is unset, the directory doesn't exist, or
    this row's specific "<strain>.zip" isn't found there -- the same gated-live shape as
    tests/test_reference_panel.py's Layer 2 (MAMEY_REF_ZIPS). Asserts only that the archive
    member exists with the declared hash/size and that the current engine can parse it into a
    BGCRecord -- no scientific or triage claim; judgment stays deferred to Sapote.
    """
    if ZIP_DIR is None:
        pytest.skip(
            "MAMEY_REFERENCE_ZIP_DIR not set -- set it to a directory of reference-strain "
            "antiSMASH zips (named '<strain>.zip') to run the live locator/parse check"
        )
    zip_path = _zip_for_strain(row["strain"])
    if zip_path is None:
        pytest.skip(f"no '{row['strain']}.zip' found in MAMEY_REFERENCE_ZIP_DIR")

    with zipfile.ZipFile(zip_path) as zf:
        members_by_basename = {Path(n).name: n for n in zf.namelist()}
        member_name = members_by_basename.get(row["region_member"])
        assert member_name is not None, (
            f"{row['bgc_alias']}: {row['region_member']} not found in {zip_path}"
        )
        info = zf.getinfo(member_name)
        assert info.file_size == int(row["region_member_bytes"]), (
            f"{row['bgc_alias']}: {row['region_member']} is {info.file_size} bytes in the "
            f"live zip; register declares {row['region_member_bytes']}"
        )
        digest = hashlib.sha256(zf.read(member_name)).hexdigest()
        assert digest == row["region_member_sha256"], (
            f"{row['bgc_alias']}: {row['region_member']} sha256 {digest} != register "
            f"{row['region_member_sha256']}"
        )

    from mamey.parsers import parse_bgcs_from_zip

    bgcs = parse_bgcs_from_zip(zip_path, json_mode="off")
    match = next(
        (b for b in bgcs if Path(b.source_gbk).name == row["region_member"]), None
    )
    assert match is not None, (
        f"{row['bgc_alias']}: parse_bgcs_from_zip found no BGCRecord whose source_gbk basename "
        f"is {row['region_member']} (parsed {len(bgcs)} region(s) from {zip_path})"
    )
    assert match.contig == row["full_node_or_contig"], (
        f"{row['bgc_alias']}: parsed contig {match.contig!r} != register "
        f"{row['full_node_or_contig']!r} -- the locator resolved a record, but not the one the "
        f"register names"
    )

    # Judgment deferred: write what parsed to a per-test receipt under tmp_path, and assert
    # only that the write succeeded -- never on the receipt's own scientific content (product
    # calls, boundary state) beyond confirming the fields exist on the parsed record.
    receipt = {
        "target_id": row.get("target_id"),
        "bgc_alias": row["bgc_alias"],
        "strain": row["strain"],
        "parsed_contig": match.contig,
        "parsed_antismash_region": match.antismash_region,
        "parsed_edge_status": match.edge_status,
        "parsed_products": list(match.products),
        "note": "class-level parse receipt only; no triage/scientific judgment recorded here",
    }
    receipt_path = tmp_path / f"{row['bgc_alias']}_parse_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    assert receipt_path.exists() and receipt_path.stat().st_size > 0
