# Figure QA on a completed render packet

Run `python tools/figure_render_qc.py <packet-figures> --render-receipt-sha256 <sha256> --out <fresh-qa-folder>` to check a finished render packet against its receipt.

The completed-packet consumer uses one admitted generation. Receipt/member locators stay inside the selected local artifact root; historical transfer paths are never opened. Member reads traverse directory handles with no-follow flags and require regular files. Every consumed PNG, SVG and caption buffer must match its admitted byte count and SHA-256. Content QA uses those buffers rather than reopening mutable packet pathnames. An introduced SVG or caption cannot silently become a new input.

The receipt and complete output roster are revalidated after content QA and immediately before report creation. Drift, removal, new consumed-companion selection or a symlink refuses with exit 2 even under `--warn-only`; no QA reports are created. This is a point-in-time generation check, not a lock on files after QA returns and not independent upstream execution or receipt authentication. An external trusted receipt SHA-256 supplies a separate transfer pin; without it the check establishes self-manifest freshness only.

If OCR is needed for a completed packet, the admitted PNG is explicitly retained in the fresh QA cache under `admitted_pngs/<SHA256>.png`. The OCR command receives that snapshot, with hash checks before and after OCR. Existing matching regular snapshots can be reused; conflicting bytes or symlinks refuse. Reports identify the selected source image, while cache text is keyed by the admitted image hash. SVG-backed QA does not need a PNG snapshot copy. Cache/partial files can remain after a later refusal; they are not a successful QA report.

Destination protection remains independent of receipt validity: existing `RENDER_QC.md` or `RENDER_QC.tsv`, including dangling symlinks, refuses before receipt parsing. Both report destinations are reserved with exclusive creation, so a late collision cannot truncate existing evidence. A second-file collision can leave a new empty first reservation for inspection. For a completed packet choose a fresh child QA folder or a separate sibling folder; the packet root and an ancestor containing bound members refuse. Ordinary pre-completion figure QA without a supplied receipt remains supported. Producer page companions are all written before one folder-wide QA call.

R page runtime/namespace and final-PDF font observations concern rendering only. They do not establish upstream ordination or embedding fitting. Numerical provenance and axis-definition captions are handled separately.

## Runtime capabilities and refusal

Completed-packet reading requires nonzero `O_DIRECTORY`, `O_NOFOLLOW` and `O_NONBLOCK` flags plus `os.open` membership in `os.supports_dir_fd`. The reader checks those advertised capabilities before opening members. A runtime that rejects descriptor traversal despite advertising it returns a typed admission refusal, closes acquired handles and writes no QA reports. There is no fallback to pathname-only reads, following symlinks or omitting hash checks.

Actual native validation covers macOS with the selected CPython runtime. It has not been run on Linux: support is conditional on the same real capabilities and filesystem behavior. Standard Windows Python does not support these `dir_fd` operations, so completed-packet admission is unavailable there. Capability-failure simulations are not native Windows or Linux tests. [Python's OS documentation](https://docs.python.org/3.13/library/os.html#os.supports_dir_fd) describes per-function availability and the platform-dependent flag constants.

Ordinary QA of genuinely unreceipted figures remains available where its image/text dependencies work; it does not establish completed-packet freshness. Do not remove a completed packet's receipt to misrepresent it as an unreceipted generation.

macOS PNG OCR additionally needs a writable Swift/Clang module cache and access to Vision recognition. A private `CLANG_MODULE_CACHE_PATH` can provide the compiler cache without changing the source or using another OCR backend. A sandbox can permit compilation while refusing recognition; keep the resulting text-not-checked state. Require a real recognition check in the permitted native context when OCR is part of acceptance. SVG text checking does not require OCR.
