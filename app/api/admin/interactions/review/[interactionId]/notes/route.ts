import { forward, reviewBackendFetch } from "@/lib/interaction-review-api";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ interactionId: string }> },
) {
  const { interactionId } = await params;
  const body = await request.text();
  return forward(
    await reviewBackendFetch(
      `/api/interactions/review/${encodeURIComponent(interactionId)}/notes`,
      { method: "POST", body },
    ),
  );
}
