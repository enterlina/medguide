export type EvidenceRecord = {
  id: string;
  title: string;
  source: "PubMed" | "PMC" | "ClinicalTrials.gov";
  sourceUrl: string;
  status:
    | "supporting"
    | "contradicting"
    | "no_significant_effect"
    | "uncertain"
    | "not_applicable"
    | "registry_results_missing";
  statusLabel: string;
  form: string;
  population: string;
  passage: string;
  identifiers: string;
  publishedYear?: string;
  studyType?: string;
  journal?: string;
  journalRating?: string;
  conflictOfInterest?: string;
};

export const evidenceStatusFilters: Array<{ value: EvidenceRecord["status"] | "all"; label: string }> = [
  { value: "all", label: "All evidence" },
  { value: "supporting", label: "Reports benefit" },
  { value: "no_significant_effect", label: "No significant effect" },
  { value: "contradicting", label: "Contradicting" },
  { value: "uncertain", label: "Uncertain" },
  { value: "registry_results_missing", label: "Results not posted" },
  { value: "not_applicable", label: "Not directly applicable" },
];

export const evidenceRecords: EvidenceRecord[] = [
  {
    id: "pubmed:23853635",
    title: "Magnesium supplementation and primary insomnia in elderly adults",
    source: "PubMed",
    sourceUrl: "https://pubmed.ncbi.nlm.nih.gov/23853635/",
    status: "no_significant_effect",
    statusLabel: "No statistically significant effect detected for this outcome",
    form: "Salt not reported in abstract",
    population: "46 older adults with primary insomnia",
    passage:
      "The abstract reports changes in several subjective outcomes, while total sleep time did not show a significant between-group difference (P = 0.37).",
    identifiers: "PMID 23853635 · PMCID PMC3703169",
    publishedYear: "2012",
    studyType: "Randomized double-blind trial",
    journal: "Journal of Research in Medical Sciences",
    journalRating: "Not assessed",
    conflictOfInterest: "None declared",
  },
  {
    id: "pubmed:33865376",
    title: "Oral magnesium for insomnia in older adults: systematic review",
    source: "PubMed",
    sourceUrl: "https://pubmed.ncbi.nlm.nih.gov/33865376/",
    status: "uncertain",
    statusLabel: "Uncertain result",
    form: "Mixed preparations",
    population: "Older adults across three trials",
    passage:
      "The abstract reports three randomized trials with 151 participants and describes evidence quality as low to very low.",
    identifiers: "PMID 33865376 · PMCID PMC8053283",
    publishedYear: "2021",
    studyType: "Systematic review and meta-analysis",
    journalRating: "Not assessed",
    conflictOfInterest: "Not assessed",
  },
  {
    id: "pubmed:39252819",
    title: "Magnesium L-threonate in adults with self-reported sleep problems",
    source: "PubMed",
    sourceUrl: "https://pubmed.ncbi.nlm.nih.gov/39252819/",
    status: "supporting",
    statusLabel: "Source reports benefit",
    form: "Magnesium L-threonate",
    population: "Adults with self-reported sleep problems",
    passage:
      "This randomized trial studied magnesium L-threonate. Its findings must not be generalized to other magnesium salts.",
    identifiers: "PMID 39252819 · PMCID PMC11381753",
    publishedYear: "2024",
    studyType: "Randomized double-blind trial",
    journal: "Sleep Medicine: X",
    journalRating: "Not assessed",
    conflictOfInterest: "Disclosures reported; review source",
  },
  {
    id: "trial:NCT04642313",
    title: "Magnesium gluconate versus potassium in diabetes and insomnia",
    source: "ClinicalTrials.gov",
    sourceUrl: "https://clinicaltrials.gov/study/NCT04642313",
    status: "registry_results_missing",
    statusLabel: "Results not posted in registry",
    form: "Magnesium gluconate, reported 250 mg",
    population: "Adults with diabetes and insomnia",
    passage:
      "Results are not posted in the trial registry, and the record does not list a linked publication. Published results may need to be searched separately.",
    identifiers: "NCT04642313",
    publishedYear: "2020",
    studyType: "Trial registry record",
    journalRating: "Not applicable",
    conflictOfInterest: "Not assessed",
  },
  {
    id: "trial:NCT05236504",
    title: "Combined melatonin and magnesium supplement for sleep disturbance",
    source: "ClinicalTrials.gov",
    sourceUrl: "https://clinicaltrials.gov/study/NCT05236504",
    status: "not_applicable",
    statusLabel: "Not directly applicable",
    form: "Melatonin + magnesium pod",
    population: "Adults with sleep disturbance",
    passage:
      "Because the intervention combines melatonin and magnesium, it cannot isolate the effect of magnesium alone. No results are posted in the fixture.",
    identifiers: "NCT05236504",
    publishedYear: "2022",
    studyType: "Trial registry record",
    journalRating: "Not applicable",
    conflictOfInterest: "Not assessed",
  },
];

