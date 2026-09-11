import importlib.util, json
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("catalog", ROOT / "tools/phylo_neighborhood_catalog.py")
catalog = importlib.util.module_from_spec(spec); spec.loader.exec_module(catalog)

def test_build_groups_prefers_owner_and_falls_back_to_inferred(tmp_path):
    required = tmp_path / "required.tsv"
    required.write_text("strain\treference_species\nAS-1\tStreptomyces alpha\n")
    near = tmp_path / "near.tsv"
    near.write_text("as_query\tnearest_type_strain\tpatristic_dist\nAS-1_x\tStreptomyces wrong NR 1\t0.1\nAS-2_x\tStreptomyces beta NR 2\t0.2\n")
    placements = [{"p":[[1,0,1,0,0]],"n":["AS_1_x"]},{"p":[[2,0,1,0,0]],"n":["AS_2_x"]}]
    groups, ledger = catalog.build_groups(required, near, placements)
    assert sorted(groups) == ["Streptomyces alpha", "Streptomyces beta"]
    assert [r["grouping_authority"] for r in ledger] == ["owner_closest_type", "inferred_nearest_reference"]

def test_main_filters_jplace_without_changing_reference_tree(tmp_path):
    run = tmp_path / "run"; (run/"place").mkdir(parents=True); (run/"report").mkdir(); (run/"refpkg").mkdir()
    payload={"tree":"(A:1,B:1){0};","placements":[{"p":[[1,0,1,0,0]],"n":["AS_1_x"]}],"metadata":{},"version":3,"fields":["edge_num","likelihood","like_weight_ratio","distal_length","pendant_length"]}
    (run/"place/epa_result.jplace").write_text(json.dumps(payload)); (run/"refpkg/ref.tree").write_text("(A:1,B:1);")
    (run/"report/streptomyces_neighborhoods.tsv").write_text("as_query\tnearest_type_strain\tpatristic_dist\nAS-1_x\tStreptomyces alpha NR 1\t0.1\n")
    required=tmp_path/"required.tsv"; required.write_text("strain\treference_species\nAS-1\tStreptomyces alpha\n")
    out=tmp_path/"out"
    assert catalog.main([str(run),"--required-reference-table",str(required),"--out",str(out)]) == 0
    sub=json.loads(next(out.glob("*/place/epa_result.jplace")).read_text())
    assert sub["tree"] == payload["tree"] and len(sub["placements"]) == 1
    assert json.loads((out/"BUILD_RECEIPT.json").read_text())["grouping_changes_inference"] is False
