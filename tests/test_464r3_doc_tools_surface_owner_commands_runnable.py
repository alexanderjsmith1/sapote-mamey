"""Every Python command named as a generated-surface owner or validator starts with `python `.

The maintenance inventory copies these strings as the commands to run. The tool files are not
executable, so `tools/file_atlas.py --check` typed as listed fails with exit 126.
"""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gso_464r3", ROOT / "tools" / "generated_surface_ownership.py")
gso = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gso)


def _commands(text):
    for part in text.split(";"):
        part = part.strip()
        if re.fullmatch(r"(?:python\s+)?tools/\S+\.py(?:\s+(?:--|<)\S.*)?", part):  # prose is not a command
            yield part


def test_python_commands_carry_the_interpreter():
    seen = 0
    for name, surface in gso.SURFACES.items():
        for field in ("owner", "validator"):
            for command in _commands(surface[field]):
                seen += 1
                assert command.startswith("python tools/"), f"{name}.{field}: {command}"
    assert seen >= 10


def test_owner_paths_still_name_files():
    for surface in gso.SURFACES.values():
        for path in surface["owner_paths"]:
            assert (ROOT / path).is_file(), path
