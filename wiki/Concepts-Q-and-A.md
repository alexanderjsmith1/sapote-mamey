# Sapote–Mamey · Concepts Q&A

*A running concepts companion to the GUIDE. the Developer or User asks, Claude answers in the voice we actually use — direct, honest about what's observed vs. inferred, and not stiff about it. Useful first, entertaining second; we'll take both. This is the conversational "why does it work this way" layer — clipped definitions live in the canonical [`GLOSSARY.md`](../docs/GLOSSARY.md) (see its **Core concepts** section for the load-bearing terms), and the deep internals live in the Encyclopedia (`03_Technical_Manual_Encyclopedia.html`).*

*Current to bundle v9.7.414 / engine Mamey 1.9.152.*

> **On the numbering.** Two series run here. **Q1–Q10** are the original conversational thread (workflow and first-encounter jargon). **Bank N** entries are numbered by position in the 100-question bank (`Sapote-Mamey_QandA_QuestionBank_100.md`) so each maps straight back to its source question — which is why the Bank numbers are not contiguous (gaps are questions not yet written up, not missing content). Cross-references of the form "(Bank N)" point within this document.

## Contents

**Working with the pipeline & environment**
Q1 wedged pytest · Q2 stop button vs timeout · Q3 usage tokens · Q4 chunk · Q5 parsing · Q9 idempotent · Q10 ijson · Bank 70 bounded streaming · Bank 71 Decimal-vs-float · Bank 72 regression / negative-control tests · Bank 73 xfail tripwire · Bank 76 GBK files & the shim

**Project jargon, scans & the two-layer design**
Q6 CGAD · Q7 project jargon · Q8 bacterial chitinases · Bank 1 Mamey/Sapote split · Bank 6 Mode B §1–§8 · Bank 7 observed/computed/inferred/assumed · Bank 8 extract-level bioactivity · Bank 9 never "antifungal-negative" · Bank 10 hallucination traps

**Genome-mining concepts**
Bank 16 70/45/20 tiers · Bank 20 KCB-dark · Bank 22 RG-GMCI · Bank 23 CCTT / T43 · Bank 24 T43 families · Bank 25 FLBR · Bank 26 UMED · Bank 27 EFLS vs RG-GMCI · Bank 28 resistance scan · Bank 29 APH-sugar-kinase veto · Bank 30 bldA/TTA · Bank 31 bldA spurious T4 · Bank 32 TFBS · Bank 33 RES_CLASS_CONCORDANCE · Bank 34 genome-grounded/scope-gated · Bank 35 the ten scans

**Scoring & prioritisation**
Bank 36 AB76 build · Bank 37 lead classes A/B/C · Bank 38 diagnostic floor · Bank 39 DAPR · Bank 40 scoring boundary · Bank 41 cohort re-score · Bank 42 evidence axes · Bank 43 WL tier · Bank 44 promiscuity cap · Bank 45 compound-class annotation

**Claim-safety & standing exclusions**
Bank 46 NAPAA · Bank 47 hglE-KS-PREV-001 · Bank 48 saccharide downgrade · Bank 49 enediyne [E-signal] · Bank 50 KCB = similarity

**Biology primer**
Bank 66 HMMER vs BLAST · Bank 67 profile HMM / marker · Bank 68 Pfam/TIGRFAM/dbCAN · Bank 69 BLAST / KnownClusterBlast · Bank 78 PKS vs NRPS · Bank 79 PKS domains · Bank 80 NRPS domains · Bank 81 Stachelhaus code · Bank 82 RiPP / maturation · Bank 83 lanthipeptide vs lasso · Bank 84 halogenase · Bank 85 HSAF/PTM · Bank 86 nikkomycin · Bank 88 GH18/GH19/GH20 chitinases · Bank 89 resistance-directed mining · Bank 90 self-resistance genes

---

# Part 1 · Conversational thread (Q1–Q10)

---

## Q1 · What is a wedged pytest?

A wedged pytest is what happens when you try to *kill* a heavy pytest run mid-flight and the environment punishes you for it by going catatonic for about three minutes.

Here's the shape of it. The full suite is ~1,400 tests and runs ~200–290 seconds. A tier cut runs that same suite as its in-tier gate. That's a long time to stare at a terminal, so the temptation — the very natural, very human temptation — is to background it, or to Ctrl-C it when you change your mind, or to fire off three strain runs at once and let the slow one get killed by a timeout. **Don't.** That's the move that wedges the box.

