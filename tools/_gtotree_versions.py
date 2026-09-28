"""_gtotree_versions.py — the one list of GToTree versions the phylo tools accept.

The planner (`plan_gtotree_iqtree.py`), the execution gate (`gtotree_execution_gate.py`) and
`docs/GTOTREE_WORKFLOW.md` used to name three different versions (1.8.16, 1.8.19 or 2.0.x, and
1.8.19), so no version passed all three. Both tools now read this module; the doc states the same list.

- 1.8.19 is the production version of the established 138-marker Actinobacteria workflow.
- 2.0.x is admitted (v9.7.432 added native v2 support), but its marker set is not assumed comparable
  with 1.8.19; a v2 tree is not pooled with 1.8.19 trees without the documented migration.
- 1.8.16 and anything else are refused. 1.8.16 also carries the interactive-prompt hang fixed in 1.8.19.
"""
import re

ACCEPTED_GTOTREE_VERSIONS_TEXT = ("1.8.19", "2.0.x")
ACCEPTED_GTOTREE_VERSIONS = re.compile(r"(?:^|\D)(?:1\.8\.19|2\.0\.\d+)(?:\D|$)")


def accepted(version_text) -> bool:
    """True when the version string names an accepted GToTree (e.g. 'GToTree v1.8.19', '2.0.0')."""
    return bool(ACCEPTED_GTOTREE_VERSIONS.search(str(version_text or "")))
