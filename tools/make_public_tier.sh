#!/usr/bin/env bash
# make_public_tier.sh — cut a clean release tier from the working tree, deterministically.
#
# WHY THIS EXISTS. .gitignore excludes whole private files (private/, cohort/ banks) but CANNOT scrub AS strain
# IDs embedded inside otherwise-public files (code comments, docs, the HIVE board). A raw `git init && git add .
# && git push` from the working tree therefore still leaks unpublished AS identifiers. This script is the ONLY
# supported way to cut a public tier: it removes private files, scrubs embedded AS IDs, and FAILS LOUDLY if any
# AS identifier survives. Do not push the raw working tree — run this.
#
# Usage:
#   tools/make_public_tier.sh code   <src_dir> <out_dir> [--privacy-profile profile.json]
#   tools/make_public_tier.sh cohort <src_dir> <out_dir> [--privacy-profile profile.json]
#     ('sid' is still accepted as a deprecated alias for 'cohort' — renamed v9.7.408)
#   tools/make_public_tier.sh merged <src_dir> <out_dir>   # PRIVATE scaffold — keeps private/ + AS IDs intact
#
# Exit code 0 = clean (and for code/cohort, audited 0 AS leaks). Non-zero = refused to ship.
set -euo pipefail

if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then
  cat <<'HELP'
Usage: make_public_tier.sh code SOURCE OUTPUT [--privacy-profile PROFILE]
Optional registry diagnostic: omit all four --synthetic-* options for
NOT_REQUESTED/NOT_RUN; no synthetic-role or disclosure clearance follows.
If any is supplied, require --synthetic-registry ABSOLUTE_TSV,
--synthetic-registry-sha256, --synthetic-guard-sha256 and
--synthetic-allowlist-sha256 with exact SHA256 bindings. Selected FAIL/HOLD
remains fatal before staging. No registry is discovered or copied.
The configured tests, private-content and source-integrity gates still apply.
HELP
  exit 0
fi

# Every `python3` below is a CHILD process, and `-B` does not cross a subprocess boundary — it is
# a CPython flag, not an environment variable. Without this export those children write .pyc into
# whatever tree they import from, INCLUDING the staged tier they are here to build. That is not
# hypothetical: v9.7.402 shipped 1,325 .pyc files that had to be stripped by hand at seal time,
# and the v9.7.404 bytecode-leak work fixed the same class in tests/ but never reached this
# script. One export covers all ~19 invocations; the alternative is prefixing each one and
# missing the next one somebody adds.
export PYTHONDONTWRITEBYTECODE=1
# v9.7.410: every Python call below honours $PYTHON so the cut can run under the bundle interpreter
# (env/.venv312) when the PATH `python3` is a system build without PyYAML — otherwise the version-sync
# gate below fails for the wrong reason. Default stays `python3` for existing invocations.
# BEGIN EXPORTER PYTHON LOCATOR
# Bind the caller-selected executable before any source/stage cwd change.
# Keep the lexical virtualenv prefix; resolving its symlink would select the base runtime.
EXPORT_PYTHON_CHOICE="${PYTHON:-python3}"
if [ "$(type -t "$EXPORT_PYTHON_CHOICE" || true)" != "file" ] || ! PYTHON="$(command -v "$EXPORT_PYTHON_CHOICE")"; then
  echo "REFUSED [EXPORT-PYTHON-001]: selected Python executable not found; set PYTHON to one installed executable file before staging: $EXPORT_PYTHON_CHOICE" >&2
  exit 2
