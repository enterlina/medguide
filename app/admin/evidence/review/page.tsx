import type { Metadata } from "next";
import { EvidenceReviewDashboard } from "@/components/evidence-review-dashboard";

export const metadata: Metadata = {
  title: "Evidence Review — MedGuide Admin",
  description: "Local review of PubMed entity matches before RAG admission.",
  robots: { index: false, follow: false },
};

export default function EvidenceReviewPage() {
  return <EvidenceReviewDashboard />;
}
