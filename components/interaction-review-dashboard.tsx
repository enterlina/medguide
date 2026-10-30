"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  FileCheck2,
  History,
  Loader2,
  LockKeyhole,
  LogOut,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

type ValidationStatus =
  | "extracted"
  | "source_span_verified"
  | "human_reviewed"
  | "rejected";

type Rule = {
  interaction_id: string;
  subject_id: string;
  object_id: string;
  interaction_type: string;
  status: string;
  severity: string | null;
  effect: string;
  recommended_action: string;
  timing_rule: {
    minimum_interval_minutes: number | null;
    direction: string;
    exact_interval_stated: boolean;
  } | null;
  conditions: string[];
  applicable_routes: string[];
  applicable_dosage_forms: string[];
  applicable_strengths: string[];
  source_passage: {
    source_id: string;
    label_id: string;
    source_url: string;
    section: string;
    text: string;
  };
  validation_status: ValidationStatus;
};

type Principal = {
  reviewer_id: string;
  display_name: string;
  roles: Array<"source_reviewer" | "clinical_reviewer" | "admin">;
};

type Summary = Record<ValidationStatus, number>;
type ReviewEvent = {
  event_id: string;
  previous_status: ValidationStatus;
  new_status: ValidationStatus;
  reviewer: string;
  note: string;
  reviewed_at: string;
};
type Detail = {
  rule: Rule;
  source_name: string;
  document_version: string | null;
  set_id: string | null;
  product_name: string | null;
  source_match: boolean;
  history: ReviewEvent[];
};

const statuses: Array<{ value: ValidationStatus; label: string }> = [
  { value: "extracted", label: "Extracted" },
  { value: "source_span_verified", label: "Source verified" },
  { value: "human_reviewed", label: "Human reviewed" },
  { value: "rejected", label: "Rejected" },
];

const interactionTypes = [
  ["", "All interaction types"],
  ["drug_drug", "Drug–Drug"],
  ["drug_supplement", "Drug–Supplement"],
  ["timing_separation", "Timing"],
  ["drug_food", "Food"],
  ["drug_beverage", "Beverage"],
  ["contraindication", "Contraindication"],
  ["population_specific_warning", "Population warning"],
];

const statusTone: Record<ValidationStatus, string> = {
  extracted: "bg-amber-50 text-amber-800 border-amber-200",
  source_span_verified: "bg-blue-50 text-blue-800 border-blue-200",
  human_reviewed: "bg-emerald-50 text-emerald-800 border-emerald-200",
  rejected: "bg-rose-50 text-rose-800 border-rose-200",
};

function displayIdentifier(value: string) {
  return value.replace(/^(ingredient|substance):/, "").replaceAll("-", " ");
}

function labelForStatus(value: ValidationStatus) {
  return statuses.find((status) => status.value === value)?.label ?? value;
}

function hasRole(principal: Principal, role: Principal["roles"][number]) {
  return principal.roles.includes("admin") || principal.roles.includes(role);
}

function readableLabelUrl(sourceUrl: string, setId?: string | null) {
  if (!sourceUrl.includes("api.fda.gov/drug/label")) return sourceUrl;
  return setId
    ? `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=${encodeURIComponent(setId)}`
    : sourceUrl;
}

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail;
    const message = typeof detail === "string" ? detail : detail?.message;
    throw Object.assign(new Error(message ?? "Request failed"), { status: response.status });
  }
  return payload as T;
}

