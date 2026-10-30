import { medicationEvidence } from "@/data/evidence-lens";

const EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils";
const MAX_NEW_RECORDS = 5;

async function fetchJson(url: string) {
  const response = await fetch(url, {
    headers: { "User-Agent": "medguide-evidence-lens/0.1" },
    signal: AbortSignal.timeout(12_000),
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Source returned ${response.status}`);
  return response.json();
}

function eutilsUrl(endpoint: string, params: Record<string, string>) {
  const url = new URL(`${EUTILS}/${endpoint}`);
  url.search = new URLSearchParams({ db: "pubmed", retmode: "json", tool: "medguide_evidence_lens", ...params }).toString();
  return url.toString();
}

export async function POST(request: Request) {
  let body: { medicationId?: unknown; since?: unknown };
  try {
    body = await request.json();
  } catch {
    return Response.json({ code: "INVALID_REQUEST", message: "Request body must be JSON." }, { status: 400 });
  }
  const medication = medicationEvidence.find((item) => item.id === body.medicationId);
  if (!medication) {
    return Response.json(
      { code: "UNSUPPORTED_MEDICATION", message: "Live update checks are configured only for reviewed medication cards." },
      { status: 400 },
    );
  }
  const { lastUpdatedAt, pubmedDiscoveryQuery, pubmedIds, trials: baselineTrials } = medication.liveSources;
  // The client sends the card's last update; never look further back than the reviewed baseline.
  const sinceInput = typeof body.since === "string" && !Number.isNaN(Date.parse(body.since)) ? body.since : lastUpdatedAt;
  const since = new Date(Math.max(Date.parse(sinceInput), Date.parse(lastUpdatedAt))).toISOString();
  if (Date.parse(since) > Date.now()) {
    return Response.json({ code: "INVALID_SINCE", message: "Last update cannot be in the future." }, { status: 400 });
  }

  const [searchResult, ...trialResults] = await Promise.allSettled([
    fetchJson(eutilsUrl("esearch.fcgi", {
      term: pubmedDiscoveryQuery,
      datetype: "edat",
      mindate: since.slice(0, 10).replaceAll("-", "/"),
      maxdate: "3000",
      retmax: "50",
      sort: "pub_date",
    })),
    ...baselineTrials.map((trial) => fetchJson(`https://clinicaltrials.gov/api/v2/studies/${trial.id}`)),
  ]);
  const checkedAt = new Date().toISOString();
  const sourceErrors: string[] = [];
  if (searchResult.status === "rejected") sourceErrors.push("PubMed unavailable");
  trialResults.forEach((result, index) => {
    if (result.status === "rejected") sourceErrors.push(`${baselineTrials[index].id} unavailable`);
  });

  const newIds: string[] = searchResult.status === "fulfilled"
    ? ((searchResult.value?.esearchresult?.idlist ?? []) as string[]).filter((id) => !pubmedIds.includes(id))
    : [];
  const shownIds = newIds.slice(0, MAX_NEW_RECORDS);
  let summaries: Record<string, { title?: string; fulljournalname?: string; pubdate?: string }> = {};
  if (shownIds.length) {
    try {
      summaries = (await fetchJson(eutilsUrl("esummary.fcgi", { id: shownIds.join(",") })))?.result ?? {};
    } catch {
      sourceErrors.push("PubMed record details unavailable");
    }
  }
  const newRecords = shownIds.map((pmid) => ({
    pmid,
    title: summaries[pmid]?.title ?? `PMID ${pmid}`,
    journal: summaries[pmid]?.fulljournalname ?? "",
    publishedAt: summaries[pmid]?.pubdate ?? null,
    url: `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`,
  }));

  const trialChanges = trialResults.flatMap((result, index) => {
    if (result.status !== "fulfilled") return [];
    const baseline = baselineTrials[index];
    const status = result.value?.protocolSection?.statusModule;
    const overallStatus: string = status?.overallStatus ?? "UNKNOWN";
    const hasResults = Boolean(result.value?.hasResults);
    const sourceUpdatedAt: string | null = status?.lastUpdatePostDateStruct?.date ?? null;
    if (!sourceUpdatedAt || sourceUpdatedAt <= since.slice(0, 10)) return [];
    const changes = [`Registry record updated ${sourceUpdatedAt}`];
    if (overallStatus !== baseline.overallStatus) changes.push(`Status: ${baseline.overallStatus} → ${overallStatus}`);
    if (hasResults && !baseline.hasResults) changes.push("Results are now posted");
    return [{ id: baseline.id, url: `https://clinicaltrials.gov/study/${baseline.id}`, changes }];
  });

  return Response.json({
    status: sourceErrors.length ? "partial" : "completed",
    checkedAt,
    since,
    newPublicationIds: newIds,
    newRecords,
    trialChanges,
    note: "New records are unreviewed candidates, not admitted evidence.",
    sourceErrors,
  });
}
