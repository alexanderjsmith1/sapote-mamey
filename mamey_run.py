#!/usr/bin/env python3
"""
Mamey Standalone ChatGPT Bundle runner.

Works without pip install — use this in ChatGPT, Colab, or any environment
where a previously installed version of mamey may be cached.

Usage:
    python mamey_run.py run --strain X --input-zip Y [options]
    python mamey_run.py run --strains A.zip B.zip C.zip --master master.xlsx
    python mamey_run.py validate ./path/to/package_dir
    python mamey_run.py run --help
"""
import sys
import os
import re
# Force the local mamey/ package to take precedence over any installed version.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mamey


def _refuse_stale_bytecode():
    """Refuse when the imported engine disagrees with the source file beside it.

    Pinning sys.path gets the right DIRECTORY. It does not get the right BYTECODE: Python's
    default .pyc invalidation compares (source mtime, source size), and a cut writes a fixed
    1980 timestamp so archives stay byte-reproducible. A version bump keeps __init__.py the
    same length, so re-extracting a newer cut over a reused directory leaves both criteria
    unchanged and the stale cache is reused. The import then reports a version its own source
    does not contain -- the failure mode that put a 1.9.154 shadow in the workspace root.

    Read as text, compare, and stop. Nothing is deleted here; the remediation is printed.
    """
    init = os.path.join(_HERE, "mamey", "__init__.py")
    try:
        with open(init, encoding="utf-8") as handle:
            source = handle.read()
            found = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', source, re.M)
    except OSError:
        return  # cannot read the source: not our failure to diagnose
    if not found:
        return  # unrecognised layout: stay out of the way rather than block a run
    on_disk, imported = found.group(1), getattr(mamey, "__version__", None)
    mismatches = []
    if imported is not None and on_disk != imported:
        mismatches.append(f"__version__: source={on_disk!r}, imported={imported!r}")
    bundle = re.search(r'^BUNDLE_VERSION\s*=\s*["\']([^"\']+)["\']', source, re.M)
    if bundle and getattr(mamey, "BUNDLE_VERSION", None) != bundle.group(1):
        mismatches.append(f"BUNDLE_VERSION: source={bundle.group(1)!r}, imported={getattr(mamey, 'BUNDLE_VERSION', None)!r}")
    if not mismatches:
        return
    sys.stderr.write(
        "STALE_BYTECODE_REFUSED: " + "; ".join(mismatches) + "\n"
        f"  package: {getattr(mamey, '__file__', '?')}\n"
        "  A cached .pyc compiled from a different cut is being reused. The cut writes a fixed\n"
        "  1980 timestamp and a version bump does not change the file's size, so Python's\n"
        "  default (mtime, size) check cannot tell the two cuts apart.\n"
        "  Remediation: remove the stale caches under this bundle, e.g.\n"
        f"    find {_HERE!r} -name __pycache__ -type d -prune -exec rm -rf {{}} +\n"
        "  Nothing has been deleted for you.\n")
    raise SystemExit(2)


_refuse_stale_bytecode()
from mamey.cli import main
sys.exit(main())
