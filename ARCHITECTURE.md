# Paragu-Auditor Architecture

## Overview

Paragu-Auditor ingests Paraguay DNCP public procurement data, pre-computes corruption-pattern red flags from the Open Contracting Partnership's Cardinal library, and lets users query in natural Spanish.

```
Paraguay OCDS (JSON-LD) ──> Silver Layer ──> FlagRunner ──> Agent ──> UI
                                  │                │           │
                                  │                │           └─ Tools (5)
                                  │                │
                                  │                └─ R003 (short period)
                                  │                └─ R018 (single bid)
                                  │                └─ R024 (close price)
                                  │                └─ R028 (identical bids)
                                  │                └─ R058 (heavy discount)
                                  │
                                  └─ Pydantic models (CompiledRelease, Tender, Bid, Award)
```

## Layers

### Data layer (`src/paragu_auditor/data/`)
- `schemas.py`: Pydantic models for OCDS CompiledReleases. Maps Paraguay DNCP procurement codes to OCDS standard values (`CO` → `open`, `LPN` → `open`, `AD` → `direct`).
- `jsonld_mapper.py`: Converts Paraguay's custom JSON-LD format (flat dicts with codes like `CO`, `ADJ`, `PYG`) to OCDS-standard Pydantic models.

### Red flags (`src/paragu_auditor/red_flags/`)
Each red flag is a pure function: `CompiledRelease → FlagResult`.
- `R018`: 1 valid bid in competitive tender → flag
- `R003`: Tender period < 15 days → flag
- `R024`: Winning price too close to 2nd lowest → flag
- `R028`: Duplicate bid amounts → flag
- `R058`: Winning price far below market → flag

All flags have TDD parity tests against Cardinal's reference examples.

### Agent (`src/paragu_auditor/agent/`)
- Two modes: Rule-based (no LLM needed) and OpenAI function-calling
- 5 tools: `buscar_contratos`, `buscar_por_ruc`, `listar_red_flags`, `verificar_contrato`, `resumen_contratacion`
- Spanish system prompt with citation rules

### UI (`src/paragu_auditor/ui/`)
- Streamlit app, chat tab + red flags dashboard tab

## Data Flow

1. **Ingest**: Load DNCP JSON-LD → `CompiledRelease` via `load_silver_data()`
2. **Flag**: Run all flags on each release via `run_all_flags_on_dataset()`
3. **Query**: User asks in Spanish → agent picks tool → tool hits in-memory data → formatted answer
4. **v2**: Replace in-memory with DuckDB / Databricks Delta

## Current Limitations

- In-memory data (DuckDB / Delta planned for v2)
- 2 of 5 flags shipped for MVP (R024/R028/R058 added in this build)
- Rule-based intent detection (LLM mode available with OpenAI key)
- No MCP server, no multi-country, no WhatsApp

## Data Source

- DNCP Paraguay: `https://www.contrataciones.gov.py/datos/`
- Open Contracting Data Standard: `https://standard.open-contracting.org/latest/`
- Cardinal red flags: `https://cartinal.readthedocs.io/`
