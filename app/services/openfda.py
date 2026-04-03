"""OpenFDA API client — drug labels, adverse events, approvals."""

import os
import httpx

BASE_URL = "https://api.fda.gov"
API_KEY = os.getenv("OPENFDA_API_KEY", "")  # Optional, raises daily limit from 1K to 120K

_client = httpx.AsyncClient(timeout=15.0)


def _params(**kwargs) -> dict:
    p = {k: v for k, v in kwargs.items() if v}
    if API_KEY:
        p["api_key"] = API_KEY
    return p


async def search_drug_labels(query: str, limit: int = 5) -> list[dict]:
    """Search FDA drug labeling by drug name or active ingredient."""
    resp = await _client.get(f"{BASE_URL}/drug/label.json", params=_params(
        search=f'openfda.brand_name:"{query}" OR openfda.generic_name:"{query}"',
        limit=min(limit, 20),
    ))
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    data = resp.json()

    results = []
    for r in data.get("results", []):
        fda = r.get("openfda", {})
        results.append({
            "brand_name": ", ".join(fda.get("brand_name", ["Unknown"])),
            "generic_name": ", ".join(fda.get("generic_name", ["Unknown"])),
            "manufacturer": ", ".join(fda.get("manufacturer_name", [])),
            "route": ", ".join(fda.get("route", [])),
            "substance_name": ", ".join(fda.get("substance_name", [])),
            "indications_and_usage": (r.get("indications_and_usage", [""])[0] or "")[:500],
            "warnings": (r.get("warnings", [""])[0] or "")[:500],
            "contraindications": (r.get("contraindications", [""])[0] or "")[:500],
            "adverse_reactions": (r.get("adverse_reactions", [""])[0] or "")[:500],
        })
    return results


async def search_adverse_events(drug_name: str, limit: int = 10) -> dict:
    """Search FDA adverse event reports (FAERS) for a drug."""
    resp = await _client.get(f"{BASE_URL}/drug/event.json", params=_params(
        search=f'patient.drug.openfda.brand_name:"{drug_name}" OR patient.drug.openfda.generic_name:"{drug_name}"',
        count="patient.reaction.reactionmeddrapt.exact",
        limit=min(limit, 25),
    ))
    if resp.status_code == 404:
        return {"drug": drug_name, "total_reports": 0, "top_reactions": []}
    resp.raise_for_status()
    data = resp.json()

    meta = data.get("meta", {}).get("results", {})
    reactions = [
        {"reaction": r["term"], "count": r["count"]}
        for r in data.get("results", [])
    ]
    return {
        "drug": drug_name,
        "total_reports": meta.get("total", 0),
        "top_reactions": reactions,
    }


async def search_drug_approvals(drug_name: str, limit: int = 5) -> list[dict]:
    """Search FDA drug approval history."""
    resp = await _client.get(f"{BASE_URL}/drug/drugsfda.json", params=_params(
        search=f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
        limit=min(limit, 10),
    ))
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    data = resp.json()

    results = []
    for r in data.get("results", []):
        fda = r.get("openfda", {})
        submissions = r.get("submissions", [])
        results.append({
            "brand_name": ", ".join(fda.get("brand_name", [])),
            "generic_name": ", ".join(fda.get("generic_name", [])),
            "application_number": r.get("application_number", ""),
            "sponsor_name": r.get("sponsor_name", ""),
            "submissions": [
                {
                    "type": s.get("submission_type", ""),
                    "number": s.get("submission_number", ""),
                    "status": s.get("submission_status", ""),
                    "status_date": s.get("submission_status_date", ""),
                }
                for s in submissions[:5]
            ],
        })
    return results
