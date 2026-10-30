import { NextResponse } from "next/server";
import {
  forward,
  REVIEW_COOKIE,
  reviewBackendFetch,
} from "@/lib/interaction-review-api";

export async function GET() {
  return forward(await reviewBackendFetch("/api/interactions/review/session"));
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as { token?: unknown } | null;
  const token = typeof body?.token === "string" ? body.token.trim() : "";
  if (!token || token.length > 500) {
    return NextResponse.json({ detail: "Valid access token required" }, { status: 422 });
  }
  const verified = await reviewBackendFetch(
    "/api/interactions/review/session",
    {},
    token,
  );
  if (!verified.ok) return forward(verified);
  const payload = await verified.json();
  const response = NextResponse.json(payload);
  response.cookies.set(REVIEW_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
  return response;
}

export async function DELETE() {
  const response = NextResponse.json({ status: "signed_out" });
  response.cookies.delete(REVIEW_COOKIE);
  return response;
}
