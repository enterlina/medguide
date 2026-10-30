import { Settings } from "lucide-react";
import { SectionPlaceholder } from "@/components/section-placeholder";

export default function SettingsPage() {
  return (
    <SectionPlaceholder
      icon={Settings}
      title="Settings"
      description="Manage medication preferences, reminders, accessibility, and account settings."
    />
  );
}
