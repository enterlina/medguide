import { NextResponse } from "next/server";
import { checkInteractions } from "@/lib/public-interactions";

export async function POST(request: Request) {
  try {
    const payload = await request.json() as { medications?: Array<{ name?: string }> };
    const names = (payload.medications ?? []).map((item) => item.name?.trim() ?? "").filter(Boolean);
    if (!names.length || names.length > 20) {
      return NextResponse.json({ detail: "Add between 1 and 20 items" }, { status: 422 });
    }
    return NextResponse.json(checkInteractions(names));
  } catch {
    return NextResponse.json({ detail: "Invalid interaction request" }, { status: 400 });
  }
}
