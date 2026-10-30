import { NextResponse } from "next/server";
import {
  keepAllUnreviewedAsCandidates,
  loadEvidenceReviewQueue,
  saveEvidenceReview,
  type EntityMatch,
  type OutcomeMatch,
  type ReviewDecision,
} from "@/lib/evidence-review-store";

const entityMatches = new Set<EntityMatch>(["exact", "related_form", "different", "unclear"]);
const outcomeMatches = new Set<OutcomeMatch>(["direct", "indirect", "not_measured", "unclear"]);
const decisions = new Set<ReviewDecision>(["include", "include_as_indirect", "exclude", "needs_review"]);

function locallyEnabled() {
  return process.env.MEDGUIDE_REVIEW_DEV_BYPASS === "true";
}

export async function GET() {
  if (!locallyEnabled()) return NextResponse.json({ detail: "Local review is disabled" }, { status: 403 });
  return NextResponse.json(await loadEvidenceReviewQueue());
}

export async function POST(request: Request) {
  if (!locallyEnabled()) return NextResponse.json({ detail: "Local review is disabled" }, { status: 403 });
  const body = await request.json();
  if (body.action === "keep_all_candidates") {
    return NextResponse.json(await keepAllUnreviewedAsCandidates());
  }
  if (
    typeof body.entityId !== "string" ||
    typeof body.pmid !== "string" ||
    !entityMatches.has(body.entityMatch) ||
    !outcomeMatches.has(body.outcomeMatch) ||
    !decisions.has(body.decision) ||
    typeof body.comment !== "string"
  ) {
    return NextResponse.json({ detail: "Invalid review payload" }, { status: 422 });
  }
  return NextResponse.json(await saveEvidenceReview(body));
}
