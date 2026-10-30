"use client";

import { Check, ChevronRight, Search, X } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import {
  participants,
  reviewQueue,
  type Participant,
  type ParticipantStatus,
} from "@/data/coordinator";

const summary = [
  { value: "124", label: "Active Participants", tone: "navy" },
  { value: "11", label: "Need Review", tone: "orange" },
  { value: "4", label: "New Concomitant Meds", tone: "amber" },
  { value: "3", label: "Protocol Conflicts", tone: "red" },
  { value: "91%", label: "Avg Adherence", tone: "green" },
];

const filters = [
  "Requires action today",
  "Needs review",
  "Protocol conflict",
  "New concomitant med",
  "Missed dose",
  "Low adherence",
] as const;

const statusStyles: Record<ParticipantStatus, string> = {
  "Needs review": "bg-orange-50 text-orange-500",
  Stable: "bg-emerald-50 text-emerald-500",
  "Follow-up": "bg-blue-50 text-blue-500",
  Urgent: "bg-red-50 text-red-500",
  "Awaiting participant": "bg-slate-100 text-slate-500",
};

function matchesFilter(participant: Participant, filter: string) {
  switch (filter) {
    case "Needs review":
      return participant.status === "Needs review";
    case "Protocol conflict":
      return participant.protocolConflict;
    case "New concomitant med":
      return Boolean(participant.newMedication);
    case "Low adherence":
      return participant.adherence < 80;
    case "Missed dose":
      return participant.id === "P-1094";
    default:
      return true;
  }
}

