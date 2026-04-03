"""PubMed E-utilities client — search and fetch biomedical literature."""

import os
import httpx
from xml.etree import ElementTree

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
API_KEY = os.getenv("NCBI_API_KEY", "")  # Optional, raises rate limit from 3/s to 10/s

_client = httpx.AsyncClient(timeout=15.0)


def _params(**kwargs) -> dict:
    p = {k: v for k, v in kwargs.items() if v}
    if API_KEY:
        p["api_key"] = API_KEY
    return p


async def search(query: str, max_results: int = 20, article_types: str = "") -> list[str]:
    """Search PubMed and return PMIDs."""
    term = query
    if article_types:
        term += f" AND {article_types}[pt]"

    resp = await _client.get(f"{BASE_URL}/esearch.fcgi", params=_params(
        db="pubmed", term=term, retmode="json", retmax=max_results, sort="relevance",
    ))
    resp.raise_for_status()
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


async def fetch_summaries(pmids: list[str]) -> list[dict]:
    """Fetch article summaries for a list of PMIDs."""
    if not pmids:
        return []

    resp = await _client.get(f"{BASE_URL}/esummary.fcgi", params=_params(
        db="pubmed", id=",".join(pmids), retmode="json",
    ))
    resp.raise_for_status()
    data = resp.json()
    result = data.get("result", {})

    articles = []
    for pmid in pmids:
        info = result.get(pmid, {})
        if not info or "error" in info:
            continue
        articles.append({
            "pmid": pmid,
            "title": info.get("title", ""),
            "authors": ", ".join(a.get("name", "") for a in info.get("authors", [])[:5]),
            "journal": info.get("fulljournalname", info.get("source", "")),
            "pub_date": info.get("pubdate", ""),
            "doi": next((eid["value"] for eid in info.get("articleids", []) if eid.get("idtype") == "doi"), ""),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return articles


async def fetch_abstracts(pmids: list[str]) -> dict[str, str]:
    """Fetch full abstracts for PMIDs (XML format required)."""
    if not pmids:
        return {}

    resp = await _client.get(f"{BASE_URL}/efetch.fcgi", params=_params(
        db="pubmed", id=",".join(pmids), rettype="abstract", retmode="xml",
    ))
    resp.raise_for_status()

    abstracts = {}
    root = ElementTree.fromstring(resp.text)
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        abstract_el = article.find(".//AbstractText")
        if pmid_el is not None and abstract_el is not None:
            abstracts[pmid_el.text] = abstract_el.text or ""
    return abstracts


async def search_with_details(query: str, max_results: int = 10, article_types: str = "") -> list[dict]:
    """Search PubMed and return full article details with abstracts."""
    pmids = await search(query, max_results, article_types)
    if not pmids:
        return []

    summaries = await fetch_summaries(pmids)
    abstracts = await fetch_abstracts(pmids)

    for article in summaries:
        article["abstract"] = abstracts.get(article["pmid"], "")

    return summaries
