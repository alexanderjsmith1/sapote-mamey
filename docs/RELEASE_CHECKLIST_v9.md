# Release review checklist for the current bundle

Use [CUT_PROTOCOL](../CUT_PROTOCOL.md) for the separately authorized cut workflow. This checklist
supports engineering review; it does not grant a version bump, build, disabled-tier override,
release seal, disclosure or publication. The previous v9.4-era checklist's smoke mode, test counts,
four-tier outcomes and automatic full-deliverable defaults are historical and cannot be adopted as
current acceptance evidence merely because its footer was restamped.

## Bind the intended object and scope

- [ ] Record the actual source path/tree digest, engine/bundle/build identities and requested operation.
- [ ] Distinguish reviewed source, prepared candidate, staged tier, published archive and extracted archive.
- [ ] Retain owner decisions separately from machine status labels and document unresolved holds.
- [ ] Use CODE-only default; any retired tier/promotion requires its own explicitly selected scope.
- [ ] Keep original inputs immutable and perform authorized source preparation in a candidate copy.

## Documentation and source contracts

- [ ] Current human landing, AGENTS contract and task router agree on discoverable workflow and permissions.
- [ ] Preserve generator ownership: CLAUDE/AGENTS bootstrap, command/tool catalogs, deliverable menu,
  release manifest, wiki mirrors and source/tier integrity each use their owning generator.
- [ ] Select current Mode B contract and authored-file verifier; legacy section counts are not current gates.
- [ ] Python/source-declared run mode is gold; standard is a deprecated alias and smoke is removed.
- [ ] Copy emitted scan/channel/recovery states from bound receipts; do not use old prompt code lists to relabel them.
- [ ] Bind the actual master workbook schema and operation; legacy schema examples do not prove a current merge passed.
- [ ] Record optional missing capabilities and unrun evidence explicitly instead of filling biological negatives.

## Verify the prepared source

- [ ] Capture version/generator checks, configured test command, environment, exact outcomes and limitations.
- [ ] For release_cut's normal path, distinguish convergence baseline from final successful configured suite.
- [ ] For external validation, bind its exact prepared tree and structured hash-pinned receipt plus log,
  node-ID list and per-node outcomes outside that tree; report freshness and all declared outcome counts.
- [ ] Do not substitute a free-text pass count, source filename or environment bypass for observed run evidence.
- [ ] Required failures block the applicable step; listing them as a “known limitation” is not a blanket waiver.

The external receipt verifier compares artifact/hash/state consistency. It does not run the suite,
authenticate its author, or establish scientific/release acceptance. The low-level tier builder can
technically skip pytest using SKIP_INTIER_PYTEST; the normal release orchestrator also uses this child
bypass after its source testing. Document the real phase and consult CUT_PROTOCOL for the permitted
entry point rather than claiming every staged-tier test ran.

## Optional cut-audit helper scope

`tools/cut_audit.py` has two separate operations. It does not authorize adopting,
sealing or publishing a cut.

```bash
python tools/cut_audit.py verify --tree '<reviewed-tree>' --python '<selected-python>' --zip '<archive.zip>' --sha256 '<archive-checksums.txt>'
```

`verify` runs the supplied tree's checksum check and `tools/sync_version.py --check`
when those files exist. Missing checksum/version-check files are reported as SKIP
and do not themselves fail verification; even an absent tree can reach PASS when
all selected checks are skipped. The ZIP hash check runs only when both archive
arguments are supplied. Its checksum-file lookup uses the archive basename as a
substring, not exact manifest-member admission. Require the intended tree and
check files, review every skip, and independently verify exact checksum membership
and archive identity. Exit 0 is not complete cut, extraction or release acceptance.

```bash
python tools/cut_audit.py rebase-verify --base '<reviewed-tree>' --card '<patch-card>' --tests '<selected-test-path>' --python '<selected-python>' --timeout '<seconds>'
```

This operation makes two whole-tree temporary copies, applies sorted top-level
`.diff`/`.patch` files, copies top-level `test_*.py` files into both trees and runs
pytest in each. It is an execution/copy operation, not a read-only card review.
Before selecting it, confirm the authorized test scope, scripts/dependencies,
storage estimate and need for full copies. Do not replace a modified-files-only
documentation patch review with this whole-tree harness by default.

Use `--tests` to select scope; without a nonempty selection it runs `tests/`.
`--run-slow` is included automatically. `--full` shown in the helper's introductory
example is not a parser option. The harness does not add `--run-network`, but this
is not proof that all selected test bodies are offline or free of external writes.
Retain the separately authorized execution scope.

Rebase exit 1 means patch application failed or new parsed FAILED/ERROR node IDs
were found. Exit 2 means a suite timed out with no new parsed IDs; new failures can
still produce exit 1 during timeout. Exit 0 means no new parsed IDs and no detected
timeout. Other nonzero pytest exits are not independently checked for a valid,
complete test run. Do not accept a clean delta when collection, invocation or
process execution failed, or when required tests were skipped. Matching failure
IDs in both copies do not prove equal failure causes or validate the base.

Capture full subprocess logs, actual codes, admitted node roster/skips and
before/after source bindings separately. The helper emits summaries, not a saved
structured validation receipt. Temporary copies are removed by default; `--keep`
retains them. Its delta report does not replace the hash-pinned external validation
receipt or other required release gates below.