function LoginPanel({ onSignedIn }: { onSignedIn: (principal: Principal) => void }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      const principal = await jsonFetch<Principal>(
        "/api/admin/interactions/review/session",
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) },
      );
      setToken("");
      onSignedIn(principal);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign-in failed");
    } finally {
      setPending(false);
    }
  }
  return (
    <main className="min-h-[calc(100vh-77px)] bg-slate-50 px-4 py-14">
      <form onSubmit={submit} className="mx-auto max-w-md rounded-[28px] border border-slate-200 bg-white p-8 shadow-card">
        <span className="grid size-12 place-items-center rounded-2xl bg-brand-navy text-white"><LockKeyhole size={22} /></span>
        <h1 className="mt-6 text-2xl font-extrabold tracking-[-0.03em] text-slate-950">Interaction review</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">Enter your reviewer access token. Your identity and roles are resolved by the review service.</p>
        <label className="mt-6 block text-xs font-bold uppercase tracking-[0.08em] text-slate-500">Access token<input type="password" autoComplete="current-password" required value={token} onChange={(event) => setToken(event.target.value)} className="mt-2 h-12 w-full rounded-xl border border-slate-300 px-4 text-sm font-medium normal-case tracking-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /></label>
        {error && <p role="alert" className="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
        <button disabled={pending} className="mt-5 inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-brand-navy text-sm font-bold text-white disabled:opacity-60">{pending && <Loader2 size={16} className="animate-spin" />}Sign in</button>
      </form>
    </main>
  );
}