export type MedicationEvidence = {
  id: string;
  name: string;
  aliases: string[];
  category: string;
  route: string;
  ingredients: string[];
  corpusLabel: string;
  evidenceLevel: string;
  evidenceLevelTone: "limited" | "moderate" | "high";
  statusLabel: string;
  scope: string;
  effectiveness: {
    condition: string;
    certainty: string;
    headline: string;
    statement: string;
    sourceLabel: string;
    sourceUrl: string;
  };
  comparison: {
    directEvidence: string;
    bottomLine: string;
    formulationMatch: string;
    population: string;
    safetyCoverage: string;
    fundingTransparency: string;
  };
  summary: string;
  limitations: string;
  studyTypes: string;
  participants: string;
  population: string;
  studiedForms: string;
  studyDuration: string;
  measuredOutcomes: string;
  safety: {
    contraindications: string;
    interactions: string;
    food: string;
    adverseEffects: string;
  };
  independence: {
    manufacturer: string;
    sponsors: string;
    investigators: string;
    funding: string;
    conflicts: string;
    replication: string;
    sponsorOverlap: "match" | "no_match" | "not_assessed";
  };
  evidence: EvidenceRecord[];
  liveSources: {
    lastUpdatedAt: string;
    pubmedDiscoveryQuery: string;
    pubmedIds: string[];
    trials: Array<{ id: string; overallStatus: string; hasResults: boolean; sourceUpdatedAt: string }>;
  };
  questionCard?: {
    question: string;
    ingredient: string;
    outcome: string;
    summary: string[];
    relevance: Array<{ label: string; status: "topic_match" | "to_verify" }>;
  };
  supplementCard?: {
    tags: string[];
    outcomes: Array<{
      name: string;
      description: string;
      status: "review_pending" | "not_evaluated";
    }>;
  };
};

