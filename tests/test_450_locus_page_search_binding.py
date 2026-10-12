"""Portable page-search cache proof using monkeypatched fake tools only.

No installed biological binary, database or search is used. The existing synthetic
locus-page tests separately exercise the CLI against their fake executables.
"""
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from tests.test_449_locus_reading_pages import lrp, _gene, S, C1, C5, C5_REWRITTEN


def _kit(tmp_path, monkeypatch, *, empty=False, fault=None):
    root = tmp_path / "inputs"
    root.mkdir()
    faa = root / f"{S}.faa"
    faa.write_text(">AS-900|g2|source\nMKT\n>AS-900|g3|source\nMKS\n")
    pfam = root / "Pfam-A.hmm"
    pfam.write_text("synthetic profile source\n")
    db = root / "mibig_proteins.dmnd"
    db.write_bytes(b"synthetic DIAMOND source")
    names = root / "mibig_proteins.tsv"
    names.write_text("id\tname\nBGC0000001|ref\tref\n")
    hmm, diamond = root / "hmmsearch", root / "diamond"
    hmm.write_text("fake hmmsearch identity v1\n")
    diamond.write_text("fake diamond identity v1\n")
    tools = {"hmmsearch": str(hmm), "diamond": str(diamond)}
    monkeypatch.setattr(lrp.shutil, "which", lambda value: tools.get(value))
    opts = SimpleNamespace(proteomes=str(root), pfam=str(pfam), mibig_proteins=str(root),
                           hmmsearch="hmmsearch", diamond="diamond", threads=2)
    calls = []

    def fake_run(argv, **kwargs):
        assert kwargs["check"] is True
        calls.append(list(argv))
        is_hmm = Path(argv[0]).name == "hmmsearch"
        query = Path(argv[-1] if is_hmm else argv[argv.index("-q") + 1])
        lines = query.read_text().splitlines()
        seqs = {lines[i][1:]: lines[i + 1] for i in range(0, len(lines), 2)}
        output = Path(argv[argv.index("--domtblout" if is_hmm else "-o") + 1])
        rows = []
        for tag, aa in seqs.items():
            if is_hmm:
                fields = ["-"] * 23
                fields[0], fields[2], fields[3] = tag, str(len(aa)), "PF_TEST"
                fields[19], fields[20] = "1", str(len(aa))
                rows.append(" ".join(fields))
            else:
                rows.append("\t".join([tag, "BGC0000001|ref", "70", str(len(aa)), str(len(aa)), "3",
                                        "100", "100", "1e-20", "99"]))
        output.write_text("" if empty else "\n".join(rows) + "\n")
        if fault is not None:
            fault(argv, output, is_hmm)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(lrp.subprocess, "run", fake_run)
    return opts, calls, {"faa": faa, "pfam": pfam, "db": db, "names": names, "hmm": hmm, "diamond": diamond}


def _search(out, opts, **kwargs):
    return lrp.page_search(S, {"g2", "g3"}, out, opts, **kwargs)


def _active(out):
    root = out / "_page_searches" / S
    return root / json.loads((root / "CURRENT.json").read_text())["generation"]


def _receipts(out):
    return list((out / "_page_searches").rglob("PAGE_SEARCH_RECEIPT.json"))


def test_exact_completed_generation_reuses_without_any_command(tmp_path, monkeypatch):
    opts, calls, _ = _kit(tmp_path, monkeypatch)
    out = tmp_path / "out"
    first = _search(out, opts)
    generation = _active(out)
    before = {p: p.read_bytes() for p in generation.iterdir()}
    receipt = json.loads((generation / "PAGE_SEARCH_RECEIPT.json").read_text())
    assert receipt["status"] == "COMPLETE"
    assert receipt["completed_searches"] == ["hmmsearch", "diamond"]
    assert receipt["binding"]["queries"][0]["aa_sha256"] == hashlib.sha256(b"MKT").hexdigest()
    assert _search(out, opts) == first
    assert len(calls) == 2
    assert {p: p.read_bytes() for p in generation.iterdir()} == before


