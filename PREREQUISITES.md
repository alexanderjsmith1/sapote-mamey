# PREREQUISITES — Sapote–Mamey v9.7.414

Everything you need to run the bundle, organized for a **manual / offline install**
(no network on the run machine). Pip add-ons are installed by hand; system tools are
installed once per machine.

---

## 0. TL;DR — what you actually have to do

Most of this is already handled. In short:

- **ijson — nothing to do.** A pure-Python copy ships **vendored** inside the engine
  (`mamey/_vendor/ijson`). Bounded/full JSON streaming works offline automatically, with or
  without a system install. The per-run banner shows `ijson(system)` or `ijson(vendored)`.
- **openpyxl, numpy, matplotlib — usually already present** in a Claude container, but they are
  **required** (openpyxl for workbooks; numpy+matplotlib for figure deliverables). If the startup
  banner flags one with ✗, install it — it's a 5-second drop-in (links below).
- **biopython — optional for the run/analysis path.** A built-in shim (`mamey/_gbk_shim.py`)
  parses standard antiSMASH GBKs without it, so `mamey run`/`validate`/`doctor` and every other
  command work without it. The one exception is **`mamey triage-raw`** (pre-extraction genome
  triage), which uses `Bio.SeqIO` directly and reports a clear "install biopython" message if it
  is missing; the HMM walk under `mamey hmm-adjudicate` likewise needs it. Install it for those.
- The bundle's **`offline_deps/`** folder (MERGED and SID tiers) carries the wheels; run
  **`bash offline_deps/bootstrap_offline.sh`** to install them all from local files, no network.
- **Guardrail hooks (`hooks/*.sh`) need only bash + python3 — no `jq`.** Since the v9.7.402
  jq-family port, every shipped hook parses its payload with python3's stdlib (jq is absent in
  clean/container shells and is deliberately not a dependency). Locked by
  `tests/test_hooks_jqless_path_v97402.py`.
- **CairoSVG needs a native Cairo library for SVG-to-PNG conversion.** Installing the Python
  package alone is not sufficient. Figure Factory's dependency-free renderers still emit their
  native SVG/data/caption set when Cairo is unavailable, and their QA receipt records
  `NATIVE_SVG_UNAVAILABLE`; a PNG sibling is not claimed in that state. See section 4.

**Every run prints a dependency line** so you (and Mamey) always know what's active:
```
  deps: openpyxl✓ | ijson(vendored)✓ JSON streaming on | figures✓ | biopython—(optional; shim in use)
        offline installs in offline_deps/ (bash offline_deps/bootstrap_offline.sh) — see PREREQUISITES.md
```

### Install links (if you ever need to fetch a wheel yourself — all quick, all small)
| Package | Why it's useful | PyPI / site |
|---|---|---|
| **pytest** | **runs the 1540-test safety suite; required for cut gates** | https://pypi.org/project/pytest/ |
| openpyxl | writes the master workbook & all `.xlsx` | https://pypi.org/project/openpyxl/ |
| numpy | figure tools (FULL-ANALYSIS deliverables) | https://pypi.org/project/numpy/ |
| matplotlib | figure tools | https://pypi.org/project/matplotlib/ · https://matplotlib.org |
| pandas **(required for figures)** | mamey-native figure set; Mode B ledger DataFrames (graceful fallback to a list-of-dicts when absent) | https://pypi.org/project/pandas/ |
| biopython *(optional)* | sturdier GBK parsing on odd inputs | https://pypi.org/project/biopython/ · https://biopython.org |
| ijson *(vendored — usually skip)* | faster JSON streaming if you want the C backend | https://pypi.org/project/ijson/ |
| pandoc *(system)* | Markdown → PDF/DOCX deliverables | https://pandoc.org/installing.html |

> **pytest in LLM sessions (Claude / ChatGPT).** The test suite needs pytest + pluggy + iniconfig.
> These are small, pure-Python packages (~2 MB total). Download the wheels from PyPI on any
> networked machine and **upload them directly into the chat session** — installation takes under
> 2 minutes. Without pytest, the cut gates (`make_public_tier.sh` post-cut invariant) cannot run,
> and the Patch Chat cannot verify a cut. **Always upload pytest wheels at session start when
> cutting a release.**

