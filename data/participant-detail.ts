export type TimelineTone = "orange" | "green" | "red" | "blue";

export interface TimelineEvent {
  id: string;
  day: number;
  title: string;
  description: string;
  source: string;
  note?: string;
  conflict?: boolean;
  tone: TimelineTone;
}

export const participantMedications = [
  { name: "Study Drug XR-7742", dose: "200mg", study: true },
  { name: "Amoxicillin", dose: "500mg" },
  { name: "Levothyroxine", dose: "50mcg" },
  { name: "Iron Supplement", dose: "65mg" },
  { name: "Lisinopril", dose: "10mg" },
  { name: "Warfarin", dose: "5mg" },
  { name: "Ibuprofen", dose: "400mg", concomitant: true },
];

export const timelineEvents: TimelineEvent[] = [
  {
    id: "continued",
    day: 18,
    title: "Ibuprofen use continued",
    description: "Participant reports ongoing use of Ibuprofen 400mg.",
    source: "AI extracted from participant check-in",
    note: "Confirmed by participant",
    conflict: true,
    tone: "orange",
  },
  {
    id: "responded",
    day: 14,
    title: "Participant responded",
    description:
      "Confirmed evening dose of Study Drug XR-7742 was taken but not logged due to device connectivity.",
    source: "Participant reported",
    tone: "green",
  },
  {
    id: "missed",
    day: 12,
    title: "Dose missed",
    description: "Study Drug XR-7742 evening dose not confirmed.",
    source: "System detected",
    note: "Reminder sent, no response",
    tone: "red",
  },
  {
    id: "reviewed",
    day: 9,
    title: "Coordinator reviewed",
    description:
      "Protocol conflict acknowledged; monitoring initiated for possible NSAID-related adverse reactions.",
    source: "Coordinator: Dr. Chen",
    tone: "blue",
  },
  {
    id: "triggered",
    day: 8,
    title: "Protocol rule triggered",
    description: "PR-14: NSAIDs not permitted during treatment phase.",
    source: "System detected",
    tone: "red",
  },
  {
    id: "added",
    day: 8,
    title: "Concomitant medication added",
    description: "Ibuprofen 400mg as needed for mild headache.",
    source: "Participant reported",
    conflict: true,
    tone: "orange",
  },
  {
    id: "late",
    day: 5,
    title: "Dose taken late",
    description:
      "Study Drug XR-7742 evening dose confirmed taken 3h late.",
    source: "Device captured",
    tone: "orange",
  },
  {
    id: "started",
    day: 1,
    title: "Study drug started",
    description:
      "First baseline dose of Study Drug XR-7742 200mg administered.",
    source: "Clinician entered",
    tone: "green",
  },
];

export const auditEvents = [
  {
    time: "01:18 PM",
    text: "Marked for continued monitoring by clinical team",
    actor: "Dr. Chen",
  },
  {
    time: "01:15 PM",
    text: "Coordinator reviewed protocol conflict alert",
    actor: "Dr. Chen",
  },
  {
    time: "10:44 AM",
    text: "Participant confirmed dose: 400mg as needed",
    actor: "Participant confirmed",
  },
  {
    time: "10:42 AM",
    text: "AI normalized medication mapping ‘Advil’ → Ibuprofen",
    actor: "AI extracted · Confirmed by participant",
  },
  {
    time: "10:42 AM",
    text: "Participant self-reported Ibuprofen ingestion on check-in",
    actor: "Participant reported",
  },
];
