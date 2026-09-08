"""Release QA integration for legacy matrix and dual-LLM handoff gates."""

from __future__ import annotations

from pathlib import Path
import json
import os
import warnings
from typing import Any

from .legacy_feature_gate import write_legacy_gate_outputs
from .llm_handoff import write_handoff_outputs

def _relpath(value: str, *, start: Path) -> str:
    try:
        if not isinstance(value, str):
            return value
        if not value:
            return value
        p = Path(value)
        if p.is_absolute():
            rel = os.path.relpath(str(p), start=str(start))
            # PC-6 (v9.7.253 audit): on Windows cross-drive paths relpath cannot relativize and
            # returns an absolute path, so the receipt would silently carry an absolute path — the
            # exact thing this function exists to prevent. Surface it instead of hiding it.
            if os.path.isabs(rel):
                warnings.warn(
                    f"release_qa: could not relativize {value!r} against {start!r}; "
                    "receipt will carry an absolute path",
                    stacklevel=2,
                )
            return rel
        return value
    except Exception as exc:
        warnings.warn(
            f"release_qa: path relativization failed for {value!r} ({exc}); "
            "receipt may carry an absolute path",
            stacklevel=2,
        )
        return value

def _relativize_nested_paths(value: Any, *, start: Path) -> Any:
    if isinstance(value, dict):
        return {key: _relativize_nested_paths(val, start=start) for key, val in value.items()}
    if isinstance(value, list):
        return [_relativize_nested_paths(item, start=start) for item in value]
    if isinstance(value, str):
        return _relpath(value, start=start)
    return value

def run_release_qa(
    bundle_root: Path,
    out_dir: Path,
    *,
    legacy_matrix: Path | None = None,
    create_default_legacy_matrix: bool = False,
    llm: str = "chatgpt",
    handshake_visible: bool = True,
    chatgpt_safe_mode_requested: bool = False,
) -> dict:
    bundle_root = bundle_root.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir_abs = out_dir.resolve()
    legacy_matrix = legacy_matrix or (out_dir_abs / "LEGACY_FEATURE_MATRIX.csv")
    legacy = write_legacy_gate_outputs(
        legacy_matrix,
        out_dir_abs / "legacy_feature_gate",
        create_default=create_default_legacy_matrix or not legacy_matrix.exists(),
    )
    handoff = write_handoff_outputs(
        bundle_root,
        out_dir_abs / "llm_handoff",
        llm=llm,
        handshake_visible=handshake_visible,
        chatgpt_safe_mode_requested=chatgpt_safe_mode_requested,
    )
    status = "PASS" if legacy["status"] == "PASS" and handoff["status"] == "PASS" else "FAIL"

    # Keep bundle_root as the anchor; all other emitted paths in RELEASE_QA_RECEIPT
    # are relative so the receipt is portable across machines and collaborators.
    receipt = {
        "status": status,
        "bundle_root": str(bundle_root),
        "out_dir": _relpath(str(out_dir_abs), start=bundle_root),
        "legacy_feature_gate": _relativize_nested_paths(legacy, start=out_dir_abs),
        "llm_handoff": _relativize_nested_paths(handoff, start=out_dir_abs),
    }
    receipt_path = out_dir_abs / "RELEASE_QA_RECEIPT.json"
    report = out_dir_abs / "RELEASE_QA_REPORT.md"

    receipt["receipt"] = _relpath(str(receipt_path), start=out_dir_abs)
    receipt["report"] = _relpath(str(report), start=out_dir_abs)
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    report.write_text(
        "\n".join([
            "# Release QA Report",
            "",
            f"Status: **{status}**",
            "",
            "## Legacy Feature Matrix Gate",
            "",
            f"- Status: {legacy['status']}",
            f"- Failures: {legacy['failure_count']}",
            f"- Receipt: `{receipt['legacy_feature_gate']['receipt']}`",
            "",
            "## Dual-LLM Handoff Receipt",
            "",
            f"- Status: {handoff['status']}",
            f"- Failures: {handoff['failure_count']}",
            f"- Receipt: `{receipt['llm_handoff']['receipt_json']}`",
        ])
    , encoding="utf-8")
    return receipt