What's actually going on (this part is *inferred* — I can't see the sandbox's process supervisor, only its behavior): pytest doesn't run alone. It spawns children — subprocess calls inside the tests themselves (`sync_version --check` shells out, the render-timeout tests spawn subprocesses, matplotlib fires up its Agg backend, any sharding spins up workers). When you kill the *parent*, the children don't reliably die with it. They're orphaned, still holding CPU and file handles and the working directory, and in a containerized process namespace they don't get reaped instantly. So you're left in a dead zone: new commands hang, the filesystem feels sticky, and nothing you do speeds it up. It clears itself in ~3 minutes when the orphans finally time out and the namespace cleans up. (The *observed* fact is the 3-minute dead zone. The orphaned-children story is my best explanation for it, not something I've watched happen line by line.)

The cruel irony: the instinct when something's stuck is to kill *more* things. That makes it strictly worse — you're just orphaning more children into the same wedge.

So the operating rules, which are really just "stop fighting the box":

1. **Run heavy things in the foreground, one at a time.** No backgrounding a pytest run and poking at it. No three-strain runs crammed into one call — the *Gemmata massiliana* 56-BGC run already proved that one (timed out, wedged, lesson learned).
2. **Poll, don't kill.** If you need to know whether it's done, wait and check, don't interrupt.
3. **If it does wedge, the fix is patience, not violence.** Walk away for three minutes. The box heals itself. Anything you type into a wedged environment is at best wasted and at worst a fresh orphan.

Think of it less like a crash and more like the environment holding a grudge. Give it a minute. It gets over it.

One practical tell: if the container goes unresponsive *right after* a test run, that's the wedge, not a new bug — and the only correct response is to do nothing for three minutes. The reflex to "check if it's still alive" by firing another command is exactly what extends it.

---

## Q2 · Do you mean when I press the stop button, or some internal timeout?

Fair catch — I was loose about that, and they're genuinely different events. Let me split them instead of bluffing one answer, because one of the three I can't actually speak to.

1. **Internal / harness timeout.** *This is the one I've actually watched wedge the box.* A bash command that runs past its limit gets killed by the harness — not by you, not by me. The three-strain *Gemmata massiliana* run is the documented case: ran long, hit the timeout, got killed mid-flight, environment went sticky. This is the canonical trigger, and it's *observed*.

2. **An explicit kill I issue** — `pkill pytest`, `kill %1`, dropping a backgrounded run because I changed my mind. The standing rule ("killing background pytest processes wedges the environment ~3 min") is literally about this case. Also real, also *observed*.

3. **You pressing stop.** Here I have to be straight: **I don't actually know what that does to an in-flight bash subprocess.** The stop button halts *my* turn — my token generation. Whether that signal travels down and kills a command that's already executing as a tool call, I can't confirm from where I sit. *If* it does, I'd expect the same wedge (same orphaned-children mechanism). But that's inference on top of inference, and honestly **you're better positioned to tell me** — you can watch whether the next thing you do after hitting stop hangs for a few minutes. I can't see your side of the button.

So when I said "kill a heavy run mid-flight," the model in my head was #1 and #2 — a process getting a hard kill while it's still holding children. I lumped #3 in by association, and your question is right to pull it back out.

The useful part: the *upshot* doesn't change across the three. A long pytest run that dies by any hard kill — timeout, my hand, or maybe yours — risks the wedge. Which is why the real defense lives upstream of all of it: foreground, sequential, one heavy thing at a time, poll instead of interrupt. If a run is short enough that you never even *want* to stop it, none of the three ever fires. The button question becomes moot when nothing's tempting you to reach for it.

The actionable version for our workflow: if you genuinely need to bound a heavy run, bound it *inside* pytest (its own `--timeout`, `-x`/`--maxfail`) rather than killing from outside. An internal stop unwinds cleanly; an external hard kill is what orphans the children.

---

## Q3 · What are "usage tokens"?

A token is the unit a language model actually reads and writes in — not words, not characters, something in between. Sub-word chunks. In English it averages ~4 characters or about ¾ of a word, but it's lumpy: "the" is one token, "antiSMASH" is three or four, a UUID or a base64 blob is a whole pile of them. I never see your text as letters or words; I see this stream of tokens, and everything I do is counted in them.

"Usage tokens," then, are just tokens in their accounting role — the ones metered to measure how much of the model a conversation has consumed (for limits, for billing, for deciding when a session has to be compacted). And here's the part that matters for *you* specifically, given the sessions you run:

It isn't your latest message that gets counted. It's **everything in my context, every single turn.** The system prompt, the entire conversation back to the top, every file you've attached, and — this is the one that bites in Patch Chat — every tool result. When the full suite runs and 200 lines of pytest output come back, that's tokens. When I `view` the TIER_MANIFEST and 600 file paths scroll past, tokens. The 5 MB zip's file listing, the leak-audit dump, the diff hunks — all of it becomes *input*, and input gets re-counted on the next turn, and the next, because I re-read the whole context each time to answer you.

That's why this very conversation got compacted at the top — the running total got large enough that the history had to be summarized into a transcript file to make room. It's the same reason I `grep -vE` the noise out of cut logs instead of dumping the raw 290-second pytest stream, and the same reason a `.docx` costs far more than the equivalent markdown. None of that is fussiness — it's token economy.

The honest boundary: I can explain the *unit* and the *mechanism* cold. What I won't pull from memory are the live numbers — how many tokens your plan allows, what the context window caps at this month, what any of it costs — because those move, and a confident-but-stale figure is worse than "go check." If you want the current limits, `docs.claude.com` / `support.claude.com` is the place, and I'm happy to go pull them.

Rough intuition to carry around: **1 token ≈ 4 characters ≈ ¾ of a word.** A dense page of prose is ~500–800 tokens. That 290-second pytest log I quietly trimmed before it hit your screen? You don't want to know.

---

## Q4 · What is a chunk?

Two answers, because I used the word loosely in Q3 and you're right to make me pay for it.

**The loose sense (what I meant a minute ago).** Just "a piece of." When I called a token a "sub-word chunk," I was using *chunk* as plain English — a bite-sized piece of text. Nothing technical there; the real unit is the token, and "chunk" was me hand-waving at "it's a piece, smaller than a word." Fine for conversation, not a term.

**The sense that's an actual term of art — and the one worth knowing.** A *chunk* is a segment a document gets split into for retrieval. This is the one that matters in our world.

When I search the web, or search our past chats, the source doesn't arrive whole. Somewhere upstream it's been sliced into chunks — segments from a few sentences to a paragraph — each indexed so a search can find the relevant pieces and hand *those* back, instead of the entire document. So what I actually receive isn't "the article," it's a handful of chunks: the bits that matched, often mid-thought, sometimes missing the sentence that would've made them make sense.

That explains a few things you've probably noticed:
- Those `index="0-2"` numbers in citations are *document-chunk, then sentence-within-it.* The citation points at the specific chunk a claim came from.
- When a past-chat search comes back as fragments in little tags instead of a clean transcript — those are chunks, not the whole conversation.
- When I run a search and then immediately `web_fetch` the full page anyway, it's usually because the chunk gave me the headline but cut off right before the number I needed. The chunk was the teaser; the fetch was the actual read.

*Honest boundary:* I know retrieval works by chunking — I watch the chunks land. The exact slice size and where the boundaries fall, I don't see; that's upstream of me, so treat any claim about "chunks are N sentences" as my inference from what arrives, not a spec I've read.

Two more uses, if you ever trip over them: **streaming chunks** (an API response arrives in pieces over the wire, not all at once) and **parse chunks** (the vendored `ijson` streams a giant antiSMASH JSON through in chunks so Mamey never loads the whole file into memory at once — you've shipped that one). Same word, different layers. But the retrieval chunk is the one that'll actually come up.

Chunking is also where the bounded-streaming idea (Bank 70) lives in practice — the chunk boundary is the point at which the parser decides what to keep and what to skip, so on a giant antiSMASH JSON it's not a cosmetic detail but the thing that keeps memory flat.

---

## Q5 · What is parsing?

This one's close to home, because parsing is the verb the entire Mamey layer is built on. "A deterministic Python extraction engine *parsing* antiSMASH output" — that's the whole job description.

**The plain definition.** Parsing is turning a stream of raw characters that *has* structure into a structure a program can actually walk. Reading a file gets you a blob — a flat run of bytes. Parsing gets you *meaning*: "this is a record, the record has a field called `product_classes`, that field is a list, the list holds these strings." The text was already structured — it followed some format, some grammar — and parsing is the act of recognizing that grammar and building the in-memory version of it. Reading is "I have the characters." Parsing is "I understand what they're saying."

**In our world.** antiSMASH hands you a wall of nested JSON (and GBK) — records inside regions inside protoclusters inside CDS features inside qualifiers, KCB hits hanging off the side. None of that is usable as text. `mamey/parsers.py` is the layer that walks the wall and hands the rest of the engine clean objects: *here is each BGC, here are its boundaries, here are its CCTT tokens, here are its KCB anchors.* The `ijson` streaming from Q4 is parsing built so a 100 MB file doesn't choke it; `_gbk_shim` is parsing GenBank when the JSON doesn't carry what you need. Every deterministic number Mamey produces starts as a parse.

**Here's the part worth underlining, because it's the spine of the whole Sapote–Mamey split:** parsing is *deterministic.* Same antiSMASH file in, same structured objects out, every time — no judgment, no model. That's Mamey, by construction. The instant you stop recognizing structure and start asking what the structure *means* — "is this BGC actually an antifungal lead?" — you've left parsing and crossed into interpretation, which is Sapote. Parsing is the exact line between the part that's reproducible because it can't be anything else, and the part that needs a verdict. For the methods paper, that line *is* the architecture.

**And because parsing is where the project quietly bleeds, three real ways it bites:**
- **Schema drift.** Parsing trusts the format. When antiSMASH changes its JSON shape between versions, a parser written for the old shape reads the new one *wrong* — silently, no crash, just bad structure downstream. That's exactly what `test_schema_drift.py` stands guard against.
- **The wrong field.** The manual-BLASTP worklist fix you shipped in v9.7.91 was a parsing bug at heart: it scored `locus_tag + product`, but antiSMASH leaves `product` empty and stashes the function in `sec_met_domain` / `gene_functions`. Parse the wrong field and the output isn't wrong, it's *empty* — which is how that worklist shipped blank on real strains until it got caught.
- **The graceful-failure case.** A good parser plans for input that breaks its assumptions. Your own redactor is the clean example: `redact_py` parses Python into tokens so it only scrubs comments and strings, never code identifiers — but when a file *won't* tokenize, it doesn't die, it falls back to plain-text scrubbing. That fallback is the mark of a parser written by someone who'd been burned before.

So: reading is having the bytes; parsing is understanding them. And in this project, parsing is also the property line between "deterministic and defensible" and "needs a human or a model to make the call."

---

## Q6 · What is CGAD?

Honest up front: I'd seen "CGAD NULL" sitting in the run boards but couldn't have told you what the letters stood for, so I went and read it out of the bundle rather than guess. Per `README.md` and the system prompt (§44), CGAD = **Chitinase Genome Architecture Detection.**

It's one of your deterministic genome-wide first-pass scans — the canonical set is KCB sweep · RG-GMCI · FLBR · CCTT · **CGAD** · UMED · EFLS · Resistance · bldA-TTA · TFBS — and its job is to find chitin-degradation machinery in a genome: chitinases (GH18), LPMOs, the GlcNAc-utilization apparatus. The markers you've been running it on are chitin / GH18 / LPMO.

**Why it earns a slot, ecologically.** Chitin is the structural polymer in *both* fungal cell walls and insect cuticle. For a cohort of bee- and wasp-associated actinomycetes hunting antifungals, a strain carrying real chitinase architecture has genome-grounded capacity to chew on fungal cell walls — an antifungal-relevant signal that isn't a BGC at all, it's genome architecture. That's the "two-pronged anti-chitin ecology read" in `F1_Ecology_Readiness`, and it's why CGAD feeds the nucleoside→antifungal axis gate (`test_chitin_gate_h4`).

**The part that's pure Sapote doctrine, and the reason it's worded so carefully.** CGAD is *genome-grounded and proteome-scope gated — but NOT isolation-source gated.* Read that as a claim-safety rule. You don't get to credit a strain with chitin-degradation capacity because it came off a bee; that's reasoning from the isolation source, which is exactly the evidence-contamination the project refuses. You ground the verdict in the actual chitinase genes the genome carries — and you record *which scope you scanned*, full proteome vs. BGC-region only, before issuing any verdict, because "I found GH18 across the whole proteome" and "I found GH18 inside one BGC" are very different claims. The system prompt is blunt about it: record proteome scope state *before* any CGAD verdict.

So when you saw **CGAD NULL** on the *Trebouxia* run — that's the scan finding no chitin-degradation architecture worth calling (which tracks; it's a green alga, not an insect symbiont swimming in chitin), reported honestly as nothing rather than reached-for.

*Evidence trail:* `README.md:126`, `prompts/CLAUDE_SYSTEM_PROMPT.md:78` (§44), `prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md:53`. The expansion is yours, recorded in your own bundle — I just went and read it instead of inventing one.

Two cross-links worth holding together: CGAD is GH18-only, which is the source of the GH19 blind spot (Bank 88), and its verdict obeys the genome-grounded / proteome-scope-gated / not-isolation-source-gated rule (Bank 34) — so a positive call on a moss strain counts exactly as much as one on a bee strain.

---

## Q7 · What other project jargon is there?

A lot — and the good news is you already wrote it all down. The canonical `docs/GLOSSARY.md` (the 424-line superset we reconciled in v9.7.96, 21 sections) *is* the authoritative set. So the truest answer is "go read your own glossary." But that's a cop-out, so here's a field guide to what actually shows up in run boards and conversation.

**The ten deterministic first-pass scans — CGAD's cousins:**
- **KCB** — Known Cluster Blast. Similarity, *not* identity (the rule you never let anyone forget).
- **RG-GMCI** — Reference-Guided Genome Mining Candidate Inference. Homology-guided linkage of fragmented BGC regions to one reference cluster. A *candidate-linkage* method, not a physical contig joiner.
- **FLBR** — the fragmented-megasynthase census: split-pathway PKS/NRPS fragment sets, graded STRONG/WEAK.
- **CCTT** — compound-class trigger table: class detection from annotation text (the T43-* triggers).
- **CGAD** — Q6.
- **UMED** — RiPP/lanthipeptide maturation-enzyme presence (in-cluster vs GAP).
- **EFLS** — edge-flank linkage: split-pathway candidate pairs across contigs.
- **Resistance** — resistance gene families (APH/Van/Erm) with an HGT guard.
- **bldA / TTA** — the rare-leucine-codon tiering, T1–T4 (the one still emitting spurious T4 on non-actinos — P-11).
- **TFBS** — transcription-factor binding-site motif counts (DasR, DmdR1, BldD, FuR, SARP…).

**Run-board codes you read every day:**
- **Assembly tiers** — GOOD ≥70 / MODERATE ≥45 / POOR ≥20 / VERY_POOR <20 (interior %). The 66/50/33 thresholds are retired.
- **Corrected BGC count** — Interior + ½·Edge + ¼·Full-contig. The **Edge status** (Interior / Edge / Full-contig) is the weighting behind it.
- **AB / AF** — antibacterial / antifungal capacity axes (AB76, AF49…). They are routing priors, not phenotype calls or assay defaults.
- **Lead classes A / B / C** — evidence-axis tiering; raising a lead's class never raises its claim confidence.
- **Strain prefixes** — AS- / AJS- / PENDING- are private (hard-guarded); SID- / WW- are public (Chevrette 2019).

**Claim-safety spine:** *biosynthetic capacity consistent with* (never "produces"); **KCB-dark** (zero similarity → novelty axis); **[E-signal]** (the neutral enediyne note; BSL-2 per-BGC flagging retired); **hglE-KS-PREV-001** (prevalent, habitat-non-specific glycolipid domain); **NAPAA** (excluded as convergent); **Mode B** (the full §1–§48 per-BGC card).

For the rest — **RiQ, HVCP, DAPR, T43**, the architecture-confidence codes, the failure/status codes — I'll send you to the glossary rather than expand letters from memory and risk a confident-but-wrong expansion (the CGAD lesson). Its 21 section headers *are* the map: BGC classes · scan names · regulatory/TFBS · architecture-confidence codes · edge status · evidence axes & lead classes · marker-aware scoring & diagnostic floor · WL/priority tiers · resistance families · assembly tiers · key metrics · claim-safety vocab · standing biological constraints · validation vocab · ecological habitats · release tiers & gates · failure/status codes · plain-language overloaded words · names · the "terms added since v9.7.28" appendix. If a term isn't in one of those buckets, it's probably not load-bearing.

---

## Q8 · Are there more bacterial chitinases we can scan for?

Yes — and there's one gap that should genuinely bother you, given your cohort.

CGAD currently keys on **GH18 chitinases + LPMOs + GlcNAc machinery**. GH18 is the right anchor — it's the dominant bacterial chitinase family. But it isn't the whole story, and the missing piece points straight at your most common genus:

- **GH19 — the one I'd add first.** GH19 chitinases are mechanistically distinct from GH18 (inverting vs. retaining glycosidases), and they were long thought plant-specific until they turned up abundantly in **Streptomyces**. Your cohort is Streptomyces-heavy. A GH18-only scan therefore risks *systematically under-calling* chitinolytic capacity in exactly the genus you have the most of — a quiet, consistent blind spot, not random noise. That's the dangerous kind: it reads like a real biological signal ("these strains carry less chitin machinery") when it's actually a marker gap.
- **GH20** — β-N-acetylhexosaminidases. The downstream step: they cleave GlcNAc off the chito-oligomers GH18/GH19 produce. Adding them rounds out the *cascade* (endo-chitinase → oligomers → GH20 monomers → GlcNAc catabolism) instead of only catching the entry enzyme.
- **Chitin-binding CBMs (CBM5 / CBM12 / CBM14)** — non-catalytic, but they're bolted onto chitin-active enzymes specifically to grip chitin. Excellent *corroborating* signal in the CCTT spirit — a chitinase carrying a chitin-binding module is a stronger call than the catalytic domain alone.
- **AA10 specifically.** You already scan "LPMO" — worth confirming the marker is keyed to **AA10** (the bacterial chitin-active LPMO family) and isn't accidentally catching **AA9** (fungal cellulose LPMOs). Same word, different substrate.

**The honest boundary, and it's a hard one:** I'm confident in the *CAZy family names* — GH18, GH19, GH20, AA10 are stable nomenclature and the biology above is textbook. I am **not** going to hand you Pfam or TIGRFAM accession numbers from memory, because naming the wrong `PF#####` is precisely the invented-accession failure mode the whole project exists to refuse. The specific HMM profiles to wire into the marker catalog need verifying against CAZy / dbCAN before they go anywhere near `build_bgc_markers.py`.

**And the doctrine carries over:** any new chitinase marker inherits CGAD's rule — genome-grounded, proteome-scope-gated, *never* isolation-source-gated. A GH19 hit is capacity, recorded with its scope; it is not "this bee symbiont must degrade fungal walls."

So: **GH19** is the real addition, **GH20 + chitin-CBMs** are the rounding-out, and **AA10** is a verification rather than a gap. It's a clean, well-motivated CGAD enhancement — but it's patch-lane work, not something to wire in from the relaxed-Q&A chair. If you want to actually chase it, the concrete next step is pulling the current dbCAN HMM accessions for GH19/GH20, and I'm happy to go verify those against live sources when you are.

---

## Q9 · What is idempotent?

An operation is idempotent if doing it twice — or ten times — leaves you exactly where doing it once did. The second application changes nothing the first didn't already do. Formally, f(f(x)) = f(x); intuitively, a light switch that only turns *on* — press ON when it's already on and nothing happens. The opposite is a toggle, which flips every press.

The cleaner test is **assign vs. increment.** `x = 5` is idempotent — set it to five a hundred times, it's five. `x += 1` is not — run it a hundred times and you've added a hundred. Same distinction as HTTP, if that's a frame you have: PUT and DELETE are idempotent (PUT the same resource twice → same state; DELETE twice → still gone), POST is not (POST twice → two records).

**You've shipped examples of it.** [CORRECTION, v9.7.213 audit: this section previously cited *apply_hygiene.sh* as a real, shipped script with specific behavior (git mv, mkdir -p, an existence guard). No file by that name exists anywhere in this bundle — not in `tools/`, not in `scripts/`, not in any CHANGELOG or PATCH_APPLY_LOG entry. Whether it once existed and was removed, or was never actually built, isn't established either way from the tree; either way, the claim was unverified and has been pulled rather than left teaching a capability that isn't there.] Two real, verified examples instead: your redactor (`tools/redact_public_tier.py`) is idempotent — `AS-XXX → AS-XXX`, but `AS-XXX` doesn't match the AS pattern, so re-running the scrub on an already-scrubbed tree changes nothing. You can't double-mangle a strain ID. `sync_version --apply` (`tools/sync_version.py`) is the same shape — it sets strings to the *current* value, so running it twice sets them to the same value, no drift.

**Here's why the concept is worth more to you than the definition** — it's a clean lens on the exact coordination problem that's been costing you cuts. Idempotence is the property that makes *"I'm not sure if I already ran this, so I'll just run it again"* safe. The operations you can re-fire without thinking are the idempotent ones — the scrub, the version sync. The ones that bite when a step runs twice, or when two chats both do them, are the **non-idempotent** ones: appending to a log, bumping a counter, and — the one that actually hurt you — *delivering a cut.* "Deliver the cut" is a POST, not a PUT. Two chats each delivering produces two cuts, or a cut you weren't expecting, exactly the way POSTing an order twice charges you twice.

So the lens is: the workflow steps that need the careful confirm-before-cut handshake are precisely the **non-idempotent, side-effectful** ones. The idempotent ones you can be cavalier about. If you ever want a fast triage of "which steps need the ritual," ask which ones would do damage if they ran twice. Those are your POSTs — guard those, and stop worrying about the rest.

---

## Q10 · What exactly is ijson used for in our Sapote–Mamey?

I name-dropped ijson in Q4 and Q5 as "the thing that streams antiSMASH JSON in chunks." You're asking me to actually back that up, so I read it in the v9.7.97 CODE tier. Short version: ijson lives in exactly **one** module — `mamey/antismash_evidence.py` — and does exactly **two** jobs. Everything else (`cli.py`, the tests) just reports on it or guards against it.

**The problem it solves.** antiSMASH hands you a whole-genome JSON that can be enormous. `json.loads` slurps the entire thing into memory as one object — fine on a tidy genome, a memory bomb (and a stall risk) on a big or messy one; `cli.py:485` literally flags this as "the one step that can stall on a large JSON." ijson is a *streaming* parser: it walks the file and emits pieces as it goes, so memory stays flat regardless of file size. (That's the parse-in-chunks idea from Q5, made concrete.)

**The two jobs:**
1. **Record streaming** (`_iter_records`, default-on when ijson is present). `_ijson.items(stream, "records.item", use_float=True)` yields antiSMASH records one at a time, straight off the `records.item` path, so the engine iterates records without ever holding the whole file.
2. **Bounded KCB/RiQ leaf streaming** (`_stream_kcb_riq`, the default `json_mode="bounded"`). `ijson.parse(raw)` walks the JSON and pulls out *only* the knownclusterblast / RiQ-relevant leaves, with a record cap and a size cap — flat memory, and it never reads the parts it doesn't need.

**The graceful-degradation ladder** (nicely defensive work by whoever wrote it): it tries `import ijson` for the system install first (fastest, if the yajl C backend is present), falls back to the **vendored pure-Python copy** in `_vendor/` if not, and if *neither* exists, sets `_HAVE_IJSON = False` and both paths quietly drop back to `json.loads` full-load. The doctor line tells you which rung you're on: `ijson(system)✓ JSON streaming on` vs `ijson(vendored)` vs `ijson✗ bounded→TXT-only`. So streaming is an optimization, never a hard dependency — Mamey still runs with no ijson at all, just hungrier and slower.

**The one detail worth tattooing somewhere, because it's a real trap:** ijson yields JSON numbers as **`Decimal`**, not `float`, by default. `Decimal` isn't JSON-serializable, so if one slips downstream into `_write_package`'s `json.dumps`, the package write *raises* and you get no output. That's why every call passes **`use_float=True`**, and why there's a dedicated regression test (`test_package_write_smoke.py`) standing guard that no un-floated Decimal ever reaches the writer. A streaming parser's "helpful" default as a downstream landmine.

**And the part that matters for your determinism story:** the module asserts the streaming output is **byte-identical to full-load** (with `use_float=True`). That's not throwaway — it means choosing the fast, memory-light path over the legacy slurp-it-all path *doesn't change a single number in the result.* ijson is purely a *how-we-read* optimization sitting underneath the deterministic guarantee, not a part of it. Exactly where you want a performance hack to live.

*Evidence trail (v9.7.97 CODE tier):* `mamey/antismash_evidence.py` — import ladder (30–46), `_iter_records` (~70–77), `_stream_kcb_riq` (~723–744), byte-identical note (15), `use_float` rationale (74–77); `mamey/cli.py:80–89` (doctor reporting); `tests/test_package_write_smoke.py` (the Decimal guard).

---

# Part 2 · Question-bank answers

*Numbered by position in the 100-question bank so they map straight back to source. Same voice, dialed a little tighter since these come in batches. Definitions referenced here live in the canonical [`GLOSSARY.md`](../docs/GLOSSARY.md).*


---

## Q11 · What does "Can you work from this to get me the full deliverables?" actually trigger?

It triggers everything, in the right order, starting from wherever you are in the workflow.

When you say that phrase — with a ZIP or package uploaded — the chat reads what you've given it and decides: is this a raw antiSMASH ZIP (needs a Mamey run first), a sealed Mamey package (ready for Sapote judgment), or a prior-session handoff (continue from the established context)? Then it runs the appropriate first step, presents the outputs, and offers the complete deliverable set without making you name each item.

The reason this phrase is particularly useful is that it expresses intent without constraining method. You don't have to know that `--mode gold` is the analysis mode (`smoke` was retired in v9.7.161 and `standard` deprecated in v9.7.92 as an alias of gold), whether figures require `render-figures`, or which menu item corresponds to your need. The chat infers it from what you've uploaded and what the package state says.

It also works mid-session. If you've already run Mamey and are partway through Sapote judgment, the same phrase picks up from the last completed step rather than starting over. And if you upload a handoff package from a prior session, the chat reads the established findings and continues without re-deriving what's already been done.

The key design decision behind this behaviour: the pipeline was built to be used conversationally, not syntactically. The structured deliverable menu and the trigger phrases in the Quick Guide exist for precision; this phrase exists for fluency. Both routes produce the same outputs.


## Bank 1 · Why split the pipeline into Mamey (deterministic) and Sapote (judgment), and what does each layer guarantee?
This is the keystone the whole project balances on. **Mamey** is deterministic Python: it reads antiSMASH JSON/GBK, extracts BGCs, computes the corrected counts, runs the ten scans, and emits structured manifests — and it does no judgment, no prose, no claims. Same input, same output, byte-for-byte. **Sapote** is the LLM judgment layer (me): it reads Mamey's structured output and does the interpretation — which lead matters, the ecological synthesis, the claim-safe Mode B prose, the watchlist read.

The reason to split them is that the two halves have opposite failure modes and must not contaminate each other. The numbers have to be *reproducible* — a methods paper lives or dies on someone re-running the extraction and getting the same manifest — and an LLM cannot guarantee that. The prose has to be *judged* — and deterministic code can't weigh evidence. So you keep the reproducible core away from the part that can hallucinate, and you check the second against the first.

What each guarantees is therefore different in kind. **Mamey guarantees determinism and traceability**: every value points back to a named field or a stated rule, nothing is generated, so there's nothing to hallucinate. **Sapote guarantees nothing automatically** — it's fallible judgment — so its guarantee is *procedural*: it operates under the standing claim-safety rules, its outputs are tagged inferred/assumed (Bank 7), and the hallucination traps (Bank 10) check it against Mamey's ground truth. The observed/computed/inferred/assumed vocabulary is just this split drawn in tags: observed + computed is Mamey, inferred + assumed is Sapote. The whole design is the answer to "how do you put an LLM in a reproducible scientific pipeline without it poisoning the science?" — don't let it near the numbers; let it judge, downstream, under rules, and checked.

The split is also *across models* in practice: ChatGPT typically drives Mamey's deterministic extraction while I run as Sapote, which is itself a check — two independent systems, one doing the reproducible mechanics and one doing the judgment, with neither grading its own work — neither model grades its own homework.

## Bank 6 · What is Mode B, and what are its §1–§8?
Mode B is the deepest single-BGC deliverable the pipeline produces — an eight-section structured card that walks one cluster from *what it is* to *what you're allowed to say about it*. It opens with an overview/architecture section and moves through the domain/machinery inventory, the KCB anchor and what it does and doesn't license, the CCTT/diagnostic triggers, co-occurrence and isolation context, and closes with the claim-safe verdict and the rendered markdown card. Every line wears its observed/computed/inferred tag. The point of the eight-section straitjacket is uniformity: a flagship lead and a throwaway cluster get judged by the same rules, so nothing gets a pass for being exciting. (The canonical §1–§8 labels live in `docs/modules/MODE_B_WRITE.md` — I'll point there rather than misquote a section title I only half-verified.)

Under the current FULL ANALYSIS MODE override, *every* BGC gets the full §1–§48 treatment — no compact/flag/minimal entries — with edge and full-contig clusters carrying a truncation-caveat banner so the fragmentation is impossible to miss in the card.

## Bank 7 · Observed / computed / inferred / assumed — what's the difference?
Four confidence tags, in descending order of how much weight they'll bear. **Observed**: it's literally in a named field or file ("the manifest lists product=t1pks"). **Computed**: a stated deterministic rule produced it from observed inputs ("corrected count = Interior + ½·Edge + ¼·Full-contig"). **Inferred**: a judgment step drew it from the evidence ("the domain set is consistent with a reducing PKS"). **Assumed**: you're filling a gap with a default ("assuming the genome is the strain it's labeled"). Every claim wears its tag so a reader sees instantly which wall is brick and which is drywall. It's also the Mamey/Sapote line drawn in vocabulary: observed + computed is Mamey, inferred is Sapote, assumed is where you write down what you couldn't check.

One cluster, all four tags at once: *observed* product=t1pks (it's in the manifest), *computed* corrected-count weight 0.5 (it's an Edge BGC, by rule), *inferred* "reducing-PKS chemotype" (from the domain set), *assumed* the genome really is its labeled strain. A reader can audit each independently — which is the whole point.

## Bank 8 · Why are supplied bioactivity observations strain-level and never pinned to one BGC?
Because the bioassay measures the *extract*, not the *cluster*. When a strain's crude extract knocks back MRSA or Candida, that activity belongs to whatever the strain actually made under those conditions — could be any BGC, a combination, or something unpredicted. Pinning it to one cluster ("BGC09 is the antifungal") is a claim the data can't carry until fractionation connects an active fraction to that cluster. So activity stays at the extract level and a BGC gets "capacity consistent with antifungal activity," never "is the antifungal." Same anti-overreach instinct as KCB=similarity: don't let a suggestive co-occurrence harden into causation.

The only thing that promotes activity from extract-level to cluster-level is bioassay-guided fractionation linking an active fraction to a cluster's predicted product. Until that's done, even a perfect KCB hit on a known antibiotic stays "capacity consistent with" — homology is not an activity assignment.

## Bank 9 · Why can a strain never be called "antifungal-negative"?
Because absence of recorded activity isn't absence of capacity — it's usually absence of the right assay. The cohort's bioassay data is non-standardized: different media, indicators, timepoints, and plenty of "never tested." A strain with no antifungal hit might be a true non-producer or might just never have been screened against Candida under inducing conditions. "Antifungal-negative" launders that gap into a finding. So the rule: contrast strains by *biosynthetic mechanism* (this one carries a polyene, that one a nucleoside-class chitin-synthase inhibitor), never by *phenotype*. Mechanism is in the genome; a phenotype absence is just a hole in the screening record.

The asymmetry is the whole point: a *positive* mechanism call ("carries a polyene") is genome-grounded and defensible, while a *negative* phenotype call depends on assay coverage you don't have. Capacity claims run one direction only — you can credit presence, never debit absence.

## Bank 10 · What is a hallucination-trap / evidence-conservation check?
A hallucination trap is a deliberate tripwire that catches the model *inventing* — if a number, accession, or claim appears that isn't in the evidence, the check fires. Evidence conservation is the companion: when you transform data (parse, merge, summarize), the useful information is *conserved* — you don't silently drop a column or manufacture a value to fill a blank; you carry honest blanks instead. Together they're the project's immune system against the one failure mode that would sink a methods paper — a confident statement with nothing behind it. It's why I read CGAD out of your own README instead of guessing the expansion: that was the trap working on me, exactly as designed.

The simplest trap is a value that must reconcile two ways — e.g. a BGC count derived independently from the manifest and from the scan states; if they disagree, something fabricated or drifted. That's exactly the shape of the AS-XXX count-discrepancy class, which is why it blocks the moss cross-strain work until resolved.

## Bank 16 · Why retire 66/50/33 for 70/45/20?
Those thresholds gate the assembly tier (GOOD/MODERATE/POOR/VERY_POOR), which governs how strong a claim a BGC's fragmentation permits. I know 70/45/20 is authoritative and locked, but I'll be honest that I don't have the original rationale memo in front of me, so I won't reconstruct a justification I didn't read. The *shape* of the change is legible, though: the new ladder is more permissive at the bottom (POOR starts at 20, not 33) and stricter at the top (GOOD needs 70, not 66) — it widens the usable middle and reserves "GOOD" for genuinely clean assemblies. For the actual reasoning, the patch notes around the bump that locked them are the place.

Concretely, the tier sets the truncation-caveat language and caps how strong a *completeness* claim a BGC may carry — so a VERY_POOR strain's clusters all ship with the fragmentation banner, and "complete cluster" language is simply unavailable to them regardless of how good the KCB hit looks.

## Bank 20 · What is "KCB-dark," and why is it a novelty signal?
A BGC is KCB-dark when KnownClusterBlast finds no meaningful similarity to anything in the known-cluster database. That's not a failure — it's arguably the most interesting result you can get: a cluster with real biosynthetic architecture and no known relative is a novelty candidate. The trap it guards against is reading "no hit" as "no value." A KCB-anchored cluster tells you what it resembles; a KCB-dark one tells you it resembles nothing on file — exactly what you want when prospecting for new chemistry. It feeds the novelty axis, and it's why the AS-XXX nikkomycin-class lead mattered: KCB-dark, but T43-NUC + chitin context made it a definitive antifungal a similarity-only scorer would have missed.

The honest counter-caveat: KCB-dark isn't *automatically* exciting either — a degenerate locus or a primary-metabolism gene is also dark. Novelty only counts when dark co-occurs with real architecture *and* a corroborating marker, which is precisely the diagnostic-floor case (Bank 38). Dark alone is a question, not an answer.

## Bank 22 · What is RG-GMCI?
Reference-Guided Genome Mining Candidate Inference. On a fragmented genome, one real BGC can shatter across several contigs, so antiSMASH reports several partial clusters. RG-GMCI uses homology: when two fragments each map to the *same reference producer cluster* in ClusterBlast output, it infers they're pieces of one cluster and links them as a *candidate* pair. The load-bearing word is candidate — it does **not** physically join contigs (that would be an assembly claim it can't back); it raises a linkage hypothesis grounded in shared reference homology, with an adjacency guard against over-linking. It's the fragmentation-aware alternative to counting partial clusters as if they were independent.

The adjacency guard is what keeps it honest: it won't link fragments whose reference-mapped positions overlap or contradict, so two copies of the same gene can't get glued into a phantom cluster. The whole design errs toward under-linking — a missed link is a smaller sin than an invented one.

v9.7.100 reworked the rescue layer without changing that honesty stance — it just stopped throwing away evidence. Three things changed. First, it now reads *all* the ClusterBlast evidence, not just KnownClusterBlast: each shared-reference hit is tagged by where it came from (`db_kind` — a characterized MIBiG cluster, a cross-genome GenBank neighbour, or a sub-operon hit that's excluded from geometry), and each pair records a `rescue_evidence_base` so a cluster with real genome neighbours but no characterized match is no longer invisible — that was the old blind spot, and on one wasp strain 341 of 402 pairs were clusterblast-only, i.e. would have been missed. Second, a `functional_rescue_class` cross-checks the gene roles on each fragment: one fragment carrying the biosynthetic core and the other the tailoring/transport genes is what a real split looks like; both carrying a complete core means they're paralogous clusters, not two halves. Third — and this is the one I'd kicked myself over — a *terminus-truncation rescue* catches the simplest split of all: an Edge region whose boundary sits right at the contig terminus, paired with a small whole-contig "severed arm," is a cluster the assembler cut in two. That physical signal now *overrides* a paralogy verdict when the only thing arguing "paralog" is a gene that's legitimately multi-copy within one cluster (the bottromycin RRE was the case that exposed it). All still candidate inference, still no nucleotide-level joining — just less evidence left on the floor.

## Bank 23 · What is CCTT, and how do the T43-* triggers work?
CCTT is the compound-class trigger table — a deterministic scan that reads antiSMASH's annotation text for diagnostic motifs of specific chemistries, each fired by a named **T43-*** trigger. The clever part is corroboration: a trigger only counts toward scoring if it fires on a *class-compatible* locus. A nucleoside trigger on a nucleoside cluster is signal; the same trigger on an unrelated locus is noise and gets excluded from the class-capacity bonus. CCTT also separates *hits* (gene/motif matches across the genome) from *BGC-carrying counts* (how many distinct clusters carry it): "T43-PHO 8 hits / 1 BGC" is one dedicated phosphonate locus, not a phosphonate-rich strain. That hits-vs-BGCs split was a real fix — pre-v9.7.27 only the hit count showed and it read as strain-level abundance.

That corroboration rule — a signal only counts on a class-compatible locus — is the same logic RES_CLASS_CONCORDANCE (Bank 33) applies on the resistance side. It's the project's general defense against a motif firing in the wrong neighborhood and getting credited as if it belonged there.

## Bank 24 · What are the T43 families?
There are ~17 T43-* tokens, of which 14 are the *diagnostic* triggers that drive scoring. The load-bearing ones: **T43-NUC** (nucleoside chitin-synthase inhibitors — nikkomycin/polyoxin) and **T43-PTM** (HSAF/polycyclic tetramate macrolactams) push **antifungal**; **T43-LAN** (lanthipeptide), **T43-LASSO** (lasso peptide), **T43-THA** (thioamide/YcaO) push **antibacterial**. Then **T43-BLA** (β-lactam — nocardicin, IPNS, clavaminate), **T43-PHO** (phosphonate — pep_mutase), **T43-ENE** (enediyne → the [E-signal] caution), **T43-IDC** (indolocarbazole), **T43-DKP** (diketopiperazine/CDPS), **T43-TOMM** (thiazole/oxazole-modified microcins), **T43-AMC** (aminocyclitol/aminoglycoside — *not* aminocoumarin, a correction we made in the encyclopedia), **T43-TET** (tetracycline/tetronate), **T43-LMPKS** (megasynthase). The tailoring signals **T43-HAL/XHAL** (halogenases) are deliberately *excluded* from the tier floor — they decorate a product, they don't define its class. (A couple of the rarer expansions — T43-NN especially — I'd confirm against the marker registry rather than swear to.)

The deliberate gap between 17 tokens and 14 *diagnostic* triggers is the design: tailoring/structural tokens like HAL/XHAL are present for annotation but withheld from the score, so the tier floor reflects the compound *class*, never its decoration. Presence in the registry and consequence in the score are two separate decisions.

## Bank 25 · What is FLBR / a fragmented megasynthase?
A megasynthase is one enormous multi-domain enzyme — a PKS or NRPS assembly line strung from many modules, sometimes 50+ kb of coding sequence. On a fragmented genome that giant gene often straddles a contig break, so antiSMASH sees two half-assembly-lines instead of one. FLBR is the census that catches this: it inventories the split-pathway fragments (the KS/C/A/T/E modules and their docking domains) and grades the evidence that two fragments belong to one original megasynthase STRONG or WEAK. It's how a VERY_POOR assembly can still yield a defensible "this strain has capacity for a large modular polyketide" — FLBR reconstructs the *candidate* megasynthase from scattered pieces without pretending the contigs are joined.

The STRONG/WEAK grade isn't cosmetic: only STRONG-linked fragments contribute their combined architecture to a capacity claim, while WEAK pairs stay reported-but-separate. So a hopeful guess can never inflate the megasynthase inventory — the burden of proof sits on the link, not on the skeptic.

## Bank 26 · What is UMED / an "in-cluster vs GAP" verdict?
UMED is the maturation-enzyme detector for RiPPs and lanthipeptides. A RiPP isn't built by an assembly line — it's a short precursor peptide chemically *matured* by dedicated tailoring enzymes (cyclases, dehydratases, the lanthionine machinery). UMED asks whether those maturases are present and whether they're **in the cluster** or there's a **GAP**. "In-cluster" means the maturation machinery sits with the precursor — a complete-looking RiPP. "GAP" means the precursor's there but the expected maturase isn't found in the cluster — the honest flag that either the cluster is truncated (fragmentation) or maturation happens elsewhere. It's the RiPP-specific completeness check, and it's why a truncated RiPP fragment gets floored to Inventory rather than over-claimed.

A GAP verdict is what trips the RiPP-fragment ceiling: a precursor-only, sub-8 kb, maturase-less fragment gets capped at Inventory (the `fragment_no_precursor` / RiPP-fragment-floor note in the rationale string), so an incomplete RiPP can never masquerade as a finished molecule.

## Bank 27 · How does EFLS differ from RG-GMCI?
Both rescue fragmentation, but they argue differently. **EFLS** (edge-flank linkage) is positional — it looks at what sits at the broken *edges* of contigs and pairs split-pathway candidates by their flanking context: "these two raw contig ends look torn apart from each other." **RG-GMCI** is homology-driven — it pairs fragments because they map to the same known reference cluster, regardless of position. So EFLS asks "do these edges fit together?" and RG-GMCI asks "do these pieces both look like the same known thing?" They're complementary: EFLS can link a *novel* split cluster with no reference (it doesn't need one), RG-GMCI can link fragments that aren't adjacent (it doesn't need them to be).

