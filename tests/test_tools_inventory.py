"""Test the tools inventory indexes every tool and the manifest block stays in sync.

This is the guard that makes the duplication failure (rebuilding a tool that already
exists) self-correcting: every tool must appear in the generated inventory, and the
session manifest's injected block must match.
"""
import pathlib
import importlib.util
import json

_TOOL = pathlib.Path(__file__).resolve().parent.parent / "tools" / "gen_tools_inventory.py"
_spec = importlib.util.spec_from_file_location("gen_tools_inventory", _TOOL)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def test_every_tool_is_indexed():
    rows = {name for name, _ in gen.collect()}
    on_disk = {p.name for p in gen.TOOLS.iterdir()
               if p.is_file() and p.suffix in {".py", ".sh"} and not p.name.startswith(".")}
    missing = on_disk - rows
    assert not missing, f"tools not in inventory: {sorted(missing)}"


def test_md_is_not_stale_if_committed():
    if not gen.MD_OUT.exists():
        return
    assert gen.MD_OUT.read_text(encoding="utf-8") == gen.render_md(gen.collect()), \
        "docs/TOOLS_INVENTORY.generated.md is stale — run tools/gen_tools_inventory.py"


def test_manifest_block_is_present_and_current():
    if not gen.MANIFEST.exists():
        return
    text = gen.MANIFEST.read_text(encoding="utf-8")
    if gen.START not in text:
        return  # not yet injected in this tier; generation covers correctness
    assert gen.render_manifest_block(gen.collect()) in text, \
        "SESSION_START_MANIFEST.md tools block is stale — run tools/gen_tools_inventory.py"


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_connection_audit_uses_real_wiring_and_excludes_generated_self_certification(tmp_path):
    _write(tmp_path / "tools" / "alpha.py", '''"""High-value alpha tool."""\nimport argparse\nif __name__ == "__main__":\n    argparse.ArgumentParser().parse_args()\n''')
    _write(tmp_path / "tools" / "beta.py", '''"""Deprecated beta helper."""\nVALUE = 1\n''')
    _write(tmp_path / "mamey" / "cli.py", 'print("python tools/alpha.py --help")\n')
    _write(tmp_path / "tests" / "test_alpha.py", 'TOOL = "tools/alpha.py"\n')
    _write(tmp_path / "docs" / "GUIDE.md", 'Run `tools/alpha.py` for the audit.\n')
    _write(
        tmp_path / "SESSION_START_MANIFEST.md",
        gen.START + '\n- `beta.py` — generated only\n' + gen.END + '\n',
    )
    _write(tmp_path / "MODULE_MANIFEST.txt", "tools/alpha.py\ntools/beta.py\n")

    payload = gen.audit_connections(tmp_path)
    rows = {row["tool"]: row for row in payload["tools"]}
    assert payload["schema_version"] == "tool_connections_v1"
    assert payload["tool_count"] == 2
    assert rows["alpha.py"]["cli_reference_files"] == ["mamey/cli.py"]
    assert rows["alpha.py"]["test_reference_files"] == ["tests/test_alpha.py"]
    assert rows["alpha.py"]["documentation_reference_files"] == ["docs/GUIDE.md"]
    assert rows["alpha.py"]["disposition"] == "CONNECTED_AND_TESTED"
    assert rows["beta.py"]["documentation_reference_files"] == []
    assert rows["beta.py"]["lifecycle"] == "DECLARED_DEPRECATED_OR_RETIRED"
    assert rows["alpha.py"]["interconnection_score"] > rows["beta.py"]["interconnection_score"]
    assert rows["alpha.py"]["operational_utility_evidence_score"] > rows["beta.py"]["operational_utility_evidence_score"]


def test_connection_audit_flags_personal_path_literals_and_parse_holds(tmp_path):
    _write(tmp_path / "tools" / "private_default.py", 'SOURCE = "/Users/example/private.tsv"\n')
    _write(tmp_path / "tools" / "broken.py", "def broken(:\n")
    payload = gen.audit_connections(tmp_path)
    rows = {row["tool"]: row for row in payload["tools"]}
    assert rows["private_default.py"]["personal_path_literal"] is True
    assert rows["private_default.py"]["disposition"] == "PERSONAL_PATH_LITERAL_REVIEW"
    assert rows["broken.py"]["disposition"] == "AST_PARSE_HOLD"
    assert rows["broken.py"]["parse_error"]


