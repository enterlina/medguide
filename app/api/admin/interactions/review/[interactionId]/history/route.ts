import { forward, reviewBackendFetch } from "@/lib/interaction-review-api";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ interactionId: string }> },
) {
  const { interactionId } = await params;
  return forward(
    await reviewBackendFetch(
      `/api/interactions/review/${encodeURIComponent(interactionId)}/history`,
    ),
  );
}
