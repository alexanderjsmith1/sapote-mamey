"""Generic layout fixtures; no authored scientific or profile-quality acceptance."""
from pathlib import Path
import pytest
import yaml
from mamey import sapote_markdown as md
from mamey import document_factory as factory
from mamey.mode_b_receipt import _resolve_card_contract
from mamey.modeb_current50_v2 import header_line, load_contract as load_named
from mamey.modeb_structure_gate import load_contract as load_default

IDENTITY = "AS-UNIT / unit_contig_length_10000 / region001 / BGC001"


def body(contract="full48", header="", *, drop=None, duplicate=None):
    spec = load_named(contract) or load_default()
    parts = [header, "# Mode B — " + IDENTITY]
    for section in spec["sections"]:
        n = int(section["number"])
        if n == drop:
            continue
        text = f"## §{n} {section['title']}\n\nGeneric layout fixture; no evidence evaluated.\n"
        parts.append(text)
        if n == duplicate:
            parts.append(text)
    return "\n\n".join(parts)


def governed(content):
    meta = {
        "schema_version": "sapote-markdown-1.0", "document_type": "mode_b_card",
        "title": "Generic card", "audience": "Unit fixture", "authority": "Unadopted test",
        "render_profile": "mode_b_card", "claim_safety_footer": "Layout fixture; no scientific acceptance.",
        "exact_locus": {"strain": "AS-UNIT", "node_or_contig": "unit_contig_length_10000",
                        "region": "region001", "bgc_alias": "BGC001"},
    }
    return "---\n" + yaml.safe_dump(meta, sort_keys=False) + "---\n\n" + content


@pytest.mark.parametrize("marker", ["current50_v2", "modeb_current50_v2"])
def test_existing_v2_named_contract_passes_its_fifty_section_layout(marker):
    header = f"<!-- MODE B TEMPLATE | contract: {marker} -->"
    assert _resolve_card_contract(header)[0] == "current50_v2"
    model = md.parse_text(governed(body("current50_v2", header)))
    assert len(list(md.iter_modeb_sections(model))) == 50
    assert md.validate_model(model).ok


def test_real_v2_emitter_header_passes_without_new_profile_heuristics():
    header = header_line("AS-UNIT", "unit_contig_length_10000", "region001", "BGC001")
    assert "profile: FINISHED_FULL50_CURRENT50_V2" in header
    model = md.parse_text(governed(body("current50_v2", header)))
    assert md.validate_model(model).ok
    assert any(header in b.data.get("text", "") for b in model.blocks)
    assert model.to_dict()["source_sha256"] == model.source_sha256


def test_v2_header_cannot_silently_accept_only_the_default_forty_eight_sections():
    header = "<!-- MODE B | contract: current50_v2 -->"
    with pytest.raises(md.SapoteMarkdownError, match="MODEB_SECTIONS_1_50_REQUIRED"):
        md.parse_text(governed(body("full48", header)))


@pytest.mark.parametrize("header", [
    "", "<!-- MODE B | contract: full48 -->", "<!-- MODE B | contract: unrecognized_future_profile -->",
    "<!-- MODE B | profile: FINISHED_FULL50_CURRENT50_V2 -->",
])
def test_default_and_unrecognized_marker_behavior_matches_existing_resolver(header):
    assert _resolve_card_contract(header)[0] == "full48"
    assert md.validate_model(md.parse_text(governed(body(header=header)))).ok
    with pytest.raises(md.SapoteMarkdownError, match="MODEB_SECTIONS_1_48_REQUIRED"):
        md.parse_text(governed(body("current50_v2", header)))


@pytest.mark.parametrize("contract,n", [("full48", 48), ("current50_v2", 50)])
def test_named_contract_still_rejects_missing_or_duplicate_sections(contract, n):
    header = f"<!-- MODE B | contract: {contract} -->"
    for args in [{"drop": 2}, {"duplicate": 2}]:
        with pytest.raises(md.SapoteMarkdownError, match=f"MODEB_SECTIONS_1_{n}_REQUIRED"):
            md.parse_text(governed(body(contract, header, **args)))


def test_conflicting_explicit_markers_keep_existing_resolver_conflict_error():
    header = "<!-- MODE B | contract: full48 -->\n\n<!-- MODE B | contract: current50_v2 -->"
    assert _resolve_card_contract(header)[3][0]["code"] == "CARD_CONTRACT_CONFLICT"
    with pytest.raises(md.SapoteMarkdownError, match="CARD_CONTRACT_CONFLICT"):
        md.parse_text(governed(body(header=header)))


def test_validator_calls_existing_resolver_with_retained_header(monkeypatch):
    from mamey import mode_b_receipt as receipt
    original = receipt._resolve_card_contract
    calls = []
    def spy(content, requested=None):
        calls.append((content, requested))
        return original(content, requested)
    monkeypatch.setattr(receipt, "_resolve_card_contract", spy)
    header = "<!-- MODE B | contract: full48 -->"
    md.parse_text(governed(body(header=header)))
    assert calls and header in calls[0][0] and calls[0][1] is None


def test_resolver_load_failure_is_a_validation_error(monkeypatch):
    from mamey import mode_b_receipt as receipt
    def unavailable(*args, **kwargs):
        raise ValueError("unit contract unavailable")
    monkeypatch.setattr(receipt, "_resolve_card_contract", unavailable)
    with pytest.raises(md.SapoteMarkdownError, match="MODEB_CONTRACT_INVALID.*unit contract unavailable"):
        md.parse_text(governed(body()))


def project(tmp_path, content):
    source = tmp_path / "unit_card.md"
    source.write_text(content)
    p = tmp_path / "unit_project.yml"
    p.write_text(yaml.safe_dump({
        "schema_version": factory.PROJECT_SCHEMA_VERSION,
        "defaults": {"audience": "Unit fixture", "authority": "Unadopted test",
                     "claim_safety_footer": "Layout fixture; no scientific acceptance."},
        "documents": [{"id": "unit", "document_type": "mode_b_card", "source": source.name,
                       "title": "Generic card", "exact_locus": {
                           "strain": "AS-UNIT", "node_or_contig": "unit_contig_length_10000",
                           "region": "region001", "bgc_alias": "BGC001"}}],
    }, sort_keys=False))
    return p


@pytest.mark.parametrize("contract", ["full48", "current50_v2"])
def test_actual_factory_check_normalizes_profile_without_rendering(tmp_path, monkeypatch, contract):
    def forbidden(*args, **kwargs):
        pytest.fail("Factory check must not invoke a renderer")
    monkeypatch.setattr(factory, "export_document", forbidden)
    header = f"<!-- MODE B | contract: {contract} -->"
    p = project(tmp_path, body(contract, header))
    before = {q.name: q.read_bytes() for q in tmp_path.iterdir() if q.is_file()}
    result = factory.check_project(p)
    assert result["status"] == "PASS" and result["document_count"] == 1
    assert set(result["normalized_sha256"]) == {"unit"}
    assert before == {q.name: q.read_bytes() for q in tmp_path.iterdir() if q.is_file()}
    assert not (tmp_path / "rendered_documents").exists()


def test_actual_factory_check_rejects_contract_conflict(tmp_path):
    header = "<!-- MODE B | contract: full48 -->\n\n<!-- MODE B | contract: current50_v2 -->"
    with pytest.raises(md.SapoteMarkdownError, match="CARD_CONTRACT_CONFLICT"):
        factory.check_project(project(tmp_path, body(header=header)))
