import type { Metadata } from "next";
import { InteractionReviewDashboard } from "@/components/interaction-review-dashboard";

export const metadata: Metadata = {
  title: "Interaction Review — MedGuide Admin",
  description: "Protected two-step review of extracted interaction rules.",
  robots: { index: false, follow: false },
};

export default function InteractionReviewPage() {
  return <InteractionReviewDashboard />;
}