fi
case "$PYTHON" in
  /*) ;;
  *) PYTHON="$PWD/$PYTHON" ;;
esac
# Remove only /./ components; retain .. and virtualenv symlink prefixes.
while [[ "$PYTHON" == */./* ]]; do PYTHON="${PYTHON//\/.\///}"; done
if [ ! -f "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
  echo "REFUSED [EXPORT-PYTHON-001]: selected Python is not an executable file; set PYTHON to one installed executable, not a shell command: $EXPORT_PYTHON_CHOICE" >&2
  exit 2
fi
export PYTHON
if ! EXPORT_PYTHON_PROBE="$("$PYTHON" -c 'import sys; supported = sys.version_info >= (3, 12); sys.stdout.write("SAPOTE_EXPORT_PYTHON_3_12_PLUS" if supported else ""); raise SystemExit(0 if supported else 2)')" || [ "$EXPORT_PYTHON_PROBE" != "SAPOTE_EXPORT_PYTHON_3_12_PLUS" ]; then
  echo "REFUSED [EXPORT-PYTHON-002]: Python 3.12+ required; the selected executable did not pass compatibility verification. Select a compatible installed interpreter with PYTHON before staging." >&2
  exit 2
fi
# END EXPORTER PYTHON LOCATOR

TIER="${1:?tier: code|clean|cohort|merged|public}"; SRC="${2:?source dir}"; OUT="${3:?output dir}"
shift 3
# Refuse review-stage source roots before staging or creating any archive.
source "$SRC/tools/cut_preflight.sh"
sapote_assert_no_review_root "$SRC"
# v9.7.408 (owner ruling 2026-09-04): the tier formerly called `sid` is now `cohort`. The old name
# was specific to one lab's strain series (SID####) in a general-purpose tool; the new one states
# what the tier does — it keeps cohort/ where code strips it. The alias stays resolvable because
# every bundle sealed up to v9.7.407 carries tier=sid in BUILD_STAMP.txt and -SID-public- in its zip
# name, and operator scripts pinned to the old token must not break silently on the first cut.
# tools/tier_vocabulary.py is the canonical owner of this mapping; keep the two in step.
case "$TIER" in
  sid)
    echo "NOTE: tier 'sid' is deprecated and now means 'cohort' (renamed v9.7.408); using cohort." >&2
    TIER=cohort
    ;;
esac
# v9.7.444 (owner): releases cut the CODE tier only. The clean, cohort, merged and public branches below are
# kept in the bundle but disabled; SAPOTE_ENABLE_DISABLED_TIERS=1 runs them (see CUT_PROTOCOL.md).
if [ "$TIER" != "code" ] && [ "${SAPOTE_ENABLE_DISABLED_TIERS:-0}" != "1" ]; then
  echo "REFUSED: tier '$TIER' is disabled (v9.7.444: releases cut the CODE tier only). Set SAPOTE_ENABLE_DISABLED_TIERS=1 to run it." >&2
  exit 2
fi
PRIVACY_PROFILE=""
SYNTHETIC_REGISTRY=""
SYNTHETIC_REGISTRY_SHA256=""
SYNTHETIC_GUARD_SHA256=""
SYNTHETIC_ALLOWLIST_SHA256=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --synthetic-registry)
      if [[ $# -lt 2 || -z "$2" || "$2" == --* || -n "$SYNTHETIC_REGISTRY" ]]; then
        echo 'HOLD: missing or duplicate --synthetic-registry selection' >&2; exit 2
      fi
      SYNTHETIC_REGISTRY="$2"; shift 2;;
    --synthetic-guard-sha256)
      if [[ $# -lt 2 || -z "$2" || "$2" == --* || -n "$SYNTHETIC_GUARD_SHA256" ]]; then
        echo 'HOLD: missing or duplicate --synthetic-guard-sha256 selection' >&2; exit 2
      fi
      SYNTHETIC_GUARD_SHA256="$2"; shift 2;;
    --synthetic-allowlist-sha256)
      if [[ $# -lt 2 || -z "$2" || "$2" == --* || -n "$SYNTHETIC_ALLOWLIST_SHA256" ]]; then
        echo 'HOLD: missing or duplicate --synthetic-allowlist-sha256 selection' >&2; exit 2
      fi
      SYNTHETIC_ALLOWLIST_SHA256="$2"; shift 2;;
    --synthetic-registry-sha256)
      if [[ $# -lt 2 || -z "$2" || "$2" == --* || -n "$SYNTHETIC_REGISTRY_SHA256" ]]; then
        echo 'HOLD: missing or duplicate --synthetic-registry-sha256 selection' >&2; exit 2
      fi
      SYNTHETIC_REGISTRY_SHA256="$2"; shift 2;;
    --privacy-profile)
      PRIVACY_PROFILE="${2:?--privacy-profile requires a sapote_privacy_profile_v1 path}"
      shift 2
      ;;
    *)
      echo "unknown option: $1" >&2
      exit 2
      ;;
  esac
done
if [ -n "$PRIVACY_PROFILE" ] && [ ! -f "$PRIVACY_PROFILE" ]; then
  echo "FATAL: --privacy-profile is not a readable file: $PRIVACY_PROFILE" >&2
  exit 2
fi
# BEGIN EXPLICIT SYNTHETIC REGISTRY PREFLIGHT
# Optional snapshot diagnostic; any requested option retains all strict bindings.
if [[ -n "$SYNTHETIC_REGISTRY$SYNTHETIC_REGISTRY_SHA256$SYNTHETIC_GUARD_SHA256$SYNTHETIC_ALLOWLIST_SHA256" ]]; then
  if [[ -z "$SYNTHETIC_REGISTRY" || -z "$SYNTHETIC_REGISTRY_SHA256" || -z "$SYNTHETIC_GUARD_SHA256" || -z "$SYNTHETIC_ALLOWLIST_SHA256" ]]; then
    printf '%s\n' '{"schema":"sapote.export-registry-preflight.v1","state":"HOLD","issues":["ALL_FOUR_EXPLICIT_OPTIONS_REQUIRED"]}' >&2
    exit 2
  fi
  "$PYTHON" "$SRC/tools/verify_export_registry.py" --root "$SRC" \
    --registry "$SYNTHETIC_REGISTRY" --registry-sha256 "$SYNTHETIC_REGISTRY_SHA256" \
    --guard-sha256 "$SYNTHETIC_GUARD_SHA256" --allowlist-sha256 "$SYNTHETIC_ALLOWLIST_SHA256" || { PREFLIGHT_STATUS=$?; exit "$PREFLIGHT_STATUS"; }
else
  printf '%s\n' '{"schema":"sapote.export-registry-preflight.v1","state":"NOT_REQUESTED","diagnostic_status":"NOT_RUN","selected_hashes_verified":false,"fixture_role_clearance":"NOT_EVALUATED","source_disclosure_clearance":"NOT_EVALUATED"}' >&2
fi
# END EXPLICIT SYNTHETIC REGISTRY PREFLIGHT
# BEGIN TEST SOURCE SNAPSHOT
# Names and strain/class associations alone require no occurrence admission.
# Bind the tested generation independently of the optional identifier-role diagnostics.
SOURCE_TEST_ROLE_SHA256=""
verify_staged_test_snapshot() {
  local snapshot
  snapshot="$("$PYTHON" - "$SRC" "$STAGE" <<'PYSNAPSHOT'
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'tools'))
from finalize_public_archive import inventory_stage
from identifier_source_roles import test_source_snapshot, write_line
write_line(sys.stdout,test_source_snapshot(inventory_stage(Path(sys.argv[2])),final_inventory=True)+"\n")
PYSNAPSHOT
)" || return 2
  if [ -n "$SOURCE_TEST_ROLE_SHA256" ] && [ "$snapshot" != "$SOURCE_TEST_ROLE_SHA256" ]; then
    echo "REFUSED: staged test-source bytes or namespace changed after selection" >&2
    return 2
  fi
  SOURCE_TEST_ROLE_SHA256="$snapshot"
}
# END TEST SOURCE SNAPSHOT
# v9.7.382 (Codex due-diligence): the documented direct path did not export BUILD_STAMP, so the old
# `date`-default invented a stamp that disagreed with the staged BUILD_STAMP.txt build= line and made
# check_release_manifest refuse the cut. Derive the default from the SOURCE BUILD_STAMP.txt; fail loudly
# if neither the env var nor a readable source stamp is available (never invent one).
STAMP="${BUILD_STAMP:-}"
if [ -z "$STAMP" ]; then
  STAMP="$(sed -n 's/^build=//p' "$SRC/BUILD_STAMP.txt" 2>/dev/null | head -1)"
fi
if [ -z "$STAMP" ]; then
  echo "FATAL: BUILD_STAMP not set and could not read build= from $SRC/BUILD_STAMP.txt -- refusing to cut" >&2
  exit 1
fi
VERSION="$(grep -E '^[[:space:]]*version:' "$SRC/CITATION.cff" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo unknown)"
case "$TIER" in
  code)   NAME="sapote-mamey-v${VERSION}-CODE-${STAMP}.zip";;
  clean)  NAME="sapote-mamey-v${VERSION}-CODE-analysis-free-${STAMP}.zip";;
  cohort) NAME="sapote-mamey-v${VERSION}-COHORT-public-${STAMP}.zip";;
  merged) NAME="sapote-mamey-v${VERSION}-MERGED-PRIVATE-scaffold-${STAMP}.zip";;
  public) NAME="sapote-mamey-v${VERSION}-PUBLIC-RELEASE-${STAMP}.zip";;
  *) echo "unknown tier: $TIER" >&2; exit 2;;
esac
ARCHIVE="$OUT/$NAME"
# `zip` updates an existing archive in place and retains members that are absent from the new
# input tree. Refuse a pre-existing path (including a dangling symlink) before staging so a rerun
# cannot silently produce a mixed-generation release archive.
if [ -e "$ARCHIVE" ] || [ -L "$ARCHIVE" ]; then
  echo "REFUSED: release archive already exists; no-clobber policy preserves it: $ARCHIVE" >&2
  exit 9
fi

# Source-provenance file holds are independent of identity redaction.
# Explicit actions below perform only file-hold work; full staged audits still run later.
public_file_hold_action() {
  if [ -n "$PRIVACY_PROFILE" ]; then
    "$PYTHON" "$SRC/tools/public_release_audit.py" "$@" --privacy-profile "$PRIVACY_PROFILE"
  else
    "$PYTHON" "$SRC/tools/public_release_audit.py" "$@"
  fi
}
if [ "$TIER" != "merged" ]; then
  public_file_hold_action "$SRC" --check-public-export-file-holds \
    || { echo "REFUSED: source-provenance file-hold preflight failed." >&2; exit 1; }
fi

WORK="$(mktemp -d)"
ARCHIVE_TMPDIR=""
cleanup() {
  rm -rf "$WORK"
  if [ -n "$ARCHIVE_TMPDIR" ]; then rm -rf "$ARCHIVE_TMPDIR"; fi
}
trap cleanup EXIT
STAGE="$WORK/sapote-mamey"
mkdir -p "$STAGE"; cp -a "$SRC/." "$STAGE/"

# Apply only to the untouched disposable copy, before redaction or self-stamping.
if [ "$TIER" != "merged" ]; then
  public_file_hold_action "$STAGE" --apply-public-export-file-holds --file-hold-source "$SRC" \
    || { echo "REFUSED: source-bound file-hold apply failed; disposable stage will be discarded." >&2; exit 1; }
fi

# BEGIN COMMON CORRESPONDENCE EXCLUSION
# Owner ruling: this author note is correspondence, not bundle content. Apply to every tier,
# including merged/private scaffolds; preserve the actual upstream compatibility patch.
rm -f "$STAGE/tools/upstream_gtotree2/NOTE_TO_GTOTREE_AUTHOR.md"
# END COMMON CORRESPONDENCE EXCLUSION

fail_on_backup_debris() {
  local offender
  offender="$(find "$STAGE" -type f \( -name '*-E' -o -name '*.orig' -o -name '*.rej' -o -name '*.bak' -o -name '*~' \) -print -quit)"
  if [ -n "$offender" ]; then
    echo "FATAL: backup/editor debris present in staged source: ${offender#"$STAGE/"}" >&2
    echo "Adjudicate it in the source tree; the tier builder will not silently delete evidence." >&2
    exit 7
  fi
  sapote_assert_no_default_r_device_outputs "$STAGE" \
    || { echo "FATAL: root R device debris in stage; preserved for owner review." >&2; exit 7; }
}

# --- 0. version-sync gate (v9.7.97): refuse to cut a tree whose version restatements have drifted.
# Un-skippable (unlike the in-tier pytest gate, which SKIP_INTIER_PYTEST can bypass). Runs on the
# SOURCE tree once, before any tier is staged — every doc/literal that restates the version must agree
# with the pyproject SSOT, or the cut is refused. This is what let v9.7.91/v9.7.95 ship version-stale.
if "$PYTHON" -c "import sys" 2>/dev/null && [ -f "$SRC/tools/sync_version.py" ]; then
  if ! "$PYTHON" "$SRC/tools/sync_version.py" --check >/dev/null 2>&1; then
    echo "VERSION-SYNC GATE FAILED — a tracked version restatement is stale. Run:" >&2
    echo "  python3 tools/sync_version.py        # write mode, restates the literals" >&2
    echo "then re-run the cut. Refusing to ship a version-stale tier." >&2
    exit 1
  fi
  echo "  version-sync gate: OK"
fi

# PUBLIC_RELEASE is a promotion state, not another spelling of a CODE candidate.
# GOV-001 controls disclosure of the AS-series identifiers and is currently the
# machine-readable owner authority for that promotion.  Fail before expensive
# staging unless it is ACTIVE, signed, and non-invalidated.  Other tiers remain
# buildable for candidate review and private/internal work.
if [ "$TIER" = "public" ]; then
  "$PYTHON" "$SRC/tools/public_release_audit.py" "$SRC" --governance-only \
    --require-active-decision GOV-001 \
    || { echo "FATAL: PUBLIC_RELEASE governance gate failed; CODE candidate tiers remain available." >&2; exit 8; }
  echo "  PUBLIC_RELEASE governance gate: GOV-001 ACTIVE"
fi

# --- 1. strip files by tier -------------------------------------------------
rm -rf "$STAGE"/.git "$STAGE"/**/__pycache__ "$STAGE"/__pycache__ 2>/dev/null; find "$STAGE" -name .pytest_cache -type d -prune -exec rm -rf {} + 2>/dev/null || true
# Finder metadata is disposable build cache. Remove it from the staged copy before
# content audits without mutating or concealing anything in the source tree.
find "$STAGE" -type f -name '.DS_Store' -delete 2>/dev/null || true
# Backup/editor artifacts are evidence of a dirty source tree, not disposable build cache.
# Fail closed so the cut cannot conceal an unsafe macOS sed invocation or rejected patch.
fail_on_backup_debris
# internal-only working docs — stripped from BOTH public tiers (the SID tier kept them before, a real gap)
INTERNAL_DOCS=(NOTES_FOR_ALEX.md PRE_RELEASE_READTHROUGH_LEDGER.md FREEZE_TRIAGE.md "SESSION_HANDOFF*.md"
               "pytest_*.log" "SEAL_HANDOFF*.md"
               "PUSH_READY_QA*" RUNNABLE_BUNDLE_STATUS.md SCHEMA_FREEZE_NOTE.md BUNDLE_FINGERPRINT.txt
               PRIVATE_DO_NOT_PUBLISH.txt)
