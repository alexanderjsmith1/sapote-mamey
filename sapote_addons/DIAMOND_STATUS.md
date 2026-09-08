# DIAMOND fast-path — status and how to enable it

**Status: SPECIFIED_UNVERIFIED.** Gemini's alignment (S4/S5) runs on the proven pyswrd
Smith–Waterman backend by default. DIAMOND is an *optional* speed upgrade, not required for
correctness. No science deliverable depends on it.

## Why it's not vendored here

DIAMOND is a C++ binary (~172 translation units) from `github.com/bbuchfink/diamond`. It is
NOT a pip package — the PyPI package named `diamond` (v4.0.515) is an unrelated defunct 2015
module and must not be installed.

The earlier claim that DIAMOND "won't compile — CMake policy floor" was **wrong and is
corrected**: CMake 4.x configures DIAMOND fine (deprecation warning only), and g++ compiles
the sources. The real blocker in a sandboxed session is that a full `-j2` build exceeds the
per-command wall-clock budget before linking. It is a time/resource constraint, not a
toolchain incompatibility.

## How to enable the DIAMOND fast-path (any ONE of these)

1. **Prebuilt static binary (recommended).** DIAMOND ships prebuilt Linux x86_64 binaries on
   GitHub Releases (`diamond-linux64.tar.gz`). github.com is typically allowlisted. Download,
   extract, put `diamond` on PATH. No compile needed. Gemini auto-detects it.
2. **Compile once outside the time budget, then vendor.** On a box without the per-command cap:
   `git clone github.com/bbuchfink/diamond && cd diamond && mkdir build && cd build &&
   cmake .. && make -j` — keep the resulting `diamond` binary (target cp312 / manylinux x86_64).
3. **Compile in-sandbox with backgrounding.** Launch `make -j$(nproc)` as a background process
   to a log and poll across commands. Feasible but fragile; prefer 1 or 2.

Once a `diamond` binary is available, Gemini's backend selection auto-upgrades
(`diamond → pyswrd → biopython`). To VERIFY and promote the fast-path (per the MAYDAY
checklist): run S5 on AS-XXX × Amel2xC10 through DIAMOND, confirm BGC047 NRPS lands at 96%
identity (matching the validated NCBI BLASTp), confirm the BGC050 lanthipeptide dehydratase
(the k-mer-prefilter false-negative) is recovered, and record the wall-clock speedup.

## The proven backend (what actually runs)

pyswrd 0.3.1 (SIMD Smith–Waterman) + pyopal + Biopython 1.87. This backend reproduced an
independent NCBI BLASTp result (BGC047 NRPS, 96.0% over 2,904 aa) to the decimal. It is
correct and fast enough for a single strain pair; DIAMOND matters only at many-strain scale.
