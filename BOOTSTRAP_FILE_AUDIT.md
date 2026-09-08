# Bootstrap file audit — generated from bootstrap_contract.yml

Bundle / engine / build: v9.7.414 / 1.9.152 · 20260907v97414a

## Classification map

| Path | Classification | Required | Scanner authority | Severity | Generated |
|---|---|---:|---:|---|---|
| `CHATGPT_START_HERE.md` | canonical / canonical_chatgpt_contract | yes | yes | hard_fail | partial |
| `CLAUDE_START_HERE.md` | canonical_other_assistant / canonical_claude_contract | yes | yes | hard_fail | version_probe_only |
| `000_READ_ME_FIRST_CHATGPT_CLAUDE.md` | canonical_router / cross_assistant_router | yes | yes | hard_fail | partial |
| `CHATGPT_READ_ME_FIRST.md` | generated_mirror / correctly_spelled_chatgpt_alias | yes | no | warning_if_missing | full |
| `CHATGTP_READ_ME_FIRST.md` | optional_typo_rescue_alias / accidental_chatgtp_transposition_rescue | no | no | none_if_missing_warn_if_divergent | full |
| `README.md` | generated_mirror / package_reader_banner | yes | no | warning_if_stale | partial |
| `README_START_HERE.md` | generated_mirror / reviewer_operator_banner | yes | no | warning_if_stale | partial |
| `BOOTSTRAP_FILE_AUDIT.md` | generated_report / generated_bootstrap_map | yes | no | warning_if_missing | full |

## Policy conclusions

- `CHATGPT_START_HERE.md` is the authoritative ChatGPT operating contract.
- `CHATGTP_READ_ME_FIRST.md` is an optional accidental-typo rescue alias. It may be shipped to catch ChatGPT→ChatGTP transposition, including ATP/GTP-context slips, but missing it should not block canonical ChatGPT discovery.
- New scanner/test logic should target canonical surfaces and treat aliases as compatibility checks only.
- Known gotcha text should be edited in `bootstrap_contract.yml`, not independently in the initiation prompt and §3.