export function CoordinatorDashboard() {
  const [activeFilter, setActiveFilter] =
    useState<(typeof filters)[number]>("Requires action today");
  const [query, setQuery] = useState("");
  const [site, setSite] = useState("All Sites");
  const [cohort, setCohort] = useState("All Cohorts");
  const [selectedParticipant, setSelectedParticipant] = useState<string | null>(
    null,
  );
  const [resolvedReviews, setResolvedReviews] = useState<string[]>([]);

  const visibleParticipants = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return participants.filter((participant) => {
      const matchesSearch =
        !normalizedQuery ||
        participant.id.toLowerCase().includes(normalizedQuery) ||
        participant.newMedication?.toLowerCase().includes(normalizedQuery) ||
        participant.status.toLowerCase().includes(normalizedQuery);
      return matchesSearch && matchesFilter(participant, activeFilter);
    });
  }, [activeFilter, query]);

  const visibleQueue = reviewQueue.filter(
    (item) =>
      !resolvedReviews.includes(item.id) &&
      (!selectedParticipant || item.participantId === selectedParticipant),
  );

  return (
    <main className="mx-auto w-full max-w-[1440px] flex-1 px-5 py-8 sm:px-8 lg:px-10">
      <p className="text-[13px] font-extrabold uppercase tracking-[0.04em] text-text-tertiary">
        Operational Summary
      </p>
      <section className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {summary.map((item) => (
          <article
            key={item.label}
            className="rounded-[16px] border border-border bg-white px-5 py-4 shadow-card"
          >
            <p
              className={`text-[25px] font-extrabold tracking-[-0.03em] ${
                item.tone === "orange"
                  ? "text-orange-500"
                  : item.tone === "amber"
                    ? "text-[#c77a24]"
                    : item.tone === "red"
                      ? "text-red-500"
                      : item.tone === "green"
                        ? "text-emerald-500"
                        : "text-brand-navy"
              }`}
            >
              {item.value}
            </p>
            <p className="mt-1 text-[13px] text-text-tertiary">{item.label}</p>
          </article>
        ))}
      </section>

      <section className="mt-6 flex flex-col justify-between gap-3 xl:flex-row xl:items-center">
        <div className="flex flex-wrap gap-2" aria-label="Participant filters">
          {filters.map((filter) => (
            <button
              key={filter}
              type="button"
              aria-pressed={activeFilter === filter}
              onClick={() => setActiveFilter(filter)}
              className={`rounded-pill border px-3.5 py-2 text-[13px] font-medium transition-colors ${
                activeFilter === filter
                  ? "border-brand-navy bg-brand-navy text-white"
                  : "border-border bg-white text-text-secondary hover:border-slate-300"
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <label className="relative">
            <span className="sr-only">Site</span>
            <select
              value={site}
              onChange={(event) => setSite(event.target.value)}
              className="h-9 appearance-none rounded-pill border border-border bg-white pl-3 pr-8 text-[13px] text-text-secondary outline-none focus:border-brand-navy"
            >
              <option>All Sites</option>
              <option>Site 042</option>
              <option>Site 109</option>
            </select>
            <ChevronRight
              size={14}
              className="pointer-events-none absolute right-2.5 top-2.5 rotate-90 text-text-tertiary"
            />
          </label>
          <label className="relative">
            <span className="sr-only">Cohort</span>
            <select
              value={cohort}
              onChange={(event) => setCohort(event.target.value)}
              className="h-9 appearance-none rounded-pill border border-border bg-white pl-3 pr-8 text-[13px] text-text-secondary outline-none focus:border-brand-navy"
            >
              <option>All Cohorts</option>
              <option>Cohort A</option>
              <option>Cohort B</option>
            </select>
            <ChevronRight
              size={14}
              className="pointer-events-none absolute right-2.5 top-2.5 rotate-90 text-text-tertiary"
            />
          </label>
        </div>
      </section>

      <section className="mt-5 grid items-start gap-6 xl:grid-cols-[minmax(0,1.8fr)_minmax(380px,1fr)]">
        <div className="min-w-0">
          <div className="mb-3 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <h1 className="text-[17px] font-extrabold tracking-[-0.02em]">
              Participants
            </h1>
            <label className="relative">
              <span className="sr-only">Search participants</span>
              <Search
                size={14}
                className="absolute left-3 top-2.5 text-text-tertiary"
              />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search ID, med, or status..."
                className="h-9 w-full rounded-[9px] border border-border bg-white pl-9 pr-8 text-[13px] outline-none placeholder:text-text-tertiary focus:border-brand-navy sm:w-[240px]"
              />
              {query && (
                <button
                  type="button"
                  aria-label="Clear search"
                  onClick={() => setQuery("")}
                  className="absolute right-2.5 top-2.5 text-text-tertiary"
                >
                  <X size={14} />
                </button>
              )}
            </label>
          </div>

          <div className="overflow-x-auto rounded-[16px] border border-border bg-white shadow-card">
            <table className="w-full min-w-[850px] border-collapse text-left">
              <thead>
                <tr className="border-b border-border bg-slate-50/70 text-[12px] font-extrabold uppercase text-text-tertiary">
                  <th className="px-4 py-3">Participant</th>
                  <th className="px-3 py-3">Day</th>
                  <th className="px-3 py-3">Adherence</th>
                  <th className="px-3 py-3">New Meds</th>
                  <th className="px-3 py-3">Protocol</th>
                  <th className="px-3 py-3">Reviews</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {visibleParticipants.map((participant) => (
                  <tr
                    key={participant.id}
                    className={
                      selectedParticipant === participant.id
                        ? "bg-orange-50/40"
                        : "hover:bg-slate-50/70"
                    }
                  >
                    <td className="px-4 py-3 text-[13px] font-bold text-text-primary">
                      {participant.id}
                    </td>
                    <td className="px-3 py-3 text-[13px] text-text-secondary">
                      {participant.day}
                    </td>
                    <td
                      className={`px-3 py-3 text-[13px] font-semibold ${
                        participant.adherence >= 95
                          ? "text-emerald-500"
                          : participant.adherence < 80
                            ? "text-red-500"
                            : "text-orange-500"
                      }`}
                    >
                      {participant.adherence}%
                    </td>
                    <td className="px-3 py-3 text-[13px] font-medium text-orange-500">
                      {participant.newMedication ?? (
                        <span className="text-text-tertiary">—</span>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      {participant.protocolConflict ? (
                        <span className="rounded-[5px] bg-red-50 px-2 py-1 text-[12px] font-bold text-red-500">
                          1 conflict
                        </span>
                      ) : (
                        <span className="text-[12px] font-semibold text-emerald-500">
                          Clear
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-[13px] text-orange-500">
                      {participant.reviews}
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={`rounded-pill px-2.5 py-1 text-[12px] font-bold ${statusStyles[participant.status]}`}
                      >
                        {participant.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {participant.id === "P-1042" ? (
                        <Link
                          href="/coordinator-dashboard/participants/P-1042"
                          className="text-[12px] font-bold text-brand-coral hover:underline"
                        >
                          Review →
                        </Link>
                      ) : (
                        <button
                          type="button"
                          onClick={() =>
                            setSelectedParticipant((selected) =>
                              selected === participant.id
                                ? null
                                : participant.id,
                            )
                          }
                          className="text-[12px] font-bold text-brand-coral hover:underline"
                        >
                          {participant.reviews ? "Review →" : "View →"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {visibleParticipants.length === 0 && (
              <p className="p-8 text-center text-[14px] text-text-tertiary">
                No participants match this search and filter.
              </p>
            )}
          </div>
        </div>

        <aside>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-[17px] font-extrabold tracking-[-0.02em]">
                Review Queue
              </h2>
              {selectedParticipant && (
                <button
                  type="button"
                  onClick={() => setSelectedParticipant(null)}
                  className="rounded-pill bg-surface-muted px-2.5 py-1 text-[12px] font-semibold text-text-secondary"
                >
                  {selectedParticipant} ×
                </button>
              )}
            </div>
            <span className="rounded-pill bg-red-50 px-2.5 py-1 text-[12px] font-bold text-red-500">
              {visibleQueue.length} Urgent
            </span>
          </div>
          <div className="space-y-3">
            {visibleQueue.map((item) => (
              <article
                key={item.id}
                className={`rounded-[16px] border border-border border-l-2 bg-white p-4 shadow-card ${
                  item.tone === "red"
                    ? "border-l-red-500"
                    : "border-l-orange-500"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-[14px] font-bold text-text-primary">
                    {item.participantId} · {item.title}
                  </h3>
                  <span className="shrink-0 rounded-pill bg-surface-muted px-2 py-1 text-[12px] font-semibold text-text-tertiary">
                    {item.source}
                  </span>
                </div>
                <p className="mt-1 text-[12px] text-text-secondary">
                  {item.summary}
                </p>
                <p
                  className={`mt-1 text-[12px] font-semibold ${
                    item.tone === "red" ? "text-red-500" : "text-orange-500"
                  }`}
                >
                  {item.detail}
                </p>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[12px] text-text-tertiary">
                    {item.detected}
                  </span>
                  <div className="flex items-center gap-2">
                    {item.actions.map((action, index) => (
                      <button
                        key={action}
                        type="button"
                        onClick={() => {
                          if (
                            action === "Resolve" ||
                            action === "Contact Partner"
                          ) {
                            setResolvedReviews((current) => [
                              ...current,
                              item.id,
                            ]);
                          } else {
                            setSelectedParticipant(item.participantId);
                          }
                        }}
                        className={
                          index === item.actions.length - 1
                            ? "rounded-[8px] bg-brand-navy px-3 py-2 text-[12px] font-bold text-white"
                            : action === "Resolve"
                              ? "text-[12px] font-bold text-emerald-500"
                              : "text-[12px] font-semibold text-text-secondary underline"
                        }
                      >
                        {action}
                      </button>
                    ))}
                  </div>
                </div>
              </article>
            ))}
            {visibleQueue.length === 0 && (
              <div className="rounded-[16px] border border-border bg-white p-8 text-center shadow-card">
                <Check
                  size={24}
                  className="mx-auto text-emerald-500"
                  aria-hidden="true"
                />
                <p className="mt-2 text-[14px] font-semibold text-text-primary">
                  Queue cleared
                </p>
                <p className="mt-1 text-[12px] text-text-tertiary">
                  No open reviews for this selection.
                </p>
              </div>
            )}
          </div>
        </aside>
      </section>
    </main>
  );
}
