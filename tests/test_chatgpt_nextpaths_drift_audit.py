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
        "8. Package the acceptance receipts for signoff.",
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
