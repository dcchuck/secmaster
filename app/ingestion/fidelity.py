from app.ingestion.base import BaseIngestor, RawRecord
from sqlmodel import SQLModel


class FidelityIngestor(BaseIngestor):
    """Fidelity data ingestion adapter.

    This is a stub -- the actual implementation will be ported
    from the existing Fidelity ingestion work.
    """

    vendor_name = "fidelity"

    def fetch(self) -> list[RawRecord]:
        raise NotImplementedError(
            "Fidelity ingestor not yet implemented. "
            "Port existing ingestion work to this interface."
        )

    def transform(self, raw: list[RawRecord]) -> list[SQLModel]:
        raise NotImplementedError(
            "Fidelity ingestor not yet implemented."
        )