In practice they cover each other's blind spots: a *novel* split cluster with no MIBiG relative is invisible to RG-GMCI but catchable by EFLS, while two *non-adjacent* fragments of a known cluster are invisible to EFLS but linkable by RG-GMCI. Running both is belt-and-suspenders on a fragmented genome.

## Bank 28 · What is the resistance scan, and what does a resistance gene next to a BGC suggest?
It scans for resistance-gene families co-located with BGCs — and the payoff isn't defense, it's *target inference*. A producer of a toxic compound has to protect itself, often with a self-resistance gene right in the cluster. So a resistance determinant beside a BGC hints at what the product *does*: an Erm methylase suggests a ribosome-targeting macrolide-like product; a VanHAX cassette suggests a glycopeptide-like cell-wall agent. The current panel covers APH/AAC (aminoglycoside), Erm (MLS), Bla/β-lactam, Cat, Tet, VanHAX, and Fos, with a class-to-compound concordance table and an HGT guard so an imported resistance gene isn't misread as self-resistance. (The bigger upgrade — duplicated *target* genes for resistance-gene-directed mining — is still open, per the markers thread.)

The HGT guard is what separates *self*-resistance from an imported passenger: a resistance gene riding a mobile element, or sitting far from any BGC, reads as acquired rather than as producer self-protection, and its target-inference credit is withheld (the mobile-element demotion in the rationale string).

