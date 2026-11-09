"""deliverable-queue resume binds the content behind --cohort-dir, --strain-metadata, ...

Resume hashed the source argument strings only. New bytes at the same
--strain-metadata path, or a new package in --cohort-dir, still skipped a DONE strain.
"""
import os
from pathlib import Path

import pytest

from mamey import deliverable_queue as queue


@pytest.fixture
def setup(tmp_path, monkeypatch):
    runs, out = tmp_path / "runs", tmp_path / "out"
    pkg = runs / "PUBLIC1" / "package"; pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text("{}")
    meta = tmp_path / "strain_metadata.tsv"; meta.write_text("strain\tgenus\nPUBLIC1\tStreptomyces\n")
    cohort = tmp_path / "cohort"; (cohort / "PUBLIC2" / "package").mkdir(parents=True)
    (cohort / "PUBLIC2" / "package" / "PUBLIC2_2_inventory.csv").write_text("BGC_ID\nBGC001\n")
    calls = []

    def fake_process(strain, runs_dir, out_root, activity_csv=None, sources=None):
        calls.append(strain)
        d = Path(out_root) / strain / "sapote"; d.mkdir(parents=True, exist_ok=True)
        (d / "report.md").write_text("report\n")
        return {"strain": strain, "status": "DETERMINISTIC_DONE"}

    monkeypatch.setattr(queue, "process_strain", fake_process)
    sources = {"strain_metadata": str(meta), "cohort_dir": str(cohort)}
    run = lambda: queue.run_queue(["PUBLIC1"], str(runs), str(out), sources=sources)
    return run, calls, meta, cohort


def test_unchanged_sources_skip(setup):
    run, calls, *_ = setup
    run(); run()
    assert calls == ["PUBLIC1"]


def test_new_metadata_bytes_at_same_path_rerun(setup):
    run, calls, meta, _ = setup
    run(); meta.write_text("strain\tgenus\nPUBLIC1\tKribbella\n"); run()
    assert calls == ["PUBLIC1", "PUBLIC1"]


def test_new_file_in_cohort_dir_reruns(setup):
    run, calls, _, cohort = setup
    run()
    extra = cohort / "PUBLIC3" / "package"; extra.mkdir(parents=True)
    (extra / "PUBLIC3_2_inventory.csv").write_text("BGC_ID\nBGC001\n")
    run()
    assert calls == ["PUBLIC1", "PUBLIC1"]


def test_removed_source_path_reruns(setup):
    run, calls, meta, _ = setup
    run(); os.remove(meta); run()
    assert calls == ["PUBLIC1", "PUBLIC1"]
