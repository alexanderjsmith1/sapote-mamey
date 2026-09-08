# AGENTS.md — the one door for coding agents (Claude Code, Codex, Cursor, ChatGPT with a shell)

**First, run `python mamey_run.py start` and do exactly what it prints.** It reports this bundle's
real version, the ordered happy path, and which docs are authoritative — trust its output over
anything remembered from a prior session. `CLAUDE.md` is a byte-identical copy of this file: same
door, two names, and you have already read it.

You are in a **Sapote-Mamey** bundle. Mamey is a deterministic extractor for antiSMASH output;
Sapote is the claim-safe judgment protocol that reads what Mamey extracts. Motto: **deterministic
extraction, judgment deferred.** Every output is a class-level hypothesis. Never write a structure,
compound-identity, or bioactivity claim that the evidence file does not carry.

## The happy path (what `start` prints)

```bash
python mamey_run.py doctor                                  # environment and dependency check
python mamey_run.py inspect <antiSMASH.zip>                 # preview; echoes a ready-to-run command
python mamey_run.py run --strain <ID> --input-zip <antiSMASH.zip> \
    --taxonomy '<Genus sp.>' --source '<isolation source>' --mode gold --capped-session
python mamey_run.py validate runs/<ID>/package              # gates; never skip
python mamey_run.py explain  runs/<ID>/package              # human-readable result summary
```

Always invoke the pipeline as `python mamey_run.py <cmd>` — it pins the local package. `python -m
mamey <cmd>` can silently run a pip-cached install of a different version. After validation, the
judgment steps read the sealed package: `list-bgcs`, `mode-b`, `render-figures`, `ingest-receipts`.
`python mamey_run.py --help` lists every subcommand; none beyond `validate` is required to obtain a
validated package.

## Then read, only as needed

- `CURRENT_DOCS_INDEX.md` — the only authority on which docs are current; a doc not listed there is
  history, not guidance.
- `CLAUDE_START_HERE.md` (Claude) or `CHATGPT_START_HERE.md` (ChatGPT) — assistant-specific operating
  rules only; both point back here. The other root `*_READ_ME_FIRST*` files are redirect stubs that
  route to `start` + this file and add nothing new.

## Hard rules that tests enforce

- **Exact-locus identity on every BGC you display:** `strain / full node-or-contig / region / BGC
  alias`, copied from one bound record. If a component is missing, stop with an identity hold.
- **Validate before interpreting.** A package that has not passed `validate` is not evidence.
- **Do not edit generated surfaces by hand** (`MODULE_MANIFEST.txt`, `docs/COMMAND_CATALOG.generated.md`,
  `SOURCE_CHECKSUMS_SHA256.txt`, `TIER_MANIFEST.txt`, and the bootstrap mirrors rendered from
  `bootstrap_contract.yml`). The generators under `tools/` own them.
- **Versions live in one place.** `BUILD_STAMP.txt` and `mamey/__init__.py` are synced by
  `tools/sync_version.py`; never hand-edit a version literal.
- **Trees need approval.** Phylogenetic runs (`phylo-run`, `phylo-autopilot`) refuse to spend CPU
  without an explicit approval flag. That is the tree-approval gate, not a bug.

## Where things are

| Need | Go to |
|---|---|
| The engine | `mamey/` (package), `mamey_run.py` (entry point that pins the local package) |
| Tests | `tests/` — `pytest tests/ -q`; skips are gated reference-panel tests, not breakage |
| Operator scripts | `tools/` — each is a front door for one job; `docs/COMMAND_CATALOG.generated.md` indexes them |
| Standing rules / registries | `mamey/data/rules_registry.json`, `registry_inventory_*.json` |
| Figures | `FIGURES_START_HERE.md` |
| Phylogenetics | `docs/PHYLO_AUTOPILOT_WORKFLOW.md` (16S + genome uploads to gated trees) |
| Release status | `RELEASE_MANIFEST.md` |

If two documents disagree, the one listed in `CURRENT_DOCS_INDEX.md` wins; if both are listed, the
newer `CHANGELOG.md` entry wins. Say so in your reply rather than picking silently.