To grab a wheel on a networked machine for later offline drop-in:
`pip download openpyxl numpy matplotlib biopython -d offline_deps/` — then copy `offline_deps/` to the
run machine and install with `bash bootstrap.sh --wheels offline_deps/` — the bundled `bootstrap.sh` offline mode (`--no-index --find-links`). The separate offline bootstrap helper is not in the CODE tier; use the bundled command above.

---

## 1. Quick reference — what each dependency is for

| Package | Type | Needed for | If missing |
|---|---|---|---|
| **openpyxl** ≥3.1.2 | pip (core) | All `.xlsx` I/O, master-workbook generation | Engine cannot write workbooks — hard fail |
| **ijson** ≥3.2.0 | **vendored** (pure-Python) | `json_mode='bounded'` (default): RiQ scores, A-domain specificities, extended KCB | **Ships in-bundle — no action.** (A system install just adds the optional faster C backend.) |
| **matplotlib** ≥3.7 | pip (figures) | Every figure tool (`tools/build_*figure*.py`, `export_figure_ready.py`, `render_dapr_boards.py`, `build_normalization_matrix.py`) | Figure tools raise `ModuleNotFoundError` — **hard fail, no fallback** |
| **pandas** ≥2.0, <3.0 **(required for figures; optional for §28 ledgers)** | pip (figures + ledgers) | mamey-native figure set; workbook-backed plots; Mode B §28 ledger DataFrame builders in `mamey.mode_b.evidence_ledgers` | Figure subset and `to_excel()`/`merge()` paths fail; the §28 ledger builders **degrade gracefully** to a list-of-dicts fallback (v9.7.151+) so writing §28 prose + a markdown table works without pandas |
| **numpy** ≥1.24 | pip (figures) | Imported directly by `build_figures.py`, `build_normalization_matrix.py` | Same figure tools fail |
| **networkx** ≥3.0 | pip (figures, **soft**) | BiG-SCAPE GCF-network figure (`mamey/bigscape_figures.py`) | **Soft-guarded**: that figure returns `SKIPPED_NO_DEPS` and silently no-ops; rest of the run is unaffected |
| **scipy** ≥1.10 | pip (figures, **soft**) | Cohort clustermap ordering (`mamey/cohort_figures.py`, `tools/cluster_relate.py`) | **Soft-guarded**: falls back to count-ordering (`_HAS_SCIPY=False`); figures still emit, just unordered by dendrogram |
| **biopython** ≥1.83 | pip (optional) | More robust GBK parsing on non-standard inputs | Built-in shim (`mamey/_gbk_shim.py`) handles standard antiSMASH region GBKs |
| **pandoc** | system binary | `tools/md_to_pdf.sh`, `tools/md_to_docx.sh` (Markdown → PDF/DOCX deliverables) | Those two scripts fail |
| **xelatex** (TeX) | system binary | `tools/md_to_pdf.sh` (PDF rendering) | PDF script fails (DOCX still works with pandoc alone) |
| **Cairo** | system library | CairoSVG-based native SVG-to-PNG pairs | Native SVG remains available; receipts state `NATIVE_SVG_UNAVAILABLE` and no PNG pair is claimed |

**Minimum to run the core extraction + master-workbook pipeline:** `openpyxl` (ijson is already
vendored). Figures and PDF/DOCX export are additive — you only need their dependencies if you generate
those deliverables.

---

## 2. One-line install (machine with network)

```
pip install 'openpyxl>=3.1.2,<4.0' 'ijson>=3.2.0,<4.0' 'matplotlib>=3.7,<4.0' 'numpy>=1.24' 'pandas>=2.0,<3.0'
# optional, if you want Biopython-backed GBK parsing:
pip install 'biopython>=1.83,<2.0'
```

Or, from inside the bundle (uses `pyproject.toml` extras):

```
pip install -e '.[figures]'      # core + matplotlib + numpy + pandas + networkx + scipy
pip install -e '.[all]'          # core + figures + biopython
```

> `numpy` is currently **not installed** on at least one of your machines. The figure
> tools need it, so include it whenever you plan to produce figures.

---

## 3. Manual / offline install (no network on the run machine)

This is the supported path for your lab/run machines. Download the wheels once on a
networked machine, drop them in a folder, and install from local files.

### 3a. Vendored-wheels folder

Put the wheels either **inside the bundle** or in a **folder containing the bundle**.
A conventional location:

```
<bundle-or-parent>/
├── wheels/
│   ├── openpyxl-….whl
│   ├── ijson-….whl
│   ├── matplotlib-….whl
│   ├── numpy-….whl
│   ├── pandas-….whl
│   └── biopython-1.87-cp312-cp312-manylinux….whl   # your chosen build
├── mamey/
├── tools/
└── …
```

Install entirely from that folder (no index, no network):

```
pip install --no-index --find-links ./wheels \
    openpyxl ijson matplotlib numpy pandas biopython
```

For a single pre-downloaded wheel:

```
pip install --no-index --no-deps ./wheels/biopython-1.87-cp312-cp312-manylinux….whl
```

### 3b. Biopython — choose your own compatible build (important)

Biopython ships as a **compiled** wheel, so it must match your interpreter and platform
(CPython version + OS/arch). The end user picks the build that matches their machine and
vendors it; there is no single universal wheel.

- The wheel you supplied is for **CPython 3.12 / manylinux x86_64** (`cp312`,
  `manylinux2014_x86_64` / `manylinux_2_17_x86_64` / `manylinux_2_28_x86_64`).
  Verified: installs and imports cleanly (`Biopython 1.87`, `Bio.SeqIO` OK) on a
  matching 3.12 interpreter.
- For a different interpreter (e.g. 3.11, 3.13) or platform (macOS arm64), fetch the
  matching wheel from PyPI / `pip download biopython` on a networked box of the same
  platform.

**Filename gotcha — keep the canonical dotted name.** A wheel filename must parse as
`name-version-pytag-abitag-platformtag.whl`, where the version uses **dots** (`1.87`,
not `1_87`) and multiple platform tags are joined by **dots**, not underscores. If the
dots get replaced by underscores (some upload/transfer steps do this), pip rejects it
with *"not a supported wheel on this platform."* The fix is purely the filename — rename
it back, e.g.:

```
# rejected (underscores):
biopython-1_87-cp312-cp312-manylinux2014_x86_64_manylinux_2_17_x86_64_manylinux_2_28_x86_64.whl
# accepted (canonical dots):
biopython-1.87-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
```

The wheel **contents** are unaffected — only the name needs restoring.

**This applies to sdists too, not just wheels.** The same underscore-corruption breaks a
`.tar.gz`'s filename parsing identically — pip needs a dotted version there as well, and
the resulting error is more confusing for an sdist than a wheel, since pip's message still
talks about platform compatibility even though the real problem (an unparseable filename)
has nothing to do with your platform:

```
# rejected (underscores):
iniconfig-2_3_0_tar.gz
# accepted (canonical dots):
iniconfig-2.3.0.tar.gz
```

### 3c. PEP 668 (externally-managed environments)

On Debian/Ubuntu system Python (and some others) pip refuses to install into the system
environment (*"externally-managed-environment"*). Two clean options:

```
# preferred: an isolated venv (no override needed)
python3 -m venv .venv && source .venv/bin/activate
pip install --no-index --find-links ./wheels openpyxl ijson matplotlib numpy biopython

# or override (only if you intend to install into the managed environment)
pip install --break-system-packages --no-index --find-links ./wheels …
```

### 3d. Pure-Python sdists that fail to build under the bundled `setuptools`

A small `.tar.gz` (e.g. `iniconfig`, `pluggy`) can fail during `pip install` even after the
filename is fixed (§3b/3c above) — not because of platform or compilation, but because
`pip` invokes a PEP 517 build backend to read the package's metadata before installing it,
and that step can fail independently of anything actually wrong with the package.

**Recognize it:** the error happens during *metadata preparation*, not compilation — these
packages have no compiled extensions, so a build failure here is a build-backend problem,
not a "missing compiler" problem. A common cause: newer sdists declare their license using
the PEP 639 single-string SPDX form (`license = "MIT"` in `pyproject.toml`) rather than the
older table form (`license = {text = "MIT"}`); older bundled `setuptools` releases can't
parse the newer syntax and the build backend invocation fails outright, with no network
access available here to fetch a newer `setuptools` as a workaround.

**Fix — install the package directly, bypassing the broken build backend:**

