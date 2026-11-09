#!/usr/bin/env bash
# build_all_deliverables.sh — regenerate default Sapote–Mamey deliverables from the banked cohort,
# then emit each as markdown + PDF + Word into deliverables/.
#
# v9.7.141 C5: fail closed. Earlier versions used `|| true` / "pdf skip" messages and still
# printed "done", which made a partial deliverable suite look complete. This script now records
# every failed phase and exits nonzero if any required report/render step fails.
#
# usage: bash tools/build_all_deliverables.sh [--replace] [BANKED_DIR] [WORKBOOK]
#
# The PDF renderer never replaces an earlier PDF or its sidecars. A rerun into the same
# deliverables/ folder therefore records a FAIL for each existing PDF unless --replace is given.
# With --replace, the earlier PDF and sidecars are moved into a private folder first, restored
# if the new render fails, and deleted only after it succeeds.
# The Word renderer refuses an existing .docx in the same way; --replace is passed through to
# tools/md_to_docx.sh, which replaces the earlier .docx only after the new one is written.
# GCF_Tags.csv is handled like the PDFs: refused without --replace, set aside and restored with it.
set -euo pipefail

REPLACE=0
if [[ "${1:-}" == "--replace" ]]; then
  REPLACE=1
  shift
fi

BANK="${1:-cohort}"
WB="${2:-deliverables/Sapote-Mamey_Master_Workbook.xlsx}"
DD="deliverables"
LOG="$DD/build_all_deliverables_status.tsv"

mkdir -p "$DD/analyses" "$DD/deep_dives" "$DD/reports"
printf 'phase\tartifact\tstatus\tdetail\n' > "$LOG"

failures=0
record() {
  local phase="$1" artifact="$2" status="$3" detail="$4"
  printf '%s\t%s\t%s\t%s\n' "$phase" "$artifact" "$status" "$detail" >> "$LOG"
}
run_required() {
  local phase="$1" artifact="$2"; shift 2
  echo "[$phase] $artifact"
  if "$@"; then
    record "$phase" "$artifact" "PASS" "$*"
  else
    rc=$?
    record "$phase" "$artifact" "FAIL" "exit=$rc :: $*"
    failures=$((failures + 1))
  fi
}

WB_ARGS=()
if [[ -n "${WB:-}" ]]; then
  WB_ARGS=(--workbook "$WB")
fi

run_required "1/4" "ModeB_DeepDives_Full.md" \
  python3 tools/build_modeb_deepdive.py --banked-dir "$BANK" ${WB_ARGS[@]+"${WB_ARGS[@]}"} --out "$DD/deep_dives/ModeB_DeepDives_Full.md"

run_required "2/4" "Thesis_Vignettes_ClassA.md" \
  python3 tools/build_thesis_vignettes.py --banked-dir "$BANK" ${WB_ARGS[@]+"${WB_ARGS[@]}"} --out "$DD/deep_dives/Thesis_Vignettes_ClassA.md"

# build_gcf_tags.py refuses an existing GCF_Tags.csv and has no replace flag. Without --replace an
# earlier file fails this step; with it, the earlier file is set aside, restored if the step fails,
# and deleted only after it succeeds.
build_gcf_tags() {
  local tags="$DD/analyses/GCF_Tags.csv" aside="" rc=0
  if [[ -e "$tags" || -L "$tags" ]]; then
    if [[ $REPLACE -eq 0 ]]; then
      echo "REFUSED: earlier GCF tags exist (rerun with --replace): $tags" >&2
      return 2
    fi
    if [[ -L "$tags" || ! -f "$tags" ]]; then echo "REFUSED: not a regular file: $tags" >&2; return 2; fi
    aside=$(mktemp -d "$DD/analyses/.GCF_Tags.previous.XXXXXX")
    mv "$tags" "$aside/"
  fi
  python3 tools/build_gcf_tags.py --banked-dir "$BANK" --thesaurus resources/gcf_thesaurus.json --out-dir "$DD/analyses" ${WB_ARGS[@]+"${WB_ARGS[@]}"} || rc=$?
  if [[ -n "$aside" ]]; then
    if [[ $rc -eq 0 ]]; then
      rm -f -- "$aside/GCF_Tags.csv"
    else
      if [[ -f "$tags" && ! -L "$tags" ]]; then rm -f -- "$tags"; fi
      mv "$aside/GCF_Tags.csv" "$tags"
    fi
    rmdir "$aside"
  fi
  return $rc
}
run_required "3/4" "GCF tags" build_gcf_tags

