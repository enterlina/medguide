"use client";

import { Check, ChevronLeft, ChevronRight, ExternalLink, FlaskConical, Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

type EntityMatch = "exact" | "related_form" | "different" | "unclear";
type OutcomeMatch = "direct" | "indirect" | "not_measured" | "unclear";
type Decision = "include" | "include_as_indirect" | "exclude" | "needs_review";
type Review = {
  entityMatch: EntityMatch;
  outcomeMatch: OutcomeMatch;
  decision: Decision;
  comment: string;
  reviewMode: "manual" | "bulk_candidate";
  reviewedAt: string;
};
type QueueItem = {
  key: string;
  entityId: string;
  entityName: string;
  entityType: string;
  query: string;
  article?: {
    pmid: string;
    title: string;
    journal?: string;
    published_at?: string;
    publication_types?: string[];
    integrity_status?: string;
    abstract: string;
    source_url: string;
  };
  review: Review | null;
};

const matchOptions: Array<[EntityMatch, string]> = [
  ["exact", "Exact ingredient"], ["related_form", "Related form"],
  ["different", "Wrong match"], ["unclear", "Unclear"],
];
const outcomeOptions: Array<[OutcomeMatch, string]> = [
  ["direct", "Direct outcome"], ["indirect", "Indirect outcome"],
  ["not_measured", "Outcome not measured"], ["unclear", "Unclear"],
];
const decisionOptions: Array<[Decision, string]> = [
  ["include", "Include"], ["include_as_indirect", "Include as indirect"],
  ["exclude", "Exclude"], ["needs_review", "Needs review"],
];

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: "no-store" });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail ?? "Request failed");
  return payload as T;
}

