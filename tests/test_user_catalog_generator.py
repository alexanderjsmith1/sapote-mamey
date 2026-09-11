"""v9.7.86 B4: the user catalog regenerates from the scanner and does not drift."""
from __future__ import annotations
import sys, pathlib, subprocess
import pytest
from tests.conftest import hermetic_env  # v9.7.404 bytecode-leak fix

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def test_user_catalog_is_in_sync():
    # the committed USER_CATALOG.generated.* must match a fresh generation
    r = subprocess.run([sys.executable, "tools/gen_user_catalog.py", "--check"],
                       cwd=ROOT, capture_output=True, text=True,
                       env=hermetic_env(PYTHONPATH=str(ROOT), PATH=__import__("os").environ.get("PATH", "")))
    assert r.returncode == 0, f"USER_CATALOG drift: {r.stdout}{r.stderr}"


def test_catalog_covers_all_15_cassette_families():
    import gen_user_catalog
    cat = gen_user_catalog.build_catalog()
    assert len(cat["cassettes"]) == 15
    # every cassette resolved to an MMC id and has enriched prose
    for c in cat["cassettes"]:
        assert c["registry_id"].startswith("MMC-"), c["family"]
        assert c["description"], f"{c['family']} has no description"


def test_tomm_azole_in_catalog_is_mmc_011():
    import gen_user_catalog
    cat = gen_user_catalog.build_catalog()
    tomm = next(c for c in cat["cassettes"] if c["family"] == "tomm_azole_ripp")
    assert tomm["registry_id"] == "MMC-011"
    assert "indolocarbazole" not in tomm["name"].lower()


def test_catalog_documents_regulators_and_transporters():
    import gen_user_catalog
    cat = gen_user_catalog.build_catalog()
    scan_names = {s["scan"] for s in cat["scans"]}
    assert "regulators" in scan_names
    assert "transporters" in scan_names