run_required "3/4" "size profile" \
  python3 tools/build_size_profile.py --banked-dir "$BANK" --out-dir "$DD/analyses" ${WB_ARGS[@]+"${WB_ARGS[@]}"}

# bash 3.2 (the macOS system bash) has no mapfile, so read the list line by line.
markdowns=()
while IFS= read -r line; do
  markdowns+=("$line")
done < <(find "$DD" -name '*.md' ! -name 'README.md' ! -name '*.wide_tables_appendix.md' ! -name '*.render.md' ! -path '*/.*' | LC_ALL=C sort)
if [[ ${#markdowns[@]} -eq 0 ]]; then
  record "4/4" "markdown discovery" "FAIL" "no markdown files found under $DD"
  failures=$((failures + 1))
else
  record "4/4" "markdown discovery" "PASS" "${#markdowns[@]} markdown file(s)"
fi

render_pdf() {
  # Render $1 to $2. Earlier outputs: refused without --replace; set aside and restored on failure with it.
  local md="$1" pdf="$2" stem="${2%.pdf}" aside="" f rc=0
  local outs=("$pdf" "$stem.resource_bindings.json" "$stem.render_preflight.json" "$stem.wide_tables_appendix.md")
  local existing=()
  for f in "${outs[@]}"; do
    if [[ -e "$f" || -L "$f" ]]; then existing+=("$f"); fi
  done
  if [[ ${#existing[@]} -gt 0 ]]; then
    if [[ $REPLACE -eq 0 ]]; then
      echo "REFUSED: earlier PDF output exists (rerun with --replace): ${existing[*]}" >&2
      return 2
    fi
    for f in "${existing[@]}"; do
      if [[ -L "$f" || ! -f "$f" ]]; then echo "REFUSED: not a regular file: $f" >&2; return 2; fi
    done
    aside=$(mktemp -d "$(dirname "$pdf")/.$(basename "$stem").previous.XXXXXX")
    for f in "${existing[@]}"; do mv "$f" "$aside/"; done
  fi
  bash tools/md_to_pdf.sh "$md" "$pdf" || rc=$?
  if [[ -n "$aside" ]]; then
    if [[ $rc -eq 0 ]]; then
      for f in "$aside"/*; do rm -f -- "$f"; done
    else
      for f in "${outs[@]}"; do if [[ -f "$f" && ! -L "$f" ]]; then rm -f -- "$f"; fi; done
      for f in "$aside"/*; do mv "$f" "$(dirname "$pdf")/"; done
    fi
    rmdir "$aside"
  fi
  return $rc
}

for md in ${markdowns[@]+"${markdowns[@]}"}; do
  pdf="${md%.md}.pdf"
  docx="${md%.md}.docx"
  if render_pdf "$md" "$pdf"; then
    record "4/4" "$pdf" "PASS" "rendered from $md"
  else
    rc=$?
    record "4/4" "$pdf" "FAIL" "exit=$rc rendering from $md"
    failures=$((failures + 1))
  fi
  docx_args=()
  if [[ $REPLACE -eq 1 ]]; then docx_args=(--replace); fi
  if bash tools/md_to_docx.sh ${docx_args[@]+"${docx_args[@]}"} "$md" "$docx"; then
    record "4/4" "$docx" "PASS" "rendered from $md"
  else
    rc=$?
    record "4/4" "$docx" "FAIL" "exit=$rc rendering from $md"
    failures=$((failures + 1))
  fi
done

if [[ $failures -gt 0 ]]; then
  echo "FAIL — build_all_deliverables encountered $failures failure(s). See $LOG" >&2
  exit 1
fi

echo "PASS — deliverables complete in $DD/ (md + pdf + docx). Status log: $LOG"
