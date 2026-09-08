# =============================================================================
# CANDIDATE REGRESSION TEST — CLAUDE_409_schemas_contracts lane
# Structural / SSOT fixes for the schema + contract-provenance audit findings:
#   F3  schemas/manifest_contract.json is not a valid standalone JSON Schema
#       (declares draft 2020-12 but has no root applicator -> accepts ANY JSON)
#   F1  mamey/data/mode_b/modeb_full30_corrective_contract.json is misnamed
#       ('full30' filename vs 48-section content) -> SSOT hazard
#   F2  mamey/data/mode_b/PROVENANCE.md cites the DELETED §1-§20 contract JSON
#       (modeb_full20_corrective_contract.json) as the *current* contract
# Evidence: development/audit/AUDIT_schemas_contracts.md (F1, F2, F3).
#
#   Drop this file in tests/ on the patched base (rename to
#   test_claude_409_schemas_contracts.py). It reads the shipped files only;
#   it does not import mamey and needs no gold package, so it does NOT skip in
#   a normal checkout. `jsonschema` is optional: if installed the F3 test also
#   asserts real standards-based accept/reject; otherwise it asserts the
#   structural invariant (root $ref -> an existing $defs member) that makes the
#   file conformant.
#
#   FAIL-before (unpatched .408):
#     - manifest_contract.json has NO top-level "$ref"/"type" -> empty root
#       schema accepts {} (and any JSON).
#     - the contract JSON has no filename<->content reconciliation note.
#     - PROVENANCE.md asserts the deleted modeb_full20_corrective_contract.json
#       is "the machine-readable ... contract for current ... Mode B cards".
#   PASS-after (this lane's three .patch files): the assertions below.
# =============================================================================
import json
from pathlib import Path

import pytest


def _root() -> Path:
    """Locate the bundle root by walking up to the dir that holds both
    `schemas/` and `mamey/data/mode_b/`."""
    here = Path(__file__).resolve()
    for cand in [here.parent, *here.parents]:
        if (cand / "schemas" / "manifest_contract.json").exists() and \
           (cand / "mamey" / "data" / "mode_b").is_dir():
            return cand
    raise RuntimeError("bundle root not found from %s" % here)


ROOT = _root()
MANIFEST_SCHEMA = ROOT / "schemas" / "manifest_contract.json"
CONTRACT = ROOT / "mamey" / "data" / "mode_b" / "modeb_full30_corrective_contract.json"
PROVENANCE = ROOT / "mamey" / "data" / "mode_b" / "PROVENANCE.md"


# --- F3: manifest_contract.json validates as a real standalone JSON Schema ----
def test_manifest_contract_has_root_applicator():
    """A draft-2020-12 schema with no root applicator accepts any document.
    The fix adds a root `$ref` to the real definition so the file constrains
    manifest.json when run through a standards validator."""
    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    ref = schema.get("$ref")
    assert ref == "#/$defs/manifest", (
        "root schema must reference the manifest definition (was: %r) — "
        "without it the root is empty and validates any JSON" % ref)
    target = ref.split("/")[-1]
    assert target in schema.get("$defs", {}), "root $ref target must exist in $defs"
    sub = schema["$defs"][target]
    assert sub.get("type") == "object" and sub.get("required"), \
        "referenced definition must actually constrain the object"


def test_manifest_contract_bespoke_reader_path_intact():
    """The fix must not disturb the path the bespoke reader uses
    (mamey/manifest_schema.py:check_package_contract reads $defs.manifest and
    the x-package-contract extension directly)."""
    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    assert "manifest" in schema["$defs"]
    assert "x-package-contract" in schema, "package artifact rules must remain"


def test_manifest_contract_rejects_empty_object():
    """Behavioural before/after. Post-fix a bare {} fails the contract; pre-fix
    (empty root) it passed. Uses jsonschema if present, else the equivalent
    required-key check on the now-referenced definition."""
    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    try:
        import jsonschema  # type: ignore
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({}, schema)
    except ImportError:
        target = schema["$ref"].split("/")[-1]
        required = schema["$defs"][target]["required"]
        missing = [k for k in required if k not in {}]
        assert missing, "referenced definition must impose required keys on {}"


# --- F1: the misnamed contract carries an in-band SSOT reconciliation note ----
def test_contract_filename_provenance_note_present():
    """The file keeps its historical 'full30' name (code + tests bind to it),
    so an in-band note must reconcile filename vs the authoritative 48-section
    schema_version to defuse the SSOT hazard."""
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["schema_version"] == "modeb_corrective_full48_v1"
    note = contract.get("filename_provenance", "")
    assert note, "contract must carry a filename_provenance SSOT note"
    assert "full48" in note and "schema_version" in note
    # the loader guard (mamey/modeb_structure_gate.py:load_contract) still holds
    assert contract.get("sections"), "sections[] must remain"
    assert len(contract["sections"]) == 48, "48-section content is the truth"


# --- F2: PROVENANCE.md no longer cites the deleted §20 contract as current ----
def test_provenance_names_live_contract_not_deleted_full20():
    text = PROVENANCE.read_text(encoding="utf-8")
    # must not present the deleted standalone file as the current contract
    assert "`modeb_full20_corrective_contract.json` is the machine-readable" not in text
    # must name the live contract + its schema_version + §1-§48
    assert "modeb_corrective_full48_v1" in text
    assert "modeb_full30_corrective_contract.json" in text
    assert "§1–§48" in text or "1–§48" in text or "§48" in text
    # must place the retired file under legacy/
    assert "legacy/modeb_full20_corrective_contract_legacy_v97144.json" in text


if __name__ == "__main__":
    import sys
    rc = pytest.main([__file__, "-q"])
    sys.exit(rc)
