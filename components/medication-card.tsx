import { Check, Clock3, MoreHorizontal, Pill } from "lucide-react";
import type { Medication } from "@/types/medication";

const medicationColor = {
  blue: "bg-[#E8F1FF] text-[#3B6EC9]",
  violet: "bg-[#F0EAFE] text-[#7656B7]",
  amber: "bg-[#FFF2D9] text-[#B97816]",
};

interface MedicationCardProps {
  medication: Medication;
  taken: boolean;
  onMarkTaken: () => void;
}

export function MedicationCard({
  medication,
  taken,
  onMarkTaken,
}: MedicationCardProps) {
  return (
    <article className="rounded-card border border-border bg-white p-4 shadow-card sm:p-5">
      <div className="flex items-start gap-3">
        <span
          className={`grid size-11 shrink-0 place-items-center rounded-[14px] ${medicationColor[medication.color]}`}
        >
          <Pill size={21} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="text-[14px] font-semibold text-text-primary">
                {medication.name}
              </h3>
              <p className="mt-0.5 text-[14px] text-text-tertiary">
                {medication.dosage} · {medication.form}
              </p>
            </div>
            <button
              type="button"
              aria-label={`More options for ${medication.name}`}
              className="grid size-8 shrink-0 place-items-center rounded-[10px] text-text-tertiary hover:bg-surface-muted hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-navy"
            >
              <MoreHorizontal size={18} />
            </button>
          </div>
          <div className="mt-4 flex items-center gap-2 text-[14px] text-text-secondary">
            <Clock3 size={14} className="text-text-tertiary" />
            <span>{medication.frequency}</span>
          </div>
          <p className="mt-1.5 text-[14px] text-text-tertiary">
            {medication.instruction}
          </p>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-border pt-4">
        <div>
          <span className="text-[13px] font-semibold uppercase tracking-[0.08em] text-text-tertiary">
            Next dose
          </span>
          <p className="mt-0.5 text-[13px] font-bold text-text-primary">
            {medication.nextDose}{" "}
            <span className="text-[13px] font-semibold text-text-tertiary">
              {medication.nextDosePeriod}
            </span>
          </p>
        </div>
        <button
          type="button"
          onClick={onMarkTaken}
          className={`inline-flex h-9 items-center gap-1.5 rounded-[10px] px-3 text-[14px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 ${
            taken
              ? "bg-emerald-50 text-emerald-600"
              : "bg-surface-muted text-text-secondary hover:bg-emerald-50 hover:text-emerald-600"
          }`}
        >
          <Check size={14} />
          {taken ? "Taken" : "Mark taken"}
        </button>
      </div>
    </article>
  );
}
