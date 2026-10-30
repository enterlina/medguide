import { CalendarDays } from "lucide-react";
import { SectionPlaceholder } from "@/components/section-placeholder";

export default function SchedulePage() {
  return (
    <SectionPlaceholder
      icon={CalendarDays}
      title="Medication schedule"
      description="Review upcoming doses and keep track of your daily medication routine."
    />
  );
}
