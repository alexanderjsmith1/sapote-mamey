#!/usr/bin/env python3
"""Reroot a Newick tree on one exact tip and emit a deterministic postflight receipt.

This is a neutral, post-compute provenance tool.  The caller chooses an outgroup tip;
the tool never chooses or evaluates one biologically.  It preserves the input, writes
one rooted Newick artifact, and records hashes, bytes, parameters, exact outgroup
resolution, tip-set parity, duplicate/near-duplicate labels, typed holds/errors, and
PASS / PASS_WITH_HOLDS / FAIL state in JSON.

Usage:
  python tools/reroot_postflight_receipt.py INPUT.tree \
    --outgroup Exact_tip_label \
    --rooted-output outputs/rooted.tree \
    --receipt outputs/rooted.receipt.json \
    --locator-root .

Biopython is required for Newick parsing/rerooting (install the ``bio`` or ``all``
extra).  Rooting is a computational transformation, not evidence of ancestry,
horizontal transfer, taxonomy, BGC function, expression, production, or activity.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import tempfile
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wbio import atomic_write_text  # noqa: E402


TOOL_VERSION = "1.0.0"
SCHEMA_VERSION = "sapote-mamey.reroot-postflight-receipt.v1"
CLAIM_CEILING = (
    "COMPUTATIONAL_ROOTING_AND_PROVENANCE_ONLY / NO PHYLOGENETIC_OR_"
    "TAXONOMIC_INTERPRETATION"
)

try:  # optional product dependency; failure is recorded as a typed receipt error
    import Bio
    from Bio import Phylo
except Exception as exc:  # pragma: no cover - exercised only in a no-bio environment
    Bio = None
    Phylo = None
    _BIO_IMPORT_DEBUG = f"{type(exc).__name__}: {exc}"
    _BIO_IMPORT_ERROR = "OPTIONAL_DEPENDENCY_IMPORT_REDACTED"
else:
    _BIO_IMPORT_DEBUG = ""
    _BIO_IMPORT_ERROR = ""


class ContractError(Exception):
    """Typed refusal which is safe to serialize into the receipt."""

    def __init__(self, code: str, message: str, detail: object = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


def file_identity(path: Path) -> dict:
    """Exact SHA-256/byte identity for one existing file."""
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def portable_locator(path: Path, locator_root: Path, role: str) -> str:
    """Return a caller-root-relative locator without serializing host paths."""
    try:
        relative = path.relative_to(locator_root)
    except ValueError as exc:
        raise ContractError(
            "LOCATOR_OUTSIDE_ROOT",
            "Every serialized artifact path must be inside the caller-supplied locator root",
            {"role": role, "locator_root_mode": "CALLER_SUPPLIED_NOT_SERIALIZED"},
        ) from exc
    return "." if relative == Path(".") else relative.as_posix()


def redacted_filesystem_detail(role: str, stage: str) -> dict:
    """Stable portable detail for a local filesystem failure."""
    return {
        "role": role,
        "stage": stage,
        "diagnostic": "LOCAL_FILESYSTEM_FAILURE_REDACTED",
    }


def write_temp_text(path: Path, text: str) -> Path:
    """Write a same-directory temporary text artifact without publishing it."""
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
    except BaseException:
        discard_temp(tmp_path)
        raise
    return tmp_path


def backup_file(path: Path) -> Path:
    """Make a byte-preserving, same-filesystem rollback copy of one existing file."""
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".rollback.tmp", dir=str(path.parent)
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        shutil.copy2(path, tmp_path)
    except BaseException:
        discard_temp(tmp_path)
        raise
    return tmp_path


def discard_temp(path: Path | None) -> None:
    """Best-effort cleanup for a private transaction temporary file."""
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def replace_temp(path: Path, target: Path) -> None:
    """Publish a same-directory temporary file while retaining target mode when present."""
    if target.exists():
        os.chmod(path, target.stat().st_mode & 0o7777)
    os.replace(path, target)


def preflight_parent(path: Path, role: str) -> None:
    """Ensure one target parent is creatable and writable before any commit."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.parent.is_dir():
            raise OSError("target parent is not a directory")
        probe = write_temp_text(path.parent / ".reroot-write-probe", "")
        discard_temp(probe)
    except OSError as exc:
        raise ContractError(
            f"{role.upper()}_PARENT_UNAVAILABLE",
            "Required artifact parent is unavailable for a transactional write",
            redacted_filesystem_detail(role, "PARENT_PREFLIGHT"),
        ) from exc


