"""Missing replay inputs must remain visible and source drift must not receive a success receipt."""
import hashlib
from contextlib import contextmanager
import csv
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pcoa_replay_metadata", ROOT / "tools/protein_pcoa_render.py")
ppr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ppr)


@pytest.fixture
def replay(tmp_path, monkeypatch):
    directory = tmp_path / "kit/out_KS"
    directory.mkdir(parents=True)
    (directory / "PCOA_KS.tsv").write_text(
        "id\tPC1\tPC2\tn_represented\tsource\tstrain\tlocus_tag\torigin\n"
        "r1\t0\t0\t1\treference\tRef\tr1\tRef.region001.gbk\n"
        "r2\t1\t1\t1\treference\tRef\tr2\tRef.region002.gbk\n"
        "i1\t2\t2\t1\tisolate\tAS-900\ti1\tAS-900__N1.region001.gbk\n")
    (directory / "NEAREST_KS.tsv").write_text("id\tnearest_pident\ni1\t60\n")
    (tmp_path / "cohorts.tsv").write_text("strain\tcohort\nAS-900\tgroup_a\n")
    captured = []
    def render(spec, prefix):
        captured.append(spec)
        for extension in ["pdf", "png", "svg"]:
            Path(f"{prefix}.{extension}").write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>KS</text></svg>')
    monkeypatch.setattr(ppr, "render_matplotlib", render)
    args = ["--kit", str(tmp_path / "kit"), "--out", str(tmp_path / "output"),
            "--cohort-table", str(tmp_path / "cohorts.tsv"), "--panel", "demo=group_a", "--renderer", "matplotlib"]
    return tmp_path, directory, args, captured


def test_unknown_axis_percentages_are_omitted_and_recorded(replay):
    root, directory, args, captured = replay
    assert ppr.main(args) == 0
    assert captured[0]["xlab"] == "PCoA 1" and captured[0]["ylab"] == "PCoA 2"
    receipt = json.loads((root / "output/render_receipt.json").read_text())
    assert receipt["panels"][0]["axis_metadata"] == {"state": "NOT_PROVIDED", "pct_axes": None}
    assert next(x for x in receipt["inputs"] if x["path"].endswith("RUN_KS.json"))["state"] == "NOT_PROVIDED"


def test_publication_option_refuses_missing_metadata_before_any_draw(replay):
    root, directory, args, captured = replay
    assert ppr.main([*args, "--require-axis-metadata"]) == 2
    assert not captured and not (root / "output/render_receipt.json").exists()


@pytest.mark.parametrize("values", [[], [1], [True, 2], [float("nan"), 2], [1, float("inf")], "30,20", ["bad", 2], [None, 2]])
def test_invalid_metadata_never_generates_a_figure(replay, values):
    root, directory, args, captured = replay
    (directory / "RUN_KS.json").write_text(json.dumps({"pct_axes": values}))
    assert ppr.main(args) == 2
    assert not captured and not (root / "output/render_receipt.json").exists()


def test_supplied_percentages_unchanged_and_input_output_bytes_bound(replay):
    root, directory, args, captured = replay
    (directory / "RUN_KS.json").write_text(json.dumps({"pct_axes": [30.0, 20.0, 10.0]}))
    assert ppr.main([*args, "--require-axis-metadata"]) == 0
    assert captured[0]["xlab"] == "PCoA 1 (30.0%)" and captured[0]["ylab"] == "PCoA 2 (20.0%)"
    receipt = json.loads((root / "output/render_receipt.json").read_text())
    for record in receipt["inputs"] + receipt["outputs"] + receipt["producers"]:
        assert record["sha256"] == hashlib.sha256(Path(record["path"]).read_bytes()).hexdigest()


@pytest.mark.parametrize("change", ["coordinates", "create_optional_metadata"])
def test_input_drift_retains_attempt_without_success_receipt(replay, monkeypatch, change):
    root, directory, args, captured = replay
    original = ppr.render_matplotlib
    def mutate(spec, prefix):
        original(spec, prefix)
        if change == "coordinates":
            with (directory / "PCOA_KS.tsv").open("a") as stream:
                stream.write("changed\n")
        else:
            (directory / "RUN_KS.json").write_text('{"pct_axes":[30,20]}')
    monkeypatch.setattr(ppr, "render_matplotlib", mutate)
    assert ppr.main(args) == 2
    assert (root / "output/PCOA_KS_demo.svg").exists()
    assert not (root / "output/render_receipt.json").exists()


