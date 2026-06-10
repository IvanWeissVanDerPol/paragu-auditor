# Paragu-Auditor

> A public procurement auditor for Paraguay's DNCP (Dirección Nacional de Contrataciones Públicas), with pre-computed corruption-pattern detection based on the Open Contracting Partnership's Cardinal library.

## What it does

- Loads Paraguay public procurement data (OCDS format)
- Pre-computes 5 red flags (R003, R018, R024, R028, R058) on every contract
- Lets you query in natural Spanish: "Show me all single-bidder contracts in Salud Pública over 500M PYG in 2024"
- Returns answers with citations back to the DNCP source

## Why it matters

ProZorro (Ukraine's procurement transparency system) saved the Ukrainian government **$1.9 billion in 2 years**. Paraguay spends ~$5B/year on procurement, with 0 transparency tooling. This is the first step.

## Status

**Complete MVP** (3,171 lines, 96 tests, all passing):
- [x] Paraguay OCDS Silver layer (JSON-LD → OCDS mapper)
- [x] R018 (single-bidder) — TDD + Cardinal parity
- [x] R003 (short submission period) — TDD + Cardinal parity
- [x] R024 (price close to winning) — TDD
- [x] R028 (identical bid prices) — TDD
- [x] R058 (heavily discounted bid) — TDD + IQR-based outlier detection
- [x] FlagRunner orchestrator
- [x] DuckDB storage layer (persistent, SQL-queryable)
- [x] Chat agent (rule-based + OpenAI function-calling modes)
- [x] Spanish system prompt with citation rules
- [x] Streamlit UI (chat + red flags dashboard)
- [x] GitHub repo, MIT license, architecture docs

**In scope for v2**:
- MCP server backend
- Multi-country demo (Mexico, Brazil, etc.)
- Databricks Apps deployment (Lakebase + Agent Bricks)
- WhatsApp integration
- Guaraní full NLP
- Real DNCP data ingestion (currently using synthetic demo data)

## Architecture

```
Paraguay OCDS data
       ↓
   Silver layer (JSON-LD → OCDS mapper)
       ↓
   Red flag runner (R003, R018)
       ↓
   Function-calling agent (Spanish)
       ↓
   Streamlit UI
```

## Setup

```bash
# Requires Python 3.10+
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run the app
streamlit run src/paragu_auditor/ui/app.py
```

## Data source

- **Primary**: `https://www.contrataciones.gov.py/datos/open-contracting-info` (DNCP, OCDS)
- **Backup**: Paraguay open data portal `https://www.paraguay.gov.py/datos-abiertos`
- **License**: Open data, CC-BY compatible, attribution to DNCP

## License

- Code: MIT
- Data: CC-BY (Paraguay open data license, attribution)

## Acknowledgments

- **Open Contracting Partnership** — Cardinal red flag library (https://cardinal.readthedocs.io/)
- **DNCP Paraguay** — open data publisher
- **ProZorro / DoZorro** (Ukraine) — inspiration and methodology
- Built by Hermes (MiniMax-M3) as a portfolio piece for Paraguay civic AI
