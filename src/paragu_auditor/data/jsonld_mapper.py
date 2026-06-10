"""JSON-LD → OCDS mapper for Paraguay DNCP data.

Paraguay DNCP publishes in two formats:
  1. Custom JSON-LD (with codes like "CO", "ADJ", currency "PYG")
  2. OCDS 1.1 (already standard, no mapping needed)

This module handles format #1. It takes a raw DNCP JSON-LD record and produces
a CompiledRelease (the canonical Silver-layer entity).

Example input (simplified):
  {
    "id_llamado": 193399,
    "anio": 2024,
    "convocante": "Dirección Nacional de Contrataciones Públicas",
    "tipo_procedimiento": "CO",
    "moneda": "PYG",
    "estado": "ADJ",
    "categoria": "40",
    "fecha_publicacion": "2024-03-15",
    "fecha_apertura": "2024-03-30"
  }

Example output:
  CompiledRelease(
    ocid="ocds-03ad3f-193399",
    tender=Tender(
      id="193399",
      ocid="ocds-03ad3f-193399",
      title="...",
      procurement_method="open",  # mapped from "CO"
      procurement_method_details="Concurso de Ofertas",
      ...
    ),
    ...
  )
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from .schemas import (
    PARAGUAY_METHOD_MAP,
    CompiledRelease,
    Money,
    Award,
    Bid,
    Contract,
    Tender,
)


# Paraguay DNCP category codes (UNSPSC segments)
# Source: Paraguay DNCP API
CATEGORY_MAP: dict[str, str] = {
    "10": "Defence and law enforcement",
    "11": "Mining and oil and gas",
    "12": "Industrial cleaning",
    "14": "Industrial manufacturing",
    "15": "Fuels and lubricants",
    "20": "Farming and fishing",
    "22": "Building and construction",
    "23": "Industrial infrastructure",
    "24": "Material handling",
    "25": "Commercial and military vehicles",
    "26": "Power generation",
    "27": "Lighting",
    "30": "Structural materials",
    "31": "Manufacturing components",
    "32": "Electronic equipment",
    "39": "Laboratory equipment",
    "40": "Computers and office equipment",
    "41": "Measuring instruments",
    "42": "Medical equipment",
    "43": "Communications equipment",
    "44": "Office equipment",
    "45": "Printing and publishing",
    "46": "Defence systems",
    "47": "Cleaning equipment",
    "48": "Service industry equipment",
    "49": "Sports and recreation",
    "50": "Food and beverage",
    "51": "Drugs and pharmaceuticals",
    "52": "Domestic appliances",
    "53": "Personal care products",
    "54": "Timepieces and jewellery",
    "55": "Printing and stationery",
    "56": "Furniture",
    "60": "Financial services",
    "61": "Insurance services",
    "62": "Banking and investment",
    "63": "Real estate",
    "64": "Telecommunications",
    "65": "Transportation",
    "70": "Healthcare services",
    "71": "Education and training",
    "72": "Hospitality and tourism",
    "73": "Maintenance and repair",
    "74": "Cleaning and janitorial",
    "75": "Agricultural services",
    "76": "Mining services",
    "77": "Oil and gas services",
    "78": "Construction services",
    "79": "Transportation services",
    "80": "Management and business services",
    "81": "Engineering and research",
    "82": "Editorial and design",
    "83": "Public sector services",
    "84": "Financial and insurance",
    "85": "Healthcare and social services",
    "86": "Education and training services",
    "90": "Travel and accommodation",
    "91": "Personal services",
    "92": "National defence",
    "93": "Public order",
    "94": "Utilities",
    "95": "Agriculture and environment",
}


def make_ocid(licitacion_id: int | str) -> str:
    """Build OCDS-compliant OCID from a Paraguay DNCP tender ID.

    Paraguay DNCP uses the prefix `ocds-03ad3f` (per their published docs).
    Format: ocds-03ad3f-{number}
    """
    return f"ocds-03ad3f-{licitacion_id}"


def parse_date(value: Any) -> Optional[date]:
    """Parse a date from various Paraguay DNCP formats.

    Paraguay uses:
    - ISO 8601: "2024-03-15"
    - Spanish: "15 de marzo de 2024"
    - Datetime: "2024-03-15T00:00:00"
    - Null
    """
    if not value or value == "-" or value == "":
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        # Try ISO format first
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            pass
        # Try DD/MM/YYYY (LATAM default)
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def parse_money(value: Any) -> Optional[Money]:
    """Parse a monetary amount from various Paraguay DNCP formats.

    DNCP data appears as:
    - Float: 850000.0
    - Int: 850000
    - String with separators: "850.000" or "850,000" or "850.000,00" or "1.500.000.000"
    - String with currency: "1.500.000.000 PYG" or "Gs. 1.500.000.000"
    - Null
    """
    if value is None or value == "" or value == "-":
        return None
    if isinstance(value, (int, float)):
        return Money(amount=float(value), currency="PYG")
    if isinstance(value, str):
        # Strip non-numeric chars except , and . and digits
        cleaned = value.replace(" ", "").upper()
        for token in ["PYG", "GS.", "GUARANÍES", "GUARANIES", "G$"]:
            cleaned = cleaned.replace(token, "")
        cleaned = cleaned.strip()

        # Now detect separator style.
        has_dot = "." in cleaned
        has_comma = "," in cleaned

        if has_dot and has_comma:
            # Both present. The LAST one is the decimal separator.
            if cleaned.rfind(",") > cleaned.rfind("."):
                # Comma is decimal: "1.500.000,00" or "1,500,000.00"
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                # Dot is decimal: "1,500,000.00"
                cleaned = cleaned.replace(",", "")
        elif has_comma and not has_dot:
            # Only comma. Could be thousands (1,500,000) or decimal (850,00).
            # Heuristic: count separators. If multiple commas at 3-digit intervals → thousands.
            comma_positions = [i for i, c in enumerate(cleaned) if c == ","]
            if len(comma_positions) == 1 and len(cleaned) - comma_positions[0] - 1 <= 2:
                # Single comma with 1-2 digits after → decimal (e.g., "850,00" or "850,5")
                cleaned = cleaned.replace(",", ".")
            else:
                # Multiple commas or comma with 3+ digits → thousands
                cleaned = cleaned.replace(",", "")
        elif has_dot and not has_comma:
            # Only dot. Could be thousands (1.500.000) or decimal (850.00).
            dot_positions = [i for i, c in enumerate(cleaned) if c == "."]
            if len(dot_positions) == 1 and len(cleaned) - dot_positions[0] - 1 <= 2:
                # Single dot with 1-2 digits after → decimal (e.g., "850.00")
                pass  # already in correct format
            else:
                # Multiple dots or dot with 3 digits → thousands
                cleaned = cleaned.replace(".", "")

        try:
            return Money(amount=float(cleaned), currency="PYG")
        except ValueError:
            return None
    return None


def map_paraguay_code(code: str) -> str:
    """Map a Paraguay DNCP code to its OCDS-standard value.

    Examples:
    - "CO" → "open"
    - "ADJ" → "active" (for award status)
    - "LPN" → "open"
    """
    if not code:
        return ""
    code_upper = code.upper().strip()
    return PARAGUAY_METHOD_MAP.get(code_upper, code_upper)


def map_category(code: str) -> str:
    """Map a UNSPSC segment code to a human-readable category."""
    if not code:
        return ""
    # Try as int (handles "40", "040", "0040") then format as 2-digit string
    try:
        code_int = int(code)
        key = f"{code_int:02d}"
    except (ValueError, TypeError):
        key = str(code).zfill(2)
    return CATEGORY_MAP.get(key, f"Category {code}")


def jsonld_to_ocds(record: dict[str, Any]) -> CompiledRelease:
    """Convert a Paraguay DNCP JSON-LD record to a CompiledRelease.

    The Paraguay DNCP record format is a flat dictionary with these fields:
    - id_llamado (int): tender ID
    - anio (int): year
    - convocante (str): procuring entity name
    - tipo_procedimiento (str): e.g., "CO", "LPN", "AD"
    - moneda (str): currency (always "PYG")
    - estado (str): e.g., "ADJ", "PEN", "CAN"
    - categoria (str): UNSPSC segment code
    - fecha_publicacion (str): publication date
    - fecha_apertura (str): opening date
    - monto_adjudicado (number): awarded amount
    - proveedor_adjudicado (str): winning supplier name
    - items (list): list of items with quantities and unit prices

    The output is a CompiledRelease that conforms to the OCDS schema
    (defined in src/paragu_auditor/data/schemas.py).
    """
    # Extract core identifiers
    licitacion_id = record.get("id_llamado") or record.get("id") or record.get("tender_id")
    if licitacion_id is None:
        raise ValueError(f"Record missing id_llamado/id/tender_id: {record.keys()}")
    ocid = make_ocid(licitacion_id)

    # Map the procurement method
    method_code = record.get("tipo_procedimiento", "")
    method_details = record.get("tipo_procedimiento_detalle") or method_code
    procurement_method = map_paraguay_code(method_code)

    # Map category
    category_code = record.get("categoria", "")
    category_name = map_category(category_code)

    # Dates
    pub_date = parse_date(record.get("fecha_publicacion"))
    open_date = parse_date(record.get("fecha_apertura"))
    close_date = parse_date(record.get("fecha_cierre") or record.get("fecha_apertura"))
    award_date = parse_date(record.get("fecha_adjudicacion"))

    # Money
    tender_value = parse_money(record.get("monto_referencial") or record.get("valor_referencial"))
    award_value = parse_money(record.get("monto_adjudicado") or record.get("valor_adjudicado"))

    # Build the tender
    tender = Tender(
        id=str(licitacion_id),
        ocid=ocid,
        title=record.get("titulo", record.get("objeto", "")),
        description=record.get("descripcion", ""),
        procurement_method=procurement_method,
        procurement_method_details=method_details,
        procurement_category=category_name,
        main_procurement_category=category_name,
        tender_period_start=pub_date,
        tender_period_end=close_date,
        tender_status=record.get("estado", ""),
        value=tender_value,
        procuring_entity_id=record.get("convocante_id"),
        procuring_entity_name=record.get("convocante", ""),
        items=record.get("items", []),
    )

    # Build bids from records if available
    bids = []
    for bid_record in record.get("bids", []):
        bids.append(
            Bid(
                id=str(bid_record.get("id", f"{ocid}-bid-{len(bids)}")),
                bidder_id=str(bid_record.get("proveedor_id", "")),
                bidder_name=bid_record.get("proveedor_nombre", ""),
                amount=parse_money(bid_record.get("monto_ofertado")),
                status=bid_record.get("estado", "valid"),
                date=parse_date(bid_record.get("fecha_oferta")),
            )
        )
    tender.bids = bids
    tender.n_bids = len(bids)
    tender.n_valid_bids = sum(1 for b in bids if b.status == "valid")

    # Build award
    award = None
    if record.get("estado") in ("ADJ", "active") or award_value is not None:
        supplier_id = record.get("proveedor_adjudicado_id", "")
        supplier_name = record.get("proveedor_adjudicado", "")
        award = Award(
            id=f"{ocid}-award",
            ocid=ocid,
            title=record.get("titulo", ""),
            status="active",
            date=award_date,
            value=award_value,
            supplier_ids=[supplier_id] if supplier_id else [],
            supplier_names=[supplier_name] if supplier_name else [],
        )

    # Build contract
    contract = None
    if award and award.status == "active":
        contract = Contract(
            id=f"{ocid}-contract",
            ocid=ocid,
            award_id=award.id,
            title=record.get("titulo", ""),
            status="active",
            date_signed=award_date,
            value=award_value,
            supplier_ids=award.supplier_ids,
        )

    return CompiledRelease(
        ocid=ocid,
        tender=tender,
        awards=[award] if award else [],
        contracts=[contract] if contract else [],
    )


def load_silver_data(source: list[dict[str, Any]] | str) -> list[CompiledRelease]:
    """Load a list of DNCP records (or path to JSONL) into CompiledRelease objects.

    Args:
        source: Either a list of dicts (already loaded) or a path to a JSONL file
                where each line is a JSON record from DNCP.

    Returns:
        List of CompiledRelease objects, one per record.

    Skips records that fail to parse (logs warning).
    """
    import json
    import logging
    from pathlib import Path

    logger = logging.getLogger(__name__)

    if isinstance(source, str):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"DNCP data file not found: {source}")
        with path.open() as f:
            records = [json.loads(line) for line in f if line.strip()]
    else:
        records = source

    releases = []
    for i, record in enumerate(records):
        try:
            release = jsonld_to_ocds(record)
            releases.append(release)
        except Exception as e:
            logger.warning(f"Skipped record {i} (id={record.get('id_llamado', '?')}): {e}")

    return releases
