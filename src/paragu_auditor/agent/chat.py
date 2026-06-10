"""Simple chat loop for the Paraguay public procurement auditor.

This module provides:
  1. A function-calling agent loop (for production with an OpenAI-compatible API)
  2. A "no-LLM" mode that simulates the agent (for testing and local dev)

For the MVP, we support both:
  - With OPENAI_API_KEY set → uses real LLM (GPT-4o-mini or similar)
  - Without key → uses simple rule-based routing (good enough for demos)

The no-LLM mode is a great learning tool: you can see exactly which tool
gets called for which question, without burning API credits.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

from .prompts import SPANISH_SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, TOOL_FUNCTIONS, call_tool, get_all_releases

logger = logging.getLogger(__name__)


# ============================================================
# NO-LLM MODE: Simple rule-based routing for testing/demos
# ============================================================

# Heuristic patterns → tool name
_INTENT_PATTERNS: list[tuple[str, str]] = [
    # verificar_contrato — must come BEFORE RUC pattern
    (r"(verifica|verificá|anali[zs]a|cheq|revisar)\s+(el\s+)?contrato\s+.*ocds", "verificar_contrato"),
    (r"(que|qué)\s+banderas?\s+(tiene|activa)\s+(el\s+)?contrato", "verificar_contrato"),
    # listar_red_flags
    (r"(banderas?\s+rojas?|red\s+flags?|r018|r003)\s+(de|en)", "listar_red_flags"),
    (r"contratos?\s+con\s+(un\s+solo\s+oferente|período\s+corto)", "listar_red_flags"),
    (r"single[\s-]?bid", "listar_red_flags"),
    # buscar_por_ruc — only if "ruc" is explicitly mentioned
    (r"ruc\s*\d{6,8}", "buscar_por_ruc"),
    (r"por\s+ruc\s", "buscar_por_ruc"),
    # resumen_contratacion
    (r"resumen\s+(de\s+)?(contrataciones?|compras?|gastos?)", "resumen_contratacion"),
    (r"total\s+(de\s+)?(contrataciones?|compras?)\s+en", "resumen_contratacion"),
    (r"(agrupado|agrupar|por\s+entidad|por\s+proveedor|por\s+modalidad)", "resumen_contratacion"),
    # Default: buscar_contratos
    (r".*", "buscar_contratos"),
]


def detect_intent_simple(question: str) -> str:
    """Very simple rule-based intent detection. Returns tool name.

    This is a DEMO MODE only. With a real LLM, this function is not used.
    """
    q = question.lower()
    for pattern, tool_name in _INTENT_PATTERNS:
        if re.search(pattern, q):
            return tool_name
    return "buscar_contratos"


def extract_filters_simple(question: str) -> dict:
    """Extract basic filters from a Spanish question. Demo mode only."""
    q = question.lower()
    filters: dict[str, Any] = {}

    # Entity detection
    entities = {
        "salud": "Ministerio de Salud",
        "msp": "Ministerio de Salud",
        "educación": "Ministerio de Educación",
        "mec": "Ministerio de Educación",
        "obras": "Ministerio de Obras",
        "mop": "Ministerio de Obras",
        "hacienda": "Ministerio de Hacienda",
    }
    for key, entity in entities.items():
        if key in q:
            filters["entidad"] = entity
            break

    # Year detection (4-digit number 2015-2030)
    year_match = re.search(r"\b(20[1-3]\d)\b", q)
    if year_match:
        filters["año"] = int(year_match.group(1))

    # Amount detection (number with "millones", "M", "millard")
    million_match = re.search(r"(\d+)\s*millones?", q)
    billion_match = re.search(r"(\d+)\s*mil(lard| millones)?", q)
    if billion_match:
        filters["monto_minimo"] = int(billion_match.group(1)) * 1_000_000_000
    elif million_match:
        filters["monto_minimo"] = int(million_match.group(1)) * 1_000_000

    # Modality detection
    if "licitacion" in q or "licitación" in q:
        filters["modalidad"] = "open"
    elif "concurso" in q:
        filters["modalidad"] = "open"
    elif "directa" in q or "direct" in q:
        filters["modalidad"] = "direct"
    elif "menor" in q or "limitada" in q:
        filters["modalidad"] = "limited"

    # Flag type
    if "r018" in q or "un solo oferente" in q or "single bid" in q:
        filters["tipo_flag"] = "R018"
    elif "r003" in q or "período corto" in q or "submission period" in q:
        filters["tipo_flag"] = "R003"

    # OCID (verificar_contrato)
    ocid_match = re.search(r"ocds-03ad3f-(\d+)", q)
    if ocid_match:
        filters["ocid"] = ocid_match.group(0)

    # RUC
    ruc_match = re.search(r"\b(\d{6,8})[-.]?(\d)?\b", q)
    if ruc_match and "ruc" in q:
        filters["ruc"] = ruc_match.group(0)

    # agrupar_por
    if "por entidad" in q or "por ministerio" in q:
        filters["agrupar_por"] = "entidad"
    elif "por proveedor" in q or "por empresa" in q:
        filters["agrupar_por"] = "proveedor"
    elif "por modalidad" in q or "por tipo" in q:
        filters["agrupar_por"] = "modalidad"

    return filters


def format_tool_result_spanish(tool_name: str, tool_result: Any, question: str) -> str:
    """Format a tool result as a Spanish-language answer. Demo mode only.

    With a real LLM, the LLM does this formatting. In demo mode, we do it
    with simple templates.
    """
    if isinstance(tool_result, dict) and "error" in tool_result:
        return f"❌ Error: {tool_result['error']}"

    if tool_name == "verificar_contrato":
        if "error" in tool_result:
            return f"❌ {tool_result['error']}"
        flags = tool_result.get("banderas_rojas_activadas", [])
        if not flags:
            return (f"📋 El contrato {tool_result['ocid']} ({tool_result['titulo']}) "
                    f"de {tool_result['entidad']}, por {tool_result['monto']}, "
                    f"**no tiene banderas rojas activadas**. "
                    f"Evaluamos R003 (período corto) y R018 (un solo oferente) y pasó ambos.")
        flag_descriptions = []
        for fr in flags:
            fid = fr["flag_id"]
            if fid == "R018":
                flag_descriptions.append(
                    f"  - **R018 (un solo oferente)**: {fr['evidence'].get('n_valid_bids', '?')} oferta(s) válida(s) en licitación {fr['evidence'].get('procurement_method', '?')}"
                )
            elif fid == "R003":
                flag_descriptions.append(
                    f"  - **R003 (período corto)**: {fr['evidence'].get('period_days', '?')} días (umbral: {fr['evidence'].get('threshold_days', '?')})"
                )
        return (f"📋 Contrato {tool_result['ocid']} ({tool_result['titulo']})\n\n"
                f"Entidad: {tool_result['entidad']}\n"
                f"Modalidad: {tool_result['modalidad_detalle']} ({tool_result['modalidad']})\n"
                f"Monto: {tool_result['monto']}\n"
                f"Bids: {tool_result['n_valid_bids']} válida(s) de {tool_result['n_bids']} total\n\n"
                f"⚠️ **Banderas rojas activadas**:\n" + "\n".join(flag_descriptions) + "\n\n"
                f"**Recomendación**: verificar con el equipo de adquisiciones y la DNCP.\n\n"
                f"Fuente: ocid={tool_result['ocid']}")

    if tool_name == "listar_red_flags":
        if not tool_result:
            return "📋 No encontré contratos con esa bandera roja en el dataset actual."
        lines = [f"📋 Encontré {len(tool_result)} contrato(s) con la bandera roja:\n"]
        for c in tool_result:
            lines.append(
                f"- **{c['ocid']}** — {c.get('titulo', '(sin título)')} — "
                f"{c.get('entidad', 'N/D')} — {c.get('monto_fmt', 'N/D')} "
                f"({c.get('n_valid_bids', '?')} oferta(s))"
            )
        return "\n".join(lines) + f"\n\nFuentes: {[c['ocid'] for c in tool_result]}"

    if tool_name == "buscar_por_ruc":
        if not tool_result:
            return f"📋 No encontré contratos para el RUC solicitado."
        lines = [f"📋 Encontré {len(tool_result)} contrato(s) para ese proveedor:\n"]
        for c in tool_result:
            lines.append(
                f"- **{c['ocid']}** — {c.get('titulo', '(sin título)')} — "
                f"{c.get('entidad', 'N/D')} — {c.get('monto_fmt', 'N/D')}"
            )
        return "\n".join(lines) + f"\n\nFuentes: {[c['ocid'] for c in tool_result]}"

    if tool_name == "resumen_contratacion":
        if "error" in tool_result:
            return f"❌ {tool_result['error']}"
        lines = [
            f"📊 Resumen de contrataciones en {tool_result['año']} agrupado por {tool_result['agrupar_por']}\n",
            f"Total grupos: {tool_result['total_grupos']}",
            f"Total contratos: {tool_result['total_contratos']}",
            f"Monto total: {tool_result['monto_total']}\n",
            "Top grupos por monto:",
        ]
        for g in tool_result.get("grupos", [])[:10]:
            lines.append(f"  - {g['nombre']}: {g['count']} contratos, {g['monto_total']}")
        return "\n".join(lines)

    if tool_name == "buscar_contratos":
        if not tool_result:
            return "📋 No encontré contratos con esos filtros."
        lines = [f"📋 Encontré {len(tool_result)} contrato(s):\n"]
        for c in tool_result:
            lines.append(
                f"- **{c['ocid']}** — {c.get('titulo', '(sin título)')} — "
                f"{c.get('entidad', 'N/D')} — {c.get('monto_fmt', 'N/D')} "
                f"({c.get('año', 'N/D')})"
            )
        return "\n".join(lines) + f"\n\nFuentes: {[c['ocid'] for c in tool_result]}"

    return f"Resultado: {json.dumps(tool_result, ensure_ascii=False, default=str)[:500]}"


def chat_simple(question: str) -> str:
    """No-LLM chat. Uses rule-based intent detection.

    This is a DEMO MODE for testing without an OpenAI key.
    With a real API key, use `chat_with_llm` instead.
    """
    # 1. Detect intent
    tool_name = detect_intent_simple(question)
    # 2. Extract filters
    filters = extract_filters_simple(question)
    # 3. Remove filters that don't apply to this tool
    valid_params = {
        "buscar_contratos": {"entidad", "proveedor", "modalidad", "año", "monto_minimo", "monto_maximo", "limite"},
        "buscar_por_ruc": {"ruc"},
        "listar_red_flags": {"tipo_flag", "año", "entidad", "limite"},
        "verificar_contrato": {"ocid"},
        "resumen_contratacion": {"año", "agrupar_por"},
    }
    filtered_args = {k: v for k, v in filters.items() if k in valid_params[tool_name]}
    if tool_name in ("buscar_contratos", "listar_red_flags") and "limite" not in filtered_args:
        filtered_args["limite"] = 10

    # 4. Call the tool
    tool_result = call_tool(tool_name, filtered_args)
    # 5. Format as Spanish answer
    return format_tool_result_spanish(tool_name, tool_result, question)


# ============================================================
# LLM MODE: Function-calling with OpenAI
# ============================================================


def chat_with_llm(
    question: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    max_iterations: int = 4,
) -> str:
    """Chat using OpenAI function-calling.

    Requires OPENAI_API_KEY env var (or pass api_key explicitly).
    Falls back to chat_simple() if no key is set.
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return chat_simple(question)

    try:
        from openai import OpenAI
    except ImportError:
        return "❌ OpenAI library not installed. Run: pip install openai"

    client = OpenAI(api_key=api_key)

    # 1. Initial call
    messages = [
        {"role": "system", "content": SPANISH_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    for i in range(max_iterations):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content or ""

        # 2. Execute each tool call
        messages.append(msg)
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            try:
                fn_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}
            tool_result = call_tool(fn_name, fn_args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result, ensure_ascii=False, default=str),
            })

    # If we exhausted iterations, return what we have
    return "⚠️ La respuesta requirió demasiados pasos. Intenta una pregunta más específica."


def chat(
    question: str,
    api_key: Optional[str] = None,
    use_llm: bool = True,
) -> str:
    """Main chat entry point. Use LLM if available and key set, else demo mode."""
    if use_llm and (api_key or os.environ.get("OPENAI_API_KEY")):
        return chat_with_llm(question, api_key=api_key)
    return chat_simple(question)
