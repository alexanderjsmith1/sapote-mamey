# Sapote–Mamey · Concepts Q&A

*A running concepts companion to the GUIDE, written as questions and answers. The answers are direct and say what is observed and what is inferred. This is the conversational "why does it work this way" layer. Short definitions live in the canonical [`GLOSSARY.md`](../GLOSSARY.md) (see its **Core concepts** section for the load-bearing terms), and the deep internals live in the Encyclopedia (`03_Technical_Manual_Encyclopedia.html`).*

*Current to bundle v9.7.459 / engine Mamey 1.9.177.*

> **On the numbering.** Two series run here. **Q1–Q11** are the original conversational thread (workflow and first-encounter jargon). **Bank N** entries are numbered by position in the 100-question bank (`Sapote-Mamey_QandA_QuestionBank_100.md`) so each maps straight back to its source question — which is why the Bank numbers are not contiguous (gaps are questions not yet written up, not missing content). Cross-references of the form "(Bank N)" point within this document.

## Contents

**Working with the pipeline & environment**
[Q1 wedged pytest](#q1--what-should-i-do-when-pytest-or-its-environment-becomes-unresponsive) · [Q2 stop button vs timeout](#q2--are-timeouts-explicit-process-termination-and-an-assistants-stop-button-equivalent) · [Q3 usage tokens](#q3--what-are-usage-tokens) · [Q4 chunk](#q4--what-is-a-chunk) · [Q5 parsing](#q5--what-is-parsing) · [Q9 idempotent](#q9--what-is-idempotent) · [Q10 ijson](#q10--what-exactly-is-ijson-used-for-in-sapotemamey) · [Bank 70 bounded streaming](#bank-70--what-is-bounded-streaming-and-what-is-the-leaf-budget) · [Bank 71 Decimal-vs-float](#bank-71--what-is-the-decimal-vs-float-gotcha) · [Bank 72 regression / negative-control tests](#bank-72--what-is-a-regression-test-and-what-makes-a-negative-control-test) · [Bank 73 xfail tripwire](#bank-73--what-is-an-xfail-and-why-is-isid-xxx-kept-as-an-xfail-tripwire) · [Bank 76 GBK files & the shim](#bank-76--what-is-a-gbk-file-and-what-is-the-_gbk_shim-for) · [Q11 choosing full deliverables](#q11--what-does-can-you-work-from-this-to-get-me-the-full-deliverables-actually-trigger)

**Project jargon, scans & the two-layer design**
[Q6 CGAD](#q6--what-is-cgad) · [Q7 project jargon](#q7--what-other-project-jargon-is-there) · [Q8 bacterial chitinases](#q8--are-there-more-bacterial-chitinases-to-scan-for) · [Bank 1 Mamey/Sapote split](#bank-1--why-split-the-pipeline-into-mamey-deterministic-and-sapote-judgment-and-what-does-each-layer-guarantee) · [Bank 6 Mode B named profiles](#bank-6--what-is-mode-b-and-what-are-its-named-profiles) · [Bank 7 observed/computed/inferred/assumed](#bank-7--observed--computed--inferred--assumed--whats-the-difference) · [Bank 8 extract-level bioactivity](#bank-8--why-are-supplied-bioactivity-observations-strain-level-and-never-pinned-to-one-bgc) · [Bank 9 never "antifungal-negative"](#bank-9--why-can-a-strain-never-be-called-antifungal-negative) · [Bank 10 hallucination traps](#bank-10--what-is-a-hallucination-trap--evidence-conservation-check)

**Genome-mining concepts**
[Bank 16 70/45/20 tiers](#bank-16--why-retire-665033-for-704520) · [Bank 20 KCB-dark](#bank-20--what-is-kcb-dark-and-why-is-it-a-novelty-signal) · [Bank 22 RG-GMCI](#bank-22--what-is-rg-gmci) · [Bank 23 CCTT / T43](#bank-23--what-is-cctt-and-how-do-the-t43--triggers-work) · [Bank 24 T43 families](#bank-24--what-are-the-t43-families) · [Bank 25 FLBR](#bank-25--what-is-flbr--a-fragmented-megasynthase) · [Bank 26 UMED](#bank-26--what-is-umed--an-in-cluster-vs-gap-verdict) · [Bank 27 EFLS vs RG-GMCI](#bank-27--how-does-efls-differ-from-rg-gmci) · [Bank 28 resistance scan](#bank-28--what-is-the-resistance-scan-and-what-does-a-resistance-gene-next-to-a-bgc-suggest) · [Bank 29 APH-sugar-kinase veto](#bank-29--what-is-the-aph-sugar-kinase-veto-and-why-is-it-needed) · [Bank 30 bldA/TTA](#bank-30--what-is-the-bldatta-tiering-and-what-does-the-rare-codon-have-to-do-with-secondary-metabolism) · [Bank 31 bldA spurious T4](#bank-31--why-does-blda-emit-spurious-t4-on-non-actinomycetes-p-11) · [Bank 32 TFBS](#bank-32--what-is-tfbs-scanning-and-which-regulator-families-matter) · [Bank 33 RES_CLASS_CONCORDANCE](#bank-33--what-is-res_class_concordance) · [Bank 34 genome-grounded/scope-gated](#bank-34--what-does-genome-grounded-proteome-scope-gated-not-isolation-source-gated-mean) · [Bank 35 the ten scans](#bank-35--why-ten-scans-and-how-do-they-feed-the-first-pass-page)

**Scoring & prioritization**
[Bank 36 AB76 build](#bank-36--how-is-a-score-like-ab76-built) · [Bank 37 lead classes A/B/C](#bank-37--what-are-lead-classes-abc-and-why-doesnt-class-raise-claim-confidence) · [Bank 38 diagnostic floor](#bank-38--what-is-the-diagnostic-floor--marker-aware-scoring) · [Bank 39 DAPR](#bank-39--what-is-dapr-and-why-is-wiring-dapr-scoring-a-scoring-boundary) · [Bank 40 scoring boundary](#bank-40--what-is-a-scoring-boundary) · [Bank 41 cohort re-score](#bank-41--why-must-the-cohort-be-re-scored-before-cross-strain-claims) · [Bank 42 evidence axes](#bank-42--what-are-the-evidence-axes-and-how-do-they-combine-into-a-verdict) · [Bank 43 WL tier](#bank-43--what-is-the-wl-tier--priority-tiering) · [Bank 44 promiscuity cap](#bank-44--what-is-the-promiscuity-cap-and-what-is-it-preventing) · [Bank 45 compound-class annotation](#bank-45--how-does-the-compound-class-annotation-layer-pick-a-chemotype)

**Claim-safety & standing exclusions**
[Bank 46 NAPAA](#bank-46--what-does-the-current-napaa-rule-permit) · [Bank 47 hglE-KS-PREV-001](#bank-47--how-should-hgle-ks-prev-001-be-interpreted) · [Bank 48 saccharide downgrade](#bank-48--why-is-the-saccharide-class-downgraded) · [Bank 49 enediyne [E-signal]](#bank-49--what-is-the-enediyne-e-signal-and-why-was-the-per-bgc-bsl-2-flag-retired) · [Bank 50 KCB = similarity](#bank-50--what-does-kcb--similarity-not-identity-prevent-in-practice)

**Biology primer**
[Bank 66 HMMER vs BLAST](#bank-66--hmmer-vs-blast--whats-the-difference) · [Bank 67 profile HMM / marker](#bank-67--what-is-a-profile-hmm--a-marker) · [Bank 68 Pfam/TIGRFAM/dbCAN](#bank-68--what-are-pfam--tigrfam--dbcan-accessions-and-why-are-they-never-quoted-from-memory) · [Bank 69 BLAST / KnownClusterBlast](#bank-69--what-is-blast-and-what-does-knownclusterblast-actually-compare) · [Bank 78 PKS vs NRPS](#bank-78--what-is-a-pks-vs-an-nrps-and-what-is-a-megasynthase) · [Bank 79 PKS domains](#bank-79--what-are-the-core-pks-domains) · [Bank 80 NRPS domains](#bank-80--what-are-the-core-nrps-domains) · [Bank 81 Stachelhaus code](#bank-81--what-is-the-stachelhaus-code-and-what-does-it-predict) · [Bank 82 RiPP / maturation](#bank-82--what-is-a-ripp-and-what-does-maturation-enzyme-mean) · [Bank 83 lanthipeptide vs lasso](#bank-83--what-is-a-lanthipeptide-vs-a-lasso-peptide-and-why-do-they-score-high) · [Bank 84 halogenase](#bank-84--what-is-a-halogenase-and-why-does-halogenation-matter) · [Bank 85 HSAF/PTM](#bank-85--what-are-hsafptm-and-why-do-they-recur-across-the-bee-strains) · [Bank 86 nikkomycin](#bank-86--what-is-nikkomycin-and-why-is-it-the-candida-lead-in-as-xxx) · [Bank 88 GH18/GH19/GH20 chitinases](#bank-88--what-are-gh18gh19gh20-chitinases-and-how-do-they-relate-to-antifungal-ecology) · [Bank 89 resistance-directed mining](#bank-89--what-is-resistance-gene-directed-genome-mining) · [Bank 90 self-resistance genes](#bank-90--what-is-a-self-resistance-gene-and-how-does-it-hint-at-a-products-target)

---

<a id="part-1--conversational-thread-q1q10"></a>

# Part 1 · Conversational thread (Q1–Q11)

---

## Q1 · What should I do when pytest or its environment becomes unresponsive?

An unresponsive test run can reflect resource pressure, blocked I/O, a child process or a process-management failure. A delay after interruption does not identify its cause. Earlier sandbox observations described a delay of roughly three minutes; the proposed orphaned-child explanation was a hypothesis, not a verified mechanism or a recovery guarantee.

Use the current suite size, logs, process state and tool-session limits when planning a run. Run heavy jobs sequentially when resources are constrained, retain the session/process identifier and monitor through the supported execution tool. Do not start duplicate jobs merely because output is quiet. If a run must stop, use the environment's supported cancellation procedure and preserve its exit, partial outputs and diagnostics before retrying.

After interruption, check whether the original process or children remain active and whether outputs are complete. Escalate an unresolved resource or process failure to the environment maintainer. There is no universal three-minute recovery time and no guarantee that waiting alone repairs the problem.

---

## Q2 · Are timeouts, explicit process termination and an assistant's stop button equivalent?

No. A harness timeout, an explicit process signal and an interface stop action can have different effects on tool calls and child processes. Those effects depend on the execution environment; do not infer them from a stopped assistant turn. Check the actual process/session state and terminal result.

Prefer a bounded test selection and an appropriate tool timeout. Pytest's `-x` or `--maxfail` stops after failures; it does not impose a wall-clock limit. A `--timeout` option requires an installed/configured timeout plugin and its own documented termination behavior. Neither approach guarantees that unrelated subprocesses or external tools unwind cleanly. See the [pytest failure controls](https://www.pytest.org/en/latest/how-to/failures.html) and [pytest-timeout documentation](https://pypi.org/project/pytest-timeout/) for their specific behavior.

When cancellation is necessary, preserve the run identity and evidence, use the supported cancellation method, and verify cleanup before a retry. Interruption is a workflow state, not a test pass or evidence that a fixed recovery interval will follow.

---

## Q3 · What are "usage tokens"?

A token is the unit a language model actually reads and writes in — not words, not characters, something in between. Sub-word chunks. In English it averages ~4 characters or about ¾ of a word, but it is lumpy: "the" is one token, "antiSMASH" is three or four, a UUID or a base64 blob is a whole pile of them. The model never sees text as letters or words; it sees this stream of tokens, and everything it does is counted in them.

"Usage tokens," then, are just tokens in their accounting role — the ones metered to measure how much of the model a conversation has consumed (for limits, for billing, for deciding when a conversation has to be compacted). Here is the part that matters for long working conversations:

It isn't the latest message that gets counted. It is **everything in the model's context, every single turn.** The system prompt, the entire conversation back to the top, every file attached, and — this is the one that bites in patch work — every tool result. When the full suite runs and 200 lines of pytest output come back, that is tokens. When a `view` of the TIER_MANIFEST scrolls 600 file paths past, tokens. The 5 MB zip's file listing, the leak-audit dump, the diff hunks — all of it becomes *input*, and input gets re-counted on the next turn, and the next, because the model re-reads the whole context each time it answers.

That is why a long working conversation gets compacted: the running total gets large enough that the history has to be summarized into a transcript file to make room. It is the same reason to `grep -vE` the noise out of cut logs instead of dumping the raw 290-second pytest stream, and the same reason a `.docx` costs far more than the equivalent markdown. None of that is fussiness; it is token economy.

The honest boundary: the *unit* and the *mechanism* are stable knowledge. The live numbers are not — how many tokens a plan allows, what the context window caps at this month, what any of it costs — because those move, and a confident-but-stale figure is worse than "go check." For the current limits, check the assistant provider's own documentation (`docs.claude.com` / `support.claude.com`).

Rough intuition to carry around: **1 token ≈ 4 characters ≈ ¾ of a word.** A dense page of prose is ~500–800 tokens. A 290-second pytest log, untrimmed, is far more than that.

---

## Q4 · What is a chunk?

Two answers, because Q3 used the word loosely.

**The loose sense (what Q3 meant).** Just "a piece of." Calling a token a "sub-word chunk" used *chunk* as plain English — a bite-sized piece of text. Nothing technical there; the real unit is the token, and "chunk" was hand-waving at "it's a piece, smaller than a word." Fine for conversation, not a term.

**The sense that is an actual term of art — and the one worth knowing.** A *chunk* is a segment a document gets split into for retrieval. This is the one that matters in this world.

When an assistant searches the web, or searches past conversations, the source doesn't arrive whole. Somewhere upstream it has been sliced into chunks — segments from a few sentences to a paragraph — each indexed so a search can find the relevant pieces and hand *those* back, instead of the entire document. So what actually arrives isn't "the article," it is a handful of chunks: the bits that matched, often mid-thought, sometimes missing the sentence that would have made them make sense.

That explains a few things you have probably noticed:
- Those `index="0-2"` numbers in citations are *document-chunk, then sentence-within-it.* The citation points at the specific chunk a claim came from.
- When a past-conversation search comes back as fragments in little tags instead of a clean transcript — those are chunks, not the whole conversation.
- When a search is immediately followed by a `web_fetch` of the full page anyway, it is usually because the chunk gave the headline but cut off right before the number that was needed. The chunk was the teaser; the fetch was the actual read.

*Honest boundary:* retrieval is known to work by chunking — the chunks are visible when they land. The exact slice size and where the boundaries fall are not visible; that is upstream. So treat any claim about "chunks are N sentences" as inference from what arrives, not a spec that has been read.

Two more uses: **streaming chunks** are pieces delivered over a transport, while **parse buffers/events** concern incremental parsing. In this bundle, `_iter_records` and the main JSON evidence walker are separate paths with their own mode, parser and limit behavior. A streaming parser does not imply that every code path avoids whole-file loading; see Q10 and Bank 70.

The bounded main walker selects auxiliary evidence by parsed field/event rules and a leaf budget, not by a retrieval chunk boundary. It continues traversal after auxiliary truncation and has separate RiQ authority/group holds. This reduces selected evidence retention; it is not a proven flat-memory or bounded-time guarantee.

---

## Q5 · What is parsing?

Parsing is the verb the entire Mamey layer is built on. "A deterministic Python extraction engine *parsing* antiSMASH output" — that's the whole job description.

**The plain definition.** Parsing is turning a stream of raw characters that *has* structure into a structure a program can actually walk. Reading a file gets you a blob — a flat run of bytes. Parsing gets you *meaning*: "this is a record, the record has a field called `product_classes`, that field is a list, the list holds these strings." The text was already structured — it followed some format, some grammar — and parsing is the act of recognizing that grammar and building the in-memory version of it. Reading is "I have the characters." Parsing is "I understand what they're saying."

**In this pipeline.** antiSMASH hands you a wall of nested JSON (and GBK) — records inside regions inside protoclusters inside CDS features inside qualifiers, KCB hits hanging off the side. None of that is usable as text. `mamey/parsers.py` is the layer that walks the wall and hands the rest of the engine clean objects: *here is each BGC, here are its boundaries, here are its CCTT tokens, here are its KCB anchors.* The `ijson` streaming from Q4 is parsing built so a 100 MB file doesn't choke it; `_gbk_shim` is the fallback GenBank implementation used when Biopython is unavailable; GenBank inventory construction is not selected only when JSON lacks a field. Every deterministic number Mamey produces starts as a parse.

**Here's the part worth underlining, because it's the spine of the whole Sapote–Mamey split:** parsing is *deterministic.* Same antiSMASH file in, same structured objects out, every time — no judgment, no model. That's Mamey, by construction. The instant you stop recognizing structure and start asking what the structure *means* — "is this BGC actually an antifungal lead?" — you've left parsing and crossed into interpretation, which is Sapote. Parsing is the exact line between the part that's reproducible because it can't be anything else, and the part that needs a verdict. For the methods paper, that line *is* the architecture.

**Parsing is also where the project quietly bleeds. Three real ways it bites:**
- **Schema drift.** Parsing trusts the format. When antiSMASH changes its JSON shape between versions, a parser written for the old shape reads the new one *wrong* — silently, no crash, just bad structure downstream. That's exactly what `test_schema_drift.py` stands guard against.
- **The wrong field.** The manual-BLASTP worklist fix shipped in v9.7.91 was a parsing bug at heart: it scored `locus_tag + product`, but antiSMASH leaves `product` empty and stashes the function in `sec_met_domain` / `gene_functions`. Parse the wrong field and the output isn't wrong, it's *empty* — which is how that worklist shipped blank on real strains until it got caught.
- **The graceful-failure case.** A good parser plans for input that breaks its assumptions. The bundle's redactor is the clean example: `redact_py` parses Python into tokens so it only scrubs comments and strings, never code identifiers — but when a file *won't* tokenize, it doesn't die, it falls back to plain-text scrubbing. That fallback is the mark of a parser written by someone who'd been burned before.

So: reading is having the bytes; parsing is understanding them. And in this project, parsing is also the property line between "deterministic and defensible" and "needs a human or a model to make the call."

---

## Q6 · What is CGAD?

"CGAD NULL" appears in the run boards, and the expansion is recorded in the bundle rather than guessed. Per the canonical glossary and the system prompt (§44), CGAD = **Chitinase Genome Architecture Detection.**

CGAD's current chitinase channel matches annotation text against GH18, GH19, AA10/LPMO, chitin-binding/CBM and GlcNAc buckets. Read the supplied CDS scope and raw counts before interpreting a result: the pattern scan covers its input records, rather than establishing that a complete proteome was searched. Bank 88 explains the dictionary; Bank 34 explains the source-scope rule.

**Why it earns a slot, ecologically.** Chitin is the structural polymer in *both* fungal cell walls and insect cuticle. For a cohort of bee- and wasp-associated actinomycetes hunting antifungals, a strain carrying real chitinase architecture has genome-grounded capacity to chew on fungal cell walls — an antifungal-relevant signal that isn't a BGC at all, it's genome architecture. That's the "two-pronged anti-chitin ecology read" in `F1_Ecology_Readiness`, and it's why CGAD feeds the nucleoside→antifungal axis gate (`test_chitin_gate_h4`).

**The part that's pure Sapote doctrine, and the reason it's worded so carefully.** CGAD is *genome-grounded and proteome-scope gated — but NOT isolation-source gated.* Read that as a claim-safety rule. You don't get to credit a strain with chitin-degradation capacity because it came off a bee; that's reasoning from the isolation source, which is exactly the evidence-contamination the project refuses. You ground the verdict in the actual chitinase genes the genome carries — and you record *which scope you scanned*, full proteome vs. BGC-region only, before issuing any verdict, because "I found GH18 across the whole proteome" and "I found GH18 inside one BGC" are very different claims. The system prompt is blunt about it: record proteome scope state *before* any CGAD verdict.

For the historical *Trebouxia* example, `CGAD NULL` alone does not establish biological absence or explain it by the isolate's ecology. Open the original scan receipt, annotation counts and recorded input scope before reusing that statement. The current pattern scanner reports `SOURCE_DERIVED`; the first-pass page itself says that a motif-only scan cannot establish a true null.

*Evidence trail:* `docs/GLOSSARY.md` ("Scan names and abbreviations" table, CGAD row), `prompts/CLAUDE_SYSTEM_PROMPT.md` (the CGAD §44 checklist line), `prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md` (the deterministic-scan table, CGAD row). The expansion is read from the bundle, not invented.

Two cross-links worth holding together: the current source-pattern dictionary includes GH18 and GH19, plus AA10/LPMO, chitin-binding and GlcNAc buckets (Bank 88); these are annotation-text patterns, not proof of exhaustive validated enzyme-family detection, and its verdict obeys the genome-grounded / proteome-scope-gated / not-isolation-source-gated rule (Bank 34) — so a positive call on a moss strain counts exactly as much as one on a bee strain.

---

## Q7 · What other project jargon is there?

A lot, and it is all written down. The canonical `docs/GLOSSARY.md` *is* the authoritative set; `docs/GUIDE/04_Glossary.md` is only a pointer to it. So the truest answer is "read the glossary." Here is a field guide to what actually shows up in run boards and conversation.

**The ten deterministic first-pass scans — CGAD's cousins:**
- **KCB** — Known Cluster Blast. Similarity, *not* identity (the rule never to forget).
- **RG-GMCI** — Reference-Guided Genome Mining Candidate Inference. Homology-guided linkage of fragmented BGC regions to one reference cluster. A *candidate-linkage* method, not a physical contig joiner.
- **FLBR** — the fragmented-megasynthase census: split-pathway PKS/NRPS fragment sets, graded STRONG/WEAK.
- **CCTT** — compound-class trigger table: class detection from annotation text (the T43-* triggers).
- **CGAD** — Q6.
- **UMED** — RiPP/lanthipeptide maturation-enzyme presence (in-cluster vs GAP).
- **EFLS** — edge-flank linkage: split-pathway candidate pairs across contigs.
- **Resistance** — resistance gene families (APH/Van/Erm) with an HGT guard.
- **bldA / TTA** — rare-leucine-codon count tiers, T1–T4; see Bank 31 for current taxonomy applicability and unresolved cases.
- **TFBS** — transcription-factor binding-site motif counts (DasR, DmdR1, BldD, FuR, SARP…).

**Run-board codes you read every day:**
- **Assembly tiers** — GOOD ≥70 / MODERATE ≥45 / POOR ≥20 / VERY_POOR <20 (interior %). The 66/50/33 thresholds are retired.
- **Corrected BGC count** — Interior + ½·Edge + ¼·Full-contig. The **Edge status** (Interior / Edge / Full-contig) is the weighting behind it.
- **AB / AF** — antibacterial / antifungal capacity axes (AB76, AF49…). They are routing priors, not phenotype calls or assay defaults.
- **Lead classes A / B / C** — evidence-axis tiering; raising a lead's class never raises its claim confidence.
- **Strain prefixes** — do not establish public authority. With no profile or explicit public override, the current resolver defaults to PRIVATE, including AS-, SID- and WW-shaped IDs. Exact privacy-profile assignments and explicit overrides have separate rules; without a profile, the AJS/PENDING/private-registry guards can refuse PUBLIC. A PUBLIC run label is not disclosure permission.

**Claim-safety spine:** *biosynthetic capacity consistent with* (never "produces"); **KCB-dark** (zero similarity → novelty axis); **[E-signal]** (the neutral enediyne note; BSL-2 per-BGC flagging retired); **hglE-KS-PREV-001** (prevalent, habitat-non-specific glycolipid domain); **NAPAA** (registry-neutral; prior Nosema hypothesis retired); **Mode B** (a card under the selected `full48` or `current50_v2` contract; see Bank 6).

For the rest — **RiQ, HVCP, DAPR, T43**, the architecture-confidence codes, the failure/status codes — go to the glossary rather than expand letters from memory and risk a confident-but-wrong expansion (the CGAD lesson). Its 21 section headers *are* the map: BGC classes · scan names · regulatory/TFBS · architecture-confidence codes · edge status · evidence axes & lead classes · marker-aware scoring & diagnostic floor · WL/priority tiers · resistance families · assembly tiers · key metrics · claim-safety vocab · standing biological constraints · validation vocab · ecological habitats · release tiers & gates · failure/status codes · plain-language overloaded words · names · the "terms added since v9.7.28" appendix. If a term isn't in one of those buckets, it's probably not load-bearing.

---

## Q8 · Are there more bacterial chitinases to scan for?

The current `CHITINASE_PATTERNS` already includes GH18, GH19, AA10/LPMO, a broad chitin-binding/CBM bucket and GlcNAc wording. These are annotation-text matches with source-scope limits, not a validated complete enzyme-family census. The earlier proposal below to add GH19 is out of date: GH19 is already in the list. This page does not add a marker or an analysis.

**Historical enhancement proposal — retained as history, not a current gap inventory:**

> Yes, and one gap matters for this cohort in particular.
>
> CGAD currently keys on **GH18 chitinases + LPMOs + GlcNAc machinery**. GH18 is the right anchor — it's the dominant bacterial chitinase family. But it isn't the whole story, and the missing piece points straight at your most common genus:
>
> - **GH19 — the one to add first.** GH19 chitinases are mechanistically distinct from GH18 (inverting vs. retaining glycosidases), and they were long thought plant-specific until they turned up abundantly in **Streptomyces**. The cohort is Streptomyces-heavy. A GH18-only scan therefore risks *systematically under-calling* chitinolytic capacity in exactly the most common genus — a quiet, consistent blind spot, not random noise. That's the dangerous kind: it reads like a real biological signal ("these strains carry less chitin machinery") when it's actually a marker gap.
> - **GH20** — β-N-acetylhexosaminidases. The downstream step: they cleave GlcNAc off the chito-oligomers GH18/GH19 produce. Adding them rounds out the *cascade* (endo-chitinase → oligomers → GH20 monomers → GlcNAc catabolism) instead of only catching the entry enzyme.
> - **Chitin-binding CBMs (CBM5 / CBM12 / CBM14)** — non-catalytic, but they're bolted onto chitin-active enzymes specifically to grip chitin. Excellent *corroborating* signal in the CCTT spirit — a chitinase carrying a chitin-binding module is a stronger call than the catalytic domain alone.
> - **AA10 specifically.** CGAD already scans "LPMO"; confirm the marker is keyed to **AA10** (the bacterial chitin-active LPMO family) and isn't accidentally catching **AA9** (fungal cellulose LPMOs). Same word, different substrate.
>
> **The hard boundary:** the *CAZy family names* are safe — GH18, GH19, GH20, AA10 are stable nomenclature and the biology above is textbook. Pfam or TIGRFAM accession numbers are **not** given here from memory, because naming the wrong `PF#####` is precisely the invented-accession failure mode the whole project exists to refuse. The specific HMM profiles to wire into the marker catalog need verifying against CAZy / dbCAN before they go anywhere near `build_bgc_markers.py`.
>
> **And the doctrine carries over:** any new chitinase marker inherits CGAD's rule — genome-grounded, proteome-scope-gated, *never* isolation-source-gated. A GH19 hit is capacity, recorded with its scope; it is not "this bee symbiont must degrade fungal walls."
>
> So: **GH19** is the real addition, **GH20 + chitin-CBMs** are the rounding-out, and **AA10** is a verification rather than a gap. It's a clean, well-motivated CGAD enhancement, but it is patch work, not something to wire in casually. The concrete next step is to pull the current dbCAN HMM accessions for GH19/GH20 and verify them against live sources.
>
> ---

## Q9 · What is idempotent?

An operation is idempotent if doing it twice — or ten times — leaves you exactly where doing it once did. The second application changes nothing the first didn't already do. Formally, f(f(x)) = f(x); intuitively, a light switch that only turns *on* — press ON when it's already on and nothing happens. The opposite is a toggle, which flips every press.

The cleaner test is **assign vs. increment.** `x = 5` is idempotent — set it to five a hundred times, it's five. `x += 1` is not — run it a hundred times and you've added a hundred. Same distinction as HTTP, if that's a frame you have: PUT and DELETE are idempotent (PUT the same resource twice → same state; DELETE twice → still gone), POST is not (POST twice → two records).

**The bundle ships examples of it.** [CORRECTION, v9.7.213 audit: this section previously cited *apply_hygiene.sh* as a real, shipped script with specific behavior (git mv, mkdir -p, an existence guard). No file by that name exists anywhere in this bundle — not in `tools/`, not in `scripts/`, not in any CHANGELOG or PATCH_APPLY_LOG entry. Whether it once existed and was removed, or was never actually built, isn't established either way from the tree; either way, the claim was unverified and has been pulled rather than left teaching a capability that isn't there.] Two real, verified examples instead: the redactor (`tools/redact_public_tier.py`) is idempotent — `AS-XXX → AS-XXX`, but `AS-XXX` doesn't match the AS pattern, so re-running the scrub on an already-scrubbed tree changes nothing. You can't double-mangle a strain ID. The version synchronizer (`tools/sync_version.py`) aims to set owned version restatements to the current source values. Its current parser accepts `--check`, but no `--apply`: `python tools/sync_version.py` selects the write path, while `python tools/sync_version.py --check` requests checks. The write path also delegates bootstrap regeneration; a later failure can leave partial bootstrap or version updates. Check the actual result and preserve the before state rather than assuming whole-tree byte idempotence.

**Use idempotence within its stated inputs and state.** A repeatable logical update can still replace source files, destroy an earlier snapshot or fail partway through a set of writes. Changing inputs, concurrent writers and external side effects also require their own review. Idempotence does not supply execution permission, source preservation or release authority.

Before repeating a write, identify the current owner, inputs, destinations and failure contract, preserve required prior bytes, and follow the authorized task. Appends, counters and delivery additionally need duplicate-operation controls. A fixed-point update and a separately authorized release are different workflow decisions.

---

## Q10 · What exactly is ijson used for in Sapote–Mamey?

ijson streams large antiSMASH JSON files. Mamey uses it in two places.

- **Reading records.** `_iter_records` in `mamey/antismash_evidence.py` streams a JSON member when it is at least 20 MiB uncompressed, or when `MAMEY_STREAM_JSON` forces it. Streaming yields one record at a time with `use_float=True`. Small files, or a missing ijson, use a full load. One record can still be large.
- **Bounded evidence.** `--json-evidence bounded` walks the JSON and keeps only selected fields, with limits on auxiliary values. It still reads the whole member, and it converts numeric Decimal scores to float. Bounded mode limits what is kept, not how much memory or time the run uses.

If neither the system ijson nor the vendored copy is available, bounded mode switches to `off` and the run records that. It does not fall back to a full load. `off` turns off the main evidence walker only; other JSON readers keep their own behavior.

`--json-evidence full` is an older selective flatten that uses `json.loads`. It refuses members above 80,000,000 uncompressed bytes. It is not a memory cap or a completeness check.

Bounded output is not byte-identical to a whole-document parse. Check the run's recorded JSON mode, truncation notes and walk counts before relying on JSON-derived evidence.

## Q11 · What does "Can you work from this to get me the full deliverables?" actually trigger?

It requests a scoped deliverable set, starting from the actual input and completed work. Identify the requested outcomes, required evidence and authorized work; the phrase is not a guarantee that every optional analysis or report is implemented or already complete.

When you say that phrase, with a ZIP or package uploaded, the assistant reads what you've given it and decides: is this a raw antiSMASH ZIP (needs a Mamey run first), a sealed Mamey package (ready for Sapote judgment), or a handoff package from earlier work (continue from the established context)? Then it selects the appropriate next step within the user’s scope, reports actual outputs and missing/deferred states, and binds requested follow-on deliverables to their current producers or authored-work requirements.

The reason this phrase is particularly useful is that it expresses intent without constraining method. You don't have to know that `--mode gold` is the analysis mode (`smoke` was retired in v9.7.161 and `standard` deprecated in v9.7.92 as an alias of gold), whether figures require `render-figures`, or which menu item corresponds to your need. The assistant infers it from what you've uploaded and what the package state says.

It also works midway. If Mamey has already run and Sapote judgment is partway through, the assistant should continue from the last step it can confirm was completed rather than starting over. If you upload a handoff package from earlier work, the assistant reads the established findings and continues without re-deriving what's already been done.

The key design decision behind this behavior: the pipeline was built to be used conversationally, not syntactically. The structured deliverable menu and the trigger phrases in the Quick Guide exist for precision; this phrase exists for fluency. Both routes should identify the same requested outcome and evidence contract; actual outputs still depend on the actual inputs, selected settings, dependencies and completed authoring/review.

---

# Part 2 · Question-bank answers

*Numbered by position in the 100-question bank. Definitions live in [GLOSSARY.md](../GLOSSARY.md).*

## Bank 1 · Why split the pipeline into Mamey (deterministic) and Sapote (judgment), and what does each layer guarantee?
This is the keystone the whole project balances on. **Mamey** is deterministic Python: it reads antiSMASH JSON/GBK, extracts BGCs, computes the corrected counts, runs the ten scans, and emits structured manifests — and defers biological judgment. It does generate reports, summaries and receipt text; those
are not finished Sapote interpretation. Analytical reproducibility is checked within the encoded
fingerprint/data scope, not by assuming every package byte is identical: dates, timings, runtime
receipts, rendered metadata and environment-dependent output can differ. **Sapote** is the LLM judgment layer: it reads Mamey's structured output and does the interpretation — which lead matters, the ecological synthesis, the claim-safe Mode B prose, the watchlist read.

The reason to split them is that the two halves have opposite failure modes and must not contaminate each other. The numbers have to be *reproducible* — a methods paper lives or dies on someone re-running the extraction and getting the same manifest — and an LLM cannot guarantee that. The prose has to be *judged* — and deterministic code can't weigh evidence. So you keep the reproducible core away from the part that can hallucinate, and you check the second against the first.

What each guarantees is therefore different in kind. **Mamey aims for deterministic, traceable extraction** within its defined inputs and configuration.
Code can still contain parser, join, scoring or presentation defects; source pointers and engineering
gates make those inspectable, not impossible. Inspect the actual evidence, scoped checks
and unresolved issues rather than treating a deterministic implementation as automatic truth. **Sapote guarantees nothing automatically** — it's fallible judgment — so its guarantee is *procedural*: it operates under the standing claim-safety rules, its outputs are tagged inferred/assumed (Bank 7), and the hallucination traps (Bank 10) check it against Mamey's ground truth. The observed/computed/inferred/assumed vocabulary is just this split drawn in tags: observed + computed is Mamey, inferred + assumed is Sapote. The whole design is the answer to "how do you put an LLM in a reproducible scientific pipeline without it poisoning the science?" — don't let it near the numbers; let it judge, downstream, under rules, and checked.

In practice the split can also run *across assistants*: one drives Mamey's deterministic extraction while another authors Sapote's judgment. Separate roles can support review, but two assistants are not independent scientific validation merely by being different systems. Bind their artifacts and checks, and delegate only within the authorized scope.

## Bank 6 · What is Mode B, and what are its named profiles?
Mode B is the deepest single-BGC deliverable the pipeline produces — a structured card that walks one cluster from *what it is* to *what you're allowed to say about it*. It starts with identity and node/region, moves through the gene-by-gene and core biosynthetic evidence, the KCB anchor and what it does and doesn't license, the alternative hypotheses, the ecological context, and closes with the claim-safe verdict, the provenance ledger, and the experimental decision tree. Every line wears its observed/computed/inferred tag. The point of the fixed section list is uniformity: a flagship lead and a throwaway cluster get judged by the same rules, so nothing gets a pass for being exciting.

Choose the section list by its named profile. Default `full48` uses `FINISHED_FULL48_CURRENT_EVIDENCE` and `mamey/data/mode_b/modeb_full30_corrective_contract.json`; opt-in `current50_v2` uses `FINISHED_FULL50_CURRENT50_V2` and `mamey/data/mode_b/modeb_current50_v2_contract.json`. Follow the [profile matrix](../MODEB_PROFILE_MATRIX.md), emit the selected template, and carry the same `--contract` into verification of the saved authored file. Historical 20/30/current50-v1 objects and their title lists remain separately scoped.

When the user selects a full-roster authored analysis, every locus in scope needs the complete selected-profile card and explicit source uncertainty. Gold extraction, a scaffold, a register count or the phrase FULL ANALYSIS MODE does not automatically author or verify those cards.

## Bank 7 · Observed / computed / inferred / assumed — what's the difference?
Four confidence tags, in descending order of how much weight they'll bear. **Observed**: it's literally in a named field or file ("the manifest lists product=t1pks"). **Computed**: a stated deterministic rule produced it from observed inputs ("corrected count = Interior + ½·Edge + ¼·Full-contig"). **Inferred**: a judgment step drew it from the evidence ("the domain set is consistent with a reducing PKS"). **Assumed**: you're filling a gap with a default ("assuming the genome is the strain it's labeled"). Every claim wears its tag so a reader sees instantly which wall is brick and which is drywall. It's also the Mamey/Sapote line drawn in vocabulary: observed + computed is Mamey, inferred is Sapote, assumed is where you write down what you couldn't check.

One cluster, all four tags at once: *observed* product=t1pks (it's in the manifest), *computed* corrected-count weight 0.5 (it's an Edge BGC, by rule), *inferred* "reducing-PKS chemotype" (from the domain set), *assumed* the genome really is its labeled strain. A reader can audit each independently — which is the whole point.

## Bank 8 · Why are supplied bioactivity observations strain-level and never pinned to one BGC?
A supplied assay observation belongs to its recorded strain, material and assay conditions until separately governed evidence supports a more specific attribution. Keep measured activity separate from a locus's predicted capacity: co-occurrence in one strain or a KCB match does not make that BGC the activity source.

The current `bioactivity_metadata_v1` input contract keeps `compound_linkage = NOT_ESTABLISHED` and rejects a different linkage value. It does not implement locus-linkage admission. Use the [bioactivity metadata contract](../BIOACTIVITY_METADATA_CONTRACT.md) to retain the actual observation and its source; any later linkage needs its own reviewed evidence. The earlier fractionation-only wording was too narrow to serve as a general linkage rule.

## Bank 9 · Why can a strain never be called "antifungal-negative"?
Do not turn an untested strain, missing assay record or failed measurement into an activity-negative finding. If a valid assay reported no activity, report that result within its actual material, target and conditions; it does not establish absence of all biosynthetic capacity.

The bioactivity metadata contract distinguishes `NOT_SUPPLIED / NOT_OBSERVED` from `MEASURED_NEGATIVE / NEGATIVE` and requires those paired states to agree. Preserve that distinction rather than prohibiting all negative observations or substituting a genome-based mechanism hypothesis for an assay result. Cross-strain phenotype comparisons need comparable assay evidence.

## Bank 10 · What is a hallucination-trap / evidence-conservation check?
A hallucination trap is a deliberate tripwire that catches the model *inventing* — if a number, accession, or claim appears that isn't in the evidence, the check fires. Evidence conservation is the companion: when you transform data (parse, merge, summarize), the useful information is *conserved* — you don't silently drop a column or manufacture a value to fill a blank; you carry honest blanks instead. Together they're the project's immune system against the one failure mode that would sink a methods paper — a confident statement with nothing behind it. It's why the CGAD expansion in Q6 was read out of the README instead of guessed: that was the trap working, exactly as designed.

The simplest trap is a value that must reconcile two ways — e.g. a BGC count derived independently from the manifest and from the scan states; if they disagree, something fabricated or drifted. That's exactly the shape of the AS-XXX count-discrepancy class, which is why it blocks the moss cross-strain work until resolved.

## Bank 16 · Why retire 66/50/33 for 70/45/20?
The current `assembly_tier` helper uses the percentage of regions labeled Interior: GOOD at 70% or above, MODERATE at 45% or above, POOR at 20% or above, and VERY_POOR below 20%; an unavailable percentage returns UNKNOWN. These are boundary-derived heuristic labels, separate from source-contig statistics such as N50.

Read the raw boundary distribution, assembly statistics and locus-specific evidence together. A tier label does not show that a whole assembly is clean or that every pathway is complete. The historical 66/50/33 change and its rationale remain dated history; this helper alone does not establish the reason for the thresholds or a universal manuscript claim ceiling.

## Bank 20 · What is "KCB-dark," and why is it a novelty signal?
A BGC is KCB-dark when an admitted KnownClusterBlast search has no meaningful reported match in the selected database. Retain search provenance and distinguish an absent or unbound search from a verified no-match result. Dark status is a prioritization signal, not proof of new chemistry. A coherent biosynthetic architecture with corroborating nucleoside and chitin-context markers can support a class-level antifungal-capacity hypothesis and scoring priority; it does not establish compound identity, expression or antifungal activity.

The honest counter-caveat: KCB-dark isn't *automatically* exciting either — a degenerate locus or a primary-metabolism gene is also dark. Novelty only counts when dark co-occurs with real architecture *and* a corroborating marker, which is precisely the diagnostic-floor case (Bank 38). Dark alone is a question, not an answer.

## Bank 22 · What is RG-GMCI?
RG-GMCI means **Reference-Guided Genome Mining Candidate Inference**. It proposes candidate fragmented-locus relationships from shared reference support and geometry. Read the saved pair with both complete endpoints—strain / full physical contig / region / BGC alias—and keep its effective verdict, supporting references, source version and alternatives together.

The current pairing pool keeps cross-genome ClusterBlast and characterized KnownClusterBlast separate; SubClusterBlast is retained outside pairing. Reference intervals can be **overlapping** or **adjacent** and count as good geometry. When coordinates are unavailable, locus-tag proximity can supply a coarse proxy. Therefore the old statement that any overlap is rejected is incorrect. Neither reference geometry nor a HIGH label proves physical linkage or independently excludes paralogy.

Start with [the channel and inference guide](../reference/04_RGGMCI_ClusterBlast_Utilization.md) to inspect reference availability, parse errors and pair evidence. The v9.7.100 case counts and terminus-rescue anecdote are historical observations; they do not supply current cohort validation or authority to join sequences.

## Bank 23 · What is CCTT, and how do the T43-* triggers work?
CCTT is the compound-class trigger table — a deterministic scan that reads antiSMASH's annotation text for diagnostic motifs of specific chemistries, each fired by a named **T43-*** trigger. The clever part is corroboration: a trigger only counts toward scoring if it fires on a *class-compatible* locus. A nucleoside trigger on a nucleoside cluster is signal; the same trigger on an unrelated locus is noise and gets excluded from the class-capacity bonus. CCTT also separates *hits* (gene/motif matches across the genome) from *BGC-carrying counts* (how many distinct clusters carry it): "T43-PHO 8 hits / 1 BGC" is one dedicated phosphonate locus, not a phosphonate-rich strain. That hits-vs-BGCs split was a real fix — pre-v9.7.27 only the hit count showed and it read as strain-level abundance.

That corroboration rule — a signal only counts on a class-compatible locus — is the same logic RES_CLASS_CONCORDANCE (Bank 33) applies on the resistance side. It's the project's general defense against a motif firing in the wrong neighborhood and getting credited as if it belonged there.

## Bank 24 · What are the T43 families?

The current `CCTT_PATTERNS` dictionary declares **18** keys: HAL, XHAL, PHO, NUC, BLA, AMC, ENE, LAN, LASSO, THA, DKP, IDC, PTM, TET, NN, PYE, GPA and BLT. The older 17-token/14-diagnostic summary is not the current roster. TOMM and LMPKS references elsewhere are not additional keys in this dictionary; TET denotes tetronate/spirotetronate, not tetracycline. Read exact names and descriptions from the source-bound generated catalog.

Dictionary presence, corroboration, axis bonus and tier-floor eligibility are different contracts. Current AB diagnostic prefixes are LAN/LASSO/THA/PHO/AMC/BLA/GPA/BLT; AF prefixes are NUC/PTM/PYE. Eligibility still depends on the scorer’s class-specific and source-context guards. A fired annotation pattern, configured bonus or floor does not establish product identity, expression or activity.

## Bank 25 · What is FLBR / a fragmented megasynthase?

FLBR is a source-pattern census and heuristic fragmentation flag, not a pair-level reconstruction or proof that scattered genes belong to one pathway. The current `scan_flbr` sums mod_KS/hyb_KS/tra_KS annotation counts and mega_NRPS context, and identifies Edge/Full-contig records carrying PKS/NRPS/transAT product wording. At least four KS-like hits plus such fragmented records gives STRONG; at least four total megasynthase-like hits or any such fragmented record gives WEAK; otherwise NULL.

It also reports orphan-motif candidates and rescue context. STRONG/WEAK does not establish a shared product, physical linkage, a joined architecture or measured recovery. Inspect the exact source scope, complete locus identities, pair-specific evidence and remaining uncertainty before interpreting a candidate set.

## Bank 26 · What is UMED / an "in-cluster vs GAP" verdict?

Current UMED is an annotation-pattern and proximity check. It selects declared maturation-gated product tokens and couples matching source hits within a 5 kb flank. Any coupled hit can yield `IN_CLUSTER_OR_PROXIMAL_MATURATION_SOURCE_SUPPORTED`; no coupled hits yield `MATURATION_GAP_SOURCE_DERIVED`; other products are `NOT_MATURATION_GATED`. This does not verify a full maturation complement or that a precursor was found.

The scorer carries the UMED gap as a flag. Its separate RiPP fragment rule tests RiPP-family wording, Edge/Full-contig geometry and a positive sub-8-kb span, then maps a higher tier to the class-dependent bottom tier. It does not use the UMED gap or a direct precursor-absence test; specialized RiPP records can become Low rather than Inventory. Neither rule establishes pathway completeness or production.

## Bank 27 · How does EFLS differ from RG-GMCI?

Current EFLS proposes preliminary shared-label pairs over a capped input set, skipping pairs whose two records are both exactly Interior. It scores intersections of product labels, MIBiG references, cassette families and CCTT labels; FLBR is retained as context, not a scored positional fit. The code does not compare raw contig ends, prove complementary sequence tiles or require different contigs. Unknown geometry also needs explicit review.

RG-GMCI has a separate reference/geometry candidate-inference contract. Shared source annotations can feed both methods, so two outputs are not automatically independent evidence. Neither method joins sequence or establishes physical continuity, production or a single shared pathway; retain both complete locus identities and the actual selected producer/receipt.

## Bank 28 · What is the resistance scan, and what does a resistance gene next to a BGC suggest?
It scans for resistance-gene families co-located with BGCs — and the payoff isn't defense, it's *target inference*. A producer of a toxic compound has to protect itself, often with a self-resistance gene right in the cluster. So a resistance determinant beside a BGC hints at what the product *does*: an Erm methylase suggests a ribosome-targeting macrolide-like product; a VanHAX cassette suggests a glycopeptide-like cell-wall agent. The current panel covers APH/AAC (aminoglycoside), Erm (MLS), Bla/β-lactam, Cat, Tet, VanHAX, and Fos, with a class-to-compound concordance table and an HGT guard so an imported resistance gene isn't misread as self-resistance. (The bigger upgrade — duplicated *target* genes for resistance-gene-directed mining — is still open, per the markers thread.)

The HGT guard is what separates *self*-resistance from an imported passenger: a resistance gene riding a mobile element, or sitting far from any BGC, reads as acquired rather than as producer self-protection, and its target-inference credit is withheld (the mobile-element demotion in the rationale string).

## Bank 29 · What is the APH-sugar-kinase veto, and why is it needed?
A false-positive killer. APH (aminoglycoside phosphotransferase) detection keys on phosphotransferase motifs — but ordinary sugar kinases in glycogen/trehalose metabolism share that fold and trip the same pattern. Without a veto, every strain's housekeeping carbohydrate metabolism lights up as "aminoglycoside resistance," and worse, that bogus APH cascades into a spurious T43-NUC nucleoside call and a T1 tier. So the veto says: APH_AAC firing in a glycogen/trehalose/sugar-kinase context is a sugar kinase, not resistance — strip it. A small rule that stops a primary-metabolism enzyme from masquerading as resistance-and-bioactivity. The motif matched; the *context* said housekeeping.

The cascade is the real danger: an un-vetoed APH would concord (Bank 33) toward aminoglycoside/nucleoside, corroborate a T43-NUC, and floor a housekeeping sugar locus to a Medium antifungal lead — a fabricated lead built entirely on glycogen metabolism. The veto kills it at the root, before the cascade starts.

## Bank 30 · What is the bldA/TTA tiering, and what does the rare codon have to do with secondary metabolism?
Lovely piece of Streptomyces biology. TTA is a leucine codon that's *rare* in actinomycete genomes, and the tRNA that reads it — bldA — is developmentally regulated: scarce until the cell hits stationary/sporulation phase. So a gene carrying a TTA codon is effectively translationally gated to late growth — exactly when secondary metabolism switches on. A BGC with a TTA codon in a key gene is therefore plausibly growth-phase-coupled to antibiotic production, a real regulatory signal. The native T1–T4 labels describe increasing counted TTA burden: T1 zero, T2 one or two, T3 three to five, T4 six or more. They are not the resistance scan’s diagnostic-to-transporter ladder and do not measure expression timing. It's an orthogonal, regulation-level line of evidence layered on top of the structural scans.

The textbook demonstration is *Streptomyces coelicolor*: a bldA mutant can't sporulate or make actinorhodin, because the pathway's activator gene (actII-ORF4) carries a TTA codon it can no longer translate. That's the whole logic in one organism — rare codon, developmentally-timed tRNA, secondary metabolism gated to late growth.

## Bank 31 · Why does bldA emit spurious T4 on non-actinomycetes (P-11)?

The historical P-11 examples identified a taxonomy-applicability problem, not an invitation to infer developmental biology from any TTA count. Current `scan_blda_tta` emits per-BGC NOT_APPLICABLE when `actino_status` recognizes `non_actinomycete`; it still records source counts. The resolver has a broader explicit genus/kingdom-token denylist than the old two-genus description. An unlisted genus returns unknown and is not gated out by this check, so taxonomy and applicability remain review holds.

T4 means six or more counted TTA codons in the scanned BGC-overlapping CDS; it does not establish that the pathway is expressed, silent, inducible or accessible under a particular culture condition. The older lineage-derived gating proposal remains a separate owner/scientific design question, not implemented authority or permission to alter the classifier.

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
The “ten scans” list is a project overview of evidence channels, not proof that every channel ran genome-wide. Check each source's input scope and receipt. For example, `run_source_scans` applies chitin annotation patterns to supplied CDS and initially records RG-GMCI as `PENDING_NOT_RUN`, because its ClusterBlast context is supplied separately by the CLI.

`build_first_pass_scans.py` reads `manifest.json` to render a report; it does not rerun those scans. Its current report lists selected sections rather than a complete ten-channel execution check. Rebuilding that view can write a new Markdown file, so retain its source manifest/hash and the actual channel states rather than treating a reproducible view as complete source coverage.

## Bank 36 · How is a score like AB76 built?
AB/AF are versioned routing/capacity scores, not measurements of activity. The installed scorer starts from class-keyword baselines, with a max-per-protocluster branch for suspected overmerge, then applies only eligible chemotype and corroborated diagnostic credit. Subsumption prevents some duplicated credit; class-specific guards and primary/mobile-context clamps can limit an axis. Eligible source-bound rescue context is applied before 0–100 bounds and tier handling. The retained `edge_penalty` currently returns zero; boundary-weighted BGC counts and architecture uncertainty are separate from axis-score deductions. Read the actual per-record rationale and current mamey/scoring.py; the illustrative baseline is not the final score formula. NAPAA is neutral and hglE-KS is informational, not class downgrades. No score or tier establishes compound identity, expression or biological activity.

For an illustrative subtotal, the current lanthipeptide keyword weight is 12 and the eligible diagnostic bonus is 25: `25 + 12 + 25 = 62` before other applicable adjustments. Do not use that subtotal as an expected final result or infer the final tier from it. Read the record's complete rationale and all axis scores: later guards, rescue context, bounds and tier handling can change the result.

## Bank 37 · What are lead classes A/B/C, and why doesn't class raise claim confidence?
A/B/C grade the *evidence* behind a lead — roughly how many independent, corroborating axes point at it — not how confident you may be about its product. That's the whole point of the rule "raising a lead's class never raises its claim confidence." Class is *strength of the case that this is worth chasing*; claim confidence is *what you can say it makes*, which stays capacity-level no matter how strong the case. A Class-A lead with three corroborating axes is still "capacity consistent with," not "produces." Keeping the two orthogonal stops the natural slide where a well-supported lead quietly gets talked about as a confirmed product.

Practically: class drives *triage* (chase the Class-A leads first), claim drives *language* (all of them get capacity-level prose). Conflating the two is the single most common way a genome-mining paper overreaches — a well-supported lead quietly described as a confirmed product — which is exactly why they're kept on separate axes.

## Bank 38 · What is the diagnostic floor / marker-aware scoring?
Marker-aware scoring reads diagnostic markers as well as class and similarity annotations. Under the configured scoring rules, corroborated diagnostics can raise priority and impose a tier floor. A nucleoside trigger, relevant TIGRFAM match and chitin context can support a class-level antifungal-capacity hypothesis even without a KCB anchor. The resulting score or tier is a triage judgment; it does not verify antifungal activity, expression or a named product. Bind each marker to the complete source locus before interpreting it.

AS-XXX's nikkomycin lead is the canonical case the floor exists for (Bank 86): KCB-dark + T43-NUC + NikJ + chitin context, floored to a real antifungal lead a similarity-only scorer would bury. The floor is, in effect, the rule that lets genuine novelty *survive* scoring instead of being penalized for having no known relative.

## Bank 39 · What is DAPR, and why is wiring DAPR scoring a "scoring boundary"?
DAPR is a compound-class framework (`DAPR_CLASS_FRAMEWORK`); currently some of its classes are *annotation-only* — recorded but not feeding the AB/AF score. The open decision is whether to *wire DAPR classes into scoring*. Why that's not a casual patch: it would change how every BGC scores, which is a **scoring boundary** — and crossing one means scores stop being comparable to anything cut before it. Every strain would need re-scoring on the new engine before any cross-strain claim held. So the v9.7.98 disclosure deliberately *surfaced* DAPR scoring as a decision rather than baking it, keeping the cut "no scoring boundary." Good example of the project knowing which changes are cosmetic and which silently break comparability.

The way it's handled is itself the lesson: rather than quietly wiring it (and silently bumping the engine), DAPR scoring is *surfaced as a decision* in a memo (kept as a record in `docs/history/retired_458/working/`), so crossing a scoring boundary is a deliberate choice you make, not something buried in a patch. Surfacing-not-baking is the general move for any change that touches comparability.

## Bank 40 · What is a scoring boundary?
Any engine change that alters the *numbers* a BGC gets — AB/AF, novelty, corrected count, tier gates — such that a score from before can't be directly compared to one from after. The deep reason it matters: your whole cross-strain story ("X has stronger antifungal capacity than Y") rests on every strain being scored by the *same ruler*. The moment the ruler changes — the v9.7.84 edge-penalty removal, or wiring DAPR — old and new scores are different units, and comparing them is quietly wrong. So the project tracks scoring boundaries explicitly and re-scores the cohort across one before making comparative claims. It's why "no scoring boundary" is a headline on every hygiene cut.

That's why every hygiene cut's disclosure carries an explicit "no scoring boundary" line — it's a promise that scores from this cut stay comparable to the last, so you can keep building cross-strain claims on one ruler. The line is small but load-bearing: it's the contract that the cohort numbers still mean the same thing.

## Bank 41 · Why must the cohort be re-scored before cross-strain claims?
Because scores from different engine versions are not comparable. The cohort was scored across *several* engine versions, and every scoring boundary between two runs — most consequentially the edge/full-contig penalty removal at 1.9.84→1.9.85 — breaks comparability (the User Manual §9.3 lists the boundaries). So one strain's AB76 from an older run and another's AB72 from a newer run are *not on the same scale*; ranking them compares different rulers. Any defensible cross-strain statement — "the strongest antifungal lead in the cohort" — first requires re-running every strain on one engine so scores are commensurable. That re-score is pure science work (not a cut); the v9.7.98 disclosure flagged it as the **highest-leverage publication blocker**.

The standing rule: *within*-strain ranking (which of this strain's BGCs is the strongest lead) is fine, because all its clusters were scored on one engine; *across*-strain ranking requires every strain to be re-scored on one engine first. That one rule keeps cohort claims defensible without freezing all analysis.

## Bank 42 · What are the evidence axes, and how do they combine into a verdict?
A lead isn't one number — it's assessed across several independent *evidence axes*, and the verdict is how they combine. The axes: structural/architectural capacity (is there a coherent assembly line?), KCB similarity (does it resemble a known producer?), novelty (is it KCB-dark?), diagnostic markers (do CCTT/resistance/TIGRFAM signals corroborate a class?), regulation (TFBS/bldA), completeness (edge status, RiPP precursor). Keeping them separate rather than blended is deliberate — they answer different questions and can *disagree* productively: a KCB-dark cluster scores low on similarity but high on novelty, and that tension is information. Lead-class (A/B/C) reflects how many axes independently agree; the claim stays capacity-level regardless. Verdict = the coherent reading across axes, with every axis's contribution legible.

The design bet is that *legible disagreement beats a smoothed average*: a single blended score would hide the KCB-dark-but-architecturally-real tension that's often the most interesting thing about a cluster. Keeping the axes separate keeps that tension visible to the reader instead of averaging it into a meaningless middle.

## Bank 43 · What is the WL tier / priority tiering?
WL = **watchlist** — the lowest, most honest tier in the priority ladder: a chemistry the system *recognizes* but hasn't curated enough to claim. The watchlist cassettes and markers (SMC-017/018/019, SMK-WATCH-001/002/003 — aryl-C-glycoside, corallorazine, azinomycin/genotoxin) are flagged TIER_3_CONTEXT_TAILORING / LOW with a standing instruction — "inventory as a candidate only; no strong claims" — and a wet-lab promotion route (LC-MS/MS, HMM/BLAST confirm). Above the watchlist sit the scored leads (the AB/AF tiers, floored-to-Medium, HIGH). The point of keeping WL as its own tier is to *retain* a recognized signal without letting it leak into a claim — a parking lot for "we've seen this, it's not nothing, but it's not evidence yet." WL interpretation is explicitly a Sapote (judgment-layer) job; the extraction layer does no WL scoring.

A watchlist entry isn't a dead end: each carries a wet-lab route (LC-MS/MS, HMM/BLAST confirm) and a curated-marker requirement, so "watchlist → scored lead" is a *defined promotion* once the evidence is built, not a permanent demotion. It's a holding pattern with an exit, not a graveyard.

## Bank 44 · What is the promiscuity cap, and what is it preventing?
A ceiling on how much any single BGC can contribute to a strain's class-capacity tally — `DEFAULT_CAP = 1.25` (the per-BGC contribution unit, "CNBU") per cluster, plus a fragment ceiling (P4: a large backbone on a sub-45 kb fragment gets its class-capacity capped). What it prevents: one giant, multi-class, or hybrid region inflating a strain's *apparent biosynthetic breadth*. Without it, a single sprawling NRPS–PKS–terpene hybrid could make a strain look like it has the capacity of three, skewing any "this strain is more biosynthetically diverse" comparison. The cap keeps the unit of accounting honest: a BGC is worth at most so much, however many things it gestures at. (CNBU is read here as the capped contribution unit, from the constant; confirm the exact acronym expansion in the scoring module rather than assume it.)

The claim it defends is the cross-strain *diversity* comparison specifically: without the cap, biosynthetic breadth (how many distinct classes a strain can make) would be hostage to one strain happening to carry a giant hybrid — an assembly accident, not a biological difference. The cap makes breadth a property of the strain, not of its contig luck.

## Bank 45 · How does the compound-class annotation layer pick a chemotype?
It reads a BGC's architecture and assigns a *chemotype* — currently ~16 chemotypes mapped against ~32 MIBiG reference clusters. It's deliberately architecture-driven and claim-safe: it calls the *class* the machinery is consistent with (a reducing PKS chemotype, an HSAF/PTM macrolactam, a glycopeptide-like cassette), not a compound. Of those chemotypes, only some carry a *scored consequence* — the ones tied to a diagnostic trigger or an AB/AF keyword move the score; the rest are annotation-only context. The call sits next to the contig in the card so the class always travels with its evidence. That split between "annotated" and "scored" chemotypes is exactly why wiring more of them into scoring is a boundary, not a tweak (Bank 39).

That annotated-but-unscored set is exactly where DAPR lives (Bank 39) — chemotypes recognized and recorded, deliberately held out of the score until someone decides to cross the boundary. The layer is the *inventory*; turning an annotation into a score is a separate, guarded decision, never automatic.

## Bank 46 · What does the current NAPAA rule permit?
The current registry records NAPAA as neutral, action none and lead_blocking false. The former Nosema hypothesis remains retired, but that does not exclude the class itself from comparative or ecological interpretation. Retain all product tokens and use only bound observations from the actual admitted cohort; no source count, habitat association, expression or activity is inferred from the label alone.

A comparison needs the measured cohort, denominator, strictness and assembly context. Prevalence alone does not authorize a permanent class downgrade. The genome-class saccharide-only display policy is separate from the wider genus/BiG-SCAPE family policy; neither should be guessed from an old prose exclusion list.

## Bank 47 · How should hglE-KS-PREV-001 be interpreted?
The current registry treats hglE-KS-PREV-001 as an informational note and explicitly states it is not a downgrade or lead-blocking rule. Historical prevalence counts describe their original sampled set, not a universal habitat distribution. Retain normal lead eligibility, the separate gene-level enediyne-artifact guard and the capacity-level claim ceiling; neither marker prevalence nor a missing/zero KCB result establishes a named product, new chemistry or activity.

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
Worth a correction here: in *this* pipeline a "marker" usually isn't a profile HMM. A Mamey/Sapote marker is a curated *detection rule* — a `Marker`/`Cassette` dataclass in `mamey_markers.py` / `sapote_markers.py` carrying an id, a tier (e.g. TIER_3_CONTEXT_TAILORING), a confidence, a target pattern (often a regex over antiSMASH's annotation text, like `r"corallorazine"`), and a wet-lab confirmation route (`hmm_blast_confirm`, LC-MS/MS). So the markers are a lightweight, auditable rule layer *on top of* antiSMASH's own HMM output — not a fresh HMM scan. Profile HMMs (the HMMER sense, Bank 66) are what produced the Pfam/TIGRFAM annotations the markers then read. (There's no `build_bgc_markers.py` in the tree; that name was question-bank shorthand. The registries are the `*_markers.py` files.)

The upside of markers being plain rules rather than opaque models is auditability — you can read a `Marker`'s regex and tier and *see* why it fired, which is exactly what a hallucination-conscious pipeline wants. The cost is recall (a regex misses paraphrases an HMM would catch), which is why the wet-lab `hmm_blast_confirm` route exists as the backstop.

## Bank 68 · What are Pfam / TIGRFAM / dbCAN accessions, and why are they never quoted from memory?
Pfam (PFxxxxx), TIGRFAM (TIGRxxxxx), and dbCAN/CAZy (GH/AA/CBM families) are curated databases of protein-family models, each entry with a stable accession — e.g. a GH18 chitinase domain, the NikJ TIGRFAM. The reason a specific accession is never recited from memory is the no-fabrication hard guard: an accession is exactly the kind of precise-looking token a language model will *confidently invent* (PF + five plausible digits), and a wrong accession in a methods paper is a citation pointing at the wrong family. So the rule: cite an accession only when it's verified against the live database (Pfam/TIGRFAM/dbCAN/CARD), never from recall. Same discipline as "verify DOIs from full text, not the abstract."

The failure mode is specific and real: a model asked for "the chitinase Pfam" will happily emit a plausible PFxxxxx that belongs to something else entirely, and nobody downstream re-checks a confident-looking accession. Treating accessions as verify-only is far cheaper than the erratum — it's the same calculus as flagging T43-NN rather than asserting it.

## Bank 69 · What is BLAST, and what does KnownClusterBlast actually compare?
BLAST (Basic Local Alignment Search Tool) finds regions of local similarity between sequences and scores them with an E-value (lower = less likely by chance). **KnownClusterBlast** is antiSMASH's application of that at the *cluster* level: it takes your BGC's genes and BLASTs them against the MIBiG database of experimentally characterized clusters, then reports which known clusters share the most genes and how well. That's the KCB hit — a similarity verdict ("your cluster shares N of M genes with the X producer cluster"), which the pipeline treats as the KCB anchor. Crucially it compares *gene content and order*, not the molecule — which is exactly why KCB is similarity-not-identity (Bank 50): shared genes suggest a related pathway, not the same product.

The number that matters in a KCB hit is the *fraction of genes shared and their identity*, not merely that a hit exists: a 3-of-30-genes hit and a 28-of-30 hit are both "hits" but mean wildly different things. That's why the anchor carries the gene-fraction, and why a thin hit doesn't license a confident class call.

## Bank 70 · What is "bounded" streaming, and what is the leaf budget?

Current bounded mode streams the main JSON walker and limits selected auxiliary string/MIBiG leaves. Its historical “record cap” variable is not a count of all biological records. When that auxiliary budget is reached, the code marks truncation and continues walking; it does not stop reading all later JSON or impose a wall-clock bound. Region-mapped RiQ scores have separate group/authority caps and incomplete/unassigned/held states.

A deterministic selection rule does not make the capped output equivalent to full loading or certify complete upstream search/schema coverage. Read each walk receipt’s `walk_complete`, auxiliary truncation, source-authority holds and mapped/unassigned RiQ counts along with requested/effective modes. Missing or held evidence is not a biological negative.

## Bank 71 · What is the Decimal-vs-float gotcha?

Streaming parsers can represent JSON numbers as Decimal, which default `json.dumps` cannot serialize. The current `_iter_records` streaming call uses `use_float=True` to align record numeric types with its `json.loads` fallback. The bounded main walker is a different path: it explicitly accepts numeric Decimal RiQ values and converts admitted scores to float.

This is a representation/serialization contract, not proof that every parser call uses the flag or every selective/capped output matches a whole-document parse byte-for-byte. Preserve parser/mode and source scope; use the actual focused parity/serialization evidence rather than promoting one flag into a package-wide correctness guarantee.

## Bank 72 · What is a regression test, and what makes a "negative control" test?
A **regression test** pins a known-good output so a future change can't silently break it: capture "on input X the engine produced Y," and the test fails the day Y changes unexpectedly. A **negative control** is the inverse — it asserts the engine *correctly does nothing*: feed an input that *should not* trigger a signal and assert the signal stays off. The P-11 set is exactly this: seven non-actinomycete genomes that should yield *no* bldA T4 call, used to catch the spurious-T4 defect. Negative controls are the under-appreciated half — most scorer bugs aren't "missed a real hit," they're "fired on something it shouldn't have," and only a negative control catches those.

The project leans on negative controls deliberately because its whole value proposition is *not over-claiming*: a generous scorer is worse than a stingy one, so the tests that matter most are the ones asserting "stayed quiet when it should have." P-11, the APH veto, and the mobile-element demotion are all really negative-control stories.

## Bank 73 · What is an xfail, and why is ISID-XXX kept as an xfail tripwire?
An `xfail` records an expected test failure; an unexpected pass is an XPASS whose effect depends on the test's strictness/configuration. Read the actual marker and selected test result rather than assuming that every XPASS fails a suite or is always shown.

The ISID example is now history. Current `tests/test_mibig_no_redaction_corruption.py` uses assertions for the restored ISID311 text and absence of its redaction placeholder. It can skip when MIBiG or the optional replacement asset is unavailable; `MAMEY_REQUIRE_OPTIONAL_ASSETS=1` makes the optional-asset assertion required. This is not a live network-status test or a current xfail tripwire. Retain the actual executed/skipped result and fixture identity before citing it.

## Bank 76 · What is a GBK file, and what is the _gbk_shim for?
A **GBK** (GenBank) file stores annotated sequence, including headers, features, coordinates, qualifiers and sequence. antiSMASH emits region GBKs with its annotations. The bundled `_gbk_shim` provides a minimal GenBank reader for selected paths. In the core `read_genbank_records` path, the lazy Biopython import is tried first: available `Bio.SeqIO` is used, and the shim is the fallback when that import is unavailable. Other consumers may select the shim directly.

A small fallback improves portability for its supported record shape; it is not a universal replacement for Biopython or proof of complete GenBank-format coverage. Preserve the actual parser, admission/refusal state and source scope when interpreting output. No historical installation or methods-paper portability claim is independently revalidated here.

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
Both are RiPP subclasses with distinctive topologies. **Lanthipeptides** carry lanthionine bridges — thioether cross-links from dehydration + cyclization — giving compact, protease-resistant scaffolds (nisin is the famous one). **Lasso peptides** are threaded knots: the tail is pulled through a macrolactam ring and locked, a genuinely lasso-shaped, remarkably stable fold. They score toward the HIGH/antibacterial end (T43-LAN, T43-LASSO) because these classes are enriched for real, often anti-Gram-positive bioactivity and their machinery is diagnostic — with the precursor *and* the maturases visible, the class call is unusually well-supported. (The claim stays capacity-level. The current short RiPP fragment rule uses product labels, Edge/Full-contig geometry and span, not a direct precursor-absence check; its bottom tier can be Low.)

The extreme stability isn't incidental: the thioether bridges and the threaded knot make these peptides resistant to proteases and heat, which is both why they survive as defensive molecules in a competitive microbial environment and why they're attractive drug scaffolds. The topology *is* the bioactivity story, not just a structural curiosity.

## Bank 84 · What is a halogenase, and why does halogenation matter?
A **halogenase** installs a halogen (usually Cl or Br) onto a scaffold — flavin-dependent ones on aromatic rings, others on aliphatic carbons. Why it matters: halogenation is a hallmark of *dedicated secondary metabolism* and frequently *tunes bioactivity* — a single chlorine can change potency, selectivity, or target binding (vancomycin, chlortetracycline, pyrrolnitrin all depend on it). So a halogenase flags "this strain decorates its products like real, optimized natural products do." But the project treats it as a *tailoring* signal, not a class definer — T43-HAL/XHAL are deliberately excluded from the tier floor (Bank 24), because halogenation embellishes a product, it doesn't tell you what class the product is.

As a prospecting tell, a halogenase flags "someone optimized this": organisms don't usually carry the machinery to install a halogen unless the decorated product is doing something worth the metabolic cost. So even though it's excluded from the class floor (Bank 24), it's a useful *interest* signal pointing at a cluster worth a closer look.

## Bank 85 · What are HSAF/PTM, and why do they recur across the bee strains?
HSAF (Heat-Stable Antifungal Factor) and the broader **PTM** (polycyclic tetramate macrolactam) family are a hybrid PKS–NRPS antifungal chemotype — dihydromaltophilin-type molecules that disrupt fungal membranes/sphingolipids. They recur across the bee cohort as a *cross-genus, within-habitat* signal: the five-strain HSAF/PTM recurrence spans Saccharopolyspora, Nocardia, Streptomyces, and Micromonospora — four genera, one habitat. That's the project's principal cross-genus finding precisely *because* it's mechanism-level and habitat-linked: different bee-associated genera independently carry the same antifungal machinery, the kind of convergence a defensive-symbiosis story predicts. (T43-PTM is one of the two antifungal diagnostic triggers, Bank 24/36.)

Structurally they're tetramic-acid-bearing macrolactams from a single hybrid PKS-NRPS, and mechanistically they hit fungal sphingolipid biosynthesis (ceramide synthase) — a different target from the polyenes (membrane ergosterol) or the nucleosides (chitin synthase). That mechanistic distinctness is why HSAF/PTM, polyene, and nucleoside leads are treated as *separate* antifungal capacities, not interchangeable ones.

## Bank 86 · What is nikkomycin, and why is it the Candida lead in AS-XXX?
Nikkomycin/polyoxin-style annotations are class-level comparator hypotheses. A nucleoside trigger, relevant TIGRFAM match and chitin context can support an antifungal-capacity hypothesis and the configured diagnostic scoring floor; they cannot establish that an isolate produces nikkomycin or that a locus has antifungal activity. Keep compound identity, expression and biological activity unconfirmed without their corresponding experimental evidence. Do not select an incompletely identified example locus.

Chitin-synthase inhibition is an attractive antifungal mechanism precisely because *humans have no chitin* — the target is fungal-specific, so the selectivity ceiling is high. That's part of why a KCB-dark nucleoside lead with the T43-NUC + NikJ signature is worth flooring up rather than burying: the mechanism class is therapeutically interesting, not merely novel.

## Bank 88 · What are GH18/GH19/GH20 chitinases, and how do they relate to antifungal ecology?

These enzyme-family labels are distinct biological categories, but the old statement that current CGAD is GH18-only is false. `CHITINASE_PATTERNS` explicitly includes GH18 and GH19 text, AA10/LPMO wording, a broad CBM/chitin-binding bucket and GlcNAc-related terms. There is no separately named GH20 bucket in that inspected dictionary. Dictionary presence is not validated family-specific recall or a complete enzyme census: generic words and partial source scope can overcall or miss functions.

Bind each observed match to its actual source, scanned scope and complete locus identity where applicable. Biological substrate specificity, family interpretation, ecological function and any proposed marker enhancement need their own source/scientific review. No habitat, activity or quantified Streptomyces-wide undercount follows from this dictionary alone.

## Bank 89 · What is resistance-gene-directed genome mining?
A prospecting strategy that flips the usual logic. Instead of "what does this cluster make?", you ask "what is this strain *defended against*?" — and let the resistance gene point you to the product. The sharpest version is **target duplication**: if a strain carries a *second, modified copy* of an essential gene (a duplicate ribosomal protein, a resistant gyrase), that's a strong tell it makes something hitting that target and needs a protected backup. So you mine for the duplicated-target signature and follow it to the nearby BGC. It's powerful because it's *function-first* and class-agnostic — it can surface a novel compound whose cluster looks unremarkable. It's on the open markers list (today's resistance scan does co-located self-resistance, Bank 28; duplicated-target is the upgrade).

The approach has a marquee proof-of-concept: platensimycin/platencin and related fatty-acid-synthesis inhibitors were surfaced by mining for a duplicated FabB/F target — exactly the "second, resistant copy of an essential gene" tell. It's not a hypothetical strategy; it has produced real compounds, which is why duplicated-target is the upgrade the resistance scan is reaching for (Bank 28).

## Bank 90 · What is a self-resistance gene, and how does it hint at a product's target?
A producer of a bioactive compound faces an obvious problem: its own product would kill it. The solution is a **self-resistance gene** — usually carried right in the BGC — that makes the strain immune to what it makes (an Erm methylase modifying its own ribosome, a resistant target variant, an efflux pump, an inactivating enzyme switched off at the right moment). For genome mining that gene is a gift: a *functional fingerprint of the product's mechanism*. A self-resistant ribosomal-modification gene says "this cluster's product targets the ribosome"; a VanHAX cassette says "cell-wall agent." That's the inference RES_CLASS_CONCORDANCE (Bank 33) formalizes and resistance-gene-directed mining (Bank 89) weaponizes — with the HGT guard (Bank 28) to make sure it's really *self*-resistance, not an imported passenger.

The limit to keep honest: not every producer co-localizes its resistance, and not every nearby resistance gene is self-resistance (the HGT-passenger problem, Bank 28). So a self-resistance read is a *strong hypothesis* about target, not a proof — which is exactly why it feeds capacity-level claims and concordance checks rather than a confident mechanism assertion.

---

*Add the next question below.*

---

*Sapote–Mamey Concepts Q&A · current to bundle v9.7.459 / engine Mamey 1.9.177 A running document — concepts are version-stable; inline version references (e.g. "shipped in v9.7.91", "v9.7.97 CODE tier") are historical record, not a currency claim. Companion to `../GLOSSARY.md` (definitions) and `03_Technical_Manual_Encyclopedia.html` (deep internals); Q&A is the conversational "why does it work this way" layer.*
