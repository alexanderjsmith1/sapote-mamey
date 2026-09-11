"""Accessible optional local interface for receipt-governed Mamey workflows.

The application contains presentation and navigation only.  Each operator
action is delegated to the explicit portable engine binding and must produce a
receipt before it changes quest progress.  It never imports the historical Lab
Quest prototype or treats an animation, colour, rank, or visit as evidence.
"""
from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

import streamlit as st

from mamey.lab_quest import (
    CLAIM_CEILING,
    HISTORICAL_PROTOTYPE_STATUS,
    EngineBinding,
    PackageSnapshot,
    build_engine_command,
    build_run_command,
    build_station_command,
    contained_path,
    discover_packages,
    formal_review_markdown,
    load_package_snapshot,
    release_for_strain,
    resolve_engine_binding,
    resolve_project_root,
    run_bound_command,
    safe_display_text,
    safe_upload_name,
    station_artifact_paths,
    validate_strain_token,
    validate_package_with_bound_engine,
    write_engine_binding_receipt,
    write_run_receipt,
)
from mamey.lab_quest_registry import EvidenceState, STATIONS, WorkflowRegistry, WorkflowState
from mamey.project_catalog import ProjectCatalog


def _root() -> Path:
    """Require an operator-selected output/source root for every launch."""
    return resolve_project_root(os.environ.get("MAMEY_LAB_QUEST_ROOT"))


def _binding() -> EngineBinding:
    return resolve_engine_binding(
        os.environ.get("MAMEY_LAB_QUEST_CODE_TIER", ""),
        expected_bundle_version=os.environ.get("MAMEY_LAB_QUEST_EXPECT_BUNDLE", ""),
        expected_engine_version=os.environ.get("MAMEY_LAB_QUEST_EXPECT_ENGINE", ""),
    )


def _registry(root: Path) -> WorkflowRegistry:
    return WorkflowRegistry(root)


def _snapshot_from_run(run, root: Path) -> PackageSnapshot | None:
    if not run or not run.package_path:
        return None
    package = Path(run.package_path)
    try:
        package.relative_to(root)
    except ValueError:
        return None
    return load_package_snapshot(package)


def _display_provenance(binding: EngineBinding, root: Path, run, snapshot: PackageSnapshot | None) -> None:
    st.subheader("Bound provenance and admission state")
    rows = [
        ("Portable code-tier root", str(binding.code_tier)),
        ("Project/source-root binding", str(root)),
        ("Bundle / engine", f"{binding.bundle_version} / {binding.engine_version}"),
        ("Code-tier binding SHA-256", binding.binding_sha256),
        ("Quest workflow state", run.state.value if run else "NOT_STARTED"),
        ("Evidence/admission state", run.evidence_state.value if run else "NOT_ADMITTED"),
        ("Owner review", "NOT_ADMITTED_BY_INTERFACE"),
        ("Release approval", "NOT_ADMITTED_BY_INTERFACE"),
        ("Project catalog", "HASH_BOUND_PORTABLE_NAVIGATION_ONLY"),
    ]
    if run:
        rows.extend(
            [
                ("Run ID", run.run_id),
                ("Input ZIP SHA-256", run.input_sha256),
            ]
        )
    if snapshot:
        rows.extend(
            [
                ("Package manifest SHA-256", snapshot.manifest_sha256),
                ("Package validation", snapshot.validator_status),
                ("Run mode / release class", f"{snapshot.mode} / {snapshot.release}"),
                ("Privacy tier / assignment", f"{snapshot.privacy_tier} / {snapshot.privacy_assignment_state}"),
                ("Evidence date", snapshot.evidence_date_utc),
            ]
        )
    st.dataframe({"field": [row[0] for row in rows], "value": [row[1] for row in rows]}, hide_index=True, use_container_width=True)


def _display_progress(registry: WorkflowRegistry, run_id: str | None) -> None:
    st.subheader("Quest progress is separate from scientific evidence")
    rows = registry.status_rows(run_id)
    st.dataframe(rows, hide_index=True, use_container_width=True)
    st.caption("Progress means a receipt-backed interface step completed. It never means an interpretation was accepted.")


