"""Focused canonical-glossary ownership and contract guards."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "docs" / "GLOSSARY.md"
POINTER = ROOT / "docs" / "GUIDE" / "04_Glossary.md"
LEGACY = (
    ROOT / "docs" / "user_guides" / "comprehensive_glossary.md",
    ROOT / "docs" / "user_guides" / "sapote_mamey_wheel_glossary.md",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_one_canonical_glossary_and_pointer_only():
    canonical = _text(CANONICAL)
    pointer = _text(POINTER)
    assert canonical.startswith("<!-- CANONICAL GLOSSARY -->")
    assert pointer.startswith("<!-- POINTER — NOT CANONICAL -->")
    assert "../GLOSSARY.md" in pointer
    assert len(pointer.splitlines()) <= 20, "guide pointer must not grow into a second glossary"
    assert not re.search(r"^## (Core concepts|BGC classes|Scan names)", pointer, re.MULTILINE)


def test_legacy_glossary_sources_are_explicitly_superseded():
    for path in LEGACY:
        text = _text(path)
        assert text.startswith("<!-- SUPERSEDED GLOSSARY SOURCE — NOT CANONICAL -->")
        assert "../GLOSSARY.md" in text
        assert "Do not extend" in text


def test_canonical_glossary_covers_current_identity_evidence_and_authority_terms():
    text = _text(CANONICAL)
    required = (
        "strain / full node-or-contig / region / BGC alias",
        "Source object",
        "evidence://root-id/path",
        "DISCOVERED_NOT_ADMITTED",
        "AVAILABLE_UNINGESTED",
        "NCBI ClusteredNR",
        "local Swiss-Prot",
        "Gene-first / sequence-first review",
        "`document_state` / `evidence_state`",
        "Privacy profile",
        "Release/archive transaction states",
        "Post-seal tool",
        "Mechanical gate / authority ceiling",
        "§1–§48",
        "fragmentation_tier",
    )
    missing = [term for term in required if term not in text]
    assert not missing, f"canonical glossary missing contract terms: {missing}"


def test_canonical_glossary_does_not_present_known_stale_snapshots_as_current():
    text = _text(CANONICAL)
    stale = (
        "§1–§8",
        "88-marker evidence library",
        "The 14 T43 diagnostic triggers",
        "canonical count 12",
        "Full compound-level claims",
        "HIGH / MEDIUM / LOW / DEPRIORITIZED",
        "KCB ≥ 15,000",
        "current to v9.7.100",
    )
    found = [term for term in stale if term in text]
    assert not found, f"canonical glossary retains stale current-state claims: {found}"


def test_glossary_cross_document_links_resolve():
    for source in (POINTER, *LEGACY):
        text = _text(source)
        for target in re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", text):
            if "://" in target or target.startswith("mailto:"):
                continue
            assert (source.parent / target).resolve().exists(), f"dead link in {source}: {target}"


def test_historical_documentation_protocol_routes_terms_to_canonical_glossary():
    protocol = _text(ROOT / "docs" / "user_guides" / "cross_chat_doc_protocol.md")
    assert "SUPERSEDED ROUTING NOTICE" in protocol
    assert "A new or corrected reader-facing term | `../GLOSSARY.md`" in protocol
    assert "do not update the superseded wheel snapshot" in protocol
