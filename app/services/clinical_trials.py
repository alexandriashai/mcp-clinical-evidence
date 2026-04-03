"""ClinicalTrials.gov API v2 client."""

import httpx

BASE_URL = "https://clinicaltrials.gov/api/v2"

_client = httpx.AsyncClient(timeout=15.0)


async def search_trials(
    condition: str = "",
    intervention: str = "",
    status: str = "",
    max_results: int = 10,
) -> list[dict]:
    """Search clinical trials by condition and/or intervention."""
    params = {"pageSize": min(max_results, 100)}
    if condition:
        params["query.cond"] = condition
    if intervention:
        params["query.intr"] = intervention
    if status:
        params["filter.overallStatus"] = status  # e.g., "RECRUITING", "COMPLETED"

    resp = await _client.get(f"{BASE_URL}/studies", params=params)
    resp.raise_for_status()
    data = resp.json()

    trials = []
    for study in data.get("studies", []):
        proto = study.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        status_mod = proto.get("statusModule", {})
        desc = proto.get("descriptionModule", {})
        design = proto.get("designModule", {})
        arms = proto.get("armsInterventionsModule", {})

        interventions = [
            i.get("name", "") for i in arms.get("interventions", [])
        ]

        trials.append({
            "nct_id": ident.get("nctId", ""),
            "title": ident.get("briefTitle", ""),
            "status": status_mod.get("overallStatus", ""),
            "start_date": status_mod.get("startDateStruct", {}).get("date", ""),
            "completion_date": status_mod.get("completionDateStruct", {}).get("date", ""),
            "brief_summary": desc.get("briefSummary", ""),
            "study_type": design.get("studyType", ""),
            "phases": design.get("phases", []),
            "interventions": interventions,
            "url": f"https://clinicaltrials.gov/study/{ident.get('nctId', '')}",
        })

    return trials


async def get_trial(nct_id: str) -> dict | None:
    """Get full details for a specific trial by NCT ID."""
    resp = await _client.get(f"{BASE_URL}/studies/{nct_id}")
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()

    proto = data.get("protocolSection", {})
    ident = proto.get("identificationModule", {})
    status_mod = proto.get("statusModule", {})
    desc = proto.get("descriptionModule", {})
    eligibility = proto.get("eligibilityModule", {})
    contacts = proto.get("contactsLocationsModule", {})

    return {
        "nct_id": ident.get("nctId", ""),
        "title": ident.get("officialTitle", ident.get("briefTitle", "")),
        "status": status_mod.get("overallStatus", ""),
        "brief_summary": desc.get("briefSummary", ""),
        "detailed_description": desc.get("detailedDescription", ""),
        "eligibility_criteria": eligibility.get("eligibilityCriteria", ""),
        "sex": eligibility.get("sex", ""),
        "min_age": eligibility.get("minimumAge", ""),
        "max_age": eligibility.get("maximumAge", ""),
        "locations": [
            {
                "facility": loc.get("facility", ""),
                "city": loc.get("city", ""),
                "state": loc.get("state", ""),
                "country": loc.get("country", ""),
            }
            for loc in contacts.get("locations", [])[:10]
        ],
        "url": f"https://clinicaltrials.gov/study/{ident.get('nctId', '')}",
    }
