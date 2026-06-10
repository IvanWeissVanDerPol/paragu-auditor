"""Tests for the Paraguay DNCP JSON-LD → OCDS mapper."""
import pytest

from paragu_auditor.data.jsonld_mapper import (
    make_ocid,
    map_paraguay_code,
    map_category,
    parse_date,
    parse_money,
    jsonld_to_ocds,
    load_silver_data,
)
from paragu_auditor.data.schemas import PARAGUAY_METHOD_MAP, CompiledRelease
from tests.data.fixtures.synthetic import (
    make_basic_record,
    make_record_licitacion_publica,
    make_record_adjudicacion_directa,
    make_record_no_bids,
    make_record_malformed_dates,
    make_record_spanish_dates,
    make_record_money_with_separators,
    make_record_no_id,
    SYNTHETIC_DATASET,
)


class TestMakeOcid:
    def test_basic(self):
        assert make_ocid(193399) == "ocds-03ad3f-193399"

    def test_string_id(self):
        assert make_ocid("12345") == "ocds-03ad3f-12345"

    def test_uses_dncp_prefix(self):
        """The prefix `ocds-03ad3f` is the Paraguay DNCP-assigned OCP ID prefix."""
        ocid = make_ocid(1)
        assert ocid.startswith("ocds-03ad3f-")


class TestMapParaguayCode:
    def test_competitive_methods_map_to_open(self):
        assert map_paraguay_code("CO") == "open"  # Concurso de Ofertas
        assert map_paraguay_code("LPN") == "open"  # Licitación Pública Nacional
        assert map_paraguay_code("LPI") == "open"  # Licitación Pública Internacional

    def test_selective_method(self):
        assert map_paraguay_code("LR") == "selective"  # Licitación Restringida
        assert map_paraguay_code("SO") == "selective"  # Sorteo de Obras

    def test_limited_method(self):
        assert map_paraguay_code("CM") == "limited"  # Compras Menores
        assert map_paraguay_code("CDU") == "limited"  # Compras por Debajo del Umbral

    def test_direct_method(self):
        assert map_paraguay_code("AD") == "direct"  # Adjudicación Directa
        assert map_paraguay_code("EX") == "direct"  # Procesos de Excepción

    def test_empty_code(self):
        assert map_paraguay_code("") == ""

    def test_unknown_code_passthrough(self):
        """Unknown codes are passed through (validator will catch them)."""
        assert map_paraguay_code("XYZ") == "XYZ"


class TestMapCategory:
    def test_known_segment(self):
        result = map_category("40")
        assert "Computers" in result or "comput" in result.lower()

    def test_zero_padded(self):
        result_1 = map_category("40")
        result_2 = map_category("040")
        # Both should return the same human-readable string
        assert result_1 == result_2

    def test_unknown_segment(self):
        assert map_category("999") == "Category 999"


class TestParseDate:
    def test_iso_format(self):
        from datetime import date
        assert parse_date("2024-03-15") == date(2024, 3, 15)

    def test_latam_dd_mm_yyyy(self):
        from datetime import date
        assert parse_date("15/03/2024") == date(2024, 3, 15)

    def test_dash_format(self):
        from datetime import date
        assert parse_date("15-03-2024") == date(2024, 3, 15)

    def test_iso_datetime(self):
        from datetime import date
        result = parse_date("2024-03-15T10:30:00")
        assert result == date(2024, 3, 15)

    def test_none(self):
        assert parse_date(None) is None

    def test_empty_string(self):
        assert parse_date("") is None

    def test_dash_placeholder(self):
        """Paraguay DNCP uses '-' for missing dates."""
        assert parse_date("-") is None

    def test_unparseable(self):
        """Unparseable strings return None, don't raise."""
        assert parse_date("not a date") is None
        assert parse_date("garbage") is None


class TestParseMoney:
    def test_int(self):
        from paragu_auditor.data.schemas import Money
        result = parse_money(1500000000)
        assert result is not None
        assert result.amount == 1500000000.0
        assert result.currency == "PYG"

    def test_float(self):
        from paragu_auditor.data.schemas import Money
        result = parse_money(1500000000.5)
        assert result is not None
        assert result.amount == 1500000000.5

    def test_string_no_separators(self):
        from paragu_auditor.data.schemas import Money
        result = parse_money("1500000000")
        assert result is not None
        assert result.amount == 1500000000.0

    def test_string_paraguayan_separators(self):
        from paragu_auditor.data.schemas import Money
        result = parse_money("1.500.000.000")
        assert result is not None
        assert result.amount == 1500000000.0

    def test_string_american_separators(self):
        from paragu_auditor.data.schemas import Money
        result = parse_money("1,500,000,000")
        assert result is not None
        assert result.amount == 1500000000.0

    def test_string_with_currency_symbol(self):
        from paragu_auditor.data.schemas import Money
        result = parse_money("1.500.000.000 PYG")
        assert result is not None
        assert result.amount == 1500000000.0

    def test_none(self):
        assert parse_money(None) is None

    def test_empty_string(self):
        assert parse_money("") is None

    def test_dash_placeholder(self):
        assert parse_money("-") is None


