"use client";

import {
  AlertTriangle,
  BellDot,
  Check,
  ChevronDown,
  ChevronUp,
  Clock3,
  ExternalLink,
  FlaskConical,
  Info,
  Pin,
  PinOff,
  Pill,
  RefreshCw,
  Scale,
  Search,
  SearchX,
  ShieldAlert,
  X,
} from "lucide-react";
import { FormEvent, Fragment, useEffect, useState } from "react";
import {
  medicationEvidence,
  type EvidenceRecord,
  type MedicationEvidence,
} from "@/data/evidence-lens";

type NewRecord = { pmid: string; title: string; journal: string; publishedAt: string | null; url: string };
type TrialChange = { id: string; url: string; changes: string[] };

type UpdateState = {
  lastUpdatedAt: string;
  lastCheckedAt: string;
  status: "completed" | "partial";
  newRecords: NewRecord[];
  newPublicationIds: string[];
  trialChanges: TrialChange[];
  sourceErrors: string[];
};

type CitationState = {
  question: string;
  answer: string;
  automated: boolean;
  sources: Array<{ citation: number; id: string; title: string; url: string; identifiers: string; applicability: string }>;
};

type CorpusStudyGroup = {
  name: string;
  tags: string[];
  updatedAt: string | null;
  articles: Array<{
    id: string;
    title: string;
    sourceUrl: string;
    pmid: string;
    journal: string | null;
    publishedYear: string | null;
    publishedAt: string | null;
    studyType: string;
    participants: string | null;
    result: string;
    conflicts: string | null;
    funding: string | null;
    citations: number | null;
    twoYearMeanCitedness: number | null;
    screening?: {
      decision: "include" | "include_as_indirect";
      confidence: "high" | "medium" | "low";
      reason: string;
    };
  }>;
};

type StatusFilter = EvidenceRecord["status"] | "all";

const UPDATES_KEY = "medguide-evidence-updates-v2";
const CARDS_KEY = "medguide-evidence-cards";
const COMPARE_KEY = "medguide-evidence-compare";
const PINNED_STUDIES_KEY = "medguide.evidence.pinned-study-groups";

const levelStyle = {
  limited: "border-amber-200 bg-amber-50 text-amber-800",
  moderate: "border-blue-200 bg-blue-50 text-blue-800",
  high: "border-emerald-200 bg-emerald-50 text-emerald-800",
};

const statusStyle: Record<EvidenceRecord["status"], string> = {
  supporting: "bg-emerald-50 text-emerald-800",
  contradicting: "bg-rose-50 text-rose-800",
  no_significant_effect: "bg-slate-100 text-slate-700",
  uncertain: "bg-amber-50 text-amber-800",
  not_applicable: "bg-slate-100 text-slate-600",
  registry_results_missing: "bg-violet-50 text-violet-800",
};

const overlapNotice = {
  match: { label: "Match", text: "The manufacturer also sponsored this study. This is a potential conflict of interest, not proof that the findings are unreliable." },
  no_match: { label: "No overlap", text: "No manufacturer–sponsor overlap was identified in the reviewed records." },
  not_assessed: { label: "Not assessed", text: "Manufacturer–sponsor overlap has not been assessed for this card. Do not read the absence of a warning as independence." },
};

function formatDate(value: string, withTime = true) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    ...(withTime ? { hour: "numeric", minute: "2-digit" } : {}),
  }).format(new Date(value));
}

function readStorage<T>(key: string, fallback: T): T {
  try {
    const stored = window.localStorage.getItem(key);
    return stored ? (JSON.parse(stored) as T) : fallback;
  } catch {
    return fallback;
  }
}

function findMedications(query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return [];
  const exactMatches = medicationEvidence.filter((medication) =>
    medication.name.toLowerCase() === normalized || medication.aliases.includes(normalized)
  );
  if (exactMatches.length) return exactMatches;
  return medicationEvidence.filter((medication) =>
    normalized.includes(medication.name.toLowerCase()) ||
    medication.aliases.some((alias) => normalized.includes(alias)) ||
    medication.name.toLowerCase().includes(normalized) ||
    medication.aliases.some((alias) => alias.includes(normalized))
  );
}

function queryParts(query: string | null, matches: MedicationEvidence[]) {
  if (!query) return [];
  const normalized = query.toLowerCase();
  const parts = matches.map((medication) => medication.name);
  if (/sleep|insomnia/.test(normalized)) parts.push("Sleep & insomnia");
  if (/anxiety|stress/.test(normalized)) parts.push("Anxiety & stress");
  if (/muscle|cramp/.test(normalized)) parts.push("Muscle function");
  if (/dose|dosage|how much/.test(normalized)) parts.push("Dose");
  if (/safe|safety|side effect/.test(normalized)) parts.push("Safety");
  return [...new Set(parts)];
}

