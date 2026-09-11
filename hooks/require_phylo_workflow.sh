#!/usr/bin/env bash
# Optional PreToolUse Bash hook. No installation or environment mutation.
exec python3 -c '
import json, os, pathlib, re, shlex, subprocess, sys
try:
    payload = json.load(sys.stdin)
except (ValueError, TypeError):
    sys.exit(0)
command = payload.get("tool_input", {}).get("command", "")
if not isinstance(command, str):
    sys.exit(0)
is_tool = re.search(r"iqtree|muscle|GToTree|FastTree|epa-ng|raxml|phylo_place\.py|mafft", command)
is_render = re.search(r"ggtree|render_clean_tree|render_all\.py|render_pruned|Phylo\.draw", command)
if not (is_tool or is_render):
    sys.exit(0)
root = pathlib.Path(os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
if is_render:
    checker = root / "tools/tree_sanity_check.py"
    try:
        tokens = shlex.split(command)
    except ValueError:
        print("BLOCKED: cannot parse tree-render command; provide explicit quoted tree paths", file=sys.stderr)
        sys.exit(2)
    trees = [pathlib.Path(t) for t in tokens if t.endswith((".treefile", ".nwk", ".newick"))]
    if not checker.is_file() or not trees:
        print("BLOCKED: local tree checker and explicit input tree paths are required", file=sys.stderr)
        sys.exit(2)
    for tree in trees:
        if not tree.is_absolute():
            tree = pathlib.Path(payload.get("cwd") or os.getcwd()) / tree
        if not tree.is_file():
            print("BLOCKED: declared input tree is missing", file=sys.stderr)
            sys.exit(2)
        result = subprocess.run([sys.executable, str(checker), str(tree)], capture_output=True, text=True)
        if result.returncode:
            print("BLOCKED: tree sanity checker failed or could not complete", file=sys.stderr)
            print(result.stdout + result.stderr, file=sys.stderr)
            sys.exit(2)
print("Read docs/PHYLO_AUTOPILOT_WORKFLOW.md and docs/PHYLO_PLACEMENT_WORKFLOW.md before phylogenetic work.", file=sys.stderr)
'
