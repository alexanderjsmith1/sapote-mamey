# Q013 F14 binding status

Status: `PROVISIONAL_BINDING`; static candidate only; publication refused.

- Observation unit: one admitted BGC row carrying complete `strain / full node-or-contig / region / BGC alias` identity.
- Fixed vector: one-hot `Arch`, `Arch_Capacity`, `Class_Conf`, and semicolon-tokenized product classes.
- Excluded: `AB_auto`, `AF_auto`, and `Novelty_auto`; these are routing priors, not PCA features.
- Transform: binary one-hot matrix, mean-centered before SVD; missing categorical values are explicit `MISSING` levels; no variance scaling.
- Architecture clustering: greedy cosine assignment at threshold `>= 0.85`; the eight most frequent represented clusters receive named colors and every remaining represented cluster is disclosed as `Other`.
- Interpretation: proximity describes this provisional feature encoding only; it does not establish biosynthetic identity, function, or activity.
- Owner action: bind the governed fitted cohort and confirm or replace the fixed vector.

Claim ceiling: descriptive extraction-layer candidate; similarity is not identity; capacity is not production.