```
1. Extract the sdist:           tar xzf <pkg>-<version>.tar.gz
2. Confirm it's pure Python — no setup.py with compiled extensions; a src/ layout
   with only .py files is the common case for small utility packages like these.
3. Get the REAL version from the package's own source (a _version.py, __init__.py,
   or the sdist's own PKG-INFO file) — do not guess or default to a placeholder
   version like 0.0.0.
4. Copy the package source directly into site-packages.
5. Write a minimal dist-info directory named exactly <pkg>-<real-version>.dist-info
   (a METADATA file with a matching `Version:` line, plus an INSTALLER file) into
   the SAME site-packages directory the source was copied into — not a scratch or
   temp path. pip and importlib.metadata only recognize a package as "installed"
   when its dist-info sits next to the actual package directory.
6. Verify with BOTH of:
       pip show <pkg>
       python3 -c "import importlib.metadata as m; print(m.version('<pkg>'))"
   Both must report the real version before the install is done. A successful
   `import <pkg>` alone is not enough — that only confirms the code is reachable,
   not that the package's metadata is correct. (A real example of getting this
   wrong: a manual recovery in this exact scenario left one package's dist-info
   with a hardcoded placeholder version, one package's dist-info in the wrong
   directory entirely, and two packages with no dist-info at all — all four
   invisible or wrong in `pip list`, despite every one of them importing and
   running correctly. `pip check` did not catch any of it, because the wheel
   declaring the dependency had no `Requires-Dist` entries to check against.)
```

On a **Miniconda** setup (`~/miniconda3`), conda environments are
not externally managed, so plain `pip install …` works without the override.

---

## 4. System binaries (PDF / DOCX deliverables)

Not pip-installable — install once per machine.

```
# macOS (Homebrew)
brew install pandoc
brew install --cask mactex-no-gui        # provides xelatex; or basictex for a smaller install

# Debian/Ubuntu
sudo apt-get install pandoc texlive-xetex
```

`tools/md_to_docx.sh` needs only **pandoc**. `tools/md_to_pdf.sh` needs **pandoc +
xelatex**, and substitutes DejaVu system fonts (it strips `lmodern`/`textcomp`), so a
minimal TeX install is enough.

### 4a. Native Cairo for CairoSVG

Cairo is a compiled system library and cannot be made portable by placing only the
pure-Python `cairosvg`/`cairocffi` packages in the wheelhouse. Install a native build that
matches the machine, then install the Python render extra in the same environment:

```
# macOS with Homebrew
brew install cairo
pip install -e '.[render]'

# Conda / Miniconda (macOS or Linux)
conda install -c conda-forge cairo cairosvg
```

Verify the native binding with a real conversion, not `import cairosvg` alone:

```
python3 -c "import cairosvg; print(len(cairosvg.svg2png(bytestring=b'<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"2\" height=\"2\"/>')))"
```

If that probe fails, Figure Factory's native SVG renderer continues through its direct,
deterministic SVG path. Its QA receipt names the degradation as
`native_svg_rasterization.state=NATIVE_SVG_UNAVAILABLE` and
`png_pair_path=NOT_EMITTED`; downstream publication gates must not infer a PNG/SVG pair.

---

## 5. Chat-start preamble block (paste-able)

Keep this handy to paste at the start of a working session, or to hand to a collaborator
standing up the bundle:

```
Sapote–Mamey — environment checklist (version intentionally omitted: a restated version rots; see BUILD_STAMP.txt)
• Python ≥3.10  (3.12 recommended; matches the supplied biopython cp312 wheel)
• pip (core):     openpyxl>=3.1.2,<4.0   ijson>=3.2.0,<4.0
• pip (figures):  matplotlib>=3.7,<4.0   numpy>=1.24   pandas>=2.0,<3.0   # all three required for any figure tool
• pip (optional): biopython>=1.83,<2.0   # platform-matched wheel; shim used if absent
• system:         pandoc  +  xelatex     # only for md_to_pdf.sh / md_to_docx.sh
• offline install: pip install --no-index --find-links ./wheels <pkgs>
• biopython filename must use dotted version/platform tags (1.87, not 1_87)
• validate a master:  python3 mamey/workbook_schema_check.py <workbook.xlsx>
  (now works as a bare script AND as: python3 -m mamey.workbook_schema_check <wb>)
```

---

## 6. Verify your install

```
python3 -c "import openpyxl, ijson; print('core OK')"
python3 -c "import matplotlib, numpy, pandas; print('figures OK')"
python3 -c "import Bio; from Bio import SeqIO; print('biopython OK', Bio.__version__)"   # optional
python3 mamey/workbook_schema_check.py examples/test_data/test_master.xlsx              # expect status: PASS
pandoc --version | head -1 ; xelatex --version | head -1                                 # optional
```
