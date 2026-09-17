#!/usr/bin/env python3
"""Refresh hashes for files in one exported tree-figure source package."""
from pathlib import Path
import hashlib
import json
import sys


def main() -> int:
    root = Path(__file__).resolve().parent
    manifest_path = root / "MANIFEST.json"
    prior = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    files = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if (
            path.is_file()
            and not path.is_symlink()
            and path.name != manifest_path.name
            and "__pycache__" not in relative.parts
            and ".pytest_cache" not in relative.parts
            and path.suffix not in {".pyc", ".pyo"}
        ):
            files[str(path.relative_to(root))] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
    prior["files"] = files
    manifest_path.write_text(json.dumps(prior, indent=2) + "\n")
    sys.stdout.write(f"manifest refreshed: {len(files)} files\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