@pytest.mark.parametrize("changed", ["faa", "pfam", "db", "names", "hmm", "diamond", "threads"])
def test_same_headers_do_not_reuse_changed_sequences_sources_tools_or_options(tmp_path, monkeypatch, changed):
    opts, calls, paths = _kit(tmp_path, monkeypatch)
    out = tmp_path / "out"
    _search(out, opts)
    previous = _active(out)
    before = {p: p.read_bytes() for p in previous.iterdir()}
    if changed == "threads":
        opts.threads = 3
    elif changed == "faa":
        paths[changed].write_text(paths[changed].read_text().replace("MKT", "MKA"))
    else:
        with paths[changed].open("ab") as stream:
            stream.write(b"changed")
    _search(out, opts)
    assert len(calls) == 4
    assert _active(out) != previous
    assert {p: p.read_bytes() for p in previous.iterdir()} == before
    assert len(_receipts(out)) == 2


def test_legacy_partial_files_are_retained_and_never_admitted(tmp_path, monkeypatch):
    opts, calls, _ = _kit(tmp_path, monkeypatch)
    out = tmp_path / "out"
    legacy = out / "_page_searches" / S
    legacy.mkdir(parents=True)
    old = {"proteins.faa": b">g2\nMKT\n>g3\nMKS\n", "pfam.domtbl": b"", "mibig.tsv": b""}
    for name, data in old.items():
        (legacy / name).write_bytes(data)
    pf, mb, reason = _search(out, opts)
    assert not reason and pf and mb and len(calls) == 2
    assert all((legacy / name).read_bytes() == data for name, data in old.items())


def test_output_tampering_creates_new_attempt_and_retains_the_corrupt_evidence(tmp_path, monkeypatch):
    opts, calls, _ = _kit(tmp_path, monkeypatch)
    out = tmp_path / "out"
    _search(out, opts)
    corrupt = _active(out)
    (corrupt / "pfam.domtbl").write_bytes(b"")
    _search(out, opts)
    assert len(calls) == 4 and _active(out) != corrupt
    assert (corrupt / "pfam.domtbl").read_bytes() == b""


@pytest.mark.parametrize("fault", ["missing", "duplicate", "empty"])
def test_unbound_query_roster_is_not_searched_or_reported_as_no_hit(tmp_path, monkeypatch, fault):
    opts, calls, paths = _kit(tmp_path, monkeypatch)
    if fault == "missing":
        paths["faa"].write_text(">g2\nMKT\n")
    elif fault == "duplicate":
        paths["faa"].write_text(">g2\nMKT\n>g2\nMKA\n>g3\nMKS\n")
    else:
        paths["faa"].write_text(">g2\n>g3\nMKS\n")
    out = tmp_path / "out"
    pf, mb, reason = _search(out, opts)
    assert not pf and not mb and reason.startswith("not run: PAGE_SEARCH_QUERY_")
    assert not calls and not _receipts(out)
    row, _ = lrp.cells(_gene("g2", C1, 1, L2b_bind="NOT_SEARCHED", mibig_queried="no (outside regions)"),
                       [], pf, mb, {}, lambda _acc: {"names": ""}, searched=False)
    assert "not searched †" in row and "no hit under the filters †" not in row


def test_empty_outputs_require_both_successful_commands_then_are_reusable(tmp_path, monkeypatch):
    opts, calls, _ = _kit(tmp_path, monkeypatch, empty=True)
    out = tmp_path / "out"
    pf, mb, reason = _search(out, opts)
    assert not reason and not pf and not mb and len(calls) == 2
    assert _search(out, opts) == (pf, mb, "") and len(calls) == 2
    assert json.loads((_active(out) / "PAGE_SEARCH_RECEIPT.json").read_text())["status"] == "COMPLETE"


def test_failed_second_command_leaves_failure_evidence_without_completion_or_active_index(tmp_path, monkeypatch):
    def fail(argv, _output, is_hmm):
        if not is_hmm:
            raise subprocess.CalledProcessError(1, argv)
    opts, calls, _ = _kit(tmp_path, monkeypatch, fault=fail)
    out = tmp_path / "out"
    with pytest.raises(subprocess.CalledProcessError):
        _search(out, opts)
    assert len(calls) == 2 and not _receipts(out)
    assert list((out / "_page_searches").rglob("PAGE_SEARCH_FAILURE.json"))
    assert list((out / "_page_searches").rglob("pfam.domtbl"))
    assert not (out / "_page_searches" / S / "CURRENT.json").exists()


