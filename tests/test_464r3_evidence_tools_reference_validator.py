"""Reference-BGC validator: a truncated manifest row is refused, and strain is declared, not bound."""
from types import SimpleNamespace
import pytest
from tests.test_reference_bgc_structural_validator_v97390 import _load_tool

HEADER = ["source_zip", "source_zip_sha256", "compound", "accession", "strain", "full_contig",
          "region", "bgc_alias", "evidence_citation"]


def test_truncated_row_missing_citation_is_refused(tmp_path):
    tool = _load_tool()
    manifest = tmp_path / "m.tsv"
    cells = ["reference.zip", "0" * 64, "compound-X", "ACC0001", "Example strain", "CTG_A",
             "region001", "BGC001"]  # citation cell absent
    manifest.write_text("\t".join(HEADER) + "\n" + "\t".join(cells) + "\n")
    with pytest.raises(tool.ManifestError, match="truncated row"):
        tool.load_reference_manifest(manifest)


def test_extra_cells_are_refused(tmp_path):
    tool = _load_tool()
    manifest = tmp_path / "m.tsv"
    cells = ["reference.zip", "0" * 64, "c", "A", "s", "CTG_A", "region001", "BGC001", "cite", "extra"]
    manifest.write_text("\t".join(HEADER) + "\n" + "\t".join(cells) + "\n")
    with pytest.raises(tool.ManifestError, match="more cells"):
        tool.load_reference_manifest(manifest)


def _spec(tool):
    return tool.ReferenceSpec(source_zip="r.zip", source_zip_sha256="0" * 64, compound="c", accession="A",
                              strain="Example strain", full_contig="CTG_A", region="region001",
                              bgc_alias="BGC001", evidence_citation="cite")


def test_parsed_strain_that_differs_does_not_select():
    tool = _load_tool()
    other = SimpleNamespace(bgc_id="BGC001", contig="CTG_A", node_id="CTG_A", antismash_region="region001",
                            region_number=1, strain="Different strain")
    with pytest.raises(tool.ManifestError, match="matched 0 records"):
        tool.select_exact_bgc(_spec(tool), [other])


def test_strain_without_parsed_source_is_labelled_declared():
    tool = _load_tool()
    bgc = SimpleNamespace(bgc_id="BGC001", contig="CTG_A", node_id="CTG_A", antismash_region="region001",
                          region_number=1)
    assert tool.select_exact_bgc(_spec(tool), [bgc]) is bgc
    assert tool.strain_binding_state(bgc) == "CURATOR_DECLARED_NOT_SOURCE_BOUND"
    assert "strain_binding_state" in tool.OUTPUT_FIELDS
