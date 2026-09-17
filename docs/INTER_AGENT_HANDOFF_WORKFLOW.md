# Hand work between assistants without losing the evidence

Use this when one assistant asks another to review, run, patch, or continue a Sapote-Mamey task. It works with any pair of assistants and any local project layout. The handoff is a pointer to evidence, not a new authority over a sealed bundle, data registry, or user decision.

## Prepare one bounded handoff

1. Use [the handoff template](../prompts/INTER_AGENT_HANDOFF_TEMPLATE.md) and give it **one request**. Separate unrelated requests into separate handoffs.
2. Identify the exact input bundle or package, its role (sealed source, unsealed candidate, external data, or proposal), and its SHA-256 or immutable receipt. Say which files were actually inspected. For a BGC, display `strain / full node-or-contig / region / BGC alias`; do not join evidence by alias alone.
3. State what is already done, what is only proposed, the output root, and any resource or disclosure limits that matter to the requested action. A quoted command is a reproducibility aid, not permission to run it.
4. Link the patch, tests, logs, and resulting artifacts separately. Distinguish a successful patch application, test pass, external-tool run, scientific interpretation, and release acceptance.
5. Put the complete handoff in one Markdown file on the sending side. Put only a short pointer in the receiving side's index. Read the other side's files in place when possible; preserve their original hashes.

## Receiving and returning

The receiver checks the named files and hashes before acting. If a path has moved or an input cannot be bound, return a hold identifying the missing item. Do not infer completion from a filename such as `FINISHED` or from a chat summary. Return a short decision (`ACCEPT_FOR_REVIEW`, `CHANGES_REQUESTED`, or `HOLD`), the evidence checked, changed files/receipts, unresolved issues, and the next owner. Keep observations distinct from interpretations.

When a run is involved, first read its current pointer, immutable run manifest, state, QA receipt, and log tail as described in [the companion-tool protocol](LLM_COMPANION_TOOL_PROTOCOL.md). Reuse its run ID and exact source hashes. Do not create a second run merely because the assistant changed.

## Example scope

A BLASTp handoff might ask: “In an isolated output folder, export one per-strain database from this source snapshot and this Mamey package; compare the channel counts and report unbound genes.” The answer includes source/package/output hashes, nr/ClusteredNR/Swiss-Prot counts, and typed holds. Similarity remains evidence, not compound identity.

A BiG-SCAPE handoff might ask for a three-query pilot with an explicit MIBiG slot and the positive loaded-count line. A query-only pilot does not validate MIBiG anchoring. The answer includes version, input/ref counts, exact run ID, database integrity, cutoff, and family output receipt.

## Relationship to older documents

[The Claude–ChatGPT workbook protocol](CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md) documents a particular historical workbook loop and platform role split. This page and its template are the general current handoff shape. [SOP-15](SOPs/SOP-15_Cross_Chat_Merge_and_Patch_Handoff.md) adds requirements for a patch packet; [the companion-tool protocol](LLM_COMPANION_TOOL_PROTOCOL.md) adds run-state requirements for external tools. None of these substitutes for the source artifact or the user's current instructions.
