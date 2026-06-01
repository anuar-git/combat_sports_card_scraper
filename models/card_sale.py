import hashlib
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class RawCardSale(BaseModel):
    listing_id: str
    source: Literal["ebay", "pwcc", "goldin"]
    scraped_at: datetime
    sale_price_usd: Decimal
    sale_date: date
    listing_title: str
    fighter_name: str | None = None
    card_year: int | None = None
    card_set: str | None = None
    card_number: str | None = None
    grade: str | None = None
    grader: Literal["PSA", "BGS", "SGC", "CGC", "Raw"] | None = None
    grade_numeric: float | None = None
    listing_url: HttpUrl
    image_url: HttpUrl | None = None
    sale_type: Literal["auction", "buy_it_now", "best_offer"]
    record_hash: str = Field(default="", description="Auto-generated SHA-256 hash")

    @field_validator("sale_price_usd")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("sale_price_usd must be greater than 0")
        if v >= 1_000_000:
            raise ValueError("sale_price_usd must be less than 1,000,000")
        return v

    @field_validator("card_year")
    @classmethod
    def validate_card_year(cls, v: int | None) -> int | None:
        if v is None:
            return v
        current_year = datetime.now().year
        if v < 1990 or v > current_year:
            raise ValueError(f"card_year must be between 1990 and {current_year}")
        return v

    @field_validator("grade_numeric")
    @classmethod
    def validate_grade_numeric(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if v < 1.0 or v > 10.0:
            raise ValueError("grade_numeric must be between 1.0 and 10.0")
        return v

    @field_validator("listing_title")
    @classmethod
    def validate_listing_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("listing_title must not be empty")
        return v

    @field_validator("fighter_name")
    @classmethod
    def normalize_fighter_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        return stripped.title() if stripped else None

    @model_validator(mode="after")
    def compute_record_hash(self) -> "RawCardSale":
        hash_input = f"{self.listing_id}{self.source}"
        computed = hashlib.sha256(hash_input.encode()).hexdigest()
        # Always overwrite — record_hash must not be set manually
        object.__setattr__(self, "record_hash", computed)
        return self


class ScrapeBatchResult(BaseModel):
    source: str
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    started_at: datetime
    completed_at: datetime
    records_scraped: int
    records_valid: int
    records_new: int
    records_written: int
    errors: list[str] = Field(default_factory=list)
