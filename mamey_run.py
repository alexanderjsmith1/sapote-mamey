#!/usr/bin/env python3
"""
Mamey Standalone ChatGPT Bundle runner.

Works without pip install — use this in ChatGPT, Colab, or any environment
where a previously installed version of mamey may be cached.

Usage:
    python mamey_run.py run --strain X --input-zip Y [options]
    python mamey_run.py run --strains A.zip B.zip C.zip --master master.xlsx
    python mamey_run.py validate ./path/to/package_dir
    python mamey_run.py run --help
"""
import sys
import os
import re
# Force the local mamey/ package to take precedence over any installed version.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)


def _build_id(stamp):
    """The line that actually distinguishes two cuts. `version=` is identical across a reseal;
    `build=` carries the build letter (…v97441b vs …v97441c), which is the whole point here."""
    if not stamp:
        return "?"
    lines = [ln.strip() for ln in stamp.splitlines() if ln.strip()]
    build = next((ln for ln in lines if ln.startswith("build=")), None)
    version = next((ln for ln in lines if ln.startswith("version=")), None)
    return " ".join(x for x in (version, build) if x) or lines[0]


def _cache_provenance_path():
    return os.path.join(_HERE, "mamey", "__pycache__", ".sapote_cut")


def _current_cut():
    """This tree's build identity. BUILD_STAMP changes on every cut AND on every reseal,
    where __version__/BUNDLE_VERSION do not -- 440a/440c and 441a/441b differ only here."""
    try:
        with open(os.path.join(_HERE, "BUILD_STAMP.txt"), encoding="utf-8") as handle:
            stamp = handle.read().strip()
    except OSError:
        return None
    return stamp or None            # empty/truncated stamp: stay out of the way, do not block


def _source_digest(root):
    """SHA-256 over every mamey/**/*.py path and its bytes, in sorted order.

    BUILD_STAMP names a cut; it does not prove the files are that cut's files. A module edited in
    place without a stamp change keeps the stamp, the version, and -- at the fixed 1980 mtime and
    the same size -- Python's own (mtime, size) check, so stale bytecode would execute past every
    other guard here. Hashing the source closes that. Measured on 9.7.442: 364 files, 7.4 MB,
    about 0.1 s warm.
    """
    import hashlib
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, "rb") as handle:
                    data = handle.read()
            except OSError:
                data = b"\0UNREADABLE\0"
            digest.update(os.path.relpath(path, root).encode("utf-8") + b"\0" + data + b"\0")
    return digest.hexdigest()


def _split_marker(text):
    """(build stamp, source digest or None) from a marker's text."""
    lines = (text or "").splitlines()
    source = next((ln[len("source="):] for ln in lines if ln.startswith("source=")), None)
    stamp = "\n".join(ln for ln in lines if not ln.startswith("source=")).strip()
    return stamp, source


def _refuse_external_bytecode_cache():
    """The bundle marker and purge do not cover Python's external pycache prefix."""
    if sys.pycache_prefix is None:
        return
    sys.stderr.write(
        "EXTERNAL_BYTECODE_CACHE_REFUSED: Python is reading bytecode outside this bundle.\n"
        "  This runner cannot bind or safely clear that cache to the current cut.\n"
        "  Start a new Python process without PYTHONPYCACHEPREFIX or -X pycache_prefix.\n")
    raise SystemExit(2)


def _refuse_symlinked_bytecode_cache():
    """A linked cache directory escapes the in-bundle walk but Python still reads its .pyc."""
    cache_root = os.path.join(_HERE, "mamey")
    if os.path.islink(cache_root):
        linked = cache_root
    else:
        linked = None
        for dirpath, dirnames, _ in os.walk(cache_root):
            linked = next((os.path.join(dirpath, name) for name in dirnames
                           if name == "__pycache__" and os.path.islink(os.path.join(dirpath, name))), None)
            if linked:
                break
    if linked:
        sys.stderr.write(
            "SYMLINKED_BYTECODE_CACHE_REFUSED: cache path escapes the in-bundle bytecode scan.\n"
            f"  linked path: {linked}\n"
            "  Replace the link with a regular directory before running this bundle.\n")
        raise SystemExit(2)


