"""P6 (v9.7.101): the release builder must emit a bundle-root SHA256SUMS over the four
tier zips (dropped in v9.7.100; per-tier checksums alone don't give cross-zip verify).
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RELEASE_SH = ROOT / "tools" / "release.sh"


def test_release_sh_emits_top_level_sha256sums():
    if not RELEASE_SH.exists():
        pytest.skip("release.sh not in this tier")
    text = RELEASE_SH.read_text()
    assert "SHA256SUMS_" in text, "release.sh must emit a top-level SHA256SUMS file"
    # over the zips, and after the parity gate (so only validated tiers are summed)
    assert "*.zip" in text
    assert text.index("check_tier_parity") < text.index("SHA256SUMS_"), (
        "SHA256SUMS should be emitted after the cross-tier parity gate"
    )
