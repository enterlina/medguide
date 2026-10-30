import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";

export type EntityMatch = "exact" | "related_form" | "different" | "unclear";
export type OutcomeMatch = "direct" | "indirect" | "not_measured" | "unclear";
export type ReviewDecision = "include" | "include_as_indirect" | "exclude" | "needs_review";

type Link = {
  pmid: string;
  entity_id: string;
  name: string;
  entity_type: string;
  query: string;
};

type Article = {
  pmid: string;
  title: string;
  journal?: string;
  published_at?: string;
  publication_types?: string[];
  integrity_status?: string;
  abstract: string;
  source_url: string;
};

export type EvidenceReview = {
  key: string;
  entityId: string;
  pmid: string;
  entityMatch: EntityMatch;
  outcomeMatch: OutcomeMatch;
  decision: ReviewDecision;
  comment: string;
  reviewMode: "manual" | "bulk_candidate";
  reviewedAt: string;
};

type Store = {
  version: "pubmed_entity_review_v1";
  updatedAt: string | null;
  reviews: Record<string, EvidenceReview>;
};

const root = process.cwd();
const discoveryRoot = path.join(root, "medguide-evidence-engine/data/catalog/discovery");
const storePath = path.join(
  root,
  "medguide-evidence-engine/artifacts/evidence-review/pubmed_entity_review.json",
);

export function reviewKey(entityId: string, pmid: string) {
  return `${entityId}::${pmid}`;
}

async function readJson<T>(filename: string): Promise<T> {
  return JSON.parse(await readFile(filename, "utf8")) as T;
}

export async function readReviewStore(): Promise<Store> {
  try {
    return await readJson<Store>(storePath);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    return { version: "pubmed_entity_review_v1", updatedAt: null, reviews: {} };
  }
}

async function writeReviewStore(store: Store) {
  await mkdir(path.dirname(storePath), { recursive: true });
  const temporary = `${storePath}.${process.pid}.tmp`;
  await writeFile(temporary, `${JSON.stringify(store, null, 2)}\n`, "utf8");
  await rename(temporary, storePath);
}

export async function loadEvidenceReviewQueue() {
  const [links, articles, store] = await Promise.all([
    readJson<Link[]>(path.join(discoveryRoot, "entity_publication_links.json")),
    readJson<Article[]>(path.join(discoveryRoot, "pubmed_recent.json")),
    readReviewStore(),
  ]);
  const articleByPmid = new Map(articles.map((article) => [article.pmid, article]));
  const items = links.map((link) => {
    const article = articleByPmid.get(link.pmid);
    return {
      key: reviewKey(link.entity_id, link.pmid),
      entityId: link.entity_id,
      entityName: link.name,
      entityType: link.entity_type,
      query: link.query,
      article,
      review: store.reviews[reviewKey(link.entity_id, link.pmid)] ?? null,
    };
  });
  return { items, updatedAt: store.updatedAt };
}

export async function saveEvidenceReview(
  value: Omit<EvidenceReview, "key" | "reviewMode" | "reviewedAt">,
) {
  const store = await readReviewStore();
  const key = reviewKey(value.entityId, value.pmid);
  const reviewedAt = new Date().toISOString();
  store.reviews[key] = { ...value, key, reviewMode: "manual", reviewedAt };
  store.updatedAt = reviewedAt;
  await writeReviewStore(store);
  return store.reviews[key];
}

export async function keepAllUnreviewedAsCandidates() {
  const queue = await loadEvidenceReviewQueue();
  const store = await readReviewStore();
  const reviewedAt = new Date().toISOString();
  let changed = 0;
  for (const item of queue.items) {
    if (store.reviews[item.key]) continue;
    store.reviews[item.key] = {
      key: item.key,
      entityId: item.entityId,
      pmid: item.article?.pmid ?? item.key.split("::").at(-1) ?? "",
      entityMatch: "unclear",
      outcomeMatch: "unclear",
      decision: "needs_review",
      comment: "Retained as a candidate by bulk screening; not scientifically validated.",
      reviewMode: "bulk_candidate",
      reviewedAt,
    };
    changed += 1;
  }
  store.updatedAt = reviewedAt;
  await writeReviewStore(store);
  return { changed, total: queue.items.length };
}