@pytest.mark.parametrize("bad_output", ["unknown_query", "pfam_coordinate", "mibig_query_length", "mibig_subject"])
def test_malformed_or_unbound_rows_cannot_commit_a_completion_receipt(tmp_path, monkeypatch, bad_output):
    def corrupt(_argv, output, is_hmm):
        text = output.read_text()
        if is_hmm and bad_output == "unknown_query":
            output.write_text(text.replace("g2 ", "unknown ", 1))
        elif is_hmm and bad_output == "pfam_coordinate":
            rows = text.splitlines()
            fields = rows[0].split()
            fields[20] = "100"
            rows[0] = " ".join(fields)
            output.write_text("\n".join(rows) + "\n")
        elif not is_hmm and bad_output == "mibig_query_length":
            output.write_text(text.replace("\t3\t3\t3\t", "\t3\t999\t3\t", 1))
        elif not is_hmm and bad_output == "mibig_subject":
            output.write_text(text.replace("BGC0000001|ref", "unstructured_id", 1))
    opts, _, _ = _kit(tmp_path, monkeypatch, fault=corrupt)
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="PAGE_SEARCH_(PFAM|MIBIG)_OUTPUT_INVALID"):
        _search(out, opts)
    assert not _receipts(out)
    assert list((out / "_page_searches").rglob("PAGE_SEARCH_FAILURE.json"))


def test_mid_search_source_drift_cannot_commit_success(tmp_path, monkeypatch):
    paths = {}
    def drift(_argv, _output, is_hmm):
        if not is_hmm:
            paths["db"].write_bytes(b"changed during search")
    opts, _, paths = _kit(tmp_path, monkeypatch, fault=drift)
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="PAGE_SEARCH_SOURCE_CHANGED: mibig_db"):
        _search(out, opts)
    assert not _receipts(out)


def test_shared_context_hashes_fixed_sources_twice_per_build_not_per_strain(tmp_path, monkeypatch):
    opts, calls, paths = _kit(tmp_path, monkeypatch)
    other = paths["faa"].with_name("AS-901.faa")
    other.write_bytes(paths["faa"].read_bytes())
    out, context = tmp_path / "out", {}
    _search(out, opts, source_context=context)
    source_count = len([row for row in context["sources"].values() if row["state"] == "PRESENT"])
    assert context["hashing_work"]["full_file_reads"] == source_count
    lrp.page_search("AS-901", {"g2", "g3"}, out, opts, source_context=context)
    assert len(calls) == 4 and context["hashing_work"]["full_file_reads"] == source_count
    lrp._page_verify_context(context, full=True)
    assert context["hashing_work"]["full_file_reads"] == 2 * source_count
    assert context["hashing_work"]["bytes_hashed"] == 2 * sum(r.get("bytes", 0) for r in context["sources"].values())


@pytest.mark.parametrize("conflict", ["length", "coordinates", "duplicate_physical_identity"])
def test_ledger_conflicts_remain_identity_holds(tmp_path, monkeypatch, conflict):
    opts, calls, _ = _kit(tmp_path, monkeypatch)
    rows = [_gene(tag, C1, i, aa="3") for i, tag in enumerate(("g2", "g3"), 1)]
    if conflict == "length":
        rows[0]["aa"] = "4"
    elif conflict == "coordinates":
        rows[0]["end"] = rows[0]["start"]
    else:
        rows.append({**rows[0], "contig": "NODE_2_length_9000_cov_1"})
    pf, mb, reason = _search(tmp_path / "out", opts, gene_rows=rows)
    assert not calls and not pf and not mb and "HOLD" in reason


@pytest.mark.parametrize("value,expected", [("", "not available"), (None, "not available"), (0, "0.00"),
                                             ("0", "0.00"), ("0.5", "0.50"),
                                            ("nan", "source value invalid"), ("bad", "source value invalid")])
