import type { LucideIcon } from "lucide-react";

interface SectionPlaceholderProps {
  title: string;
  description: string;
  icon: LucideIcon;
}

export function SectionPlaceholder({
  title,
  description,
  icon: Icon,
}: SectionPlaceholderProps) {
  return (
    <main className="mx-auto w-full max-w-[1440px] flex-1 px-5 py-10 sm:px-8 lg:px-10">
      <div className="rounded-card border border-border bg-white p-8 shadow-card">
        <span className="grid size-11 place-items-center rounded-[14px] bg-surface-muted text-brand-navy">
          <Icon size={21} />
        </span>
        <h1 className="mt-6 text-[26px] font-extrabold tracking-[-0.035em] text-text-primary">
          {title}
        </h1>
        <p className="mt-2 max-w-xl text-[13px] leading-5 text-text-secondary">
          {description}
        </p>
      </div>
    </main>
  );
}