## Bank 29 · What is the APH-sugar-kinase veto, and why is it needed?
A false-positive killer. APH (aminoglycoside phosphotransferase) detection keys on phosphotransferase motifs — but ordinary sugar kinases in glycogen/trehalose metabolism share that fold and trip the same pattern. Without a veto, every strain's housekeeping carbohydrate metabolism lights up as "aminoglycoside resistance," and worse, that bogus APH cascades into a spurious T43-NUC nucleoside call and a T1 tier. So the veto says: APH_AAC firing in a glycogen/trehalose/sugar-kinase context is a sugar kinase, not resistance — strip it. A small rule that stops a primary-metabolism enzyme from masquerading as resistance-and-bioactivity. The motif matched; the *context* said housekeeping.

The cascade is the real danger: an un-vetoed APH would concord (Bank 33) toward aminoglycoside/nucleoside, corroborate a T43-NUC, and floor a housekeeping sugar locus to a Medium antifungal lead — a fabricated lead built entirely on glycogen metabolism. The veto kills it at the root, before the cascade starts.

## Bank 30 · What is the bldA/TTA tiering, and what does the rare codon have to do with secondary metabolism?
Lovely piece of Streptomyces biology. TTA is a leucine codon that's *rare* in actinomycete genomes, and the tRNA that reads it — bldA — is developmentally regulated: scarce until the cell hits stationary/sporulation phase. So a gene carrying a TTA codon is effectively translationally gated to late growth — exactly when secondary metabolism switches on. A BGC with a TTA codon in a key gene is therefore plausibly growth-phase-coupled to antibiotic production, a real regulatory signal. The T1–T4 tiering grades it (T1 strong/diagnostic down to T4 weak/noise). It's an orthogonal, regulation-level line of evidence layered on top of the structural scans.