## Duplicate dictionary-key gate scope

For an explicitly selected source review, request the **duplicate dictionary-key
gate** and bind its exact Python source roots:

```bash
python tools/check_duplicate_dict_keys.py --root '<source-directory>' --strict --json
```

Default roots are `mamey`, `tools` and `tests` relative to the current directory.
Directory discovery selects case-sensitive `.py` filenames and prunes
`__pycache__`, `_vendor`, `.git`, `node_modules`, `build` and `dist` by directory
name. Explicit regular-file roots are parsed regardless of suffix. Prefer
nonoverlapping roots and retain selected/excluded paths and source hashes;
`files_scanned` counts encountered files, not necessarily distinct files or
successful parses.

Exit 1 reports detected unallowlisted collisions; exit 2 covers missing roots,
zero encountered files or directory-walk failures. Individual file-read failures
can instead raise exceptions. A syntax-error file currently yields no collision
findings and still contributes to the file count. A nonempty collection of such
files can therefore satisfy the file-count admission while detecting nothing.
Capture diagnostics and independently establish parse coverage before accepting
PASS. JSON output reports collisions and file count, not a saved source-bound
completion receipt.

The checker compares hashable literal keys using Python equality, including
collisions such as `1`/`True`/`1.0`. Computed keys and dictionary expansions are
outside its detection scope. Literal `None` is also currently skipped because it
shares the unknown-key sentinel, so repeated `None` keys can escape the gate.
Reported entry counts concern tracked literal keys, not every literal entry or
runtime construction. PASS does not establish absence of all overwrites,
valid execution or data integrity. The current source allowlist is empty;
`--strict` ignores any future configured allowlist. The historical three-site
allowlist narrative in the helper's introduction is not current acceptance
scope or disclosure authority.

## Module-inventory gate and manifest ownership

```bash
python tools/check_module_accretion.py --json
```

The gate uses the bundle containing the script. It compares discovered `mamey/**/*.py` membership with paths parsed from `SOURCE_CHECKSUMS_SHA256.txt`; the editable `MODULE_MANIFEST.txt` is not its comparison baseline. The checksum reader admits digest format and duplicate raw path checks, not actual source-byte hash equality or full checksum-path containment. Preserve independently verified baseline identity and the intended module roster (`tools/check_module_accretion.py:43–108`).

Current discovery excludes `__pycache__`; missing/empty module roots can yield zero current modules without a traversal error. Removed modules are reported but do not make the gate fail. A parse/read error while extracting a docstring becomes `(no docstring)` and the module remains counted, without a separate failed-file state. A normal exit 0 therefore means no unjustified additions, reported directory-walk errors or baseline-parser errors under this membership check; it does not prove a complete, runnable or intact bundle. Inspect counts, removals and independent source/read/parse coverage (`:52–77,157–218`).

Justification takes basenames from `Consolidates:`/`Accretion-justified:` lines in the first recognized top-level version entry. One basename can justify distinct same-named modules under different subdirectories. The checker does not admit the entry's version against the selected cut or establish a real consolidation/reason. If no version header is recognized, it uses the first 4,000 characters. Review exact full paths, selected current entry and rationale independently (`:111–130,167–175`).

`--write` is a separate direct overwrite of `MODULE_MANIFEST.txt`, not a read-only check. It can write a zero-module inventory and it does not update `SOURCE_CHECKSUMS_SHA256.txt`; consequently it does not clear a checksum-baseline addition merely by regenerating the editable manifest. The older source usage/remediation suggesting that writing the manifest resets this gate is not its current behavior. Select writes only as part of the authorized versioned cut procedure, preserve prior metadata and validate inventory before publication. Neither mode saves a structured input-hash receipt; JSON is emitted to stdout. Record actual command, inputs/hashes, complete diagnostics and exit status into a fresh disjoint destination. Unexpected read/write errors may prevent a complete report (`:133–154,211–233`).

## Verify the tier and archive

- [ ] Record exact selected tier, derivation/content/governance/version/strict-membership gates and their scope.
- [ ] Verify final staged bytes and the actual archive transaction result; do not assume source success proves archive success.
- [ ] Bind archive hash, extract to a clean review location and run the separately required complete artifact checks.
- [ ] Inspect differences in node outcomes and skips, not only aggregate pass counts; unexplained failures remain holds.
- [ ] Record child in-tier tests as RAN, SKIPPED or NOT VERIFIED using actual cut logs.
- [ ] Verify checksum membership/completeness as well as every listed digest; a partial listed-file check is insufficient.
- [ ] Keep source, stage and extracted-archive receipts separately identifiable; preserve failed/superseded evidence.

## Human handoff and owner decision

- [ ] Lead with candidate behavior, review scope, changed files, verification and unresolved holds.
- [ ] State what is implemented, generated, tested, inspected and accepted as separate claims.
- [ ] Report whether an archive was published, refused or retained under recovery hold; none implies release seal.
- [ ] Document scientific claim ceilings, exact locus identities, denominator/source boundaries and privacy scope.
- [ ] Retain independent owner authorization for sealing, PUBLIC_RELEASE promotion and distribution.

Use the actual manifest/logs for counts and states. No historical test total, layout, DOI placeholder,
promotional label or signed-looking metadata substitutes for this evidence.

## Version reference

*Sapote-Mamey Bundle v9.7.449 | Active controller: docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md*
