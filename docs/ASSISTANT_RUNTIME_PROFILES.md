# Separate assistant guidance from runtime limits

Early Sapote–Mamey workflows were developed in hosted chat interfaces before migration to local
coding agents. Repeated handoffs, capped runs and explicit completion menus come from that
context and should be evaluated in it. A constraint that helped
one environment is not automatically suitable as a universal rule for every later environment.

This is operational guidance, not a new configuration feature. No profile-switching command or
automatic hardware tuner is introduced by this document.

## Three independent decisions

| Decision | Evidence to use | Do not infer from |
|---|---|---|
| What the assistant should do | Current user request, selected output/profile and evidence standards | The presence of data or a historical system prompt |
| What execution is permitted | Workspace roots, network/disclosure scope, resource authorization | Model name, an old approval phrase or a handoff command |
| What execution is feasible | Python/dependencies, input size, RAM, process budget, measured timings | Subscription tier, model capability or the word “full” |

A model can differ in how well it follows instructions, handles long context or writes code.
The Python process still uses the code's parser limits and its actual host environment. A different
model does not change a hardcoded JSON byte cap. More CPU cores do not by themselves remove an
in-memory parser's RAM demand or make a sequential operation parallel.

## Choose settings from observed conditions

| Observed environment condition | Suitable adaptation | Keep explicit |
|---|---|---|
| Short process/session lifetime | Bounded work units, checkpoints, resumable logs | What evidence/output the shortened run omits |
| Ephemeral filesystem | Export recoverable artifacts before the environment expires | Where the handoff is saved and how inputs are rebound |
| Persistent local workspace | Reuse verified environment and prior receipts | User scope, path permissions and stale-source checks |
| Constrained RAM | Streaming/bounded parsing or a smaller selected task | Record/byte caps, truncation and unknown channel completeness |
| User-approved larger local budget | A separately reviewed cap/resource adjustment | Measured cost, test cases and unchanged versus altered scientific behavior |
| Useful next-step coaching requested | Offer grounded options suited to the user | User preference rather than a universal menu quota |

Do not assume a browser-hosted session is always ephemeral, or that a local session has unlimited
resources. Inspect the actual environment. Defaults should describe their applicability, side
effects and escape conditions; explicit user choices remain authoritative within host constraints.

## What to record with a benchmark or walkthrough

Record software commit and uncommitted patch identity, interpreter and dependencies, input hash
and uncompressed JSON size, parser mode, cap values, elapsed time, measured peak memory when
available, exit status, evidence-visibility receipt and unresolved warnings. CPU/thread settings
matter only for components that use them; do not claim a core-count speedup without a measurement.

Do not compare a held parse with an admitted parse as though they did the same amount of work.
One successful strain is a useful acceptance example, not a universal performance guarantee.
When raising a cap, preserve the earlier held/truncated attempt and test the size boundary too.

## Migration priorities

Keep truthful evidence receipts, immutable inputs, scoped identities, resumability and resource
preflights. Retire unconditional model identities, repeated installs, rigid response rituals and
instructions that suppress legitimate audit findings. Where an old behavior is still helpful,
make it an explicit task or environment choice rather than deleting the capability.
