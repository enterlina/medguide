import { History } from "lucide-react";
import { SectionPlaceholder } from "@/components/section-placeholder";

export default function HistoryPage() {
  return (
    <SectionPlaceholder
      icon={History}
      title="Medication history"
      description="Review completed doses, medication changes, and past interaction checks."
    />
  );
}
