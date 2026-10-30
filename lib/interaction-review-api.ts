import "server-only";

import { cookies } from "next/headers";

export const REVIEW_COOKIE = "medguide_review_session";

function backendUrl(path: string) {
  const base = process.env.MEDGUIDE_EVIDENCE_API_URL ?? "http://127.0.0.1:8000";
  return `${base.replace(/\/$/, "")}${path}`;
}

export async function reviewerToken() {
  return (await cookies()).get(REVIEW_COOKIE)?.value ?? null;
}

export async function reviewBackendFetch(
  path: string,
  init: RequestInit = {},
  explicitToken?: string,
) {
  const token = explicitToken ?? (await reviewerToken());
  const devBypass =
    process.env.NODE_ENV !== "production" &&
    process.env.MEDGUIDE_REVIEW_DEV_BYPASS === "true";
  if (!token && !devBypass) {
    return Response.json({ detail: "Reviewer session required" }, { status: 401 });
  }
  try {
    return await fetch(backendUrl(path), {
      ...init,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  } catch {
    return Response.json(
      { detail: "Interaction review service is unavailable" },
      { status: 503 },
    );
  }
}

export async function forward(response: Response) {
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
  });
}
