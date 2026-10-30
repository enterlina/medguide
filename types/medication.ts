export type MedicationStatus = "active" | "completed" | "paused";

export interface Medication {
  id: string;
  name: string;
  genericName: string;
  dosage: string;
  form: string;
  frequency: string;
  nextDose: string;
  nextDosePeriod: string;
  instruction: string;
  color: "blue" | "violet" | "amber";
  status: MedicationStatus;
}

export interface ScheduleItem {
  id: string;
  medicationId: string;
  time: string;
  period: string;
  taken: boolean;
}

export interface Insight {
  id: string;
  kind: "safe" | "timing" | "food";
  title: string;
  description: string;
  medicationIds: string[];
}