The textbook demonstration is *Streptomyces coelicolor*: a bldA mutant can't sporulate or make actinorhodin, because the pathway's activator gene (actII-ORF4) carries a TTA codon it can no longer translate. That's the whole logic in one organism — rare codon, developmentally-timed tRNA, secondary metabolism gated to late growth.

## Bank 31 · Why does bldA emit spurious T4 on non-actinomycetes (P-11)?
The whole TTA logic only *means* something in actinomycetes, where the rare-codon/bldA biology holds. In an alga, a fungus, a Deinococcus, a Mesorhizobium, a TTA codon is just leucine with no developmental gating — so a "T4" there reads GC/codon noise as a regulatory signal. The P-11 defect: the genus denylist only catches a couple of non-actino genera (Gemmata, Melissococcus → correct NOT_APPLICABLE); everything else falls through to "unknown" and emits a meaningless T4. The fix is to gate on *kingdom from the GBK lineage* rather than a hand-maintained genus list. Until then those T4s on the seven non-actino strains are artifacts and get dropped from heat maps. Top open engine defect.

The fix is small and testable: read kingdom from the GBK ORGANISM/lineage line, return NOT_APPLICABLE for anything non-actinobacterial, and lock it with the seven-strain P-11 negative-control set (Bank 72) so the regression can't silently creep back. It's a denylist-to-derivation change — replace a hand-maintained list with a property read off the data.

## Bank 32 · What is TFBS scanning, and which regulator families matter?
TFBS = transcription-factor binding sites. Beyond a BGC's structural genes, its *regulation* leaves footprints — short DNA motifs upstream where regulatory proteins bind. TFBS scanning counts those per BGC for known actinomycete regulator families: DasR (the global GlcNAc/chitin-responsive repressor — which ties straight into the antifungal/chitin ecology story), BldD (master developmental regulator), FuR (iron), DmdR1, the SARP activators. A BGC under a DasR site, for instance, is plausibly induced by chitin breakdown products — a regulation-level hypothesis about *when* the cluster turns on. Deliberately a count, not a claim: motifs present, interpretation left to the judgment layer.

DasR is the one to watch for these strains: it derepresses on GlcNAc (a chitin breakdown product), so a BGC under a DasR site is plausibly switched on *by the very chitin signal* the defensive-symbiosis story centers on. It's a regulation-level hint that lines up with the ecology without being credited *from* the ecology (Bank 34).

## Bank 33 · What is RES_CLASS_CONCORDANCE?
The table linking a *resistance class* to the *compound classes* it's diagnostic for — the logic that turns "there's a VanHAX cassette here" into "consistent with a glycopeptide-class product." When the resistance scan finds a self-resistance gene beside a BGC, concordance checks whether that resistance type *matches* the cluster's predicted chemistry. A match strengthens the call (the producer protects against exactly what it looks like it makes); a mismatch is a flag, not a credit. It's the resistance-side twin of CCTT's corroboration rule: a signal only counts when it's *coherent* with the locus it fired on. (APH_AAC concords with aminoglycoside/aminocyclitol/nucleoside, for example.)

A *mismatch* is its own signal: a resistance gene whose class doesn't fit the cluster's chemistry suggests either a mis-typed cluster or an unrelated determinant. So concordance is a coherence check in both directions — it strengthens a coherent pair and flags an incoherent one, rather than only handing out bonuses.

## Bank 34 · What does "genome-grounded, proteome-scope-gated, NOT isolation-source-gated" mean?
It's CGAD's rule, but it's really the project's evidence creed in one phrase. **Genome-grounded**: the verdict comes from genes the genome actually carries, not a guess. **Proteome-scope-gated**: you must record *what you scanned* — full proteome vs. BGC-region only — before any verdict, because "found across the whole proteome" and "found inside one cluster" are different-strength claims. **NOT isolation-source-gated**: you may never credit a capacity *because of where the strain came from*. "It's a bee symbiont, so it must degrade chitin" is reasoning from the isolation source — the exact evidence contamination the project refuses. Ecology may *motivate* a hypothesis; only the genome may *support* it.

The sin it forbids has a name in the project — *isolation-source contamination of evidence* — and it's insidious precisely because it's so plausible ("bee symbiont, therefore antifungal"). Banning it is what lets a positive call on a moss strain carry exactly the weight of one on a bee strain, which is what makes the cross-habitat comparison fair.

## Bank 35 · Why ten scans, and how do they feed the first-pass page?
The ten deterministic scans — KCB, RG-GMCI, FLBR, CCTT, CGAD, UMED, EFLS, Resistance, bldA/TTA, TFBS — are the genome-wide pre-triage layer: they run once per package and write into `3_scan_states.json` / the evidence channels *before* any per-BGC Mode B. The point is to surface the whole strain's landscape on one **first-pass scans page** (`build_first_pass_scans.py` renders it from the manifest, no re-scan) so you can triage which BGCs deserve deep Mode B rather than diving blind. "First-pass" because they're cheap, deterministic, and comprehensive — the wide net before the focused dive. Ten because each catches a different axis (similarity, fragmentation, class, chitin, maturation, resistance, regulation…) the others miss.

Because they're deterministic and run once, the first-pass page is a *cache*, not a recomputation — `build_first_pass_scans.py` reads the manifest rather than re-scanning, so the triage view is reproducible and free to regenerate. That matters when you're re-cutting docs and don't want scan drift between two renders of the "same" strain.

## Bank 36 · How is a score like AB76 built?
AB/AF are capacity scores, built deterministically then floored and suppressed. The base is a constant plus class-keyword credit: `base_ab = 25 + keyword_score(class_text, AB_KEYWORDS)` (carbapenem +18, phosphonate +15, thiopeptide/thioamide +14, NRPS +12…); `base_af = 20 + AF_KEYWORDS` (HSAF/nikkomycin/polyoxin/nystatin +20, polyene/nucleoside +18, tetramate +16…). On top, a *corroborated* diagnostic trigger adds a +25 bonus and floors the lead to at least Medium — T43-NUC/PTM on AF, T43-LAN/LASSO/THA on AB. Then the *suppressors* fire: primary-metabolism/pigment cores, standing-rule downgrades (NAPAA, hglE), mis-anchored KCB, mobile-element-dominated regions, and uncorroborated triggers all *strip* credit. So "AB76" = base + class keywords + any corroborated diagnostic bonus − suppressions, a transparent sum you can read off the rationale string, not a black box.

Worked example: a lanthipeptide cluster with a corroborated T43-LAN reads `25 (base) + 12 (lanthipeptide keyword) + 25 (diagnostic bonus) = AB62`, then floored to at least Medium. You can read that exact arithmetic off the rationale string rather than trusting the number — which is the point of building the score additively in the first place.

## Bank 37 · What are lead classes A/B/C, and why doesn't class raise claim confidence?
A/B/C grade the *evidence* behind a lead — roughly how many independent, corroborating axes point at it — not how confident you may be about its product. That's the whole point of the rule "raising a lead's class never raises its claim confidence." Class is *strength of the case that this is worth chasing*; claim confidence is *what you can say it makes*, which stays capacity-level no matter how strong the case. A Class-A lead with three corroborating axes is still "capacity consistent with," not "produces." Keeping the two orthogonal stops the natural slide where a well-supported lead quietly gets talked about as a confirmed product.

Practically: class drives *triage* (chase the Class-A leads first), claim drives *language* (all of them get capacity-level prose). Conflating the two is the single most common way a genome-mining paper overreaches — a well-supported lead quietly described as a confirmed product — which is exactly why they're kept on separate axes.

