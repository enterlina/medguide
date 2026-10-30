import { forward, reviewBackendFetch } from "@/lib/interaction-review-api";

export async function GET() {
  return forward(await reviewBackendFetch("/api/interactions/review/summary"));
}