def test_later_set_metadata_failure_is_preflighted_before_first_draw(replay):
    root, directory, args, captured = replay
    (directory / "RUN_KS.json").write_text('{"pct_axes":[30,20]}')
    other = directory.parent / "out_ZZZ"
    other.mkdir()
    (other / "PCOA_ZZZ.tsv").write_bytes((directory / "PCOA_KS.tsv").read_bytes())
    assert ppr.main([*args, "--require-axis-metadata"]) == 2
    assert not captured


def substitute_second_read(monkeypatch, target, replacement):
    """Restore a valid changed file before any later drift guard sees its path."""
    previous = target.read_bytes()
    original_open = Path.open
    state = {"reads": 0, "substituted": False}
    @contextmanager
    def replacement_stream(args, kwargs):
        target.write_bytes(replacement)
        try:
            with original_open(target, *args, **kwargs) as stream:
                yield stream
        finally:
            target.write_bytes(previous)
    def guarded_open(path, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        if path == target and "r" in mode:
            state["reads"] += 1
            if state["reads"] == 2:
                state["substituted"] = True
                return replacement_stream(args, kwargs)
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guarded_open)
    return state, previous


@pytest.mark.parametrize("kind", ["coordinates", "nearest", "run", "cohorts", "set_names", "drop_origins"])
def test_replace_parse_restore_refused_before_any_draw(replay, monkeypatch, kind):
    root, directory, args, captured = replay
    if kind == "coordinates":
        target = directory / "PCOA_KS.tsv"
        replacement = target.read_bytes().replace(b"i1\t2\t2", b"i1\t9\t2")
    elif kind == "nearest":
        target = directory / "NEAREST_KS.tsv"
        replacement = b"id\tnearest_pident\ni1\t90\n"
    elif kind == "run":
        target = directory / "RUN_KS.json"
        target.write_text('{"pct_axes":[30,20]}')
        replacement = b'{"pct_axes":[44,33]}'
    elif kind == "cohorts":
        target = root / "cohorts.tsv"
        replacement = b"strain\tcohort\nAS-900\tgroup_b\n"
    elif kind == "set_names":
        target = root / "names.tsv"
        target.write_text("set\ttitle\ttag\nKS\tOriginal title\tKS\n")
        replacement = b"set\ttitle\ttag\nKS\tAlternative title\tAlternate\n"
        args = [*args, "--set-names", str(target)]
    else:
        target = root / "drop.txt"
        target.write_text("Ref.region001.gbk\n")
        replacement = b"AS-900__N1.region001.gbk\n"
        args = [*args, "--drop-origins", str(target)]
    state, previous = substitute_second_read(monkeypatch, target, replacement)
    assert ppr.main(args) == 2
    assert state["substituted"] is True
    assert target.read_bytes() == previous
    assert not captured
    assert not (root / "output/render_receipt.json").exists()


@pytest.mark.parametrize("kind", ["run", "nearest"])
def test_optional_absence_cannot_be_replaced_read_and_restored(replay, monkeypatch, kind):
    root, directory, args, captured = replay
    target = directory / ("RUN_KS.json" if kind == "run" else "NEAREST_KS.tsv")
    target.unlink(missing_ok=True)
    replacement = b'{"pct_axes":[30,20]}' if kind == "run" else b"id\tnearest_pident\ni1\t90\n"
    original_binding = ppr.file_binding
    original_read = Path.read_bytes
    state = {"created": False, "consumed": False}
    def admit_then_create(path):
        record = original_binding(path)
        if path == target and not state["created"]:
            assert record["state"] == "NOT_PROVIDED"
            target.write_bytes(replacement)
            state["created"] = True
        return record
    def restore_after_read(path):
        raw = original_read(path)
        if path == target:
            target.unlink()
            state["consumed"] = True
        return raw
    monkeypatch.setattr(ppr, "file_binding", admit_then_create)
    monkeypatch.setattr(Path, "read_bytes", restore_after_read)
    assert ppr.main(args) == 2
    assert state == {"created": True, "consumed": True}
    assert not target.exists() and not captured
    assert not (root / "output/render_receipt.json").exists()


@pytest.mark.parametrize("extra", [
    ["--set", "KS", "--set", "KS"],
    ["--panel", "demo=group_a"],
])
def test_duplicate_requests_refused_before_creating_output(replay, extra):
    root, directory, args, captured = replay
    assert ppr.main([*args, *extra]) == 2
    assert not captured and not (root / "output").exists()