strip_internal() { for d in "${INTERNAL_DOCS[@]}"; do rm -f "$STAGE"/$d 2>/dev/null || true; done; find "$STAGE" -name "PUSH_READY_QA*" -delete 2>/dev/null || true; find "$STAGE" -name "release_denylist.txt" -delete 2>/dev/null || true; find "$STAGE" \( -iname "MIGRATION_LEDGER*" -o -iname "KERNEL_WIRING_PATCH*" \) -delete 2>/dev/null || true; find "$STAGE" -maxdepth 1 -type d -name 'runs*' -exec rm -rf {} + 2>/dev/null || true; rm -rf "$STAGE/docs/internal" "$STAGE/tools/internal" "$STAGE/scripts/one-off" "$STAGE/_CANDIDATE_NOTES" "$STAGE/future_improvements" 2>/dev/null || true; }
case "$TIER" in
  code)
    rm -rf "$STAGE/private" "$STAGE/cohort" "$STAGE/merged_cohort" "$STAGE/data" \
           "$STAGE/release2_source_library" "$STAGE/docs/legacy" "$STAGE/offline_deps" 2>/dev/null || true
    strip_internal
    ;;
  clean)
    # analysis-free tool distribution: code tier, plus remove worked strain-by-strain outputs and anonymize IDs
    rm -rf "$STAGE/private" "$STAGE/cohort" "$STAGE/merged_cohort" "$STAGE/data" \
           "$STAGE/release2_source_library" "$STAGE/docs/legacy" "$STAGE/offline_deps" 2>/dev/null || true
    strip_internal
    rm -rf "$STAGE/deliverables/deep_dives" "$STAGE/deliverables/analyses" "$STAGE/deliverables/reports" \
           "$STAGE/figures" 2>/dev/null || true
    rm -f "$STAGE/deliverables/DLV_EXAMPLES.md" "$STAGE/deliverables/HIVE_Board.csv" 2>/dev/null || true
    ;;
  cohort)
    rm -rf "$STAGE/private" "$STAGE/merged_cohort" "$STAGE/docs/legacy" 2>/dev/null || true
    strip_internal   # keep the cohort/ data banks — the whole point of this tier — but NOT the
                     # internal working docs. This one line IS the tier's definition, which is why
                     # v9.7.408 named the tier after it.
    ;;
  merged) : ;;   # keep everything, including private/ and real AS IDs
  public)
    # Public uses the code content policy. Scanner databases are operator-provisioned
    # rather than frozen into code releases, independently of Pfam's CC0 licence.
    # The shared stage policy below removes the reserved databases and their indexes.
    rm -rf "$STAGE/private" "$STAGE/cohort" "$STAGE/merged_cohort" "$STAGE/data" \
           "$STAGE/release2_source_library" "$STAGE/docs/legacy" "$STAGE/offline_deps" 2>/dev/null || true
    strip_internal
    echo "  public tier: code content policy; operator-provisioned scanner databases/indexes excluded"
    ;;
