export type ParticipantStatus =
  | "Needs review"
  | "Stable"
  | "Follow-up"
  | "Urgent"
  | "Awaiting participant";

export interface Participant {
  id: string;
  day: number;
  adherence: number;
  newMedication?: string;
  protocolConflict: boolean;
  reviews: number;
  status: ParticipantStatus;
}

export interface ReviewItem {
  id: string;
  participantId: string;
  title: string;
  summary: string;
  detail: string;
  detected: string;
  source: "Participant reported" | "System detected";
  tone: "orange" | "red";
  actions: string[];
}

export const participants: Participant[] = [
  {
    id: "P-1042",
    day: 18,
    adherence: 96,
    newMedication: "Ibuprofen",
    protocolConflict: true,
    reviews: 2,
    status: "Needs review",
  },
  {
    id: "P-1088",
    day: 11,
    adherence: 100,
    protocolConflict: false,
    reviews: 0,
    status: "Stable",
  },
  {
    id: "P-1094",
    day: 24,
    adherence: 82,
    newMedication: "Magnesium",
    protocolConflict: false,
    reviews: 1,
    status: "Follow-up",
  },
  {
    id: "P-1103",
    day: 7,
    adherence: 100,
    protocolConflict: false,
    reviews: 0,
    status: "Stable",
  },
  {
    id: "P-1067",
    day: 31,
    adherence: 71,
    newMedication: "Vitamin D",
    protocolConflict: false,
    reviews: 3,
    status: "Urgent",
  },
  {
    id: "P-1112",
    day: 5,
    adherence: 100,
    protocolConflict: false,
    reviews: 0,
    status: "Awaiting participant",
  },
  {
    id: "P-1055",
    day: 22,
    adherence: 89,
    newMedication: "Aspirin",
    protocolConflict: true,
    reviews: 1,
    status: "Needs review",
  },
];

export const reviewQueue: ReviewItem[] = [
  {
    id: "review-1042",
    participantId: "P-1042",
    title: "New concomitant medication",
    summary: "Ibuprofen reported on Day 18",
    detail: "Matches protocol restriction",
    detected: "Reported 2h ago",
    source: "Participant reported",
    tone: "orange",
    actions: ["Contact", "Resolve", "Review"],
  },
  {
    id: "review-1094",
    participantId: "P-1094",
    title: "Missed study dose",
    summary: "Evening dose not confirmed",
    detail: "Participant has not responded to reminder",
    detected: "Detected 14h ago",
    source: "System detected",
    tone: "red",
    actions: ["Open Timeline", "Contact Partner"],
  },
  {
    id: "review-1067",
    participantId: "P-1067",
    title: "Low adherence alert",
    summary: "71% adherence over last 7 days",
    detail: "3 missed doses, 1 late dose",
    detected: "Detected 1d ago",
    source: "System detected",
    tone: "orange",
    actions: ["Contact", "Review"],
  },
  {
    id: "review-1055",
    participantId: "P-1055",
    title: "New concomitant medication",
    summary: "Aspirin reported on Day 22",
    detail: "May interact with study medication",
    detected: "Reported 4h ago",
    source: "Participant reported",
    tone: "orange",
    actions: ["Resolve", "Review"],
  },
];
