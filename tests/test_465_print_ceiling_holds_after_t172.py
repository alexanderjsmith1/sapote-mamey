"""465 08: the .465 stack stays within the repository's print-call ceiling.

The sequence-group sharing tool added one direct print call, which took the measured count
past the ceiling in tools/repo_health.py. Its summary line is now written to sys.stdout, with
the same bytes.
"""
import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_venn_tool_has_no_direct_print():
    tree = ast.parse((ROOT / "tools/sequence_group_sharing_venn.py").read_text(encoding="utf-8"))
    calls = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == "print"]
    assert not calls, calls


def test_print_calls_within_ceiling():
    out = subprocess.run([sys.executable, str(ROOT / "tools/repo_health.py"), "--root", str(ROOT), "--json"],
                         capture_output=True, text=True, timeout=600)
    data = json.loads(out.stdout)
    rows = data if isinstance(data, list) else data.get("results", data.get("checks", []))
    row = next(r for r in rows if r["name"] == "print_calls")
    assert row["status"] == "OK", row["detail"]