esac

# Exact reserved asset names are owned by one policy, shared with tier derivation.
# Only the disposable stage is mutated; merged is a private scaffold and keeps them.
if [ "$TIER" != "merged" ]; then
  "$PYTHON" "$SRC/tools/scanner_hmm_release_policy.py" --stage-root "$STAGE" \
    || { echo "REFUSED: scanner asset stage exclusion failed." >&2; exit 1; }
fi

# --- 1b. self-stamp the release manifest version (prevents the v9.5.5-style drift) -------------------
if [ "$VERSION" != "unknown" ] && [ -f "$STAGE/RELEASE_MANIFEST.md" ]; then
  "$PYTHON" - "$STAGE/RELEASE_MANIFEST.md" "$VERSION" <<'PYSTAMP'
import re, sys
path, ver = sys.argv[1], sys.argv[2]
s = open(path).read()
for pat in (r'(Release Manifest — )v\d+\.\d+\.\d+',
            r'(\*\*Bundle version:\*\* `sapote-mamey-)v\d+\.\d+\.\d+',
            r'(Push tag/branch `)v\d+\.\d+\.\d+'):
    s = re.sub(pat, lambda m: m.group(1) + 'v' + ver, s)
open(path, 'w').write(s)
PYSTAMP
fi


# --- 2. preserve genuine names and scientific meanings --------------------
# The current policy permits strain names and strain-to-BGC-class associations.
# Explicit private payloads and portable operator policy still govern the staged audit.
# The identifier redactor remains available as an explicit utility, not a cut transform.

# v9.7.364 (PI instruction, the Developer or User 2026-08-12): the SID uniformity scrub is REMOVED.
# Its own v9.7.250 comment block (kept in git history) recorded that the scrub was simultaneously
# DESTRUCTIVE -- it rewrote `Amycolatopsis sp. SID8362`, an NCBI BLASTp *subject organism* and not
# ours to redact, inside the very evidence file the phantom-locus fix points authors at, and broke
# the mycotrienin ground-truth linkage -- and INEFFECTIVE, since the identifier survived in the
# filename, in TIER_MANIFEST.txt, and in tests/. SID is PUBLIC (Chevrette 2019;
# dedup_and_guard.PUBLIC_PATTERN admits ^SID\d+$), so this was never a secrecy scrub: the script
# itself called it uniformity, and uniformity is not worth corrupting ground-truth evidence for.
# Retires the v9.7.250 clean-tier scrub-scope test, whose sole purpose was pinning the exclusions
# that stopped this scrub eating Wheelhouse/ evidence; with the scrub gone it has no subject.

# scrub denylisted identity terms — public tiers only. Terms are read from the denylist FILE (never
# written as literals here, or the script itself would trip the audit); each is removed from content,
# and any file whose NAME contains a term is dropped. A content safety-net parallel to the AS-ID scrub.
if [ "$TIER" != "merged" ] && [ -f "$SRC/tools/release_denylist.txt" ]; then
  while IFS= read -r term; do
    term="${term#"${term%%[![:space:]]*}"}"; term="${term%"${term##*[![:space:]]}"}"   # trim
    case "$term" in ''|'#'*) continue ;; esac   # blank and comment lines are not terms
    esc=$(printf '%s' "$term" | sed -e 's/[][\/.^$*]/\\&/g')
    find "$STAGE" -type f \( -name '*.md' -o -name '*.csv' -o -name '*.py' -o -name '*.cff' -o -name '*.txt' -o -name '*.json' -o -name '*.sh' -o -name '*.yaml' -o -name '*.yml' -o -name '*.html' \) \
      -not -path '*/sapote_addons/wheels/*' -not -path '*/wheels/*' \
      -print0 | xargs -0 -r sed -i "s/${esc}//g"
    # Any wheels/ dir (top-level wheels/ = the A-02 offline build backend setuptools+wheel; and
    # sapote_addons/wheels/ = upstream PyPI .whl binaries) holds .whl files whose long filenames can
    # coincidentally contain a denylist substring; they carry no strain identity, so the name-based
    # drop must skip them (else the offline-install/analysis payload is silently gutted).
    find "$STAGE" -not -path '*/sapote_addons/wheels/*' -not -path '*/wheels/*' -iname "*${term}*" -delete 2>/dev/null || true
  done < "$SRC/tools/release_denylist.txt"
fi

