# Sapote–Mamey — front-facing docs

One folder, current versions, for the documents a user actually opens. Everything here tracks the shipped bundle version. The reading ladder is **Quick Guide → User Manual → Encyclopedia**, with one **Glossary** as the single source for term definitions.

| # | document | what it's for |
|---|---|---|
| 02 | **Quick Guide** (`02_Quick_Guide.md`) | start here — **installation** (§0), run command, key flags, deliverable menu, and **Useful commands** (natural-language triggers). |
| 01 | **User Manual** (`01_User_Manual.md`) | consolidated operating manual: **§2 install** (Python, bundle, add-on wheels, bundle tiers, verification) → running a strain → reading output (boards, Mode B, receipt persistence) → configuration → engine internals. |
| 03 | **Technical Manual / Encyclopedia** (`03_Technical_Manual_Encyclopedia.html`) | the deep reference: engine internals, detection, scoring, deliverables, the merge. Open in a browser. Carries inline `(v9.7.X)` grounding tags per section; scoring sections current to v9.7.147. |
| 04 | **Glossary pointer** (`04_Glossary.md`) | points to the single canonical `docs/GLOSSARY.md`; it intentionally contains no duplicate definitions. |
| 06 | **Concepts Q&A** (`06_Concepts_QandA.md`) | the conversational "why does it work this way" companion — pipeline concepts (the Mamey/Sapote split, the ten scans, claim-safety, scoring boundaries, the engine internals) answered in plain language. Complements the Glossary's clipped definitions; a running document. |
| — | **June 2026 Newsletter** (`07_Newsletter_June_2026.html`) | first-edition newsletter: pipeline introduction, feature overview for v9.7.119–v9.7.147, science spotlight, deliverable menu. Open in a browser. |
| — | **Common Mistakes** (`../COMMON_MISTAKES.md`) | the most frequent errors: wrong ZIP type, stale antiSMASH, accession labels, missing deps, workbook conflicts — read this first if something goes wrong. |

*Current as of bundle v9.7.414 / engine Mamey 1.9.152. The reading ladder is Quick Guide → User Manual → Encyclopedia + one Glossary; newsletter per major arc. Update these in place each release.*
