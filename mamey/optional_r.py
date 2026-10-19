"""Offline, bounded admission for optional R renderer packages."""
from __future__ import annotations
import re
import shutil
import subprocess

TREE_RENDER_PACKAGES = ('ape', 'ggtree', 'ggplot2', 'aplot', 'treeio', 'patchwork')


def r_package_status(packages=('ggtree',), executable=None, timeout=10):
    """Return (state, message, Rscript); READY, UNAVAILABLE or UNVERIFIED."""
    if isinstance(packages, str):
        raise ValueError('R packages must be a sequence of package names, not a string')
    packages = tuple(packages)
    r = executable or shutil.which('Rscript')
    if not r:
        return 'UNAVAILABLE', 'Rscript unavailable; R integration unverified', None
    if not packages:
        return 'UNVERIFIED', 'No R package profile selected; readiness not measured', r
    for package in packages:
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9.]*', package):
            raise ValueError('invalid R package name')
        try:
            result = subprocess.run([r, '-e', f'if (!requireNamespace("{package}", quietly=TRUE)) {{cat("SAPOTE_R_MISSING:{package}\\n"); quit(status=10L)}}; cat("SAPOTE_R_READY:{package}\\n"); quit(status=0L)'],
                                    capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 'UNVERIFIED', f'R package probe unverified: {package} ({type(exc).__name__})', r
        if result.returncode == 10 and f"SAPOTE_R_MISSING:{package}" in result.stdout:
            return 'UNAVAILABLE', f'R package {package} unavailable; render integration unverified', r
        if result.returncode != 0:
            return 'UNVERIFIED', f'R package probe unverified: {package} (rc={result.returncode})', r
        if f"SAPOTE_R_READY:{package}" not in result.stdout.splitlines():
            return 'UNVERIFIED', f'R package probe did not confirm namespace: {package}; verify the selected Rscript executable', r
    return 'READY', 'R namespace probes passed (rendering unverified): ' + ', '.join(packages), r