## Bank 38 · What is the diagnostic floor / marker-aware scoring?
Marker-aware scoring means the scorer doesn't just count BGC classes — it reads the *diagnostic markers* (CCTT triggers, TIGRFAMs, resistance genes) and lets them override a naive class score. The **diagnostic floor** is the mechanism: when a corroborated diagnostic marker is present, the lead is *floored* to at least Medium regardless of what KCB thought. Canonical case: the AS-XXX nikkomycin-style cluster — KCB-dark, annotated as unremarkable "other," so a similarity-only scorer buries it — but T43-NUC + the NikJ TIGRFAM + chitin context are a definitive antifungal signature, so the floor lifts it to a real lead. It's the rule that keeps genuinely novel chemistry from being penalized *for being* novel.

AS-XXX's nikkomycin lead is the canonical case the floor exists for (Bank 86): KCB-dark + T43-NUC + NikJ + chitin context, floored to a real antifungal lead a similarity-only scorer would bury. The floor is, in effect, the rule that lets genuine novelty *survive* scoring instead of being penalized for having no known relative.

## Bank 39 · What is DAPR, and why is wiring DAPR scoring a "scoring boundary"?
DAPR is a compound-class framework (`DAPR_CLASS_FRAMEWORK`); currently some of its classes are *annotation-only* — recorded but not feeding the AB/AF score. The open decision is whether to *wire DAPR classes into scoring*. Why that's not a casual patch: it would change how every BGC scores, which is a **scoring boundary** — and crossing one means scores stop being comparable to anything cut before it. Every strain would need re-scoring on the new engine before any cross-strain claim held. So the v9.7.98 disclosure deliberately *surfaced* DAPR scoring as a decision rather than baking it, keeping the cut "no scoring boundary." Good example of the project knowing which changes are cosmetic and which silently break comparability.

The way it's handled is itself the lesson: rather than quietly wiring it (and silently bumping the engine), DAPR scoring is *surfaced as a decision* in `docs/working/`, so crossing a scoring boundary is a deliberate choice you make, not something buried in a patch. Surfacing-not-baking is the general move for any change that touches comparability.

## Bank 40 · What is a scoring boundary?
Any engine change that alters the *numbers* a BGC gets — AB/AF, novelty, corrected count, tier gates — such that a score from before can't be directly compared to one from after. The deep reason it matters: your whole cross-strain story ("X has stronger antifungal capacity than Y") rests on every strain being scored by the *same ruler*. The moment the ruler changes — the v9.7.84 edge-penalty removal, or wiring DAPR — old and new scores are different units, and comparing them is quietly wrong. So the project tracks scoring boundaries explicitly and re-scores the cohort across one before making comparative claims. It's why "no scoring boundary" is a headline on every hygiene cut.

That's why every hygiene cut's disclosure carries an explicit "no scoring boundary" line — it's a promise that scores from this cut stay comparable to the last, so you can keep building cross-strain claims on one ruler. The line is small but load-bearing: it's the contract that the cohort numbers still mean the same thing.

## Bank 41 · Why must the cohort be re-scored before cross-strain claims?
Because the cohort was scored across *several* engine versions, and at least three scoring boundaries stack between the oldest runs (engine ≤1.9.84) and the current line — most consequentially the edge/full-contig penalty removal at 1.9.84→1.9.85. So one strain's AB76 from an old run and another's AB72 from a new run are *not on the same scale*; ranking them compares different rulers. Any defensible cross-strain statement — "the strongest antifungal lead in the cohort" — first requires re-running every strain on one current engine so scores are commensurable. That re-score is pure science work (not a cut), and the v9.7.98 disclosure flags it as the **highest-leverage publication blocker still open**. Within-strain ranking is fine today; across-strain isn't.

The practical line today: *within*-strain ranking (which of this strain's BGCs is the strongest lead) is fine, because all its clusters were scored on one engine; *across*-strain ranking waits on the re-run. That one rule is what keeps the current cohort claims defensible in the interim without freezing all analysis.

## Bank 42 · What are the evidence axes, and how do they combine into a verdict?
A lead isn't one number — it's assessed across several independent *evidence axes*, and the verdict is how they combine. The axes: structural/architectural capacity (is there a coherent assembly line?), KCB similarity (does it resemble a known producer?), novelty (is it KCB-dark?), diagnostic markers (do CCTT/resistance/TIGRFAM signals corroborate a class?), regulation (TFBS/bldA), completeness (edge status, RiPP precursor). Keeping them separate rather than blended is deliberate — they answer different questions and can *disagree* productively: a KCB-dark cluster scores low on similarity but high on novelty, and that tension is information. Lead-class (A/B/C) reflects how many axes independently agree; the claim stays capacity-level regardless. Verdict = the coherent reading across axes, with every axis's contribution legible.

The design bet is that *legible disagreement beats a smoothed average*: a single blended score would hide the KCB-dark-but-architecturally-real tension that's often the most interesting thing about a cluster. Keeping the axes separate keeps that tension visible to the reader instead of averaging it into a meaningless middle.

## Bank 43 · What is the WL tier / priority tiering?
WL = **watchlist** — the lowest, most honest tier in the priority ladder: a chemistry the system *recognizes* but hasn't curated enough to claim. The watchlist cassettes and markers (SMC-017/018/019, SMK-WATCH-001/002/003 — aryl-C-glycoside, corallorazine, azinomycin/genotoxin) are flagged TIER_3_CONTEXT_TAILORING / LOW with a standing instruction — "inventory as a candidate only; no strong claims" — and a wet-lab promotion route (LC-MS/MS, HMM/BLAST confirm). Above the watchlist sit the scored leads (the AB/AF tiers, floored-to-Medium, HIGH). The point of keeping WL as its own tier is to *retain* a recognized signal without letting it leak into a claim — a parking lot for "we've seen this, it's not nothing, but it's not evidence yet." WL interpretation is explicitly a Sapote (judgment-layer) job; the extraction layer does no WL scoring.

A watchlist entry isn't a dead end: each carries a wet-lab route (LC-MS/MS, HMM/BLAST confirm) and a curated-marker requirement, so "watchlist → scored lead" is a *defined promotion* once the evidence is built, not a permanent demotion. It's a holding pattern with an exit, not a graveyard.

## Bank 44 · What is the promiscuity cap, and what is it preventing?
A ceiling on how much any single BGC can contribute to a strain's class-capacity tally — `DEFAULT_CAP = 1.25` (the per-BGC contribution unit, "CNBU") per cluster, plus a fragment ceiling (P4: a large backbone on a sub-45 kb fragment gets its class-capacity capped). What it prevents: one giant, multi-class, or hybrid region inflating a strain's *apparent biosynthetic breadth*. Without it, a single sprawling NRPS–PKS–terpene hybrid could make a strain look like it has the capacity of three, skewing any "this strain is more biosynthetically diverse" comparison. The cap keeps the unit of accounting honest: a BGC is worth at most so much, however many things it gestures at. (I'm reading CNBU as the capped contribution unit from the constant; the exact acronym expansion I'd confirm in the scoring module rather than assert.)

The claim it defends is the cross-strain *diversity* comparison specifically: without the cap, biosynthetic breadth (how many distinct classes a strain can make) would be hostage to one strain happening to carry a giant hybrid — an assembly accident, not a biological difference. The cap makes breadth a property of the strain, not of its contig luck.

## Bank 45 · How does the compound-class annotation layer pick a chemotype?
It reads a BGC's architecture and assigns a *chemotype* — currently ~16 chemotypes mapped against ~32 MIBiG reference clusters. It's deliberately architecture-driven and claim-safe: it calls the *class* the machinery is consistent with (a reducing PKS chemotype, an HSAF/PTM macrolactam, a glycopeptide-like cassette), not a compound. Of those chemotypes, only some carry a *scored consequence* — the ones tied to a diagnostic trigger or an AB/AF keyword move the score; the rest are annotation-only context. The call sits next to the contig in the card so the class always travels with its evidence. That split between "annotated" and "scored" chemotypes is exactly why wiring more of them into scoring is a boundary, not a tweak (Bank 39).

That annotated-but-unscored set is exactly where DAPR lives (Bank 39) — chemotypes recognized and recorded, deliberately held out of the score until someone decides to cross the boundary. The layer is the *inventory*; turning an annotation into a score is a separate, guarded decision, never automatic.

## Bank 46 · Why is NAPAA permanently excluded from comparative claims?
Because it's *everywhere and tells you nothing*. NAPAA shows up across the cohort regardless of habitat, so its presence can't distinguish a bee symbiont from a moss isolate — it's not ecologically informative. It also rode in on the now-retired Nosema hypothesis (the idea it tied to a specific host-disease context), which didn't hold up. So the standing rule downgrades it: it can be inventoried, but it never counts toward a cross-strain or cross-habitat contrast. Including a ubiquitous signal in a comparison just adds noise that *looks* like signal — the exclusion keeps the comparative axis populated only by things that actually vary across the cohort.

NAPAA is the textbook instance of the project's general exclusion principle: a signal's comparative value is its *variance across the cohort*, not its presence. Anything near-universal gets downgraded for comparison no matter how real it is, because it can't discriminate — the same reasoning that retires hglE-KS-PREV-001 (Bank 47).

## Bank 47 · Why is hglE-KS-PREV-001 (hexacosalactone) excluded as habitat-non-specific?
Same logic as NAPAA, different molecule. The hglE-KS-PREV-001 marker (hexacosalactone-class) is *prevalent and habitat-non-specific* — it turns up across 8+ strains spanning 7 genera and 3 habitats. A signal that common can't carry a habitat-specific or strain-distinguishing claim, so it's downgraded out of comparative ranking. The nuance the rationale string preserves: the downgrade is about *comparative* use — its structural novelty, if any, is unaffected (the suppressor note literally reads "structural novelty unaffected"). It replaced the earlier BRYO-HGT-001 marker, which was retired in its favor precisely because hglE-KS-PREV-001 is the better-characterized, more honestly-labeled prevalent marker.

It earned its place by *replacing* BRYO-HGT-001, which had been doing the same job worse — labeled as if bryophyte-specific when it wasn't. Swapping in the honestly-named "prevalent, habitat-non-specific" marker is a small example of the project correcting a name that implied more specificity than the data supported.

## Bank 48 · Why is the saccharide class downgraded?
Because it sits too close to *primary metabolism* and is too ubiquitous to be informative. Sugar biosynthesis/modification machinery is everywhere — much of it housekeeping carbohydrate metabolism, not dedicated secondary-metabolite production — so a "saccharide BGC" call is a weak basis for a bioactivity or novelty claim. It's the same family of reasoning as the APH-sugar-kinase veto (Bank 29): carbohydrate machinery is a frequent false-positive source for "interesting chemistry." So saccharides are inventoried but downgraded out of the comparative lead ranking by standing rule.

The nuance the downgrade has to hold carefully: plenty of real antibiotics are glycosylated (aminoglycosides, glycopeptides), so the rule downgrades the *bare saccharide class call*, not sugar chemistry wherever it appears. A glycosyltransferase decorating an NRPS aglycone is still scored on the NRPS — the sugar isn't vetoed, the lone "it's a saccharide" verdict is.

## Bank 49 · What is the enediyne [E-signal], and why was the per-BGC BSL-2 flag retired?
Enediynes are a genuinely dangerous class — extremely potent DNA-cleaving warheads (calicheamicin-like). A confirmed `ene_KS` enediyne carries an **[E-signal]** claim-safety note flagging the cytotoxicity/self-protection review and standard-SOP handling. What was *retired* was the per-BGC **BSL-2 flag**, and the reasoning is sharp: a *selective* biosafety flag gives false reassurance. If you flag some BGCs BSL-2 and not others, a reader infers the unflagged ones are cleared — which you can't promise. The neutral [E-signal] note replaced it: it raises the specific enediyne caution without implying a safety verdict on anything else. There's also a real-vs-artifact step — confirm a genuine `ene_KS` call against an `hglE-KS` cross-reaction at the gene level before acting on it.

The retired-BSL-2 reasoning generalizes to a useful rule: a *selective* safety flag is worse than none, because silence on the unflagged items reads as clearance you can't promise. Better to carry a neutral hazard note on the specific class and make no implied verdict about everything else.

## Bank 50 · What does "KCB = similarity, not identity" prevent in practice?
It prevents the most seductive overreach in genome mining: reading "this cluster looks like the calicheamicin cluster" as "this strain makes calicheamicin." KnownClusterBlast reports *homology* to a known cluster — a similarity signal — but homology isn't identity: the hit cluster can share architecture and still make a different molecule, a tailored variant, or nothing under your conditions. So a KCB hit licenses "capacity consistent with the [X]-class," never "produces [X]." It's the difference between "related to" and "is," and the whole claim-safety edifice rests on never letting the first quietly become the second. (It's also why a *mis-anchored* KCB hit — one whose class diagnostic is absent — gets its anchor-derived credit suppressed.)

The pipeline enforces this mechanically too: a *mis-anchored* KCB hit — one whose class-defining diagnostic is absent from the cluster — has its anchor-derived credit suppressed (the MIS-ANCHOR note). So "looks like X but lacks X's signature" can't quietly borrow X's score; the resemblance has to be backed by the diagnostic to pay out.

## Bank 66 · HMMER vs BLAST — what's the difference?
Both find homology, but they ask different questions. **BLAST** aligns one sequence against another (or a database) pairwise — fast, good for "what does this specific protein resemble?" **HMMER** searches with a *profile hidden Markov model*: a statistical model built from a multiple alignment of a whole *family*, encoding which positions are conserved and which vary. So HMMER answers "does this protein belong to this family?" and catches distant members BLAST would miss, because the profile knows position 40 is always a catalytic His while position 41 is anything. In practice antiSMASH and Pfam/TIGRFAM use profile HMMs to *call domains and families*; BLAST (KnownClusterBlast) compares whole *clusters* to known ones. Different granularity, complementary jobs.

In this stack you mostly *consume* both rather than run them: antiSMASH already ran the profile-HMM domain calls (Pfam/TIGRFAM) and the KnownClusterBlast, and Mamey reads those outputs. So the distinction matters less for "which tool do we run" and more for "what does this annotation field actually mean" when a marker reads it.

## Bank 67 · What is a profile HMM / a marker?
Worth a correction here: in *this* pipeline a "marker" usually isn't a profile HMM. A Mamey/Sapote marker is a curated *detection rule* — a `Marker`/`Cassette` dataclass in `mamey_markers.py` / `sapote_markers.py` carrying an id, a tier (e.g. TIER_3_CONTEXT_TAILORING), a confidence, a target pattern (often a regex over antiSMASH's annotation text, like `r"corallorazine"`), and a wet-lab confirmation route (`hmm_blast_confirm`, LC-MS/MS). So the markers are a lightweight, auditable rule layer *on top of* antiSMASH's own HMM output — not a fresh HMM scan. Profile HMMs (the HMMER sense, Bank 66) are what produced the Pfam/TIGRFAM annotations the markers then read. (There's no `build_bgc_markers.py` in the tree — that was my question-bank shorthand; the registries are the `*_markers.py` files.)

