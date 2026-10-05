"""Pydantic data contracts for the portfolio data boundaries.

These models are the single source of truth for the shape of on-disk data.
Every write to a data file goes through them, and reads validate against them,
so a pipeline, service, or dashboard can never silently disagree on columns
again (the class of bug that crashed the dashboard with ``KeyError``).
"""

from __future__ import annotations

from datetime import date as _date
from typing import ClassVar, Iterable, Literal
from uuid import uuid4

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ContractError(ValueError):
    """Raised when data on disk violates a schema contract."""

    def __init__(self, model: str, row_index, reason: str):
        super().__init__(f"Invalid {model} record at row {row_index}: {reason}")
        self.model_name = model
        self.row_index = row_index


class _RowModel(BaseModel):
    """Shared helpers for mapping a model to/from a CSV row."""

    COLUMNS: ClassVar[tuple[str, ...]] = ()

    def to_row(self) -> dict:
        return {col: getattr(self, col) for col in self.COLUMNS}

    @classmethod
    def from_row(cls, row: dict):
        clean = {k: row.get(k) for k in cls.COLUMNS if k in row}
        return cls.model_validate(clean)

    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame) -> list:
        """Validate every row of a DataFrame; raise ContractError on the first."""
        records = df.to_dict("records")
        items = []
        for index, row in enumerate(records):
            try:
                items.append(cls.from_row(row))
            except ValidationError as exc:
                raise ContractError(cls.__name__, index, str(exc)) from exc
        return items

    @classmethod
    def dataframe(cls, items: Iterable["_RowModel"]) -> pd.DataFrame:
        rows = [item.to_row() for item in items]
        return pd.DataFrame(rows, columns=list(cls.COLUMNS))


class Transaction(_RowModel):
    """One append-only buy/sell event in the ledger."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transaction_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    stock_id: int
    stock_name: str
    action: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    date: _date = Field(default_factory=_date.today)

    COLUMNS = (
        "transaction_id",
        "stock_id",
        "stock_name",
        "action",
        "quantity",
        "price",
        "date",
    )


class PortfolioHolding(_RowModel):
    """A derived position: net quantity and average buy price per stock."""

    model_config = ConfigDict(extra="forbid")

    stock_id: int
    stock_name: str
    quantity: float
    avg_buy_price: float
    total_investment: float

    COLUMNS = (
        "stock_id",
        "stock_name",
        "quantity",
        "avg_buy_price",
        "total_investment",
    )
