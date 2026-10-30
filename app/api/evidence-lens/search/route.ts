import { readFile } from "node:fs/promises";
import path from "node:path";
import { NextRequest, NextResponse } from "next/server";

type CorpusDocument = {
  source_document_id: string;
  title: string;
  source_uri: string;
  metadata: { supplements?: string[]; publication_types?: string[]; published_at?: string; last_checked_at?: string };
  sections: Array<{ section: string; text: string }>;
};
type OpenAlexWork = { cited_by_count?: number; primary_location?: { source?: { id?: string } | null } | null };
type OpenAlexSource = { summary_stats?: { "2yr_mean_citedness"?: number | null } };
type CatalogEntity = { entity_id: string; display_name: string; canonical_name: string; aliases?: string[]; components?: string[]; entity_type: "medication" | "supplement" };
type CatalogPublication = {
  pmid: string;
  title: string;
  journal?: string;
  published_at?: string;
  source_updated_at?: string;
  publication_types?: string[];
  abstract?: string;
  source_url: string;
};
type CatalogLink = { pmid: string; entity_id: string; name: string; entity_type: string };
type AiScreening = {
  screening_key: string;
  entity_id: string;
  entity_name: string;
  pmid: string;
  decision: "include" | "include_as_indirect" | "exclude" | "needs_review";
  confidence: "high" | "medium" | "low";
  evidence_quotes?: string[];
  reason: string;
  screened_at: string;
};

const corpusPath = path.join(process.cwd(), "medguide-evidence-engine/data/supplements/processed/rag_documents.json");
const publicationPath = path.join(process.cwd(), "medguide-evidence-engine/data/supplements/discovery/pubmed_recent.json");
const entityCatalogPath = path.join(process.cwd(), "medguide-evidence-engine/data/catalog/entities.json");
const catalogPublicationPath = path.join(process.cwd(), "medguide-evidence-engine/data/catalog/discovery/pubmed_recent.json");
const catalogLinkPath = path.join(process.cwd(), "medguide-evidence-engine/data/catalog/discovery/entity_publication_links.json");
const aiScreeningPath = path.join(process.cwd(), "medguide-evidence-engine/artifacts/evidence-review/openai_screening_v2.jsonl");
const stopWords = new Set(["a", "an", "and", "are", "can", "does", "for", "help", "how", "is", "it", "me", "of", "or", "the", "to", "what", "with"]);
const outcomePatterns: Array<[RegExp, string]> = [
  [/sleep|insomnia/i, "Sleep & insomnia"], [/depress/i, "Depression"],
  [/anxiety|stress/i, "Anxiety & stress"], [/muscle|cramp|exercise|strength/i, "Muscle & exercise"],
  [/glucose|diabet|insulin/i, "Blood sugar"], [/heart|cardiovascular|blood pressure/i, "Heart health"],
  [/dose|dosage|how much/i, "Dose"], [/safe|safety|side effect/i, "Safety"],
];

function normalize(value: string) { return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim(); }
function tokens(value: string) { return normalize(value).split(/\s+/).filter((token) => token.length > 1 && !stopWords.has(token)); }
function outcomeTags(value: string) { return outcomePatterns.filter(([pattern]) => pattern.test(value)).map(([, label]) => label); }
function outcomeTerms(value: string) {
  const terms: string[] = [];
  if (/sleep|insomnia/i.test(value)) terms.push("sleep", "insomnia");
  if (/depress/i.test(value)) terms.push("depress");
  if (/anxiety|stress/i.test(value)) terms.push("anxiety", "stress");
  if (/muscle|cramp|exercise|strength/i.test(value)) terms.push("muscle", "cramp", "exercise", "strength");
  if (/glucose|diabet|insulin/i.test(value)) terms.push("glucose", "diabet", "insulin");
  if (/heart|cardiovascular|blood pressure/i.test(value)) terms.push("heart", "cardiovascular", "blood pressure");
  if (/safe|safety|side effect/i.test(value)) terms.push("safe", "safety", "adverse", "side effect");
  return terms;
}