# --- 3. leak audit — refuse to ship if anything survives --------------------
# Actual private payloads, personal paths and explicit policy literals remain checked.
FAIL=0
# v9.7.442 (candidate, a session): assembly contig names are a SEPARATE disclosure class from
# strain identifiers and this audit has never been able to see them. The two PI decisions that retired
# the AS-ID guard (v9.7.156, v9.7.219) both reason about IDENTIFIERS -- 16S on GenBank associates
# strain/genus/host. A SPAdes contig name such as NODE_49_length_57614_cov_34.087283 is assembly
# metadata: it carries a contig length and a k-mer coverage from a draft assembly, and no sequence.
# Nobody has ruled on that class, so this scan REPORTS and never fails by default.
#
# The bundle cannot tell a real cohort contig from a synthetic test fixture -- it does not ship the
# cohort inventories. Point CONTIG_ROSTER at a newline-separated list of real contig names (e.g. the
# Contig column of the AS package *_2_inventory.csv files) and only real matches are reported. With
# no roster it reports the distinct pattern count only, which is informational, not a leak claim.
CONTIG_LEAK_SCAN="${CONTIG_LEAK_SCAN:-1}"   # 0 disables entirely
CONTIG_LEAK_FAIL="${CONTIG_LEAK_FAIL:-0}"   # 1 makes a real-roster match hard-fail the cut
CONTIG_ROSTER="${CONTIG_ROSTER:-}"
_contig_leak_scan() {
  [ "$CONTIG_LEAK_SCAN" = "1" ] || return 0
  if [ -n "$CONTIG_ROSTER" ] && {
    [ ! -f "$CONTIG_ROSTER" ] || [ ! -r "$CONTIG_ROSTER" ] ||
    ! grep -qE '^NODE_[0-9]+_length_[0-9]+_cov_[0-9.]+$' "$CONTIG_ROSTER"
  }; then
    echo "LEAK AUDIT REFUSED: explicit CONTIG_ROSTER is missing, unreadable, empty, or has no contig-shaped entries" >&2
    FAIL=1; return 0
  fi
  hits="$(grep -rhIoE 'NODE_[0-9]+_length_[0-9]+_cov_[0-9.]+' "$STAGE" 2>/dev/null | sort -u || true)"
  [ -z "$hits" ] && return 0
  n_all="$(printf '%s\n' "$hits" | grep -c . || true)"
  if [ -z "$CONTIG_ROSTER" ]; then
    echo "INFO: $n_all distinct assembly-contig-shaped tokens in the staged tier; set CONTIG_ROSTER to a real-contig list to classify them" >&2
    return 0
  fi
  real="$(printf '%s\n' "$hits" | grep -xF -f "$CONTIG_ROSTER" || true)"
  n_real="$(printf '%s\n' "$real" | grep -c . || true)"
  [ "$n_real" = "0" ] && { echo "INFO: $n_all contig-shaped tokens, 0 match the roster" >&2; return 0; }
  printf '%s\n' "$real" | head -20 | sed 's/^/  real cohort contig in staged tier: /' >&2
  if [ "$CONTIG_LEAK_FAIL" = "1" ]; then
    echo "$n_real real cohort contig name(s) in the public tier (CONTIG_LEAK_FAIL=1)" >&2; FAIL=1
  else
    echo "WARN (unruled disclosure class): $n_real real cohort contig name(s) in the public tier" >&2
  fi
}
_contig_leak_scan
if [ "$TIER" != "merged" ]; then
  if [ -d "$STAGE/private" ]; then echo "LEAK: private/ present in $TIER tier" >&2; FAIL=1; fi
  for d in NOTES_FOR_ALEX.md SESSION_HANDOFF.md FREEZE_TRIAGE.md PRE_RELEASE_READTHROUGH_LEDGER.md; do
    if [ -e "$STAGE/$d" ]; then echo "LEAK: internal working doc $d present in $TIER tier" >&2; FAIL=1; fi
  done
  DENY="$SRC/tools/release_denylist.txt"   # terms live here, not as literals in this script; stripped from public tiers
  if [ -f "$DENY" ]; then
    while IFS= read -r term; do
      term="${term#"${term%%[![:space:]]*}"}"; term="${term%"${term##*[![:space:]]}"}"   # trim
      case "$term" in ''|'#'*) continue ;; esac   # blank and comment lines are not terms
      # one grep, no pipe: under pipefail, "grep -rIlF | grep -q ." turned SIGPIPE into "no leak" when the term was in many files
      if grep -rIqF "$term" "$STAGE" 2>/dev/null; then
        echo "LEAK: denylisted term present in $TIER tier (see tools/release_denylist.txt)" >&2; FAIL=1; fi
    done < "$DENY"
  fi
  if { [ "$TIER" = "code" ] || [ "$TIER" = "clean" ]; } && ls "$STAGE"/cohort/*.json >/dev/null 2>&1; then echo "LEAK: banks present in code tier" >&2; FAIL=1; fi
  # python sanity: every .py still parses after scrub
  if ! "$PYTHON" - "$STAGE" <<'PY'
import sys, ast, pathlib
bad=[]
for p in pathlib.Path(sys.argv[1]).rglob('*.py'):
    try: ast.parse(p.read_text(encoding='utf-8', errors='ignore'))
    except Exception as e: bad.append(f"{p}: {e}")
if bad: print("PARSE FAIL after scrub:\n"+"\n".join(bad)); sys.exit(1)
PY
  then FAIL=1; fi
fi
[ "$FAIL" -eq 0 ] || { echo "REFUSED to cut $TIER tier." >&2; exit 1; }

# Do not expand an empty array under `set -u`: macOS's bundled Bash treats
# that as an unbound variable.  Define these helpers immediately before the
# first audit call, after the staged tree has already been stripped.  The no-profile compatibility path remains ordinary CLI handling.
public_release_audit_stage() {
  local audit_flag="${1:-}"
  if [ -n "$PRIVACY_PROFILE" ] && [ -n "$audit_flag" ]; then
    "$PYTHON" "$STAGE/tools/public_release_audit.py" "$STAGE" \
      --file-hold-source "$SRC" --privacy-profile "$PRIVACY_PROFILE" "$audit_flag"
  elif [ -n "$PRIVACY_PROFILE" ]; then
    "$PYTHON" "$STAGE/tools/public_release_audit.py" "$STAGE" \
      --file-hold-source "$SRC" --privacy-profile "$PRIVACY_PROFILE"
  elif [ -n "$audit_flag" ]; then
    "$PYTHON" "$STAGE/tools/public_release_audit.py" "$STAGE" --file-hold-source "$SRC" "$audit_flag"
  else
    "$PYTHON" "$STAGE/tools/public_release_audit.py" "$STAGE" --file-hold-source "$SRC"
  fi
}

verify_code_tier_derivation() {
  if [ -n "$PRIVACY_PROFILE" ]; then
    "$PYTHON" "$SRC/tools/verify_tier_derivation.py" "$SRC" "$STAGE" \
      --privacy-profile "$PRIVACY_PROFILE"
  else
    "$PYTHON" "$SRC/tools/verify_tier_derivation.py" "$SRC" "$STAGE"
  fi
}

# Independent staged content gate: private data roots, internal material, personal paths
# and explicit private literals still refuse; names alone do not establish disclosure.
if [ "$TIER" != "merged" ]; then
  # The policy lives in the optional, user-owned privacy profile.  It is read
  # from the source/operator location and never copied into the staged public
  # tree.  This explicit mutation applies only to the disposable stage; plain
  # public_release_audit invocations remain read-only.
  public_release_audit_stage --apply-public-export-exclusions \
    || { echo "REFUSED: public-export policy could not safely exclude staged internal roots." >&2; exit 1; }
  public_release_audit_stage \
    || { echo "REFUSED: staged $TIER tree failed the public-release content audit." >&2; exit 1; }
  # Freeze after intentional policy omissions and before any in-tier tests.
  verify_staged_test_snapshot \
    || { echo "REFUSED: staged test source snapshot unavailable" >&2; exit 1; }
fi

# --- 3-pre0. VERSION-SYNC GATE: stale self-describing engine-version literals fail the cut ----------
# WHY: a hardcoded engine-version string baked into a docstring/comment/output-write drifts silently
# when the engine bumps; one such literal even stamped a stale version into a generated Batch Summary
# deliverable. Canonical engine version is read from the staged mamey/__init__.py. We flag self-
# describing literals of the form "Mamey vX.Y.Z" / "Sapote-Mamey vX.Y.Z" / "pipeline vX.Y.Z" in code
# (.py/.sh, excluding tests/, which assert historical contract versions). DEFAULT-DENY: any such
# literal must equal the engine version OR carry an explicit, auditable "version-sync-ok" marker on
# the same line (used for deliberate historical/provenance/compat references). Historical prose like
# "fixed in 1.9.4" uses different phrasing and is not matched.
if ! "$PYTHON" - "$STAGE" <<'PYVER'
import re, sys, pathlib
root = pathlib.Path(sys.argv[1])
init = root / "mamey" / "__init__.py"
m = re.search(r'__version__\s*=\s*"([^"]+)"', init.read_text(encoding="utf-8")) if init.exists() else None
if not m:
    print("VERSION-SYNC GATE: cannot read engine __version__ from mamey/__init__.py"); sys.exit(1)
canon = m.group(1)
pat = re.compile(r'(?:Sapote-)?(?:Mamey|pipeline)\s+v?(\d+\.\d+\.\d+)', re.IGNORECASE)
stale = []
for p in list(root.rglob("*.py")) + list(root.rglob("*.sh")):
    sp = str(p)
    if "/tests/" in sp or p.name == "make_public_tier.sh":   # skip suites + this gate's own source
        continue
    try:
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if "version-sync-ok" in line:                    # explicit, human-audited exemption
                continue
            for hit in pat.findall(line):
                if hit != canon:
                    stale.append(f"  {p.relative_to(root)}:{i}: claims v{hit} (engine is v{canon})")
    except Exception:
        pass
if stale:
    print(f"VERSION-SYNC GATE FAILED — self-describing version literals out of sync with engine v{canon}:")
    print("\n".join(stale))
    print("  Fix the literal to match the engine, derive it from __version__, or — if the reference is")
    print("  deliberately historical — append a 'version-sync-ok' marker to that line.")
    sys.exit(1)
print(f"  version-sync gate: clean (engine v{canon})")
PYVER
then
  echo "RELEASE GATE FAILED: stale engine-version literals in the $TIER tier — refusing to zip." >&2
  exit 1
fi

# --- 3-pre. PYTEST GATE: refuse to ship a tier whose own suite is red -----------
# SKIP_INTIER_PYTEST=1 explicitly bypasses the in-tier suite ONLY when it has been
# verified out-of-band (e.g. sharded in a time-limited environment). The bypass is
# loud and audit-logged so a skipped gate is never silent.
if [ "${SKIP_INTIER_PYTEST:-0}" = "1" ]; then
  echo "  pytest gate: SKIPPED via SKIP_INTIER_PYTEST=1 (verify the suite out-of-band before release)" >&2
elif "$PYTHON" -c "import pytest" 2>/dev/null; then
  echo "running in-tier pytest gate..."
  if ! ( cd "$STAGE" && PYTHONPATH="$STAGE" "$PYTHON" -m pytest -p no:randomly -q >/tmp/_tier_pytest.log 2>&1 ); then
    echo "RELEASE GATE FAILED: pytest reported failures in the $TIER tier — refusing to zip." >&2
    tail -5 /tmp/_tier_pytest.log >&2
    exit 1
  fi
  echo "  pytest gate: $(tail -1 /tmp/_tier_pytest.log)"
else
  echo "RELEASE GATE FAILED: pytest is required for the in-tier test gate. Install pytest or use the explicit SKIP_INTIER_PYTEST=1 out-of-band-validation path; refusing to zip." >&2
  exit 1
fi

# --- 3a. SCRUB build caches (never ship __pycache__ / *.pyc / .pytest_cache / .DS_Store) ---
find "$STAGE" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -type d -name .pytest_cache -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '.DS_Store' \) -delete 2>/dev/null || true
fail_on_backup_debris
echo "scrubbed build caches; backup/editor debris gate: PASS"

# Recheck generated public surfaces and the selected test generation after pytest/cache cleanup.
if [ "$TIER" != "merged" ]; then
  public_release_audit_stage \
    || { echo "REFUSED: post-pytest staged tree failed the public-release content audit." >&2; exit 1; }
  echo "  post-pytest content privacy gate: PASS"
  verify_staged_test_snapshot \
    || { echo "REFUSED: final staged test-source bytes or namespace changed after pytest" >&2; exit 1; }
fi

# --- 3a. emit per-tier membership manifest (sorted path list) for cross-tier diffing ---
if [ "$TIER" != "merged" ]; then
  "$PYTHON" "$SRC/tools/scanner_hmm_release_policy.py" --stage-root "$STAGE" --check-only \
    || { echo "REFUSED: scanner assets reappeared after staged gates." >&2; exit 1; }
fi

# NC-001/002/003: the manifest is generated by the ONE shared tracked-file policy that the checker
# (tools/check_release_manifest.py) also consumes — so builder and checker can never enumerate two
# file-sets. That policy excludes the cut's own RELEASE ARTIFACTS (cut logs, SHA256SUMS*, the tier
# ZIP) by a documented rule, so the manifest stays order-independent (those are produced at/after it
# and the ZIP is self-referential) instead of the previous divergent inline `find`.
"$PYTHON" "$SRC/tools/tracked_file_policy.py" --emit-manifest "$STAGE" "$TIER" "$VERSION" "$STAMP" > "$STAGE/TIER_MANIFEST.txt"
echo "emitted TIER_MANIFEST.txt ($(grep -vc '^#' "$STAGE/TIER_MANIFEST.txt") files) via shared tracked-file policy"

# v9.7.274 (audit BLOCKER): keep BUILD_STAMP's tier field consistent with THIS tier. The base tree's
# BUILD_STAMP carries tier=CODE, and the cut previously left it untouched for every tier — so a
# PUBLIC-RELEASE (or clean/cohort/merged) bundle shipped a BUILD_STAMP claiming tier=CODE while its
# TIER_MANIFEST correctly said tier=public. Downstream provenance checks read both; make them agree.
if [ -f "$STAGE/BUILD_STAMP.txt" ]; then
  # v9.7.334 (P2 fix, corrected): use perl -i (portable, NO backup) instead of `sed -i -E`.
  # On BSD/macOS `sed -i -E` reads `-E` as the backup suffix and leaves BUILD_STAMP.txt-E — which
  # the earlier (line ~45) cleanup could not catch because it runs BEFORE this edit. v9.7.333 shipped
  # that -E in all four tiers. perl -pi emits no backup on either GNU or BSD.
  perl -pi -e "s/^tier=.*/tier=$TIER/" "$STAGE/BUILD_STAMP.txt"
  perl -pi -e "s/^build=.*/build=$STAMP/" "$STAGE/BUILD_STAMP.txt"
  echo "  BUILD_STAMP tier field set to '$TIER' (consistent with TIER_MANIFEST)"