def preflight_target(path: Path, locator: str, role: str, exists_code: str, replace: bool) -> bool:
    """Reject unsafe existing targets before any output transaction begins."""
    if not path.exists():
        return False
    if path.is_dir():
        raise ContractError(
            f"{role.upper()}_TARGET_NOT_FILE",
            "Artifact target must be a file path",
            {"role": role, "locator": locator},
        )
    if not replace:
        raise ContractError(
            exists_code,
            "Artifact already exists; choose a new path or pass --replace",
            locator,
        )
    return True


def restore_or_remove_output(
    output_path: Path,
    output_identity: dict,
    backup_path: Path | None,
) -> bool:
    """Undo this invocation only when the published output still matches it."""
    try:
        if not output_path.is_file() or file_identity(output_path) != output_identity:
            return False
        if backup_path is None:
            output_path.unlink()
        else:
            os.replace(backup_path, output_path)
        return True
    except OSError:
        return False


def commit_artifacts_transactionally(
    output_path: Path,
    receipt_path: Path,
    rooted_text: str,
    receipt: dict,
    output_preexisted: bool,
) -> None:
    """Publish rooted output and receipt, rolling back this invocation on failure."""
    output_tmp = receipt_tmp = backup_path = None
    output_committed = False
    output_identity = None
    try:
        output_tmp = write_temp_text(output_path, rooted_text)
        output_identity = file_identity(output_tmp)
        receipt["rooted_output"].update({"written": True, **output_identity})
        receipt["state"] = "PASS_WITH_HOLDS" if receipt["holds"] else "PASS"
        receipt_tmp = write_temp_text(
            receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        )
        if output_preexisted:
            backup_path = backup_file(output_path)
        replace_temp(output_tmp, output_path)
        output_tmp = None
        output_committed = True
        replace_temp(receipt_tmp, receipt_path)
        receipt_tmp = None
    except OSError as exc:
        rolled_back = False
        if output_committed and output_identity is not None:
            rolled_back = restore_or_remove_output(output_path, output_identity, backup_path)
            if rolled_back:
                backup_path = None
        receipt["rooted_output"].update({"written": False, "sha256": None, "bytes": None})
        raise ContractError(
            "ARTIFACT_TRANSACTION_FAILED",
            "Rooted output and receipt could not be committed as one governed transaction",
            {
                "diagnostic": "LOCAL_FILESYSTEM_FAILURE_REDACTED",
                "output_rollback": "COMPLETED" if rolled_back else "NOT_REQUIRED_OR_NOT_CONFIRMED",
            },
        ) from exc
    finally:
        discard_temp(output_tmp)
        discard_temp(receipt_tmp)
        discard_temp(backup_path)


