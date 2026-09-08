#!/usr/bin/env bash
# build_all_deliverables.sh — regenerate default Sapote–Mamey deliverables from the banked cohort,
# then emit each as markdown + PDF + Word into deliverables/.
#
# v9.7.141 C5: fail closed. Earlier versions used `|| true` / "pdf skip" messages and still
# printed "done", which made a partial deliverable suite look complete. This script now records
# every failed phase and exits nonzero if any required report/render step fails.
#
# usage: bash tools/build_all_deliverables.sh [BANKED_DIR] [WORKBOOK]
set -euo pipefail

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
  python3 tools/build_modeb_deepdive.py --banked-dir "$BANK" "${WB_ARGS[@]}" --out "$DD/deep_dives/ModeB_DeepDives_Full.md"

run_required "2/4" "Thesis_Vignettes_ClassA.md" \
  python3 tools/build_thesis_vignettes.py --banked-dir "$BANK" "${WB_ARGS[@]}" --out "$DD/deep_dives/Thesis_Vignettes_ClassA.md"

run_required "3/4" "GCF tags" \
  python3 tools/build_gcf_tags.py --banked-dir "$BANK" --thesaurus resources/gcf_thesaurus.json --out-dir "$DD/analyses" "${WB_ARGS[@]}"

run_required "3/4" "size profile" \
  python3 tools/build_size_profile.py --banked-dir "$BANK" --out-dir "$DD/analyses" "${WB_ARGS[@]}"

mapfile -t markdowns < <(find "$DD" -name '*.md' ! -name 'README.md' | LC_ALL=C sort)
if [[ ${#markdowns[@]} -eq 0 ]]; then
  record "4/4" "markdown discovery" "FAIL" "no markdown files found under $DD"
  failures=$((failures + 1))
else
  record "4/4" "markdown discovery" "PASS" "${#markdowns[@]} markdown file(s)"
fi

for md in "${markdowns[@]}"; do
  pdf="${md%.md}.pdf"
  docx="${md%.md}.docx"
  if bash tools/md_to_pdf.sh "$md" "$pdf"; then
    record "4/4" "$pdf" "PASS" "rendered from $md"
  else
    rc=$?
    record "4/4" "$pdf" "FAIL" "exit=$rc rendering from $md"
    failures=$((failures + 1))
  fi
  if bash tools/md_to_docx.sh "$md" "$docx"; then
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