function excerpt(document: CorpusDocument) {
  const abstract = document.sections.find((section) => section.section.toLowerCase() === "abstract")?.text ?? document.sections[0]?.text ?? "";
  const resultStart = abstract.search(/\b(?:results?|conclusions?):/i);
  const result = resultStart >= 0 ? abstract.slice(resultStart) : abstract;
  return result.replace(/\s+/g, " ").trim().slice(0, 5000);
}

function abstractExcerpt(abstract: string) {
  const resultStart = abstract.search(/\b(?:results?|conclusions?):/i);
  const result = resultStart >= 0 ? abstract.slice(resultStart) : abstract;
  return result.replace(/\s+/g, " ").trim().slice(0, 5000);
}

function participantCount(text: string) {
  const patterns = [
    /\bn\s*[=  ]\s*(\d{2,5})\b/i,
    /\b(?:total of|included|enrolled|randomized|analysed|analyzed)\s+(\d{2,5})\s+(?:participants?|patients?|adults?|subjects?|people|individuals?)\b/i,
    /\b(\d{2,5})\s+(?:participants?|patients?|adults?|subjects?|people|individuals?)\s+(?:were|was|completed|received|with|aged|enrolled|participated)/i,
  ];
  for (const pattern of patterns) { const match = text.match(pattern); if (match) return match[1]; }
  return null;
}

function resolveIngredient(query: string, supplementNames: string[], catalog: CatalogEntity[]) {
  const normalizedQuery = normalize(query);
  if (/\b(?:magne|magnesium)\s*b6\b/.test(normalizedQuery)) return { label: "Magne-B6", targets: supplementNames.filter((name) => normalize(name).startsWith("magnesium ")) };
  const entity = catalog.find((item) => [item.display_name, item.canonical_name, ...(item.aliases ?? [])].some((name) => normalize(name) === normalizedQuery));
  if (entity) {
    const terms = [entity.display_name, entity.canonical_name, ...(entity.components ?? []), ...(entity.aliases ?? [])].map(normalize);
    return { label: entity.display_name, targets: supplementNames.filter((name) => terms.some((term) => normalize(name) === term || normalize(name).includes(term) || term.includes(normalize(name)))) };
  }
  const exact = supplementNames.filter((name) => normalizedQuery.includes(normalize(name))).sort((a, b) => b.length - a.length)[0];
  if (exact) return { label: exact, targets: [exact] };
  if (/\bmagnesium\b/.test(normalizedQuery)) return { label: "Magnesium", targets: supplementNames.filter((name) => normalize(name).startsWith("magnesium ")) };
  return null;
}

function resolveCatalogEntity(query: string, catalog: CatalogEntity[]) {
  const normalizedQuery = normalize(query);
  const names = (entity: CatalogEntity) => [entity.display_name, entity.canonical_name, ...(entity.aliases ?? [])];
  const exact = catalog.find((entity) => names(entity).some((name) => normalize(name) === normalizedQuery));
  if (exact) return exact;
  return catalog
    .filter((entity) => names(entity).some((name) => normalizedQuery.includes(normalize(name))))
    .sort((a, b) => Math.max(...names(b).map((name) => normalize(name).length)) - Math.max(...names(a).map((name) => normalize(name).length)))[0] ?? null;
}

async function readJsonLines<T>(filePath: string): Promise<T[]> {
  const value = await readFile(filePath, "utf8");
  return value.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line) as T);
}

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(2500), next: { revalidate: 86_400 } });
    return response.ok ? await response.json() as T : null;
  } catch { return null; }
}

