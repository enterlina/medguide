export interface MedicationSummary {
  id: string;
  name: string;
  dose: string;
  frequency: string;
  issue?: "Timing issue" | "Interaction";
  category?: "Prescription" | "Supplement" | "Study medication";
  study?: boolean;
  meta?: string;
}

export interface DosePlanItem {
  id: string;
  period: "Morning" | "Afternoon" | "Evening";
  name: string;
  dose: string;
  time: string;
  instruction: string;
  detail?: string;
  next?: boolean;
  completed?: boolean;
  emphasized?: boolean;
  study?: boolean;
}

export const medicationSummaries: MedicationSummary[] = [
  { id: "amoxicillin", name: "Amoxicillin", dose: "500mg", frequency: "3×/day" },
  {
    id: "levothyroxine",
    name: "Levothyroxine",
    dose: "50mcg",
    frequency: "1×/day",
  },
  {
    id: "iron",
    name: "Iron Supplement",
    dose: "65mg",
    frequency: "1×/day",
    issue: "Timing issue",
  },
  { id: "lisinopril", name: "Lisinopril", dose: "10mg", frequency: "1×/day" },
  {
    id: "warfarin",
    name: "Warfarin",
    dose: "5mg",
    frequency: "1×/day",
    issue: "Interaction",
  },
];

export const dosePlan: DosePlanItem[] = [
  {
    id: "levothyroxine-morning",
    period: "Morning",
    name: "Levothyroxine",
    dose: "50mcg",
    time: "7:00 AM",
    instruction: "Empty stomach · 30 min before food",
    completed: true,
  },
  {
    id: "amoxicillin-morning",
    period: "Morning",
    name: "Amoxicillin",
    dose: "500mg",
    time: "8:00 AM",
    instruction: "With breakfast",
    completed: true,
  },
  {
    id: "iron-afternoon",
    period: "Afternoon",
    name: "Iron Supplement",
    dose: "65mg",
    time: "12:00 PM",
    instruction: "Moved from 8:00 AM → 12:00 PM",
    detail: "Keeps 4h separation from Levothyroxine · Why?",
    emphasized: true,
  },
  {
    id: "amoxicillin-afternoon",
    period: "Afternoon",
    name: "Amoxicillin",
    dose: "500mg",
    time: "2:00 PM",
    instruction: "With food",
    next: true,
    emphasized: true,
  },
  {
    id: "amoxicillin-evening",
    period: "Evening",
    name: "Amoxicillin",
    dose: "500mg",
    time: "8:00 PM",
    instruction: "With dinner",
  },
  {
    id: "lisinopril-evening",
    period: "Evening",
    name: "Lisinopril",
    dose: "10mg",
    time: "8:00 PM",
    instruction: "With dinner",
  },
  {
    id: "warfarin-evening",
    period: "Evening",
    name: "Warfarin",
    dose: "5mg",
    time: "8:00 PM",
    instruction: "With dinner",
  },
];

export const medicationInstructions = [
  { name: "Levothyroxine", tags: ["Empty stomach", "30 min before food"] },
  { name: "Iron Supplement", tags: ["Take with vitamin C", "Avoid dairy 2h"] },
  { name: "Warfarin", tags: ["Avoid grapefruit", "Limit vitamin K"] },
  { name: "Amoxicillin", tags: ["Take with food"] },
];

export const clinicalMedicationSummaries: MedicationSummary[] = [
  {
    id: "amoxicillin",
    name: "Amoxicillin",
    dose: "500mg",
    frequency: "3×/day",
    category: "Prescription",
  },
  {
    id: "levothyroxine",
    name: "Levothyroxine",
    dose: "50mcg",
    frequency: "1×/day",
    category: "Prescription",
  },
  {
    id: "lisinopril",
    name: "Lisinopril",
    dose: "10mg",
    frequency: "1×/day",
    category: "Prescription",
  },
  {
    id: "warfarin",
    name: "Warfarin",
    dose: "5mg",
    frequency: "1×/day",
    issue: "Interaction",
    category: "Prescription",
  },
  {
    id: "iron",
    name: "Iron Supplement",
    dose: "65mg",
    frequency: "1×/day",
    issue: "Timing issue",
    category: "Supplement",
  },
  {
    id: "study-drug",
    name: "Study Drug XR-7742",
    dose: "200mg",
    frequency: "2×/day",
    category: "Study medication",
    study: true,
    meta: "BEACON-3 Trial · Site 042",
  },
];

export const clinicalDosePlan: DosePlanItem[] = [
  {
    id: "levothyroxine-morning",
    period: "Morning",
    name: "Levothyroxine",
    dose: "50mcg",
    time: "7:00 AM",
    instruction: "Empty stomach · 30 min before food",
    completed: true,
  },
  {
    id: "study-morning",
    period: "Morning",
    name: "Study Drug XR-7742",
    dose: "200mg",
    time: "7:30 AM",
    instruction: "With water only · per protocol",
    completed: true,
    study: true,
  },
  {
    id: "amoxicillin-morning",
    period: "Morning",
    name: "Amoxicillin",
    dose: "500mg",
    time: "8:00 AM",
    instruction: "With breakfast",
    completed: true,
  },
  {
    id: "study-afternoon",
    period: "Afternoon",
    name: "Study Drug",
    dose: "XR-7742 200mg",
    time: "12:00 PM",
    instruction: "With water only · per protocol",
    next: true,
    emphasized: true,
    study: true,
  },
  {
    id: "iron-afternoon",
    period: "Afternoon",
    name: "Iron Supplement",
    dose: "65mg",
    time: "12:00 PM",
    instruction: "Moved from 8:00 AM → 12:00 PM",
    detail: "Keeps 4h separation from Levothyroxine · Why?",
    emphasized: true,
  },
  {
    id: "amoxicillin-afternoon",
    period: "Afternoon",
    name: "Amoxicillin",
    dose: "500mg",
    time: "2:00 PM",
    instruction: "With food",
    emphasized: true,
  },
  {
    id: "amoxicillin-evening",
    period: "Evening",
    name: "Amoxicillin",
    dose: "500mg",
    time: "8:00 PM",
    instruction: "With dinner",
  },
  {
    id: "lisinopril-evening",
    period: "Evening",
    name: "Lisinopril",
    dose: "10mg",
    time: "8:00 PM",
    instruction: "With dinner",
  },
  {
    id: "warfarin-evening",
    period: "Evening",
    name: "Warfarin",
    dose: "5mg",
    time: "8:00 PM",
    instruction: "With dinner",
  },
];

export const clinicalMedicationInstructions = [
  {
    name: "Study Drug XR-7742",
    tags: ["With water only", "Per protocol"],
    study: true,
  },
  { name: "Levothyroxine", tags: ["Empty stomach", "30 min before food"] },
  { name: "Iron Supplement", tags: ["Take with vitamin C", "Avoid dairy 2h"] },
  { name: "Warfarin", tags: ["Avoid grapefruit", "Limit vitamin K"] },
  { name: "Amoxicillin", tags: ["Take with food"] },
];