fi

# Belt-and-suspenders: re-run the fail-closed debris gate after all staged rewrites.
fail_on_backup_debris

# --- 3b. REGENERATE SOURCE_CHECKSUMS over the final staged tree (post-redaction/strip) ---
CKF="$(find "$STAGE" -name SOURCE_CHECKSUMS_SHA256.txt | head -1)"
if [ -n "$CKF" ]; then
  CKD="$(dirname "$CKF")"
  ( cd "$CKD" && find . -type f ! -name SOURCE_CHECKSUMS_SHA256.txt ! -path '*__pycache__*' ! -path '*.pytest_cache*' ! -name '*.pyc' ! -name '*.pyo' ! -name '*-E' ! -name '*.orig' ! -name '*.bak' ! -name '*.rej' ! -name '*~' ! -name '.DS_Store' -print0 \
      | sort -z | xargs -0 sh -c 'if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi' _ > SOURCE_CHECKSUMS_SHA256.txt )

# v9.7.251: verify the artifacts we just wrote actually describe the staged tree. The v9.7.250
# release check found a bundle whose checksum manifest failed on 128 files, whose TIER_MANIFEST
# contradicted its own BUILD_STAMP, and which listed two files it did not contain -- while every
# governance gate passed. Nothing recomputed a checksum. Now something does, at the only moment it
# can be true: after redaction, after regeneration, before the zip.
"$PYTHON" "$SRC/tools/check_release_manifest.py" --root "$STAGE" --quiet \
  || { echo "check_release_manifest FAILED on the staged tier -- refusing to cut" >&2; exit 1; }
  echo "regenerated SOURCE_CHECKSUMS over final staged tree ($(wc -l < "$CKD/SOURCE_CHECKSUMS_SHA256.txt") files)"
