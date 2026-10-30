import { NextResponse } from "next/server";

const BACKEND_URL = process.env.MEDGUIDE_API_URL ?? "http://127.0.0.1:8000";

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/interactions/catalog`, { cache: "no-store" });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch {
    return NextResponse.json({ ingredients: [], products: [] }, { status: 503 });
  }
}
