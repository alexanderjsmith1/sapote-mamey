"""Complete-locus ranking joins and explicit holds; synthetic evidence only."""
import csv
import json

import pytest

from mamey.exact_identity import ExactLocusIdentityError
from mamey.figures_smoke import _ranking_rows, generate


def row(contig="SYNTHETIC.1", region="region001", alias="BGC001", **extra):
    return {"Contig": contig, "Node_ID": contig, "antiSMASH_Region": region,
            "BGC_ID": alias, **extra}


def test_shared_alias_on_distinct_loci_keeps_exact_lengths():
    inventory = [row(Length_kb="10"), row("SYNTHETIC.2", Length_kb="30")]
    rows = _ranking_rows([row("SYNTHETIC.2"), row()], inventory, "SYNTHETIC_STRAIN")
    assert [r["length"] for r in rows] == [30, 10]
    assert rows[0]["exact_locus"] == "SYNTHETIC_STRAIN / SYNTHETIC.2 / region001 / BGC001"


@pytest.mark.parametrize("triage,inventory,strain", [
    ([{"BGC_ID": "BGC001"}], [row(Length_kb="10")], "SYNTHETIC_STRAIN"),
    ([row("SYNTHETIC.2")], [row(Length_kb="10")], "SYNTHETIC_STRAIN"),
    ([row()], [row(), row()], "SYNTHETIC_STRAIN"),
    ([row(), row()], [row()], "SYNTHETIC_STRAIN"),
    ([row(Node_ID="OTHER.1")], [], "SYNTHETIC_STRAIN"),
    ([row(strain_id="OTHER_STRAIN")], [], "SYNTHETIC_STRAIN"),
    ([row(Length_kb="11")], [row(Length_kb="10")], "SYNTHETIC_STRAIN"),
    ([row(Boundary="Edge")], [row(Boundary="Interior")], "SYNTHETIC_STRAIN"),
    ([row()], [], None),
    ([row("NODE_1")], [], "SYNTHETIC_STRAIN"),
])
def test_incomplete_duplicate_or_conflicting_identity_holds(triage, inventory, strain):
    with pytest.raises(ExactLocusIdentityError):
        _ranking_rows(triage, inventory, strain)


def write_package(tmp_path, data, *, manifest=True):
    pkg = tmp_path / "package"
    pkg.mkdir()
    if manifest:
        (pkg / "manifest.json").write_text(json.dumps({"strain_id": "SYNTHETIC_STRAIN"}))
    with (pkg / "synthetic_2_inventory.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data))
        writer.writeheader()
        writer.writerow(data)
    return pkg


def test_missing_manifest_reports_hold_while_aggregate_plot_remains(tmp_path):
    pytest.importorskip("matplotlib")
    pkg = write_package(tmp_path, row(Length_kb="10", Products="terpene", Boundary="Interior"),
                        manifest=False)
    result = generate(pkg)
    assert result["identity_holds"] == ["fig_bgc_ranking: HOLD_IDENTITY_UNRESOLVED"]
    assert "fig_bgc_ranking.png" not in result["files"]
    assert "fig_assembly_tier.png" in result["files"]
    assert "[HOLD] fig_bgc_ranking" in (pkg / "issue_log.md").read_text()


def test_render_sidecar_preserves_full_identity(tmp_path):
    pytest.importorskip("matplotlib")
    contig = "NODE_12_length_987654_cov_12.34"
    # Current native producer normalizes the node key at the first period;
    # display must retain the separate complete physical Contig field.
    pkg = write_package(tmp_path, row(contig, Node_ID="NODE_12_length_987654_cov_12",
                                     Length_kb="10", Boundary="Edge"))
    result = generate(pkg)
    assert result["identity_holds"] == []
    with (pkg / "smoke_figures/fig_bgc_ranking_data.csv").open() as handle:
        data = list(csv.DictReader(handle))
    assert data[0]["exact_locus"] == f"SYNTHETIC_STRAIN / {contig} / region001 / BGC001"
    assert (pkg / "smoke_figures/fig_bgc_ranking.png").read_bytes().startswith(b"\x89PNG")
