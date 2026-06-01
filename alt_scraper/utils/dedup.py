import json
import os
from typing import TYPE_CHECKING

from utils.logger import get_logger

if TYPE_CHECKING:
    from models.card_sale import RawCardSale

_log = get_logger("dedup")


def load_seen_hashes(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        return set()
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in seen hashes file {path}: {exc}") from exc
    return set(data)


def save_seen_hashes(hashes: set[str], path: str) -> None:
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(sorted(hashes), f, indent=2)
    os.replace(tmp_path, path)


def filter_new_records(records: list["RawCardSale"], seen: set[str]) -> list["RawCardSale"]:
    new = [r for r in records if r.record_hash not in seen]
    filtered_count = len(records) - len(new)
    if filtered_count:
        _log.info("dedup_filtered", filtered=filtered_count, new=len(new))
    return new


def update_seen_hashes(records: list["RawCardSale"], seen: set[str]) -> set[str]:
    updated = seen | {r.record_hash for r in records}
    return updated
