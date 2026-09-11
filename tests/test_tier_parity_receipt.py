import json
import subprocess
import sys
import zipfile
from pathlib import Path


def _tier_zip(path: Path, tier_name: str, overrides=None):
    files = {
        "CITATION.cff": 'cff-version: 1.2.0\nversion: "9.7.141"\n',
        "mamey/mamey_cassettes.py": 'Cassette("MMC-001")\n',
        "mamey/sapote_cassettes.py": 'Cassette("SMC-001")\n',
        "mamey/mamey_markers.py": 'Marker("MMK-ABC-001")\n',
        "mamey/sapote_markers.py": 'Marker("SMK-ABC-001")\n',
        "bundle_support/registry_inventory_v1.9.4.json": "[]\n",
        "docs/BUNDLE_CAPABILITIES.md": "session\n",
        "docs/DELIVERABLE_MANIFEST_TEMPLATE.md": "deliverable\n",
        "tools/check_deliverable_suite.py": "print('ok')\n",
        "tools/sapote_judgment_receipt.py": "print('ok')\n",
    }
    if overrides:
        files.update(overrides)
    with zipfile.ZipFile(path, "w") as z:
        root = f"sapote-mamey-v9.7.141-{tier_name}/"
        for rel, text in files.items():
            z.writestr(root + rel, text)


def test_check_tier_parity_writes_receipt(tmp_path):
    zips = []
    for tier in ["CODE", "CODE-analysis-free", "SID-public", "MERGED-PRIVATE-scaffold"]:
        zp = tmp_path / f"sapote-mamey-v9.7.141-{tier}-20260101v97141a.zip"
        _tier_zip(zp, tier)
        zips.append(str(zp))
    receipt = tmp_path / "TIER_PARITY_RECEIPT.json"
    res = subprocess.run(
        [sys.executable, "tools/check_tier_parity.py", "--zips", *zips, "--receipt-out", str(receipt)],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    payload = json.loads(receipt.read_text())
    assert payload["schema_version"] == "tier_parity_receipt_v1"
    assert payload["status"] == "PASS"
    assert len(payload["tiers"]) == 4


def test_check_tier_parity_refuses_an_incomplete_set(tmp_path):
    code = tmp_path / "sapote-mamey-v9.7.141-CODE-20260101v97141a.zip"
    _tier_zip(code, "CODE")
    receipt = tmp_path / "TIER_PARITY_RECEIPT.json"
    res = subprocess.run(
        [sys.executable, "tools/check_tier_parity.py", "--zips", str(code),
         "--receipt-out", str(receipt)],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert res.returncode == 1
    payload = json.loads(receipt.read_text())
    assert payload["status"] == "FAIL"
    assert payload["required_tiers"] == ["clean", "code", "cohort", "merged"]
    assert any("missing required tier" in finding for finding in payload["findings"])


def test_check_tier_parity_recognizes_optional_public_promotion(tmp_path):
    zips = []
    for tier in ["CODE", "CODE-analysis-free", "SID-public", "MERGED-PRIVATE-scaffold",
                 "PUBLIC-RELEASE"]:
        zp = tmp_path / f"sapote-mamey-v9.7.141-{tier}-20260101v97141a.zip"
        _tier_zip(zp, tier)
        zips.append(str(zp))
    res = subprocess.run(
        [sys.executable, "tools/check_tier_parity.py", "--zips", *zips, "--json"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    payload = json.loads(res.stdout)
    assert [tier["tier"] for tier in payload["tiers"]][-1] == "public"


def test_with_public_requires_public_promotion(tmp_path):
    zips = []
    for tier in ["CODE", "CODE-analysis-free", "SID-public", "MERGED-PRIVATE-scaffold"]:
        zp = tmp_path / f"sapote-mamey-v9.7.141-{tier}.zip"
        _tier_zip(zp, tier)
        zips.append(str(zp))
    res = subprocess.run(
        [sys.executable, "tools/check_tier_parity.py", "--zips", *zips,
         "--with-public", "--json"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert res.returncode == 1
    payload = json.loads(res.stdout)
    assert payload["required_tiers"] == ["clean", "code", "cohort", "merged", "public"]
    assert any("public" in finding for finding in payload["findings"])


def test_release_wrapper_opt_in_threads_public_to_cut_and_parity():
    script = (Path(__file__).resolve().parents[1] / "tools" / "release.sh").read_text()
    assert 'TIERS+=(public)' in script
    assert 'PARITY_ARGS+=(--with-public)' in script
    assert 'for TIER in "${TIERS[@]}"' in script


def test_check_tier_parity_receipt_fails_on_drift(tmp_path):
    good = tmp_path / "sapote-mamey-v9.7.141-CODE-20260101v97141a.zip"
    bad = tmp_path / "sapote-mamey-v9.7.141-SID-public-20260101v97141a.zip"
    _tier_zip(good, "CODE")
    _tier_zip(
        bad,
        "SID-public",
        overrides={"mamey/sapote_markers.py": 'Marker("SMK-ABC-001")\nMarker("SMK-ABC-002")\n'},
    )
    receipt = tmp_path / "TIER_PARITY_RECEIPT.json"
    res = subprocess.run(
        [sys.executable, "tools/check_tier_parity.py", "--zips", str(good), str(bad), "--receipt-out", str(receipt)],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert res.returncode == 1
    payload = json.loads(receipt.read_text())
    assert payload["status"] == "FAIL"
    assert payload["findings"]
