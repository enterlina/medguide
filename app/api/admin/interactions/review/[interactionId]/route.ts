import { forward, reviewBackendFetch } from "@/lib/interaction-review-api";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ interactionId: string }> },
) {
  const { interactionId } = await params;
  return forward(
    await reviewBackendFetch(`/api/interactions/review/${encodeURIComponent(interactionId)}`),
  );
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ interactionId: string }> },
) {
  const { interactionId } = await params;
  const body = await request.text();
  return forward(
    await reviewBackendFetch(`/api/interactions/review/${encodeURIComponent(interactionId)}`, {
      method: "POST",
      body,
    }),
  );
}
