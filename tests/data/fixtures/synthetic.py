"""Synthetic Paraguay DNCP test fixtures.

These are NOT real DNCP data — they are synthetic records crafted to test
the JSON-LD mapper. The format mirrors what DNCP publishes at
https://www.contrataciones.gov.py/datos/.
"""
from __future__ import annotations

from typing import Any


def make_basic_record() -> dict[str, Any]:
    """A simple, well-formed Paraguay DNCP record."""
    return {
        "id_llamado": 193399,
        "anio": 2024,
        "convocante": "Dirección Nacional de Contrataciones Públicas",
        "tipo_procedimiento": "CO",  # Concurso de Ofertas
        "moneda": "PYG",
        "estado": "ADJ",  # Adjudicado
        "categoria": "40",  # Computers and office equipment
        "titulo": "Adquisición de equipos informáticos para el Ministerio de Salud",
        "descripcion": "Compra de 200 laptops para distribución nacional",
        "fecha_publicacion": "2024-03-15",
        "fecha_apertura": "2024-03-30",
        "monto_adjudicado": 1500000000,  # 1.5 billion PYG
        "proveedor_adjudicado": "CompuTech S.A.",
        "proveedor_adjudicado_id": "80012345-6",
        "items": [
            {
                "descripcion": "Laptop 15 pulgadas",
                "cantidad": 200,
                "unidad": "unidad",
                "precio_unitario": 7500000,
            }
        ],
        "bids": [
            {
                "id": "bid-1",
                "proveedor_id": "80012345-6",
                "proveedor_nombre": "CompuTech S.A.",
                "monto_ofertado": 1500000000,
                "estado": "valid",
                "fecha_oferta": "2024-03-29",
            },
            {
                "id": "bid-2",
                "proveedor_id": "80098765-4",
                "proveedor_nombre": "TechSolutions Paraguay",
                "monto_ofertado": 1650000000,
                "estado": "valid",
                "fecha_oferta": "2024-03-28",
            }
        ],
    }


def make_record_licitacion_publica() -> dict[str, Any]:
    """A LPN (Licitación Pública Nacional) record."""
    record = make_basic_record()
    record["id_llamado"] = 193400
    record["tipo_procedimiento"] = "LPN"
    record["monto_adjudicado"] = 5500000000  # 5.5 billion PYG
    record["titulo"] = "Construcción de hospital regional en Alto Paraná"
    return record


def make_record_adjudicacion_directa() -> dict[str, Any]:
    """A direct award (no competition)."""
    record = make_basic_record()
    record["id_llamado"] = 193401
    record["tipo_procedimiento"] = "AD"
    record["monto_adjudicado"] = 75000000
    record["titulo"] = "Servicio de limpieza mensual"
    return record


def make_record_no_bids() -> dict[str, Any]:
    """A record where no bids were submitted (deserted)."""
    record = make_basic_record()
    record["id_llamado"] = 193402
    record["estado"] = "DES"  # Desierto
    record["bids"] = []
    record["monto_adjudicado"] = None
    record["proveedor_adjudicado"] = None
    return record


def make_record_malformed_dates() -> dict[str, Any]:
    """A record with malformed date fields."""
    record = make_basic_record()
    record["id_llamado"] = 193403
    record["fecha_publicacion"] = "not a date"
    record["fecha_apertura"] = ""
    return record


def make_record_spanish_dates() -> dict[str, Any]:
    """A record with Spanish-language date formats (real Paraguay DNCP data)."""
    record = make_basic_record()
    record["id_llamado"] = 193404
    record["fecha_publicacion"] = "15/03/2024"
    record["fecha_apertura"] = "30/03/2024"
    return record


def make_record_money_with_separators() -> dict[str, Any]:
    """A record with money values in various string formats."""
    record = make_basic_record()
    record["id_llamado"] = 193405
    record["monto_adjudicado"] = "1.500.000.000"  # Paraguayan/Argentine style
    return record


def make_record_no_id() -> dict[str, Any]:
    """An unparseable record missing the required ID."""
    return {
        "anio": 2024,
        "convocante": "Some Entity",
        # Missing id_llamado
    }


