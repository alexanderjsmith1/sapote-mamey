"""Draft public release-check controls using small synthetic trees. NOT RUN."""
from pathlib import Path
import hashlib
import pytest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import check_release_manifest as gate
import verify_release_identity as identity

def tree(root):
    (root/"BUILD_STAMP.txt").write_text("build=synthetic\n")
    (root/"payload.txt").write_text("synthetic payload")
    (root/"TIER_MANIFEST.txt").write_text("# stamp=synthetic\n./BUILD_STAMP.txt\n./payload.txt\n")
    sums=root/"SOURCE_CHECKSUMS_SHA256.txt"
    sums.write_text("".join(hashlib.sha256((root/name).read_bytes()).hexdigest()+"  ./"+name+"\n" for name in ("BUILD_STAMP.txt","payload.txt","TIER_MANIFEST.txt")))
    return sums

@pytest.mark.parametrize("case",["complete","empty","comments","subset","duplicate","missing_tier","missing_stamp","symlink_tier"])
def test_public_check_requires_admitted_coverage(tmp_path,case):
    sums=tree(tmp_path)
    if case=="empty":sums.write_text("")
    elif case=="comments":sums.write_text("# no content\n")
    elif case=="subset":sums.write_text(sums.read_text().splitlines()[0]+"\n")
    elif case=="duplicate":sums.write_text(sums.read_text()+sums.read_text().splitlines()[0]+"\n")
    elif case=="missing_tier":(tmp_path/"TIER_MANIFEST.txt").unlink()
    elif case=="missing_stamp":(tmp_path/"BUILD_STAMP.txt").unlink()
    elif case=="symlink_tier":
        tier=tmp_path/"TIER_MANIFEST.txt";text=tier.read_text();tier.unlink()
        other=tmp_path/"other";other.write_text(text);tier.symlink_to(other)
    assert gate.main(["--root",str(tmp_path),"--quiet"])==(0 if case=="complete" else 1)

def test_strict_identity_content_inherits_coverage(tmp_path):
    tree(tmp_path).write_text("# nothing measured\n")
    assert identity.check_content(tmp_path,strict_coverage=True)
    # The byte-check-only helper retains its deliberately limited default contract.
    assert identity.check_content(tmp_path)==[]
