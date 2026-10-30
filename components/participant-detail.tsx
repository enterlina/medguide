"use client";

import {
  ArrowLeft,
  Check,
  ChevronDown,
  Link2,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import {
  auditEvents,
  participantMedications,
  timelineEvents,
  type TimelineEvent,
} from "@/data/participant-detail";

const toneStyles: Record<TimelineEvent["tone"], string> = {
  orange: "bg-orange-500",
  green: "bg-emerald-500",
  red: "bg-red-500",
  blue: "bg-blue-500",
};

export function ParticipantDetail() {
  const [eventFilter, setEventFilter] = useState("All events");
  const [contactOpen, setContactOpen] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const [messageSent, setMessageSent] = useState(false);

  const events = useMemo(() => {
    if (eventFilter === "Protocol conflicts") {
      return timelineEvents.filter((event) => event.conflict);
    }
    if (eventFilter === "Dose events") {
      return timelineEvents.filter((event) =>
        event.title.toLowerCase().includes("dose"),
      );
    }
    return timelineEvents;
  }, [eventFilter]);

  return (
    <>
      <main className="mx-auto w-full max-w-[1440px] flex-1 px-5 py-6 sm:px-8 lg:px-10">
        <Link
          href="/coordinator-dashboard"
          className="inline-flex items-center gap-1.5 text-[12px] font-semibold text-text-tertiary hover:text-text-primary"
        >
          <ArrowLeft size={13} /> Back to Participant Dashboard
        </Link>

        <section className="mt-5 flex flex-col justify-between gap-5 rounded-[16px] border border-border bg-white px-5 py-4 shadow-card lg:flex-row lg:items-center">
          <div>
            <h1 className="text-[21px] font-extrabold tracking-[-0.03em]">
              P-1042
            </h1>
            <p className="mt-1 text-[12px] text-text-tertiary">
              BEACON-3 Trial · Site 042 (Boston Clinical)
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-5 lg:ml-auto">
            {[
              ["Study Timeline", "Day 18"],
              ["Adherence", "96%"],
              ["Open Reviews", "2 Alerts"],
              ["Operational Status", "Needs Review"],
            ].map(([label, value], index) => (
              <div
                key={label}
                className="border-l border-border pl-5 first:border-0 first:pl-0"
              >
                <p className="text-[12px] font-extrabold uppercase text-text-tertiary">
                  {label}
                </p>
                {index === 3 ? (
                  <span className="mt-1 inline-block rounded-pill bg-orange-50 px-2.5 py-1 text-[12px] font-bold text-orange-500">
                    {value}
                  </span>
                ) : (
                  <p
                    className={`mt-1 text-[14px] font-bold ${
                      index === 1
                        ? "text-emerald-500"
                        : index === 2
                          ? "text-orange-500"
                          : "text-text-primary"
                    }`}
                  >
                    {value}
                  </p>
                )}
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              className="h-9 rounded-[9px] px-3 text-[12px] font-bold text-brand-coral hover:bg-orange-50"
            >
              View Full Profile
            </button>
            <button
              type="button"
              onClick={() => setContactOpen(true)}
              className="h-9 rounded-[9px] bg-brand-navy px-4 text-[12px] font-bold text-white"
            >
              Contact Participant
            </button>
          </div>
        </section>

        <section className="mt-5 rounded-[16px] border border-border bg-white p-4 shadow-card">
          <p className="mb-3 flex items-center gap-1.5 text-[12px] font-extrabold uppercase text-text-tertiary">
            <Link2 size={12} className="-rotate-45" /> Active Regime (7
            medications)
          </p>
          <div className="flex flex-wrap gap-2">
            {participantMedications.map((medication) => (
              <span
                key={medication.name}
                className={`rounded-[6px] border px-2.5 py-1.5 text-[12px] font-semibold ${
                  medication.concomitant
                    ? "border-orange-400 bg-orange-50 text-orange-500"
                    : medication.study
                      ? "border-[#dad7ff] bg-[#f0efff] text-[#7165ee]"
                      : "border-border bg-surface-muted text-text-primary"
                }`}
              >
                {medication.name}{" "}
                <span className="font-normal">{medication.dose}</span>
                {medication.study && (
                  <strong className="ml-2 rounded-[3px] bg-[#7165ee] px-1 py-0.5 text-[11px] uppercase text-white">
                    Study
                  </strong>
                )}
                {medication.concomitant && (
                  <strong className="ml-2 rounded-[3px] bg-orange-500 px-1 py-0.5 text-[11px] uppercase text-white">
                    Concomitant
                  </strong>
                )}
              </span>
            ))}
          </div>
        </section>

        <section className="mt-5 grid items-start gap-6 xl:grid-cols-[minmax(0,1.65fr)_minmax(380px,1fr)]">
          <div className="min-w-0">
            <section className="rounded-[16px] border border-l-[3px] border-border border-l-[#d9e0eb] bg-white p-5 shadow-card">
              <div className="flex items-center justify-between">
                <h2 className="flex items-center gap-2 text-[13px] font-extrabold">
                  <Sparkles size={17} className="text-[#7165ee]" /> AI Summary
                  Insights
                </h2>
                <span className="text-[12px] text-text-tertiary">
                  Generated 2h ago
                </span>
              </div>
              <p className="mt-4 text-[13px] leading-[1.65] text-text-secondary">
                Participant reported ibuprofen on Day 8. This medication
                matches a protocol restriction (PR-14: NSAIDs not permitted)
                and has not yet been reviewed by the study team. Study
                medication adherence over the last 14 days is 86%, with one
                missed dose and two late doses.
              </p>
              <div className="mt-4 flex flex-col justify-between gap-3 border-t border-border pt-3 sm:flex-row sm:items-end">
                <p className="text-[12px] italic text-text-tertiary">
                  AI summarizes participant data. Does not make clinical
                  decisions.
                </p>
                <div className="flex flex-wrap gap-2">
                  <button className="text-[12px] font-semibold text-text-tertiary underline">
                    View source events
                  </button>
                  <button
                    onClick={() => setContactOpen(true)}
                    className="text-[12px] font-bold text-brand-coral"
                  >
                    Contact participant
                  </button>
                  <button
                    onClick={() => setReviewed(true)}
                    className={`rounded-[8px] px-3 py-2 text-[12px] font-bold text-white ${
                      reviewed ? "bg-emerald-500" : "bg-brand-navy"
                    }`}
                  >
                    {reviewed ? "Reviewed" : "Review Action"}
                  </button>
                </div>
              </div>
            </section>

            <div className="mb-3 mt-6 flex items-center justify-between">
              <h2 className="text-[15px] font-extrabold">
                Medication Timeline
              </h2>
              <label className="relative">
                <span className="sr-only">Filter timeline</span>
                <select
                  value={eventFilter}
                  onChange={(event) => setEventFilter(event.target.value)}
                  className="h-8 appearance-none rounded-[9px] border border-border bg-white pl-3 pr-8 text-[12px] text-text-secondary outline-none"
                >
                  <option>All events</option>
                  <option>Protocol conflicts</option>
                  <option>Dose events</option>
                </select>
                <ChevronDown
                  size={12}
                  className="pointer-events-none absolute right-2.5 top-2.5 text-text-tertiary"
                />
              </label>
            </div>
            <section className="relative">
              <div className="absolute bottom-7 left-[67px] top-3 w-px bg-border" />
              <div className="space-y-3">
                {events.map((event) => (
                  <article
                    key={event.id}
                    className="relative grid grid-cols-[55px_16px_minmax(0,1fr)] gap-1"
                  >
                    <p className="pt-2 text-right text-[12px] font-bold text-text-tertiary">
                      Day {event.day}
                    </p>
                    <span
                      className={`relative z-10 mt-2.5 size-2 rounded-full ring-4 ring-background ${toneStyles[event.tone]}`}
                    />
                    <div className="rounded-[12px] border border-border bg-white p-3 shadow-card">
                      <div className="flex items-start justify-between gap-3">
                        <h3 className="text-[13px] font-bold text-text-primary">
                          {event.title}
                        </h3>
                        {event.conflict && (
                          <span className="rounded-pill bg-orange-50 px-2 py-1 text-[12px] font-bold uppercase text-orange-500">
                            Protocol conflict
                          </span>
                        )}
                      </div>
                      <p className="mt-2 text-[12px] leading-[1.45] text-text-secondary">
                        {event.description}
                      </p>
                      <div className="mt-2 flex flex-wrap justify-between gap-2 text-[12px] text-text-tertiary">
                        <p>
                          Source:{" "}
                          <strong className="ml-1 text-text-secondary">
                            {event.source}
                          </strong>
                        </p>
                        {event.note && <em>{event.note}</em>}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </div>

          <aside className="grid content-start gap-5">
            <section className="rounded-[16px] border border-border bg-white p-4 shadow-card">
              <div className="flex items-center justify-between">
                <h2 className="text-[13px] font-extrabold">Protocol Rules</h2>
                <span className="rounded-pill bg-red-50 px-2 py-1 text-[12px] font-bold text-red-500">
                  1 active conflict
                </span>
              </div>
              <div className="mt-3 rounded-[12px] bg-surface-muted p-3">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-[12px] font-bold">Protocol Rule PR-14</h3>
                  <span className="rounded-pill bg-red-50 px-2 py-1 text-[11px] font-bold text-red-500">
                    Requires study-team review
                  </span>
                </div>
                <p className="mt-2 text-[12px] text-text-secondary">
                  NSAIDs not permitted during active treatment period.
                </p>
                <p className="mt-2 text-[12px] font-semibold text-orange-500">
                  Ibuprofen added Day 8{" "}
                  <span className="font-normal text-text-tertiary">
                    · (Ongoing)
                  </span>
                </p>
                <div className="mt-3 flex items-center justify-between">
                  <button className="text-[12px] font-semibold text-text-tertiary underline">
                    View full rules
                  </button>
                  <button
                    onClick={() => setReviewed(true)}
                    className={`rounded-[8px] px-3 py-2 text-[12px] font-bold text-white ${
                      reviewed ? "bg-emerald-500" : "bg-brand-navy"
                    }`}
                  >
                    {reviewed ? "Reviewed" : "Review Conflict"}
                  </button>
                </div>
              </div>
            </section>

            <section className="rounded-[16px] border border-border bg-white p-4 shadow-card">
              <h2 className="text-[13px] font-extrabold">
                Concomitant Medications Log
              </h2>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[350px] text-left">
                  <thead className="text-[12px] font-extrabold uppercase text-text-tertiary">
                    <tr>
                      <th className="pb-2">Medication</th>
                      <th className="pb-2">Regime</th>
                      <th className="pb-2">Conflict status</th>
                      <th className="pb-2">Review</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border text-[12px]">
                    <tr>
                      <td className="py-2 font-bold">
                        Ibuprofen 400mg
                        <span className="block text-[12px] font-normal text-text-tertiary">
                          Day 8 · Self-reported
                        </span>
                      </td>
                      <td>As needed</td>
                      <td className="text-red-500">Rule PR-14</td>
                      <td className="text-orange-500">Needs Review</td>
                    </tr>
                    <tr>
                      <td className="py-2 font-bold">
                        Vitamin D 2000 IU
                        <span className="block text-[12px] font-normal text-text-tertiary">
                          Baseline · Clinician
                        </span>
                      </td>
                      <td>Daily</td>
                      <td className="text-emerald-500">No conflict</td>
                      <td className="text-emerald-500">Reviewed</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-[16px] border border-border bg-white p-4 shadow-card">
              <div className="flex items-center justify-between">
                <h2 className="text-[13px] font-extrabold">
                  Adherence Performance
                </h2>
                <span className="text-[12px] text-text-tertiary">
                  Last 14 days
                </span>
              </div>
              <div className="mt-3 flex items-end gap-5">
                <strong className="text-[34px] font-extrabold text-orange-500">
                  86%
                </strong>
                <div className="flex-1 pb-2">
                  <div className="flex h-1.5 overflow-hidden rounded-pill">
                    <span className="w-[70%] bg-emerald-500" />
                    <span className="w-[14%] bg-orange-500" />
                    <span className="w-[8%] bg-red-500" />
                    <span className="w-[8%] bg-slate-400" />
                  </div>
                  <p className="mt-2 text-[12px] text-text-tertiary">
                    <span className="text-emerald-500">●</span> 12 taken　
                    <span className="text-orange-500">●</span> 2 late　
                    <span className="text-red-500">●</span> 1 missed　
                    <span className="text-slate-400">●</span> 1 unconfirmed
                  </p>
                </div>
              </div>
              <button className="mt-3 border-t border-border pt-3 text-[12px] font-bold text-brand-coral">
                View adherence timeline →
              </button>
            </section>

            <section className="rounded-[16px] border border-border bg-white p-4 shadow-card">
              <div className="flex items-center justify-between">
                <h2 className="text-[13px] font-extrabold">Audit Trail</h2>
                <span className="text-[12px] text-text-tertiary">
                  Day 8 events filter active
                </span>
              </div>
              <div className="mt-3 space-y-3">
                {auditEvents.map((event) => (
                  <div
                    key={`${event.time}-${event.text}`}
                    className="grid grid-cols-[8px_55px_1fr] gap-2"
                  >
                    <span className="mt-1.5 size-1.5 rounded-full bg-slate-500" />
                    <div>
                      <p className="text-[12px] font-bold">{event.time}</p>
                      <p className="text-[12px] text-text-tertiary">
                        {event.actor}
                      </p>
                    </div>
                    <p className="text-[12px] leading-[1.4] text-text-secondary">
                      {event.text}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          </aside>
        </section>
      </main>

      {contactOpen && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-brand-navy/35 p-4"
          onMouseDown={() => setContactOpen(false)}
        >
          <form
            onSubmit={(event) => {
              event.preventDefault();
              setMessageSent(true);
            }}
            onMouseDown={(event) => event.stopPropagation()}
            className="w-full max-w-md rounded-card bg-white p-6 shadow-[0_24px_70px_rgba(15,23,42,0.2)]"
          >
            <div className="flex justify-between">
              <div>
                <h2 className="text-[17px] font-extrabold">
                  Contact participant
                </h2>
                <p className="mt-1 text-[13px] text-text-tertiary">
                  Secure message to participant P-1042
                </p>
              </div>
              <button
                type="button"
                aria-label="Close"
                onClick={() => setContactOpen(false)}
                className="grid size-9 place-items-center rounded-[9px] bg-surface-muted"
              >
                <X size={16} />
              </button>
            </div>
            {messageSent ? (
              <div className="mt-6 rounded-[12px] bg-emerald-50 p-4 text-center">
                <Check size={22} className="mx-auto text-emerald-500" />
                <p className="mt-2 text-[14px] font-bold text-emerald-600">
                  Message sent securely
                </p>
              </div>
            ) : (
              <>
                <textarea
                  required
                  rows={5}
                  defaultValue="Please contact the study team to review your recently reported ibuprofen use."
                  className="mt-5 w-full resize-none rounded-[12px] border border-border p-3 text-[14px] outline-none focus:border-brand-navy"
                />
                <button
                  type="submit"
                  className="mt-3 h-10 w-full rounded-[10px] bg-brand-navy text-[13px] font-bold text-white"
                >
                  Send secure message
                </button>
              </>
            )}
          </form>
        </div>
      )}
    </>
  );
}
