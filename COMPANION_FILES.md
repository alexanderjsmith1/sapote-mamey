# COMPANION FILES — what travels alongside this bundle

**Read this before telling the user a capability is unavailable.**

Sapote–Mamey is never shipped alone. By design it depends on companion files — genome
FASTAs, antiSMASH result archives, vendored Python wheels, optional binaries, and reference
clusters — that are **attached separately in the chat, not packed inside this zip.** The most
common failure mode is: the user forgets to attach one, and the assistant concludes the
feature "isn't available" when it simply wasn't uploaded (or didn't land).

## The rule

If a task needs one of the companion files below and you don't see it in the uploads:
**do NOT report the capability as unavailable or unsupported.** Instead, tell the user
exactly which file you're missing and ask them to attach it — name the file. Assume "forgot
to attach" before "doesn't exist." Only after the user confirms a file genuinely isn't
available should you treat that capability as blocked, and even then say what it would enable.

## Two bundles travel together

To keep pipeline cuts lean, the heavy static wheels are split into a SEPARATE addon bundle:

1. **This bundle (Sapote–Mamey)** — the engine, all `mamey/` modules, tools, tests, prompts,
   docs, `install_sapote_addons.sh`, and the Gemini docs (`sapote_addons/README_OFFLINE_ANALYSIS.md`,
   `DIAMOND_STATUS.md`). Lean; changes every cut.
2. **The `sapote_addons` addon bundle** (`sapote-addons-<date>.zip`, ~53 MB) — the vendored
   Python wheels (pyrodigal, pyfastani, pyswrd, pyhmmer, pyskani, pyfamsa, matplotlib, ijson,
   pytest, and the rest) + their MANIFESTs. Static; changes only when the wheels change.

**Both must be attached.** To install the offline stack: extract the `sapote_addons` addon
alongside this bundle, then run `bash install_sapote_addons.sh` (it auto-locates the wheels,
or pass the path: `bash install_sapote_addons.sh /path/to/sapote_addons/wheels`).

If the addon bundle is missing, the Gemini/analysis stack can't install offline — but that's
a **missing attachment, not a missing feature**: tell the user to attach the `sapote_addons`
zip. Do NOT report Gemini as unavailable.

## What travels ALONGSIDE (attached separately — ask if missing)

| Capability the user may ask for | Companion file(s) needed | If absent, say… |
|---|---|---|
| Run Mamey on a strain | that strain's **antiSMASH result ZIP** (region GBKs + clusterblast/ subclusterblast/ knownclusterblast/ txt) | "I need the antiSMASH output ZIP for <strain> — please attach it." |
| Gemini two-strain comparison S5/S6 (per-BGC similarity, comparator recovery) | **two antiSMASH ZIPs** (strain A + strain B) | "I have the pipeline; I need both strains' antiSMASH ZIPs to compare." |
| Gemini S1/S2 (proteome + whole-genome ANI) | **two whole-genome FASTAs** (`.fasta`/`.fna`) | "ANI needs the genome FASTA assemblies for both strains — please attach them." |
| DIAMOND fast-path (optional speed) | a prebuilt **`diamond` binary** on PATH (NOT vendored; see DIAMOND_STATUS.md) | "DIAMOND isn't attached; I'll use the proven pyswrd backend unless you provide the binary." |
| KCB / MIBiG reference comparison | the relevant **MIBiG cluster ZIP(s)** or reference antiSMASH archive | "I need the MIBiG reference ZIP for <accession> to compare against." |
| Master-workbook cross-strain work | the **Master Hub .xlsx** | "Please attach the master workbook so I can update/read the cross-strain sheets." |
| 16S species cross-check (Gemini S3) | a **16S sequence** for the strain | "Attach the 16S sequence if you want the independent species check." |

## Quick self-check when a request seems blocked

1. Is the needed input a companion file from the table above?
2. Is it actually in the uploads, or am I assuming?
3. If not present → name it and ask. Do not say "unsupported."

The pipeline being in your hands means the *capability* is present. Missing data is a
missing attachment, not a missing feature.