export function EvidenceReviewDashboard() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [index, setIndex] = useState(0);
  const [filter, setFilter] = useState("unreviewed");
  const [entityFilter, setEntityFilter] = useState("all");
  const [entityMatch, setEntityMatch] = useState<EntityMatch>("unclear");
  const [outcomeMatch, setOutcomeMatch] = useState<OutcomeMatch>("unclear");
  const [decision, setDecision] = useState<Decision>("needs_review");
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const payload = await jsonFetch<{ items: QueueItem[] }>("/api/admin/evidence/review");
    setItems(payload.items);
  }, []);

  useEffect(() => {
    // Initial client-side hydration from the local review API.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load().catch((caught) => setError(caught instanceof Error ? caught.message : "Unable to load review"))
      .finally(() => setLoading(false));
  }, [load]);

  const entities = useMemo(() => [...new Set(items.map((item) => item.entityName))].sort(), [items]);
  const visible = useMemo(() => items.filter((item) => {
    if (entityFilter !== "all" && item.entityName !== entityFilter) return false;
    if (filter === "unreviewed") return !item.review;
    if (filter === "included") return item.review?.decision === "include" || item.review?.decision === "include_as_indirect";
    if (filter === "excluded") return item.review?.decision === "exclude";
    if (filter === "needs_review") return item.review?.decision === "needs_review";
    return true;
  }), [items, filter, entityFilter]);
  const current = visible[Math.min(index, Math.max(visible.length - 1, 0))];
  const counts = useMemo(() => ({
    total: items.length,
    reviewed: items.filter((item) => item.review?.reviewMode === "manual").length,
    candidates: items.filter((item) => item.review?.reviewMode === "bulk_candidate").length,
    included: items.filter((item) => item.review?.decision === "include" || item.review?.decision === "include_as_indirect").length,
    excluded: items.filter((item) => item.review?.decision === "exclude").length,
  }), [items]);

  useEffect(() => {
    // A changed filter starts a new queue view at its first item.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIndex(0);
  }, [filter, entityFilter]);

  useEffect(() => {
    // The form is a draft of the selected persisted review.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEntityMatch(current?.review?.entityMatch ?? "unclear");
    setOutcomeMatch(current?.review?.outcomeMatch ?? "unclear");
    setDecision(current?.review?.decision ?? "needs_review");
    setComment(current?.review?.comment ?? "");
  }, [current?.key, current?.review?.comment, current?.review?.decision, current?.review?.entityMatch, current?.review?.outcomeMatch]);

  async function save() {
    if (!current?.article) return;
    setLoading(true); setError(""); setMessage("");
    try {
      await jsonFetch("/api/admin/evidence/review", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entityId: current.entityId, pmid: current.article.pmid, entityMatch, outcomeMatch, decision, comment }),
      });
      await load();
      setMessage("Review saved in the separate review layer.");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Save failed"); }
    finally { setLoading(false); }
  }

  async function keepAllCandidates() {
    if (!window.confirm("Keep every unreviewed match as a candidate? This does not validate or merge the articles.")) return;
    setLoading(true); setError("");
    try {
      const result = await jsonFetch<{ changed: number }>("/api/admin/evidence/review", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "keep_all_candidates" }),
      });
      await load(); setMessage(`${result.changed} matches retained as unvalidated candidates.`);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Bulk action failed"); }
    finally { setLoading(false); }
  }

  if (loading && !items.length) return <main className="grid min-h-screen place-items-center bg-slate-50"><Loader2 className="animate-spin" /></main>;
  return (
    <main className="min-h-screen bg-slate-50 px-5 py-8 text-slate-950">
      <div className="mx-auto max-w-[1500px]">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div><p className="text-xs font-bold uppercase tracking-[0.12em] text-brand-coral">Local evidence review</p><h1 className="mt-2 text-3xl font-extrabold tracking-[-0.04em]">PubMed matches</h1><p className="mt-2 max-w-2xl text-sm text-slate-600">Confirm whether each article really studies the selected medicine or supplement. Decisions stay separate from the RAG corpus.</p></div>
          <button onClick={keepAllCandidates} className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-bold shadow-sm">Keep all as candidates</button>
        </div>
        <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-5">
          {Object.entries(counts).map(([label, value]) => <div key={label} className="rounded-2xl bg-white p-4 shadow-card"><div className="text-2xl font-extrabold">{value}</div><div className="mt-1 text-xs font-bold uppercase tracking-wide text-slate-500">{label.replace("_", " ")}</div></div>)}
        </div>
        <div className="mt-5 flex flex-wrap gap-3 rounded-2xl bg-white p-4 shadow-card">
          <select value={filter} onChange={(event) => setFilter(event.target.value)} className="h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold"><option value="all">All matches</option><option value="unreviewed">Unreviewed</option><option value="included">Included</option><option value="excluded">Excluded</option><option value="needs_review">Needs review</option></select>
          <select value={entityFilter} onChange={(event) => setEntityFilter(event.target.value)} className="h-11 min-w-64 rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold"><option value="all">All medicines & supplements</option>{entities.map((entity) => <option key={entity}>{entity}</option>)}</select>
          <span className="ml-auto self-center text-sm font-semibold text-slate-500">{visible.length ? Math.min(index + 1, visible.length) : 0} of {visible.length}</span>
        </div>
        {error && <p role="alert" className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>}
        {message && <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</p>}
        {!current ? <div className="mt-5 rounded-[28px] bg-white p-16 text-center shadow-card"><Check className="mx-auto text-emerald-600" /><h2 className="mt-4 text-xl font-bold">Nothing in this filter</h2></div> : (
          <section className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
            <article className="rounded-[28px] bg-white p-7 shadow-card">
              <div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-orange-50 px-3 py-1 text-xs font-bold text-orange-700">{current.entityName}</span><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">PMID {current.article?.pmid}</span>{current.review && <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-700">{current.review.reviewMode === "manual" ? "Reviewed" : "Candidate only"}</span>}</div>
              <h2 className="mt-5 text-2xl font-extrabold leading-tight tracking-[-0.025em]">{current.article?.title ?? "Publication unavailable"}</h2>
              <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm text-slate-500"><span>{current.article?.journal}</span><span>{current.article?.published_at}</span><span>{current.article?.publication_types?.filter((type) => type !== "Journal Article").join(" · ")}</span></div>
              <a href={current.article?.source_url} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-blue-700">Open PubMed <ExternalLink size={14} /></a>
              <div className="mt-7 border-t border-slate-200 pt-6"><h3 className="flex items-center gap-2 text-sm font-extrabold uppercase tracking-[0.08em] text-slate-500"><FlaskConical size={17} />Abstract</h3><p className="mt-4 whitespace-pre-line text-[15px] leading-7 text-slate-700">{current.article?.abstract || "No abstract available."}</p></div>
            </article>
            <aside className="h-fit rounded-[28px] bg-white p-6 shadow-card lg:sticky lg:top-5">
              <h3 className="text-xl font-extrabold">Your review</h3>
              <label className="mt-5 block text-xs font-bold uppercase tracking-wide text-slate-500">Ingredient match<select value={entityMatch} onChange={(event) => setEntityMatch(event.target.value as EntityMatch)} className="mt-2 h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold">{matchOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
              <label className="mt-4 block text-xs font-bold uppercase tracking-wide text-slate-500">Outcome match<select value={outcomeMatch} onChange={(event) => setOutcomeMatch(event.target.value as OutcomeMatch)} className="mt-2 h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold">{outcomeOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
              <label className="mt-4 block text-xs font-bold uppercase tracking-wide text-slate-500">Decision<select value={decision} onChange={(event) => setDecision(event.target.value as Decision)} className="mt-2 h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold">{decisionOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
              <label className="mt-4 block text-xs font-bold uppercase tracking-wide text-slate-500">Comment<textarea value={comment} onChange={(event) => setComment(event.target.value)} rows={4} placeholder="Why does this article match or not match?" className="mt-2 w-full rounded-xl border border-slate-300 p-3 text-sm normal-case tracking-normal" /></label>
              <button onClick={save} disabled={loading} className="mt-5 inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-brand-navy text-sm font-bold text-white disabled:opacity-50">{loading ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}Save review</button>
              <div className="mt-4 flex gap-2"><button onClick={() => setIndex((value) => Math.max(0, value - 1))} disabled={index === 0} className="inline-flex h-11 flex-1 items-center justify-center gap-1 rounded-xl border border-slate-300 text-sm font-bold disabled:opacity-30"><ChevronLeft size={16} />Previous</button><button onClick={() => setIndex((value) => Math.min(visible.length - 1, value + 1))} disabled={index >= visible.length - 1} className="inline-flex h-11 flex-1 items-center justify-center gap-1 rounded-xl border border-slate-300 text-sm font-bold disabled:opacity-30">Next<ChevronRight size={16} /></button></div>
            </aside>
          </section>
        )}
      </div>
    </main>
  );
}
