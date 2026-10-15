"""Shared GToTree admission, probe and argv policy for existing phylogeny tools.

Admitted version families remain 1.8.19 and 2.0.x. Interface admission also
requires successful version/help probes and the version-specific option roster;
it does not certify an installed environment or marker-set equivalence.

Native source contracts: v1.8.19 tag c4e526449d5933339d2f0d2f9318de9e82eaef12;
v2 rewrite bc70746e6c01a1d44596b2adfba8e4e6717fe70d (reports 2.0.0).
The latter uses -s for detailed help; -h intentionally omits some needed flags.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

# The planner and its execution/readback consumers share these contracts.
GOVERNED_LAYOUT = {
    "kind": "GOVERNED_RUNNER_V1",
    "workdir_relative": "outputs/governed_run",
    "gtotree_relative": "outputs/governed_run/gtotree",
    "status_relative": "outputs/governed_run/run_status.json",
}


def safe_tip_label(value, fallback):
    """Existing planner normalization; never infer taxonomy or type material."""
    label = re.sub(r"[\t\r\n]+", " ", value).strip() or fallback
    return re.sub(r"[()*&^#$@!\\/|\[\]]", "_", label)


def plan_tip_rows(assemblies):
    """Derive labels/roles from scientific plan records, not the mapping file."""
    if not isinstance(assemblies, list) or not assemblies:
        raise ValueError("PLAN_ASSEMBLY_ROSTER")
    result = []
    for row in assemblies:
        if not isinstance(row, dict) or row.get("role") not in ("QUERY", "REFERENCE", "OUTGROUP"):
            raise ValueError("PLAN_TIP_ROLE_BINDING")
        if (any(not isinstance(row.get(k), str) for k in ("object_path", "label", "strain_id"))
                or not row["object_path"]):
            raise ValueError("PLAN_TIP_IDENTITY")
        label = safe_tip_label(row["label"], row["strain_id"])
        if not label or any(ch.isspace() or ch in "():,;[]'\"" for ch in label):
            raise ValueError("PLAN_TIP_IDENTITY")
        result.append((Path(row["object_path"]).name, label, row["role"]))
    if (len({r[0] for r in result}) != len(result) or len({r[1] for r in result}) != len(result)
            or sum(r[2] == "OUTGROUP" for r in result) != 1
            or not any(r[2] == "QUERY" for r in result)):
        raise ValueError("PLAN_TIP_ROLE_BINDING")
    return result


def mapping_input_keys(entries, version_text="1.8.19"):
    """Use version-specific native ingress keys without rewriting supplied paths.

    v2's GenomeData retains the exact provided path and derives a separate genome
    ID with the FASTA extension removed. Our v2 mapping uses only the former;
    basename-with-extension is not a supported substitute for an absolute input.
    v1 retains the existing basename contract.
    """
    selected = profile(version_text)
    if any(not isinstance(entry, str) or not entry or
           any(ch in entry for ch in "\t\r\n") for entry in entries):
        raise ValueError("GTOTREE_MAPPING_INPUT_IDENTITY")
    keys = ([Path(entry).name for entry in entries] if selected["major"] == 1
            else list(entries))
    if len(set(keys)) != len(keys):
        raise ValueError("GTOTREE_MAPPING_INPUT_IDENTITY")
    return keys


def plan_mapping_rows(assemblies, version_text):
    """Reconstruct mapping keys, labels and roles from the scientific manifest."""
    planned = plan_tip_rows(assemblies)
    keys = mapping_input_keys([row["object_path"] for row in assemblies], version_text)
    return [(key, label, role) for key, (_, label, role) in zip(keys, planned)]


def governed_paths(root, layout):
    """One explicit layout; no existence-based fallback or caller path escape."""
    if layout != GOVERNED_LAYOUT:
        raise ValueError("PLAN_GOVERNED_LAYOUT")
    root = Path(root).resolve(strict=True)
    return {key: root / value for key, value in layout.items() if key.endswith("_relative")}

ACCEPTED_GTOTREE_VERSIONS_TEXT = ("1.8.19", "2.0.x")
GTOTREE_BINS = ("GToTree", "gtotree")
ALIGNMENT_NAMES = ("aligned-SCGs.faa", "Aligned_SCGs.faa", "Aligned_SCGs_mod_names.faa")
# Compatibility export for consumers of a single banner. Multi-line admission
# must use accepted(), which rejects contradictory version declarations.
ACCEPTED_GTOTREE_VERSIONS = re.compile(
    r"\A\s*(?:GToTree\s+)?v?(?:1\.8\.19|2\.0\.\d+)\s*\Z", re.IGNORECASE
)
_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_BANNER = re.compile(r"^(?:GToTree\s+)?v?(\d+\.\d+\.\d+)$", re.IGNORECASE)
# Released GToTree 1.8.19 numbers its required inputs: "      2)  [-H <file>] location of ...". A numbered
# prefix ("2)") is a declaration like the "- " bullet; prose that merely mentions a flag still does not match.
_DECLARATION = re.compile(
    r"^\s*(?:-\s+|\d+\)\s+)?\[?\s*(-[A-Za-z])(?:\s*[,|]\s*(--[A-Za-z][\w-]*))?"
)
_COMMON_OPTIONS = ("-f", "-H", "-m", "-j", "-M", "-N", "-k", "-o")
PROBE_TEXT_LIMIT = 65536


def parse_version(version_text) -> str | None:
    """Read one unambiguous numeric banner (stdout and stderr may be combined).

    Repeated identical banners are harmless. Conflicting declarations, suffixes,
    or a GToTree-labelled line not in the documented banner format are refused.
    Unrelated warning lines cannot provide an alternate version by substring.
    """
    versions = set()
    for line in _ANSI.sub("", str(version_text or "")).splitlines():
        line = line.strip()
        if not line:
            continue
        match = _BANNER.fullmatch(line)
        if match:
            versions.add(match.group(1))
        elif re.search(r"\bGToTree\b", line, re.IGNORECASE) or re.match(r"^v?\d+\.\d+\.\d+", line):
            return None
    return next(iter(versions)) if len(versions) == 1 else None


def accepted(version_text) -> bool:
    version = parse_version(version_text)
    return bool(version and (version == "1.8.19" or re.fullmatch(r"2\.0\.\d+", version)))


def profile(version_text) -> dict:
    version = parse_version(version_text)
    if not accepted(version_text):
        raise ValueError("GTOTREE_VERSION: requires unambiguous 1.8.19 or 2.0.x")
    major = int(version.split(".")[0])
    return {
        "version": version, "major": major,
        "profile": "1.8.19" if major == 1 else "2.0.x",
        "help_argv": ["-h"] if major == 1 else ["-s"],
        "required_options": list(_COMMON_OPTIONS) + (["-n"] if major == 1 else []),
        # v2 concatenates through its Python owner, not the v1 helper executable.
        "required_helpers": (["hmmsearch", "prodigal", "muscle", "trimal", "gtt-cat-alignments"]
                             if major == 1 else ["prodigal", "muscle", "trimal"]),
        "mapping_contract": ("two_or_three_column_tsv_input_basename_to_label" if major == 1 else
                             "two_or_three_column_tsv_exact_provided_path_or_genome_id_to_label"),
    }


def declared_help_options(text) -> set[str]:
    """Read option declaration lines, not flag mentions buried in prose."""
    found = set()
    for line in _ANSI.sub("", str(text or "")).splitlines():
        match = _DECLARATION.match(line)
        if match:
            found.update(value for value in match.groups() if value)
    return found


def probe(binary, *, timeout=10, run=None) -> dict:
    """Version and detailed-interface probes only; no analysis or discovery job."""
    result = {
        "status": "MISSING" if not binary else "PROBE_FAILED", "path": binary,
        "version": None, "normalized_version": None, "profile": None,
        "version_exit": None, "help_exit": None, "help_argv": None,
        "help_contract": "NOT_CHECKED", "missing_help_tokens": [],
        "verified_interface": "HOLD_UNVERIFIED_VERSION",
    }
    if not binary:
        return result
    invoke = run or subprocess.run
    try:
        version = invoke([binary, "-v"], capture_output=True, text=True,
                         stdin=subprocess.DEVNULL, timeout=timeout, check=False)
        raw = ((version.stdout or "") + "\n" + (version.stderr or "")).strip()
        result.update(version=raw[:PROBE_TEXT_LIMIT], version_exit=version.returncode,
                      version_text_chars=len(raw))
        if len(raw) > PROBE_TEXT_LIMIT:
            result["error"] = "GTOTREE_PROBE_TEXT_LIMIT"
            return result
        if version.returncode != 0:
            result["error"] = "GTOTREE_VERSION_PROBE_EXIT"
            return result
        try:
            selected = profile(raw)
        except ValueError:
            result["error"] = "GTOTREE_VERSION"
            return result
        result.update(normalized_version=selected["version"], profile=selected["profile"],
                      major=selected["major"], help_argv=selected["help_argv"],
                      required_options=selected["required_options"],
                      required_helpers=selected["required_helpers"],
                      mapping_contract=selected["mapping_contract"])
        help_result = invoke([binary, *selected["help_argv"]], capture_output=True, text=True,
                             stdin=subprocess.DEVNULL, timeout=timeout, check=False)
        help_text = (help_result.stdout or "") + "\n" + (help_result.stderr or "")
        result["help_exit"] = help_result.returncode
        if len(help_text) > PROBE_TEXT_LIMIT:
            result["error"] = "GTOTREE_HELP_TEXT_LIMIT"
            return result
        missing = sorted(set(selected["required_options"]) - declared_help_options(help_text))
        result["missing_help_tokens"] = missing
        passed = help_result.returncode == 0 and not missing
        result.update(status="PRESENT" if help_result.returncode == 0 else "PROBE_FAILED",
                      help_contract="PASS" if passed else "HOLD_HELP_DRIFT",
                      verified_interface="PASS" if passed else "HOLD_HELP_DRIFT")
        if help_result.returncode != 0:
            result["error"] = "GTOTREE_HELP_PROBE_EXIT"
        return result
    except (OSError, subprocess.SubprocessError) as exc:
        result["error"] = type(exc).__name__
        return result


def command(binary, version_text, genome_list, hmm, threads, jobs, out_dir,
            *, mapping_file=None, keep_alignments=False) -> list[str]:
    """Common alignment-only argv. No implicit default threads or version guess."""
    selected = profile(version_text)
    for name, value in (("threads", threads), ("jobs", jobs)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("GTOTREE_RESOURCE: " + name + " must be a positive integer")
    argv = [str(binary), "-f", str(genome_list), "-H", str(hmm)]
    if mapping_file is not None:
        argv.extend(["-m", str(mapping_file)])
    argv.extend(["-j", str(jobs)])
    if selected["major"] == 1:
        argv.extend(["-n", str(threads)])
    argv.extend(["-M", str(threads), "-N"])
    if keep_alignments:
        argv.append("-k")
    return argv + ["-o", str(out_dir)]


def resource_contract(version_text, threads, jobs, *, verified_runtime=None, cpu_budget=None) -> dict:
    """Separate CLI controls from an admitted source-specific HMM CPU bound.

    No force override exists. A future v2 profile needs independently reviewed
    exact source/runtime binding before changing this resource admission.
    """
    selected = profile(version_text)
    for name, value in (("threads", threads), ("jobs", jobs)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("GTOTREE_RESOURCE: " + name + " must be a positive integer")
    common = {"profile": selected["profile"], "jobs": jobs, "muscle_threads": threads,
              "requested_threads_per_tree": threads, "native_execution_validated": False}
    if selected["major"] == 1:
        return dict(common, status="PASS_EXPLICIT_CLI_RESOURCE_BOUND", hmm_threads=threads,
                    maximum_parallel_search_threads=threads * jobs, hmm_control="-n",
                    source_profile="v1.8.19_cli_contract")
    if verified_runtime is not None:
        from _gtotree_runtime import require_verified
        return require_verified(verified_runtime).contract(selected["version"], threads, jobs, cpu_budget)
    return dict(common, status="HOLD_UNVERIFIED_V2_RESOURCE_PROFILE", hmm_threads=None,
                maximum_parallel_search_threads=None, hmm_control="NOT_EXPOSED_BY_REVIEWED_CLI",
                source_profile=None,
                reviewed_upstream_fact={"commit": "bc70746e6c01a1d44596b2adfba8e4e6717fe70d",
                    "owner": "gtotree/utils/misc/general.py::search_threads_per_genome",
                    "hardcoded_threads": 2,
                    "scope": "static source fact, not selected executable derivation"})