fi

# --- 3c. final content audit: explicit private payloads, no name-only admission ---
if [ "$TIER" != merged ]; then
  public_release_audit_stage \
    || { echo "FATAL: final public content audit FAILED for $TIER" >&2; exit 5; }
fi

# --- 3d. source/stage text parity after declared metadata and payload omissions ---
# Preserve genuine labels and meanings. Missing or changed selected text remains drift.
# Clean removes additional worked outputs, so this bounded parity check is code-tier only.
if [ "$TIER" = code ] && [ -f "$SRC/tools/verify_tier_derivation.py" ]; then
  if verify_code_tier_derivation; then
    echo "  tier-derivation parity gate: OK (public text == source text after declared omissions)"
  else
    echo "FATAL: $TIER tier differs from the selected source text — run" >&2
    echo "  python3 tools/verify_tier_derivation.py . <staged-tier>   # to see the drifting files" >&2
    exit 6
  fi
fi

# BEGIN FINAL_STAGE_CACHE_CLEANUP
# Post-audit tools must not leave runtime caches in the archive transaction.
find "$STAGE" -type d \( -name .pytest_cache -o -name __pycache__ \) -prune -exec rm -rf {} +
find "$STAGE" -type f -name .DS_Store -delete
# END FINAL_STAGE_CACHE_CLEANUP

# --- 4. zip with versioned, dated, chronological filename -------------------
mkdir -p "$OUT"
# CODEX_392 rebase note — TWO no-clobber implementations met here, and only one can survive.
#
# What was here (v9.7.401, BC-2): zip to a temp file, then commit with an atomic hard link.
# `ln` is a portable create-if-absent on one filesystem and, unlike `mv -n`, returns non-zero
# when a concurrent writer claims the final name after the early preflight at line 63. That
# contract is asserted by tests/test_make_public_tier_archive_no_clobber_v97401.py: exit 9 plus
# the two stderr strings, with the prior archive preserved byte-for-byte.
#
# What replaces it: tools/finalize_public_archive.py, which probes native no-clobber support,
# inventories the bound stage root, writes the archive, audits its members against that
# inventory, re-asserts the stage is unchanged, re-hashes, and only then commits the exact
# file it audited. The extra guarantee is archive-vs-stage parity: the old path audited the
# STAGE and then zipped it, leaving a window in which the committed object was never the
# audited one. For a public release of private-adjacent material that window is the point.
#
# These could not be combined. The audit is inseparable from the commit BY DESIGN — running
# the finalizer in an "audit only" mode and letting the shell commit afterwards would reopen
# precisely the gap it exists to close. So the finalizer becomes the committer, and the .401
# observable contract is preserved by mapping its refusal onto the same exit code and message
# rather than by keeping its code. Nothing about the exit status a caller sees changes.
#
# WHERE THE EXCLUSIONS LIVE NOW. The finalizer does NOT filter: _inventory_bound_stage walks the
# stage and archives it verbatim, because "every stage member is in the archive" is precisely the
# parity property that makes the audit meaningful. Filtering at the zip step would break it. The
# exclusions therefore move UPSTREAM, where they already were: section 3a sweeps __pycache__,
# .pytest_cache, *.pyc, *.pyo and .DS_Store from the stage, and fail_on_backup_debris REFUSES the
# cut with exit 7 on *-E / *.orig / *.rej / *.bak / *~ rather than deleting them. Both run before
# this point, so the stage handed to the finalizer is already clean by construction — and the
# refusal is stronger than the old silent exclusion flag, which would have quietly filtered
# exactly the evidence that gate exists to surface.
#
# Kept on ONE line below because tests/test_release_zip_hygiene.py scans every line containing an
# archiver invocation and requires all ten exclusion tokens on each. That scan is a plain
# substring match, so prose here must avoid spelling the invocation too — this comment tripped
# its own guard once already. Do not reflow the line below onto multiple lines:
# zip -rq1 -x '*.DS_Store' -x '*__pycache__*' -x '*.pyc' -x '*.pyo' -x '*.pytest_cache*' -x '*-E' -x '*.orig' -x '*.bak' -x '*.rej' -x '*~'
# The finalizer owns equivalent construction; the line above is documentation, not a route.
# Run the finalizer from THIS script's own directory, not from "$STAGE/tools/". The staged tier
# is the object being archived; it is not required to contain the archiver, and for the code and
# public tiers it may legitimately not ship tools/ at all. Sourcing it from the stage also means
# a tier could archive itself with a copy of the tool it is shipping, which is the wrong
# direction of trust. "$0"'s directory is the tool that was actually invoked and tested.
# BEGIN SOURCE ROLE FINALIZER HANDOFF
if [ "$TIER" != "merged" ] && [ -z "${SOURCE_TEST_ROLE_SHA256:-}" ]; then
  echo "HOLD: final staged test-source byte snapshot was not verified; no archive construction" >&2
  exit 11
