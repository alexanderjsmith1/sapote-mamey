"""v9.7.383 — the external-tool inventory must ship, and must be fully resolved.

The bundle previously shipped only the INTERNAL script catalog
(docs/TOOLS_INVENTORY.generated.md); the EXTERNAL tool stack (antiSMASH, BiG-SCAPE,
IQ-TREE, GToTree, BLAST+, SPAdes + versions/citations) was a workspace-only file, so a
GitHub user / methods reviewer got no external-tool record. This suite pins:

- docs/EXTERNAL_TOOL_INVENTORY.md SHIPS;
- it carries NO unresolved `VERIFY` token (a fail-closed gate — a half-resolved methods
  table is worse than none, so the cut must not ship one);
- it actually names the core external tools + the DB releases it claims to document;
- the generated internal catalog points at it (kills the name-confusion).
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "EXTERNAL_TOOL_INVENTORY.md"


def test_external_inventory_ships():
    assert DOC.is_file(), "docs/EXTERNAL_TOOL_INVENTORY.md must ship in the bundle"


def test_no_unresolved_verify_token():
    body = DOC.read_text(encoding="utf-8")
    # the scaffold marker is the bare uppercase token; 'verified'/'Verified' are fine
    assert "VERIFY" not in body, (
        "EXTERNAL_TOOL_INVENTORY.md still carries an unresolved VERIFY cell — "
        "resolve it (or mark it rolling/remote) before the cut"
    )


def test_names_the_core_external_tools_and_db_releases():
    body = DOC.read_text(encoding="utf-8")
    for tool in ("antiSMASH", "BiG-SCAPE", "pyhmmer", "Pfam", "BLAST+", "GToTree", "IQ-TREE"):
        assert tool in body, f"external inventory must name {tool}"
    # verified releases the tool-master closed, so a future edit can't quietly drop them
    for release in ("8.0.4", "0.12.1", "38.2", "4.0"):
        assert release in body, f"external inventory must record release {release}"


def test_generated_catalog_points_at_external_inventory():
    gen = (ROOT / "docs" / "TOOLS_INVENTORY.generated.md").read_text(encoding="utf-8")
    assert "EXTERNAL_TOOL_INVENTORY.md" in gen, (
        "the generated internal catalog must point readers at the external inventory"
    )