export const medicationEvidence: MedicationEvidence[] = [
  {
    id: "magnesium-glycinate",
    name: "Magnesium glycinate",
    aliases: ["magnesium glycinate", "magnesium bisglycinate", "glycinate magnesium"],
    category: "Dietary supplement · Mineral compound",
    route: "Oral",
    ingredients: ["Magnesium", "Glycinate"],
    corpusLabel: "Candidate evidence awaiting extraction and validation",
    evidenceLevel: "Evidence analysis pending",
    evidenceLevelTone: "limited",
    statusLabel: "Not verified",
    scope: "Sleep quality",
    effectiveness: {
      condition: "Sleep quality",
      certainty: "Not assessed",
      headline: "Direct evidence has not been verified",
      statement: "There is not yet enough verified evidence in the current MedGuide evaluation to conclude whether magnesium glycinate improves sleep quality.",
      sourceLabel: "PubMed evidence analysis pending",
      sourceUrl: "https://pubmed.ncbi.nlm.nih.gov/?term=magnesium+glycinate+sleep",
    },
    comparison: {
      directEvidence: "To verify",
      bottomLine: "Insufficient verified evidence",
      formulationMatch: "To verify",
      population: "To verify",
      safetyCoverage: "Not evaluated",
      fundingTransparency: "Not evaluated",
    },
    summary: "No verified conclusion is available yet for magnesium glycinate and sleep quality.",
    limitations: "Studies of other magnesium formulations are indirect evidence and must not be treated as proof for glycinate.",
    studyTypes: "Awaiting extraction",
    participants: "Awaiting extraction",
    population: "Awaiting extraction",
    studiedForms: "Magnesium glycinate and related formulations",
    studyDuration: "Awaiting extraction",
    measuredOutcomes: "Awaiting extraction",
    safety: {
      contraindications: "Requires verification against appropriate safety sources.",
      interactions: "Requires verification against appropriate safety sources.",
      food: "Requires verification against appropriate safety sources.",
      adverseEffects: "Requires verification against appropriate safety sources.",
    },
    independence: {
      manufacturer: "Not applicable to an ingredient-level profile",
      sponsors: "Awaiting extraction",
      investigators: "Awaiting extraction",
      funding: "Awaiting extraction",
      conflicts: "Awaiting extraction",
      replication: "Not verified",
      sponsorOverlap: "not_assessed",
    },
    evidence: [],
    liveSources: {
      lastUpdatedAt: "2026-10-28T12:00:00.000Z",
      pubmedDiscoveryQuery: "((magnesium glycinate[Title/Abstract]) OR (magnesium bisglycinate[Title/Abstract])) AND (sleep[Title/Abstract] OR insomnia[Title/Abstract])",
      pubmedIds: [],
      trials: [],
    },
    questionCard: {
      question: "Does magnesium glycinate improve sleep quality?",
      ingredient: "Magnesium glycinate",
      outcome: "Sleep quality",
      summary: [
        "There is not yet enough verified evidence in the current MedGuide evaluation to conclude whether magnesium glycinate improves sleep quality.",
        "Studies of other magnesium formulations may provide indirect evidence, but should not be treated as proof for glycinate.",
      ],
      relevance: [
        { label: "Magnesium + sleep", status: "topic_match" },
        { label: "Magnesium glycinate specifically", status: "to_verify" },
        { label: "Healthy adults", status: "to_verify" },
        { label: "Sleep quality outcome", status: "to_verify" },
      ],
    },
    supplementCard: {
      tags: ["Magnesium", "Glycinate"],
      outcomes: [
        { name: "Sleep quality", description: "Magnesium glycinate and related formulations", status: "review_pending" },
        { name: "Muscle function", description: "Relevant studies to be retrieved", status: "not_evaluated" },
        { name: "Magnesium deficiency", description: "Relevant studies to be retrieved", status: "not_evaluated" },
      ],
    },
  },
  {
    id: "magnesium-sleep",
    name: "Magnesium",
    aliases: ["magnesium", "magnesium supplement", "magnesium l-threonate", "magnesium gluconate"],
    category: "Mineral supplement",
    route: "Oral",
    ingredients: ["Magnesium"],
    corpusLabel: "Research on magnesium and sleep outcomes",
    evidenceLevel: "Certainty not assessed",
    evidenceLevelTone: "limited",
    statusLabel: "Evidence inconclusive",
    scope: "Sleep outcomes in adults",
    effectiveness: {
      condition: "Insomnia and sleep quality",
      certainty: "Low to very low",
      headline: "For sleep outcomes in older adults",
      statement: "A systematic review of three small randomized trials (151 participants) rates the evidence quality as low to very low; results differ by magnesium form and outcome.",
      sourceLabel: "PMID 33865376 · PubMed",
      sourceUrl: "https://pubmed.ncbi.nlm.nih.gov/33865376/",
    },
    comparison: {
      directEvidence: "Partial — evidence covers several magnesium forms",
      bottomLine: "Inconclusive for sleep",
      formulationMatch: "Mixed; results depend on magnesium form",
      population: "Adults, mainly older adults with sleep problems",
      safetyCoverage: "Not covered by these studies",
      fundingTransparency: "Incomplete",
    },
    summary: "Small studies of different magnesium forms report mixed sleep outcomes.",
    limitations: "Forms, doses and populations differ. A non-significant result does not prove no effect.",
    studyTypes: "Randomized trials · systematic review · trial registrations",
    participants: "151 across three trials in the review; records may overlap",
    population: "Adults with insomnia or self-reported sleep problems; mainly older adults",
    studiedForms: "Mixed forms · L-threonate · gluconate · magnesium plus melatonin",
    studyDuration: "8 weeks in one trial; other durations vary",
    measuredOutcomes: "Sleep quality · insomnia severity · sleep duration · daytime function",
    safety: {
      contraindications: "",
      interactions: "",
      food: "",
      adverseEffects: "",
    },
    independence: {
      manufacturer: "Commercial products are not mapped to tested interventions",
      sponsors: "Study-specific sponsor extraction requires review",
      investigators: "Available source records list study authors/investigators; independence has not been adjudicated",
      funding: "Funding differs by study and requires study-by-study review",
      conflicts: "Not consistently verified across all source records",
      replication: "Not verified",
      sponsorOverlap: "not_assessed",
    },
    evidence: evidenceRecords,
    liveSources: {
      lastUpdatedAt: "2026-10-26T17:30:00.000Z",
      pubmedDiscoveryQuery: "(magnesium[Title/Abstract]) AND (sleep[Title/Abstract] OR insomnia[Title/Abstract]) AND humans[MeSH Terms]",
      pubmedIds: ["23853635", "33865376", "39252819"],
      trials: [
        { id: "NCT04642313", overallStatus: "UNKNOWN", hasResults: false, sourceUpdatedAt: "2020-11-24" },
        { id: "NCT05236504", overallStatus: "UNKNOWN", hasResults: false, sourceUpdatedAt: "2022-04-01" },
      ],
    },
  },
  {
    id: "magne-b6",
    name: "Magne-B6",
    aliases: ["magne b6", "magne-b6", "magnesium b6", "magnesium pyridoxine", "magnesium"],
    category: "Commercial magnesium + pyridoxine product family",
    route: "Oral",
    ingredients: ["Magnesium", "Vitamin B6 (pyridoxine)"],
    corpusLabel: "Research on related oral magnesium preparations",
    evidenceLevel: "Indirect evidence from oral magnesium studies",
    evidenceLevelTone: "limited",
    statusLabel: "Related magnesium research",
    scope: "Sleep and insomnia",
    effectiveness: {
      condition: "Insomnia and sleep quality",
      certainty: "Low to very low",
      headline: "Results remain uncertain",
      statement: "A systematic review combined three randomized trials of oral magnesium in 151 older adults with insomnia. The authors rated the evidence as low to very low quality. The trials used other magnesium preparations, so they do not answer whether Magne-B6 itself improves sleep.",
      sourceLabel: "Related systematic review · PMID 33865376",
      sourceUrl: "https://pubmed.ncbi.nlm.nih.gov/33865376/",
    },
    comparison: {
      directEvidence: "No direct Magne-B6 study identified",
      bottomLine: "No product-specific conclusion",
      formulationMatch: "No verified match",
      population: "No product-specific population",
      safetyCoverage: "Not assessed for this product",
      fundingTransparency: "Not applicable without a direct study",
    },
    summary: "One systematic review examined oral magnesium for insomnia in older adults. It included three randomized trials with 151 participants, but the evidence was low quality and the studied preparations were not Magne-B6.",
    limitations: "The review studied other oral magnesium preparations in older adults. Its results may not apply to Magne-B6, other doses, or younger people.",
    studyTypes: "Systematic review of 3 randomized trials",
    participants: "151 participants across 3 trials",
    population: "Older adults with insomnia",
    studiedForms: "Various oral magnesium preparations",
    studyDuration: "",
    measuredOutcomes: "Insomnia symptoms and sleep-related outcomes",
    safety: {
      contraindications: "",
      interactions: "",
      food: "",
      adverseEffects: "",
    },
    independence: {
      manufacturer: "Not normalized across country-specific product registrations",
      sponsors: "No direct product-specific study identified",
      investigators: "No direct product-specific study identified",
      funding: "Not applicable until a direct study is admitted",
      conflicts: "Not assessed",
      replication: "Not verified",
      sponsorOverlap: "not_assessed",
    },
    evidence: [
      {
        id: "related:pubmed:33865376:magne-b6",
        title: "Oral magnesium for insomnia in older adults: systematic review",
        source: "PubMed",
        sourceUrl: "https://pubmed.ncbi.nlm.nih.gov/33865376/",
        status: "not_applicable",
        statusLabel: "Related research on oral magnesium",
        form: "Various oral magnesium preparations; not Magne-B6",
        population: "151 older adults across three randomized trials",
        passage: "The review found that the available trials were small and the overall evidence was low to very low quality. It cannot establish whether Magne-B6 improves sleep because that product was not studied.",
        identifiers: "PMID 33865376 · PMCID PMC8053283",
        publishedYear: "2021",
        studyType: "Systematic review and meta-analysis",
        journalRating: "Not assessed",
        conflictOfInterest: "Not assessed",
      },
    ],
    liveSources: {
      lastUpdatedAt: "2026-10-26T17:30:00.000Z",
      pubmedDiscoveryQuery: "((Magne-B6[Title/Abstract]) OR (magnesium[Title/Abstract] AND pyridoxine[Title/Abstract])) AND (sleep[Title/Abstract] OR insomnia[Title/Abstract])",
      pubmedIds: [],
      trials: [],
    },
  },
];

