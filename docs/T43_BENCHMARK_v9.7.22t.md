# T43 diagnostic-trigger benchmark — corrected baseline + word-boundary patch

Build: bundle 9.7.22 / Mamey 1.9.30 / stamp 20260614t · offline run
Scope: the 15 active CCTT diagnostic triggers (`CCTT_PATTERNS` in `mamey/source_scans.py`):
HAL XHAL PHO NUC BLA AMC ENE LAN LASSO THA DKP IDC PTM TET NN.
Firing any one → `TIER_1_DIAGNOSTIC`. (Named "T43" for the 43 triggers the set started as.)

## 1. Method
- Reference set: merged GBKs from both archives (`/tmp/gbks` accession-named + `/tmp/gbks2` compound-named).
- Per compound, fire = union over its GBK family. Regex matched against GBK annotation text
  (stand-in for the engine's `_scan_patterns` over the parsed CDS list).
- Recall set: 14 labeled known-class positives. Precision set: 6 negative controls
  (polyenes / plain NRPS that should trigger nothing).

## 2. Correction to the prior (9/14) benchmark — observed
The earlier 9/14 figure was a **benchmark artifact, not a trigger weakness**:
- staurosporine (IDC), malayamycin (NUC), pyrrolnitrin (HAL) are keyed by **accession** in the
  first archive, so an exact compound-name lookup returned empty and **scored them as misses**.
- "lobophorin" is keyed **"lobophorin CR4"** — same false miss.

When actually scanned, all four fire their expected class. Corrected baseline:

| compound | expect | fires | result |
|---|---|---|---|
| staurosporine | IDC | IDC | HIT |
| nikkomycin | NUC | NUC | HIT |
| polyoxin | NUC | NUC (+PTM*) | HIT |
| malayamycin | NUC | NUC | HIT |
| nocardicin | BLA | BLA | HIT |
| HSAF | PTM | PTM | HIT |
| C-1027 | ENE | ENE (+HAL†) | HIT |
| balhimycin | HAL | HAL (+LAN*) | HIT |
| pyrrolnitrin | HAL | HAL | HIT |
| marinopyrrol | HAL | HAL | HIT |
| albonoursin | DKP | DKP | HIT |
| kijanimicin | TET | TET (+LAN*) | HIT |
| lobophorin | TET | TET | HIT |
| lienamycin | ENE | — | MISS‡ |

**Corrected recall: 13/14 (13/13 if lienamycin is excluded — see ‡).**
\* spurious co-call, cleared by the patch. † correct co-call (C-1027 is chlorinated). 
‡ lienamycin's ENE label is **unverified** — its GBK shows LnmA–G + generic "polyketide synthase",
nothing enediyne-specific. No marker was fabricated to force this hit.

## 3. Bug 1 — LAN false positives (precision) — observed → fixed
`lanm` / `lanc` lacked word boundaries and matched **inside amino-acid translation runs**
(`...AADKMIQVA`**`LANM`**`YTEL...` in lichenysin; `...VSGGD`**`LANM`**`PWPRL...` in streptothricin).
L-A-N-M and L-A-N-C are valid residue runs.

**Fix:** `\b` on the six **amino-acid-spellable** short CCTT tokens only:
`lanc lanm hsaf cdps creE creD`.
Tokens containing B/O (`fkbh dois btrc ycaO`) were **left unbounded** — they cannot occur in a
translation, so they carry no substring-FP risk, and bounding `fkbh` broke lobophorin's real
TET hit (`FkbH-like protein`). Principle: bound iff the token is spellable in the 20 AA letters.

## 4. Bug 2 — recall — NOT a bug
The recall gap was the §2 benchmark artifact. Triggers achieve 13/13 on present, labeled,
class-confirmed compounds. The marker-backing pass was therefore **not performed**: forcing a
marker onto lienamycin (label unconfirmed) would be fitting to a bad label.

## 5. Before / after (patched patterns)
| metric | before | after |
|---|---|---|
| recall (present labeled) | 13/13 | 13/13 (held) |
| neg-control FPs | 2/6 | **0/6** |
| within-hit spurious classes | 4 | 1 (c-1027→HAL, correct) |

Cleared by `\b`: lichenysin→LAN, streptothricin→LAN (neg FPs); polyoxin→PTM (hsaf),
balhimycin→LAN, kijanimicin→LAN (spurious). HSAF still fires PTM (standalone `HSAF`); lobophorin
still fires TET (`fkbh` left unbounded).

## 6. Landing — three synced artifacts (Worst-#8 instance)
The CCTT patterns are mirrored in three parity-guarded places:
1. `mamey/source_scans.py` — `CCTT_PATTERNS` literals (edited).
2. `bundle_support/registry_inventory_v1.9.4.json` — `mamey_cctt` library `targets[].value` `|`-alternations
   (bounded **only** in `library=="mamey_cctt"`; a global pass collaterally bounded the
   `mamey_cassette` lanthipeptide/polyene_ptm_hsaf entries and was reverted to restore parity).
3. `docs/MARKER_CATALOG.generated.json` — regenerated via `tools/gen_marker_catalog.py`.

Parity guards that enforce the sync: `tests/test_b2_registry_parity.py`
(`REGISTRY_DETECTOR_ACTIVE=True`, so `ss.CCTT_PATTERNS` is built from the JSON) and
`tests/test_marker_catalog.py`.

## 7. Verification
- All four tiers, full suite, no regression: **CODE 536 · CAF 534 · SID 536 · MERGED 535** passed.
- New guard `tests/test_cctt_word_boundaries.py` (3 tests) in all tiers.
- Teeth proven: reverting `\blanm\b`/`\blanc\b` in the **active registry** fails
  `test_lan_does_not_fire_on_translation_substring`; restored → green.

## 8. Status / not done
- Fix + guard landed and green in the working tiers. **Not yet packaged** as a new build cut
  (no build-letter bump / zip / checksums / public-tier leak audit).
- `mamey_cassette` carries the same unbounded `lanm`/`lanc`/`hsaf` tokens; left as-is
  (out of CCTT scope, needs its own validation) — flagged as a follow-up.
- lienamycin class label needs literature verification before any ENE marker is considered.
