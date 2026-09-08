"""Receipt-backed workflow registry for the optional Lab Quest interface.

The registry describes interface workflow only.  It intentionally separates
operator progress from the evidence-admission state and cannot self-issue owner
review or release approval.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from .lab_quest import EngineBinding, PackageSnapshot, contained_path, sha256_file, utc_now, verify_engine_binding_current


class WorkflowState(StrEnum):
    INPUT_STAGED = "INPUT_STAGED"
    EXTRACTION_RECEIPTED = "EXTRACTION_RECEIPTED"
    PACKAGE_VALIDATED = "PACKAGE_VALIDATED"
    BLASTP_STATUS_RECEIPTED = "BLASTP_STATUS_RECEIPTED"
    MODE_B_SKELETON_RECEIPTED = "MODE_B_SKELETON_RECEIPTED"
    FIGURES_RECEIPTED = "FIGURES_RECEIPTED"
    HANDOFF_SEALED = "HANDOFF_SEALED"
    FAILED = "FAILED"


class EvidenceState(StrEnum):
    INPUT_STAGED = "INPUT_STAGED"
    EXTRACTED = "EXTRACTED"
    VALIDATED = "VALIDATED"
    BLASTP_INCOMPLETE = "BLASTP_INCOMPLETE"
    INTERPRETATION_PENDING = "INTERPRETATION_PENDING"
    OWNER_REVIEWED = "OWNER_REVIEWED"
    RELEASE_APPROVED = "RELEASE_APPROVED"


STATIONS: tuple[tuple[str, str, str], ...] = (
    ("INPUT", "Input", "Stage a contained antiSMASH ZIP and record its identity."),
    ("EXTRACTION", "Extraction", "Run the explicitly bound portable Mamey engine."),
    ("PACKAGE", "Package validation", "Validate a package and bind its manifest hash."),
    ("BLASTP", "BLASTP status", "Record availability/status; this does not manufacture homology results."),
    ("MODE_B", "Mode B skeleton", "Emit deterministic structure only; interpretation remains pending."),
    ("FIGURES_HANDOFF", "Figures and handoff", "Receipt-bound post-seal rendering and portable handoff."),
)

_TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.INPUT_STAGED: frozenset({WorkflowState.EXTRACTION_RECEIPTED, WorkflowState.FAILED}),
    WorkflowState.EXTRACTION_RECEIPTED: frozenset({WorkflowState.PACKAGE_VALIDATED, WorkflowState.FAILED}),
    WorkflowState.PACKAGE_VALIDATED: frozenset({WorkflowState.BLASTP_STATUS_RECEIPTED, WorkflowState.FAILED}),
    WorkflowState.BLASTP_STATUS_RECEIPTED: frozenset({WorkflowState.MODE_B_SKELETON_RECEIPTED, WorkflowState.FAILED}),
    WorkflowState.MODE_B_SKELETON_RECEIPTED: frozenset({WorkflowState.FIGURES_RECEIPTED, WorkflowState.FAILED}),
    WorkflowState.FIGURES_RECEIPTED: frozenset({WorkflowState.HANDOFF_SEALED, WorkflowState.FAILED}),
    WorkflowState.HANDOFF_SEALED: frozenset(),
    WorkflowState.FAILED: frozenset(),
}

_EVIDENCE_FOR_STATE: dict[WorkflowState, EvidenceState] = {
    WorkflowState.INPUT_STAGED: EvidenceState.INPUT_STAGED,
    WorkflowState.EXTRACTION_RECEIPTED: EvidenceState.EXTRACTED,
    WorkflowState.PACKAGE_VALIDATED: EvidenceState.VALIDATED,
    WorkflowState.BLASTP_STATUS_RECEIPTED: EvidenceState.BLASTP_INCOMPLETE,
    WorkflowState.MODE_B_SKELETON_RECEIPTED: EvidenceState.INTERPRETATION_PENDING,
    WorkflowState.FIGURES_RECEIPTED: EvidenceState.INTERPRETATION_PENDING,
    WorkflowState.HANDOFF_SEALED: EvidenceState.INTERPRETATION_PENDING,
    WorkflowState.FAILED: EvidenceState.INPUT_STAGED,
}

_RECEIPT_STATION_FOR_STATE: dict[WorkflowState, str] = {
    WorkflowState.INPUT_STAGED: "INPUT",
    WorkflowState.EXTRACTION_RECEIPTED: "EXTRACTION",
    WorkflowState.PACKAGE_VALIDATED: "PACKAGE",
    WorkflowState.BLASTP_STATUS_RECEIPTED: "BLASTP",
    WorkflowState.MODE_B_SKELETON_RECEIPTED: "MODE_B",
    WorkflowState.FIGURES_RECEIPTED: "FIGURES",
    WorkflowState.HANDOFF_SEALED: "HANDOFF",
}


@dataclass(frozen=True)
class WorkflowRun:
    run_id: str
    state: WorkflowState
    evidence_state: EvidenceState
    input_path: str
    input_sha256: str
    engine_binding_sha256: str
    package_path: str | None
    package_manifest_sha256: str | None
    events: tuple[dict[str, Any], ...]


class WorkflowRegistry:
    """Small JSON registry whose every state change points to a verified receipt."""

    schema = "mamey_lab_quest_registry_v2"

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).expanduser().resolve()
        self.path = contained_path(self.project_root, "lab_quest_outputs", "workflow_registry.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"schema": self.schema, "runs": []})

    def _read(self) -> dict[str, Any]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("schema") != self.schema or not isinstance(payload.get("runs"), list):
            raise ValueError("Lab Quest registry is malformed or has an unsupported schema")
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def _receipt_event(self, receipt: str | Path, target: WorkflowState) -> dict[str, Any]:
        path = Path(receipt).expanduser().resolve()
        try:
            path.relative_to(self.project_root)
        except ValueError as exc:
            raise ValueError("workflow receipt must be below the selected project root") from exc
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != "mamey_lab_quest_workflow_receipt_v2":
            raise ValueError("workflow receipt has an unsupported schema")
        if payload.get("status") != "PASS":
            raise ValueError("a failed receipt cannot unlock a Lab Quest workflow station")
        if payload.get("station") != _RECEIPT_STATION_FOR_STATE[target]:
            raise ValueError("workflow receipt station does not match requested state")
        binding_sha = str((payload.get("engine_binding") or {}).get("binding_sha256") or "")
        if not binding_sha:
            raise ValueError("workflow receipt lacks the bound engine identity")
        return {
            "created_utc": str(payload.get("created_utc") or utc_now()),
            "state": target.value,
            "evidence_state": _EVIDENCE_FOR_STATE[target].value,
            "receipt_path": str(path),
            "receipt_sha256": sha256_file(path),
            "station": str(payload.get("station") or ""),
            "engine_binding_sha256": binding_sha,
            "package": payload.get("package"),
        }

    def create_input_run(
        self,
        *,
        input_path: str | Path,
        receipt: str | Path,
        binding: EngineBinding,
        run_id: str | None = None,
    ) -> WorkflowRun:
        path = Path(input_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        event = self._receipt_event(receipt, WorkflowState.INPUT_STAGED)
        receipt_payload = json.loads(Path(receipt).read_text(encoding="utf-8"))
        bound = (receipt_payload.get("engine_binding") or {}).get("binding_sha256")
        if bound != binding.binding_sha256:
            raise ValueError("input receipt is bound to a different code tier")
        payload = self._read()
        run = {
            "run_id": run_id or str(uuid.uuid4()),
            "created_utc": utc_now(),
            "updated_utc": utc_now(),
            "state": WorkflowState.INPUT_STAGED.value,
            "evidence_state": EvidenceState.INPUT_STAGED.value,
            "input_path": str(path),
            "input_sha256": sha256_file(path),
            "engine_binding_sha256": binding.binding_sha256,
            "package_path": None,
            "package_manifest_sha256": None,
            "events": [event],
        }
        payload["runs"].append(run)
        self._write(payload)
        return self._as_run(run)

    def get(self, run_id: str) -> WorkflowRun:
        for run in self._read()["runs"]:
            if run.get("run_id") == run_id:
                return self._as_run(run)
        raise KeyError(run_id)

    @staticmethod
    def _as_run(run: dict[str, Any]) -> WorkflowRun:
        return WorkflowRun(
            run_id=str(run["run_id"]),
            state=WorkflowState(run["state"]),
            evidence_state=EvidenceState(run["evidence_state"]),
            input_path=str(run["input_path"]),
            input_sha256=str(run["input_sha256"]),
            engine_binding_sha256=str(run["engine_binding_sha256"]),
            package_path=run.get("package_path"),
            package_manifest_sha256=run.get("package_manifest_sha256"),
            events=tuple(run.get("events") or []),
        )

    def transition(self, run_id: str, target: WorkflowState, receipt: str | Path) -> WorkflowRun:
        payload = self._read()
        for run in payload["runs"]:
            if run.get("run_id") != run_id:
                continue
            current = WorkflowState(run["state"])
            if target not in _TRANSITIONS[current]:
                raise ValueError(f"invalid receipt-backed transition: {current.value} -> {target.value}")
            event = self._receipt_event(receipt, target)
            if event["engine_binding_sha256"] != run.get("engine_binding_sha256"):
                raise ValueError("workflow receipt is bound to a different portable code tier")
            package = event.get("package") or {}
            run["state"] = target.value
            run["evidence_state"] = _EVIDENCE_FOR_STATE[target].value
            run["updated_utc"] = utc_now()
            run["events"].append(event)
            if package:
                run["package_path"] = package.get("path")
                run["package_manifest_sha256"] = package.get("manifest_sha256")
            self._write(payload)
            return self._as_run(run)
        raise KeyError(run_id)

    def record_package_validation(self, run_id: str, snapshot: PackageSnapshot, receipt: str | Path) -> WorkflowRun:
        run = self.get(run_id)
        if run.state is not WorkflowState.EXTRACTION_RECEIPTED:
            raise ValueError("package validation requires an extraction receipt first")
        current_manifest = sha256_file(snapshot.package / "manifest.json")
        if current_manifest != snapshot.manifest_sha256:
            raise ValueError("package manifest changed while validation was being recorded")
        return self.transition(run_id, WorkflowState.PACKAGE_VALIDATED, receipt)

    def _validate_receipt_artifacts(self, payload: dict[str, Any]) -> None:
        """Recheck every receipt-declared output before restoring a saved run.

        A receipt hash proves that the recorded receipt has not drifted. It does
        not by itself prove that a post-seal artifact named by that receipt is
        still present or byte-identical. Keep those checks separate and fail
        closed before any saved-run station can unlock.
        """
        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, list):
            raise ValueError("stored workflow receipt has an invalid artifact list")
        for item in artifacts:
            if not isinstance(item, dict):
                raise ValueError("stored workflow receipt has an invalid artifact entry")
            raw_path = str(item.get("path") or "")
            if not raw_path:
                raise ValueError("stored workflow receipt artifact path is missing")
            artifact = Path(raw_path).expanduser().resolve()
            try:
                artifact.relative_to(self.project_root)
            except ValueError as exc:
                raise ValueError("stored workflow receipt artifact escapes the selected project root") from exc
            expected_sha = str(item.get("sha256") or "")
            if item.get("exists") is not True or len(expected_sha) != 64:
                raise ValueError("stored workflow receipt has an incomplete artifact binding")
            if not artifact.is_file():
                raise ValueError("stored workflow receipt artifact is missing; downstream stations remain locked")
            if sha256_file(artifact) != expected_sha:
                raise ValueError("stored workflow receipt artifact hash is stale; downstream stations remain locked")

    def _validate_receipt_chain(self, run: dict[str, Any], binding: EngineBinding) -> None:
        verify_engine_binding_current(binding)
        if run.get("engine_binding_sha256") != binding.binding_sha256:
            raise ValueError("stored run is bound to a different portable code tier")
        input_path = Path(str(run.get("input_path") or "")).resolve()
        try:
            input_path.relative_to(self.project_root)
        except ValueError as exc:
            raise ValueError("stored input ZIP escapes the selected project root") from exc
        if not input_path.is_file() or sha256_file(input_path) != run.get("input_sha256"):
            raise ValueError("stored input ZIP hash is stale; downstream stations remain locked")
        events = list(run.get("events") or [])
        state = WorkflowState(run["state"])
        required = [item for item in WorkflowState if item is not WorkflowState.FAILED]
        expected_states = required[: required.index(state) + 1]
        if [event.get("state") for event in events] != [item.value for item in expected_states]:
            raise ValueError("stored workflow receipt chain is incomplete or out of order")
        for event, expected_state in zip(events, expected_states, strict=True):
            receipt = Path(str(event.get("receipt_path") or "")).resolve()
            try:
                receipt.relative_to(self.project_root)
            except ValueError as exc:
                raise ValueError("stored workflow receipt escapes the selected project root") from exc
            if not receipt.is_file() or sha256_file(receipt) != event.get("receipt_sha256"):
                raise ValueError("stored workflow receipt hash is stale; downstream stations remain locked")
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            if (
                payload.get("schema") != "mamey_lab_quest_workflow_receipt_v2"
                or payload.get("status") != "PASS"
                or payload.get("station") != _RECEIPT_STATION_FOR_STATE[expected_state]
                or str((payload.get("engine_binding") or {}).get("binding_sha256") or "") != binding.binding_sha256
            ):
                raise ValueError("stored workflow receipt no longer supports the recorded state")
            self._validate_receipt_artifacts(payload)

    def load_last_validated_run(self, binding: EngineBinding) -> WorkflowRun:
        """Return the latest package-bearing run only after chain and manifest revalidation."""
        candidates = []
        for run in self._read()["runs"]:
            if run.get("package_path") and run.get("package_manifest_sha256"):
                candidates.append(run)
        if not candidates:
            raise ValueError("no receipt-backed validated package is available")
        latest = max(candidates, key=lambda item: str(item.get("updated_utc") or ""))
        self._validate_receipt_chain(latest, binding)
        package = Path(str(latest["package_path"])).resolve()
        try:
            package.relative_to(self.project_root)
        except ValueError as exc:
            raise ValueError("stored package escapes the selected project root") from exc
        current = sha256_file(package / "manifest.json")
        if current != latest["package_manifest_sha256"]:
            raise ValueError("stored package manifest hash is stale; downstream stations remain locked")
        return self._as_run(latest)

    def status_rows(self, run_id: str | None) -> list[dict[str, str]]:
        current = self.get(run_id) if run_id else None
        order = [state for state in WorkflowState if state is not WorkflowState.FAILED]
        current_index = order.index(current.state) if current and current.state in order else -1
        station_states = (
            WorkflowState.INPUT_STAGED,
            WorkflowState.EXTRACTION_RECEIPTED,
            WorkflowState.PACKAGE_VALIDATED,
            WorkflowState.BLASTP_STATUS_RECEIPTED,
            WorkflowState.MODE_B_SKELETON_RECEIPTED,
            WorkflowState.HANDOFF_SEALED,
        )
        return [
            {
                "station": station,
                "label": label,
                "quest_progress": (
                    "IN_PROGRESS"
                    if current and station == "FIGURES_HANDOFF" and current.state is WorkflowState.FIGURES_RECEIPTED
                    else "COMPLETE" if order.index(station_state) <= current_index else "LOCKED"
                ),
                "evidence_state": (
                    current.evidence_state.value
                    if current and (station_state is current.state or (station == "FIGURES_HANDOFF" and current.state is WorkflowState.FIGURES_RECEIPTED))
                    else "NOT_ADMITTED"
                ),
                "description": description,
            }
            for station_state, (station, label, description) in zip(station_states, STATIONS, strict=True)
        ]