def test_distinct_requests_cannot_alias_one_output_prefix(replay):
    root, directory, args, captured = replay
    for name in ("A_B", "A"):
        other = directory.parent / ("out_" + name)
        other.mkdir()
        (other / ("PCOA_" + name + ".tsv")).write_bytes((directory / "PCOA_KS.tsv").read_bytes())
    assert ppr.main([*args, "--set", "A_B", "--set", "A",
                     "--panel", "C=group_a", "--panel", "B_C=group_a"]) == 2
    assert not captured and not (root / "output").exists()


@pytest.mark.parametrize("extra", [
    ["--panel", "DEMO=group_a"],
    ["--panel", "moss_é=group_a", "--panel", "moss_e\u0301=group_a"],
    ["--set", "KS", "--set", "ks"],
])
def test_case_or_unicode_equivalent_prefixes_refused_portably(replay, extra):
    root, directory, args, captured = replay
    assert ppr.main([*args, *extra]) == 2
    assert not captured and not (root / "output").exists()


@pytest.mark.parametrize("sets,panels", [
    (["../KS"], ["demo=x"]), (["KS"], ["../outside=x"]),
    (["KS\\nested"], ["demo=x"]), (["KS"], ["nested\\outside=x"]),
    ([""], ["demo=x"]), (["KS"], ["=x"]), (["KS"], ["missing-equals"]),
])
def test_output_ids_are_contained_filename_components(sets, panels):
    with pytest.raises(ppr.RenderRefusal):
        ppr.admit_output_ids(sets, panels)


def test_safe_output_ids_preserve_spaces_unicode_and_panel_order():
    ppr.admit_output_ids(["KS", "GT1"], ["bee and wasp=x", "moss_é=y"])


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029", "\r\n", "\n"])
def test_bound_tsv_keeps_legacy_physical_csv_newlines(tmp_path, separator):
    path = tmp_path / "physical.tsv"
    raw = ("\ufeffid\tnotes\r\np1\t\"left" + separator + "right\"\r\np2\tplain\r\n").encode("utf-8")
    path.write_bytes(raw)
    expected = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""), delimiter="\t"))
    assert ppr.read_tsv(path) == expected
    assert ppr.read_tsv(path, expected_binding=ppr.file_binding(path)) == expected


def test_direct_panel_default_and_admitted_drop_set_preserve_figure_spec(replay, monkeypatch):
    root, directory, args, captured = replay
    drop = root / "drop.txt"
    drop.write_text("Ref.region001.gbk\n")
    options = SimpleNamespace(drop_origins=str(drop), exclude_strain=[], label_below=70.0,
                              top_strains=0, quantile=.95, number_above=30, mid_below=None,
                              require_axis_metadata=False)
    monkeypatch.setattr(ppr, "choose_labels", lambda points, background, **kwargs: ([], [], 0, False))
    rows = ppr.read_tsv(directory / "PCOA_KS.tsv")
    common = (options, "KS", rows, {"i1": 60}, {}, {"AS-900": "group_a"},
              "demo", {"group_a"}, "#0072B2", "Study isolates", {})
    left = root / "legacy_panel"
    right = root / "admitted_panel"
    left.mkdir(); right.mkdir()
    legacy = ppr.build_panel(*common, left, "matplotlib")
    admitted = ppr.build_panel(*common, right, "matplotlib", drop_origins={"Ref.region001.gbk"})
    assert captured[0] == captured[1]
    assert {k: v for k, v in legacy.items() if k != "stamp"} == {
        k: v for k, v in admitted.items() if k != "stamp"}


@pytest.mark.parametrize("kind,already_admitted", [
    ("coordinates", False), ("nearest", False), ("run", False),
    ("cohorts", False), ("set_names", False), ("drop_origins", False),
    ("nearest", True),
])
def test_retargeted_input_symlink_refused_before_any_draw(replay, monkeypatch, kind, already_admitted):
    root, directory, args, captured = replay
    run_path = directory / "RUN_KS.json"
    run_path.write_text('{"pct_axes":[30,20]}')
    paths = {"coordinates": directory / "PCOA_KS.tsv",
             "nearest": directory / "NEAREST_KS.tsv", "run": run_path,
             "cohorts": root / "cohorts.tsv"}
    if kind == "set_names":
        paths[kind] = root / "names.tsv"
        paths[kind].write_text("set\ttitle\ttag\nKS\tSaved title\tKS\n")
        args = [*args, "--set-names", str(paths[kind])]
    elif kind == "drop_origins":
        paths[kind] = root / "drop.txt"
        paths[kind].write_text("Ref.region001.gbk\n")
        args = [*args, "--drop-origins", str(paths[kind])]
    target = paths[kind]
    backing = root / (kind + ".original")
    backing.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(backing)
    if already_admitted:
        replacement = directory / "PCOA_KS.tsv"
    else:
        replacement = root / (kind + ".replacement")
        replacement.write_bytes(backing.read_bytes() + b"\n")
    original_binding = ppr.file_binding
    state = {"retargeted": False}
    def admit_then_retarget(path):
        record = original_binding(path)
        # RUN is the final set input admitted, after every expected binding is saved.
        if path == run_path and not state["retargeted"]:
            target.unlink()
            target.symlink_to(replacement)
            state["retargeted"] = True
        return record
    monkeypatch.setattr(ppr, "file_binding", admit_then_retarget)
    assert ppr.main(args) == 2
    assert state["retargeted"] is True
    assert not captured and not (root / "output/render_receipt.json").exists()


