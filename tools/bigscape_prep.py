#!/usr/bin/env python3
"""bigscape_prep.py — stage antiSMASH region GBKs into a BiG-SCAPE input dir.

Extracts every antiSMASH `*region*.gbk` from a set of inputs and strain-prefixes each
filename so records from different strains never collide (SPAdes NODE_* names can clash)
and strain provenance stays visible in the BiG-SCAPE HTML and the SQLite `gbk.path`.

STRICTNESS-AWARE (v9.7.370, AMBER). antiSMASH is run at more than one detection strictness
across this cohort (loose / relaxed / strict), and a BiG-SCAPE clustering is only valid when
every input region comes from the SAME strictness — a loose region for one strain vs a relaxed
region for another are not comparable, and mixing them silently corrupts the GCF families.
Strictness is recorded ONLY in the antiSMASH run JSON inside each ZIP; the region GBK itself
does NOT carry it, so once GBKs are loose in a directory their flavor is unrecoverable. This
tool therefore:
  * detects each ZIP's strictness from its antiSMASH JSON,
  * stages ONLY the strains whose strictness matches --strictness (skips + loudly reports the
    rest), and
  * writes a STRICTNESS_MANIFEST.tsv into the output dir recording the detected strictness,
    staged/skipped state, and region count for every input — the provenance that a directory
    of GBKs can no longer carry on its own.
A mixed-flavor input can no longer form by accident: --strictness is required unless you pass
--allow-mixed (which still records every flavor in the manifest and prints a loud warning).

Inputs may be:
  - raw antiSMASH output ZIPs (one per strain; strain ID = zip stem), and/or
  - sealed Sapote-Mamey package directories/ZIPs (region GBKs are pulled from the packaged run).

Usage:
  python bigscape_prep.py --inputs <dir-of-zips|zip...> --strictness loose  --out bigscape_input_loose/
  python bigscape_prep.py --inputs <dir-of-zips|zip...> --strictness relaxed --out bigscape_input_relaxed/
  python bigscape_prep.py --inputs runs/ --from-packages --strictness loose --out bigscape_input/

CLAIM-SAFETY: this is a staging/provenance tool; it makes no biological claim. A "strictness
mismatch" means an input was produced under a different antiSMASH detection setting, nothing
about the strain's biology. Judgment deferred.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
from bigscape_input_decontam_guard import removed_contig_ids  # noqa: E402
import argparse, os, re, sys, tempfile, zipfile, shutil, glob, json, csv, hashlib

REGION = re.compile(r"region\d+\.gbk$", re.I)
VALID_STRICTNESS = ("loose", "relaxed", "strict")


def _hard_excluded() -> set:
    """Read the exclusion owner strictly before staging any files."""
    _here = _os.path.dirname(_os.path.abspath(__file__))
    _sys.path.insert(0, _os.path.dirname(_here))
    from mamey.exclusions import load_exclusions
    return set(load_exclusions(strict=True)["hard_excluded"])


def strain_from(name: str) -> str:
    b = os.path.basename(name)
    b = re.sub(r"\.(zip|tar\.gz|tgz)$", "", b, flags=re.I)
    return b


def _strictness_from_text(text: str):
    """Pull the first '"strictness": "<flavor>"' out of an antiSMASH JSON blob."""
    m = re.search(r'"strictness"\s*:\s*"([a-z]+)"', text)
    return m.group(1) if m and m.group(1) in VALID_STRICTNESS else None


# Returned when an input's JSON files declare more than one strictness (DREL-049).
CONFLICTING = "CONFLICTING"


def _one_strictness(found):
    """One declared flavor, CONFLICTING when declarations disagree, or None when there are none."""
    flavors = set(found)
    if len(flavors) > 1:
        return CONFLICTING
    return flavors.pop() if flavors else None


def detect_strictness_zip(zip_path):
    """Read every antiSMASH JSON inside a ZIP and return its strictness, CONFLICTING, or None."""
    found = []
    try:
        with zipfile.ZipFile(zip_path) as z:
            jsons = [m for m in z.namelist()
                     if m.lower().endswith(".json") and not os.path.basename(m).startswith("._")]
            for m in jsons:
                s = _strictness_from_text(z.read(m).decode("utf-8", "replace"))
                if s:
                    found.append(s)
    except Exception:
        return None
    return _one_strictness(found)


def detect_strictness_dir(d):
    """Strictness for a package/dir from its antiSMASH JSONs: one flavor, CONFLICTING, or None."""
    found = []
    for j in glob.glob(os.path.join(d, "**", "*.json"), recursive=True):
        if os.path.basename(j).startswith("._"):
            continue
        try:
            s = _strictness_from_text(open(j, encoding="utf-8", errors="replace").read())
            if s:
                found.append(s)
        except Exception:
            continue
    return _one_strictness(found)


def _stage_region(data, destination, strain, source_locator, minimum, excluded_regions, written=None, roster=None):
    n_cds = len(re.findall(rb"(?m)^     CDS +", data))
    if minimum and n_cds < minimum:
        excluded_regions.append(dict(strain=strain, source_locator=source_locator,
            source_sha256=hashlib.sha256(data).hexdigest(), n_cds=n_cds,
            min_query_genes=minimum, identity_state="SOURCE_RECORD_ONLY_ALIAS_UNBOUND"))
        return 0
    if os.path.exists(destination):
        raise ValueError("STAGING_COLLISION: duplicate destination basename")
    with open(destination, "wb") as handle:
        handle.write(data)
    if written is not None:
        written.append(destination)
    if roster is not None:
        region = re.search(r"(region\d+)\.gbk$", source_locator, re.I)
        roster.append({"strain": strain, "member_path": source_locator, "member_bytes": len(data),
                       "member_sha256": hashlib.sha256(data).hexdigest(),
                       "record_id": _record_id(source_locator), "region": region.group(1) if region else "",
                       "staged_file": os.path.basename(destination)})
    return 1


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_id(name):
    """antiSMASH names region files <record id>.regionNNN.gbk."""
    return re.sub(r"\.region\d+\.gbk$", "", os.path.basename(name))


def stage_zip(zip_path, out, strain, min_query_genes=0, excluded_regions=None, drop_contigs=None, dropped=None,
              written=None, roster=None):
    excluded_regions = [] if excluded_regions is None else excluded_regions
    n = 0
    with zipfile.ZipFile(zip_path) as z:
        for member in z.namelist():
            if not os.path.basename(member).startswith("._") and REGION.search(member):
                if drop_contigs and _record_id(member) in drop_contigs:
                    if dropped is not None:
                        dropped.append((strain, _record_id(member), member))
                    continue
                destination = os.path.join(out, f"{strain}_{os.path.basename(member)}")
                n += _stage_region(z.read(member), destination, strain, member,
                                   min_query_genes, excluded_regions, written, roster)
    return n


def stage_dir(d, out, strain, min_query_genes=0, excluded_regions=None, drop_contigs=None, dropped=None,
              written=None, roster=None):
    excluded_regions = [] if excluded_regions is None else excluded_regions
    n = 0
    for source in sorted(glob.glob(os.path.join(d, "**", "*.gbk"), recursive=True)):
        if not os.path.basename(source).startswith("._") and REGION.search(source):
            if drop_contigs and _record_id(source) in drop_contigs:
                if dropped is not None:
                    dropped.append((strain, _record_id(source), os.path.relpath(source, d)))
                continue
            with open(source, "rb") as handle:
                data = handle.read()
            n += _stage_region(data, os.path.join(out, f"{strain}_{os.path.basename(source)}"),
                               strain, os.path.relpath(source, d), min_query_genes, excluded_regions, written, roster)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True, help="dir of zips/pkgs and/or individual zips")
    ap.add_argument("--out", required=True)
    ap.add_argument("--from-packages", action="store_true",
                    help="inputs are sealed Mamey package dirs/zips, not raw antiSMASH zips")
    ap.add_argument("--strictness", choices=VALID_STRICTNESS,
                    help="stage ONLY inputs of this antiSMASH strictness; others are skipped and "
                         "reported. Required unless --allow-mixed.")
    ap.add_argument("--allow-mixed", action="store_true",
                    help="stage regardless of strictness (still recorded in the manifest). "
                         "Use only when you have verified the inputs are single-flavor by other means.")
    ap.add_argument("--assume-strictness", choices=VALID_STRICTNESS,
                    help="for inputs whose strictness can't be detected (e.g. bare GBK dirs with no "
                         "antiSMASH JSON), treat them as this flavor. Recorded as ASSUMED in the manifest.")
    ap.add_argument("--allow-excluded", action="store_true",
                    help="stage even ruled hard-excluded strains (OFFICIAL_DATA/exclusions.json). "
                         "Default: they are skipped and reported. Use only with a documented reason.")
    ap.add_argument("--min-query-genes", type=int, default=0,
                    help="opt-in minimum CDS count for explicitly named query strains; 0 disables")
    ap.add_argument("--query-strain", action="append", default=[],
                    help="exact staged query strain ID; repeat for each query. Other strains are never filtered")
    ap.add_argument("--drop-contigs", action="append", default=[], metavar="STRAIN=TSV",
                    help="drop this strain's regions on contigs listed in TSV (first column = record id, "
                         "or clade_decontam.py's contig_bins.tsv keep == 0 rows), "
                         "e.g. contigs removed by a decontamination; repeat per strain. Written to DROPPED_CONTIG_REGIONS.tsv")
    ap.add_argument("--allow-zero-drop", action="append", default=[], metavar="STRAIN",
                    help="explicitly permit zero matching regions for this drop-list strain after review")
    a = ap.parse_args()
    drop = {}
    for spec in a.drop_contigs:
        d_strain, sep, d_path = spec.partition("=")
        if not d_strain or not sep or not os.path.isfile(d_path):
            ap.error(f"--drop-contigs needs STRAIN=existing.tsv, got {spec!r}")
        if d_strain in drop:
            ap.error(f"duplicate --drop-contigs strain {d_strain!r}; provide one list per strain")
        try:
            drop[d_strain] = removed_contig_ids(d_path)
        except ValueError as exc:
            ap.error(str(exc))
        if not drop[d_strain]:
            ap.error(f"--drop-contigs for {d_strain!r} has no contig IDs")
    if set(a.allow_zero_drop) - set(drop):
        ap.error("--allow-zero-drop requires a matching --drop-contigs strain")
    dropped = []
    if a.min_query_genes < 0 or (a.min_query_genes and not a.query_strain):
        ap.error("--min-query-genes must be nonnegative and requires explicit --query-strain values")
    small_regions = []

    try:
        excluded = set() if a.allow_excluded else _hard_excluded()
    except (ImportError, OSError, ValueError) as exc:
        ap.error(f"exclusion policy unavailable: {exc}")

    if not a.strictness and not a.allow_mixed:
        ap.error("refusing to stage a possibly-mixed-strictness input: pass --strictness "
                 "{loose|relaxed|strict}, or --allow-mixed if you have verified single-flavor by other means.")

    if os.path.isdir(a.out) and os.listdir(a.out):
        ap.error("refusing non-empty staging output; choose a fresh output directory")
    os.makedirs(a.out, exist_ok=True)
    items = []
    for inp in a.inputs:
        if os.path.isdir(inp):
            items += sorted(glob.glob(os.path.join(inp, "*.zip")))
            items += [p for p in sorted(glob.glob(os.path.join(inp, "*"))) if os.path.isdir(p)]
        else:
            items.append(inp)

    total = 0
    input_errors = []  # DREL-034: requested inputs that could not be read
    empty_inputs = []  # inputs read and admitted that contributed no region GBK
    members_roster = []  # one row per staged region file: source and member hashes, record id, region
    manifest = []  # (strain, detected, state, n, source)
    flavors_staged = set()
    for it in items:
        strain = strain_from(it)
        strain = re.sub(r"_SapoteMamey.*$", "", strain)  # normalize package names -> strain id
        # v9.7.431: sanitise unsafe filename characters before staging. A duplicate-copy artifact
        # like "AS-XXX (1).zip" would otherwise prefix all of its regions with "AS-XXX (1)_",
        # which strain_from_gbk_name() cannot parse -- it returns the full stem, creating phantom
        # strains. Strip the " (N)" / " copy" duplicate suffix first, then map any remaining
        # non-safe chars (spaces, parens) to "_". Log the rename so it is visible in the staging
        # run log and in the STRICTNESS_MANIFEST (the strain column shows the sanitised id).
        _orig_strain = strain
        strain = re.sub(r"\s+\(\d+\)$", "", strain)             # strip " (N)" duplicate-copy suffix
        strain = re.sub(r"\s+copy$", "", strain, flags=re.I)        # strip " copy" duplicate suffix
        strain = re.sub(r"[^A-Za-z0-9._-]", "_", strain)            # map remaining unsafe chars to "_"
        if strain != _orig_strain:
            emit(f"  [sanitized strain id] {_orig_strain!r} -> {strain!r}", file=sys.stderr)
        is_dir = os.path.isdir(it)
        # DREL-034: a requested input must be accounted for. A missing path or an unreadable
        # ZIP is an input error (exit 2), not a silent drop or an "undetectable strictness" skip.
        if not os.path.exists(it):
            manifest.append((strain, "-", "ERROR:MISSING_INPUT", 0, it))
            input_errors.append(it)
            sys.stderr.write(f"  {strain}: ERROR — input not found: {it}\n")
            continue
        if not is_dir and not it.lower().endswith(".zip"):
            manifest.append((strain, "-", "SKIP_UNSUPPORTED_INPUT", 0, it))
            sys.stderr.write(f"  {strain}: SKIP — not a .zip or directory: {it}\n")
            continue
        if not is_dir and not zipfile.is_zipfile(it):
            manifest.append((strain, "-", "ERROR:UNREADABLE_ZIP", 0, it))
            input_errors.append(it)
            sys.stderr.write(f"  {strain}: ERROR — not a readable ZIP: {it}\n")
            continue

        # Ruled hard-excluded strains never stage (unless --allow-excluded): their BGCs must not
        # enter a GCF network. Skip-and-report, mirroring the strictness skip below.
        if strain in excluded:
            manifest.append((strain, "-", "SKIP_HARD_EXCLUDED", 0, it))
            emit(f"  {strain}: SKIP — ruled hard-excluded (OFFICIAL_DATA/exclusions.json); "
                  f"pass --allow-excluded to override", file=sys.stderr)
            continue

        detected = detect_strictness_zip(it) if not is_dir else detect_strictness_dir(it)
        if detected == CONFLICTING:
            # DREL-049: never let one member's declaration silently win over another's.
            manifest.append((strain, CONFLICTING, "ERROR:CONFLICTING_STRICTNESS", 0, it))
            input_errors.append(it)
            sys.stderr.write(f"  {strain}: ERROR — its JSON files declare different strictness values\n")
            continue
        assumed = False
        if detected is None and a.assume_strictness:
            detected, assumed = a.assume_strictness, True

        # Decide whether to stage this input.
        if a.strictness and not a.allow_mixed:
            if detected is None:
                manifest.append((strain, "UNKNOWN", "SKIP_UNDETECTABLE", 0, it))
                emit(f"  {strain}: SKIP — strictness undetectable (no antiSMASH JSON); "
                      f"pass --assume-strictness to force", file=sys.stderr)
                continue
            if detected != a.strictness:
                manifest.append((strain, detected + ("(assumed)" if assumed else ""),
                                 f"SKIP_WRONG_FLAVOR(!={a.strictness})", 0, it))
                emit(f"  {strain}: SKIP — {detected} != requested {a.strictness}", file=sys.stderr)
                continue

        written = []
        input_roster = []
        filtered_before = len(dropped) + len(small_regions)
        try:
            minimum = a.min_query_genes if strain in set(a.query_strain) else 0
            n = (stage_dir if is_dir else stage_zip)(it, a.out, strain, minimum, small_regions,
                                                     drop.get(strain), dropped, written, input_roster)
        except Exception as e:
            # DREL-032: a failed input must not leave part of itself staged. The output started
            # empty, so every file it wrote in this run is its own; remove them, and fail the run.
            left = []
            for path in written:
                try:
                    os.remove(path)
                except OSError as rm_exc:
                    left.append(f"{path} ({rm_exc})")
            if left:
                sys.stderr.write(f"  {strain}: could not remove partly staged file(s): {'; '.join(left)}\n")
            manifest.append((strain, detected or "UNKNOWN", f"ERROR:{type(e).__name__}", 0, it))
            input_errors.append(it)
            emit(f"  {strain}: ERROR ({type(e).__name__}: {e}); removed {len(written)} partly staged file(s)",
                 file=sys.stderr)
            continue

        # Only an input that staged completely contributes roster rows (a failed input was rolled back above).
        source_sha = "" if is_dir else _file_sha256(it)
        for row in input_roster:
            members_roster.append({"source": it, "source_sha256": source_sha, **row})
        state = "STAGED" + ("(assumed_flavor)" if assumed else "")
        if not n:
            # An input that contributed no region GBK is not STAGED. Say whether operator filters
            # removed its regions or none were found. Neither is evidence of biological absence.
            filtered = len(dropped) + len(small_regions) - filtered_before
            state = "EMPTY_ALL_REGIONS_FILTERED" if filtered else "EMPTY_NO_REGION_GBKS"
            empty_inputs.append((strain, state))
            sys.stderr.write(f"  {strain}: EMPTY — contributed 0 region GBKs ({state}); "
                             "a staging result, not a biological absence\n")
        manifest.append((strain, detected or "UNKNOWN", state, n, it))
        if n:
            flavors_staged.add(detected or "UNKNOWN")
            emit(f"  {strain}: {n} region GBKs [{detected or 'UNKNOWN'}]")
            total += n

    # Write the provenance manifest — the flavor record a bare GBK dir cannot carry.
    mpath = os.path.join(a.out, "STRICTNESS_MANIFEST.tsv")
    with open(mpath, "w") as fh:
        fh.write("strain\tdetected_strictness\tstate\tn_regions\tsource\n")
        for row in sorted(manifest):
            fh.write("\t".join(str(x) for x in row) + "\n")

    # Source-to-member roster. It binds each staged file to its source and bytes; it carries no BGC alias
    # and no antiSMASH version, so a full strain / node / region / alias identity still needs a crosswalk.
    roster_fields = ["strain", "source", "source_sha256", "member_path", "member_bytes", "member_sha256",
                     "record_id", "region", "staged_file"]
    with open(os.path.join(a.out, "STAGED_MEMBERS.tsv"), "w", newline="", encoding="utf-8") as fh:
        from mamey.csv_safety import SafeDictWriter as _RosterWriter
        writer = _RosterWriter(fh, roster_fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(members_roster)

    if drop:
        with open(os.path.join(a.out, "DROPPED_CONTIG_REGIONS.tsv"), "w", encoding="utf-8") as fh:
            fh.write("strain\trecord\tsource_member\n")
            for row in dropped:
                fh.write("\t".join(row) + "\n")
        staged = {row[0] for row in manifest
                  if str(row[2]).startswith("STAGED") or row[2] == "EMPTY_ALL_REGIONS_FILTERED"}
        for d_strain in sorted(drop):
            hits = sum(1 for row in dropped if row[0] == d_strain)
            emit(f"  {d_strain}: dropped {hits} region(s) on {len(drop[d_strain])} listed contig(s)", file=sys.stderr)
        missing = sorted(set(drop) - staged)
        if missing:
            emit(f"** --drop-contigs named strain(s) that were not staged: {missing}. "
                 f"Check the strain id; nothing was dropped for them. **", file=sys.stderr)
            return 2
        zero = sorted(s for s in drop if s in staged and not any(row[0] == s for row in dropped)
                      and s not in a.allow_zero_drop)
        if zero:
            emit(f"** ZERO_DROP_REFUSED: no regions matched removed contigs for {zero}. "
                 "Check assembly and contig IDs, or pass --allow-zero-drop STRAIN after review. **",
                 file=sys.stderr)
            return 2

    if a.min_query_genes:
        from mamey.csv_safety import SafeDictWriter
        with open(os.path.join(a.out, "EXCLUDED_SMALL_QUERY_FRAGMENTS.tsv"), "w", newline="", encoding="utf-8") as handle:
            writer = SafeDictWriter(handle, ["strain", "source_locator", "source_sha256", "n_cds", "min_query_genes", "identity_state"], delimiter="\t", lineterminator="\n")
            writer.writeheader(); writer.writerows(small_regions)
        with open(os.path.join(a.out, "QUERY_FILTER.json"), "w", encoding="utf-8") as handle:
            json.dump({"query_strains": sorted(set(a.query_strain)), "min_query_genes": a.min_query_genes,
                       "excluded_source_records": len(small_regions),
                       "ceiling": "Operator-selected input scope; source archives unchanged; no biological absence claim"}, handle, indent=2)
    emit(f"\nstaged {total} region GBKs -> {a.out}", f"strictness manifest -> {mpath}", sep="\n")
    if empty_inputs:
        sys.stderr.write(f"** EMPTY_INPUTS: {len(empty_inputs)} admitted input(s) contributed 0 region GBKs: "
                         + ", ".join(f"{s_} ({st})" for s_, st in empty_inputs)
                         + f". They are not STAGED; see {mpath}. **\n")
    if len(flavors_staged) > 1:
        emit(f"** WARNING: staged a MIXED-strictness set: {sorted(flavors_staged)}. "
              f"A BiG-SCAPE clustering over this dir is NOT flavor-consistent. **", file=sys.stderr)
        return 2
    if input_errors:
        sys.stderr.write(f"** INPUT_ERRORS: {len(input_errors)} requested input(s) could not be read or staged; see "
                         f"ERROR rows in {mpath}. The staged set does not cover the request. **\n")
        return 2
    if flavors_staged:
        emit(f"single-flavor set: {sorted(flavors_staged)[0]}  (safe for one BiG-SCAPE run)")
    return 0 if total else 1

if __name__ == "__main__":
    sys.exit(main())
