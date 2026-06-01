import hashlib
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from models.card_sale import RawCardSale

VALID_KWARGS = dict(
    listing_id="abc123",
    source="ebay",
    scraped_at=datetime.now(timezone.utc),
    sale_price_usd=Decimal("99.99"),
    sale_date=date(2024, 6, 1),
    listing_title="UFC Conor McGregor PSA 10 Rookie Card",
    listing_url="https://www.ebay.com/itm/123456",
    sale_type="auction",
)


def make_sale(**overrides) -> RawCardSale:
    return RawCardSale(**{**VALID_KWARGS, **overrides})


def test_valid_instantiation():
    sale = make_sale()
    assert sale.listing_id == "abc123"
    assert sale.source == "ebay"
    assert sale.sale_price_usd == Decimal("99.99")


def test_record_hash_auto_generated():
    sale = make_sale()
    expected = hashlib.sha256(b"abc123ebay").hexdigest()
    assert sale.record_hash == expected


def test_record_hash_cannot_be_overridden():
    """Manually supplied hash must be overwritten by the model validator."""
    sale = RawCardSale(**{**VALID_KWARGS, "record_hash": "fake_hash"})
    expected = hashlib.sha256(b"abc123ebay").hexdigest()
    assert sale.record_hash == expected
    assert sale.record_hash != "fake_hash"


def test_sale_price_rejects_zero():
    with pytest.raises(ValidationError):
        make_sale(sale_price_usd=Decimal("0"))


def test_sale_price_rejects_negative():
    with pytest.raises(ValidationError):
        make_sale(sale_price_usd=Decimal("-5.00"))


def test_sale_price_rejects_over_limit():
    with pytest.raises(ValidationError):
        make_sale(sale_price_usd=Decimal("1000000"))


def test_sale_price_accepts_boundary():
    sale = make_sale(sale_price_usd=Decimal("999999.99"))
    assert sale.sale_price_usd == Decimal("999999.99")


def test_card_year_rejects_before_1990():
    with pytest.raises(ValidationError):
        make_sale(card_year=1989)


def test_card_year_rejects_future():
    from datetime import datetime
    future_year = datetime.now().year + 1
    with pytest.raises(ValidationError):
        make_sale(card_year=future_year)


def test_card_year_accepts_valid():
    sale = make_sale(card_year=2009)
    assert sale.card_year == 2009


def test_card_year_none_allowed():
    sale = make_sale(card_year=None)
    assert sale.card_year is None


def test_grade_numeric_rejects_below_1():
    with pytest.raises(ValidationError):
        make_sale(grade_numeric=0.9)


def test_grade_numeric_rejects_above_10():
    with pytest.raises(ValidationError):
        make_sale(grade_numeric=10.1)


def test_grade_numeric_accepts_boundary_values():
    sale_min = make_sale(grade_numeric=1.0)
    sale_max = make_sale(grade_numeric=10.0)
    assert sale_min.grade_numeric == 1.0
    assert sale_max.grade_numeric == 10.0


def test_listing_title_rejects_empty_string():
    with pytest.raises(ValidationError):
        make_sale(listing_title="")


def test_listing_title_rejects_whitespace_only():
    with pytest.raises(ValidationError):
        make_sale(listing_title="   ")


def test_fighter_name_is_title_cased():
    sale = make_sale(fighter_name="  conor mcgregor  ")
    assert sale.fighter_name == "Conor Mcgregor"


def test_fighter_name_none_allowed():
    sale = make_sale(fighter_name=None)
    assert sale.fighter_name is None