def _dirs_holding_bytecode(root):
    """Cache directories under `root` that still contain .pyc, sorted.

    An emptied but undeletable __pycache__ is functionally purged: no bytecode is left to serve
    a foreign cut. Only surviving .pyc matter, so both the refusal and the purge report ask this
    one question instead of each walking the tree with its own rule.
    """
    found = []
    for dirpath, _, files in os.walk(root):
        if any(name.endswith(".pyc") for name in files):
            found.append(dirpath)
    return sorted(found)


def _refuse_foreign_bytecode():
    """Refuse a __pycache__ that was compiled from a DIFFERENT cut of this bundle.

    _refuse_stale_bytecode() below compares the imported engine against its own source, which
    catches a version bump. It cannot catch a same-version reseal: a reseal changes module
    content while __version__ and BUNDLE_VERSION stay put, so the source/imported comparison
    agrees and stale bytecode is served anyway (demonstrated: a byte-size-identical module edit
    at the 1980 stamp is invisible to Python's (mtime, size) check).

    So stamp the cache with the cut that produced it and compare on the next run. Cheap: one
    small file. Precise: fires only when the tree's BUILD_STAMP actually changed. Deletes
    nothing -- pass --purge-bytecode to clear the caches, or remove them yourself.
    """
    cut = _current_cut()
    if cut is None:
        return                      # no BUILD_STAMP: not our failure to diagnose
    marker = _cache_provenance_path()
    cache_root = os.path.join(_HERE, "mamey")
    if not os.path.isdir(cache_root):
        return
    try:
        with open(marker, encoding="utf-8") as handle:
            seen = handle.read().strip()
    except OSError:
        seen = None
    source = _source_digest(cache_root)
    seen_stamp, seen_source = _split_marker(seen)
    if seen is not None and seen_stamp == cut:
        if seen_source == source:
            return
        # Same cut, different source: a module was changed in place without a stamp change, or
        # the marker predates source hashing. The cache was built from files that are no longer
        # there, so treat it exactly like an unmarked cache: clear it, recheck, re-mark.
        sys.stderr.write(
            "SOURCE_DRIFT_DETECTED: mamey/ source differs from the source this cache was built from,\n"
            "  under the same BUILD_STAMP. Treating the cache as untrusted.\n")
        seen = None
    if seen is None:
        # A cache made before this marker existed has no trustworthy cut identity. Do not
        # bless its bytecode with the current stamp: it may be from a same-version reseal.
        # Refusing outright is too blunt, because this runner is not the only thing that writes
        # mamey/__pycache__. The test suite does, 196 tools/ scripts import mamey, and
        # tools/intake_harness.py imports mamey and THEN shells out to this runner -- so on a
        # pristine tree the documented batch route refused its own inputs. Bytecode is derived
        # data, so clear the untrusted cache instead of sending the operator away: the stale code
        # still never executes, and the whole cost is one recompile.
        #
        # Fail closed if the clear does not take. `_dirs_holding_bytecode` is `1246F6CE`'s, and
        # their finding is why this re-checks: rmtree runs with ignore_errors=True, so a cache the
        # filesystem will not release is skipped silently. Proceeding then would import exactly
        # the bytecode this branch exists to distrust.
        unbound = _dirs_holding_bytecode(cache_root)
        if unbound:
            _purge_bytecode(cache_root, quiet=True)
            still = _dirs_holding_bytecode(cache_root)
            if still:
                sys.stderr.write(
                    "UNBOUND_BYTECODE_REFUSED: .pyc with no cut marker could not be cleared.\n")
                for path in still:
                    sys.stderr.write(f"  unbound cache: {path}\n")
                sys.stderr.write(
                    "  Check write permission on each directory and on its parent, then remove\n"
                    "  them yourself, or:\n"
                    f"    find {_HERE!r} -name __pycache__ -type d -prune -exec rm -rf {{}} +\n")
                raise SystemExit(2)
            sys.stderr.write(
                "UNBOUND_BYTECODE_CLEARED: %d cache director%s under mamey/ carried no cut marker,\n"
                "  so their bytecode could not be trusted and was removed before import.\n"
                "  Only derived bytecode was deleted; this run recompiles it.\n"
                % (len(unbound), "y" if len(unbound) == 1 else "ies"))
        try:                        # clean first run: mark before imports create bytecode
            os.makedirs(os.path.dirname(marker), exist_ok=True)
            with open(marker, "w", encoding="utf-8") as handle:
                handle.write(cut + "\nsource=" + source + "\n")
        except OSError:
            pass
        return
    sys.stderr.write(
        "FOREIGN_BYTECODE_REFUSED: __pycache__ under this bundle was compiled from a different cut.\n"
        f"  cache was built by : {_build_id(seen_stamp)}\n"
        f"  this tree is       : {_build_id(cut)}\n"
        "  A same-version reseal changes module content while the version string does not, so\n"
        "  neither the version check below nor Python's (mtime, size) check can see it.\n"
        "  Remediation: re-run with --purge-bytecode, or:\n"
        f"    find {_HERE!r} -name __pycache__ -type d -prune -exec rm -rf {{}} +\n"
        "  Nothing has been deleted for you.\n")
    raise SystemExit(2)


