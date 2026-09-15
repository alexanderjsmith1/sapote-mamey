from pathlib import Path
import subprocess
import sys


def test_chatgpt_nextpaths_drift_audit_passes_current_repo():
    res = subprocess.run(
        [sys.executable, "tools/audit_chatgpt_nextpaths_drift.py", "."],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "PASS" in res.stdout


def test_chatgpt_nextpaths_drift_audit_fails_high_risk_3_to_10(tmp_path):
    (tmp_path / "prompts" / "reuse").mkdir(parents=True)
    bad = tmp_path / "prompts" / "reuse" / "BAD.md"
    bad.write_text("End with 3–10 numbered next paths.\n", encoding="utf-8")
    res = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parents[1] / "tools/audit_chatgpt_nextpaths_drift.py"), str(tmp_path)],
        text=True,
        capture_output=True,
    )
    assert res.returncode == 1
    assert "BAD.md" in res.stdout


def test_check_chatgpt_next_paths_good_and_bad_samples(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    good = tmp_path / "good.md"
    good.write_text("\n".join([
        "1. Run the Mode B coverage contract fixture.",
        "2. Add heartbeat coverage around workbook writes.",
        "3. Validate recovery status in package manifests.",
        "4. Rebuild the four-tier wrapper with receipts.",
        "5. Audit claim-safety wording in sample cards.",
        "6. Update current docs with deprecation language.",
        "7. Run the targeted release-safety test suite.",
        "8. SAVE STATE — saved: [checkpoint](SAVE_STATE.md).",
    ]), encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text("\n".join([
        "1. Continue.",
        "2. Continue.",
        "3. Continue.",
        "4. Continue.",
        "5. Continue.",
    ]), encoding="utf-8")

    res_good = subprocess.run([sys.executable, "tools/check_chatgpt_next_paths.py", str(good)], cwd=repo, text=True, capture_output=True)
    assert res_good.returncode == 0, res_good.stdout + res_good.stderr
    res_bad = subprocess.run([sys.executable, "tools/check_chatgpt_next_paths.py", str(bad)], cwd=repo, text=True, capture_output=True)
    assert res_bad.returncode == 1


def test_shared_handoff_boundaries_and_save_confirmation(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    for count, saved, expected in [(2, True, 1), (3, True, 0), (8, True, 0), (9, True, 1), (3, False, 1)]:
        rows = [f"{i}. Review evidence channel number {i} for this package." for i in range(1, count)]
        rows.append(f"{count}. " + ("SAVE STATE — saved: [checkpoint](SAVE_STATE.md)." if saved else "Review remaining scientific interpretation issues."))
        path = tmp_path / "handoff.md"
        path.write_text("\n\n".join(rows))
        result = subprocess.run([sys.executable, "tools/check_chatgpt_next_paths.py", str(path)], cwd=repo, capture_output=True, text=True)
        assert result.returncode == expected, result.stdout