The upside of markers being plain rules rather than opaque models is auditability — you can read a `Marker`'s regex and tier and *see* why it fired, which is exactly what a hallucination-conscious pipeline wants. The cost is recall (a regex misses paraphrases an HMM would catch), which is why the wet-lab `hmm_blast_confirm` route exists as the backstop.

## Bank 68 · What are Pfam / TIGRFAM / dbCAN accessions, and why won't you quote them from memory?
Pfam (PFxxxxx), TIGRFAM (TIGRxxxxx), and dbCAN/CAZy (GH/AA/CBM families) are curated databases of protein-family models, each entry with a stable accession — e.g. a GH18 chitinase domain, the NikJ TIGRFAM. The reason I won't recite a specific accession from memory is the no-fabrication hard guard: an accession is exactly the kind of precise-looking token a language model will *confidently invent* (PF + five plausible digits), and a wrong accession in a methods paper is a citation pointing at the wrong family. So the rule: cite an accession only when it's verified against the live database (Pfam/TIGRFAM/dbCAN/CARD), never from recall. Same discipline as "verify DOIs from full text, not the abstract."

The failure mode is specific and real: a model asked for "the chitinase Pfam" will happily emit a plausible PFxxxxx that belongs to something else entirely, and nobody downstream re-checks a confident-looking accession. Treating accessions as verify-only is far cheaper than the erratum — it's the same calculus as flagging T43-NN rather than asserting it.

## Bank 69 · What is BLAST, and what does KnownClusterBlast actually compare?
BLAST (Basic Local Alignment Search Tool) finds regions of local similarity between sequences and scores them with an E-value (lower = less likely by chance). **KnownClusterBlast** is antiSMASH's application of that at the *cluster* level: it takes your BGC's genes and BLASTs them against the MIBiG database of experimentally characterized clusters, then reports which known clusters share the most genes and how well. That's the KCB hit — a similarity verdict ("your cluster shares N of M genes with the X producer cluster"), which the pipeline treats as the KCB anchor. Crucially it compares *gene content and order*, not the molecule — which is exactly why KCB is similarity-not-identity (Bank 50): shared genes suggest a related pathway, not the same product.

The number that matters in a KCB hit is the *fraction of genes shared and their identity*, not merely that a hit exists: a 3-of-30-genes hit and a 28-of-30 hit are both "hits" but mean wildly different things. That's why the anchor carries the gene-fraction, and why a thin hit doesn't license a confident class call.

## Bank 70 · What is "bounded" streaming, and what is the leaf budget?
Following the ijson answer (Q10): some antiSMASH JSON subtrees — KnownClusterBlast and RiQ especially — are huge, and you don't need all of it. "Bounded" streaming means the parser walks the tree but stops descending once it's collected enough: a **leaf budget** caps how many leaf values it'll pull from a given subtree before moving on. So instead of materializing a 200 MB KCB blob, it streams just the top hits up to the budget. It's the difference between "read everything then filter" and "read only as much as the question needs" — bounded memory, bounded time, and (the part that matters for the paper) a *deterministic* truncation rule rather than an ad-hoc cutoff.

The subtle requirement is that the truncation be *deterministic and documented*: if the leaf budget cut off different hits on different runs, the pipeline would lose reproducibility. So the budget is a fixed cap applied in a fixed traversal order — which is what lets the streamed result stay byte-identical to a full load.

## Bank 71 · What is the Decimal-vs-float gotcha?
When you stream JSON numbers, the parser must choose a representation. ijson defaults to Python `Decimal` for exactness — great for fidelity, but it breaks the moment downstream code does ordinary float math or comparisons, because `Decimal` and `float` don't mix cleanly (type errors, or subtle mismatches). The fix is `use_float=True`, telling ijson to emit plain floats so streamed values behave identically to a `json.loads` parse. A small flag with a big consequence: it's what guarantees the streaming path is *byte-identical in result* to the full-load path — the optimization must not change the answer.

It's a *gotcha* specifically because it fails silently and late: the parse succeeds, the values look right in a print, and the Decimal/float clash only surfaces deep in a comparison or a sum — often as a wrong number rather than a clean crash. Setting `use_float=True` up front is much cheaper than chasing a phantom scoring discrepancy later.

## Bank 72 · What is a regression test, and what makes a "negative control" test?
A **regression test** pins a known-good output so a future change can't silently break it: capture "on input X the engine produced Y," and the test fails the day Y changes unexpectedly. A **negative control** is the inverse — it asserts the engine *correctly does nothing*: feed an input that *should not* trigger a signal and assert the signal stays off. The P-11 set is exactly this: seven non-actinomycete genomes that should yield *no* bldA T4 call, used to catch the spurious-T4 defect. Negative controls are the under-appreciated half — most scorer bugs aren't "missed a real hit," they're "fired on something it shouldn't have," and only a negative control catches those.

The project leans on negative controls deliberately because its whole value proposition is *not over-claiming*: a generous scorer is worse than a stingy one, so the tests that matter most are the ones asserting "stayed quiet when it should have." P-11, the APH veto, and the mobile-element demotion are all really negative-control stories.

## Bank 73 · What is an xfail, and why is ISID-XXX kept as an xfail tripwire?
An **xfail** ("expected failure") is a test you assert *should* fail right now, for a known reason — it stays green as long as it fails, and flips to a loud **xpass** the moment it starts passing. Perfect for a tripwire: ISID-XXX is a MIBiG entry whose organism record is corrupted/unreachable (taxId 2601673, network down). Rather than delete the test or silently skip it, it's kept as an xfail — so the failure stays *visible* in every run, and the day the upstream record is fixed, the test xpasses and signals "you can restore this and remove the marker." It's how you defer something without forgetting it: a deferral that announces itself the instant the blocker clears.

The reason it's an xfail and not a `skip` is visibility: a skip is silent and easy to forget, while an xfail stays *on the scoreboard* every run and actively flips to xpass the moment the blocker clears. It's deferral with a built-in reminder — the only kind of deferral that doesn't quietly rot into a permanent gap.

## Bank 76 · What is a GBK file, and what is the _gbk_shim for?
A **GBK** (GenBank) file is the standard flat-file format for annotated sequence — a header, a FEATURES table (genes, domains, coordinates, qualifiers), and the sequence. antiSMASH emits per-region `region*.gbk` files carrying its annotations. The **`_gbk_shim`** is a *minimal, dependency-free GenBank parser* the pipeline vendors to read those files — it deliberately replaces Biopython's `SeqIO`. Why re-implement parsing? To shed a heavy third-party dependency for the one narrow job the pipeline needs: pulling the FEATURES table and Pfam/TIGRFAM qualifiers out of antiSMASH region GBKs (`extract_gbk_pfam_hits`). Fewer dependencies means a more reproducible, portable bundle — which matters when the methods paper has to install and run cleanly somewhere else.

There's a real engineering tradeoff here: Biopython is powerful but heavy and a moving dependency target, and the pipeline needs exactly one narrow capability from it. A ~200-line vendored parser you control beats a multi-megabyte dependency you don't — especially when the methods paper has to install cleanly on a reviewer's machine years from now.

## Bank 78 · What is a PKS vs an NRPS, and what is a megasynthase?
Both are modular *assembly-line* enzymes that build complex molecules one building block at a time. A **PKS** (polyketide synthase) extends a carbon chain using acyl units — fatty-acid synthesis run as a programmable factory — giving erythromycin, the polyenes, and such. An **NRPS** (non-ribosomal peptide synthetase) strings together amino acids, including weird non-proteinogenic ones, without a ribosome — giving peptides like vancomycin and the β-lactam precursors. Each module adds one unit, and the order of modules encodes the product. A **megasynthase** is one of these taken to extremes: a single enormous protein (or a few) carrying many modules — tens of kilobases of coding sequence — which is exactly why it's so vulnerable to being split across a contig break (Bank 25, FLBR).

The cases that matter most for these strains are often *hybrids* — PKS-NRPS assembly lines mixing acyl and amino-acid units (HSAF/PTM is exactly this, Bank 85). Hybrids are also the largest megasynthases, so they're where fragmentation bites hardest and FLBR (Bank 25) earns its keep.

## Bank 79 · What are the core PKS domains?
Reading the assembly line left to right: **KS** (ketosynthase) does the chain-extending condensation; **AT** (acyltransferase) picks and loads the next building block; **ACP** (acyl carrier protein) is the tether the growing chain rides on. Then the optional *reductive loop* that sets oxidation state: **KR** (ketoreductase) → hydroxyl, **DH** (dehydratase) → double bond, **ER** (enoylreductase) → single bond. Whichever of KR/DH/ER are present determines how reduced that position ends up (the difference between a highly-oxygenated and a fatty chain). **TE** (thioesterase) at the end releases — often cyclizes — the finished product. The domain string is the program; reading it is how you infer the chemotype.

