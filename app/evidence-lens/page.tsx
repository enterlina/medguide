import type { Metadata } from "next";
import { EvidenceLens } from "@/components/evidence-lens";

export const metadata: Metadata = {
  title: "Evidence Lens — MedGuide",
  description: "Trace bounded health research questions to inspectable source passages.",
};

export default function EvidenceLensPage() {
  return <EvidenceLens />;
}