async function openAlexMetrics(pmids: string[]) {
  const works = await Promise.all(pmids.map(async (pmid) => [pmid, await fetchJson<OpenAlexWork>(`https://api.openalex.org/works/pmid:${pmid}?select=cited_by_count,primary_location`)] as const));
  const sourceIds = [...new Set(works.map(([, work]) => work?.primary_location?.source?.id?.split("/").at(-1)).filter((id): id is string => Boolean(id)))];
  const sources = new Map(await Promise.all(sourceIds.map(async (id) => [id, await fetchJson<OpenAlexSource>(`https://api.openalex.org/sources/${id}?select=summary_stats`)] as const)));
  return new Map(works.map(([pmid, work]) => {
    const sourceId = work?.primary_location?.source?.id?.split("/").at(-1);
    return [pmid, { citations: typeof work?.cited_by_count === "number" ? work.cited_by_count : null, twoYearMeanCitedness: sourceId ? sources.get(sourceId)?.summary_stats?.["2yr_mean_citedness"] ?? null : null }];
  }));
}

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q")?.trim() ?? "";
  if (query.length < 1) return NextResponse.json({ groups: [], suggestions: [], documentCount: 0 });
  const [documents, publications, catalog, catalogPublications, catalogLinks, screenings] = await Promise.all([
    readFile(corpusPath, "utf8").then((value) => JSON.parse(value) as CorpusDocument[]),
    readFile(publicationPath, "utf8").then((value) => JSON.parse(value) as Array<{ pmid: string; journal?: string }>),
    readFile(entityCatalogPath, "utf8").then((value) => JSON.parse(value) as CatalogEntity[]),
    readFile(catalogPublicationPath, "utf8").then((value) => JSON.parse(value) as CatalogPublication[]),
    readFile(catalogLinkPath, "utf8").then((value) => JSON.parse(value) as CatalogLink[]),
    readJsonLines<AiScreening>(aiScreeningPath),
  ]);
  const journals = new Map(publications.map((publication) => [publication.pmid, publication.journal ?? null]));
  const supplementNames = [...new Set(documents.flatMap((document) => document.metadata.supplements ?? []))].sort();
  const normalizedQuery = normalize(query);
  const suggestions = catalog
    .filter((entity) => [entity.display_name, entity.canonical_name, ...(entity.aliases ?? []), ...(entity.components ?? [])].some((name) => normalize(name).includes(normalizedQuery) || tokens(query).some((token) => normalize(name).includes(token))))
    .sort((a, b) => Number(normalize(a.display_name).startsWith(normalizedQuery)) * -1 - Number(normalize(b.display_name).startsWith(normalizedQuery)) * -1 || a.display_name.localeCompare(b.display_name))
    .map((entity) => entity.display_name)
    .slice(0, 8);
  if (request.nextUrl.searchParams.get("suggest") === "1") return NextResponse.json({ suggestions });

  const catalogEntity = resolveCatalogEntity(query, catalog);
  if (catalogEntity) {
    const entityIds = new Set([catalogEntity.entity_id]);
    const publicationByPmid = new Map(catalogPublications.map((publication) => [String(publication.pmid), publication]));
    const requestedOutcomes = outcomeTerms(query);
    const screenedByPmid = new Map(
      screenings
        .filter((screening) => screening.entity_id === catalogEntity.entity_id)
        .map((screening) => [screening.pmid, screening]),
    );
    const accepted = catalogLinks
      .filter((link) => entityIds.has(link.entity_id))
      .map((link) => ({ publication: publicationByPmid.get(String(link.pmid)), screening: screenedByPmid.get(String(link.pmid)) }))
      .filter((item): item is { publication: CatalogPublication; screening: AiScreening | undefined } => Boolean(item.publication))
      .filter(({ screening }) => !screening || screening.decision === "include" || screening.decision === "include_as_indirect")
      .map((item) => {
        const searchable = `${item.publication.title} ${item.publication.abstract ?? ""}`.toLowerCase();
        const outcomeScore = requestedOutcomes.reduce((total, term) => total + (item.publication.title.toLowerCase().includes(term) ? 5 : 0) + (searchable.includes(term) ? 1 : 0), 0);
        return { ...item, outcomeScore };
      })
      .filter((item) => requestedOutcomes.length === 0 || item.outcomeScore > 0)
      .sort((a, b) => Number(b.screening?.decision === "include") - Number(a.screening?.decision === "include") || Number(Boolean(b.screening)) - Number(Boolean(a.screening)) || b.outcomeScore - a.outcomeScore || (b.publication.published_at ?? "").localeCompare(a.publication.published_at ?? ""));
    if (accepted.length) {
      const metrics = await openAlexMetrics(accepted.map(({ publication }) => String(publication.pmid)));
      const updatedAt = accepted.map(({ publication, screening }) => publication.source_updated_at ?? screening?.screened_at).filter(Boolean).sort().at(-1) ?? null;
      return NextResponse.json({
        groups: [{
          name: catalogEntity.display_name,
          tags: outcomeTags(query),
          updatedAt,
          articles: accepted.map(({ publication, screening }) => ({
            id: `pubmed:${publication.pmid}`,
            title: publication.title,
            sourceUrl: publication.source_url,
            pmid: String(publication.pmid),
            journal: publication.journal ?? null,
            publishedYear: publication.published_at?.slice(0, 4) ?? null,
            publishedAt: publication.published_at ?? null,
            studyType: publication.publication_types?.filter((type) => type !== "Journal Article").join(" · ") || "Journal article",
            participants: participantCount(publication.abstract ?? ""),
            result: abstractExcerpt(publication.abstract ?? screening?.evidence_quotes?.join(" ") ?? screening?.reason ?? publication.title),
            conflicts: null,
            funding: null,
            citations: metrics.get(String(publication.pmid))?.citations ?? null,
            twoYearMeanCitedness: metrics.get(String(publication.pmid))?.twoYearMeanCitedness ?? null,
            screening: screening ? { decision: screening.decision, confidence: screening.confidence, reason: screening.reason } : undefined,
          })),
        }],
        suggestions,
        selectedEntity: catalogEntity.display_name,
        documentCount: catalogPublications.length,
        evidenceLayer: accepted.every(({ screening }) => Boolean(screening)) ? "ai_screened" : "pubmed_candidates_with_ai_screened_subset",
      });
    }
  }

  const ingredient = resolveIngredient(query, supplementNames, catalog);
  if (!ingredient) return NextResponse.json({ groups: [], suggestions, documentCount: documents.length });
  const targets = new Set(ingredient.targets);
  const requestedOutcomes = outcomeTerms(query);
  const scored = documents
    .filter((document) => (document.metadata.supplements ?? []).some((supplement) => targets.has(supplement)))
    .map((document) => {
      const searchable = `${document.title} ${document.sections.map((section) => section.text).join(" ")}`.toLowerCase();
      const exactTarget = (document.metadata.supplements ?? []).some((supplement) => normalizedQuery.includes(normalize(supplement)));
      const outcomeScore = requestedOutcomes.reduce((total, term) => total + (document.title.toLowerCase().includes(term) ? 5 : 0) + (searchable.includes(term) ? 1 : 0), 0);
      return { document, score: (exactTarget ? 20 : 0) + outcomeScore, outcomeScore };
    })
    .filter((item) => requestedOutcomes.length === 0 || item.outcomeScore > 0)
    .sort((a, b) => b.score - a.score || (b.document.metadata.published_at ?? "").localeCompare(a.document.metadata.published_at ?? ""))
    .slice(0, 10);
  const metrics = await openAlexMetrics(scored.map(({ document }) => document.source_document_id.replace("pubmed:", "")));
  const groups = scored.length ? [{
    name: ingredient.label,
    tags: outcomeTags(query),
    updatedAt: scored.map(({ document }) => document.metadata.last_checked_at).filter(Boolean).sort().at(-1) ?? null,
    articles: scored.map(({ document }) => {
      const pmid = document.source_document_id.replace("pubmed:", "");
      const abstract = document.sections.map((section) => section.text).join(" ");
      return {
        id: document.source_document_id, title: document.title, sourceUrl: document.source_uri, pmid,
        journal: journals.get(pmid) ?? null, publishedYear: document.metadata.published_at?.slice(0, 4) ?? null,
        publishedAt: document.metadata.published_at ?? null,
        studyType: document.metadata.publication_types?.filter((type) => type !== "Journal Article").join(" · ") || "Journal article",
        participants: participantCount(abstract), result: excerpt(document), conflicts: null, funding: null,
        citations: metrics.get(pmid)?.citations ?? null, twoYearMeanCitedness: metrics.get(pmid)?.twoYearMeanCitedness ?? null,
      };
    }),
  }] : [];
  return NextResponse.json({ groups, suggestions, selectedEntity: ingredient.label, documentCount: documents.length });
}