A worked read: KS-AT-ACP alone leaves a ketone (most oxidized); add KR and you get a hydroxyl; KR-DH a double bond; KR-DH-ER a fully reduced methylene. So scanning the per-module reductive loops down the assembly line is literally how you infer the product's oxidation pattern straight from sequence.

## Bank 80 · What are the core NRPS domains?
Same assembly-line logic, amino-acid alphabet. **A** (adenylation) selects and activates a specific amino acid — the specificity-determining domain (what the Stachelhaus code reads, Bank 81). **T**/PCP (thiolation / peptidyl carrier protein) tethers it. **C** (condensation) forms the peptide bond to the growing chain. Optional **E** (epimerization) flips an L-amino acid to D — common in these products, and part of why they resist normal proteases. **TE** (thioesterase) releases and frequently macrocyclizes the peptide. So a minimal extending module is C-A-T; the number and order of modules, and which A-domains are present, encode the peptide sequence.

Beyond the core C-A-T, real modules carry tailoring domains that change the product: *Cy* (heterocyclization) forms the thiazoline/oxazoline rings of products like pyochelin and bacitracin, *Ox* installs oxidations, *MT* methylates. Spotting these is how you move from "a peptide" to "a thiazoline-bearing peptide" — detail that A-domain prediction alone (Bank 81) misses.

## Bank 81 · What is the Stachelhaus code, and what does it predict?
The A (adenylation) domain of an NRPS module chooses *which* amino acid gets incorporated, and the choice is governed by ~8–10 residues lining its substrate pocket. The **Stachelhaus code** is that signature — extract those specificity-conferring residues and you can *predict the substrate* by matching the code against a table of known A-domains. It's how antiSMASH guesses "this module loads threonine." The honest caveat, which fits the project's instincts: it's a *prediction*, strongest for well-characterized substrates and shakier for unusual ones — a hypothesis about the building block, not proof of it. It's on the markers wishlist precisely because A-domain specificity is a powerful but not-yet-wired evidence axis.

Worth knowing it's the *classic* method: newer A-domain predictors (machine-learning models over the whole domain rather than 8 residues) often beat it on unusual substrates. The principle holds — the A-domain pocket encodes specificity — but the 8-residue code is the first-pass, not the last word, which is the right way to treat any single predictor.

## Bank 82 · What is a RiPP, and what does "maturation enzyme" mean?
A **RiPP** (ribosomally synthesized and post-translationally modified peptide) is made the opposite way from NRPS peptides: the ribosome translates a short *precursor* peptide from an actual gene, and then dedicated **maturation enzymes** chemically remodel it — cyclizing, dehydrating, installing thioether bridges, removing a leader sequence. The mature product (a lanthipeptide, lasso peptide, thiopeptide) bears little resemblance to the linear precursor. "Maturation enzyme" is the catch-all for that tailoring machinery, and UMED (Bank 26) checks whether those enzymes are present and *in the cluster* — because a precursor with no maturase nearby is either truncated or matured elsewhere, and you can't claim the finished molecule from the precursor alone.

RiPPs are appealing prospecting targets precisely because the gene *is* the blueprint: the precursor's core sequence is encoded directly, so once you can read the maturation logic you can often predict the product more confidently than for a PKS/NRPS. The catch UMED guards (Bank 26) is that you need the precursor *and* the maturases — the precursor alone is a sequence, not a molecule.

## Bank 83 · What is a lanthipeptide vs a lasso peptide, and why do they score HIGH?
Both are RiPP subclasses with distinctive topologies. **Lanthipeptides** carry lanthionine bridges — thioether cross-links from dehydration + cyclization — giving compact, protease-resistant scaffolds (nisin is the famous one). **Lasso peptides** are threaded knots: the tail is pulled through a macrolactam ring and locked, a genuinely lasso-shaped, remarkably stable fold. They score toward the HIGH/antibacterial end (T43-LAN, T43-LASSO) because these classes are enriched for real, often anti-Gram-positive bioactivity and their machinery is diagnostic — with the precursor *and* the maturases visible, the class call is unusually well-supported. (The claim still stays capacity-level, and a fragment with no precursor gets floored to Inventory regardless.)

The extreme stability isn't incidental: the thioether bridges and the threaded knot make these peptides resistant to proteases and heat, which is both why they survive as defensive molecules in a competitive microbial environment and why they're attractive drug scaffolds. The topology *is* the bioactivity story, not just a structural curiosity.

## Bank 84 · What is a halogenase, and why does halogenation matter?
A **halogenase** installs a halogen (usually Cl or Br) onto a scaffold — flavin-dependent ones on aromatic rings, others on aliphatic carbons. Why it matters: halogenation is a hallmark of *dedicated secondary metabolism* and frequently *tunes bioactivity* — a single chlorine can change potency, selectivity, or target binding (vancomycin, chlortetracycline, pyrrolnitrin all depend on it). So a halogenase flags "this strain decorates its products like real, optimized natural products do." But the project treats it as a *tailoring* signal, not a class definer — T43-HAL/XHAL are deliberately excluded from the tier floor (Bank 24), because halogenation embellishes a product, it doesn't tell you what class the product is.

As a prospecting tell, a halogenase flags "someone optimized this": organisms don't usually carry the machinery to install a halogen unless the decorated product is doing something worth the metabolic cost. So even though it's excluded from the class floor (Bank 24), it's a useful *interest* signal pointing at a cluster worth a closer look.

## Bank 85 · What are HSAF/PTM, and why do they recur across your bee strains?
HSAF (Heat-Stable Antifungal Factor) and the broader **PTM** (polycyclic tetramate macrolactam) family are a hybrid PKS–NRPS antifungal chemotype — dihydromaltophilin-type molecules that disrupt fungal membranes/sphingolipids. They recur across the bee cohort as a *cross-genus, within-habitat* signal: the five-strain HSAF/PTM recurrence spans Saccharopolyspora, Nocardia, Streptomyces, and Micromonospora — four genera, one habitat. That's the project's principal cross-genus finding precisely *because* it's mechanism-level and habitat-linked: different bee-associated genera independently carry the same antifungal machinery, the kind of convergence a defensive-symbiosis story predicts. (T43-PTM is one of the two antifungal diagnostic triggers, Bank 24/36.)

Structurally they're tetramic-acid-bearing macrolactams from a single hybrid PKS-NRPS, and mechanistically they hit fungal sphingolipid biosynthesis (ceramide synthase) — a different target from the polyenes (membrane ergosterol) or the nucleosides (chitin synthase). That mechanistic distinctness is why HSAF/PTM, polyene, and nucleoside leads are treated as *separate* antifungal capacities, not interchangeable ones.

## Bank 86 · What is nikkomycin, and why is it the Candida lead in AS-XXX?
**Nikkomycins** are peptidyl-nucleoside antifungals that inhibit *chitin synthase* — they mimic the substrate, so the fungus can't build its chitin cell wall (polyoxins do the same). In AS-XXX (the flagship VERY_POOR-assembly strain) the nikkomycin-class cluster on NODE_162 is the primary *Candida* lead, and it's the canonical illustration of the diagnostic floor (Bank 38): the cluster is **KCB-dark** and annotated as unremarkable, so a similarity-only scorer would bury it — but the **T43-NUC** nucleoside trigger plus the NikJ TIGRFAM plus chitin context make it a definitive antifungal signature, which floors it to a real lead. It's the single best argument for why marker-aware scoring beats KCB-only.

Chitin-synthase inhibition is an attractive antifungal mechanism precisely because *humans have no chitin* — the target is fungal-specific, so the selectivity ceiling is high. That's part of why a KCB-dark nucleoside lead with the T43-NUC + NikJ signature is worth flooring up rather than burying: the mechanism class is therapeutically interesting, not merely novel.

## Bank 88 · What are GH18/GH19/GH20 chitinases, and how do they relate to antifungal ecology?
Glycoside hydrolase families that cut chitin, but not interchangeable. **GH18** is the big bacterial/fungal chitinase family (and what CGAD currently scans). **GH19** is the other true chitinase family — classically plant/streptomycete, mechanistically distinct (inverting vs. GH18's retaining) — and it's the project's known *blind spot*: because CGAD is GH18-only, a Streptomyces leaning on GH19 chitinases can look chitinase-light when it isn't. **GH20** are β-N-acetylhexosaminidases — they finish the job GH18 starts, cleaving chito-oligomers to monomers. Chitin-degradation capacity is ecologically loaded for these strains (fungal cell walls and insect cuticle are chitin), which is why CGAD exists and why the GH19 gap is on the markers wishlist.

Closing the GH19 gap is a real to-do, not a footnote: until CGAD adds GH19, any cross-strain chitinase comparison *systematically under-counts Streptomyces* — the exact genus the bee story leans on. So the blind spot isn't neutral; it biases a comparison the project cares about, which is why it sits on the markers wishlist.

## Bank 89 · What is resistance-gene-directed genome mining?
A prospecting strategy that flips the usual logic. Instead of "what does this cluster make?", you ask "what is this strain *defended against*?" — and let the resistance gene point you to the product. The sharpest version is **target duplication**: if a strain carries a *second, modified copy* of an essential gene (a duplicate ribosomal protein, a resistant gyrase), that's a strong tell it makes something hitting that target and needs a protected backup. So you mine for the duplicated-target signature and follow it to the nearby BGC. It's powerful because it's *function-first* and class-agnostic — it can surface a novel compound whose cluster looks unremarkable. It's on the open markers list (today's resistance scan does co-located self-resistance, Bank 28; duplicated-target is the upgrade).

The approach has a marquee proof-of-concept: platensimycin/platencin and related fatty-acid-synthesis inhibitors were surfaced by mining for a duplicated FabB/F target — exactly the "second, resistant copy of an essential gene" tell. It's not a hypothetical strategy; it has produced real compounds, which is why duplicated-target is the upgrade the resistance scan is reaching for (Bank 28).

## Bank 90 · What is a self-resistance gene, and how does it hint at a product's target?
A producer of a bioactive compound faces an obvious problem: its own product would kill it. The solution is a **self-resistance gene** — usually carried right in the BGC — that makes the strain immune to what it makes (an Erm methylase modifying its own ribosome, a resistant target variant, an efflux pump, an inactivating enzyme switched off at the right moment). For genome mining that gene is a gift: a *functional fingerprint of the product's mechanism*. A self-resistant ribosomal-modification gene says "this cluster's product targets the ribosome"; a VanHAX cassette says "cell-wall agent." That's the inference RES_CLASS_CONCORDANCE (Bank 33) formalizes and resistance-gene-directed mining (Bank 89) weaponizes — with the HGT guard (Bank 28) to make sure it's really *self*-resistance, not an imported passenger.

The limit to keep honest: not every producer co-localizes its resistance, and not every nearby resistance gene is self-resistance (the HGT-passenger problem, Bank 28). So a self-resistance read is a *strong hypothesis* about target, not a proof — which is exactly why it feeds capacity-level claims and concordance checks rather than a confident mechanism assertion.

---

*Add the next question below.*

---

*Sapote–Mamey Concepts Q&A · current to bundle v9.7.414 / engine Mamey 1.9.152 A running document — concepts are version-stable; inline version references (e.g. "shipped in v9.7.91", "v9.7.97 CODE tier") are historical record, not a currency claim. Companion to `../GLOSSARY.md` (definitions) and `03_Technical_Manual_Encyclopedia.html` (deep internals); Q&A is the conversational "why does it work this way" layer.*
