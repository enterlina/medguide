# MedGuide — AI-Powered Medication Intelligence

**Nebius × NVIDIA Global AI Hackathon 2026** · Proposed track: **Best Apps and Agents**

> **Status: In development (hackathon MVP).** This is a research/demo prototype, not a medical device or a substitute for clinician or pharmacist advice. Features described below are planned unless explicitly marked implemented.

## Overview

MedGuide helps people understand their **complete medication regimen** instead of reviewing medications one by one. The MVP demonstrates an end-to-end workflow: enter several medications, normalize their names, retrieve documented potential interactions from reliable medical sources, and present understandable explanations with traceable references and uncertainty.

**Core differentiator:** Contextual regimen analysis + evidence-backed retrieval + explainable AI in one connected experience. The LLM must never invent drug interactions or independently recommend changing treatment.

## Existing work versus hackathon implementation

MedGuide began as a product concept with prior UX/design work and an earlier prototype. This repository tracks the **hackathon-specific implementation**. Previous work and new development will be identified separately.

| Component | Current status |
| --- | --- |
| Product vision and initial UX workflows | Existing prior work; documentation pending |
| Figma designs | Existing prior work; link to be added |
| Frontend for this hackathon | Planned |
| Medication normalization | Planned |
| Medical sources and RAG | Planned |
| AI model and Nebius integration | Planned |
| API and deployed end-to-end demo | Planned |

Update this table only after implementation and testing.

## MVP scope

1. **Add medications:** Enter multiple medication names and optional details.
2. **Confirm matches:** Review normalized names; resolve ambiguous medications.
3. **Analyze regimen:** Search licensed/accessible reliable references for documented interactions.
4. **View results:** Present source-backed findings, uncertainty, limitations, and questions to discuss with a professional.

**Out of scope:** medication reminders, longitudinal symptom tracking, autonomous dose optimization, diagnosis, and treatment decisions.

## Architecture (proposed)

```text
Frontend — Developer 1 (proposed workstream)
  Medication entry → Review → Results / references
                    ↕
           REST / OpenAPI contract
                    ↕
Backend — Developer 2 (proposed workstream; Python/FastAPI)
  Validation → Drug-name normalization
  Evidence retrieval → RAG → Structured explanations
                    ↕
       Medical reference data + vector index
                    ↕
     NVIDIA open-source model on Nebius
```

The exact models, embedding strategy, vector store, data sources, and Nebius configuration are still being evaluated. See [Technical plan](docs/TECHNICAL_PLAN.md).

## Proposed development workstreams

The roles below organize **planned work**, not team membership, authorship, contributions, or commitments by any individual. Both workstreams may be completed by a single developer. No contributor is assigned by this document.

| Workstream | Planned scope | Deliverable |
| --- | --- | --- |
| **Developer 1 — Product & Frontend** | Product priorities, user journeys, UX/UI design, Figma, frontend implementation | Usable medication entry, review and results interface |
| **Developer 2 — AI & Backend** | Model evaluation, Nebius/NVIDIA integration, drug-name normalization, retrieval/RAG, analysis API and backend deployment | Tested evidence pipeline and documented API |
| **Integration & QA** | Connect frontend and backend, evaluate safety and edge cases, prepare demo | End-to-end MVP and submission materials |

Workstream labels describe technical responsibilities only. Actual contributions should be established by code, design files, commits, pull requests, and other records of completed work.

## Development schedule

**Planning targets, as of October 18, 2026.** Dates are not completion claims.

| Date | Developer 1 — product/frontend | Developer 2 — AI/backend | Integration milestone |
| --- | --- | --- | --- |
| **Oct 18–20** | Finalize screens and MVP workflow | Propose NVIDIA model, data sources, Nebius architecture, API | Agree on response contract |
| **Oct 21–23** | Build entry/results UI using mock JSON | Implement normalization, retrieval and `/api/analyze` | Representative analysis response |
| **Oct 24–26** | Connect live API, polish error/uncertainty states | Integrate Nebius inference, citations, safety tests | End-to-end demo |
| **Oct 27–28** | Polish UX, demo and screenshots | Deployment, reproducibility, evaluation | External smoke test |
| **Oct 29** | Record video and finalize submission | Verify setup and code | Submission package ready |
| **Oct 30** | Submit before official deadline (verify timezone in rules) | Final technical check | Submission confirmed |

## Collaboration and Git workflow

- `main` — stable, reviewed integration.
- `feature/frontend` — proposed frontend workstream (primarily `frontend/`).
- `feature/ai-backend` — proposed AI/backend workstream (primarily `backend/`).
- `docs/` — API and technical specifications; coordinate changes as needed.
- Define the response schema before integration. Frontend development may use mock responses until the backend is ready.
- Use pull requests to merge into `main`. Never commit secrets, tokens, or patient data.

## Design, demo and submission links

- **Figma:** _Link pending_
- **Live demo:** _Pending deployment_
- **YouTube demo:** _Pending_
- **Devpost submission:** _Pending_

## Project structure

```text
medguide/
├── frontend/                 # UI workstream
├── backend/                  # API, retrieval and AI workstream
├── docs/
│   ├── API_CONTRACT.md
│   ├── TECHNICAL_PLAN.md
│   └── HACKATHON_CHECKLIST.md
├── assets/
├── .gitignore
├── LICENSE
└── README.md
```

## Local setup

**Not yet runnable.** Backend/frontend dependencies, environment variables, installation steps and real execution commands will be documented and verified after the first working implementation. No API credentials will be stored in this repository.

## Medical safety principles

- Use synthetic demo scenarios; do not publish real patient information.
- Check source licenses and usage terms.
- Keep retrieved evidence separate from generated explanations.
- Surface unknown/ambiguous matches and missing or conflicting evidence.
- Never present “no interaction found” as proof of safety.
- Do not output autonomous dosage changes or definitive medical advice.
- Maintain representative evaluation cases and known limitations.

## Hackathon submission

Track requirements in [Hackathon checklist](docs/HACKATHON_CHECKLIST.md) and verify all details against [official hackathon rules](https://nebiusglobalaihackathon.devpost.com/rules). Planned demonstration: a functioning app using eligible Nebius infrastructure and an NVIDIA open-source model, documented source code, and a short walkthrough.

## License

MIT — see [LICENSE](LICENSE). Third-party datasets, libraries and model weights retain their separate licenses.
