"""Paraguay OCDS Silver layer.

Maps Paraguay DNCP's custom JSON-LD format to the Open Contracting Data Standard (OCDS)
schema, validates the data, and exposes it as Pydantic models for downstream use.

Paraguay DNCP publishes in two formats:
  1. Custom JSON-LD (with /datos/contexts/planificacion.json context)
  2. OCDS 1.1 (with ocds-03ad3f- prefix)

This module handles both. The Silver layer is the conformed, validated, typed view.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


# Paraguay DNCP procurement method codes → OCDS standard values
# Source: Cardinal example queries + Paraguay DNCP API
PARAGUAY_METHOD_MAP: dict[str, str] = {
    # Competitive / open
    "CO": "open",  # Concurso de Ofertas
    "LPN": "open",  # Licitación Pública Nacional
    "LPI": "open",  # Licitación Pública Internacional
    "CD": "open",  # Concurso de Precios / Comparación de Precios
    "SASI": "open",  # Subasta Agil / Subasta Inversa
    # Selective
    "LR": "selective",  # Licitación Restringida
    "SO": "selective",  # Sorteo de Obras
    # Limited
    "CM": "limited",  # Compras Menores
    "CDU": "limited",  # Compras por Debajo del Umbral
    # Direct
    "AD": "direct",  # Adjudicación Directa
    "AM": "direct",  # Adjudicación por Menor
    "EX": "direct",  # Procesos de Excepción
}

# Reverse map (for display)
OCDS_METHOD_TO_PARAGUAY: dict[str, str] = {
    "open": "Concurso de Ofertas / Licitación Pública",
    "selective": "Licitación Restringida",
    "limited": "Compras Menores / Bajo Umbral",
    "direct": "Adjudicación Directa / Excepción",
    "none": "Sin procedimiento",
}


class Money(BaseModel):
    """A monetary amount with currency."""
    amount: float
    currency: str = "PYG"

    @property
    def amount_pyg(self) -> float:
        """Always returns amount in PYG (Paraguay's currency)."""
        return self.amount  # PYG is the only currency in DNCP data


class Organization(BaseModel):
    """A procuring entity or supplier."""
    id: str
    name: str
    ruc: Optional[str] = None  # Paraguay tax ID
    department: Optional[str] = None  # Paraguay's 17 departments
    role: Optional[str] = None  # "procuringEntity" | "supplier" | "tenderer"


class Bid(BaseModel):
    """A single bid on a tender."""
    id: str
    bidder_id: str
    bidder_name: Optional[str] = None
    amount: Optional[Money] = None
    currency: str = "PYG"
    status: str = "valid"  # valid | invalid | disqualified
    date: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"valid", "invalid", "disqualified", "pending"}
        if v not in allowed:
            # Paraguay DNCP uses "ADJ" for awarded, "DES" for deserted, etc.
            # Map to OCDS-standard values
            mapping = {
                "ADJ": "valid",  # Adjudicado (won)
                "DES": "disqualified",  # Desierto (deserted)
                "NUL": "disqualified",  # Anulado
                "VAL": "valid",
                "INV": "invalid",  # Invalidado
            }
            return mapping.get(v, "valid")  # Default to valid if unknown
        return v


class Tender(BaseModel):
    """The procurement tender (the call for bids)."""
    id: str
    ocid: str  # Open Contracting ID, format: ocds-03ad3f-{number}
    title: str = ""
    description: str = ""
    procurement_method: str  # OCDS standard: open | selective | limited | direct
    procurement_method_details: str = ""  # Original Paraguay string
    procurement_category: Optional[str] = None  # works | goods | services
    main_procurement_category: Optional[str] = None
    tender_period_start: Optional[date] = None
    tender_period_end: Optional[date] = None
    submission_period_days: Optional[int] = None
    tender_status: Optional[str] = None
    value: Optional[Money] = None
    procuring_entity_id: Optional[str] = None
    procuring_entity_name: Optional[str] = None
    items: list[dict[str, Any]] = Field(default_factory=list)
    bids: list[Bid] = Field(default_factory=list)
    n_bids: int = 0
    n_valid_bids: int = 0

    @field_validator("procurement_method")
    @classmethod
    def validate_procurement_method(cls, v: str) -> str:
        """Accept both OCDS standard values and Paraguay DNCP codes."""
        allowed = {"open", "selective", "limited", "direct", "none"}
        if v in allowed:
            return v
        # Try to map from Paraguay code
        mapped = PARAGUAY_METHOD_MAP.get(v.upper())
        if mapped:
            return mapped
        # If we can't map it, raise with helpful message
        raise ValueError(
            f"Unknown procurement method: '{v}'. "
            f"Expected one of {allowed} or a Paraguay code: {list(PARAGUAY_METHOD_MAP.keys())}"
        )

    def calculate_submission_period(self) -> Optional[int]:
        """Calculate submission period in days. Returns None if dates missing."""
        if self.tender_period_start and self.tender_period_end:
            delta = self.tender_period_end - self.tender_period_start
            return delta.days
        return None


class Award(BaseModel):
    """An award (the winning contract)."""
    id: str
    ocid: str
    title: str = ""
    status: str = "active"  # active | pending | cancelled | unsuccessful
    date: Optional[date | datetime] = None
    value: Optional[Money] = None
    supplier_ids: list[str] = Field(default_factory=list)
    supplier_names: list[str] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"active", "pending", "cancelled", "unsuccessful"}
        if v in allowed:
            return v
        # Map Paraguay codes
        mapping = {
            "ADJ": "active",  # Adjudicado
            "PEN": "pending",  # Pendiente
            "CAN": "cancelled",  # Cancelado
            "DES": "unsuccessful",  # Desierto
        }
        return mapping.get(v, "active")


class Contract(BaseModel):
    """A contract (the executed agreement)."""
    id: str
    ocid: str
    award_id: str
    title: str = ""
    status: str = "active"
    date_signed: Optional[date] = None
    value: Optional[Money] = None
    supplier_ids: list[str] = Field(default_factory=list)


class CompiledRelease(BaseModel):
    """An OCDS compiled release — one per OCID.

    This is the canonical Silver-layer entity. All red flags operate on this.
    """
    ocid: str
    tender: Tender
    awards: list[Award] = Field(default_factory=list)
    contracts: list[Contract] = Field(default_factory=list)

    def winning_bid_amount(self) -> Optional[float]:
        """The amount of the winning bid, if available."""
        valid_bids = [b for b in self.tender.bids if b.status == "valid" and b.amount]
        if not valid_bids:
            return None
        return min(b.amount.amount for b in valid_bids)

    def second_lowest_bid_amount(self) -> Optional[float]:
        """The amount of the second-lowest valid bid, if available."""
        valid_bids = sorted(
            [b for b in self.tender.bids if b.status == "valid" and b.amount],
            key=lambda b: b.amount.amount,
        )
        if len(valid_bids) < 2:
            return None
        return valid_bids[1].amount.amount
