# Games — Sapote–Mamey Audit Protocols

Two adversarial audit games for code and documentation quality.

| Game | What it does | Unit | Method |
|------|-------------|------|--------|
| **Bunny Hop** | Per-file quality assessment | One file at a time | Inspector vs Defender adversarial |
| **Bug Hunt** | Codebase-wide bug sweep | Whole tree | Pattern grep + targeted reads |

Both games produce **patch cards** — prioritized lists of fixes with effort estimates.
Results from either game feed into the Patch Chat for the next version cut.

## When to use which

- **Bunny Hop** — new files, governance docs, design review, or "is this file sound?"
- **Bug Hunt** — pre-release sweep, after a version jump, or "find all the bugs"
- **Both in one session** — Bug Hunt first (clear systematic issues), then Bunny Hop
  on the files Bug Hunt flagged as highest-risk.

## Files

- `BUNNY_HOP_AUDIT_GAME.md` — Full Bunny Hop rules and format
- `BUG_HUNT_PROTOCOL.md` — Full Bug Hunt protocol with pattern library
- `BUNNY_HOP_REQUEST_TEMPLATE.md` — Template for requesting hops from other sessions

## How to start

Upload the bundle + this folder's game doc into any Claude or ChatGPT session.
The game doc is self-contained — no prior context needed.

---

**
