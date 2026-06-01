import json
import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from models.card_sale import RawCardSale
from utils.dedup import filter_new_records, load_seen_hashes, save_seen_hashes, update_seen_hashes

VALID_KWARGS = dict(
    source="ebay",
    scraped_at=datetime.now(timezone.utc),
    sale_price_usd=Decimal("50.00"),
    sale_date=date(2024, 1, 1),
    listing_title="UFC Card PSA 10",
    listing_url="https://www.ebay.com/itm/111",
    sale_type="auction",
)


def make_sale(listing_id: str) -> RawCardSale:
    return RawCardSale(listing_id=listing_id, **VALID_KWARGS)


def test_load_seen_hashes_returns_empty_set_when_missing():
    result = load_seen_hashes("/tmp/nonexistent_file_abc123.json")
    assert result == set()


def test_load_seen_hashes_loads_existing_file():
    hashes = {"hash1", "hash2", "hash3"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sorted(hashes), f)
        path = f.name
    try:
        loaded = load_seen_hashes(path)
        assert loaded == hashes
    finally:
        os.unlink(path)


def test_load_seen_hashes_raises_on_invalid_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json {{{")
        path = f.name
    try:
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_seen_hashes(path)
    finally:
        os.unlink(path)


def test_filter_new_records_returns_only_unseen():
    r1 = make_sale("id1")
    r2 = make_sale("id2")
    r3 = make_sale("id3")
    seen = {r1.record_hash}
    result = filter_new_records([r1, r2, r3], seen)
    assert r1 not in result
    assert r2 in result
    assert r3 in result


def test_filter_new_records_returns_all_when_seen_empty():
    records = [make_sale(f"id{i}") for i in range(5)]
    result = filter_new_records(records, set())
    assert result == records


def test_filter_new_records_returns_empty_when_all_seen():
    records = [make_sale(f"id{i}") for i in range(3)]
    seen = {r.record_hash for r in records}
    result = filter_new_records(records, seen)
    assert result == []


def test_update_seen_hashes_adds_new_hashes():
    existing = {"existing_hash"}
    records = [make_sale("id1"), make_sale("id2")]
    updated = update_seen_hashes(records, existing)
    assert "existing_hash" in updated
    for r in records:
        assert r.record_hash in updated


def test_update_seen_hashes_does_not_mutate_input():
    existing = {"existing_hash"}
    records = [make_sale("id1")]
    updated = update_seen_hashes(records, existing)
    assert existing == {"existing_hash"}
    assert len(updated) == 2


def test_save_seen_hashes_writes_sorted_reloadable_json():
    hashes = {"zzz", "aaa", "mmm"}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "hashes.json")
        save_seen_hashes(hashes, path)
        with open(path) as f:
            data = json.load(f)
        assert data == sorted(hashes)
        reloaded = load_seen_hashes(path)
        assert reloaded == hashes