class TestJsonldToOcds:
    def test_basic_record(self):
        record = make_basic_record()
        release = jsonld_to_ocds(record)

        assert isinstance(release, CompiledRelease)
        assert release.ocid == "ocds-03ad3f-193399"
        assert release.tender.id == "193399"
        assert release.tender.procurement_method == "open"  # mapped from "CO"
        assert release.tender.procurement_method_details == "CO"
        assert release.tender.procuring_entity_name == "Dirección Nacional de Contrataciones Públicas"
        assert len(release.tender.bids) == 2
        assert release.tender.n_bids == 2
        assert release.tender.n_valid_bids == 2

    def test_lpn_maps_to_open(self):
        record = make_record_licitacion_publica()
        release = jsonld_to_ocds(record)
        assert release.tender.procurement_method == "open"

    def test_direct_award(self):
        record = make_record_adjudicacion_directa()
        release = jsonld_to_ocds(record)
        assert release.tender.procurement_method == "direct"
        # Should still have award
        assert len(release.awards) == 1

    def test_no_bids_deserted(self):
        record = make_record_no_bids()
        release = jsonld_to_ocds(record)
        assert release.tender.n_bids == 0
        assert release.tender.n_valid_bids == 0
        # Awards should be empty (status was DES, not ADJ)
        assert len(release.awards) == 0

    def test_malformed_dates_default_to_none(self):
        record = make_record_malformed_dates()
        release = jsonld_to_ocds(record)
        # Malformed dates should not raise; they default to None
        assert release.tender.tender_period_start is None
        assert release.tender.tender_period_end is None

    def test_spanish_date_formats(self):
        record = make_record_spanish_dates()
        release = jsonld_to_ocds(record)
        from datetime import date
        assert release.tender.tender_period_start == date(2024, 3, 15)
        assert release.tender.tender_period_end == date(2024, 3, 30)

    def test_money_with_separators(self):
        record = make_record_money_with_separators()
        release = jsonld_to_ocds(record)
        # The award should have the parsed money
        if release.awards:
            assert release.awards[0].value.amount == 1500000000.0

    def test_winning_and_second_lowest_bid(self):
        record = make_basic_record()
        release = jsonld_to_ocds(record)
        # Winning bid: 1.5B, Second-lowest: 1.65B
        assert release.winning_bid_amount() == 1500000000.0
        assert release.second_lowest_bid_amount() == 1650000000.0

    def test_only_one_valid_bid(self):
        record = make_basic_record()
        # Mark second bid as invalid
        record["bids"][1]["estado"] = "invalid"
        release = jsonld_to_ocds(record)
        assert release.tender.n_valid_bids == 1
        # With only 1 valid bid, second-lowest should be None
        assert release.second_lowest_bid_amount() is None

    def test_missing_id_raises(self):
        record = make_record_no_id()
        with pytest.raises(ValueError) as exc_info:
            jsonld_to_ocds(record)
        assert "id_llamado" in str(exc_info.value) or "tender_id" in str(exc_info.value)


class TestLoadSilverData:
    def test_load_list(self):
        releases = load_silver_data(SYNTHETIC_DATASET)
        # Should have loaded at least 6 of the 7 (one is malformed: no_id)
        assert len(releases) >= 6
        assert len(releases) <= 7
        for r in releases:
            assert isinstance(r, CompiledRelease)

    def test_load_skips_invalid_records(self):
        # Include a deliberately invalid record
        bad_data = SYNTHETIC_DATASET + [make_record_no_id()]
        releases = load_silver_data(bad_data)
        # Should skip the bad one
        assert all(r.ocid for r in releases)
        # No empty OCIDs from the no_id record
        assert all(r.ocid != "ocds-03ad3f-None" for r in releases)

    def test_load_file(self, tmp_path):
        import json
        # Write a JSONL file
        jsonl_path = tmp_path / "test.jsonl"
        with jsonl_path.open("w") as f:
            for record in SYNTHETIC_DATASET:
                f.write(json.dumps(record) + "\n")

        releases = load_silver_data(str(jsonl_path))
        assert len(releases) >= 6

    def test_load_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_silver_data("/tmp/this_does_not_exist_xyz.jsonl")
