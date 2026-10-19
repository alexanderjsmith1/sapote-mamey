"""Cut snapshot fragment: names require no role admission; byte drift still refuses."""
from pathlib import Path
import os
import subprocess
import sys
import pytest
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "tools/make_public_tier.sh").read_text()
SNAPSHOT = SCRIPT.split("# BEGIN TEST SOURCE SNAPSHOT\n", 1)[1].split("# END TEST SOURCE SNAPSHOT", 1)[0]

@pytest.mark.parametrize("settings", [{}, {"AS_SCRUB": "0"}, {"AS_GUARD_RETIRED": "1"}, {"AS_SCRUB": "invalid"}])
def test_names_without_role_table_have_bound_snapshot(tmp_path, settings):
    root = tmp_path / "stage"; (root / "tests").mkdir(parents=True)
    (root / "tests" / "named.txt").write_text("AS-705\tNRPS\n")
    code = 'set -eu\n' + SNAPSHOT + '\nverify_staged_test_snapshot\nprintf "%s\\n" "$SOURCE_TEST_ROLE_SHA256"\n'
    result = subprocess.run(["bash", "-c", code], env={**os.environ, **settings, "SRC":str(ROOT), "STAGE":str(root), "PYTHON":sys.executable}, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0 and len(result.stdout.strip()) == 64
    assert (root / "tests" / "named.txt").read_text() == "AS-705\tNRPS\n"
    assert not (root / "tests" / "reviewed_public_reference_sites.json").exists()

@pytest.mark.parametrize("change", ["bytes", "namespace", "symlink"])
def test_staged_snapshot_refuses_generation_drift(tmp_path, change):
    root = tmp_path / "stage"; (root / "tests").mkdir(parents=True)
    (root / "tests" / "named.txt").write_text("AS-705\tNRPS\n")
    if change == "bytes": mutation = 'printf "changed\\n" >> "$STAGE/tests/named.txt"'
    elif change == "namespace": mutation = 'mkdir "$STAGE/tests/late"'
    else: mutation = 'ln -s named.txt "$STAGE/tests/link.txt"'
    code = 'set -eu\n' + SNAPSHOT + '\nverify_staged_test_snapshot\n' + mutation + '\nverify_staged_test_snapshot\n'
    result = subprocess.run(["bash", "-c", code], env={**os.environ,"SRC":str(ROOT),"STAGE":str(root),"PYTHON":sys.executable}, capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert not list(root.glob("*.zip"))


@pytest.mark.parametrize("late_change", [False, True])
def test_policy_omission_precedes_snapshot_and_later_drift_still_refuses(tmp_path, late_change):
    # Tie the behavioral probe to the actual cut's ordering, including its first capture call.
    first = SCRIPT.index('verify_staged_test_snapshot \\\n    || { echo "REFUSED: staged test source snapshot unavailable"')
    assert SCRIPT.index('public_release_audit_stage --apply-public-export-exclusions') < first
    assert first < SCRIPT.index('running in-tier pytest gate...')
    sys.path.insert(0,str(ROOT/'tools'))
    import public_release_audit as audit_mod
    from mamey.privacy_profile import PublicExportPolicy
    root = tmp_path/'stage';(root/'tests/fixtures/private_payload').mkdir(parents=True)
    (root/'tests/fixtures/private_payload/invented.txt').write_text('invented private fixture only\n')
    (root/'tests/named.txt').write_text('AS-705\tNRPS\n')
    policy=PublicExportPolicy(excluded_root_names=frozenset(),
        excluded_relative_paths=frozenset({'tests/fixtures/private_payload'}),
        private_identifiers=(),allowlisted_occurrences=())
    removed,problems=audit_mod.apply_public_export_exclusions(root,policy)
    assert removed == ['tests/fixtures/private_payload'] and not problems
    assert not (root/'tests/fixtures/private_payload').exists()
    mutation='printf "late change\\n" >> "$STAGE/tests/named.txt"\n' if late_change else ''
    code='set -eu\n'+SNAPSHOT+'\nverify_staged_test_snapshot\n'+mutation+'verify_staged_test_snapshot\n'
    result=subprocess.run(['bash','-c',code],env={**os.environ,'SRC':str(ROOT),'STAGE':str(root),'PYTHON':sys.executable},capture_output=True,text=True,timeout=20)
    assert (result.returncode != 0) if late_change else (result.returncode == 0)
    if late_change:assert 'staged test-source bytes or namespace changed' in result.stderr
