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
  - sealed Mamey Complete_Package dirs/zips (region GBKs are pulled from the packaged run).

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
import argparse, os, re, sys, tempfile, zipfile, shutil, glob, json

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


def detect_strictness_zip(zip_path):
    """Read the antiSMASH run JSON inside a ZIP and return its strictness, or None."""
    try:
        with zipfile.ZipFile(zip_path) as z:
            jsons = [m for m in z.namelist()
                     if m.lower().endswith(".json") and not os.path.basename(m).startswith("._")]
            # antiSMASH writes one big run JSON; scan largest-first for the field.
            for m in sorted(jsons, key=lambda n: -z.getinfo(n).file_size):
                head = z.read(m).decode("utf-8", "replace")
                s = _strictness_from_text(head)
                if s:
                    return s
    except Exception:
        return None
    return None


def detect_strictness_dir(d):
    """Best-effort strictness for a package/dir: look for an antiSMASH JSON beside the GBKs."""
    for j in glob.glob(os.path.join(d, "**", "*.json"), recursive=True):
        if os.path.basename(j).startswith("._"):
            continue
        try:
            s = _strictness_from_text(open(j, encoding="utf-8", errors="replace").read())
            if s:
                return s
        except Exception:
            continue
    return None


def stage_zip(zip_path, out, strain):
    n = 0
    with zipfile.ZipFile(zip_path) as z:
        for m in z.namelist():
            if os.path.basename(m).startswith("._"):
                continue  # skip macOS AppleDouble resource forks (non-UTF-8; crash BiG-SCAPE)
            if REGION.search(m):
                data = z.read(m)
                dst = os.path.join(out, f"{strain}_{os.path.basename(m)}")
                with open(dst, "wb") as fh:
                    fh.write(data)
                n += 1
    return n

def stage_dir(d, out, strain):
    n = 0
    for f in glob.glob(os.path.join(d, "**", "*.gbk"), recursive=True):
        if os.path.basename(f).startswith("._"):
            continue  # skip macOS AppleDouble resource forks
        if REGION.search(f):
            shutil.copy(f, os.path.join(out, f"{strain}_{os.path.basename(f)}"))
            n += 1
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
    a = ap.parse_args()

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
    manifest = []  # (strain, detected, state, n, source)
    flavors_staged = set()
    for it in items:
        strain = strain_from(it)
        strain = re.sub(r"_SapoteMamey.*$", "", strain)  # normalize package names -> strain id
        is_dir = os.path.isdir(it)
        if not is_dir and not it.lower().endswith(".zip"):
            continue

        # Ruled hard-excluded strains never stage (unless --allow-excluded): their BGCs must not
        # enter a GCF network. Skip-and-report, mirroring the strictness skip below.
        if strain in excluded:
            manifest.append((strain, "-", "SKIP_HARD_EXCLUDED", 0, it))
            emit(f"  {strain}: SKIP — ruled hard-excluded (OFFICIAL_DATA/exclusions.json); "
                  f"pass --allow-excluded to override", file=sys.stderr)
            continue

        detected = detect_strictness_zip(it) if not is_dir else detect_strictness_dir(it)
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

        try:
            n = stage_dir(it, a.out, strain) if is_dir else stage_zip(it, a.out, strain)
        except Exception as e:
            manifest.append((strain, detected or "UNKNOWN", f"ERROR:{type(e).__name__}", 0, it))
            emit(f"  {strain}: SKIP ({type(e).__name__}: {e})", file=sys.stderr)
            continue

        state = "STAGED" + ("(assumed_flavor)" if assumed else "")
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

    emit(f"\nstaged {total} region GBKs -> {a.out}", f"strictness manifest -> {mpath}", sep="\n")
    if len(flavors_staged) > 1:
        emit(f"** WARNING: staged a MIXED-strictness set: {sorted(flavors_staged)}. "
              f"A BiG-SCAPE clustering over this dir is NOT flavor-consistent. **", file=sys.stderr)
        return 2
    if flavors_staged:
        emit(f"single-flavor set: {sorted(flavors_staged)[0]}  (safe for one BiG-SCAPE run)")
    return 0 if total else 1

if __name__ == "__main__":
    sys.exit(main())
