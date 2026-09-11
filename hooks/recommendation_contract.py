#!/usr/bin/env python3
import sys

CONTRACT = (
    "RECOMMENDATION CONTRACT (state your position, not just the options). Whenever a reply raises an "
    "open question, a choice between approaches, a trade-off, a governance/ownership question, or "
    "anything you would hand back to the user to decide: you MUST give a RECOMMENDED POSITION and the "
    "REASONING for it. Format: what you recommend, in one line; then why, grounded in what you "
    "actually verified (name the file/number/receipt); then what would change your mind, or the "
    "residual risk. Rank multiple decisions by consequence, not by the order you found them. "
    "Never present a bare menu of options and stop. Never hedge to avoid committing. If you genuinely "
    "cannot recommend, say so explicitly and state exactly what evidence would let you. "
    "A recommendation is NOT permission to act: keep the standing gates — the user authorizes release actions and "
    "rules on scientific evidence; irreversible or outward-facing actions still need approval; "
    "verify before asserting; claim-safety holds (class-level hypotheses, judgment deferred). "
    "Stay correctable: if a owner or user contradicts a recommendation, adopt the correction "
    "plainly and say what changed."
)


def main() -> int:
    try:
        sys.stdin.read()  # drain the hook payload; content is not needed
    except Exception:
        pass
    try:
        import json
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": CONTRACT,
            }
        }))
    except Exception:
        return 0  # fail open — never wedge a prompt
    return 0


if __name__ == "__main__":
    sys.exit(main())