@pytest.mark.parametrize("kind", ["run", "nearest"])
@pytest.mark.parametrize("malformed", ["directory", "broken_symlink"])
def test_existing_nonregular_optional_input_is_not_missing(replay, kind, malformed):
    root, directory, args, captured = replay
    target = directory / ("RUN_KS.json" if kind == "run" else "NEAREST_KS.tsv")
    target.unlink(missing_ok=True)
    if malformed == "directory":
        target.mkdir()
    else:
        target.symlink_to(root / "nonexistent_input")
    assert ppr.main(args) == 2
    assert not captured and not (root / "output/render_receipt.json").exists()


@pytest.mark.parametrize("kind", ["run", "nearest"])
def test_optional_directory_created_after_absence_admission_is_refused(replay, monkeypatch, kind):
    root, directory, args, captured = replay
    target = directory / ("RUN_KS.json" if kind == "run" else "NEAREST_KS.tsv")
    target.unlink(missing_ok=True)
    original_binding = ppr.file_binding
    state = {"created": False}
    def admit_then_create_directory(path):
        record = original_binding(path)
        if path == target and not state["created"]:
            assert record["state"] == "NOT_PROVIDED"
            target.mkdir()
            state["created"] = True
        return record
    monkeypatch.setattr(ppr, "file_binding", admit_then_create_directory)
    assert ppr.main(args) == 2
    assert state["created"] is True
    assert not captured and not (root / "output/render_receipt.json").exists()


@pytest.mark.parametrize("kind", ["run", "nearest"])
def test_genuinely_absent_optional_input_keeps_legacy_success(replay, kind):
    root, directory, args, captured = replay
    target = directory / ("RUN_KS.json" if kind == "run" else "NEAREST_KS.tsv")
    target.unlink(missing_ok=True)
    assert ppr.main(args) == 0
    assert captured
    receipt = json.loads((root / "output/render_receipt.json").read_text())
    assert next(row for row in receipt["inputs"] if row["path"] == str(target.resolve())) == {
        "path": str(target.resolve()), "state": "NOT_PROVIDED"}


@pytest.mark.parametrize("kind", ["run", "nearest"])
def test_stable_optional_file_symlink_remains_supported(replay, kind):
    root, directory, args, captured = replay
    target = directory / ("RUN_KS.json" if kind == "run" else "NEAREST_KS.tsv")
    if kind == "run":
        target.write_text('{"pct_axes":[30,20]}')
    backing = root / (kind + ".saved_input")
    backing.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(backing)
    assert ppr.main(args) == 0
    assert captured
    receipt = json.loads((root / "output/render_receipt.json").read_text())
    record = next(row for row in receipt["inputs"] if row["path"] == str(backing.resolve()))
    assert record["state"] == "PRESENT"
    assert record["sha256"] == hashlib.sha256(backing.read_bytes()).hexdigest()


@pytest.mark.parametrize("reader", ["file_binding", "read_bound_bytes"])
def test_input_open_failure_has_typed_refusal(tmp_path, monkeypatch, reader):
    target = tmp_path / "saved.tsv"
    target.write_text("id\n1\n")
    expected = ppr.file_binding(target)
    original_open = Path.open
    def refuse_open(path, *args, **kwargs):
        if path == target:
            raise IsADirectoryError("input changed between admission and read")
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", refuse_open)
    with pytest.raises(ppr.RenderRefusal, match="cannot read input"):
        if reader == "file_binding":
            ppr.file_binding(target)
        else:
            ppr.read_bound_bytes(target, expected)