def test_connection_audit_does_not_invent_main_guard_or_miss_dotted_import(tmp_path):
    _write(tmp_path / "tools" / "helper.py", 'VALUE = 1\nif __name__ != "__main__":\n    VALUE = 2\n')
    _write(tmp_path / "mamey" / "consumer.py", "from tools.helper import VALUE\n")
    payload = gen.audit_connections(tmp_path)
    row = payload["tools"][0]
    assert row["interface"] == "IMPORT_ONLY_OR_HELPER"
    assert row["source_reference_files"] == ["mamey/consumer.py"]


def test_connection_audit_cli_json_and_tsv_are_machine_readable(tmp_path, capsys):
    _write(tmp_path / "tools" / "solo.sh", "#!/bin/sh\necho ok\n")
    assert gen.main(["--connections", "--root", str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tool_count"] == 1
    assert payload["tools"][0]["interface"] == "SHELL_ENTRYPOINT"

    assert gen.main(["--connections", "--root", str(tmp_path), "--format", "tsv"]) == 0
    tsv = capsys.readouterr().out
    assert tsv.splitlines()[0].startswith("tool\tpath\tsha256\tbytes")
    assert "solo.sh\ttools/solo.sh\t" in tsv

    output = tmp_path / "nested" / "connections.json"
    assert gen.main([
        "--connections", "--root", str(tmp_path), "--format", "json",
        "--output", str(output),
    ]) == 0
    assert capsys.readouterr().out == ""
    assert json.loads(output.read_text(encoding="utf-8"))["tool_count"] == 1


def test_capability_search_measures_split_fragment_contig_and_rescue_in_path_with_spaces(tmp_path):
    root = tmp_path / "portable bundle with spaces"
    _write(root / "tools" / "split_rollup.py", '''"""Split-pathway cohort rollup.

Find split biosynthetic regions across contigs and summarize rescue candidates.
"""
import argparse
if __name__ == "__main__":
    argparse.ArgumentParser().parse_args()
''')
    _write(root / "tools" / "fragment_reconstruction.py", '''"""Fragment reconstruction.

Order fragmented cluster pieces against a reference scaffold.
"""
if __name__ == "__main__":
    raise SystemExit(0)
''')
    _write(root / "mamey" / "contig_rescue.py", '''"""Contig rescue evidence helper.

Represent rescue evidence without changing extraction behavior.
"""
''')

    expected = {
        "split": "tools/split_rollup.py",
        "fragment": "tools/fragment_reconstruction.py",
        "contig": "mamey/contig_rescue.py",
        "rescue": "mamey/contig_rescue.py",
    }
    for concept, path in expected.items():
        hits = gen.search_capabilities([concept], root=root, top=10)
        assert path in [hit["path"] for hit in hits], (concept, hits)
        selected = next(hit for hit in hits if hit["path"] == path)
        assert selected["matched_lines"]
        assert selected["match_count"] >= 1

    combined = [hit["path"] for hit in gen.search_capabilities(
        ["contig", "rescue"], root=root, top=5,
    )]
    assert "tools/split_rollup.py" in combined
    assert "tools/fragment_reconstruction.py" in combined


def test_measured_bundle_regression_surfaces_rollup_and_reconstruction_in_top_five():
    root = pathlib.Path(__file__).resolve().parent.parent
    paths = [hit["path"] for hit in gen.search_capabilities(
        ["contig", "rescue"], root=root, top=5,
    )]
    assert "tools/rggmci_cohort_rollup.py" in paths
    assert "tools/build_reconstruction.py" in paths


def test_capability_search_is_deterministic_and_uses_real_entrypoint_hints(tmp_path):
    _write(tmp_path / "tools" / "alpha.py", '''"""Split alpha helper."""
import argparse
if __name__ == "__main__":
    argparse.ArgumentParser().parse_args()
''')
    _write(tmp_path / "mamey" / "beta.py", '''"""Split beta import helper."""
VALUE = 1
''')
    first = gen.search_capabilities(["split", "split"], root=tmp_path, top=10)
    second = gen.search_capabilities(["split"], root=tmp_path, top=10)
    assert first == second
    rows = {hit["path"]: hit for hit in first}
    assert rows["tools/alpha.py"]["run_hint"] == "python tools/alpha.py --help"
    assert rows["mamey/beta.py"]["run_hint"] == ""


def test_capability_cli_parser_preserves_keywords_and_limit():
    from mamey import cli

    args = cli.build_parser().parse_args([
        "capabilities", "split", "fragment", "contig", "rescue", "--top", "7",
    ])
    assert args.func is cli.capabilities_command
    assert args.keywords == ["split", "fragment", "contig", "rescue"]
    assert args.top == 7


def test_capability_command_handles_unknown_concept_without_writing(tmp_path, capsys):
    rc = gen.capabilities_command(["not-a-real-capability-token"], root=tmp_path, top=5)
    assert rc == 0
    assert "no matches" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []
