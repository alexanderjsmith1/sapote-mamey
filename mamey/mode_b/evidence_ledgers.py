"""Mode B evidence and missing-parts ledgers (v9.7.143a).

v9.7.151 (60-file bunny-hop #2): pandas became an undocumented hard
dependency here because §28 (Evidence provenance ledger) is mandatory in
the §1–§48 contract enforced by `modeb_structure_gate`. PREREQUISITES.md
does not list pandas; a user following the documented install path would
hit a hard `RuntimeError` from `_frame()` when building any ledger
programmatically. (The Mode B markdown itself never requires pandas —
§28 is written as prose + a markdown table. The hard-crash only hits
callers using the Python builders below.)

Fix: `_frame()` now returns a pandas `DataFrame` when pandas is available,
and falls back to a lightweight `_RowList` (a list subclass with `.columns`
and basic DataFrame-shaped attrs) when it isn't. Common iteration / `len`
/ JSON-roundtrip patterns work the same in both modes. Anything that
calls pandas-specific methods (`.iloc`, `.merge`, `.to_excel`) on the
result will fail loudly with `AttributeError` rather than silently
swallowing the missing-dep case.

PREREQUISITES.md updated to note pandas is required for the optional
DataFrame builders here in addition to the mamey-native figure set.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Any


class _RowList(list):
    """Drop-in fallback for pd.DataFrame when pandas is unavailable.

    Quacks like a DataFrame for the operations callers in this codebase
    perform: iteration over rows, `len()`, `.columns`, and reading
    individual fields by key. Does NOT implement pandas-specific methods;
    callers wanting `.iloc` / `.merge` / `.to_excel` must install pandas
    (the regular path). Marker attribute `_no_pandas_fallback = True` lets
    diagnostic code surface the fallback in receipts.
    """
    _no_pandas_fallback = True

    def __init__(self, rows: list[dict[str, Any]], columns: list[str]):
        super().__init__(rows)
        self.columns = list(columns)

    def to_dict(self, orient: str = "records") -> list[dict[str, Any]]:
        if orient == "records":
            return [dict(r) for r in self]
        raise NotImplementedError(
            "_RowList.to_dict only supports orient='records'; install "
            "pandas for full DataFrame semantics.")

    def __repr__(self) -> str:
        return f"_RowList(rows={len(self)}, columns={self.columns})"


def _frame(rows: list[dict[str, Any]], cols: list[str]):
    """Return a pandas DataFrame when pandas is available, else a
    `_RowList` fallback. The fallback is deliberate — §28 ledger
    construction must never hard-crash on a missing optional dep."""
    try:
        import pandas as pd  # type: ignore
        return pd.DataFrame(rows, columns=cols)
    except ImportError:
        return _RowList(rows, cols)


def build_missing_parts_ledger(components: Iterable[Mapping[str, Any]]):
    """Create a missing-parts ledger with the canonical columns."""

    cols = ["expected_component", "present", "where", "evidence", "missing_or_uncertain", "notes"]
    rows = []
    for comp in components:
        row = {c: comp.get(c, "") for c in cols}
        rows.append(row)
    return _frame(rows, cols)


def build_evidence_ledger(claims: Iterable[Mapping[str, Any]]):
    """Create a claim/evidence ledger with conservative claim-safety fields."""

    cols = ["claim", "evidence_type", "evidence_detail", "strength", "claim_allowed", "claim_safety_note"]
    rows = []
    for claim in claims:
        row = {c: claim.get(c, "") for c in cols}
        rows.append(row)
    return _frame(rows, cols)


def build_user_action_queue(actions: Iterable[Mapping[str, Any]]):
    """Create a prioritized next-action queue."""

    cols = ["priority", "action", "why", "input_needed", "expected_output_after_action"]
    rows = []
    for action in actions:
        row = {c: action.get(c, "") for c in cols}
        rows.append(row)
    df = _frame(rows, cols)
    # v9.7.151: pandas path uses sort_values; fallback path sorts the
    # underlying list-of-dicts in place. Same observable order.
    if hasattr(df, "sort_values") and "priority" in getattr(df, "columns", []):
        return df.sort_values("priority")
    if isinstance(df, _RowList) and "priority" in df.columns:
        df.sort(key=lambda r: r.get("priority", ""))
    return df
