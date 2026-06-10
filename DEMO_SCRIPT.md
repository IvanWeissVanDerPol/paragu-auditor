# Paragu-Auditor Demo Script (for your friend at Databricks)

## Quick start
```bash
git clone https://github.com/IvanWeissVanDerPol/paragu-auditor.git
cd paragu-auditor
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v        # Verify 96 tests pass
streamlit run src/paragu_auditor/ui/app.py  # Launch UI
```

## 3 demo queries (no API key needed — rule-based mode)

### Q1 — Find single-bidder contracts
> "Mostrame los contratos con un solo oferente en Salud"

Agent finds 1 contract (rayos X, Salud, 780M PYG) — flagged R018. Shows evidence and recommendations.

### Q2 — Verify a specific contract
> "Verificá el contrato ocds-03ad3f-193399"

Agent runs all 5 flags on that OCID. Shows which flags triggered and why.

### Q3 — Summary by entity
> "Resumen de contrataciones en 2024 por entidad"

Agent groups by entity, shows counts + total monto. Good for "see the big picture."

## With an OpenAI key (real LLM)
```bash
export OPENAI_API_KEY=sk-...
streamlit run src/paragu_auditor/ui/app.py
```
Then ask the same questions — the LLM handles routing more naturally.

## Architecture in 30 seconds
- **Data**: Paraguay DNCP OCDS (10 synthetic contracts for demo, real data from contrataciones.gov.py)
- **Red flags**: 5 Cardinal-patterns (R003/R018/R024/R028/R058) — 96 tests with Cardinal parity
- **Storage**: DuckDB (swap to Databricks Delta for production)
- **Agent**: Spanish prompt, 5 tools, rules OR OpenAI function-calling
- **UI**: Streamlit (single file, 74 lines)
- **License**: MIT