def test_missing_saved_gene_average_is_not_displayed_as_zero(value, expected):
    row, _ = lrp.cells(_gene("g2", C1, 1, LG_gene_avg_p=value), [], {}, {}, {}, lambda _acc: {}, False)
    assert f"| {expected} |" in row



def test_completion_marker_is_last_and_an_interrupted_commit_stays_failed(tmp_path, monkeypatch):
    opts, _, _ = _kit(tmp_path, monkeypatch)
    original = lrp._page_atomic_json
    seen = []
    def interrupt(path, value):
        seen.append(path.name)
        if path.name == "PAGE_SEARCH_RECEIPT.json":
            assert all((path.parent / name).is_file() for name in lrp.PAGE_SEARCH_OUTPUTS)
            assert not (path.parent.parents[2] / "CURRENT.json").exists()
            raise InterruptedError("synthetic interrupted completion")
        return original(path, value)
    monkeypatch.setattr(lrp, "_page_atomic_json", interrupt)
    out = tmp_path / "out"
    with pytest.raises(InterruptedError):
        _search(out, opts)
    assert seen == ["PAGE_SEARCH_RECEIPT.json", "PAGE_SEARCH_FAILURE.json"]
    assert not _receipts(out)
    assert list((out / "_page_searches").rglob("PAGE_SEARCH_FAILURE.json"))


def test_missing_explicit_tool_is_not_replaced_or_auto_searched(tmp_path, monkeypatch):
    opts, calls, _ = _kit(tmp_path, monkeypatch)
    monkeypatch.setattr(lrp.shutil, "which", lambda _name: None)
    pf, mb, reason = _search(tmp_path / "out", opts)
    assert not pf and not mb and not calls
    assert "no hmmsearch" in reason and "no DIAMOND" in reason


def test_reusing_older_valid_binding_updates_active_index_without_commands(tmp_path, monkeypatch):
    opts, calls, _ = _kit(tmp_path, monkeypatch)
    out = tmp_path / "out"
    original = _search(out, opts)
    earlier = _active(out)
    evidence_before = {p: p.read_bytes() for p in earlier.iterdir()}
    opts.threads = 3
    _search(out, opts)
    assert _active(out) != earlier
    opts.threads = 2
    assert _search(out, opts) == original and len(calls) == 4
    assert _active(out) == earlier
    assert {p: p.read_bytes() for p in earlier.iterdir()} == evidence_before


@pytest.mark.parametrize("fault", ["status", "missing_search", "byte_count"])
def test_incomplete_or_inconsistent_receipt_is_retained_but_not_reused(tmp_path, monkeypatch, fault):
    opts, calls, _ = _kit(tmp_path, monkeypatch)
    out = tmp_path / "out"
    _search(out, opts)
    old = _active(out)
    receipt_path = old / "PAGE_SEARCH_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    if fault == "status":
        receipt["status"] = "RUNNING"
    elif fault == "missing_search":
        receipt["completed_searches"] = ["hmmsearch"]
    else:
        receipt["outputs"]["pfam.domtbl"]["bytes"] += 1
    receipt_path.write_text(json.dumps(receipt))
    old_payload = receipt_path.read_bytes()
    _search(out, opts)
    assert len(calls) == 4 and _active(out) != old
    assert receipt_path.read_bytes() == old_payload


@pytest.mark.parametrize("was_absent", [False, True])
def test_exact_consumed_names_binding_rejects_read_then_change(tmp_path, monkeypatch, was_absent):
    opts, calls, paths = _kit(tmp_path, monkeypatch)
    if was_absent:
        paths["names"].unlink()  # synthetic fixture only
    _names, consumed = lrp._page_mibig_names(paths["names"])
    paths["names"].write_text("id\tname\nBGC0000001|ref\tchanged after read\n")
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="PAGE_SEARCH_SOURCE_CHANGED: consumed_mibig_names"):
        _search(out, opts, consumed_mibig_names=consumed)
    assert not calls and not _receipts(out)


def test_cache_root_symlink_refuses_without_commands_or_external_writes(tmp_path, monkeypatch):
    opts, calls, _ = _kit(tmp_path, monkeypatch)
    out, external = tmp_path / "out", tmp_path / "external"
    out.mkdir()
    external.mkdir()
    (out / "_page_searches").symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError, match="PAGE_SEARCH_CACHE_PATH_REFUSED"):
        _search(out, opts)
    assert not calls and not list(external.iterdir())


