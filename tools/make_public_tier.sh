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
PYTHON="${PYTHON:-python3}"

TIER="${1:?tier: code|clean|cohort|merged|public}"; SRC="${2:?source dir}"; OUT="${3:?output dir}"
shift 3
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
PRIVACY_PROFILE=""
while [ "$#" -gt 0 ]; do
  case "$1" in
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

WORK="$(mktemp -d)"
ARCHIVE_TMPDIR=""
cleanup() {
  rm -rf "$WORK"
  if [ -n "$ARCHIVE_TMPDIR" ]; then rm -rf "$ARCHIVE_TMPDIR"; fi
}
trap cleanup EXIT
STAGE="$WORK/sapote-mamey"
mkdir -p "$STAGE"; cp -a "$SRC/." "$STAGE/"

fail_on_backup_debris() {
  local offender
  offender="$(find "$STAGE" -type f \( -name '*-E' -o -name '*.orig' -o -name '*.rej' -o -name '*.bak' -o -name '*~' \) -print -quit)"
  if [ -n "$offender" ]; then
    echo "FATAL: backup/editor debris present in staged source: ${offender#"$STAGE/"}" >&2
    echo "Adjudicate it in the source tree; the tier builder will not silently delete evidence." >&2
    exit 7
  fi
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
    # v9.7.271: the Pfam HMM is CC0 (freely redistributable) and the only other stripped item, the
    # teicoplanin fixtures, were retired for a small public fixture (v9.7.270). There is therefore
    # nothing left that must be withheld from a public release, so the public tier now ships the SAME
    # content as the code tier (HMM included) — it is a labelled alias of code pending the tier reorg.
    # See NOTICE for the CC0 attribution. No strip, no download stubs, no fail-closed HMM check.
    rm -rf "$STAGE/private" "$STAGE/cohort" "$STAGE/merged_cohort" "$STAGE/data" \
           "$STAGE/release2_source_library" "$STAGE/docs/legacy" "$STAGE/offline_deps" 2>/dev/null || true
    strip_internal
    echo "  public tier: ships full content incl. Pfam HMM (CC0) — content-identical to the code tier"
    ;;
esac

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


# --- 2. scrub embedded AS strain IDs (code/cohort/clean only; merged keeps them) ------
# v9.7.95: re-enabled. The maintained CAS-safe redactor scrubs private AS-/AJS-/PENDING- IDs to
# AS-XXX across the staged tree (comments/strings/docs only for .py via tokenizer; full text for
# md/csv/etc.), skipping the whitelist (checksums/manifest/synthetic-ID allowlist) and verifying
# cassette stable-IDs are untouched. --as-only keeps public SID (Chevrette 2019) intact; the clean
# tier leaves SID alone by design (SID is public). Without this the leak audit refuses every public tier,
# because real cohort IDs live in code comments, docs, and the CHANGELOG. merged keeps real IDs.
# v9.7.219 (PI decision, the Developer or User Smith, 2026-07-06): the AS-series cohort is PUBLIC — the
# Hymenoptera paper publishes strain/genus/host/16S/accession for all AS strains, and BGC content is not
# meaningful additional disclosure. The AS-ID scrub is therefore DEACTIVATED by default, so real AS IDs
# (incl. the folded Master_Strain_Table) survive into the public tier. Tier structure is UNCHANGED — all
# four tiers still cut and cross-tier parity still holds (public == redact(private), redact now identity
# for AS). Machinery RETAINED and reversible: set AS_SCRUB=1 to re-arm the scrub for a future private cohort.
# v9.7.364 (PI instruction, the Developer or User 2026-08-12): the AS_SCRUB *rewriting* machinery is REMOVED, not
# merely left deactivated.
#
# SCOPE OF THE REMOVAL, stated exactly, because two different controls shared one flag name:
#   * REMOVED  -- the AS-ID *scrub*: the pass that REWROTE real AS-#### identifiers to placeholders
#                 in the staged tree. Inert at AS_SCRUB=0 since v9.7.219, and a switch that is never
#                 on is a switch nobody tests -- it read as a live control while doing nothing.
#   * RETAINED -- the AS-ID *leak audit* (`_as_leak` / the `--check-only` pass further down): the
#                 read-only control that REPORTS unpublished identifiers found in a staged tier and
#                 can fail the cut. It rewrites nothing.
#
# The distinction is the whole point. A scrub MUTATES the release; an audit OBSERVES it. Deleting a
# mutation nobody runs removes dead weight. Deleting the observation would remove a safety net, which
# is not what was approved -- and the audit is the only thing that would notice if a genuinely private
# identifier ever entered a public tier. Identifier disclosure was never the real exposure anyway
# (AS ids are public; 16S is on GenBank) -- the exposure is unpublished genome FINDINGS in prose,
# which no identifier control of either kind has ever caught. `tools/redact_public_tier.py` is
# RETAINED and stays reusable for a future genuinely-private cohort. It had been inert at AS_SCRUB=0 since v9.7.219 (PI decision, cohort public), and a
# switch that is never on is a switch nobody tests -- it read as a live control while doing nothing.
# AS identifiers are public (16S on GenBank). The real exposure is unpublished genome FINDINGS in
# prose, which no identifier scrub ever caught. `tools/redact_public_tier.py` is RETAINED and stays
# reusable for a future genuinely-private cohort.

# v9.7.390 public-candidate correction: a public tier must be free of project-cohort identifiers
# regardless of whether an older disclosure decision retired the AS leak flag. The redactor is the
# maintained content-rewrite SSOT and skips tests, executable Python, and explicit synthetic/public
# exceptions. Python genericization requires reviewed source patches because string literals may
# be executable data. This documentation/configuration transform is unconditional for every
# non-private tier; AS_SCRUB cannot disable it.
if [ "$TIER" != "merged" ]; then
  "$PYTHON" "$STAGE/tools/redact_public_tier.py" --tree "$STAGE" --walk --as-only \
    || { echo "FATAL: public-tree cohort-identifier redaction failed" >&2; exit 1; }
fi

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
    [ -z "$term" ] && continue
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
# v9.7.156 (PI decision, the Developer or User Smith, 2026-06-30): the AS-series privacy guard is
# RETIRED. All AS strains have 16S on GenBank publicly associating strain/genus/host; BGC content
# is not meaningful additional disclosure; Sapote-Mamey ships concurrent with the publications.
# The AS-ID portions of the leak audit are DEMOTED from FAIL to WARN. The machinery is retained
# (reusable if a future private cohort needs it) — set AS_GUARD_RETIRED=0 to re-arm. All OTHER
# hygiene (private/ tree, internal working docs, denylist terms, SID redaction) stays hard-fail.
AS_GUARD_RETIRED="${AS_GUARD_RETIRED:-1}"
# v9.7.364 NOTE: this AS_SCRUB reference is the LEAK AUDIT, which is a different control from the
# scrub removed above. The scrub REWROTE content; this only REPORTS. the Developer or User approved removing the
# scrub machinery, not disabling a safety net, so the audit is retained as-is. If the AS-disclosure
# decision (GOV-001) is ever repudiated, this is the switch that re-arms hard-fail leak detection.
AS_SCRUB="${AS_SCRUB:-0}"
_as_leak() {   # $1 = message. Fully deactivated when AS_SCRUB=0 (cohort public, PI 2026-07-06);
               # WARN when the guard is retired but scrub armed; hard-fail only when fully armed.
  if [ "$AS_SCRUB" != "1" ]; then
    :   # cohort public — AS leak audit deactivated (re-arm with AS_SCRUB=1)
  elif [ "$AS_GUARD_RETIRED" = "1" ]; then
    echo "WARN (AS guard retired 2026-06-30): $1" >&2
  else
    echo "$1" >&2; FAIL=1
  fi
}
FAIL=0
if [ "$TIER" != "merged" ]; then
  # Non-test files: any AS/AJS/PENDING strain ID is a leak (XXX-redacted placeholders excepted).
  # v9.7.88: matches the scrubber's refined pattern — hyphenated AS-/AJS- (2-4 digits) OR DASHLESS
  # AS + 3-4 digits (covers dashless AS-NNN). It deliberately does NOT match dashless AJS (AJS327 is a public
  # MIBiG organism), 2-digit dashless (AS15 is public), or the LAS-NNN compound-name tail. The
  # synthetic-ID allowlist file is excluded separately.
  if [ "$AS_SCRUB" = "1" ] && ! "$PYTHON" "$SRC/tools/redact_public_tier.py" --tree "$STAGE" --walk --check-only --as-only >/tmp/_public_tier_private_id_check.log 2>&1; then
    head -20 /tmp/_public_tier_private_id_check.log >&2
    _as_leak "private AS/AJS/PENDING identifiers survived in non-test files (redactor SSOT)"
  fi
  # v9.7.88 root-cause fix (audit F-1): tests/ is NO LONGER exempt from the leak audit. The
  # redaction scrub skips tests/ (so the in-tier pytest gate stays passable), which is exactly
  # how real cohort strains shipped in public tiers (the v9.7.86 and v9.7.87 leaks). Tests may
  # contain ONLY documented synthetic IDs (tools/test_synthetic_ids.txt); any AS/AJS/PENDING ID in
  # a test that is not on that allowlist fails the cut. This closes the class instead of swapping
  # one number at a time. The allowlist is verified against the real cohort list out-of-band.
  SYN="$SRC/tools/test_synthetic_ids.txt"
  if [ -d "$STAGE/tests" ]; then
    TEST_IDS="$(grep -rhIoE '\b(AS|AJS|as|ajs)-?[0-9]{2,}|\bPENDING-[A-Z0-9]+' "$STAGE/tests" 2>/dev/null | sort -u || true)"
    while IFS= read -r tid; do
      [ -z "$tid" ] && continue
      # redacted placeholders are always fine
      case "$tid" in AS-XXX|AJS-XXX|PENDING-XXX) continue;; esac
      # uppercase + normalise dashless asNNN/ajsNNN -> AS-NNN/AJS-NNN for the allowlist comparison
      norm="$(printf '%s' "$tid" | tr 'a-z' 'A-Z' | sed -E 's/^(AS|AJS)([0-9])/\1-\2/')"
      if ! grep -qxF "$norm" "$SYN" 2>/dev/null; then
        echo "  (was: non-synthetic strain ID in tests/: $tid, not in tools/test_synthetic_ids.txt)" >&2
        _as_leak "non-synthetic strain ID in tests/: $tid"
      fi
    done <<< "$TEST_IDS"
  fi
  if [ -d "$STAGE/private" ]; then echo "LEAK: private/ present in $TIER tier" >&2; FAIL=1; fi
  for d in NOTES_FOR_ALEX.md SESSION_HANDOFF.md FREEZE_TRIAGE.md PRE_RELEASE_READTHROUGH_LEDGER.md; do
    if [ -e "$STAGE/$d" ]; then echo "LEAK: internal working doc $d present in $TIER tier" >&2; FAIL=1; fi
  done
  DENY="$SRC/tools/release_denylist.txt"   # terms live here, not as literals in this script; stripped from public tiers
  if [ -f "$DENY" ]; then
    while IFS= read -r term; do
      [ -z "$term" ] && continue
      if grep -rIlF "$term" "$STAGE" 2>/dev/null | grep -q .; then
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
# first audit call, after the staged tree has already been stripped and
# redacted.  The no-profile compatibility path remains ordinary CLI handling.
public_release_audit_stage() {
  local audit_flag="${1:-}"
  if [ -n "$PRIVACY_PROFILE" ] && [ -n "$audit_flag" ]; then
    "$PYTHON" "$STAGE/tools/public_release_audit.py" "$STAGE" \
      --privacy-profile "$PRIVACY_PROFILE" "$audit_flag"
  elif [ -n "$PRIVACY_PROFILE" ]; then
    "$PYTHON" "$STAGE/tools/public_release_audit.py" "$STAGE" \
      --privacy-profile "$PRIVACY_PROFILE"
  elif [ -n "$audit_flag" ]; then
    "$PYTHON" "$STAGE/tools/public_release_audit.py" "$STAGE" "$audit_flag"
  else
    "$PYTHON" "$STAGE/tools/public_release_audit.py" "$STAGE"
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

# Independent post-transformation gate. This checks the staged tree, not the source tree, and
# fails on internal future-work material, residual non-test cohort identifiers in content or
# paths, private data roots, workspace paths, and the existing identity denylist controls.
if [ "$TIER" != "merged" ]; then
  # The policy lives in the optional, user-owned privacy profile.  It is read
  # from the source/operator location and never copied into the staged public
  # tree.  This explicit mutation applies only to the disposable stage; plain
  # public_release_audit invocations remain read-only.
  public_release_audit_stage --apply-public-export-exclusions \
    || { echo "REFUSED: public-export policy could not safely exclude staged internal roots." >&2; exit 1; }
  public_release_audit_stage \
    || { echo "REFUSED: staged $TIER tree failed the public-release content audit." >&2; exit 1; }
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

# Some suite gates intentionally regenerate documentation inventories from the staged tree.
# After removing pytest's synthetic-ID cache, reapply the documentation-only privacy transform
# and audit so generated public surfaces cannot reintroduce cohort identifiers. Executable Python
# remains byte-identical.
if [ "$TIER" != "merged" ]; then
  "$PYTHON" "$STAGE/tools/redact_public_tier.py" --tree "$STAGE" --walk --as-only \
    || { echo "FATAL: post-pytest documentation redaction failed" >&2; exit 1; }
  public_release_audit_stage \
    || { echo "REFUSED: post-pytest staged tree failed the public-release content audit." >&2; exit 1; }
  echo "  post-pytest documentation privacy gate: PASS"
fi

# --- 3a. emit per-tier membership manifest (sorted path list) for cross-tier diffing ---
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

# --- 3c. fail-closed invariant: no unpublished AS-### IDs in a public tier ---
# release-health 2026-08-04 (the patch lane): this AS-ONLY invariant must honour AS_SCRUB exactly like the §3
# leak audit above. Under the PI decision (2026-07-06, AS_SCRUB=0) the AS-/Hymenoptera cohort is PUBLIC,
# so surviving AS IDs are EXPECTED, not a leak — running an `--as-only` fail here contradicted that policy
# and refused every code/public cut (the two test_public_tier_strip_v9_7_267 failures). §3 already
# deactivates the AS/AJS/PENDING leak checks when AS_SCRUB!=1; §3c was the one gate left un-gated. This
# aligns them. Machinery retained + reversible: AS_SCRUB=1 re-arms the full AS invariant for a future
# private cohort. `--as-only` never covered AJS-/PENDING-, so nothing else loses protection here.
if [ "$TIER" != merged ] && [ "$AS_SCRUB" = "1" ]; then
  ( cd "$STAGE" && { "$PYTHON" -m pytest tests/test_no_unpublished_ids_in_public_tier.py -q 2>/dev/null || "$PYTHON" tools/redact_public_tier.py --tree . --walk --check-only --as-only; } ) \
    || { echo "FATAL: public-tier unpublished-ID invariant FAILED for $TIER" >&2; exit 5; }
elif [ "$TIER" != merged ]; then
  echo "  §3c AS-ID invariant DEACTIVATED (AS_SCRUB=0, PI 2026-07-06 — cohort public). Set AS_SCRUB=1 to re-arm." >&2
fi

# --- 3d. tier-derivation parity gate (v9.7.97): the public tier must be an exact redaction-view
# of the private source. verify_tier_derivation imports the live redaction SSOT and confirms
# public == redact(private) for every shared content file — catching any file that diverged from
# pure redaction (the class of drift the inlined-copy version used to miss). Scoped to code ONLY:
# code is a pure single-function redaction-view (redact_public_tier.py --as-only).
#
# v9.7.408: the paragraph that stood here described a SID anonymization pass run by the sid tier and
# a matching SID->SID-XXX sed scrub in the clean tier. Neither exists. The SID uniformity scrub was
# REMOVED at v9.7.364 (see the note at the top of section 2) because it was destructive and
# ineffective, and every redact_public_tier.py call in this script passes --as-only, which leaves
# SID alone by design — SID is public (Chevrette 2019). The comment outlived its code by two cuts and
# was live enough to send a v9.7.408 design review down the wrong path before the code was read.
# A comment that describes deleted behaviour is a check that stopped checking, in prose.
#
# The surviving reason this gate is scoped to code alone: clean removes worked outputs on top of the
# base redaction, so it is not a pure redact-view of merged and the derivation check cannot model it.
# Parity for the other tiers is covered by the leak audit and the redaction-correctness checks
# elsewhere in this script.
if [ "$TIER" = code ] && [ -f "$SRC/tools/verify_tier_derivation.py" ]; then
  if verify_code_tier_derivation; then
    echo "  tier-derivation parity gate: OK (public == redact(private))"
  else
    echo "FATAL: $TIER tier is NOT an exact redaction-view of the private source — run" >&2
    echo "  python3 tools/verify_tier_derivation.py . <staged-tier>   # to see the drifting files" >&2
    exit 6
  fi
fi

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
ARCHTXN_TOOL="$(cd "$(dirname "$0")" && pwd)/finalize_public_archive.py"
if [ ! -f "$ARCHTXN_TOOL" ]; then
  echo "FATAL: archive finalizer missing beside make_public_tier.sh: $ARCHTXN_TOOL" >&2
  exit 10
fi
ARCHTXN_ERR="$(mktemp "${TMPDIR:-/tmp}/archtxn.XXXXXX")"
if ! PYTHONPATH="$(dirname "$(dirname "$ARCHTXN_TOOL")")" "$PYTHON" "$ARCHTXN_TOOL" \
      --stage-root "$STAGE" --output-dir "$OUT" --archive-name "$NAME" \
      >/dev/null 2>"$ARCHTXN_ERR"; then
  # Distinguish the two refusal classes rather than collapsing them. Only a claimed destination
  # is the .401 exit-9 case; a build or member-audit failure is a different fault and must not
  # be reported as a concurrent writer, or the operator debugs the wrong thing. The finalizer's
  # own typed refusal is always echoed through — swallowing it would hide the error_code that
  # says which of the frozen ARCHTXN-* conditions fired.
  cat "$ARCHTXN_ERR" >&2
  if grep -q 'ARCHTXN-TXN-001' "$ARCHTXN_ERR"; then
    rm -f "$ARCHTXN_ERR"
    echo "REFUSED: release archive path was claimed before commit; preserved existing path: $ARCHIVE" >&2
    exit 9
  fi
  rm -f "$ARCHTXN_ERR"
  echo "REFUSED: final archive transaction did not commit an audited archive; no object created." >&2
  exit 10
fi
rm -f "$ARCHTXN_ERR"
echo "OK  $TIER  ->  $ARCHIVE  (v${VERSION}, leak-audited: $([ "$TIER" = merged ] && echo 'n/a (private)' || echo '0 private/unpublished AS strain IDs (allowlist-aware; synthetic AS-9xx and public enterocin AS-48 are permitted by design)'))"
