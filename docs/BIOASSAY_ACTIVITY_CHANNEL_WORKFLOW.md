# Bioassay activity-channel workflow — where it sits

Post-seal-adjacent, optional, strain-level. Measured screening data is NOT part of the deterministic run and
does NOT alter scoring; it is admitted as typed context via the bioactivity metadata contract.

1. Build/refresh the 4-concentration reconstruction (owner-confirmed layout: quadrant→concentration order,
   OD controls, omit list). 2. `tools/bioassay_to_activity_channel.py --recon <csv> --out <dir> --validate <tree>`
   emits per-strain `bioactivity_metadata_v1` objects and self-checks them against `mamey.bioactivity_metadata`.
   3. Pass a strain's object to `mamey_run.py run --bioactivity-json`. 4. The engine's claim-safety gate keeps
   downstream text extract-level (never a per-BGC phenotype).

Governance: strain-level only; capacity != production; no BGC attribution; preliminary single-replicate screen
(artifacts expected); judgment deferred.
