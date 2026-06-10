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

**MVP** (focused build, ~15-20 hours):
- [x] Project scaffold
- [ ] Paraguay OCDS Silver layer (with JSON-LD mapper)
- [ ] R018 (single-bidder) red flag + tests
- [ ] R003 (short submission period) red flag + tests
- [ ] Chat agent (function-calling, Spanish system prompt)
- [ ] Streamlit UI (chat + red flags dashboard)
- [ ] Documentation

**Out of scope for MVP** (defer to v2):
- R024, R028, R058 (3 more red flags)
- MCP server backend
- Multi-country demo (Mexico, Brazil, etc.)
- Databricks Apps deployment
- Lakehouse + Lakebase
- WhatsApp integration
- Guaraní full NLP

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
