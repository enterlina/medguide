import { FlaskConical } from "lucide-react";
import { SectionPlaceholder } from "@/components/section-placeholder";

export default function ClinicalTrialsPage() {
  return (
    <SectionPlaceholder
      icon={FlaskConical}
      title="Clinical trials"
      description="Explore relevant research and recruiting studies from trusted clinical trial sources."
    />
  );
}
