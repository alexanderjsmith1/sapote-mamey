"""A failed BiG-SCAPE launch does not adopt a database left by an earlier run in the same folder."""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deliverable_tools"))
sys.path.insert(0, str(ROOT))
import bigscape_run as br  # noqa: E402


def test_failed_run_with_old_db_has_no_result(tmp_path, monkeypatch):
    gbks = tmp_path / "gbks"; gbks.mkdir()
    (gbks / "ctg1.region001.gbk").write_text("LOCUS       ctg1 10 bp DNA\nORIGIN\n        1 acgtacgtac\n//\n")
    out = tmp_path / "out"; out.mkdir()
    old = out / "old_run.db"; old.write_bytes(b"SQLite format 3\x00")
    past = time.time() - 3600; os.utime(old, (past, past))
    monkeypatch.setattr(br, "ensure_fasttree", lambda *a, **k: None)
    monkeypatch.setattr(br, "_stage_no_space", lambda p, w: p)
    monkeypatch.setattr(br.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1))
    res = br.run_pipeline(input_gbk_dir=str(gbks), out=str(out), run_widgets=False, work_dir=str(tmp_path / "w"))
    assert res["db"] is None and res["returncode"] == 1
    assert res["stale_db"] == str(old)
