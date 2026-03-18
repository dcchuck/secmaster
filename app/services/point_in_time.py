from datetime import date
from typing import TypeVar

from sqlmodel import SQLModel

T = TypeVar("T", bound=SQLModel)


def apply_as_of_filter(stmt, model: type[T], as_of: date | None):
    """Apply effective dating filter to a select statement.

    Uses the pattern:
        WHERE effective_start_date <= as_of
          AND (effective_end_date IS NULL OR effective_end_date > as_of)
    """
    if as_of is None:
        return stmt

    stmt = stmt.where(model.effective_start_date <= as_of)
    stmt = stmt.where(
        (model.effective_end_date.is_(None)) | (model.effective_end_date > as_of)  # type: ignore
    )
    return stmt