def _purge_bytecode(root=None, quiet=False):
    """Clear every __pycache__ under `root` (the whole bundle by default) and report what went.

    `quiet` is for the internal caller in `_refuse_foreign_bytecode`, which re-checks the result
    itself and prints a message specific to that case.

    rmtree runs with ignore_errors=True, so a directory the filesystem refuses to give up is
    skipped without raising. Counting attempts would then report a purge that did not happen,
    and both refusals above send the operator here as their remediation -- so a silent failure
    reads as "purged N" and the very next run refuses again, with no way out. Check each target
    after the attempt and name the ones that still hold bytecode.
    """
    removed, kept = 0, []
    for dirpath, dirnames, _ in os.walk(root or _HERE):
        for name in list(dirnames):
            if name == "__pycache__":
                import shutil
                target = os.path.join(dirpath, name)
                shutil.rmtree(target, ignore_errors=True)
                dirnames.remove(name)
                if _dirs_holding_bytecode(target):
                    kept.append(target)
                else:
                    removed += 1
    if not quiet:
        sys.stderr.write(f"purged {removed} __pycache__ director%s under this bundle\n"
                         % ("y" if removed == 1 else "ies"))
        if kept:
            sys.stderr.write(
                "PURGE_INCOMPLETE: %d cache director%s still hold .pyc after the purge.\n"
                % (len(kept), "y" if len(kept) == 1 else "ies"))
            for path in kept:
                sys.stderr.write(f"  kept: {path}\n")
            sys.stderr.write(
                "  A refusal will fire again; --purge-bytecode cannot clear these. Check write\n"
                "  permission on each directory and on its parent, then remove it yourself.\n")


if "--purge-bytecode" in sys.argv:
    sys.argv.remove("--purge-bytecode")
    _purge_bytecode()

_refuse_external_bytecode_cache()
_refuse_symlinked_bytecode_cache()
_refuse_foreign_bytecode()
import mamey


