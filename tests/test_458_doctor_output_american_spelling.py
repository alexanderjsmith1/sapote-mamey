"""User-facing doctor output uses American spelling (house rule).

Reads the string literals inside `doctor_command` without running doctor, so the
test does not touch `runs/_doctor_probe`.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _doctor_strings():
    tree = ast.parse((ROOT / "mamey" / "cli.py").read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "doctor_command")
    return [n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def test_doctor_output_says_license_not_licence():
    strings = _doctor_strings()
    assert not [s for s in strings if "licence" in s.lower()]
    assert any("MIT license" in s for s in strings)
