# MedGuide — Devpost submission copy

**Tagline:** Understand what you take, what may interact, and what the research actually says.

**Live demo:** https://medguide-orcin.vercel.app/evidence-lens  
**Source code:** https://github.com/enterlina/medguide

## Short description

MedGuide is a source-linked research prototype that helps people explore medication, supplement,
food, and drink combinations and inspect the studies behind them. It combines official FDA,
DailyMed, and NIH guidance with PubMed evidence, hybrid retrieval, and cited synthesis using NVIDIA
Nemotron 3 Nano through Nebius Token Factory. Unknown or unreviewed evidence is never presented as
proof of safety.

## Inspiration

People often combine prescriptions, over-the-counter medicines, vitamins, supplements, food, and
drinks. The information needed to understand those combinations is scattered across regulatory
labels and scientific papers, and it is usually written for specialists.

MedGuide brings two common questions into one source-linked experience:

1. **Can I take these together?**
2. **What do studies say about this medicine or supplement?**

The goal is not to replace a clinician. It is to help people explore technical information in
plain language and verify it against the original source.

## What it does

MedGuide has two workflows.

### Taking & Combining

Users add medicines, supplements, food, or drinks. MedGuide displays available interaction,
timing, administration, and warning information from FDA, DailyMed, and NIH sources. Each finding
links back to its source. Missing data remains **unknown**—it is never presented as proof that a
combination is safe.

### What Studies Say

Users search for a medicine, vitamin, or supplement and inspect a structured table of relevant
publications. Available fields include study design, year, participants, results, research context,
and PubMed links. The interface separates direct from related evidence and does not turn a study
registration or an AI-screened candidate into a clinical conclusion.

MedGuide is an evidence-navigation research prototype, not a prescribing or diagnostic tool.

## How we built it

- **Product:** Next.js 16, React 19, TypeScript, and a responsive source-first interface.
- **Backend:** FastAPI, Pydantic, and a SQLite repository layer.
- **Official sources:** DailyMed SPL, openFDA labels, NIH ODS, and RxNorm normalization.
- **Research sources:** PubMed/PMC and ClinicalTrials.gov.
- **Retrieval:** BM25 and multilingual E5 are combined with Reciprocal Rank Fusion (RRF).
- **Evidence model:** source passages, extracted interpretations, and human-review status are stored
  separately so provenance is not confused with clinical approval.
- **Hackathon AI:** NVIDIA Nemotron 3 Nano (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`) runs through
  Nebius Token Factory for cited research synthesis. The adapter fails closed when credentials or
  model output are unavailable and does not silently substitute another provider.

The pipeline follows:

`source adapters → normalization → typed extraction → retrieval → cited synthesis → validation`

## Challenges we ran into

### Provenance is not clinical correctness

Finding an exact sentence in an official label proves where text came from, but it does not prove
that the entities, severity, interpretation, or recommendation are correct. We therefore keep
source verification and clinical review as separate states.

### Missing evidence can create false reassurance

“No warning found” is not the same as “safe.” A 56-case curated safety audit exposed unresolved
coverage and missed-interaction cases. We report those limitations instead of hiding them behind a
green result.

### Biomedical retrieval needs both recall and restraint

Strict filtering can miss useful related studies, while broad search can surface irrelevant
papers. MedGuide retrieves broadly, ranks by topic, and presents applicability separately.

### Plain language must preserve meaning

FDA labels and abstracts contain important detail but are difficult to scan. We designed compact
summaries while retaining expandable source text and direct links.

## Accomplishments that we're proud of

- Built and deployed both user journeys in one working application.
- Created a reproducible corpus pipeline across regulatory and research sources.
- Stored **7,865 interaction-rule candidates** with explicit review states.
- Deterministically matched **7,864 of 7,865** extracted passages to stored source sections. This is
  a provenance result, not a claim of clinical correctness.
- Evaluated retrieval on all **323 NFCorpus test queries**. RRF reached nDCG@10 **0.3461**
  (95% bootstrap CI **0.3113–0.3813**) and outperformed BM25; its advantage over Dense E5 was not
  statistically distinguishable.
- Ran a clearly labeled **200-question restricted-corpus BioASQ pilot**, rather than presenting it
  as the official full-PubMed benchmark.
- Added an immutable audit trail and a role-aware human-review workflow.
- Completed a real Nebius Token Factory request with NVIDIA Nemotron and retained a sanitized
  runtime trace.

We are especially proud that the evaluation reports unfavorable results too: the current safety
audit identifies interaction coverage as a release blocker, and the project does not claim to be
clinically validated.

## What we learned

Healthcare AI is not mainly about producing a fluent answer. It is about preserving provenance,
separating fact from interpretation, communicating uncertainty, and testing the cases where a
missing result could mislead someone.

We also learned that hybrid retrieval is not automatically superior. In our NFCorpus experiment,
RRF clearly improved on BM25, but its measured advantage over Dense E5 was inconclusive, and the
tested reranker made results worse. Evaluation changed the design rather than merely decorating it.

## What's next for MedGuide

1. Fix the missed must-detect interaction cases found by the safety audit.
2. Expand and deduplicate official-label and supplement coverage.
3. Have clinical reviewers validate a stratified rule sample and measure agreement.
4. Build MedGuide-specific relevance judgments and citation-support evaluation.
5. Improve plain-language summaries without hiding the exact source passage.
6. Add continuous evidence updates while keeping AI-screened, source-verified, and human-reviewed
   evidence visibly separate.

The long-term goal is a trustworthy bridge between everyday medication questions and verifiable
scientific evidence.

## Built with

Next.js · React · TypeScript · FastAPI · Python · SQLite · BM25 · multilingual E5 · RRF · Nebius
Token Factory · NVIDIA Nemotron 3 Nano · DailyMed · openFDA · NIH ODS · RxNorm · PubMed · PMC ·
ClinicalTrials.gov