# A small synthetic dataset for end-to-end testing
SYNTHETIC_DATASET: list[dict[str, Any]] = [
    make_basic_record(),
    make_record_licitacion_publica(),
    make_record_adjudicacion_directa(),
    make_record_no_bids(),
    make_record_malformed_dates(),
    make_record_spanish_dates(),
    make_record_money_with_separators(),
]

# ===== DEMO-RICH RECORDS (for the Streamlit UI) =====

def make_salud_single_bidder() -> dict[str, Any]:
    """Ministry of Salud contract with 1 bid → R018 flagged. Good demo."""
    return {
        "id_llamado": 193410,
        "anio": 2024,
        "convocante": "Ministerio de Salud Pública y Bienestar Social",
        "tipo_procedimiento": "CO",
        "estado": "ADJ",
        "categoria": "42",
        "titulo": "Adquisición de equipos de rayos X para hospitales regionales",
        "monto_adjudicado": 780000000,
        "proveedor_adjudicado": "Insumos Médicos del Paraguay S.R.L.",
        "proveedor_adjudicado_id": "80098765-4",
        "fecha_publicacion": "2024-02-01",
        "fecha_apertura": "2024-02-15",
        "bids": [
            {"id": "b1", "proveedor_id": "80098765-4", "proveedor_nombre": "Insumos Médicos del Paraguay S.R.L.",
             "monto_ofertado": 780000000, "estado": "valid", "fecha_oferta": "2024-02-14"},
        ],
    }


def make_salud_short_period() -> dict[str, Any]:
    """Ministry of Salud contract with 5-day period → R003 flagged."""
    return {
        "id_llamado": 193420,
        "anio": 2024,
        "convocante": "Ministerio de Salud Pública y Bienestar Social",
        "tipo_procedimiento": "CO",
        "estado": "ADJ",
        "categoria": "51",
        "titulo": "Compra de medicamentos oncológicos",
        "monto_adjudicado": 950000000,
        "proveedor_adjudicado": "Farmacéutica Nacional S.A.",
        "proveedor_adjudicado_id": "80123456-7",
        "fecha_publicacion": "2024-03-15",
        "fecha_apertura": "2024-03-20",  # 5 days
        "bids": [
            {"id": "b1", "proveedor_id": "80123456-7", "proveedor_nombre": "Farmacéutica Nacional S.A.",
             "monto_ofertado": 950000000, "estado": "valid", "fecha_oferta": "2024-03-19"},
            {"id": "b2", "proveedor_id": "80045678-9", "proveedor_nombre": "MedCorp Paraguay S.A.",
             "monto_ofertado": 970000000, "estado": "valid", "fecha_oferta": "2024-03-18"},
        ],
    }


def make_mop_competitive() -> dict[str, Any]:
    """Ministry of Public Works with 3 bids, healthy competition, no flags."""
    return {
        "id_llamado": 193430,
        "anio": 2024,
        "convocante": "Ministerio de Obras Públicas y Comunicaciones",
        "tipo_procedimiento": "LPN",
        "estado": "ADJ",
        "categoria": "78",
        "titulo": "Pavimentación de ruta nacional N°7 tramo Santa Rosa-San Ignacio",
        "monto_adjudicado": 8500000000,  # 8.5B PYG
        "proveedor_adjudicado": "Constructora Paraná S.A.",
        "proveedor_adjudicado_id": "80345678-1",
        "fecha_publicacion": "2024-01-01",
        "fecha_apertura": "2024-02-15",  # 45 days
        "bids": [
            {"id": "b1", "proveedor_id": "80345678-1", "proveedor_nombre": "Constructora Paraná S.A.",
             "monto_ofertado": 8500000000, "estado": "valid", "fecha_oferta": "2024-02-14"},
            {"id": "b2", "proveedor_id": "80456789-2", "proveedor_nombre": "Consorcio Vial Paraguay",
             "monto_ofertado": 9200000000, "estado": "valid", "fecha_oferta": "2024-02-13"},
            {"id": "b3", "proveedor_id": "80567890-3", "proveedor_nombre": "Ingeniería de Caminos S.A.",
             "monto_ofertado": 8900000000, "estado": "valid", "fecha_oferta": "2024-02-12"},
        ],
    }


# Full demo dataset
DEMO_DATASET: list[dict[str, Any]] = (
    SYNTHETIC_DATASET
    + [
        make_salud_single_bidder(),
        make_salud_short_period(),
        make_mop_competitive(),
    ]
)
