"""Offline, bounded admission for optional R renderer packages."""
from __future__ import annotations
import re
import shutil
import subprocess

TREE_RENDER_PACKAGES = ('ape', 'ggtree', 'ggplot2', 'aplot', 'treeio', 'patchwork')


def r_package_status(packages=('ggtree',), executable=None, timeout=10):
    """Return (state, message, Rscript); READY, UNAVAILABLE or UNVERIFIED."""
    r = executable or shutil.which('Rscript')
    if not r:
        return 'UNAVAILABLE', 'Rscript unavailable; R integration unverified', None
    for package in packages:
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9.]*', package):
            raise ValueError('invalid R package name')
        try:
            result = subprocess.run([r, '-e', f'if (!requireNamespace("{package}", quietly=TRUE)) {{cat("SAPOTE_R_MISSING:{package}\\n"); quit(status=10L)}}; quit(status=0L)'],
                                    capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 'UNVERIFIED', f'R package probe unverified: {package} ({type(exc).__name__})', r
        if result.returncode == 10 and f"SAPOTE_R_MISSING:{package}" in result.stdout:
            return 'UNAVAILABLE', f'R package {package} unavailable; render integration unverified', r
        if result.returncode != 0:
            return 'UNVERIFIED', f'R package probe unverified: {package} (rc={result.returncode})', r
    return 'READY', 'R packages available: ' + ', '.join(packages), r
