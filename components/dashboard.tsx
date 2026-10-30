"use client";

import {
  ArrowRight,
  Check,
  ChevronRight,
  Link2,
  Plus,
  Siren,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";
import { Fragment, useState } from "react";
import {
  clinicalDosePlan,
  clinicalMedicationInstructions,
  clinicalMedicationSummaries,
  dosePlan,
  medicationInstructions,
  medicationSummaries,
  type DosePlanItem,
} from "@/data/dashboard";

function MedicineRail({
  onAdd,
  clinicalTrialMode,
}: {
  onAdd: () => void;
  clinicalTrialMode: boolean;
}) {
  const items = clinicalTrialMode
    ? clinicalMedicationSummaries
    : medicationSummaries;

  return (
    <aside>
      <div className="mb-5 flex items-center justify-between">
        <h1 className="text-[17px] font-extrabold tracking-[-0.02em]">
          My Medications
        </h1>
        <button
          type="button"
          onClick={onAdd}
          className="inline-flex h-8 items-center gap-1.5 rounded-[10px] bg-brand-coral px-3.5 text-[14px] font-bold text-white hover:bg-brand-coral-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-coral focus-visible:ring-offset-2"
        >
          <Plus size={14} strokeWidth={2.8} /> Add
        </button>
      </div>

      <section className="rounded-card bg-white p-4 shadow-card">
        <div className="divide-y divide-border">
          {items.map((medication, index) => (
            <Fragment key={medication.id}>
              {medication.category &&
                medication.category !== items[index - 1]?.category && (
                  <p className="pt-4 text-[12px] font-extrabold uppercase text-text-tertiary first:pt-0">
                    {medication.category}
                  </p>
                )}
              <button
                type="button"
                className="flex w-full items-center gap-3 py-4 text-left first:pt-1 hover:opacity-75 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-navy"
              >
                <span
                  className={`grid size-9 shrink-0 place-items-center rounded-full bg-surface-muted ${
                    medication.study ? "text-[#7165ee]" : "text-brand-navy"
                  }`}
                >
                  <Link2 size={17} className="-rotate-45" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2">
                    <span
                      className={`truncate text-[13px] font-semibold ${
                        medication.study
                          ? "text-[#7165ee]"
                          : "text-text-primary"
                      }`}
                    >
                      {medication.name}
                    </span>
                    {medication.study && (
                      <span className="ml-auto rounded-pill bg-[#f0efff] px-2 py-1 text-[12px] font-bold uppercase text-[#7165ee]">
                        Study
                      </span>
                    )}
                    {medication.issue && (
                      <span className="ml-auto shrink-0 rounded-pill bg-[#fff0ec] px-2 py-1 text-[12px] font-bold uppercase text-brand-coral">
                        {medication.issue}
                      </span>
                    )}
                  </span>
                  <span className="mt-0.5 block text-[13px] text-text-tertiary">
                    {medication.dose} · {medication.frequency}
                  </span>
                  {medication.meta && (
                    <span className="mt-0.5 block text-[12px] text-text-tertiary">
                      {medication.meta}
                    </span>
                  )}
                </span>
                <ChevronRight size={15} className="shrink-0 text-slate-400" />
              </button>
            </Fragment>
          ))}
        </div>
        <Link
          href="/clinical-trial-mode"
          className="mt-1 text-left text-[13px] font-medium leading-[1.4] text-text-tertiary underline decoration-slate-400 underline-offset-2 hover:text-text-primary"
        >
          Participating in a clinical study? Add study medication →
        </Link>
      </section>
    </aside>
  );
}

function DoseRow({
  dose,
  checked,
  onToggle,
}: {
  dose: DosePlanItem;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      className={`grid min-h-[56px] grid-cols-[20px_minmax(135px,1fr)_minmax(150px,1.25fr)] items-center gap-2 rounded-[13px] px-3 py-2.5 ${
        dose.completed
          ? "bg-surface-muted text-slate-400"
          : dose.emphasized
            ? "border border-border bg-white"
            : "bg-white"
      }`}
    >
      <button
        type="button"
        aria-label={`${checked ? "Unmark" : "Mark"} ${dose.name} taken`}
        aria-pressed={checked}
        onClick={onToggle}
        className={`grid size-4 place-items-center rounded-[5px] border ${
          checked
            ? "border-[#70cda7] bg-[#70cda7] text-white"
            : "border-slate-300 bg-white"
        }`}
      >
        {checked && <Check size={11} strokeWidth={3} />}
      </button>
      <div className="min-w-0">
        <p
          className={`truncate text-[14px] font-semibold ${
            dose.study
              ? "text-[#7165ee]"
              : dose.completed
                ? "text-slate-400"
                : "text-text-primary"
          }`}
        >
          {dose.name} {dose.dose}
          {dose.study && (
            <span className="ml-2 rounded-[4px] bg-[#f0efff] px-1.5 py-0.5 text-[12px] font-bold uppercase text-[#7165ee]">
              Study
            </span>
          )}
          {dose.next && (
            <span className="ml-2 rounded-[4px] bg-emerald-50 px-1.5 py-0.5 text-[12px] font-bold uppercase text-emerald-500">
              Next
            </span>
          )}
        </p>
        <p className="mt-0.5 text-[12px] text-text-tertiary">{dose.time}</p>
      </div>
      <div className="text-[12px] leading-[1.35] text-text-tertiary">
        <p>{dose.instruction}</p>
        {dose.detail && (
          <p>
            Keeps 4h separation from Levothyroxine ·{" "}
            <button
              type="button"
              className="font-semibold text-text-primary underline"
            >
              Why?
            </button>
          </p>
        )}
      </div>
    </div>
  );
}

function MedicationPlan({
  clinicalTrialMode,
}: {
  clinicalTrialMode: boolean;
}) {
  const plan = clinicalTrialMode ? clinicalDosePlan : dosePlan;
  const totalDoses = clinicalTrialMode ? 10 : 8;
  const nextDoseId = clinicalTrialMode
    ? "study-afternoon"
    : "amoxicillin-afternoon";
  const [taken, setTaken] = useState(() =>
    [
      ...plan.filter((dose) => dose.completed).map((dose) => dose.id),
      "earlier-dose",
    ],
  );
  const periods: DosePlanItem["period"][] = ["Morning", "Afternoon", "Evening"];
  const nextTaken = taken.includes(nextDoseId);
  const [reportOpen, setReportOpen] = useState(false);
  const [reported, setReported] = useState(false);

  function toggle(id: string) {
    setTaken((current) =>
      current.includes(id)
        ? current.filter((doseId) => doseId !== id)
        : [...current, id],
    );
  }

  return (
    <section className="rounded-card bg-white p-5 shadow-card">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-[16px] font-extrabold tracking-[-0.02em]">
            Today&apos;s Medication Plan
          </h2>
          <p className="mt-1 text-[13px] text-text-tertiary">
            Tue, Jan 30 · {taken.length} of {totalDoses} doses taken
          </p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-pill bg-surface-muted px-3 py-1.5 text-[13px] font-semibold text-text-secondary">
          <span className="size-2 rounded-full bg-emerald-500" />
          {taken.length} of {totalDoses}
        </span>
      </div>

      <div className="mt-4 flex items-center gap-3 rounded-[14px] border border-border bg-surface-muted p-3">
        <span
          className={`grid size-10 shrink-0 place-items-center rounded-[11px] text-white ${
            clinicalTrialMode ? "bg-[#7165ee]" : "bg-[#65c9a0]"
          }`}
        >
          <Link2 size={19} className="-rotate-45" />
        </span>
        <p className="min-w-0 flex-1 text-[14px] font-semibold text-text-primary">
          {clinicalTrialMode
            ? "Next: Study Drug XR-7742 200mg · 12:00 PM · in 1h 2m"
            : "Next: Amoxicillin 500mg · 2:00 PM · in 2h 18m"}
        </p>
        <button
          type="button"
          onClick={() => toggle(nextDoseId)}
          className={`h-8 shrink-0 rounded-[9px] px-4 text-[13px] font-bold ${
            nextTaken
              ? "bg-emerald-500 text-white"
              : "bg-brand-navy text-white hover:bg-[#292943]"
          }`}
        >
          {nextTaken ? "Taken" : "Mark taken"}
        </button>
      </div>

      <div className="mt-4 flex items-center justify-between rounded-[13px] border border-border px-3 py-2.5">
        <div>
          <p className="text-[14px] font-semibold text-text-primary">
            Schedule optimized
          </p>
          <p className="mt-0.5 text-[12px] text-text-tertiary">
            1 interaction still needs your review
          </p>
        </div>
        <button
          type="button"
          className="inline-flex h-8 items-center gap-1.5 rounded-[9px] border border-border bg-white px-3 text-[13px] font-bold text-text-primary hover:bg-surface-muted"
        >
          <Sparkles size={14} className="text-brand-coral" /> View details
        </button>
      </div>

      <button
        type="button"
        className="mt-4 text-[13px] font-semibold text-text-tertiary underline decoration-slate-300 underline-offset-2"
      >
        How MedGuide builds your plan →
      </button>

      {clinicalTrialMode && (
        <div className="mt-4 rounded-[13px] border border-border">
          <button
            type="button"
            aria-expanded={reportOpen}
            onClick={() => setReportOpen((open) => !open)}
            className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-surface-muted"
          >
            <span className="grid size-8 place-items-center rounded-full bg-surface-muted text-brand-navy">
              <Link2 size={15} className="-rotate-45" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[13px] font-semibold text-text-primary">
                Took something not on your list?
              </span>
              <span className="block text-[12px] text-text-tertiary">
                {reported
                  ? "Medication reported to your study team"
                  : "Report a medication, supplement, or OTC drug"}
              </span>
            </span>
            {reported ? (
              <Check size={16} className="text-emerald-500" />
            ) : (
              <ChevronRight
                size={16}
                className={`text-slate-400 transition-transform ${
                  reportOpen ? "rotate-90" : ""
                }`}
              />
            )}
          </button>
          {reportOpen && !reported && (
            <form
              className="flex gap-2 border-t border-border p-3"
              onSubmit={(event) => {
                event.preventDefault();
                setReported(true);
                setReportOpen(false);
              }}
            >
              <label htmlFor="unlisted-medication" className="sr-only">
                Medication or supplement
              </label>
              <input
                id="unlisted-medication"
                required
                placeholder="e.g. Ibuprofen 200mg"
                className="h-9 min-w-0 flex-1 rounded-[9px] border border-border px-3 text-[13px] outline-none focus:border-brand-navy"
              />
              <button
                type="submit"
                className="rounded-[9px] bg-brand-navy px-3 text-[12px] font-bold text-white"
              >
                Report
              </button>
            </form>
          )}
        </div>
      )}

      <div className="mt-3 space-y-3">
        {periods.map((period) => (
          <section key={period}>
            <h3 className="mb-2 text-[12px] font-extrabold uppercase tracking-[0.03em] text-text-tertiary">
              {period}
            </h3>
            <div className="space-y-2">
              {plan
                .filter((dose) => dose.period === period)
                .map((dose) => (
                  <DoseRow
                    key={dose.id}
                    dose={dose}
                    checked={taken.includes(dose.id)}
                    onToggle={() => toggle(dose.id)}
                  />
                ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}

const rules = [
  {
    text: "Iron Supplement ↔ Levothyroxine - Too close together. Separate by 4+ hours.",
    tag: "Timing",
    actions: ["Why?", "Fix schedule"],
  },
  {
    text: "Warfarin ↔ Amoxicillin - May increase bleeding risk. Monitor INR.",
    tag: "Interaction",
    actions: ["Source", "Review details"],
  },
  {
    text: "Warfarin - Grapefruit interaction. Avoid during treatment.",
    tag: "Food",
    actions: ["Source", "Learn more"],
  },
];

const clinicalRules = [
  {
    text: "Do not take NSAIDs during study period. Contact study team if needed.",
    tag: "Protocol",
    actions: ["Source", "Learn more"],
    protocol: true,
  },
  {
    text: "Iron Supplement ↔ Levothyroxine - Too close together. Separate by 4+ hours.",
    tag: "Timing",
    actions: ["Why?", "Fix schedule"],
  },
  {
    text: "Warfarin ↔ Amoxicillin - May increase bleeding risk. Monitor INR.",
    tag: "Interaction",
    actions: ["Source", "Review details"],
  },
  {
    text: "Ibuprofen was flagged - This medication may conflict with your study instructions.",
    tag: "Concomitant med",
    actions: ["Contact study team"],
  },
];

function RulesPanel({
  clinicalTrialMode,
}: {
  clinicalTrialMode: boolean;
}) {
  const displayedRules = clinicalTrialMode ? clinicalRules : rules;
  const [selectedRule, setSelectedRule] = useState<string | null>(null);

  return (
    <section className="rounded-card bg-white p-4 shadow-card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-[14px] font-extrabold">Rules to Review</h2>
        <span className="rounded-pill bg-[#fff0ec] px-2.5 py-1 text-[12px] font-bold text-brand-coral">
          {displayedRules.length}
        </span>
      </div>
      <div className="space-y-2">
        {displayedRules.map((rule) => (
          <article
            key={rule.text}
            className="rounded-[13px] bg-surface-muted px-3 py-3"
          >
            <div className="flex items-start gap-2">
              <Siren
                size={15}
                className="mt-0.5 shrink-0 text-orange-500"
                aria-hidden="true"
              />
              <p className="text-[13px] font-semibold leading-[1.4] text-text-primary">
                {rule.text}
              </p>
            </div>
            <div className="mt-2 flex items-center justify-between gap-2">
              <span
                className={`rounded-pill px-2 py-1 text-[12px] font-bold uppercase ${
                  "protocol" in rule && rule.protocol
                    ? "bg-[#f0efff] text-[#7165ee]"
                    : "bg-[#fff0ec] text-orange-500"
                }`}
              >
                {rule.tag}
              </span>
              <div className="flex items-center gap-2">
                {rule.actions.map((action, index) => (
                  <button
                    key={action}
                    type="button"
                    onClick={() =>
                      setSelectedRule((selected) =>
                        selected === rule.text ? null : rule.text,
                      )
                    }
                    className={
                      index === rule.actions.length - 1
                        ? rule.tag === "Concomitant med"
                          ? "rounded-pill bg-brand-coral px-3 py-1.5 text-[12px] font-bold text-white"
                          : "rounded-pill bg-white px-3 py-1.5 text-[12px] font-bold text-text-primary shadow-sm"
                        : "text-[12px] font-semibold text-text-primary underline"
                    }
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
            {selectedRule === rule.text && (
              <p
                role="status"
                className="mt-2 rounded-[8px] bg-white px-2.5 py-2 text-[12px] leading-[1.4] text-text-secondary"
              >
                {rule.tag === "Protocol"
                  ? "This requirement comes from the BEACON-3 study protocol. Contact the study team before taking an NSAID."
                  : rule.tag === "Concomitant med"
                    ? "Your study team has been notified in this prototype."
                    : "This recommendation is based on the medications and timing currently saved in your plan."}
              </p>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

function InstructionsPanel({
  clinicalTrialMode,
}: {
  clinicalTrialMode: boolean;
}) {
  const instructions = clinicalTrialMode
    ? clinicalMedicationInstructions
    : medicationInstructions;

  return (
    <section className="rounded-card bg-white p-4 shadow-card">
      <h2 className="mb-3 text-[14px] font-extrabold">How to Take Them</h2>
      <div className="divide-y divide-border">
        {instructions.map((medication) => (
          <div
            key={medication.name}
            className="flex min-h-12 items-center justify-between gap-3 py-3"
          >
            <p
              className={`text-[13px] font-semibold ${
                "study" in medication && medication.study
                  ? "text-[#7165ee]"
                  : "text-text-primary"
              }`}
            >
              {medication.name}
            </p>
            <div className="flex flex-wrap justify-end gap-1.5">
              {medication.tags.map((tag) => (
                <span
                  key={tag}
                  className={`rounded-pill px-2.5 py-1 text-[12px] font-medium ${
                    "study" in medication && medication.study
                      ? "bg-[#f0efff] text-[#7165ee]"
                      : "bg-surface-muted text-text-secondary"
                  }`}
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function Dashboard({
  clinicalTrialMode = false,
}: {
  clinicalTrialMode?: boolean;
}) {
  const [addOpen, setAddOpen] = useState(false);

  return (
    <>
      <main className="mx-auto grid w-full max-w-[1440px] flex-1 grid-cols-1 items-start gap-6 px-5 py-8 sm:px-8 lg:grid-cols-[320px_minmax(0,1fr)] lg:px-10 xl:grid-cols-[320px_560px_minmax(360px,1fr)]">
        <MedicineRail
          onAdd={() => setAddOpen(true)}
          clinicalTrialMode={clinicalTrialMode}
        />
        <MedicationPlan clinicalTrialMode={clinicalTrialMode} />
        <div className="grid content-start gap-5 lg:col-start-2 xl:col-start-auto">
          <RulesPanel clinicalTrialMode={clinicalTrialMode} />
          <InstructionsPanel clinicalTrialMode={clinicalTrialMode} />
        </div>
      </main>

      {addOpen && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-brand-navy/35 p-4 backdrop-blur-[2px]"
          onMouseDown={() => setAddOpen(false)}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-title"
            onMouseDown={(event) => event.stopPropagation()}
            className="w-full max-w-md rounded-card bg-white p-6 shadow-[0_24px_70px_rgba(15,23,42,0.2)]"
          >
            <div className="flex items-start justify-between">
              <div>
                <h2 id="add-title" className="text-[18px] font-extrabold">
                  Add medication
                </h2>
                <p className="mt-1 text-[14px] text-text-secondary">
                  Search by brand or generic medication name.
                </p>
              </div>
              <button
                type="button"
                aria-label="Close"
                onClick={() => setAddOpen(false)}
                className="grid size-9 place-items-center rounded-[10px] bg-surface-muted"
              >
                <X size={17} />
              </button>
            </div>
            <label
              htmlFor="medication-name"
              className="mt-6 block text-[14px] font-semibold"
            >
              Medication name
            </label>
            <input
              id="medication-name"
              autoFocus
              placeholder="e.g. Ibuprofen"
              className="mt-2 h-11 w-full rounded-[12px] border border-border px-3.5 text-[13px] outline-none focus:border-brand-navy focus:ring-2 focus:ring-brand-navy/10"
            />
            <button
              type="button"
              onClick={() => setAddOpen(false)}
              className="mt-5 inline-flex h-10 w-full items-center justify-center gap-2 rounded-[12px] bg-brand-coral text-[12px] font-bold text-white"
            >
              Continue <ArrowRight size={15} />
            </button>
          </section>
        </div>
      )}
    </>
  );
}
