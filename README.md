# MCP Clinical Evidence

An MCP server aggregating clinical evidence from PubMed, ClinicalTrials.gov, and OpenFDA for medical necessity arguments in insurance litigation.

## Features

- **PubMed** — 37M+ biomedical citations with full abstracts via NCBI E-utilities
- **ClinicalTrials.gov** — 500K+ clinical trials via API v2
- **OpenFDA** — Drug labels, adverse event reports (FAERS), approval history
- **Comprehensive search** — cross-source evidence aggregation in one tool call
- **MCP protocol** endpoint for Claude.ai and other MCP clients
- **REST API** with Swagger docs

## MCP Tools

| Tool | Description |
|------|-------------|
| `pubmed_search` | Search biomedical literature with abstracts |
| `clinical_trial_search` | Search trials by condition and intervention |
| `clinical_trial_detail` | Full trial details by NCT ID |
| `drug_label` | FDA indications, warnings, contraindications, adverse reactions |
| `drug_adverse_events` | FAERS adverse event reports — top reactions for a drug |
| `drug_approvals` | FDA drug approval history and submissions |
| `medical_evidence_search` | Comprehensive cross-source search for medical necessity |

## Quick Start

### Connect via MCP (Claude.ai)

Add as a connector:
- **URL:** `https://evidence.wyldfyre.ai/mcp`
- **Authentication:** None required

### REST API

```bash
# PubMed search
curl "https://evidence.wyldfyre.ai/pubmed/search?q=ketamine+treatment+resistant+depression&limit=5"

# Clinical trials
curl "https://evidence.wyldfyre.ai/trials/search?condition=major+depressive+disorder&intervention=ketamine"

# FDA drug label
curl "https://evidence.wyldfyre.ai/fda/labels?drug=ozempic"

# Adverse events
curl "https://evidence.wyldfyre.ai/fda/adverse-events?drug=ozempic"

# Drug approvals
curl "https://evidence.wyldfyre.ai/fda/approvals?drug=metformin"
```

Full Swagger docs: https://evidence.wyldfyre.ai/docs

## Self-Hosting

```bash
pip install -r requirements.txt

# Optional: set API keys for higher rate limits
export NCBI_API_KEY="your-key"      # 10 req/s (vs 3 without)
export OPENFDA_API_KEY="your-key"   # 120K/day (vs 1K without)

# Start REST API
uvicorn app.main:app --host 0.0.0.0 --port 8110

# Start MCP server (separate process)
python run_mcp.py
```

API keys are free:
- NCBI: https://www.ncbi.nlm.nih.gov/account/ → Settings → API Key
- OpenFDA: https://open.fda.gov/apis/authentication/

## Data Sources

| Source | Coverage | Auth | Rate Limits |
|--------|----------|------|-------------|
| [PubMed](https://pubmed.ncbi.nlm.nih.gov/) | 37M+ citations | Optional key | 3/s free, 10/s with key |
| [ClinicalTrials.gov](https://clinicaltrials.gov/) | 500K+ trials | None | Not published |
| [OpenFDA](https://open.fda.gov/) | Drug labels, FAERS, approvals | Optional key | 1K/day free, 120K/day with key |

## Architecture

```
Claude.ai / MCP Client
        │
        ▼ MCP Protocol
evidence.wyldfyre.ai/mcp (:8111)
        │
        ├── PubMed (NCBI E-utilities)
        ├── ClinicalTrials.gov (API v2)
        └── OpenFDA (labels, events, approvals)
```

## License

MIT
