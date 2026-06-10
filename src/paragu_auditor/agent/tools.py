"""Function-calling tools for the chat agent.

These tools are designed to be called by an LLM with function-calling.
Each tool:
  - Has a clear, structured schema (function name + JSON parameters)
  - Returns a list of records (compilations of CompiledRelease + flag info)
  - Always includes OCID for citation

For the MVP, data is loaded from a synthetic dataset.
For v2, swap the data source with Databricks Delta tables.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ..data.jsonld_mapper import load_silver_data
from ..data.schemas import CompiledRelease
from ..red_flags.runner import run_all_flags, run_all_flags_on_dataset


# Load data once at module import (MVP: in-memory)
# v2: replace with Databricks Delta query
_DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "synthetic_ocds.jsonl"
_RELEASES: list[CompiledRelease] = []
_LOADED = False


def _load_data() -> list[CompiledRelease]:
    """Lazy-load the synthetic dataset."""
    global _LOADED, _RELEASES
    if not _LOADED:
        if _DATA_PATH.exists():
            _RELEASES = load_silver_data(str(_DATA_PATH))
        else:
            # No data file yet — fall back to fixture data
            from tests.data.fixtures.synthetic import DEMO_DATASET
            _RELEASES = load_silver_data(DEMO_DATASET)
        _LOADED = True
    return _RELEASES


def get_all_releases() -> list[CompiledRelease]:
    """Public accessor for the in-memory dataset."""
    return _load_data()


# ===== TOOL SCHEMAS =====
# These are the function-calling schemas the LLM sees.
# Each tool has: name, description, parameters (JSON Schema).

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "buscar_contratos",
            "description": "Busca contratos públicos de Paraguay por filtros. Devuelve hasta N resultados ordenados por fecha.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entidad": {
                        "type": "string",
                        "description": "Nombre de la entidad contratante (ej: 'Ministerio de Salud Pública')",
                    },
                    "proveedor": {
                        "type": "string",
                        "description": "Nombre del proveedor o parte del nombre",
                    },
                    "modalidad": {
                        "type": "string",
                        "description": "Modalidad de contratación: 'open' (licitación), 'selective' (restringida), 'limited' (menores), 'direct' (directa)",
                    },
                    "año": {
                        "type": "integer",
                        "description": "Año del contrato (ej: 2024)",
                    },
                    "monto_minimo": {
                        "type": "integer",
                        "description": "Monto mínimo en PYG (Guaraníes)",
                    },
                    "monto_maximo": {
                        "type": "integer",
                        "description": "Monto máximo en PYG",
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Máximo de resultados a devolver (1-50, default 10)",
                        "default": 10,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_por_ruc",
            "description": "Busca todos los contratos adjudicados a un proveedor específico por RUC (Registro Único de Contribuyente).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ruc": {
                        "type": "string",
                        "description": "RUC del proveedor (formato Paraguay: 80012345-6 o 8001234)",
                    },
                },
                "required": ["ruc"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_red_flags",
            "description": "Lista los contratos marcados por una bandera roja específica (R003, R018). Útil para encontrar patrones de riesgo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_flag": {
                        "type": "string",
                        "description": "Tipo de bandera roja: 'R003' (período corto) o 'R018' (un solo oferente)",
                    },
                    "año": {
                        "type": "integer",
                        "description": "Año (ej: 2024)",
                    },
                    "entidad": {
                        "type": "string",
                        "description": "Filtrar por entidad contratante",
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Máximo de resultados (default 20)",
                        "default": 20,
                    },
                },
                "required": ["tipo_flag"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verificar_contrato",
            "description": "Para un contrato específico, lista todas las banderas rojas que activa con explicación detallada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ocid": {
                        "type": "string",
                        "description": "OCID del contrato (formato: ocds-03ad3f-NÚMERO)",
                    },
                },
                "required": ["ocid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resumen_contratacion",
            "description": "Resumen agregado de contrataciones por período. Útil para visualizar tendencias.",
            "parameters": {
                "type": "object",
                "properties": {
                    "año": {
                        "type": "integer",
                        "description": "Año (ej: 2024)",
                    },
                    "agrupar_por": {
                        "type": "string",
                        "description": "Campo para agrupar: 'entidad', 'proveedor', 'modalidad'",
                    },
                },
                "required": ["año", "agrupar_por"],
            },
        },
    },
]


# ===== TOOL IMPLEMENTATIONS =====

def _format_money(amount: Optional[float]) -> str:
    """Format a PYG amount in Paraguayan style: 1.500.000.000 PYG."""
    if amount is None:
        return "N/D"
    # Paraguayan style: dots as thousand separators, no decimals for PYG
    return f"{int(amount):,}".replace(",", ".") + " PYG"


def _release_to_summary(r: CompiledRelease) -> dict:
    """Convert a CompiledRelease to a JSON-safe summary dict."""
    # Get amount from tender value, award value, or first award value
    amount = None
    if r.tender.value:
        amount = r.tender.value.amount
    if amount is None and r.awards:
        for a in r.awards:
            if a.value:
                amount = a.value.amount
                break
    return {
        "ocid": r.ocid,
        "titulo": r.tender.title,
        "entidad": r.tender.procuring_entity_name,
        "modalidad": r.tender.procurement_method,
        "modalidad_detalle": r.tender.procurement_method_details,
        "monto": amount,
        "monto_fmt": _format_money(amount),
        "año": r.tender.tender_period_start.year if r.tender.tender_period_start else None,
        "n_bids": r.tender.n_bids,
        "n_valid_bids": r.tender.n_valid_bids,
    }


def buscar_contratos(
    entidad: Optional[str] = None,
    proveedor: Optional[str] = None,
    modalidad: Optional[str] = None,
    año: Optional[int] = None,
    monto_minimo: Optional[int] = None,
    monto_maximo: Optional[int] = None,
    limite: int = 10,
) -> list[dict]:
    """Search contracts by filters."""
    releases = _load_data()
    results = []

    for r in releases:
        # Entity filter (case-insensitive substring)
        if entidad and (not r.tender.procuring_entity_name or
                        entidad.lower() not in r.tender.procuring_entity_name.lower()):
            continue
        # Procurement method filter
        if modalidad and r.tender.procurement_method != modalidad:
            continue
        # Year filter
        if año and (not r.tender.tender_period_start or
                    r.tender.tender_period_start.year != año):
            continue
        # Amount filters
        if monto_minimo and (not r.tender.value or r.tender.value.amount < monto_minimo):
            continue
        if monto_maximo and (not r.tender.value or r.tender.value.amount > monto_maximo):
            continue
        # Vendor filter (check supplier names in awards)
        if proveedor:
            supplier_names_lower = proveedor.lower()
            found = False
            for a in r.awards:
                for name in a.supplier_names:
                    if supplier_names_lower in name.lower():
                        found = True
                        break
                if found:
                    break
            if not found:
                continue
        results.append(_release_to_summary(r))
        if len(results) >= limite:
            break

    return results


def buscar_por_ruc(ruc: str) -> list[dict]:
    """Search contracts by vendor RUC."""
    releases = _load_data()
    results = []
    ruc_clean = ruc.replace("-", "").replace(".", "").strip()

    for r in releases:
        for a in r.awards:
            for supplier_id in a.supplier_ids:
                if ruc_clean in supplier_id.replace("-", "").replace(".", ""):
                    results.append(_release_to_summary(r))
                    break
            if results and results[-1].get("ocid") == r.ocid:
                break
    return results


def listar_red_flags(
    tipo_flag: str,
    año: Optional[int] = None,
    entidad: Optional[str] = None,
    limite: int = 20,
) -> list[dict]:
    """List contracts flagged by a specific red flag."""
    releases = _load_data()
    results = []

    for r in releases:
        # Year filter
        if año and (not r.tender.tender_period_start or
                    r.tender.tender_period_start.year != año):
            continue
        # Entity filter
        if entidad and (not r.tender.procuring_entity_name or
                        entidad.lower() not in r.tender.procuring_entity_name.lower()):
            continue
        # Run flags on this release
        flag_results = run_all_flags(r, flag_ids=[tipo_flag])
        for fr in flag_results:
            if not fr.skipped and fr.value >= 1.0:
                summary = _release_to_summary(r)
                summary["flag_evidence"] = fr.evidence
                summary["flag_skip_reason"] = fr.skip_reason
                results.append(summary)
                if len(results) >= limite:
                    return results

    return results


def verificar_contrato(ocid: str) -> dict:
    """For a specific contract, list all red flags it triggers with explanation."""
    releases = _load_data()
    target = None
    for r in releases:
        if r.ocid == ocid:
            target = r
            break
    if not target:
        return {"error": f"No se encontró contrato con OCID {ocid}"}

    flag_results = run_all_flags(target)
    flagged = [fr for fr in flag_results if not fr.skipped and fr.value >= 1.0]

    return {
        "ocid": target.ocid,
        "titulo": target.tender.title,
        "entidad": target.tender.procuring_entity_name,
        "modalidad": target.tender.procurement_method,
        "modalidad_detalle": target.tender.procurement_method_details,
        "monto": _format_money(target.tender.value.amount if target.tender.value else None),
        "n_bids": target.tender.n_bids,
        "n_valid_bids": target.tender.n_valid_bids,
        "banderas_rojas_activadas": [fr.to_dict() for fr in flagged],
        "todas_las_banderas_evaluadas": [fr.to_dict() for fr in flag_results],
    }


def resumen_contratacion(año: int, agrupar_por: str) -> dict:
    """Aggregated summary by entity, vendor, or modality."""
    releases = _load_data()
    grouped: dict = {}

    for r in releases:
        if not r.tender.tender_period_start or r.tender.tender_period_start.year != año:
            continue
        # Determine group key
        if agrupar_por == "entidad":
            key = r.tender.procuring_entity_name or "Sin entidad"
        elif agrupar_por == "proveedor":
            if not r.awards or not r.awards[0].supplier_names:
                key = "Sin proveedor"
            else:
                key = r.awards[0].supplier_names[0]
        elif agrupar_por == "modalidad":
            key = r.tender.procurement_method_details or r.tender.procurement_method
        else:
            return {"error": f"agrupar_por inválido: {agrupar_por}"}

        if key not in grouped:
            grouped[key] = {"count": 0, "monto_total": 0, "ocids": []}
        grouped[key]["count"] += 1
        if r.tender.value:
            grouped[key]["monto_total"] += r.tender.value.amount
        grouped[key]["ocids"].append(r.ocid)

    # Format for output
    output = {
        "año": año,
        "agrupar_por": agrupar_por,
        "total_grupos": len(grouped),
        "total_contratos": sum(g["count"] for g in grouped.values()),
        "monto_total": _format_money(sum(g["monto_total"] for g in grouped.values())),
        "grupos": [
            {
                "nombre": k,
                "count": v["count"],
                "monto_total": _format_money(v["monto_total"]),
                "ocids": v["ocids"][:5],  # Sample only
            }
            for k, v in sorted(grouped.items(), key=lambda x: -x[1]["monto_total"])
        ],
    }
    return output


# ===== TOOL DISPATCH =====
TOOL_FUNCTIONS = {
    "buscar_contratos": buscar_contratos,
    "buscar_por_ruc": buscar_por_ruc,
    "listar_red_flags": listar_red_flags,
    "verificar_contrato": verificar_contrato,
    "resumen_contratacion": resumen_contratacion,
}


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Dispatch a tool call to the appropriate function.

    Args:
        name: Tool name (must be in TOOL_FUNCTIONS).
        arguments: Tool arguments as a dict.

    Returns:
        The tool's return value (will be JSON-serialized for the LLM).
    """
    if name not in TOOL_FUNCTIONS:
        return {"error": f"Herramienta desconocida: {name}"}
    fn = TOOL_FUNCTIONS[name]
    try:
        return fn(**arguments)
    except Exception as e:
        return {"error": f"Error en herramienta {name}: {type(e).__name__}: {e}"}