def test_active_index_failure_retains_but_excludes_completed_attempt(tmp_path, monkeypatch):
    opts, calls, _ = _kit(tmp_path, monkeypatch)
    atomic = lrp._page_atomic_json
    def fail_index(path, value):
        if path.name == "CURRENT.json":
            raise OSError("synthetic index failure")
        return atomic(path, value)
    monkeypatch.setattr(lrp, "_page_atomic_json", fail_index)
    out = tmp_path / "out"
    with pytest.raises(OSError, match="synthetic index failure"):
        _search(out, opts)
    failed = _receipts(out)[0].parent
    before = {p: p.read_bytes() for p in failed.iterdir()}
    assert (failed / "PAGE_SEARCH_FAILURE.json").exists()
    monkeypatch.setattr(lrp, "_page_atomic_json", atomic)
    _search(out, opts)
    assert len(calls) == 4 and _active(out) != failed
    assert {p: p.read_bytes() for p in failed.iterdir()} == before


def _colliding_contigs():
    alternate = "NODE_5_length_8000_cov_42.0"
    return {
        C1: [_gene("core", C1, 1, bgc="BGC001", region="region001")],
        C5: [_gene("exact_target", C5, 1)],
        alternate: [_gene("different_contig", alternate, 1)],
    }


def test_exact_full_contig_identity_wins_over_a_normalized_alias_collision():
    rows, order, _ = lrp.select_rows(_colliding_contigs(), "BGC001", [{"pair": "p"}],
                                    {"p": [{"status": "MISSING_FOUND_CLEAR", "best_contig": C5,
                                             "best_locus": "exact_target"}]}, {})
    assert order == [C1, C5]
    assert [r["locus_tag"] for r in rows] == ["core", "exact_target"]
    assert rows[-1]["contig"] == C5


def test_ambiguous_normalized_contig_alias_refuses_instead_of_selecting_last_row():
    with pytest.raises(ValueError, match="LOCUS_PAGE_CONTIG_IDENTITY_HOLD"):
        lrp.select_rows(_colliding_contigs(), "BGC001", [{"pair": "p"}],
                        {"p": [{"status": "MISSING_FOUND_CLEAR", "best_contig": C5_REWRITTEN,
                                 "best_locus": "exact_target"}]}, {})


def _fake_page_build(monkeypatch, source=None, *, drift=False):
    def build_pages(opts, out, context, built, output_paths):
        current = json.loads((out / "_page_searches" / "SOURCE_BINDING_RUN_RECEIPT.json").read_text())
        assert current["status"] == "RUNNING", "attempt state must precede log/page writes"
        if source is not None:
            lrp._page_source_context({"fixture": source}, context)
        page, log = out / ((opts.bgc or "first") + ".md"), out / "BUILD_LOG.tsv"
        output_paths.extend([page, log])
        page.write_text("synthetic reader output\n")
        with log.open("a") as stream:
            stream.write((opts.bgc or "first") + "\tOK\n")
        built.append(page)
        if drift:
            source.write_bytes(b"source changed after pages were written")
    monkeypatch.setattr(lrp, "_build_pages", build_pages)


def _run_current(out):
    return json.loads((out / "_page_searches" / "SOURCE_BINDING_RUN_RECEIPT.json").read_text())


def test_build_success_publishes_scoped_immutable_attempt_and_exact_outputs(tmp_path, monkeypatch):
    source = tmp_path / "tiny_source"
    source.write_bytes(b"source v1")
    _fake_page_build(monkeypatch, source)
    out = tmp_path / "out"
    built = lrp.build(SimpleNamespace(out=str(out), bgc=None))
    current = _run_current(out)
    assert current["status"] == "VERIFIED" and current["source_validation"] == "FINAL_HASH_VERIFIED"
    assert "not whole-build scientific validation" in current["scope"]
    assert current["hashing_work"] == {"full_file_reads": 2, "bytes_hashed": 2 * len(b"source v1")}
    record = out / current["record_path"]
    assert current["record_sha256"] == hashlib.sha256(record.read_bytes()).hexdigest()
    assert (record.parent / "RUNNING.json").is_file()
    assert {r["path"] for r in current["outputs"]} == {"first.md", "BUILD_LOG.tsv"}
    for item in current["outputs"]:
        assert item["sha256"] == hashlib.sha256((out / item["path"]).read_bytes()).hexdigest()
    assert built == [out / "first.md"]