def _save_upload(root: Path, upload) -> Path:
    filename = safe_upload_name(upload.name)
    target = contained_path(root, "lab_quest_inputs", filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(upload.getvalue())
    return target


def _execution_receipt(
    *,
    root: Path,
    binding: EngineBinding,
    run,
    station: str,
    command: list[str],
    snapshot: PackageSnapshot | None = None,
    artifacts: tuple[Path, ...] = (),
) -> tuple[Path, subprocess.CompletedProcess[str]]:
    completed = run_bound_command(command)
    receipt = write_run_receipt(
        root,
        command,
        run.input_path,
        completed.returncode,
        completed.stdout,
        completed.stderr,
        binding,
        run_id=run.run_id,
        station=station,
        package_snapshot=snapshot,
        artifact_paths=artifacts,
    )
    return receipt, completed


def _show_command_result(completed: subprocess.CompletedProcess[str], receipt: Path) -> None:
    if completed.returncode == 0:
        st.success(f"Receipt recorded: {receipt}")
    else:
        st.error(f"Command exited {completed.returncode}; failed receipt recorded: {receipt}")
    transcript = (completed.stdout + "\n" + completed.stderr).strip()
    if transcript:
        st.code(transcript[-12000:], language="text")


def show_figure_with_alt_text(path: str | Path, alt_text: str) -> None:
    """Display a local figure only with a non-empty text alternative/caption."""
    figure = Path(path).resolve()
    alt = safe_display_text(alt_text, "figure text alternative", max_length=500)
    if not figure.is_file() or not alt:
        raise ValueError("figure display requires an existing local file and a non-empty text alternative")
    st.image(str(figure), caption=alt, use_container_width=True)


def _input_station(root: Path, binding: EngineBinding, registry: WorkflowRegistry) -> None:
    st.subheader("1. Input")
    st.write("Stage a portable antiSMASH ZIP below the selected project root. This creates a receipt; it does not run extraction.")
    upload = st.file_uploader("antiSMASH ZIP", type=["zip"], key="lq_upload")
    strain = st.text_input("Strain identifier", key="lq_strain")
    taxonomy = st.text_input("Taxonomy or placeholder", key="lq_taxonomy")
    source = st.text_input("Source or host context", key="lq_source")
    if st.button("Stage input and create receipt", type="primary"):
        try:
            if upload is None:
                raise ValueError("Select an antiSMASH ZIP first")
            clean_strain = validate_strain_token(strain)
            safe_display_text(taxonomy, "taxonomy")
            safe_display_text(source, "source")
            input_path = _save_upload(root, upload)
            provisional_id = str(uuid.uuid4())
            receipt = write_run_receipt(
                root,
                ["LAB_QUEST_STAGE_INPUT"],
                input_path,
                0,
                "Input staged below project root.",
                "",
                binding,
                run_id=provisional_id,
                station="INPUT",
                context={
                    "strain": clean_strain,
                    "taxonomy": taxonomy,
                    "source_context": source,
                    "release_class": release_for_strain(clean_strain),
                },
            )
            run = registry.create_input_run(
                input_path=input_path,
                receipt=receipt,
                binding=binding,
                run_id=provisional_id,
            )
            st.session_state["lq_run_id"] = run.run_id
            st.session_state["lq_strain_value"] = clean_strain
            st.session_state["lq_taxonomy_value"] = taxonomy
            st.session_state["lq_source_value"] = source
            st.success(f"Input staged as {run.run_id}. Release class: {release_for_strain(clean_strain)}.")
        except Exception as exc:
            st.error(str(exc))


def _extraction_station(root: Path, binding: EngineBinding, registry: WorkflowRegistry, run) -> None:
    st.subheader("2. Extraction")
    if not run or run.state is not WorkflowState.INPUT_STAGED:
        st.info("Unlocks after an input receipt is staged.")
        return
    strain = st.session_state.get("lq_strain_value", "")
    taxonomy = st.session_state.get("lq_taxonomy_value", "")
    source = st.session_state.get("lq_source_value", "")
    if st.button("Run bound Mamey gold extraction", type="primary"):
        try:
            command = build_run_command(
                binding=binding,
                project_root=root,
                input_zip=run.input_path,
                strain=strain,
                taxonomy=taxonomy,
                source=source,
            )
            receipt, completed = _execution_receipt(root=root, binding=binding, run=run, station="EXTRACTION", command=command)
            if completed.returncode == 0:
                registry.transition(run.run_id, WorkflowState.EXTRACTION_RECEIPTED, receipt)
            _show_command_result(completed, receipt)
        except Exception as exc:
            st.error(str(exc))


def _package_station(root: Path, binding: EngineBinding, registry: WorkflowRegistry, run) -> None:
    st.subheader("3. Package validation")
    if not run or run.state is not WorkflowState.EXTRACTION_RECEIPTED:
        st.info("Unlocks after an extraction receipt. A historical package must be imported through a staged run, not assumed current.")
        return
    catalog = ProjectCatalog(root)
    visibility = st.radio(
        "Package visibility",
        ["PUBLIC", "PRIVATE_PROJECT"],
        horizontal=True,
        help="PUBLIC is an explicit release allowlist. PRIVATE_PROJECT is an operator-only local view.",
    )
    try:
        catalogued = set(catalog.verified_packages(visibility))
    except ValueError as exc:
        # Do not silently rely on a stale entry.  A new package may still be
        # selected for its first validation and will then be registered anew.
        catalogued = set()
        st.warning(f"Existing project catalog is not current: {exc}")
    # Uncatalogued discovery is confined to the operator-only project view.
    # A PUBLIC widget receives only already hash-bound, explicitly PUBLIC rows;
    # private identifiers never reach its options or format function.
    discovered = set(discover_packages(root)) if visibility == "PRIVATE_PROJECT" else set()
    packages = sorted(catalogued | discovered)
    if not packages:
        st.warning("No candidate packages are available below the selected project root.")
        return
    selected = st.selectbox("Candidate package", packages, format_func=lambda item: str(item.relative_to(root)), key="lq_package")
    if st.button("Validate and bind package manifest", type="primary"):
        try:
            command, completed, snapshot = validate_package_with_bound_engine(
                binding=binding,
                project_root=root,
                package=selected,
            )
            if completed.returncode != 0 or snapshot is None:
                receipt = write_run_receipt(
                    root,
                    command,
                    run.input_path,
                    completed.returncode,
                    completed.stdout,
                    completed.stderr,
                    binding,
                    run_id=run.run_id,
                    station="PACKAGE",
                )
                _show_command_result(completed, receipt)
                return
            if snapshot.validator_status not in {"PASS", "PASS_WITH_ISSUES", "MAMEY_COMPLETE"}:
                raise ValueError(f"package validation does not unlock Lab Quest: {snapshot.validator_status}")
            receipt = write_run_receipt(
                root,
                command,
                run.input_path,
                0,
                completed.stdout,
                completed.stderr,
                binding,
                run_id=run.run_id,
                station="PACKAGE",
                package_snapshot=snapshot,
            )
            registry.record_package_validation(run.run_id, snapshot, receipt)
            catalog.register_package(snapshot.package)
            st.session_state["lq_package_path"] = str(selected)
            st.success(f"Validated and catalogued package manifest {snapshot.manifest_sha256}.")
        except Exception as exc:
            st.error(f"Package remained locked: {exc}")


def _command_station(root: Path, binding: EngineBinding, registry: WorkflowRegistry, run, snapshot: PackageSnapshot | None, station: str, target: WorkflowState, label: str) -> None:
    st.subheader(label)
    if not run or not snapshot:
        st.info("Unlocks after receipt-backed package validation.")
        return
    expected = {
        "BLASTP": WorkflowState.PACKAGE_VALIDATED,
        "MODE_B": WorkflowState.BLASTP_STATUS_RECEIPTED,
        "FIGURES": WorkflowState.MODE_B_SKELETON_RECEIPTED,
        "HANDOFF": WorkflowState.FIGURES_RECEIPTED,
    }[station]
    if run.state is not expected:
        st.info(f"Unlocks after {expected.value}.")
        return
    if st.button(f"Run {station} through bound engine", type="primary"):
        try:
            command = build_station_command(binding=binding, project_root=root, package=snapshot.package, station=station, run_id=run.run_id)
            artifacts = station_artifact_paths(
                project_root=root,
                package=snapshot.package,
                station=station,
                run_id=run.run_id,
            )
            receipt, completed = _execution_receipt(
                root=root,
                binding=binding,
                run=run,
                station=station,
                command=command,
                snapshot=snapshot,
                artifacts=artifacts,
            )
            if completed.returncode == 0:
                registry.transition(run.run_id, target, receipt)
            _show_command_result(completed, receipt)
        except Exception as exc:
            st.error(str(exc))


def main() -> None:
    st.set_page_config(page_title="Sapote-Mamey review", layout="wide")
    try:
        root = _root()
        binding = _binding()
        write_engine_binding_receipt(root, binding)
    except Exception as exc:
        st.error(f"Lab Quest refused to start: {exc}")
        st.stop()

    registry = _registry(root)
    run_id = st.session_state.get("lq_run_id")
    try:
        run = registry.get(run_id) if run_id else None
    except KeyError:
        run = None
    snapshot = _snapshot_from_run(run, root)

    with st.sidebar:
        st.subheader("Presentation")
        theme = st.radio("Theme", ["Arcade review", "Scientific review"], index=0)
        low_motion = st.checkbox("Low-motion mode (enforced)", value=True, disabled=True)
        st.caption("Native Streamlit controls support keyboard navigation. No workflow state is colour-only.")
        st.caption("The interface uses no animation-dependent status. A scientific-review download omits the Lab Quest persona and emoji.")
    title = "Lab Quest" if theme == "Arcade review" else "Sapote-Mamey scientific review"
    st.title(title)
    st.caption(f"Local optional interface · low motion: {'on' if low_motion else 'off'}")
    st.warning(CLAIM_CEILING)
    st.info(HISTORICAL_PROTOTYPE_STATUS)
    _display_provenance(binding, root, run, snapshot)
    if theme == "Scientific review":
        st.download_button(
            "Download scientific-review record",
            data=formal_review_markdown(binding=binding, project_root=root, run=run, snapshot=snapshot),
            file_name="sapote_mamey_scientific_review.md",
            mime="text/markdown",
        )
    if st.button("Load last receipt-backed validated package"):
        try:
            loaded = registry.load_last_validated_run(binding)
            # Re-run current validation and exact-identity construction before unlocking this session.
            load_package_snapshot(loaded.package_path or "")
            st.session_state["lq_run_id"] = loaded.run_id
            st.success(f"Loaded run {loaded.run_id} after manifest-hash and package validation checks.")
            st.rerun()
        except Exception as exc:
            st.error(f"No downstream station was unlocked: {exc}")
    _display_progress(registry, run.run_id if run else None)

    input_tab, extraction_tab, package_tab, blastp_tab, modeb_tab, figures_tab = st.tabs([item[1] for item in STATIONS])
    with input_tab:
        _input_station(root, binding, registry)
    with extraction_tab:
        _extraction_station(root, binding, registry, run)
    with package_tab:
        _package_station(root, binding, registry, run)
    with blastp_tab:
        _command_station(root, binding, registry, run, snapshot, "BLASTP", WorkflowState.BLASTP_STATUS_RECEIPTED, "4. BLASTP status")
    with modeb_tab:
        _command_station(root, binding, registry, run, snapshot, "MODE_B", WorkflowState.MODE_B_SKELETON_RECEIPTED, "5. Mode B skeleton")
    with figures_tab:
        _command_station(root, binding, registry, run, snapshot, "FIGURES", WorkflowState.FIGURES_RECEIPTED, "6a. Figures")
        refreshed = registry.get(run.run_id) if run else None
        _command_station(root, binding, registry, refreshed, snapshot, "HANDOFF", WorkflowState.HANDOFF_SEALED, "6b. Portable handoff")
        st.caption("Figures require text alternatives when shown in the interface. This screen does not create publication-ready outputs or scientific acceptance.")


if __name__ == "__main__":
    main()
