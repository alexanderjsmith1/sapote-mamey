# Optional assistant hooks

These scripts are available for explicit installation. Shipping them does not activate them,
and this cut does not change any user's assistant settings. The current user's instructions
and authorization take precedence over advisory text emitted by a hook.

Set SAPOTE_WORKSPACE_ROOT to the project whose work is being checked. Set SAPOTE_BUNDLE_ROOT
to the extracted bundle used to invoke the hooks; keep that path pinned to the reviewed cut.
Python hooks require Python 3.12 or newer. Shell hooks require Bash and Python; the BLASTp
concurrency hook uses Python standard-library JSON parsing and requires permission to inspect the process list.

| Script under hooks | Event | Behavior |
|---|---|---|
| require_phylo_workflow.sh | PreToolUse with Bash matcher | Requires an explicit tree path and local tools/tree_sanity_check.py for recognized render commands; checks exit status. This is a command-pattern guard, not a universal render interceptor. |
| block_blastp_overconcurrency.sh | PreToolUse with Bash matcher | Checks recognized runner launches and stagger syntax; default cap 10, configurable 1 to 12. This does not enforce service-wide submission timing across machines. |
| c10_tool_drift.py | SessionStart with --mode baseline; Stop with --mode check | Reports changed existing tools under tools/ in the selected project. It detects changes after they occur. |
| reasoning_self_audit_stop.py | Stop | Requests evidence for certain unsupported factual phrases; heuristic, debounced. |
| contradiction_and_magnitude_stop.py | Stop | Requests review of certain numeric discrepancies; does not prove an arithmetic or scientific error. |
| state_save_reminder.py | Stop | Reports stale STATE.md files under task_state/ or SAPOTE_TASK_STATE_ROOT; advisory. |
| no_stop_short.py | Stop | Checks .claude/state/TASK_CONTRACT.md; missing/stale contracts allow stopping, and repeated blocks have a backstop. |
| recommendation_contract.py | UserPromptSubmit | Adds a short recommendation-writing reminder; does not authorize an action. |

The example below shows the host event structure for one shell hook and one Python hook.
Merge only the entries you select into the host's project hook configuration; preserve existing
entries. Confirm that the host supports these events and payloads before enabling them.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "bash \"$SAPOTE_BUNDLE_ROOT/hooks/require_phylo_workflow.sh\""}
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {"type": "command", "command": "python3 \"$SAPOTE_BUNDLE_ROOT/hooks/recommendation_contract.py\""}
        ]
      }
    ]
  }
}
```

For c10_tool_drift.py, use the same project root and session identifier for both events.
For the workflow hook, point SAPOTE_WORKSPACE_ROOT at the bundle root containing the intended
checker. It does not search neighboring releases or install a workspace-specific gate wrapper.
Test selected hooks with generic inputs before using them on active work. A hook warning is
not a release, completeness, provenance, or scientific-acceptance receipt.