def test_failed_append_replaces_current_success_and_retains_prior_record_and_partial_outputs(tmp_path, monkeypatch):
    source = tmp_path / "tiny_source"
    source.write_bytes(b"source v1")
    _fake_page_build(monkeypatch, source)
    out = tmp_path / "out"
    lrp.build(SimpleNamespace(out=str(out), bgc=None))
    previous_payload = (out / "_page_searches" / "SOURCE_BINDING_RUN_RECEIPT.json").read_bytes()
    previous = _run_current(out)
    previous_record = out / previous["record_path"]
    record_before, page_before = previous_record.read_bytes(), (out / "first.md").read_bytes()
    _fake_page_build(monkeypatch, source, drift=True)
    with pytest.raises(ValueError, match="PAGE_SEARCH_SOURCE_CHANGED"):
        lrp.build(SimpleNamespace(out=str(out), bgc="BGC002"))
    current = _run_current(out)
    assert current["status"] == "FAILED" and current["source_validation"] == "NOT_VERIFIED"
    attempt = out / current["attempt"]
    assert (attempt / "PREVIOUS_CURRENT.json").read_bytes() == previous_payload
    assert current["previous_current_sha256"] == hashlib.sha256(previous_payload).hexdigest()
    assert (attempt / "RUNNING.json").is_file() and (attempt / "FAILED.json").is_file()
    assert not (attempt / "VERIFIED.json").exists()
    assert previous_record.read_bytes() == record_before and (out / "first.md").read_bytes() == page_before
    assert {r["path"] for r in current["outputs"]} == {"BGC002.md", "BUILD_LOG.tsv"}
    assert current["error"]["type"] == "ValueError"


def test_no_search_context_preserves_legacy_current_bytes_without_claiming_source_verification(tmp_path, monkeypatch):
    out = tmp_path / "out"
    root = out / "_page_searches"
    root.mkdir(parents=True)
    legacy = b'{"status":"VERIFIED","legacy":true}\n'
    (root / "SOURCE_BINDING_RUN_RECEIPT.json").write_bytes(legacy)
    _fake_page_build(monkeypatch)
    lrp.build(SimpleNamespace(out=str(out), bgc=None))
    current = _run_current(out)
    assert current["status"] == current["source_validation"] == "NO_SEARCH_CONTEXT"
    assert current["sources"] == {} and current["hashing_work"] == {}
    assert (out / current["attempt"] / "PREVIOUS_CURRENT.json").read_bytes() == legacy


def test_existing_build_refusal_does_not_change_current_run_status(tmp_path, monkeypatch):
    out = tmp_path / "out"
    root = out / "_page_searches"
    root.mkdir(parents=True)
    (out / "BUILD_LOG.tsv").write_text("existing build\n")
    marker = root / "SOURCE_BINDING_RUN_RECEIPT.json"
    marker.write_text('{"status":"VERIFIED"}')
    before = marker.read_bytes()
    _fake_page_build(monkeypatch)
    with pytest.raises(SystemExit, match="versions are never overwritten"):
        lrp.build(SimpleNamespace(out=str(out), bgc=None))
    assert marker.read_bytes() == before and not (root / "run_attempts").exists()


