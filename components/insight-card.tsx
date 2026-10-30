import { CheckCircle2, ChevronRight, Clock3, Utensils } from "lucide-react";
import type { Insight } from "@/types/medication";

const styles = {
  safe: {
    icon: CheckCircle2,
    iconClass: "bg-emerald-50 text-emerald-500",
    label: "Safe",
    labelClass: "bg-emerald-50 text-emerald-600",
  },
  timing: {
    icon: Clock3,
    iconClass: "bg-orange-50 text-orange-500",
    label: "Timing",
    labelClass: "bg-orange-50 text-orange-600",
  },
  food: {
    icon: Utensils,
    iconClass: "bg-[#FFF7E8] text-[#D78A16]",
    label: "Food",
    labelClass: "bg-[#FFF7E8] text-[#A8660B]",
  },
};

export function InsightCard({ insight }: { insight: Insight }) {
  const style = styles[insight.kind];
  const Icon = style.icon;

  return (
    <button
      type="button"
      className="group flex w-full items-start gap-3 rounded-[16px] border border-border bg-white p-4 text-left transition-colors hover:border-slate-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-navy"
    >
      <span
        className={`grid size-9 shrink-0 place-items-center rounded-[12px] ${style.iconClass}`}
      >
        <Icon size={17} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-2">
          <span className="text-[12px] font-semibold text-text-primary">
            {insight.title}
          </span>
          <span
            className={`rounded-pill px-2 py-1 text-[12px] font-bold uppercase tracking-[0.06em] ${style.labelClass}`}
          >
            {style.label}
          </span>
        </span>
        <span className="mt-1.5 block text-[14px] leading-[1.55] text-text-secondary">
          {insight.description}
        </span>
      </span>
      <ChevronRight
        size={16}
        className="mt-2 shrink-0 text-text-tertiary transition-transform group-hover:translate-x-0.5"
      />
    </button>
  );
}
