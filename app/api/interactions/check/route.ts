import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = await request.text();
  const base = process.env.MEDGUIDE_EVIDENCE_API_URL ?? "http://127.0.0.1:8000";
  try {
    const response = await fetch(`${base.replace(/\/$/, "")}/api/interactions/check`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body,
    });
    return new Response(await response.text(), {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json({ detail: "Interaction service is unavailable" }, { status: 503 });
  }
}
