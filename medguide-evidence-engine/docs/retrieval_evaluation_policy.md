# Retrieval relevance and evidence applicability

MedGuide evaluates discovery separately from clinical applicability. First-stage retrieval must not
exclude a publication because its formulation, population, dose or design differs from the question.

## Topic relevance (human gold for retrieval)

| Grade | Definition |
| ---: | --- |
| 0 | Irrelevant to the question topic. |
| 1 | Related ingredient or topic, but not the requested outcome. |
| 2 | Requested ingredient or ingredient family in relation to the requested outcome. |
| 3 | Directly addresses the requested ingredient and outcome. |

`Topic Recall@k` treats grades 1–3 as relevant and divides retrieved judged-relevant documents by
all judged-relevant documents for the query. `Topic nDCG@10` uses the 0–3 grades as gains.
`Relevant Evidence Hit@k` is one when at least one grade 2–3 document occurs in the top k.
Incomplete pooling must be reported; an unreviewed document is never interpreted as grade 0.

## Evidence applicability (post-retrieval only)

Applicability stores ingredient formulation, population, dose, outcome, study design, study quality,
evidence direction and citation support independently. `unknown`, `not_reported`, `different` and
`partial` are descriptive states, not first-stage exclusion rules.

`PICO Match@10`, `Strong Evidence Recall@20`, contradictory-evidence recall, citation-support
accuracy and evidence coverage are downstream diagnostics. They must not be mixed into Topic Recall
or used to hide thematically relevant studies.

No unverified medical gold labels are generated automatically. Human-reviewed annotations require a
reviewer identity and an explicit topic-relevance grade.
