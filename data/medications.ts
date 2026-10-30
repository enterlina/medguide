import type { Insight, Medication, ScheduleItem } from "@/types/medication";

export const medications: Medication[] = [
  {
    id: "med-001",
    name: "Lisinopril",
    genericName: "Lisinopril",
    dosage: "10 mg",
    form: "Tablet",
    frequency: "Once daily",
    nextDose: "8:00",
    nextDosePeriod: "AM",
    instruction: "Take at the same time each day",
    color: "blue",
    status: "active",
  },
  {
    id: "med-002",
    name: "Metformin",
    genericName: "Metformin hydrochloride",
    dosage: "500 mg",
    form: "Tablet",
    frequency: "Twice daily",
    nextDose: "12:30",
    nextDosePeriod: "PM",
    instruction: "Take with a meal",
    color: "violet",
    status: "active",
  },
  {
    id: "med-003",
    name: "Atorvastatin",
    genericName: "Atorvastatin calcium",
    dosage: "20 mg",
    form: "Tablet",
    frequency: "Once daily",
    nextDose: "9:00",
    nextDosePeriod: "PM",
    instruction: "Take in the evening",
    color: "amber",
    status: "active",
  },
];

export const schedule: ScheduleItem[] = [
  {
    id: "dose-001",
    medicationId: "med-001",
    time: "8:00",
    period: "AM",
    taken: false,
  },
  {
    id: "dose-002",
    medicationId: "med-002",
    time: "12:30",
    period: "PM",
    taken: false,
  },
  {
    id: "dose-003",
    medicationId: "med-003",
    time: "9:00",
    period: "PM",
    taken: false,
  },
];

export const insights: Insight[] = [
  {
    id: "insight-001",
    kind: "safe",
    title: "No major interactions found",
    description:
      "Your current medications have no known major interactions when taken as directed.",
    medicationIds: ["med-001", "med-002", "med-003"],
  },
  {
    id: "insight-002",
    kind: "timing",
    title: "Keep a consistent schedule",
    description:
      "Take Lisinopril at the same time each morning to maintain a steady routine.",
    medicationIds: ["med-001"],
  },
  {
    id: "insight-003",
    kind: "food",
    title: "Take Metformin with food",
    description:
      "Taking it with your midday meal can help reduce stomach discomfort.",
    medicationIds: ["med-002"],
  },
];
