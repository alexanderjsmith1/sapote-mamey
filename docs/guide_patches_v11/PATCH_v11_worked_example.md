# PATCH — worked-example update brief
## Keep S. amethystogenes as the User Guide spine; carry it forward to v9.7.23

> The reproducible worked example — *Streptosporangium amethystogenes* subsp. *fukuiense*
> (GCA_042665875.1), a public NCBI type strain — is the single best feature of the User Guide.
> It runs through the whole pipeline (handshake → batch plan → triage board → Mode B → package)
> so a reader sees the real artifact at every step. **Keep the strain; keep the spine.** This
> patch updates what the example *shows* so it reflects the current engine, and adds the one
> thing the v8.9.9 run could not show: the architecture-capacity call.
>
> Two routes, your choice:
> 1. **Minimal** — leave the v8.9.9 transcript in place, add a short "what's new since this run"
>    sidebar at each step noting the current behavior. Fastest; preserves the real transcript.
> 2. **Re-run** — run GCA_042665875.1 through the current engine and replace the transcript with
>    a fresh one. Cleaner; costs a real run. Recommended once the engine is settled post-merge.
>
> The edits below are written for route 1 (sidebars), and convert directly to route 2 if you re-run.

---

## §7.2 The intake handshake — what to update

The annotated handshake teaches well and its *structure* should be kept. Update the specifics:

- **antiSMASH version** "v8.0.4" → whatever the re-run uses; note it explicitly.
- **Sheet count / depth-floor** "(v8.9.9 depth floor)" → current.
- **[ADD] a line for the architecture layer.** The v8.9.9 handshake had no architecture-capacity
  step; the current one does. Add to the assembly summary block:

  > *Architecture-capacity layer: active. Each cluster will receive a capacity call (HIGH/MODERATE/
  > LOW) from its backbone, module counts, and tailoring constellation — independent of whether a
  > keyword marker fires or a KnownClusterBlast anchor resolves.*

- **[KEEP]** the "what to look for" callouts (Completeness LOCK, region GBKs present,
  default-assumed MRSA+Candida, 100% Interior). All still correct and well-explained.

This strain is an ideal architecture-layer demonstration because it is 100% Interior with a clean
10 Mb assembly — every cluster is fully observed, so the architecture call is made on complete
machinery rather than fragments. Worth saying so in the sidebar.

## §7.4 Reading the triage board — what to update

The top-3 board (BGC09 mannopeptimycin glycopeptide, BGC24 polyene macrolide, BGC48 orthosomycin)
is a strong illustration and the chemistry is sound. Two updates:

- **[ADD] an architecture-capacity column** to the board. For these three the architecture call
  and the marker/KCB evidence agree, which is itself the point worth making — when all three
  detectors converge, confidence is highest. Suggested addition to each row:
  - BGC09 → *capacity consistent with glycopeptide (HIGH)* — the 6+-module NRPS with halogenase
    and the enduracididine markers is exactly the glycopeptide architecture rule.
  - BGC24 → *capacity consistent with large modular PKS / polyene (HIGH)* — the high KS count.
  - BGC48 → *capacity consistent with glycosylated antibiotic (HIGH)* — the 9× glycosyltransferase
    constellation.
- **[KEEP — this is the jewel]** The **BGC48 pulvomycin-override story** stays exactly as written.
  It is the best single teaching moment in the guide: antiSMASH's KnownClusterBlast called
  "pulvomycin" at 8% similarity (shared deoxysugar enzymes, not a real class relationship), and
  the domain evidence — 9× TIGR04516 glycosyltransferases, class-definitive for orthosomycin —
  overrode it. Keep the narrative intact; it teaches claim-safety better than any assertion could.

  **[ADD] a one-line modern echo** after it: *The same principle now operates at the detector
  level — the architecture layer calls BGC48's class from its glycosyltransferase constellation
  directly, independent of the KCB label, which is why a wrong KCB name no longer drives the call.*

## §7.5 Inside a Mode B report — what to update

The eight-section Mode B structure (§1 overview → §8 claim-safety audit) is current and correct;
keep it. The BGC24 isolation protocol (extract at pH 6–7, monitor UV 300–380 nm, compare against
nystatin/amphotericin/candicidin standards) is good chemistry and stays.

- **[ADD]** a note that the §1 overview line now carries the architecture-capacity call and its
  confidence grade alongside the KCB hit and the novelty score — so a reader sees, in one line,
  what the cluster resembles (KCB, similarity) *and* what its architecture says it is (capacity).

## §7.6 The output package — what to update

This needs the most work because the package contract changed.

- **[VERSION]** "25 sheets" → confirm current sheet count against the live workbook generator.
- **[CONCEPT]** Reframe the package as the *Mamey sealed package* with the *Sapote deliverables*
  built on top — the v8.9.9 guide treated them as one undifferentiated output. The sealed package
  is the deterministic, checksummed evidence; the compiled PDF, the dual-track DAPR table, the
  layperson guide, and the bench guide are judgment-layer products.
- **[ADD] the honest gap, stated plainly:** the sealed package today ships the machine-readable
  files and the workbook but no reader-facing PDF or figures; the deterministic strain-brief
  renderer is the in-progress addition that closes it. (This is the same note as the package
  patch — keep the wording consistent across documents.)
- **[KEEP]** the Project Memory Snapshot and Run Transcript descriptions — still accurate and still
  the right continuity/audit story.

## §7.3 The batch plan — what to update

- **[KEEP]** the priority-ordering logic (Tier-1 diagnostic markers first, then high KCB, then
  interior clusters) — still how batching works, still well-explained.
- **[ADD]** one line that the architecture-capacity call now contributes to priority alongside the
  marker and KCB evidence, so a marker-invisible cluster with a HIGH-confidence architecture call
  can earn an early batch slot it would have missed under the v8.9.9 logic.

---

## What NOT to change in §7

The reproducibility framing — "any reader can download GCA_042665875.1 from NCBI, run it through
antiSMASH, and follow this section" — is the whole value of the worked example and must survive
every edit. If you take the re-run route, re-run *this exact public strain* so the example stays
reproducible by a reader with no access to lab data. Do not swap in an AS strain: the worked
example must be public, both for reproducibility and because the public/unpublished guard forbids
an AS strain in a shared guide.
