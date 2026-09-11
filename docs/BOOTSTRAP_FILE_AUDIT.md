# Bootstrap file audit — generated from bootstrap_contract.yml

Bundle / engine / build: v9.7.428 / 1.9.163 · 20260911v97428a

## Bootstrap surface contract

Two audiences: `README.md` for people; `AGENTS.md` is the canonical portable contract intended for every coding assistant.
Automatic instruction-file discovery varies by product. `CLAUDE.md` is a byte-identical Claude discovery copy; other assistants must be directed to `AGENTS.md` or receive it through their supported instruction mechanism.

| Path | Role | Required | Scanner authority | Purpose |
|---|---|---|---|---|
| `AGENTS.md` | canonical_agent_contract | yes | yes | Canonical portable contract intended for every coding assistant; automatic discovery varies by product. |
| `CLAUDE.md` | agent_discovery_alias | yes | no | Byte-identical Claude discovery copy of AGENTS.md; other assistants are not assumed to discover this filename. |
| `README.md` | human_landing_page | yes | no | Human overview and installation links; routes coding assistants to AGENTS.md. |
| `docs/BOOTSTRAP_FILE_AUDIT.md` | generated_bootstrap_map | yes | no | Generated map of the human page, canonical assistant contract, and Claude discovery copy. |