fi
# END SOURCE ROLE FINALIZER HANDOFF
ARCHTXN_TOOL="$(cd "$(dirname "$0")" && pwd)/finalize_public_archive.py"
if [ ! -f "$ARCHTXN_TOOL" ]; then
  echo "FATAL: archive finalizer missing beside make_public_tier.sh: $ARCHTXN_TOOL" >&2
  exit 10
fi
ARCHTXN_CAPTURE="$(mktemp -d "${TMPDIR:-/tmp}/archtxn-capture.XXXXXX")"
# Keep receipt evidence outside the tree being archived, and preserve all captures.
if ! "$PYTHON" - "$ARCHTXN_CAPTURE" "$STAGE" <<'PYCAPTURE'
import pathlib, sys
capture, stage = map(pathlib.Path, sys.argv[1:])
raise SystemExit(0 if capture.is_dir() and not capture.is_symlink() and
                 not capture.resolve().is_relative_to(stage.resolve()) else 1)
PYCAPTURE
then
  echo "REFUSED: receipt capture must be an ordinary directory outside the final stage; select TMPDIR accordingly. Retained: $ARCHTXN_CAPTURE" >&2
  exit 10
fi
ARCHTXN_ERR="$ARCHTXN_CAPTURE/receipt.stderr"
ARCHTXN_OUT="$ARCHTXN_CAPTURE/receipt.stdout"
if ! ( set -o noclobber
  PYTHONPATH="$(dirname "$(dirname "$ARCHTXN_TOOL")")" "$PYTHON" "$ARCHTXN_TOOL" \
      --stage-root "$STAGE" --output-dir "$OUT" --archive-name "$NAME" \
      --expected-test-source-sha256 "${SOURCE_TEST_ROLE_SHA256:-}" \
      >"$ARCHTXN_OUT" 2>"$ARCHTXN_ERR"
); then
  if [ -f "$ARCHTXN_ERR" ] && [ ! -L "$ARCHTXN_ERR" ]; then cat "$ARCHTXN_ERR" >&2; fi
  if { [ -f "$ARCHTXN_OUT" ] && [ ! -L "$ARCHTXN_OUT" ] && [ -s "$ARCHTXN_OUT" ]; } ||
     { [ -f "$ARCHTXN_ERR" ] && [ ! -L "$ARCHTXN_ERR" ] && grep -Eq '"status"[[:space:]]*:[[:space:]]*"(COMMITTED_HOLD|COMMIT_STATE_HOLD)"' "$ARCHTXN_ERR"; }; then
    if [ -f "$ARCHTXN_OUT" ] && [ ! -L "$ARCHTXN_OUT" ]; then cat "$ARCHTXN_OUT" >&2; fi
    echo "HOLD: finalizer failure receipt requires commit/durability review; preserved final path if present: $ARCHIVE; capture: $ARCHTXN_CAPTURE" >&2
    exit 11
  fi
  if [ -f "$ARCHTXN_ERR" ] && [ ! -L "$ARCHTXN_ERR" ] && grep -q 'ARCHTXN-TXN-001' "$ARCHTXN_ERR"; then
    echo "REFUSED: release archive path was claimed before commit; preserved existing path: $ARCHIVE; capture: $ARCHTXN_CAPTURE" >&2
    exit 9
  fi
  if [ -e "$ARCHIVE" ] || [ -L "$ARCHIVE" ]; then
    echo "HOLD: final path is present after finalizer failure; commitment is unverified; preserved path: $ARCHIVE; capture: $ARCHTXN_CAPTURE" >&2
    exit 11
  fi
  echo "REFUSED: finalizer did not report commitment; no final archive path observed; retained capture: $ARCHTXN_CAPTURE" >&2
  exit 10
fi
# Exit zero alone does not prove a receipt was completely delivered or bind its object.
if ! "$PYTHON" - "$ARCHTXN_OUT" "$ARCHIVE" "$NAME" <<'PYRECEIPT'
import hashlib, json, os, pathlib, re, stat, sys
try:
    receipt_path, archive_path = map(pathlib.Path, sys.argv[1:3])
    if receipt_path.is_symlink() or not receipt_path.is_file() or receipt_path.stat().st_size > 1048576:
        raise ValueError("receipt shape")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError("duplicate receipt key")
            result[key] = value
        return result
    record = json.loads(receipt_path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if (set(record) != {"status","error_code","reason_code","final_name","member_count","archive_sha256","archive_bytes","cleanup_state"} or
            record["status"] != "COMMITTED" or record["error_code"] is not None or record["reason_code"] is not None or
            record["final_name"] != sys.argv[3] or record["cleanup_state"] != "TEMP_REMOVED_BY_COMMIT" or
            type(record["member_count"]) is not int or record["member_count"] < 0 or
            type(record["archive_bytes"]) is not int or record["archive_bytes"] <= 0 or
            not isinstance(record["archive_sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", record["archive_sha256"]) is None):
        raise ValueError("receipt contract")
    observed = archive_path.lstat()
    if not stat.S_ISREG(observed.st_mode) or observed.st_size != record["archive_bytes"]:
        raise ValueError("archive shape")
    # Size, byte count and digest must describe one opened regular object generation.
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(archive_path, flags)
    try:
        before = os.fstat(descriptor)
        def identity(value):
            return (value.st_dev, value.st_ino, stat.S_IFMT(value.st_mode))
        def generation(value):
            return (identity(value), value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        if (not stat.S_ISREG(before.st_mode) or before.st_ino <= 0 or
                identity(before) != identity(observed) or
                generation(before) != generation(observed) or
                before.st_size != record["archive_bytes"]):
            raise ValueError("opened archive binding")
        digest = hashlib.sha256()
        byte_count = 0
        while True:
            block = os.read(descriptor, 1048576)
            if not block:
                break
            byte_count += len(block)
            if byte_count > record["archive_bytes"]:
                raise ValueError("archive grew during read")
            digest.update(block)
        after = os.fstat(descriptor)
        selected = archive_path.lstat()
        if (byte_count != record["archive_bytes"] or
                generation(after) != generation(before) or
                not stat.S_ISREG(selected.st_mode) or
                generation(selected) != generation(after) or
                digest.hexdigest() != record["archive_sha256"]):
            raise ValueError("archive generation or digest changed")
    finally:
        os.close(descriptor)
except (OSError, ValueError, TypeError, KeyError, KeyboardInterrupt, SystemExit):
    raise SystemExit(1)
PYRECEIPT
then
  echo "HOLD: finalizer success receipt is missing, incomplete, contradictory or object-unbound; preserved final path if present: $ARCHIVE; retained capture: $ARCHTXN_CAPTURE" >&2
  exit 11
fi

echo "Receipt capture retained: $ARCHTXN_CAPTURE" >&2
echo "OK  $TIER  ->  $ARCHIVE  (v${VERSION}, leak-audited: $([ "$TIER" = merged ] && echo 'n/a (private)' || echo '0 unresolved identifier-policy findings in executed gates; synthetic declarations and exact public references have separate scopes'))"
