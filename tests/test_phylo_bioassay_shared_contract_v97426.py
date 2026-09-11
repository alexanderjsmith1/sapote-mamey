"""v9.7.426 red-first contracts for phylogeny and bioassay producers.

These fixtures are synthetic.  They prove producer/consumer state handling without
touching live BLAST jobs, private sequence stores, or external executables.
"""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def _load(name: str):
    path = TOOLS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_test_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _bioassay_csv(tmp_path: Path) -> Path:
    path = tmp_path / "recon.csv"
    fields = [
        "strain_id", "organism", "max_inhibition_raw", "screening_pattern",
        "host", "genus_16s",
    ]
    rows = [
        # One measured positive against MRSA. Candida was never tested.
        {"strain_id": "SYN-1", "organism": "MRSA", "max_inhibition_raw": "81",
         "screening_pattern": "STRONG_DOSE_CONSISTENT"},
        # One measured negative against Candida. MRSA was never tested.
        {"strain_id": "SYN-2", "organism": "Candida albicans", "max_inhibition_raw": "4",
         "screening_pattern": "NO_50PCT_OBSERVATION"},
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_af_dossier_preserves_not_tested_separately_from_measured_negative(tmp_path):
    tool = _load("bioassay_to_activity_channel")
    by_strain = {row["strain"]: row for row in tool.build_af_dossier(_bioassay_csv(tmp_path))}

    assert by_strain["SYN-1"]["anti_MRSA"] == "positive"
    assert by_strain["SYN-1"]["anti_Candida"] == "not_tested"
    assert by_strain["SYN-2"]["anti_Candida"] == "negative"
    assert by_strain["SYN-2"]["anti_MRSA"] == "not_tested"


def test_shared_reference_screen_matches_definition_and_fasta_header_forms(tmp_path):
    shared = _load("_phylo16s")
    place = _load("phylo_place")

    bad_definition = "Uncultured Streptomyces sp. clone SYN-ENV 16S ribosomal RNA gene"
    good_definition = "Streptomyces coelicolor strain SYN-T 16S ribosomal RNA gene"
    assert shared.reference_definition_hold(bad_definition)
    assert shared.reference_definition_hold(good_definition) is None

    ref = tmp_path / "ref.fasta"
    ref.write_text(
        ">AB000001.1 " + good_definition + "\n" + "ACGT" * 300 + "\n"
        ">AB000002.1 " + bad_definition + "\n" + "ACGT" * 300 + "\n"
    )
    rejected = place.screen_reference_definitions(str(ref))
    assert len(rejected) == 1
    assert "AB000002.1" in rejected[0][0]


def _build_ref_args(ref: Path, out: Path):
    return types.SimpleNamespace(
        ref_fasta=str(ref), group="moss", refpkg=str(out), approved_by="tester",
        add_outgroup="", outgroup_scope="genus", one_per_species=False,
        min_ref_len=0, threads=1, bootstrap=0,
    )


def test_build_ref_wires_screen_before_external_execution(tmp_path, monkeypatch):
    place = _load("phylo_place")
    ref = tmp_path / "ref.fasta"
    ref.write_text(
        ">AB000002.1 Uncultured Streptomyces sp. clone SYN-ENV\n" + "ACGT" * 300 + "\n"
    )
    monkeypatch.setattr(place, "_which", lambda *args: "/fake/tool")

    def never_run(*args, **kwargs):
        raise AssertionError("external tool ran before reference admission")

    for name in ("run", "call", "check_call", "Popen"):
        monkeypatch.setattr(place.subprocess, name, never_run, raising=False)
    try:
        place.cmd_build_ref(_build_ref_args(ref, tmp_path / "refpkg"))
    except SystemExit as exc:
        assert "REFERENCE_ADMISSION_UNCULTURED" in str(exc)
        assert "AB000002.1" in str(exc)
    else:  # pragma: no cover - makes an absent refusal explicit
        raise AssertionError("uncultured reference was admitted")


def test_build_ref_clean_reference_reaches_next_stage(tmp_path, monkeypatch):
    place = _load("phylo_place")
    ref = tmp_path / "ref.fasta"
    ref.write_text(
        ">AB000001.1 Streptomyces coelicolor strain SYN-T\n" + "ACGT" * 300 + "\n"
    )
    monkeypatch.setattr(place, "_which", lambda *args: "/fake/tool")
    reached = {}

    def stop_after_screen(*args, **kwargs):
        reached["external"] = True
        raise SystemExit("synthetic stop after admission")

    monkeypatch.setattr(place.subprocess, "call", stop_after_screen)
    try:
        place.cmd_build_ref(_build_ref_args(ref, tmp_path / "refpkg"))
    except SystemExit as exc:
        assert "REFERENCE_ADMISSION_UNCULTURED" not in str(exc)
    assert reached.get("external") is True


def test_autopilot_reference_builder_excludes_environmental_clone(tmp_path):
    autopilot = _load("phylo_autopilot")
    titles = (
        "A1\tMicromonospora echinospora strain SYN-T\n"
        "A2\tMicromonospora sp. clone SYN-ENV\n"
        "A3\tUncultured Micromonospora bacterium\n"
    )
    calls = {}

    def runner(cmd, capture_output=True, text=True):
        if "-entry" in cmd:
            return types.SimpleNamespace(stdout=titles, returncode=0, stderr="")
        calls["batch"] = Path(cmd[cmd.index("-entry_batch") + 1]).read_text().split()
        return types.SimpleNamespace(
            stdout=">A1 Micromonospora echinospora strain SYN-T\n" + "ACGT" * 300 + "\n",
            returncode=0,
            stderr="",
        )

    out = tmp_path / "ref.fasta"
    count = autopilot.build_reference_fasta(
        ["Micromonospora"], "DB", str(out), sentinels=(), outgroup=(), runner=runner
    )
    assert count == 1
    assert calls["batch"] == ["A1"]


def test_gtotree_figure_consumer_accepts_typed_bioassay_track(tmp_path):
    overlay = _load("tree_bgc_overlay")
    matrix = tmp_path / "annotations.tsv"
    matrix.write_text(
        "strain\tchannel\tfeature\tvalue\tstate\n"
        "SYN-1\tBIOASSAY\tanti_MRSA\t1\tOBSERVED\n"
        "SYN-2\tBIOASSAY\tanti_MRSA\t0\tOBSERVED\n"
        "SYN-2\tBIOASSAY\tanti_Candida\t\tNOT_MEASURED\n"
    )
    rows, columns = overlay._load_annotations(matrix, {"SYN-1", "SYN-2"})
    assert ("BIOASSAY", "anti_MRSA") in columns
    by_feature = {(r["strain"], r["feature"]): r for r in rows}
    assert by_feature[("SYN-2", "anti_MRSA")]["value"] == 0.0
    assert by_feature[("SYN-2", "anti_Candida")]["state"] == "NOT_MEASURED"