export function InteractionReviewDashboard() {
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [status, setStatus] = useState<ValidationStatus>("extracted");
  const [interactionType, setInteractionType] = useState("");
  const [rules, setRules] = useState<Rule[]>([]);
  const [selected, setSelected] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(false);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadSummary = useCallback(async () => {
    setSummary(await jsonFetch<Summary>("/api/admin/interactions/review/summary"));
  }, []);

  const loadQueue = useCallback(async () => {
    const params = new URLSearchParams({ status, limit: "100", offset: "0" });
    if (interactionType) params.set("interaction_type", interactionType);
    const payload = await jsonFetch<{ rules: Rule[] }>(`/api/admin/interactions/review?${params}`);
    setRules(payload.rules);
  }, [status, interactionType]);

  const loadDetail = useCallback(async (id: string) => {
    setSelected(await jsonFetch<Detail>(`/api/admin/interactions/review/${encodeURIComponent(id)}`));
    setComment("");
  }, []);

  useEffect(() => {
    jsonFetch<Principal>("/api/admin/interactions/review/session")
      .then(setPrincipal)
      .catch(() => setPrincipal(null))
      .finally(() => setAuthChecked(true));
  }, []);

  useEffect(() => {
    if (!principal) return;
    async function refresh() {
      setLoading(true);
      setError("");
      try {
        await Promise.all([loadSummary(), loadQueue()]);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Unable to load review queue");
      } finally {
        setLoading(false);
      }
    }
    void refresh();
  }, [principal, loadSummary, loadQueue]);

  async function submitAction(target: ValidationStatus) {
    if (!selected || comment.trim().length < 3) {
      setError("A reviewer comment is required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await jsonFetch(`/api/admin/interactions/review/${encodeURIComponent(selected.rule.interaction_id)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_status: target, expected_status: selected.rule.validation_status, comment: comment.trim() }),
      });
      setNotice(`Rule moved to ${labelForStatus(target)}.`);
      await Promise.all([loadSummary(), loadQueue(), loadDetail(selected.rule.interaction_id)]);
    } catch (caught) {
      const statusCode = (caught as { status?: number }).status;
      setError(statusCode === 409 ? "This rule was changed by another reviewer. The latest version has been reloaded." : caught instanceof Error ? caught.message : "Review failed");
      if (statusCode === 409) await Promise.all([loadSummary(), loadQueue(), loadDetail(selected.rule.interaction_id)]);
    } finally {
      setLoading(false);
    }
  }

  async function requestNote(kind: "correction" | "clarification") {
    if (!selected || comment.trim().length < 3) {
      setError("A reviewer comment is required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await jsonFetch(`/api/admin/interactions/review/${encodeURIComponent(selected.rule.interaction_id)}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind, expected_status: selected.rule.validation_status, comment: comment.trim() }),
      });
      setNotice(kind === "correction" ? "Correction requested." : "Clarification requested.");
      await loadDetail(selected.rule.interaction_id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  async function signOut() {
    await fetch("/api/admin/interactions/review/session", { method: "DELETE" });
    setPrincipal(null);
    setSelected(null);
  }

  if (!authChecked) return <main className="grid min-h-[calc(100vh-77px)] place-items-center bg-slate-50"><Loader2 className="animate-spin text-slate-400" /></main>;
  if (!principal) return <LoginPanel onSignedIn={setPrincipal} />;

  return (
    <main className="min-h-[calc(100vh-77px)] bg-[#f6f7f9] px-4 py-7 sm:px-8">
      <div className="mx-auto max-w-[1500px]">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div><div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-600"><ShieldCheck size={14} /> Protected review workspace</div><h1 className="mt-3 text-3xl font-extrabold tracking-[-0.04em] text-brand-navy sm:text-4xl">Interaction review dashboard</h1><p className="mt-2 text-sm text-slate-600">Review provenance first, then clinical interpretation. No bulk approval.</p></div>
          <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3"><div><p className="text-sm font-bold text-slate-900">{principal.display_name}</p><p className="text-xs text-slate-500">{principal.roles.join(" · ")}</p></div><button type="button" onClick={signOut} aria-label="Sign out" className="grid size-9 place-items-center rounded-xl bg-slate-100 text-slate-600"><LogOut size={15} /></button></div>
        </header>

        <section className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{statuses.map((item) => <button key={item.value} type="button" onClick={() => setStatus(item.value)} className={`rounded-2xl border p-5 text-left transition ${status === item.value ? "border-brand-navy bg-brand-navy text-white" : "border-slate-200 bg-white text-slate-900"}`}><span className={`text-xs font-bold uppercase tracking-[0.07em] ${status === item.value ? "text-white/70" : "text-slate-500"}`}>{item.label}</span><strong className="mt-2 block text-3xl">{summary?.[item.value] ?? "—"}</strong></button>)}</section>

        {(error || notice) && <div className={`mt-4 rounded-xl px-4 py-3 text-sm ${error ? "border border-rose-200 bg-rose-50 text-rose-800" : "border border-emerald-200 bg-emerald-50 text-emerald-800"}`}>{error || notice}</div>}

        <div className="mt-6 grid gap-5 xl:grid-cols-[minmax(420px,0.85fr)_minmax(560px,1.15fr)]">
          <section className="overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-card">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4"><div><h2 className="font-extrabold text-slate-950">Review queue</h2><p className="text-xs text-slate-500">{rules.length} visible rules</p></div><div className="flex gap-2"><select value={interactionType} onChange={(event) => setInteractionType(event.target.value)} className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-xs font-semibold">{interactionTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><button type="button" onClick={() => Promise.all([loadSummary(), loadQueue()])} aria-label="Refresh queue" className="grid size-10 place-items-center rounded-xl border border-slate-200"><RefreshCw size={15} className={loading ? "animate-spin" : ""} /></button></div></div>
            <div className="max-h-[760px] overflow-y-auto divide-y divide-slate-100">{rules.map((rule) => <button key={rule.interaction_id} type="button" onClick={() => loadDetail(rule.interaction_id)} className={`w-full p-4 text-left hover:bg-slate-50 ${selected?.rule.interaction_id === rule.interaction_id ? "bg-blue-50" : ""}`}><div className="flex items-start justify-between gap-3"><div><p className="font-bold capitalize text-slate-950">{displayIdentifier(rule.subject_id)} <span className="font-normal text-slate-400">×</span> {displayIdentifier(rule.object_id)}</p><p className="mt-1 text-xs text-slate-500">{rule.interaction_type.replaceAll("_", " ")} · {rule.severity ?? "Severity not extracted"}</p></div><span className={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-bold ${statusTone[rule.validation_status]}`}>{labelForStatus(rule.validation_status)}</span></div>{["CONTRAINDICATED", "AVOID_COMBINATION"].includes(rule.status) && <span className="mt-3 inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-1 text-[10px] font-bold text-rose-700"><AlertTriangle size={11} /> Potentially serious</span>}</button>)}{!rules.length && !loading && <p className="p-8 text-center text-sm text-slate-500">No rules match this filter.</p>}</div>
          </section>

          <section className="min-h-[620px] rounded-[24px] border border-slate-200 bg-white p-5 shadow-card sm:p-7">
            {!selected ? <div className="grid min-h-[560px] place-items-center text-center"><div><FileCheck2 className="mx-auto text-slate-300" size={36} /><h2 className="mt-3 font-extrabold text-slate-900">Select a rule</h2><p className="mt-1 text-sm text-slate-500">Compare extraction with the stored official label passage.</p></div></div> : <RuleDetail detail={selected} principal={principal} comment={comment} setComment={setComment} loading={loading} onAction={submitAction} onNote={requestNote} />}
          </section>
        </div>
      </div>
    </main>
  );
}

function RuleDetail({ detail, principal, comment, setComment, loading, onAction, onNote }: { detail: Detail; principal: Principal; comment: string; setComment: (value: string) => void; loading: boolean; onAction: (target: ValidationStatus) => void; onNote: (kind: "correction" | "clarification") => void }) {
  const { rule } = detail;
  const sourceStep = rule.validation_status === "extracted";
  const clinicalStep = rule.validation_status === "source_span_verified";
  const readableSourceUrl = readableLabelUrl(rule.source_passage.source_url, detail.set_id);
  const hasReadableAlternative = readableSourceUrl !== rule.source_passage.source_url;
  return <div>
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.08em] text-slate-500">Rule detail</p><h2 className="mt-2 text-2xl font-extrabold capitalize text-slate-950">{displayIdentifier(rule.subject_id)} × {displayIdentifier(rule.object_id)}</h2><p className="mt-1 text-sm text-slate-500">{rule.interaction_type.replaceAll("_", " ")}</p></div><span className={`rounded-full border px-3 py-1.5 text-xs font-bold ${statusTone[rule.validation_status]}`}>{labelForStatus(rule.validation_status)}</span></div>
    <div className="mt-6 grid gap-5 lg:grid-cols-2"><DetailBlock title="Medication information" rows={[["Medication A", displayIdentifier(rule.subject_id)], ["Medication B / Substance", displayIdentifier(rule.object_id)], ["Interaction type", rule.interaction_type.replaceAll("_", " ")], ["Severity", rule.severity ?? "Not extracted"], ["Label product", detail.product_name ?? "Not available"]]} /><DetailBlock title="Applicability" rows={[["Conditions", rule.conditions.join(" · ") || "None extracted"], ["Routes", rule.applicable_routes.join(" · ") || "Not restricted"], ["Dosage forms", rule.applicable_dosage_forms.join(" · ") || "Not restricted"], ["Strengths", rule.applicable_strengths.join(" · ") || "Not restricted"], ["Timing", rule.timing_rule ? `${rule.timing_rule.minimum_interval_minutes ?? "Not stated"} min · ${rule.timing_rule.direction}` : "No timing rule"]]} /></div>
    <section className="mt-6 border-t border-slate-200 pt-6"><h3 className="font-extrabold text-slate-950">Extracted interpretation</h3><p className="mt-3 text-xs font-bold uppercase tracking-[0.07em] text-slate-500">Clinical effect</p><p className="mt-1 text-sm leading-6 text-slate-800">{rule.effect}</p><p className="mt-4 text-xs font-bold uppercase tracking-[0.07em] text-slate-500">Recommended action</p><p className="mt-1 text-sm leading-6 text-slate-800">{rule.recommended_action}</p></section>
    <section className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-extrabold text-slate-950">Original source</h3><p className="mt-1 text-xs text-slate-500">{detail.source_name} · version {detail.document_version ?? "not available"} · {rule.source_passage.section}</p></div><span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${detail.source_match ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>{detail.source_match ? <CheckCircle2 size={13} /> : <XCircle size={13} />}Exact source match: {detail.source_match ? "Pass" : "Fail"}</span></div><blockquote className="mt-4 border-l-2 border-slate-400 pl-4 text-sm leading-7 text-slate-800">{rule.source_passage.text}</blockquote><div className="mt-4 flex flex-wrap items-center gap-3"><a href={readableSourceUrl} target="_blank" rel="noreferrer" className="inline-flex h-10 items-center gap-2 rounded-xl bg-blue-700 px-4 text-xs font-bold text-white hover:bg-blue-800">Open readable label <ExternalLink size={12} /></a>{hasReadableAlternative && <a href={rule.source_passage.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-slate-800 hover:underline">Raw openFDA JSON <ExternalLink size={11} /></a>}</div><p className="mt-3 text-xs leading-5 text-slate-500">The readable DailyMed page is provided for human review. The saved openFDA response remains the machine-verifiable source.</p></section>
    {(sourceStep || clinicalStep) && <section className="mt-6 border-t border-slate-200 pt-6"><h3 className="font-extrabold text-slate-950">{sourceStep ? "Step 1 — Source verification" : "Step 2 — Clinical review"}</h3><p className="mt-1 text-sm text-slate-500">{sourceStep ? "Confirm the exact passage supports the extracted entities before advancing." : "Review substances, interpretation, applicability, recommendation and timing."}</p><label className="mt-4 block text-xs font-bold uppercase tracking-[0.07em] text-slate-500">Required reviewer comment<textarea value={comment} onChange={(event) => setComment(event.target.value)} rows={3} maxLength={2000} className="mt-2 w-full rounded-xl border border-slate-300 p-3 text-sm font-medium normal-case tracking-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /></label><div className="mt-3 flex flex-wrap gap-2">{sourceStep && hasRole(principal, "source_reviewer") && <><button disabled={loading || !detail.source_match} onClick={() => onAction("source_span_verified")} className="inline-flex h-10 items-center gap-2 rounded-xl bg-blue-700 px-4 text-xs font-bold text-white disabled:opacity-40"><CheckCircle2 size={14} />Verify source</button><button disabled={loading} onClick={() => onNote("correction")} className="h-10 rounded-xl border border-amber-300 px-4 text-xs font-bold text-amber-800">Request correction</button><button disabled={loading} onClick={() => onAction("rejected")} className="h-10 rounded-xl border border-rose-300 px-4 text-xs font-bold text-rose-700">Reject</button></>}{clinicalStep && hasRole(principal, "clinical_reviewer") && <><button disabled={loading} onClick={() => onAction("human_reviewed")} className="inline-flex h-10 items-center gap-2 rounded-xl bg-emerald-700 px-4 text-xs font-bold text-white"><ShieldCheck size={14} />Approve interaction</button><button disabled={loading} onClick={() => onNote("clarification")} className="h-10 rounded-xl border border-amber-300 px-4 text-xs font-bold text-amber-800">Request clarification</button><button disabled={loading} onClick={() => onAction("rejected")} className="h-10 rounded-xl border border-rose-300 px-4 text-xs font-bold text-rose-700">Reject</button></>}{((sourceStep && !hasRole(principal, "source_reviewer")) || (clinicalStep && !hasRole(principal, "clinical_reviewer"))) && <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">Your role can view this rule but cannot perform this review step.</p>}</div></section>}
    <section className="mt-6 border-t border-slate-200 pt-6"><h3 className="flex items-center gap-2 font-extrabold text-slate-950"><History size={16} /> Review history</h3>{detail.history.length ? <ol className="mt-3 space-y-3">{detail.history.map((event) => <li key={event.event_id} className="rounded-xl bg-slate-50 p-3 text-sm"><div className="flex flex-wrap justify-between gap-2"><strong>{event.previous_status} → {event.new_status}</strong><time className="text-xs text-slate-500">{new Date(event.reviewed_at).toLocaleString()}</time></div><p className="mt-1 text-xs text-slate-500">{event.reviewer}</p><p className="mt-2 leading-5 text-slate-700">{event.note}</p></li>)}</ol> : <p className="mt-2 text-sm text-slate-500">No review decisions yet.</p>}</section>
  </div>;
}

function DetailBlock({ title, rows }: { title: string; rows: string[][] }) {
  return <section><h3 className="font-extrabold text-slate-950">{title}</h3><dl className="mt-2 divide-y divide-slate-100">{rows.map(([label, value]) => <div key={label} className="grid grid-cols-[120px_1fr] gap-3 py-2.5"><dt className="text-xs font-semibold text-slate-500">{label}</dt><dd className="text-sm font-medium capitalize text-slate-800">{value}</dd></div>)}</dl></section>;
}
