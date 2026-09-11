# Sapote–Mamey v9.7.7 — patch notes (engine 1.9.14)

Two scan/scoring defects fixed, both of which affected prior analysis output. Fixed at the
**true runtime source of truth**, regression-tested, and impact-quantified on the four-strain
validation panel. Engine 1.9.13 → **1.9.14**; bundle 9.7.6 → **9.7.7**.

---

## Bug 1 — halogenase false positive (dehalogenase matched as substring)

**Defect.** The trigger regex was bare `r"halogenase"`, which substring-matches **"dehalogenase"**.
Haloacid/haloalkane *de*halogenases (catabolic housekeeping enzymes, α/β-hydrolase fold) therefore
fired the halogenation `[E-signal]`.

**Root cause (non-obvious).** The bare pattern lived in **six** Python sites — `source_scans.py:23,73,99`,
`mamey_markers.py:40,86`, `mamey_cassettes.py:28` — but patching those did **not** change runtime
behaviour. `source_scans.py` rebuilds its pattern dicts at import from
`bundle_support/registry_inventory_v1.9.4.json` via `registry_detector.build_pattern_dicts()`
(`globals()[name] = dict`, unless `MAMEY_DISABLE_REGISTRY_DETECTOR=1`). The Python literals are a
**dead fallback**; the operative patterns are the registry JSON. The bare `halogenase` lived in three
JSON entries: **MMK-DOM-014** (line 482), **MMK-CCTT-001** (1621), **MMC-003** (2819). This was only
caught because the regression test imports the *runtime* dict, not the literals.

**Fix.** `halogenase` → `(?<!de)halogenase` (negative lookbehind for "de") at all three registry
entries **and** all six Python fallback sites. Case-insensitive (`re.I`) — excludes DE/De/dE/de.
Plurals preserved (no trailing anchor). Other halogenase entries (MMK-CCTT-002, SMK-HAL-001,
SMK-XHAL-001, SMC-006/007) were already safe (prefixed or `manual`).

**Verified impact (CNQ490, the only panel strain with dehalogenase annotations — 5 of them):**

| | v1.9.13 | v1.9.14 |
|---|---|---|
| distinct halogenation-hit loci | 11 | **4** |
| removed | — | 7 |
| of removed: confirmed dehalogenase false positives | — | 4 (haloacid ×2, haloalkane ×2) |
| of removed: α/β-hydrolase-fold relatives (epoxide hydrolase, α/β hydrolase) | — | 3 |
| **real halogenases lost** | — | **0** (verified by product annotation) |

Other strains unaffected (NBC 01746, ATCC 19425 carry no dehalogenase; PLAI 1-1's single dehalogenase
was not in a halogenation hit bucket).

---

## Bug 2 — AB/AF inflation in `score_keywords`

**Defect.** `score_keywords` used a bare `key in text` **substring** test summed over every weight key,
which (a) matched `"polyene"` inside `"arylpolyene"` (an APE-type **pigment** scored as an antifungal),
(b) matched `"t2pks"` inside `"hr-t2pks"` (one locus counted as two classes), and (c) stacked every
nested token, inflating multi-product regions.

**Fix (`mamey/scoring.py`).** Delimited-word matching (`(?<![a-z0-9])key(?![a-z0-9])`) so keys match as
hyphen/space-delimited tokens but not glued substrings; an explicit `PIGMENT_NONLEAD_CLASSES`
exclusion (`arylpolyene`, `ladderane`); and `SUBCLASS_SUBSUMES` so a specific subtype suppresses the
generic it implies (`hr-t2pks` ⊅ `t2pks`, `transat-pks` ⊅ `t1pks`). Legitimate delimited subtypes are
preserved (`azole`/`ripp` in `azole-containing-ripp`, `siderophore` in `ni-siderophore`, `nrps` in
`nrps-like`, `terpene` in `terpene-precursor`).

**Verified impact (canonical case + panel):**
- Inflation case `arylpolyene + nrps + hr-t2pks + saccharide`: AB keyword-sum **46 → 34** (region AB 71 → 59).
- Arylpolyene AF: **18 → 0**. Panel headline: CNQ490 **BGC013** (PKS; arylpolyene) AF **46 → 28**.
- Saccharide / terpene-precursor / PKS-subclass double-counts removed across 4/1/1/2 BGCs per strain.
  Change is surgical, not a wholesale rescore.

---

## Antifungal lead — unaffected

The polyene-macrolide antifungal lead in *Saccharomonospora piscinae* CNQ490
(BGC030/033/034 cross-contig group) is **KCB-coverage based**, independent of both `AB_auto` and the
halogenase scan. Lead-locus scores are unchanged; the find holds. Capacity-level, KCB = similarity.

---

## Tests & versioning
- New: `tests/test_scan_scoring_bugfixes.py` — 6 regression guards (dehalogenase-doesn't-fire incl.
  case/plural; real-halogenase-fires; end-to-end via `_scan_patterns`; arylpolyene-not-AF;
  AB-no-subclass-double-count; delimited-subtypes-preserved). Tests import the **runtime** dict, so they
  guard the registry JSON, not the dead literals.
- Full suite: **54 passed, 3 skipped** (the 3 are the known local-only deep guards).
- Engine `1.9.13 → 1.9.14` (`pyproject.toml`, `mamey/__init__.py`); runtime patterns confirmed in both
  registry-active and `MAMEY_DISABLE_REGISTRY_DETECTOR=1` fallback modes.
- Bundle `9.7.6 → 9.7.7` (`CITATION.cff`, `docs/BUNDLE_CAPABILITIES.md`, reuse-prompt headers).

## Maintainability flag (latent risk)
One bug lived in **6 Python sites + 3 registry-JSON entries** because the halogenase regex is
duplicated across `source_scans.py`, `mamey_markers.py`, `mamey_cassettes.py`, **and** the canonical
registry JSON, with the JSON silently overriding the Python at import. Recommend collapsing to a single
source of truth (registry JSON) and generating the Python literals from it, or deleting the dead
literals, so this class of drift can't recur.
