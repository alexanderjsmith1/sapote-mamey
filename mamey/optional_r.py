"""Offline, bounded admission for optional R renderer packages."""
from __future__ import annotations
import re
import shutil
import subprocess

TREE_RENDER_PACKAGES = ('ape', 'ggtree', 'ggplot2', 'aplot', 'treeio', 'patchwork')

# R figure groups: one list for doctor, the R installer and the tests (tests/test_456_r_figure_groups.py keeps
# bundle_support/install_r_figure_packages.R in step). "core" serves every R figure: the shared minimum-text helper
# loads svglite, systemfonts and xml2. Each other group adds one figure family; a missing one is not an error.
R_FIGURE_GROUPS = {
    'core': ('ggplot2', 'ggtext', 'jsonlite', 'scales', 'dplyr', 'patchwork', 'ggrepel', 'svglite', 'systemfonts', 'xml2'),
    'trees': ('ape', 'ggtree', 'treeio', 'aplot', 'phangorn'),
    'bioassay': ('tidyr', 'png'),
    'extras': ('ragg', 'ggchicklet'),
}
R_GROUP_ADDS = {
    'core': 'every R figure',
    'trees': 'phylogenetic tree figures',
    'bioassay': 'bioassay panels',
    'extras': 'genus-composition PNGs (ragg) and rounded class-group bars (ggchicklet)',
}


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


def r_group_status(executable=None, timeout=30):
    """Probe every R_FIGURE_GROUPS package in one Rscript call.

    Returns (state, {group: missing packages}, Rscript). state is READY (the probe ran), UNAVAILABLE (no Rscript) or
    UNVERIFIED (the probe failed); the dict is empty unless the probe ran."""
    r = executable or shutil.which('Rscript')
    if not r:
        return 'UNAVAILABLE', {}, None
    names = sorted({p for group in R_FIGURE_GROUPS.values() for p in group})
    code = 'for (p in c(' + ','.join(f'"{p}"' for p in names) + ')) cat("SAPOTE_R", p, requireNamespace(p, quietly=TRUE), "\\n")'
    try:
        result = subprocess.run([r, '-e', code], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return 'UNVERIFIED', {}, r
    seen = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == 'SAPOTE_R':
            seen[parts[1]] = parts[2] == 'TRUE'
    if result.returncode != 0 or set(seen) != set(names):
        return 'UNVERIFIED', {}, r
    return 'READY', {g: [p for p in pkgs if not seen[p]] for g, pkgs in R_FIGURE_GROUPS.items()}, r


def r_group_report(executable=None):
    """doctor lines as (ok, text): one per R figure group, or one line when R cannot be probed."""
    state, missing, _ = r_group_status(executable)
    if state == 'UNAVAILABLE':
        return [(False, 'Rscript not found: R figures are unavailable (docs/PREREQUISITES.md, "R figure stack")')]
    if state != 'READY':
        return [(False, 'R figure packages not measured: the Rscript probe failed')]
    lines = []
    for group, gone in missing.items():
        if not gone:
            lines.append((True, f'R {group} packages ✓ ({R_GROUP_ADDS[group]})'))
        else:
            fix = 'Rscript bundle_support/install_r_figure_packages.R' + ('' if group == 'core' else f' --require {group}')
            lines.append((False, f'R {group} packages missing ({", ".join(gone)}): {R_GROUP_ADDS[group]} unavailable; run {fix}'))
    return lines
