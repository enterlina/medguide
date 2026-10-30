import { ExternalLink, Globe2, PlayCircle, Trophy } from "lucide-react";

const projectLinks = [
  {
    label: "Live demo",
    href: "https://medguide-orcin.vercel.app/evidence-lens",
    icon: Globe2,
  },
  {
    label: "Hackathon project",
    href: "https://devpost.com/software/medguide-ai-medication-supplement-intelligence",
    icon: Trophy,
  },
  {
    label: "Demo video",
    href: "https://youtu.be/zyctKYUrL9U?si=583ddMtDRrbLeXQB",
    icon: PlayCircle,
  },
] as const;

export function ProjectLinks({ className = "" }: { className?: string }) {
  return (
    <nav aria-label="MedGuide project links" className={`flex flex-wrap justify-center gap-2 ${className}`}>
      {projectLinks.map(({ label, href, icon: Icon }) => (
        <a
          key={label}
          href={href}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2.5 text-[12px] font-bold text-brand-navy shadow-sm transition hover:-translate-y-0.5 hover:text-brand-coral hover:shadow-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-coral"
        >
          <Icon size={16} aria-hidden="true" />
          {label}
          <ExternalLink size={12} className="text-slate-400" aria-hidden="true" />
        </a>
      ))}
    </nav>
  );
}
