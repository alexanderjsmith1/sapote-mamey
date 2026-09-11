"""test_inspect_command_gold_only_v97162.py

Regression: `mamey inspect` must suggest the current gold-direct run command,
never the removed smoke/chatgpt-safe/chatgpt-followup surface. The stale block
survived the v9.7.161 smoke removal in package_inspector.py (lines ~179/192)
and was fixed in v9.7.162's doc-sweep. This locks it so it can't come back.
"""
import io
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

import mamey.package_inspector as pi


def _make_fake_antismash_zip(tmp_path: Path) -> Path:
    """Minimal ZIP that inspect will parse: one region GBK + a JSON."""
    z = tmp_path / "FAKE-STRAIN.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr(
            "NODE_1_length_50000_cov_10.region001.gbk",
            "LOCUS       NODE_1  50000 bp    DNA\n//\n",
        )
        zf.writestr("FAKE-STRAIN.json", "{}")
    return z


def _run_inspect(zip_path: Path) -> str:
    class _Args:
        pass

    args = _Args()
    # inspect_command reads args.zip / args.input_zip depending on version;
    # set both defensively.
    args.zip = str(zip_path)
    args.input_zip = str(zip_path)
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            pi.inspect_command(args)
        except AttributeError:
            # signature variant: inspect_command(zip_path)
            pi.inspect_command(str(zip_path))
    return buf.getvalue()


def test_inspect_emits_no_removed_flags(tmp_path):
    out = _run_inspect(_make_fake_antismash_zip(tmp_path))
    lowered = out.lower()
    assert "--mode smoke" not in lowered
    assert "--chatgpt-safe" not in lowered
    assert "--chatgpt-followup" not in lowered


def test_inspect_emits_gold_direct_command(tmp_path):
    out = _run_inspect(_make_fake_antismash_zip(tmp_path))
    assert "--mode gold" in out
    assert "--capped-session" in out
    assert "--release" in out