def commit_receipt_only(receipt_path: Path, receipt: dict) -> None:
    """Persist a failure receipt only after no output transaction has started."""
    tmp_path = None
    try:
        tmp_path = write_temp_text(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        replace_temp(tmp_path, receipt_path)
        tmp_path = None
    finally:
        discard_temp(tmp_path)


def normalize_tip_label(label: str) -> str:
    """Conservative deterministic key used only to WARN about near duplicates.

    It is deliberately not an identity assertion: NFKC + casefold followed by removal
    of non-alphanumerics can reveal labels which differ only in punctuation/case.  The
    receipt exposes the algorithm and emits a HOLD; it never collapses tips.
    """
    folded = unicodedata.normalize("NFKC", label).casefold()
    return re.sub(r"[^a-z0-9]+", "", folded)


def duplicate_report(tips: list[str]) -> tuple[list[dict], list[dict]]:
    """Return exact duplicates and deterministic near-duplicate groups."""
    exact = [
        {"label": label, "count": count}
        for label, count in sorted(Counter(tips).items())
        if count > 1
    ]
    groups: dict[str, set[str]] = defaultdict(set)
    for tip in tips:
        groups[normalize_tip_label(tip)].add(tip)
    near = [
        {"normalization_key": key, "labels": sorted(labels)}
        for key, labels in sorted(groups.items())
        if key and len(labels) > 1
    ]
    return exact, near


def tip_set_report(input_tips: list[str], output_tips: list[str]) -> dict:
    """Compare tip multisets, so both loss/addition and multiplicity drift are visible."""
    before, after = Counter(input_tips), Counter(output_tips)
    removed = sorted((before - after).elements())
    added = sorted((after - before).elements())
    return {
        "input_count": len(input_tips),
        "output_count": len(output_tips),
        "parity": not removed and not added,
        "removed": removed,
        "added": added,
        "input_sorted_tip_sha256": hashlib.sha256(
            ("\n".join(sorted(input_tips)) + "\n").encode("utf-8")
        ).hexdigest(),
        "output_sorted_tip_sha256": hashlib.sha256(
            ("\n".join(sorted(output_tips)) + "\n").encode("utf-8")
        ).hexdigest(),
    }


def parse_tree_text(text: str):
    """Parse exactly one Newick tree or raise a typed malformed-input refusal."""
    if Phylo is None:
        raise ContractError(
            "BIOPYTHON_UNAVAILABLE",
            "Biopython is required for deterministic Newick parsing and rerooting",
            _BIO_IMPORT_ERROR,
        )
    try:
        tree = Phylo.read(io.StringIO(text), "newick")
    except Exception as exc:
        raise ContractError(
            "MALFORMED_NEWICK",
            "Input is not exactly one parseable Newick tree",
            f"{type(exc).__name__}: {exc}",
        ) from exc
    return tree


def tip_labels(tree) -> list[str]:
    tips = [tip.name for tip in tree.get_terminals()]
    if not tips:
        raise ContractError("NO_TIPS", "Newick tree contains no terminal tips")
    if any(name is None or not str(name).strip() for name in tips):
        raise ContractError("EMPTY_TIP_LABEL", "Every terminal tip must have a non-empty label")
    return [str(name) for name in tips]


def render_newick(tree) -> str:
    """Stable Newick serialization used for both output bytes and read-back QA."""
    handle = io.StringIO()
    Phylo.write(
        [tree],
        handle,
        "newick",
        plain=False,
        format_branch_length="%1.10f",
        format_confidence="%1.10g",
    )
    text = handle.getvalue()
    return text if text.endswith("\n") else text + "\n"


def base_receipt(args) -> dict:
    source = Path(__file__).resolve()
    return {
        "schema_version": SCHEMA_VERSION,
        "state": "FAIL",
        "claim_ceiling": CLAIM_CEILING,
        "tool": {
            "name": "reroot_postflight_receipt.py",
            "version": TOOL_VERSION,
            "source_sha256": file_identity(source)["sha256"],
            "source_bytes": source.stat().st_size,
            "python_version": platform.python_version(),
            "newick_engine": "Bio.Phylo" if Bio is not None else "UNAVAILABLE",
            "newick_engine_version": getattr(Bio, "__version__", None),
        },
        "parameters": {
            "outgroup_selector": args.outgroup,
            "outgroup_match_mode": "EXACT_TIP_LABEL",
            "rooting_operation": "Bio.Phylo.root_with_outgroup(single_terminal)",
            "output_format": "newick",
            "branch_length_format": "%1.10f",
            "confidence_format": "%1.10g",
            "replace_existing_outputs": bool(args.replace),
            "near_duplicate_algorithm": "NFKC_CASEFOLD_REMOVE_NONALPHANUMERIC_V1",
        },
        "locator_contract": {
            "mode": "CALLER_SUPPLIED_ROOT_RELATIVE_V1",
            "locator_root_serialization": "NOT_SERIALIZED",
            "absolute_locator_policy": "FORBIDDEN_IN_RECEIPT",
        },
        "input_tree": {
            "locator": None,
            "sha256": None,
            "bytes": None,
        },
        "requested_outgroup": {
            "selector": args.outgroup,
            "match_mode": "EXACT_TIP_LABEL",
        },
        "resolved_outgroup": {
            "state": "NOT_EVALUATED",
            "match_count": 0,
            "matches": [],
            "root_child_after_reroot": False,
        },
        "tip_checks": {
            "input_tips": [],
            "exact_duplicates": [],
            "near_duplicates": [],
            "tip_set_parity": None,
        },
        "rooted_output": {
            "requested_locator": None,
            "written": False,
            "sha256": None,
            "bytes": None,
        },
        "receipt_locator": None,
        "checks": [],
        "warnings": [],
        "holds": [],
        "errors": [],
    }


def add_check(receipt: dict, code: str, status: str, message: str, detail=None) -> None:
    item = {"code": code, "status": status, "message": message}
    if detail is not None:
        item["detail"] = detail
    receipt["checks"].append(item)


def fail(receipt: dict, exc: ContractError) -> None:
    item = {"code": exc.code, "message": exc.message}
    if exc.detail is not None:
        item["detail"] = exc.detail
    receipt["errors"].append(item)
    add_check(receipt, exc.code, "FAIL", exc.message, exc.detail)
    receipt["state"] = "FAIL"


def execute(args) -> tuple[int, dict, bool, bool, str | None]:
    """Run the governed computation without ever printing local paths by default.

    Returns exit code, receipt payload, whether a failure receipt may be safely written,
    whether the success transaction already wrote a receipt, and optional local-only
    diagnostic text.  The last value never enters the portable receipt.
    """
    receipt = base_receipt(args)
    failure_receipt_ready = False

    try:
        input_path = Path(args.input_tree).expanduser().resolve()
        output_path = Path(args.rooted_output).expanduser().resolve()
        receipt_path = Path(args.receipt).expanduser().resolve()
        locator_root = Path(args.locator_root).expanduser().resolve()
        if not locator_root.is_dir():
            raise ContractError(
                "LOCATOR_ROOT_INVALID",
                "Locator root must be an existing directory",
                {"locator_root_mode": "CALLER_SUPPLIED_NOT_SERIALIZED"},
            )
        receipt["input_tree"]["locator"] = portable_locator(input_path, locator_root, "input_tree")
        receipt["rooted_output"]["requested_locator"] = portable_locator(
            output_path, locator_root, "rooted_output"
        )
        receipt["receipt_locator"] = portable_locator(receipt_path, locator_root, "receipt")
        if len({input_path, output_path, receipt_path}) != 3:
            raise ContractError(
                "PATH_COLLISION",
                "Input tree, rooted output, and receipt must be three distinct paths",
            )
        output_preexisted = preflight_target(
            output_path,
            receipt["rooted_output"]["requested_locator"],
            "rooted_output",
            "ROOTED_OUTPUT_EXISTS",
            args.replace,
        )
        preflight_target(
            receipt_path,
            receipt["receipt_locator"],
            "receipt",
            "RECEIPT_EXISTS",
            args.replace,
        )
        preflight_parent(output_path, "rooted_output")
        preflight_parent(receipt_path, "receipt")
        failure_receipt_ready = True
        if not input_path.is_file():
            raise ContractError(
                "INPUT_NOT_FOUND", "Input tree is not a readable file", receipt["input_tree"]["locator"]
            )
        ident = file_identity(input_path)
        receipt["input_tree"].update(ident)

        tree = parse_tree_text(input_path.read_text(encoding="utf-8"))
        input_tips = tip_labels(tree)
        receipt["tip_checks"]["input_tips"] = sorted(input_tips)
        exact, near = duplicate_report(input_tips)
        receipt["tip_checks"]["exact_duplicates"] = exact
        receipt["tip_checks"]["near_duplicates"] = near
        if exact:
            raise ContractError(
                "DUPLICATE_TIP_LABEL",
                "Exact duplicate tip labels make identity and outgroup resolution ambiguous",
                exact,
            )
        add_check(receipt, "TIP_LABEL_UNIQUENESS", "PASS", "All exact tip labels are unique")
        if near:
            hold = {
                "code": "NEAR_DUPLICATE_TIP_LABEL",
                "message": "Tip labels collide under the documented conservative normalization; no tips were collapsed",
                "detail": near,
            }
            receipt["holds"].append(hold)
            add_check(receipt, hold["code"], "HOLD", hold["message"], near)
        else:
            add_check(receipt, "NEAR_DUPLICATE_TIP_LABEL", "PASS", "No deterministic near-duplicate groups detected")

        matches = [tip for tip in tree.get_terminals() if tip.name == args.outgroup]
        receipt["resolved_outgroup"].update(
            {
                "state": "RESOLVED_UNIQUE" if len(matches) == 1 else (
                    "MISSING" if not matches else "AMBIGUOUS"
                ),
                "match_count": len(matches),
                "matches": [tip.name for tip in matches],
            }
        )
        if not matches:
            raise ContractError(
                "OUTGROUP_MISSING",
                "Exact outgroup selector matches no terminal tip",
                {"requested": args.outgroup, "available_tips": sorted(input_tips)},
            )
        if len(matches) != 1:
            raise ContractError(
                "OUTGROUP_AMBIGUOUS",
                "Exact outgroup selector must resolve to exactly one terminal tip",
                {"requested": args.outgroup, "match_count": len(matches)},
            )
        add_check(receipt, "OUTGROUP_RESOLUTION", "PASS", "Exact selector resolved one terminal tip")

        tree.root_with_outgroup(matches[0])
        rooted_text = render_newick(tree)
        reread = parse_tree_text(rooted_text)
        output_tips = tip_labels(reread)
        parity = tip_set_report(input_tips, output_tips)
        receipt["tip_checks"]["tip_set_parity"] = parity
        if not parity["parity"]:
            raise ContractError(
                "TIP_SET_CHANGED",
                "Rerooted output does not preserve the input tip multiset",
                parity,
            )
        add_check(receipt, "TIP_SET_PARITY", "PASS", "Rerooted output preserves the exact tip multiset", parity)

        root_matches = [
            child for child in reread.root.clades
            if child.is_terminal() and child.name == args.outgroup
        ]
        is_root_child = len(root_matches) == 1
        receipt["resolved_outgroup"]["root_child_after_reroot"] = is_root_child
        if not is_root_child:
            raise ContractError(
                "OUTGROUP_NOT_ROOT_CHILD",
                "Resolved outgroup is not a direct child of the rooted output root",
                args.outgroup,
            )
        add_check(receipt, "ROOTED_TOPOLOGY", "PASS", "Resolved outgroup is a direct child of the output root")

        commit_artifacts_transactionally(
            output_path, receipt_path, rooted_text, receipt, output_preexisted
        )
        return 0, receipt, failure_receipt_ready, True, None
    except ContractError as exc:
        fail(receipt, exc)
        return 1, receipt, failure_receipt_ready, False, None
    except Exception as exc:  # fail closed; preserve local detail only behind explicit opt-in
        fail(
            receipt,
            ContractError(
                "UNEXPECTED_TOOL_ERROR",
                "Unexpected error while producing the reroot/postflight contract",
                {"diagnostic": "LOCAL_EXCEPTION_REDACTED"},
            ),
        )
        return 1, receipt, failure_receipt_ready, False, f"{type(exc).__name__}: {exc}"


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_tree", help="one input Newick tree; never modified")
    ap.add_argument("--outgroup", required=True, help="exact terminal-tip label selected by the caller")
    ap.add_argument("--rooted-output", required=True, help="new rooted Newick output path")
    ap.add_argument("--receipt", required=True, help="deterministic JSON receipt path")
    ap.add_argument(
        "--locator-root",
        required=True,
        help="existing root used to serialize all receipt locators as portable relative paths; never serialized",
    )
    ap.add_argument(
        "--replace",
        action="store_true",
        help="atomically replace existing rooted output/receipt; default is fail-closed",
    )
    ap.add_argument(
        "--local-debug",
        action="store_true",
        help="emit local nonportable diagnostics to stderr only; never serialized in receipts",
    )
    return ap


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    code, receipt, failure_receipt_ready, receipt_written, local_detail = execute(args)
    if code and failure_receipt_ready:
        try:
            receipt_path = Path(args.receipt).expanduser().resolve()
            commit_receipt_only(receipt_path, receipt)
            receipt_written = True
        except OSError as exc:
            local_detail = f"{type(exc).__name__}: {exc}"
            receipt_written = False
    error_code = receipt["errors"][-1]["code"] if receipt["errors"] else "NONE"
    receipt_locator = receipt["receipt_locator"] if receipt_written else "NOT_WRITTEN"
    sys.stdout.write(f"{receipt['state']} code={error_code} receipt={receipt_locator}\n")
    if receipt["rooted_output"]["written"]:
        sys.stdout.write(f"rooted_output={receipt['rooted_output']['requested_locator']}\n")
    if args.local_debug and local_detail:
        sys.stderr.write(f"LOCAL_NONPORTABLE_DIAGNOSTIC detail={local_detail}\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
