import { NextResponse } from "next/server";
import { interactionCatalog } from "@/lib/public-interactions";

export async function GET() {
  return NextResponse.json(interactionCatalog());
}