function SpecificationSection({
  title,
  rows,
}: {
  title: string;
  rows: Array<{ label: string; value: React.ReactNode }>;
}) {
  return (
    <section className="border-t border-slate-200 pt-7 first:border-t-0 first:pt-0">
      <h3 className="mb-3 text-xl font-extrabold tracking-[-0.02em] text-slate-950">
        {title}
      </h3>
      <dl>
        {rows.map((row) => (
          <div key={row.label} className="grid gap-1 border-b border-slate-200 py-3.5 last:border-0 sm:grid-cols-[minmax(180px,34%)_1fr] sm:gap-8">
            <dt className="text-sm font-medium text-slate-500">{row.label}</dt>
            <dd className="text-[15px] font-semibold leading-6 text-slate-900">{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function SourceLink({ href, children }: { href: string; children: React.ReactNode }) {
  return <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-blue-700 hover:underline">{children}<ExternalLink size={12} /></a>;
}

function StudiesTable({ records }: { records: EvidenceRecord[] }) {
  if (!records.length) return null;
  return <div className="mt-5 overflow-x-auto rounded-[14px] border border-border">
    <table className="w-full min-w-[1080px] border-collapse text-left">
      <thead className="bg-slate-50 text-[11px] font-extrabold uppercase tracking-[0.05em] text-text-tertiary">
        <tr><th className="px-4 py-3">Study</th><th className="px-3 py-3">Year</th><th className="px-3 py-3">Design</th><th className="px-3 py-3">Participants</th><th className="px-3 py-3">Form</th><th className="px-3 py-3">Result &amp; relevance</th><th className="px-3 py-3">Journal</th><th className="px-3 py-3">Conflicts</th></tr>
      </thead>
      <tbody className="divide-y divide-border bg-white text-[12px] text-text-secondary">
        {records.map((record) => <tr key={record.id} className="align-top hover:bg-slate-50/60">
          <td className="max-w-[260px] px-4 py-4"><SourceLink href={record.sourceUrl}>{record.title}</SourceLink><p className="mt-1 text-[11px] text-text-tertiary">{[record.journal, record.identifiers].filter(Boolean).join(" · ")}</p></td>
          <td className="px-3 py-4 font-bold text-text-primary">{record.publishedYear ?? "Not available"}</td>
          <td className="max-w-[160px] px-3 py-4">{record.studyType ?? "Not assessed"}</td>
          <td className="max-w-[180px] px-3 py-4">{record.population}</td>
          <td className="max-w-[180px] px-3 py-4">{record.form}</td>
          <td className="max-w-[220px] px-3 py-4"><span className={`inline-flex rounded-pill px-2 py-1 text-[9px] font-bold ${statusStyle[record.status]}`}>{record.statusLabel}</span><p className="mt-2 line-clamp-3 leading-5">{record.passage}</p></td>
          <td className="px-3 py-4"><p className="font-semibold text-text-primary">{record.journal ?? (record.source === "ClinicalTrials.gov" ? "Trial registry" : "Not available")}</p><span className="mt-1 inline-flex rounded-pill bg-surface-muted px-2 py-1 text-[9px] font-bold text-text-tertiary">{record.journalRating ?? "Not assessed"}</span></td>
          <td className="max-w-[170px] px-3 py-4"><span className="inline-flex rounded-pill bg-surface-muted px-2 py-1 text-[9px] font-bold text-text-secondary">{record.conflictOfInterest ?? "Not assessed"}</span></td>
        </tr>)}
      </tbody>
    </table>
  </div>;
}

function ExpandableResult({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const conclusionMatch = text.match(/\bconclusions?:\s*([\s\S]*)/i);
  const rawFindings = (conclusionMatch ? text.slice(0, conclusionMatch.index) : text).replace(/^\s*results?:\s*/i, "").trim();
  const rawConclusion = conclusionMatch?.[1]?.trim() ?? "";
  const simplify = (value: string) => value
    .replace(/\s*\([^)]*(?:95%|\bCI\b|\bSMD\b|\bMD\b|\bRR\b|\bOR\b|\bHR\b|\bP\s*[<=>]|\bI\s*[²2]|heterogeneity)[^)]*\)/gi, "")
    .replace(/\bTC\b/g, "total cholesterol")
    .replace(/\bLDL-C\b/g, "LDL (‘bad’) cholesterol")
    .replace(/\bHDL-C\b/g, "HDL (‘good’) cholesterol")
    .replace(/\bTG\b/g, "triglycerides")
    .replace(/\bApo B1?\b/gi, "apolipoprotein B")
    .replace(/\bApo A1\b/gi, "apolipoprotein A1")
    .replace(/\bsignificantly decreased\b/gi, "was lower")
    .replace(/\bdid not alter\b/gi, "did not clearly change")
    .replace(/\s+([,.;:])/g, "$1")
    .replace(/\s{2,}/g, " ")
    .trim();
  const simplifiedFindings = simplify(rawFindings);
  const findingSentences = simplifiedFindings.split(/(?<=[.!?])\s+(?=[A-Z])/).filter(Boolean).slice(0, 3);
  const bottomLine = simplify(rawConclusion || findingSentences.at(-1) || rawFindings);
  const displayedFindings = rawConclusion ? findingSentences : findingSentences.slice(0, -1);

  return <div className="space-y-3 text-[12px]">
    <div className="rounded-[10px] bg-blue-50 px-3 py-2.5">
      <p className="text-[10px] font-extrabold uppercase tracking-[0.06em] text-blue-700">Bottom line</p>
      <p className="mt-1 font-semibold leading-5 text-slate-800">{bottomLine}</p>
    </div>
    {displayedFindings.length > 0 && <div>
      <p className="text-[10px] font-extrabold uppercase tracking-[0.06em] text-text-tertiary">Key findings</p>
      <ul className="mt-1.5 space-y-1.5">{displayedFindings.map((finding, index) => <li key={`${finding}-${index}`} className="flex gap-2 leading-5"><span className="mt-[7px] size-1.5 shrink-0 rounded-full bg-brand-coral" /><span>{finding}</span></li>)}</ul>
    </div>}
    <button type="button" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded} className="inline-flex items-center gap-1 text-[11px] font-bold text-blue-700 hover:underline">{expanded ? "Hide technical details" : "View technical details"}{expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}</button>
    {expanded && <div className="rounded-[10px] border border-border bg-slate-50 px-3 py-2.5"><p className="text-[10px] font-extrabold uppercase tracking-[0.06em] text-text-tertiary">Original study wording</p><p className="mt-1 whitespace-pre-wrap leading-5 text-text-secondary">{text}</p></div>}
  </div>;
}

function CorpusStudiesCard({ group, pinned, onTogglePin }: { group: CorpusStudyGroup; pinned: boolean; onTogglePin: () => void }) {
  return <article className="overflow-hidden rounded-card border border-border bg-white p-5 shadow-card sm:p-6">
    <div className="flex items-start justify-between gap-4"><div><h2 className="text-xl font-extrabold tracking-[-0.03em] text-brand-navy">{group.name}</h2><div className="mt-2 flex flex-wrap gap-2"><span className="rounded-pill bg-surface-muted px-2.5 py-1 text-[10px] font-bold text-text-secondary">{group.articles.length} studies</span>{group.tags.map((tag) => <span key={tag} className="rounded-pill bg-blue-50 px-2.5 py-1 text-[10px] font-bold text-blue-700">{tag}</span>)}</div></div><button type="button" onClick={onTogglePin} aria-pressed={pinned} aria-label={pinned ? `Unpin ${group.name}` : `Pin ${group.name}`} className={`inline-flex size-9 shrink-0 items-center justify-center rounded-full transition ${pinned ? "bg-brand-coral text-white" : "bg-surface-muted text-slate-500 hover:text-brand-coral"}`}>{pinned ? <PinOff size={16} /> : <Pin size={16} />}</button></div>
    <div className="mt-4 overflow-x-auto rounded-[14px] border border-border">
      <table className="w-full min-w-[1040px] table-fixed border-collapse text-left">
        <thead className="bg-slate-50 text-[11px] font-extrabold uppercase tracking-[0.05em] text-text-tertiary"><tr><th className="w-[22%] px-4 py-3">Study</th><th className="w-[5%] px-2 py-3">Year</th><th className="w-[11%] px-2 py-3">Design</th><th className="w-[8%] px-2 py-3">Participants</th><th className="w-[40%] px-2 py-3">Result</th><th className="w-[14%] px-2 py-3">Journal metrics</th></tr></thead>
        <tbody className="divide-y divide-border bg-white text-[12px] text-text-secondary">{group.articles.map((article) => <tr key={article.id} className="align-top hover:bg-slate-50/60">
          <td className="max-w-[260px] px-4 py-4"><a href={article.sourceUrl} target="_blank" rel="noreferrer" className="font-semibold text-blue-700 hover:underline">{article.title}</a><p className="mt-1 text-[11px] text-text-tertiary">PMID {article.pmid}</p></td>
          <td className="px-2 py-4 font-bold text-text-primary">{article.publishedYear ?? "Not available"}</td>
          <td className="px-2 py-4">{article.studyType}</td>
          <td className="px-2 py-4">{article.participants ? `${article.participants} participants` : <span className="rounded-pill bg-surface-muted px-2 py-1 text-[10px] font-bold text-text-tertiary">Not extracted</span>}</td>
          <td className="px-2 py-4"><ExpandableResult text={article.result} /></td>
          <td className="px-2 py-4"><p className="font-semibold text-text-primary">{article.journal ?? "Journal not available"}</p><div className="mt-2 flex flex-wrap gap-1.5">{article.citations !== null && <span className="rounded-pill bg-blue-50 px-2 py-1 text-[10px] font-bold text-blue-700">{article.citations} citations</span>}{article.twoYearMeanCitedness !== null && <span className="rounded-pill bg-violet-50 px-2 py-1 text-[10px] font-bold text-violet-700">2-year citation rate {article.twoYearMeanCitedness.toFixed(1)}</span>}{article.citations === null && article.twoYearMeanCitedness === null && <span className="rounded-pill bg-surface-muted px-2 py-1 text-[10px] font-bold text-text-tertiary">Not available</span>}</div></td>
        </tr>)}</tbody>
      </table>
    </div>
    {group.updatedAt && <span className="mt-3 inline-flex items-center gap-1.5 text-[10px] font-semibold text-text-tertiary"><Clock3 size={11} /> Studies updated {formatDate(group.updatedAt, false)}</span>}
  </article>;
}

function CompactEvidenceCard({
  medication, records, update, onClose,
}: {
  medication: MedicationEvidence;
  records: EvidenceRecord[];
  isExpanded: boolean;
  isCompared: boolean;
  update?: UpdateState;
  checking: boolean;
  draft?: CitationState;
  question: string;
  drafting: boolean;
  onClose: () => void;
  onCompare: () => void;
  onToggle: () => void;
  onCheckUpdates: () => void;
  onQuestionChange: (value: string) => void;
  onGenerateDraft: () => void;
}) {
  const lastUpdatedAt = update?.lastUpdatedAt ?? medication.liveSources.lastUpdatedAt;
  return <article className="overflow-hidden rounded-card border border-border bg-white shadow-card">
    <div className="p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-xl font-extrabold tracking-[-0.03em] text-brand-navy">{medication.name}</h2><p className="mt-1 text-[12px] text-text-tertiary">{medication.category} · {medication.route}</p><div className="mt-3 flex flex-wrap gap-2">{medication.ingredients.map((ingredient) => <span key={ingredient} className="rounded-pill bg-surface-muted px-2.5 py-1 text-[10px] font-bold text-text-secondary">{ingredient}</span>)}{medication.scope && <span className="rounded-pill bg-blue-50 px-2.5 py-1 text-[10px] font-bold text-blue-700">{medication.scope}</span>}<span className="rounded-pill bg-surface-muted px-2.5 py-1 text-[10px] font-bold text-text-secondary">{records.length} stud{records.length === 1 ? "y" : "ies"}</span></div></div><button type="button" aria-label={`Close ${medication.name} card`} onClick={onClose} className="grid size-8 place-items-center rounded-[10px] text-slate-400 hover:bg-surface-muted"><X size={15} /></button></div>
      <StudiesTable records={records} />
      <span className="mt-3 inline-flex items-center gap-1.5 text-[10px] font-semibold text-text-tertiary"><Clock3 size={11} /> Studies updated {formatDate(lastUpdatedAt, false)}</span>
    </div>
  </article>;
}

function QuestionEvidenceCard({ medication }: { medication: MedicationEvidence }) {
  const card = medication.questionCard;
  if (!card) return null;
  return (
    <article className="rounded-[30px] border border-slate-300 bg-white p-6 shadow-card sm:p-9">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700"><FlaskConical size={14} /> Research answer</span>
        <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-700">Evidence preview</span>
      </div>
      <h2 className="mt-6 max-w-4xl text-2xl font-extrabold tracking-[-0.035em] text-slate-950 sm:text-3xl">{card.question}</h2>
      <p className="mt-3 text-sm font-medium text-slate-500">Ingredient: {card.ingredient} <span aria-hidden="true">·</span> Outcome: {card.outcome}</p>

      <section className="mt-8 rounded-2xl bg-slate-50 p-5 sm:p-6">
        <h3 className="flex items-center gap-2 text-base font-extrabold text-slate-950"><Info size={17} className="text-slate-500" /> Evidence summary</h3>
        <div className="mt-3 max-w-4xl space-y-3 text-[15px] leading-7 text-slate-800">{card.summary.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}</div>
      </section>

      <dl className="mt-7 grid grid-cols-3 gap-3 border-b border-slate-200 pb-7 text-center">
        {["Relevant studies", "Direct evidence", "Participants"].map((label) => <div key={label}><dd className="text-2xl font-extrabold text-slate-900">—</dd><dt className="mt-1 text-xs font-medium text-slate-500 sm:text-sm">{label}</dt></div>)}
      </dl>

      <section className="mt-7">
        <h3 className="text-lg font-extrabold text-slate-950">Evidence relevance</h3>
        <dl className="mt-3 divide-y divide-slate-100">{card.relevance.map((item) => <div key={item.label} className="flex items-center justify-between gap-4 py-3"><dt className="text-sm font-medium text-slate-800">{item.label}</dt><dd className={`shrink-0 rounded-full px-3 py-1 text-xs font-bold ${item.status === "topic_match" ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-700"}`}>{item.status === "topic_match" ? "Topic match" : "To verify"}</dd></div>)}</dl>
      </section>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-5 text-xs text-slate-500">
        <span>Source: PubMed · Evidence analysis pending</span>
        <span className="rounded-full bg-orange-50 px-3 py-1 font-bold text-orange-700">Not verified</span>
      </div>
    </article>
  );
}

function SupplementProfileCard({
  medication,
  isExpanded,
  isCompared,
  onClose,
  onCompare,
  onToggle,
}: {
  medication: MedicationEvidence;
  isExpanded: boolean;
  isCompared: boolean;
  onClose: () => void;
  onCompare: () => void;
  onToggle: () => void;
}) {
  const card = medication.supplementCard;
  if (!card) return null;
  const details = [
    ["Study types", medication.studyTypes],
    ["Participants", medication.participants],
    ["Studied doses", "Awaiting extraction"],
    ["Study duration", medication.studyDuration],
    ["Study funding", medication.independence.funding],
  ];
  return (
    <article className="overflow-hidden rounded-[30px] border border-slate-300 bg-white shadow-card">
      <div className="p-6 sm:p-9">
        <div className="flex items-start justify-between gap-5">
          <div className="flex min-w-0 gap-4"><Pill size={30} className="mt-1 shrink-0 text-slate-900" /><div><h2 className="text-3xl font-extrabold tracking-[-0.04em] text-slate-950">{medication.name}</h2><p className="mt-1 text-sm font-medium text-slate-500">{medication.category}</p><div className="mt-3 flex flex-wrap gap-2">{card.tags.map((tag) => <span key={tag} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{tag}</span>)}</div></div></div>
          <button type="button" aria-label={`Close ${medication.name} card`} onClick={onClose} className="grid size-10 shrink-0 place-items-center rounded-xl border border-slate-200 text-slate-500 hover:bg-slate-50"><X size={16} /></button>
        </div>

        <section className="mt-8 border-t border-slate-200 pt-7">
          <h3 className="text-xl font-extrabold text-slate-950">Scientific evidence by outcome</h3>
          <div className="mt-3 divide-y divide-slate-200">{card.outcomes.map((outcome) => <div key={outcome.name} className="flex items-center justify-between gap-5 py-4"><div><h4 className="font-bold text-slate-900">{outcome.name}</h4><p className="mt-1 text-sm text-slate-500">{outcome.description}</p></div><span className={`shrink-0 rounded-full px-3 py-1 text-xs font-bold ${outcome.status === "review_pending" ? "bg-orange-50 text-orange-700" : "bg-slate-100 text-slate-700"}`}>{outcome.status === "review_pending" ? "Review pending" : "Not evaluated"}</span></div>)}</div>
        </section>

        <section className="mt-7">
          <h3 className="text-xl font-extrabold text-slate-950">Research details</h3>
          <dl className="mt-3">{details.map(([label, value]) => <div key={label} className="grid gap-1 border-b border-slate-200 py-3 sm:grid-cols-[40%_1fr]"><dt className="text-sm font-medium text-slate-700">{label}</dt><dd className="text-sm font-medium text-slate-500">{value}</dd></div>)}</dl>
        </section>

        <section className="mt-7">
          <h3 className="text-xl font-extrabold text-slate-950">Safety &amp; interactions</h3>
          <div className="mt-4 rounded-2xl bg-slate-50 p-5"><h4 className="flex items-center gap-2 font-extrabold text-slate-900"><ShieldAlert size={18} className="text-slate-500" /> Safety review</h4><p className="mt-3 text-sm leading-6 text-slate-700">Contraindications, drug interactions, adverse effects and food/timing considerations require verification against appropriate safety sources.</p></div>
        </section>

        {isExpanded && <section className="mt-7 rounded-2xl border border-dashed border-slate-300 p-5"><h3 className="font-extrabold text-slate-950">Evidence sources</h3><p className="mt-2 text-sm leading-6 text-slate-600">No verified publication has been admitted to this ingredient-and-outcome view yet. Retrieval candidates remain separate until extraction and source-span validation are complete.</p><SourceLink href={medication.effectiveness.sourceUrl}>Open PubMed discovery search</SourceLink></section>}

        <div className="mt-7 flex flex-wrap gap-2">
          <button type="button" onClick={onToggle} aria-expanded={isExpanded} className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl border border-slate-300 px-4 text-sm font-bold text-slate-800 hover:bg-slate-50">{isExpanded ? "Hide evidence sources" : "Explore evidence sources"}{isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}</button>
          <button type="button" onClick={onCompare} aria-pressed={isCompared} className={`inline-flex min-h-11 items-center gap-2 rounded-xl border px-4 text-sm font-bold ${isCompared ? "border-brand-navy bg-brand-navy text-white" : "border-slate-300 text-slate-800 hover:bg-slate-50"}`}><Scale size={16} />{isCompared ? "Added to compare" : "Add to compare"}</button>
        </div>
      </div>
    </article>
  );
}

export function EvidenceLens() {
  const [query, setQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState<string | null>(null);
  const [statusFilter] = useState<StatusFilter>("all");
  const [cards, setCards] = useState<string[]>([]);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [updates, setUpdates] = useState<Record<string, UpdateState>>({});
  const [checking, setChecking] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, CitationState>>({});
  const [questions, setQuestions] = useState<Record<string, string>>({
    "magnesium-glycinate": "Does magnesium glycinate improve sleep quality?",
    "magnesium-sleep": "What does the evidence show about taking magnesium for insomnia?",
    "magne-b6": "Can Magne-B6 be used for insomnia?",
  });
  const [drafting, setDrafting] = useState<string | null>(null);
  const [corpusGroups, setCorpusGroups] = useState<CorpusStudyGroup[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [pinnedStudyGroups, setPinnedStudyGroups] = useState<CorpusStudyGroup[]>([]);
  const [searchingCorpus, setSearchingCorpus] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  useEffect(() => {
    const restoreState = window.setTimeout(() => {
      setUpdates(readStorage(UPDATES_KEY, {}));
      // Legacy evidence cards accumulated across searches. The study view now keeps
      // only explicitly pinned result groups, so remove that older persisted state.
      setCards([]);
      window.localStorage.removeItem(CARDS_KEY);
      setCompareIds(readStorage<string[]>(COMPARE_KEY, []).filter((id) => medicationEvidence.some((m) => m.id === id)));
      setPinnedStudyGroups(readStorage<CorpusStudyGroup[]>(PINNED_STUDIES_KEY, []));
    }, 0);

    return () => window.clearTimeout(restoreState);
  }, []);

  useEffect(() => {
    const value = query.trim();
    if (value.length < 1) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`/api/evidence-lens/search?q=${encodeURIComponent(value)}&suggest=1`, { signal: controller.signal });
        const payload = await response.json();
        const local = medicationEvidence
          .filter((medication) => medication.name.toLowerCase().includes(value.toLowerCase()) || medication.aliases.some((alias) => alias.includes(value.toLowerCase())))
          .map((medication) => medication.name);
        setSuggestions([...new Set([...local, ...(payload.suggestions ?? [])])].slice(0, 8));
      } catch (caught) {
        if (!(caught instanceof DOMException && caught.name === "AbortError")) setSuggestions([]);
      }
    }, 180);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  function saveCards(next: string[]) {
    setCards(next);
    window.localStorage.setItem(CARDS_KEY, JSON.stringify(next));
  }

  function toggleComparison(id: string) {
    const next = compareIds.includes(id) ? compareIds.filter((value) => value !== id) : [...compareIds, id];
    setCompareIds(next);
    window.localStorage.setItem(COMPARE_KEY, JSON.stringify(next));
  }

  function closeCard(id: string) {
    saveCards(cards.filter((value) => value !== id));
    if (compareIds.includes(id)) toggleComparison(id);
  }

  function toggleStudyPin(name: string) {
    const isPinned = pinnedStudyGroups.some((group) => group.name === name);
    const group = corpusGroups.find((candidate) => candidate.name === name) ?? pinnedStudyGroups.find((candidate) => candidate.name === name);
    const next = isPinned ? pinnedStudyGroups.filter((candidate) => candidate.name !== name) : group ? [...pinnedStudyGroups, group] : pinnedStudyGroups;
    setPinnedStudyGroups(next);
    window.localStorage.setItem(PINNED_STUDIES_KEY, JSON.stringify(next));
  }

  const matches = activeQuery ? findMedications(activeQuery) : [];
  const displayedStudyGroups = [...corpusGroups, ...pinnedStudyGroups.filter((group) => !corpusGroups.some((current) => current.name === group.name))];
  const studyGroupNames = new Set(displayedStudyGroups.map((group) => group.name));
  const parsedQueryParts = [...new Set([...queryParts(activeQuery, matches), ...(selectedEntity ? [selectedEntity] : []), ...displayedStudyGroups.flatMap((group) => [group.name, ...group.tags])])];
  const visibleCards = cards
    .map((id) => medicationEvidence.find((medication) => medication.id === id))
    .filter((medication): medication is MedicationEvidence => Boolean(medication));
  async function runStudySearch(value: string) {
    const normalized = value.trim().slice(0, 300);
    if (!normalized) return;
    // Move the selected item into a chip and leave the field ready for another search.
    setQuery("");
    setActiveQuery(normalized);
    setSuggestions([]);
    setError(null);
    const found = findMedications(normalized);
    // Every search replaces unpinned results. Pinned study groups are managed separately.
    saveCards([]);
    setExpanded((current) => ({ ...current, ...Object.fromEntries(found.map((medication) => [medication.id, false])) }));
    setSearchingCorpus(true);
    try {
      const response = await fetch(`/api/evidence-lens/search?q=${encodeURIComponent(normalized)}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message ?? "Study search failed.");
      const nextGroups = (payload.groups ?? []) as CorpusStudyGroup[];
      setCorpusGroups(nextGroups);
      setSelectedEntity(payload.selectedEntity ?? null);
      setPinnedStudyGroups((current) => {
        const refreshed = current.map((pinned) => nextGroups.find((group) => group.name === pinned.name) ?? pinned);
        window.localStorage.setItem(PINNED_STUDIES_KEY, JSON.stringify(refreshed));
        return refreshed;
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Study search failed.");
      setCorpusGroups([]);
      setSelectedEntity(null);
    } finally {
      setSearchingCorpus(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void runStudySearch(query);
  }

  function clearSearch() {
    setActiveQuery(null);
    setQuery("");
    setCorpusGroups([]);
    setSelectedEntity(null);
  }

  function renderStudySearch(compact = false) {
    return <form onSubmit={submit} className={compact ? "w-full" : "mx-auto w-full max-w-[900px]"}>
      <div className="relative">
        <label className="relative block rounded-[32px] border border-slate-200 bg-white px-6 py-3 shadow-[0_8px_28px_rgba(15,23,42,0.08)] transition focus-within:border-slate-300 focus-within:shadow-[0_10px_32px_rgba(15,23,42,0.12)]"><Search size={21} className="absolute left-6 top-1/2 -translate-y-1/2 text-slate-500" /><input value={query} onChange={(event) => { setQuery(event.target.value); if (event.target.value.trim().length < 1) setSuggestions([]); }} placeholder="Type a medication, vitamin, or supplement" maxLength={300} autoComplete="off" role="combobox" aria-autocomplete="list" aria-controls="evidence-search-suggestions" aria-expanded={suggestions.length > 0} className="h-11 w-full bg-transparent pl-9 pr-3 text-[16px] font-medium text-text-primary outline-none placeholder:font-normal placeholder:text-slate-400" /></label>
        {suggestions.length > 0 && <div id="evidence-search-suggestions" role="listbox" className="absolute left-0 right-0 z-20 mt-2 overflow-hidden rounded-[18px] border border-border bg-white p-2 text-left shadow-xl">{suggestions.map((suggestion) => <button key={suggestion} type="button" role="option" aria-selected="false" onClick={() => { setSuggestions([]); void runStudySearch(suggestion); }} className="flex w-full touch-manipulation items-center gap-3 rounded-[12px] px-4 py-3 text-left text-[13px] font-bold text-text-primary hover:bg-surface-muted"><Search size={15} className="text-text-tertiary" />{suggestion}</button>)}</div>}
      </div>
    </form>;
  }

  async function checkUpdates(medication: MedicationEvidence) {
    setChecking(medication.id);
    setError(null);
    const previous = updates[medication.id];
    try {
      const response = await fetch("/api/evidence-lens/updates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ medicationId: medication.id, since: previous?.lastUpdatedAt ?? medication.liveSources.lastUpdatedAt }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message ?? "Source update check failed.");
      const completed = payload.status === "completed";
      // Keep earlier unreviewed findings until the card is reviewed again.
      const newRecords = [...(payload.newRecords as NewRecord[]), ...(previous?.newRecords ?? [])]
        .filter((record, index, all) => all.findIndex((other) => other.pmid === record.pmid) === index);
      const trialChanges = [...(payload.trialChanges as TrialChange[]), ...(previous?.trialChanges ?? [])]
        .filter((change, index, all) => all.findIndex((other) => other.id === change.id) === index);
      const next: UpdateState = {
        // Only advance the last update when every source answered; otherwise the gap would be skipped next time.
        lastUpdatedAt: completed ? payload.checkedAt : previous?.lastUpdatedAt ?? medication.liveSources.lastUpdatedAt,
        lastCheckedAt: payload.checkedAt,
        status: payload.status,
        newRecords,
        newPublicationIds: [...new Set([...(payload.newPublicationIds as string[]), ...(previous?.newPublicationIds ?? [])])],
        trialChanges,
        sourceErrors: payload.sourceErrors ?? [],
      };
      setUpdates((current) => {
        const value = { ...current, [medication.id]: next };
        window.localStorage.setItem(UPDATES_KEY, JSON.stringify(value));
        return value;
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Source update check failed.");
    } finally {
      setChecking(null);
    }
  }

  async function generateDraft(medication: MedicationEvidence) {
    const question = questions[medication.id]?.trim();
    if (!question || question.length < 3) {
      setError("Enter a question with at least 3 characters.");
      return;
    }
    setDrafting(medication.id);
    setError(null);
    try {
      const response = await fetch("/api/evidence-lens/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          medicationId: medication.id,
          question,
        }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.answer) throw new Error(payload.message ?? "Draft generation failed.");
      setDrafts((current) => ({
        ...current,
        [medication.id]: {
          question,
          answer: payload.answer,
          automated: payload.citationValidation?.semantic_support_automated === true,
          sources: payload.sources ?? [],
        },
      }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Draft generation failed.");
    } finally {
      setDrafting(null);
    }
  }

  return (
    <main className="min-h-[calc(100vh-77px)] bg-[#f6f7f9] px-4 py-5 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-[1440px]">
        {(activeQuery || displayedStudyGroups.length > 0) && <div className="rounded-[28px] bg-white p-3 shadow-card sm:p-4">
          {renderStudySearch(true)}
          {parsedQueryParts.length > 0 && <div className="mt-4 flex flex-wrap items-center gap-2">{parsedQueryParts.map((part) => {
            const canPin = studyGroupNames.has(part);
            const isPinned = pinnedStudyGroups.some((group) => group.name === part);
            return <span key={part} className={`inline-flex items-center gap-2 rounded-pill border px-3 py-2 text-[12px] font-bold ${isPinned ? "border-brand-coral bg-brand-coral text-white" : "border-transparent bg-surface-muted text-text-primary"}`}>{part}{canPin && <button type="button" aria-label={isPinned ? `Unpin ${part}` : `Pin ${part}`} title={isPinned ? "Unpin" : "Keep this study card"} onClick={() => toggleStudyPin(part)} className={isPinned ? "text-white/80 hover:text-white" : "text-slate-400 hover:text-brand-coral"}>{isPinned ? <PinOff size={13} /> : <Pin size={13} />}</button>}<button type="button" aria-label={`Remove ${part}`} onClick={() => { if (isPinned) toggleStudyPin(part); if (canPin) setCorpusGroups((groups) => groups.filter((group) => group.name !== part)); else clearSearch(); }} className={isPinned ? "text-white/80 hover:text-white" : "text-slate-400 hover:text-brand-coral"}><X size={13} /></button></span>;
          })}</div>}
        </div>}

        {error && <div role="alert" className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}

        {searchingCorpus && <section className="mt-6 rounded-card bg-white p-6 text-center text-sm font-semibold text-text-secondary shadow-card"><RefreshCw size={18} className="mx-auto mb-2 animate-spin text-brand-coral" />Searching 220 PubMed publications…</section>}

        {!searchingCorpus && !activeQuery && !visibleCards.length && !displayedStudyGroups.length && (
          <section className="grid min-h-[calc(100vh-170px)] place-items-center px-4 py-10 text-center">
            <div className="w-full max-w-[900px] -translate-y-6 sm:-translate-y-8">
              <FlaskConical size={36} className="mx-auto text-slate-300" />
              <h2 className="mt-3 text-[24px] font-extrabold text-brand-navy">Find what studies say about your medication</h2>
              <div className="mx-auto mt-5 flex max-w-[760px] flex-wrap justify-center gap-2">
                {[
                  { icon: Search, title: "Relevant studies", tone: "text-brand-coral" },
                  { icon: FlaskConical, title: "Study design", tone: "text-violet-600" },
                  { icon: Info, title: "Key results", tone: "text-blue-600" },
                  { icon: Scale, title: "Research context", tone: "text-emerald-600" },
                ].map(({ icon: Icon, title, tone }) => <span key={title} className="inline-flex items-center gap-2 rounded-pill bg-white px-4 py-2.5 text-[12px] font-bold text-brand-navy shadow-sm"><Icon size={16} className={tone} />{title}</span>)}
              </div>
              <div className="mx-auto mt-7">{renderStudySearch()}</div>
            </div>
          </section>
        )}

        {!searchingCorpus && activeQuery && corpusGroups.length === 0 && (
          <section className="grid min-h-[calc(100vh-310px)] place-items-center px-6 py-12 text-center">
            <div className="max-w-xl">
              <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-white text-slate-400 shadow-sm">
                <SearchX size={26} aria-hidden="true" />
              </span>
              <h2 className="mt-4 text-[22px] font-extrabold text-slate-900">No publications found</h2>
              <p className="mt-2 text-[15px] leading-6 text-slate-500">
                We do not currently have matching PubMed studies for <span className="font-semibold text-slate-700">{selectedEntity ?? activeQuery}</span>.
              </p>
            </div>
          </section>
        )}

        {displayedStudyGroups.length > 0 && <div className="mt-6 grid gap-4">{displayedStudyGroups.map((group) => <CorpusStudiesCard key={group.name} group={group} pinned={pinnedStudyGroups.some((item) => item.name === group.name)} onTogglePin={() => toggleStudyPin(group.name)} />)}</div>}

        <div className="mt-6 grid gap-4">
          {visibleCards.map((medication) => {
            const records = statusFilter === "all" ? medication.evidence : medication.evidence.filter((record) => record.status === statusFilter);
            return <CompactEvidenceCard
              key={medication.id}
              medication={medication}
              records={records}
              isExpanded={expanded[medication.id] === true}
              isCompared={compareIds.includes(medication.id)}
              update={updates[medication.id]}
              checking={checking === medication.id}
              draft={drafts[medication.id]}
              question={questions[medication.id] ?? ""}
              drafting={drafting === medication.id}
              onClose={() => closeCard(medication.id)}
              onCompare={() => toggleComparison(medication.id)}
              onToggle={() => setExpanded((current) => ({ ...current, [medication.id]: !current[medication.id] }))}
              onCheckUpdates={() => checkUpdates(medication)}
              onQuestionChange={(value) => setQuestions((current) => ({ ...current, [medication.id]: value }))}
              onGenerateDraft={() => generateDraft(medication)}
            />;
          })}
        </div>

        <div className="hidden" aria-hidden="true">
          {visibleCards.map((medication) => {
            const isExpanded = expanded[medication.id] !== false;
            const update = updates[medication.id];
            const draft = drafts[medication.id];
            const lastUpdatedAt = update?.lastUpdatedAt ?? medication.liveSources.lastUpdatedAt;
            const publicationCount = update?.newPublicationIds.length ?? 0;
            const pendingCount = publicationCount + (update?.trialChanges.length ?? 0);
            const records = statusFilter === "all" ? medication.evidence : medication.evidence.filter((record) => record.status === statusFilter);
            const overlap = overlapNotice[medication.independence.sponsorOverlap];
            if (medication.questionCard && medication.supplementCard) {
              return (
                <Fragment key={medication.id}>
                  <QuestionEvidenceCard medication={medication} />
                  <SupplementProfileCard
                    medication={medication}
                    isExpanded={isExpanded}
                    isCompared={compareIds.includes(medication.id)}
                    onClose={() => closeCard(medication.id)}
                    onCompare={() => toggleComparison(medication.id)}
                    onToggle={() => setExpanded((current) => ({ ...current, [medication.id]: !isExpanded }))}
                  />
                </Fragment>
              );
            }
            return (
              <article key={medication.id} className="overflow-hidden rounded-[30px] border border-slate-300 bg-white shadow-card">
                <div className="p-6 sm:p-10">
                  <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0">
                      <h2 className="text-4xl font-extrabold tracking-[-0.045em] text-brand-navy">{medication.name}</h2>
                      <p className="mt-2 text-base font-medium text-slate-500">{medication.category} · {medication.route}</p>
                      <div className="mt-4 flex flex-wrap items-center gap-2"><span className={`rounded-full border px-3 py-1 text-xs font-bold ${levelStyle[medication.evidenceLevelTone]}`}>{medication.statusLabel}</span><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">{medication.scope}</span>{pendingCount > 0 && <span className="inline-flex items-center gap-1 rounded-full bg-brand-coral px-3 py-1 text-xs font-bold text-white"><BellDot size={12} /> {pendingCount} new · review required</span>}</div>
                    </div>
                    <div className="flex shrink-0 flex-wrap items-center gap-2">
                      <button type="button" onClick={() => toggleComparison(medication.id)} aria-pressed={compareIds.includes(medication.id)} className={`inline-flex h-10 items-center gap-2 rounded-xl border px-3.5 text-xs font-bold ${compareIds.includes(medication.id) ? "border-brand-navy bg-brand-navy text-white" : "border-slate-200 text-slate-700 hover:bg-slate-50"}`}>{compareIds.includes(medication.id) && <Check size={14} />}{compareIds.includes(medication.id) ? "Added to compare" : "Add to compare"}</button>
                      <button type="button" onClick={() => checkUpdates(medication)} disabled={checking === medication.id} className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 px-3.5 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-60"><RefreshCw size={14} className={checking === medication.id ? "animate-spin" : ""} />{checking === medication.id ? "Checking sources…" : "Check new sources"}</button>
                      <button type="button" onClick={() => setExpanded((current) => ({ ...current, [medication.id]: !isExpanded }))} aria-expanded={isExpanded} className="inline-flex h-10 items-center gap-2 rounded-xl bg-brand-navy px-4 text-xs font-bold text-white">{isExpanded ? "Hide details" : "Show details"}{isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</button>
                      <button type="button" aria-label={`Close ${medication.name} card`} onClick={() => closeCard(medication.id)} className="grid size-10 place-items-center rounded-xl border border-slate-200 text-slate-500 hover:bg-slate-50"><X size={16} /></button>
                    </div>
                  </div>

                  <div className="mt-10 max-w-4xl">
                    <p className="text-sm font-bold uppercase tracking-[0.08em] text-slate-500">Clinical effectiveness</p>
                    <h3 className="mt-3 text-2xl font-extrabold text-slate-950">{medication.effectiveness.condition}</h3>
                    <div className="mt-3 flex flex-wrap items-center gap-3"><span className={`rounded-full border px-3 py-1 text-xs font-bold ${levelStyle[medication.evidenceLevelTone]}`}>{medication.effectiveness.certainty} certainty</span><span className="text-sm text-slate-500">{medication.effectiveness.headline}</span></div>
                    <p className="mt-4 text-base leading-7 text-slate-800">{medication.effectiveness.statement}</p>
                    <p className="mt-3 text-sm text-slate-500">Source: <SourceLink href={medication.effectiveness.sourceUrl}>{medication.effectiveness.sourceLabel}</SourceLink></p>
                  </div>

                  <div className="mt-7 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-slate-200 pt-4 text-xs text-slate-500"><span className="inline-flex items-center gap-1.5"><Clock3 size={13} /> Last updated {formatDate(lastUpdatedAt)}</span>{update && <span className="inline-flex items-center gap-1.5"><RefreshCw size={13} /> Sources checked {formatDate(update.lastCheckedAt)}{update.status === "partial" ? " · some sources unavailable" : ""}</span>}</div>
                </div>

                {isExpanded && (
                  <div className="border-t border-slate-200 bg-white p-6 sm:p-10">
                    {update && (pendingCount > 0 || update.sourceErrors.length > 0) && (
                      <section className="mb-6 rounded-2xl border border-brand-coral/30 bg-white p-5">
                        <div className="flex items-center gap-2"><BellDot size={17} className="text-brand-coral" /><h3 className="font-bold text-slate-950">New since previous update</h3></div>
                        <p className="mt-1 text-xs text-slate-500">Unreviewed candidates. They are not part of the evidence below until reviewed.</p>
                        {publicationCount > 0 && <p className="mt-3 text-sm text-slate-700">{publicationCount} new PubMed record{publicationCount > 1 ? "s" : ""}{publicationCount > update.newRecords.length ? ` · showing ${update.newRecords.length}` : ""}</p>}
                        <ul className="mt-3 grid gap-2">{update.newRecords.map((record) => <li key={record.pmid} className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-sm"><SourceLink href={record.url}>PMID {record.pmid}</SourceLink><p className="mt-1 font-semibold text-slate-900">{record.title}</p>{(record.journal || record.publishedAt) && <p className="text-xs text-slate-500">{[record.journal, record.publishedAt].filter(Boolean).join(" · ")}</p>}</li>)}{update.trialChanges.map((change) => <li key={change.id} className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-sm"><SourceLink href={change.url}>{change.id}</SourceLink><p className="mt-1 text-slate-700">{change.changes.join(" · ")}</p></li>)}</ul>
                        {update.sourceErrors.length > 0 && <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-rose-700"><AlertTriangle size={13} /> {update.sourceErrors.join(" · ")}</p>}
                      </section>
                    )}
                    <div className="space-y-8">
                      <SpecificationSection title="Clinical evidence" rows={[{ label: "Evidence status", value: medication.statusLabel }, { label: "Evidence level", value: medication.evidenceLevel }, { label: "Study type", value: medication.studyTypes }, { label: "Participants", value: medication.participants }, { label: "Population", value: medication.population }, { label: "Studied formulation", value: medication.studiedForms }, { label: "Study duration", value: medication.studyDuration }, { label: "Measured outcomes", value: medication.measuredOutcomes }, { label: "Evidence limitations", value: medication.limitations }]} />

                      <SpecificationSection title="Safety & interactions" rows={[{ label: "Contraindications", value: medication.safety.contraindications }, { label: "Drug interactions", value: medication.safety.interactions }, { label: "Food interactions", value: medication.safety.food }, { label: "Adverse effects", value: medication.safety.adverseEffects }]} />

                      <SpecificationSection title={`Evidence sources · ${records.length} of ${medication.evidence.length}`} rows={records.length ? records.map((record) => ({ label: record.identifiers, value: <div><div className="flex flex-wrap items-center gap-2"><span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${statusStyle[record.status]}`}>{record.statusLabel}</span><SourceLink href={record.sourceUrl}>Open {record.source}</SourceLink></div><p className="mt-2 font-bold">{record.title}</p><p className="mt-1 text-sm font-normal leading-6 text-slate-600">{record.passage}</p></div> })) : [{ label: "Sources", value: "No records of this evidence type in the reviewed corpus." }]} />

                      <SpecificationSection title="Research independence" rows={[{ label: "Manufacturer", value: medication.independence.manufacturer }, { label: "Study sponsors", value: medication.independence.sponsors }, { label: "Investigators", value: medication.independence.investigators }, { label: "Funding source", value: medication.independence.funding }, { label: "Conflicts disclosed", value: medication.independence.conflicts }, { label: "Independent replication", value: medication.independence.replication }, { label: "Manufacturer–sponsor overlap", value: <div><span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold text-slate-600">{overlap.label}</span><p className="mt-2 text-xs font-normal leading-5 text-slate-600">{overlap.text}</p></div> }]} />

                      <section className="border-t border-slate-200 pt-7">
                        <div>
                          <h3 className="text-xl font-extrabold tracking-[-0.02em] text-slate-950">Ask about this evidence</h3>
                          <p className="mt-1 text-sm text-slate-500">Get a direct answer grounded only in the reviewed sources shown above.</p>
                        </div>
                        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
                          <label className="flex-1 text-xs font-bold uppercase tracking-[0.07em] text-slate-500">Your question
                            <textarea value={questions[medication.id] ?? ""} onChange={(event) => setQuestions((current) => ({ ...current, [medication.id]: event.target.value }))} maxLength={500} rows={2} placeholder={`Ask about ${medication.name}…`} className="mt-2 w-full resize-y rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium normal-case tracking-normal text-slate-900 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
                          </label>
                          <button type="button" onClick={() => generateDraft(medication)} disabled={drafting === medication.id} className="h-11 rounded-xl bg-brand-navy px-5 text-xs font-bold text-white disabled:opacity-60">{drafting === medication.id ? "Answering…" : "Answer from evidence"}</button>
                        </div>
                        {draft && <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50 p-5">
                          <p className="text-xs font-bold uppercase tracking-[0.07em] text-blue-700">Question</p>
                          <p className="mt-1 font-semibold text-blue-950">{draft.question}</p>
                          <div className="mt-4 inline-flex rounded-full border border-blue-200 bg-white px-2.5 py-1 text-[11px] font-bold text-blue-800">{draft.automated ? "Automated checks passed · human review required" : "Citation review required"}</div>
                          <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-blue-950">{draft.answer}</p>
                          <div className="mt-5 border-t border-blue-200 pt-4">
                            <p className="text-xs font-bold uppercase tracking-[0.07em] text-blue-700">Sources used</p>
                            {draft.sources.length ? <ol className="mt-3 space-y-3">{draft.sources.map((source) => <li key={source.id} className="text-sm text-blue-950"><span className="mr-2 font-extrabold">[{source.citation}]</span><SourceLink href={source.url}>{source.title}</SourceLink><p className="ml-7 mt-1 text-xs text-blue-800">{source.identifiers} · {source.applicability}</p></li>)}</ol> : <p className="mt-2 text-sm text-blue-900">No valid source citation was returned; review is required.</p>}
                          </div>
                        </div>}
                      </section>
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>

      </div>
    </main>
  );
}
