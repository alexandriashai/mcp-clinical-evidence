"""Clinical Evidence MCP Server — FastAPI application."""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .services import pubmed, clinical_trials, openfda

app = FastAPI(
    title="Clinical Evidence MCP Server",
    description="Search PubMed (37M+ citations), ClinicalTrials.gov (500K+ trials), "
                "and OpenFDA (drug labels, adverse events, approvals) for medical necessity evidence.",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# MCP protocol runs as separate process on port 8111 — see mcp_server.py


@app.get("/health")
async def health():
    return {"status": "ok", "sources": ["pubmed", "clinicaltrials.gov", "openfda"]}


@app.get("/")
def root():
    return {
        "name": "Clinical Evidence MCP Server",
        "version": "1.0.0",
        "docs": "/docs",
        "mcp": "https://evidence.wyldfyre.ai/mcp",
        "sources": {
            "pubmed": "37M+ biomedical citations via NCBI E-utilities",
            "clinicaltrials": "500K+ trials via ClinicalTrials.gov API v2",
            "openfda": "Drug labels, adverse events, approvals via OpenFDA",
        },
    }


@app.get("/pubmed/search")
async def pubmed_search(
    q: str = Query(..., description="Search terms"),
    limit: int = Query(10, ge=1, le=20),
    type: str = Query("", description="Article type filter: systematic review, randomized controlled trial, meta-analysis"),
):
    return await pubmed.search_with_details(q, limit, type)


@app.get("/trials/search")
async def trials_search(
    condition: str = Query("", description="Disease or condition"),
    intervention: str = Query("", description="Treatment or drug"),
    status: str = Query("", description="RECRUITING, COMPLETED, etc."),
    limit: int = Query(10, ge=1, le=20),
):
    return await clinical_trials.search_trials(condition, intervention, status, limit)


@app.get("/trials/{nct_id}")
async def trial_detail(nct_id: str):
    result = await clinical_trials.get_trial(nct_id)
    if not result:
        return {"error": f"Trial {nct_id} not found"}
    return result


@app.get("/fda/labels")
async def fda_labels(drug: str = Query(...), limit: int = Query(5, ge=1, le=20)):
    return await openfda.search_drug_labels(drug, limit)


@app.get("/fda/adverse-events")
async def fda_adverse_events(drug: str = Query(...), limit: int = Query(15, ge=1, le=25)):
    return await openfda.search_adverse_events(drug, limit)


@app.get("/fda/approvals")
async def fda_approvals(drug: str = Query(...)):
    return await openfda.search_drug_approvals(drug)
