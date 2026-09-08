# Plain-English authoring guidance — distilled from the May-27 layperson prose

*Source: AS-XXX Laypersons Guide + AS-XXX layperson section (2026-05-26/27). These read well; the goal is to
port their readability into the current `guide` / `compile-report` layperson slots **without** porting their
pre-gate overclaiming. Every "makes / produces / kills" below is rewritten to capacity language.*

## 1. The structural arc (use as the layperson section skeleton)

The May-27 guides follow one reliable order. It works because it answers the reader's questions in the order
they arise:

1. **Title + one-line subtitle** — e.g. "A plain-English introduction to the natural products of a bumblebee
   bacterium." One clause, no jargon.
2. **Audience line** — state who it's for ("intended for collaborators, funding bodies, and anyone who wants
   to understand what this bacterium is capable of"). Sets the register.
3. **"What is <strain>?"** — genus, the actinomycete lineage ("the same family that gave us over half of all
   antibiotics in use"), where it was isolated, and the extract-level activity — framed as *capacity/observed
   activity*, not per-BGC phenotype.
4. **"What did the genome analysis find?"** — antiSMASH found N BGCs; define BGC once, with an analogy;
   flag assembly completeness here.
5. **"The N most important findings"** — a numbered lead-with-the-so-what list (see §3).
6. **Per-BGC plain-language table** — one row per BGC, priority marker, class, one plain sentence.
7. **Ecological synthesis** — tie the capacity profile to the niche.

## 2. The analogy library (reusable, already claim-safe)

These are the specific analogies that carried the May-27 prose. They're safe to reuse because they describe
*structure and capacity*, not product identity:

- **BGC = "factory blueprint" or "recipe"** — the workhorse analogy. Pair with: reading a recipe is not the
  same as having cooked the dish (capacity ≠ product).
- **Incomplete assembly = "a book with some pages torn out"** (short-read) vs "the whole book" (finished
  genome). For this erythraea run the honest inverse applies: finished genome = complete recipes.
- **"N complete blueprints is an unusually rich chemical inventory for a single bacterium"** — gives the
  reader a sense of scale.
- **Siderophore = "iron-grabbing molecule"; the cluster's regulators = "an emergency response kit."**
- **Mechanism one-liners**: polyether ionophore "works by punching holes in bacterial membranes"; modular
  PKS = "a multi-station assembly line that builds a carbon backbone one block at a time."
- **Concrete comparators with a number**: name the nearest known compound, its mechanism, and one number
  (e.g. database-similarity score, or "the reference database of 2,500+ natural products").

## 3. Lead with the "so what" (the Top-5 move)

Each of the five findings in AS-XXX follows the same micro-structure, which is worth encoding:

> **<one-line headline> (BGC N).** <what class of chemistry, in plain words> · <nearest known comparator +
> one-line mechanism + why it matters> · <honest caveat: incompleteness / needs isolation>.

Rewritten claim-safe, the erythraea BGC006 headline becomes: *"A known-antibiotic benchmark (BGC006). This
cluster's gene content sits nearest the erythromycin assembly line by protein similarity — a useful
confirmation that the analysis recovers a chemistry we already understand. Capacity consistent with a
macrolide of that class; identity still requires isolation."* Note: lead with the interest, end with the
caveat — never bury the caveat, never drop it.

## 4. Caveat discipline (inline, per finding — not a footnote)

The May-27 prose flags limits **at the point of each claim**, which is why it reads as honest rather than
hedged:

- Per-finding incompleteness: "…but the cluster is partially incomplete in the current assembly and needs
  confirmation by long-read sequencing."
- Priority markers carry the caveat visually: ★★★/★★/★ for discovery priority, ■ for assembly-incomplete.
- One global claim-safety line up front ("everything here describes capacity, not proof; the computer
  predicts recipes, it does not cook them").

## 5. The claim-safety delta (what NOT to port)

The May-27 guides predate the current gates and use production verbs freely. Port the structure and
analogies; rewrite the verbs:

| May-27 wording (do not reuse) | Current claim-safe wording |
|---|---|
| "BGC 25 encodes the machinery to **make** X" | "capacity consistent with X" |
| "BGC 35 **most closely matches** gargantulide… **kills** Candida" | "nearest MIBiG neighbour by protein similarity is gargantulide; capacity consistent with that antifungal class" |
| "This bacterium **makes** an iron-grabber" | "carries machinery with capacity consistent with a siderophore" |
| per-BGC activity ("explains AS-XXX's anti-Candida activity") | activity stays **extract-level**; not pinned to a BGC without fractionation |
| "KCB score 25,090 → it **is** maklamicin-class" | KCB is **similarity, not identity**; "nearest neighbour," "capacity consistent with" |

## 6. Concrete edit to the `guide` skeleton prompts

The current Part-1 LAY prompt is terse ("identity, why-care, factory analogy, what-makes-it-special, honest
caveats"). Encode the above by expanding the prompt to name the arc (§1), require the factory/recipe analogy
+ the "reading a recipe isn't cooking it" caveat pairing (§2), require one nearest-comparator-with-number per
top lead (§3), and require the capacity-verb table (§5) as a linter reference. The claim-safety linter already
catches production verbs; this guidance is the *positive* target it doesn't supply.
