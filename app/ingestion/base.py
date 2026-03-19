from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlmodel import Session, SQLModel

# Raw records from vendors -- untyped dicts before transformation
RawRecord = dict


@dataclass
class IngestResult:
    vendor_name: str = ""
    records_fetched: int = 0
    records_loaded: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)


class BaseIngestor(ABC):
    """Abstract base class for vendor data ingestion.

    Subclasses implement fetch() and transform().
    The base class provides load() and run().
    """

    vendor_name: str = "unknown"

    def __init__(self, session: Session):
        self.session = session

    @abstractmethod
    def fetch(self) -> list[RawRecord]:
        """Pull raw data from vendor source."""
        ...

    @abstractmethod
    def transform(self, raw: list[RawRecord]) -> list[SQLModel]:
        """Normalize raw records into canonical SQLModel instances."""
        ...

    def load(self, records: list[SQLModel]) -> int:
        """Persist records to the database. Returns count of records loaded."""
        for record in records:
            self.session.add(record)
        self.session.commit()
        return len(records)

    def run(self) -> IngestResult:
        """Execute the full fetch -> transform -> load pipeline."""
        result = IngestResult(vendor_name=self.vendor_name)

        raw = self.fetch()
        result.records_fetched = len(raw)

        records = self.transform(raw)
        result.records_loaded = self.load(records)

        return result
