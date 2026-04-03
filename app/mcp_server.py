"""MCP Server for Clinical Evidence — PubMed, ClinicalTrials.gov, OpenFDA."""

from dotenv import load_dotenv
load_dotenv()

import asyncio
from mcp.server.fastmcp import FastMCP
from .services import pubmed, clinical_trials, openfda

mcp = FastMCP(
    "Clinical Evidence",
    instructions="Search biomedical literature, clinical trials, and FDA drug data "
                 "for medical necessity evidence in insurance litigation. "
                 "37M+ PubMed citations, 500K+ clinical trials, FDA drug labels and adverse events.",
    host="0.0.0.0",
    port=8111,
)


@mcp.tool()
async def pubmed_search(
    query: str,
    max_results: int = 10,
    article_type: str = "",
) -> str:
    """Search PubMed for biomedical literature. Returns titles, authors, journals, and abstracts.

    Args:
        query: Search terms (e.g., "CPAP therapy obstructive sleep apnea efficacy")
        max_results: Number of results (default 10, max 20)
        article_type: Filter by type — "systematic review", "randomized controlled trial", "meta-analysis", "clinical trial", or "" for all
    """
    articles = await pubmed.search_with_details(query, min(max_results, 20), article_type)

    if not articles:
        return f"No PubMed articles found for: {query}"

    lines = [f"**PubMed results for:** {query}\n"]
    for a in articles:
        lines.append(f"### {a['title']}")
        lines.append(f"**Authors:** {a['authors']}")
        lines.append(f"**Journal:** {a['journal']} ({a['pub_date']})")
        lines.append(f"**PMID:** [{a['pmid']}]({a['url']})" + (f" | DOI: {a['doi']}" if a['doi'] else ""))
        if a.get("abstract"):
            abstract = a["abstract"][:600]
            if len(a["abstract"]) > 600:
                abstract += "..."
            lines.append(f"\n{abstract}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def clinical_trial_search(
    condition: str = "",
    intervention: str = "",
    status: str = "",
    max_results: int = 10,
) -> str:
    """Search ClinicalTrials.gov for clinical trials by condition and/or intervention.

    Args:
        condition: Disease or condition (e.g., "major depressive disorder")
        intervention: Treatment or drug (e.g., "ketamine", "cognitive behavioral therapy")
        status: Filter by status — "RECRUITING", "COMPLETED", "ACTIVE_NOT_RECRUITING", or "" for all
        max_results: Number of results (default 10, max 20)
    """
    trials = await clinical_trials.search_trials(condition, intervention, status, min(max_results, 20))

    if not trials:
        return f"No clinical trials found for condition='{condition}', intervention='{intervention}'"

    lines = [f"**Clinical trials" + (f" for {condition}" if condition else "") + (f" with {intervention}" if intervention else "") + ":**\n"]
    for t in trials:
        phases = ", ".join(t["phases"]) if t["phases"] else "N/A"
        interventions = ", ".join(t["interventions"][:3]) if t["interventions"] else "N/A"
        lines.append(f"### {t['title']}")
        lines.append(f"**NCT ID:** [{t['nct_id']}]({t['url']}) | **Status:** {t['status']} | **Phase:** {phases}")
        lines.append(f"**Interventions:** {interventions}")
        if t.get("brief_summary"):
            summary = t["brief_summary"][:400]
            if len(t["brief_summary"]) > 400:
                summary += "..."
            lines.append(f"\n{summary}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def clinical_trial_detail(nct_id: str) -> str:
    """Get full details for a specific clinical trial by NCT ID.

    Args:
        nct_id: The ClinicalTrials.gov identifier (e.g., "NCT03872505")
    """
    trial = await clinical_trials.get_trial(nct_id)
    if not trial:
        return f"Trial {nct_id} not found."

    lines = [
        f"## {trial['title']}",
        f"**NCT ID:** [{trial['nct_id']}]({trial['url']})",
        f"**Status:** {trial['status']}",
        "",
        "### Summary",
        trial.get("brief_summary", "N/A"),
        "",
    ]

    if trial.get("detailed_description"):
        desc = trial["detailed_description"][:800]
        lines.append("### Detailed Description")
        lines.append(desc)
        lines.append("")

    if trial.get("eligibility_criteria"):
        criteria = trial["eligibility_criteria"][:800]
        lines.append("### Eligibility Criteria")
        lines.append(criteria)
        lines.append("")

    if trial.get("locations"):
        lines.append("### Locations")
        for loc in trial["locations"][:5]:
            lines.append(f"- {loc.get('facility', 'N/A')}, {loc.get('city', '')}, {loc.get('state', '')} {loc.get('country', '')}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def drug_label(drug_name: str) -> str:
    """Look up FDA-approved drug labeling — indications, warnings, contraindications, adverse reactions.

    Args:
        drug_name: Brand or generic drug name (e.g., "Ozempic", "metformin", "duloxetine")
    """
    labels = await openfda.search_drug_labels(drug_name, limit=3)

    if not labels:
        return f"No FDA drug labels found for: {drug_name}"

    lines = [f"**FDA Drug Label for:** {drug_name}\n"]
    for l in labels:
        lines.append(f"### {l['brand_name']} ({l['generic_name']})")
        lines.append(f"**Manufacturer:** {l['manufacturer']}")
        lines.append(f"**Route:** {l['route']}")
        if l.get("indications_and_usage"):
            lines.append(f"\n**Indications:** {l['indications_and_usage']}")
        if l.get("warnings"):
            lines.append(f"\n**Warnings:** {l['warnings']}")
        if l.get("contraindications"):
            lines.append(f"\n**Contraindications:** {l['contraindications']}")
        if l.get("adverse_reactions"):
            lines.append(f"\n**Adverse Reactions:** {l['adverse_reactions']}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def drug_adverse_events(drug_name: str, limit: int = 15) -> str:
    """Search FDA adverse event reports (FAERS) for a drug — shows most commonly reported reactions.
    Critical for arguing medical necessity of alternative treatments.

    Args:
        drug_name: Brand or generic drug name
        limit: Number of top reactions to return (default 15)
    """
    result = await openfda.search_adverse_events(drug_name, min(limit, 25))

    if result["total_reports"] == 0:
        return f"No adverse event reports found for: {drug_name}"

    lines = [
        f"**FDA Adverse Event Reports for:** {drug_name}",
        f"**Total reports:** {result['total_reports']:,}\n",
        "**Most commonly reported reactions:**",
    ]
    for r in result["top_reactions"]:
        lines.append(f"- {r['reaction']}: {r['count']:,} reports")

    return "\n".join(lines)


@mcp.tool()
async def drug_approvals(drug_name: str) -> str:
    """Search FDA drug approval history — application numbers, sponsors, submission timeline.

    Args:
        drug_name: Brand or generic drug name
    """
    approvals = await openfda.search_drug_approvals(drug_name)

    if not approvals:
        return f"No FDA approval records found for: {drug_name}"

    lines = [f"**FDA Approval History for:** {drug_name}\n"]
    for a in approvals:
        lines.append(f"### {a['brand_name']} ({a['generic_name']})")
        lines.append(f"**Application:** {a['application_number']} | **Sponsor:** {a['sponsor_name']}")
        if a.get("submissions"):
            lines.append("**Submissions:**")
            for s in a["submissions"]:
                lines.append(f"- {s['type']} #{s['number']}: {s['status']} ({s['status_date']})")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def medical_evidence_search(
    condition: str,
    treatment: str = "",
    evidence_type: str = "all",
) -> str:
    """Comprehensive evidence search across PubMed, ClinicalTrials.gov, and FDA.
    Use this for medical necessity arguments — finds clinical evidence, active trials, and FDA data.

    Args:
        condition: The medical condition (e.g., "treatment-resistant depression")
        treatment: The specific treatment in question (e.g., "transcranial magnetic stimulation")
        evidence_type: "all", "pubmed", "trials", or "fda"
    """
    query = f"{condition} {treatment}".strip()
    sections = []

    if evidence_type in ("all", "pubmed"):
        articles = await pubmed.search_with_details(
            f"{query} systematic review OR meta-analysis", max_results=5, article_types=""
        )
        if articles:
            lines = ["## PubMed — Systematic Reviews & Meta-Analyses\n"]
            for a in articles:
                lines.append(f"- **{a['title']}** — {a['journal']} ({a['pub_date']}) [PMID: {a['pmid']}]({a['url']})")
            sections.append("\n".join(lines))

    if evidence_type in ("all", "trials") and treatment:
        trials = await clinical_trials.search_trials(condition, treatment, max_results=5)
        if trials:
            lines = ["## ClinicalTrials.gov — Active Research\n"]
            for t in trials:
                phases = ", ".join(t["phases"]) if t["phases"] else "N/A"
                lines.append(f"- **{t['title']}** — {t['status']}, Phase {phases} [{t['nct_id']}]({t['url']})")
            sections.append("\n".join(lines))

    if evidence_type in ("all", "fda") and treatment:
        labels = await openfda.search_drug_labels(treatment, limit=2)
        if labels:
            lines = ["## FDA — Drug Labeling\n"]
            for l in labels:
                lines.append(f"- **{l['brand_name']}** ({l['generic_name']}) — {l['manufacturer']}")
                if l.get("indications_and_usage"):
                    lines.append(f"  Indications: {l['indications_and_usage'][:200]}")
            sections.append("\n".join(lines))

    if not sections:
        return f"No evidence found for condition='{condition}', treatment='{treatment}'"

    header = f"# Medical Evidence: {condition}" + (f" + {treatment}" if treatment else "") + "\n"
    return header + "\n\n".join(sections)
