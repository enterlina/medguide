import { forward, reviewBackendFetch } from "@/lib/interaction-review-api";

export async function GET(request: Request) {
  const query = new URL(request.url).search;
  return forward(await reviewBackendFetch(`/api/interactions/review${query}`));
}
