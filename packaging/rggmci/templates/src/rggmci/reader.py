"""Construct standalone records from the engine-owned common region intake.

Geometry, products, ordering, deduplication and aliases are lifted from parsers.py.
Expected coordinate fallbacks share diagnostics; unexpected errors/refusals propagate.
"""
from __future__ import annotations

from pathlib import Path
from ._parsers import iter_region_core_inputs, project_rggmci_records
from ._records import BGCRecord


def read_regions(zip_path: str | Path) -> list[BGCRecord]:
    return [BGCRecord(**fields) for _, _, fields, _ in iter_region_core_inputs(zip_path)]
