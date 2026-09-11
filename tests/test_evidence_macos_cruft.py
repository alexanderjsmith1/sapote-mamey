"""PARSE-P03/P08 (v9.7.325): antiSMASH evidence file-name lists must skip macOS AppleDouble
shadows. A `._NODE.region001.gbk` / `._regions.json` sidecar satisfies the naive
endswith('.gbk')+'region' / endswith('.json') filters, so without is_macos_cruft it would be
parsed as phantom evidence (or swallow an ijson error). Locks the filter on all three lists.
"""
import sys, os, zipfile
sys.path.insert(0, os.path.dirname(__file__))
from mamey.antismash_evidence import parse_antismash_evidence, extract_gbk_pfam_hits
from mamey.parsers import is_macos_cruft


def test_json_files_excludes_macos_shadows(tmp_path):
    z = tmp_path / "t.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("regions.json", "{}")                  # real
        zf.writestr("._regions.json", "junk")              # AppleDouble shadow
        zf.writestr("__MACOSX/._regions.json", "junk")     # resource-fork shadow
    ev = parse_antismash_evidence(str(z), json_mode="bounded")
    jf = ev.get("json_files", [])
    assert "regions.json" in jf
    assert not any(is_macos_cruft(n) for n in jf), f"shadow leaked into json_files: {jf}"


def test_gbk_pfam_ignores_shadow_regions(tmp_path):
    # only a shadow region GBK present -> filter drops it, nothing to parse, no crash
    z = tmp_path / "t.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("__MACOSX/._NODE_1.region001.gbk", "junk not a genbank record")
        zf.writestr("._NODE_1.region001.gbk", "junk not a genbank record")
    hits = extract_gbk_pfam_hits(str(z))   # must not raise on the shadow "gbk"
    assert isinstance(hits, dict)