@pytest.mark.parametrize("component", ["cache_root", "attempts_root", "current"])
def test_run_status_symlink_refusal_precedes_any_external_or_page_write(tmp_path, monkeypatch, component):
    out, external = tmp_path / "out", tmp_path / "external"
    out.mkdir()
    external.mkdir()
    root = out / "_page_searches"
    if component == "cache_root":
        root.symlink_to(external, target_is_directory=True)
    else:
        root.mkdir()
        if component == "attempts_root":
            (root / "run_attempts").symlink_to(external, target_is_directory=True)
        else:
            target = external / "receipt.json"
            target.write_text('{"status":"VERIFIED"}')
            (root / "SOURCE_BINDING_RUN_RECEIPT.json").symlink_to(target)
    before = {p.relative_to(external): p.read_bytes() for p in external.iterdir()}
    def no_build(*_args):
        pytest.fail("symlink refusal must precede page build")
    monkeypatch.setattr(lrp, "_build_pages", no_build)
    with pytest.raises(ValueError, match="PAGE_SEARCH_CACHE_PATH_REFUSED"):
        lrp.build(SimpleNamespace(out=str(out), bgc=None))
    assert {p.relative_to(external): p.read_bytes() for p in external.iterdir()} == before
    assert not (out / "BUILD_LOG.tsv").exists()


@pytest.mark.parametrize("fault", ["missing", "unreadable"])
def test_terminal_success_requires_every_explicit_attempt_output_to_be_bound(tmp_path, monkeypatch, fault):
    _fake_page_build(monkeypatch)
    produce = lrp._build_pages
    original_read = Path.read_bytes
    def damaged_build(opts, out, context, built, output_paths):
        produce(opts, out, context, built, output_paths)
        page = out / "first.md"
        if fault == "missing":
            page.unlink()  # synthetic fixture only
        else:
            def unreadable(path):
                if path == page:
                    raise PermissionError("synthetic unreadable page")
                return original_read(path)
            monkeypatch.setattr(Path, "read_bytes", unreadable)
    monkeypatch.setattr(lrp, "_build_pages", damaged_build)
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="PAGE_SEARCH_RUN_OUTPUT_BINDING_FAILED"):
        lrp.build(SimpleNamespace(out=str(out), bgc=None))
    current = _run_current(out)
    assert current["status"] == "FAILED" and current["source_validation"] == "NOT_VERIFIED"
    page_binding = next(item for item in current["outputs"] if item["path"] == "first.md")
    assert page_binding["state"] == "MISSING_OR_UNREADABLE"
    attempt = out / current["attempt"]
    assert (attempt / "FAILED.json").is_file() and not (attempt / "NO_SEARCH_CONTEXT.json").exists()


def test_secondary_search_receipt_failure_warns_without_masking_original_error(tmp_path, monkeypatch):
    def original_failure(argv, output, is_hmm):
        raise RuntimeError("synthetic original search failure")
    opts, calls, _ = _kit(tmp_path, monkeypatch, fault=original_failure)
    atomic = lrp._page_atomic_json
    def fail_failure_receipt(path, value):
        if path.name == "PAGE_SEARCH_FAILURE.json":
            raise OSError("synthetic receipt write failure")
        return atomic(path, value)
    warnings = []
    monkeypatch.setattr(lrp, "_page_atomic_json", fail_failure_receipt)
    monkeypatch.setattr(lrp._OUT, "warning", lambda *args: warnings.append(args))
    out = tmp_path / "out"
    with pytest.raises(RuntimeError, match="synthetic original search failure"):
        _search(out, opts)
    assert len(calls) == 1 and not _receipts(out)
    assert len(warnings) == 1 and "Could not record page-search failure" in warnings[0][0]
    assert str(warnings[0][-1]) == "synthetic receipt write failure"


def test_secondary_run_receipt_failure_warns_and_retains_running_status(tmp_path, monkeypatch):
    warnings = []
    monkeypatch.setattr(lrp._OUT, "warning", lambda *args: warnings.append(args))
    original_finish = lrp._page_finish_run
    def fail_failed_status(run, status, *args, **kwargs):
        if status == "FAILED":
            raise OSError("synthetic receipt write failure")
        return original_finish(run, status, *args, **kwargs)
    monkeypatch.setattr(lrp, "_page_finish_run", fail_failed_status)
    def fail_build(*args, **kwargs):
        raise ValueError("synthetic original build failure")
    monkeypatch.setattr(lrp, "_build_pages", fail_build)
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="synthetic original build failure"):
        lrp.build(SimpleNamespace(out=str(out), bgc=None))
    assert _run_current(out)["status"] == "RUNNING"
    assert len(warnings) == 1 and "Could not record failed locus-page attempt" in warnings[0][0]
    assert str(warnings[0][-1]) == "synthetic receipt write failure"