def _refuse_stale_bytecode():
    """Refuse when the imported engine disagrees with the source file beside it.

    Pinning sys.path gets the right DIRECTORY. It does not get the right BYTECODE: Python's
    default .pyc invalidation compares (source mtime, source size), and a cut writes a fixed
    1980 timestamp so archives stay byte-reproducible. A version bump keeps __init__.py the
    same length, so re-extracting a newer cut over a reused directory leaves both criteria
    unchanged and the stale cache is reused. The import then reports a version its own source
    does not contain -- the failure mode that put a 1.9.154 shadow in the workspace root.

    Read as text, compare, and stop. Nothing is deleted here; the remediation is printed.
    """
    init = os.path.join(_HERE, "mamey", "__init__.py")
    try:
        with open(init, encoding="utf-8") as handle:
            source = handle.read()
            found = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', source, re.M)
    except OSError:
        return  # cannot read the source: not our failure to diagnose
    if not found:
        return  # unrecognised layout: stay out of the way rather than block a run
    on_disk, imported = found.group(1), getattr(mamey, "__version__", None)
    mismatches = []
    if imported is not None and on_disk != imported:
        mismatches.append(f"__version__: source={on_disk!r}, imported={imported!r}")
    bundle = re.search(r'^BUNDLE_VERSION\s*=\s*["\']([^"\']+)["\']', source, re.M)
    if bundle and getattr(mamey, "BUNDLE_VERSION", None) != bundle.group(1):
        mismatches.append(f"BUNDLE_VERSION: source={bundle.group(1)!r}, imported={getattr(mamey, 'BUNDLE_VERSION', None)!r}")
    if not mismatches:
        return
    sys.stderr.write(
        "STALE_BYTECODE_REFUSED: " + "; ".join(mismatches) + "\n"
        f"  package: {getattr(mamey, '__file__', '?')}\n"
        "  A cached .pyc compiled from a different cut is being reused. The cut writes a fixed\n"
        "  1980 timestamp and a version bump does not change the file's size, so Python's\n"
        "  default (mtime, size) check cannot tell the two cuts apart.\n"
        "  Remediation: remove the stale caches under this bundle, e.g.\n"
        f"    find {_HERE!r} -name __pycache__ -type d -prune -exec rm -rf {{}} +\n"
        "  Nothing has been deleted for you.\n")
    raise SystemExit(2)


def _warn_if_package_is_not_this_bundle():
    """Warn when the imported package is not the mamey/ beside THIS mamey_run.py.

    The version check above compares source against imported WITHIN one tree, so it catches stale
    bytecode. It cannot notice that the tree itself is a superseded build, because a reseal of the
    same cut moves neither version string: 9.7.440 build `…440a` and build `…440c` both report
    __version__ 1.9.169 and BUNDLE_VERSION 9.7.440, and their Mode-B publication gates behaved
    differently. The field that separates them is the build id in BUILD_STAMP.txt.

    Two things are reported, both advisory -- this never blocks a run:
      * the imported package resolved outside this bundle (a shadow copy elsewhere on sys.path);
      * the build id, so a receipt or a transcript records WHICH tree produced the run, not just
        which version it claimed to be.
    """
    stamp = "(no BUILD_STAMP.txt)"
    try:
        with open(os.path.join(_HERE, "BUILD_STAMP.txt"), encoding="utf-8") as handle:
            found = re.search(r"^build=(.+)$", handle.read(), re.M)
        if found:
            stamp = found.group(1).strip()
    except OSError:
        pass  # absent or unreadable: report it as unknown, never guess a build id
    package = getattr(mamey, "__file__", None)
    expected = os.path.join(_HERE, "mamey", "__init__.py")
    if package and os.path.realpath(package) != os.path.realpath(expected):
        sys.stderr.write(
            f"SHADOW_PACKAGE_WARNING: imported mamey is not the one beside this runner\n"
            f"  imported: {package}\n  expected: {expected}\n"
            f"  this bundle's build: {stamp}\n"
            "  A version match does not prove a build match; compare BUILD_STAMP.txt.\n")
        return
    sys.stderr.write(f"mamey build: {stamp}\n")


_warn_if_package_is_not_this_bundle()
_refuse_stale_bytecode()
from mamey.cli import main
sys.exit(main())
