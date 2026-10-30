from scripts.download_bioasq_pubmed import extract_pmid, parse_articles


def test_parse_pubmed_article() -> None:
    payload = b"""<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>
    <Article><ArticleTitle>Test title</ArticleTitle><Journal><JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue><Title>Test Journal</Title></Journal><Abstract>
    <AbstractText Label="RESULTS">Supported result.</AbstractText></Abstract>
    <PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList>
    </Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"""
    record = parse_articles(payload)[0]
    assert record["pmid"] == "123"
    assert record["abstract"] == "Supported result."
    assert record["abstract_sections"][0]["section"] == "RESULTS"
    assert record["publication_year"] == 2025
    assert record["journal"] == "Test Journal"


def test_extract_pmid_variants() -> None:
    assert extract_pmid("http://www.ncbi.nlm.nih.gov/pubmed/123") == "123"
    assert extract_pmid("https://pubmed.ncbi.nlm.nih.gov/456/") == "456"
