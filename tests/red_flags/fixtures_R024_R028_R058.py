"""Cardinal-style OCID fixtures for R024 (close price), R028 (identical),
and R058 (heavily discounted)."""
from __future__ import annotations

from datetime import date
from paragu_auditor.data.schemas import CompiledRelease, Tender, Bid, Money, Award


def make_close_price_open_tender() -> CompiledRelease:
    """Open tender, winning=100, 2nd=104 → diff=4% ≤ 5% → FLAGGED R024."""
    return CompiledRelease(
        ocid="ocds-03ad3f-R024-001",
        tender=Tender(id="R024-001", ocid="ocds-03ad3f-R024-001",
            procurement_method="open",
            bids=[
                Bid(id="b1", bidder_id="v1", bidder_name="LowBidder Co",
                    amount=Money(amount=100.0), status="valid"),
                Bid(id="b2", bidder_id="v2", bidder_name="CloseBidder Co",
                    amount=Money(amount=104.0), status="valid"),
            ], n_bids=2, n_valid_bids=2),
        awards=[Award(id="a1", ocid="ocds-03ad3f-R024-001", status="active",
                       value=Money(amount=100.0), supplier_ids=["v1"])],
    )


def make_normal_price_open_tender() -> CompiledRelease:
    """Open tender, winning=100, 2nd=200 → diff=100% → NOT FLAGGED."""
    return CompiledRelease(
        ocid="ocds-03ad3f-R024-002",
        tender=Tender(id="R024-002", ocid="ocds-03ad3f-R024-002",
            procurement_method="open",
            bids=[
                Bid(id="b1", bidder_id="v1", bidder_name="LowBidder Co",
                    amount=Money(amount=100.0), status="valid"),
                Bid(id="b2", bidder_id="v2", bidder_name="Expensive Co",
                    amount=Money(amount=200.0), status="valid"),
            ], n_bids=2, n_valid_bids=2),
    )


def make_identical_price_tender() -> CompiledRelease:
    """2 bids both at 100 → FLAGGED R028."""
    return CompiledRelease(
        ocid="ocds-03ad3f-R028-001",
        tender=Tender(id="R028-001", ocid="ocds-03ad3f-R028-001",
            procurement_method="open",
            bids=[
                Bid(id="b1", bidder_id="v1", bidder_name="Co A",
                    amount=Money(amount=100.0), status="valid"),
                Bid(id="b2", bidder_id="v2", bidder_name="Co B",
                    amount=Money(amount=100.0), status="valid"),
            ], n_bids=2, n_valid_bids=2),
        awards=[Award(id="a1", ocid="ocds-03ad3f-R028-001", status="active",
                       value=Money(amount=100.0), supplier_ids=["v1", "v2"])],
    )


def make_different_price_tender() -> CompiledRelease:
    """3 bids all different → NOT FLAGGED R028."""
    return CompiledRelease(
        ocid="ocds-03ad3f-R028-002",
        tender=Tender(id="R028-002", ocid="ocds-03ad3f-R028-002",
            procurement_method="open",
            bids=[
                Bid(id="b1", bidder_id="v1", bidder_name="Co A",
                    amount=Money(amount=100.0), status="valid"),
                Bid(id="b2", bidder_id="v2", bidder_name="Co B",
                    amount=Money(amount=110.0), status="valid"),
                Bid(id="b3", bidder_id="v3", bidder_name="Co C",
                    amount=Money(amount=120.0), status="valid"),
            ], n_bids=3, n_valid_bids=3),
    )


def make_dataset_for_R058() -> list[CompiledRelease]:
    """5 tenders: 4 normal, 1 heavy outlier. Outlier should be flagged."""
    base = []
    for i in range(4):
        ocid = f"ocds-03ad3f-R058-00{i+2}"
        base.append(CompiledRelease(
            ocid=ocid,
            tender=Tender(id=ocid, ocid=ocid, procurement_method="open",
                bids=[
                    Bid(id="b1", bidder_id="v1", bidder_name="A",
                        amount=Money(amount=100.0), status="valid"),
                    Bid(id="b2", bidder_id="v2", bidder_name="B",
                        amount=Money(amount=110.0 + i*5), status="valid"),
                ], n_bids=2, n_valid_bids=2),
            awards=[Award(id=f"a{i}", ocid=ocid, status="active",
                          value=Money(amount=100.0), supplier_ids=["v1"])],
        ))
    # Add the outlier: winning=100, 2nd=300 → diff=200%
    base.append(CompiledRelease(
        ocid="ocds-03ad3f-R058-999",
        tender=Tender(id="ocds-03ad3f-R058-999", ocid="ocds-03ad3f-R058-999",
            procurement_method="open",
            bids=[
                Bid(id="b1", bidder_id="v_outlier", bidder_name="Outlier Co",
                    amount=Money(amount=100.0), status="valid"),
                Bid(id="b2", bidder_id="v_normal", bidder_name="Normal Co",
                    amount=Money(amount=300.0), status="valid"),
            ], n_bids=2, n_valid_bids=2),
        awards=[Award(id="a_last", ocid="ocds-03ad3f-R058-999", status="active",
                      value=Money(amount=100.0), supplier_ids=["v_outlier"])],
    ))
    return base
