from datetime import date

import pytest
from sqlmodel import Session

from app.ingestion.base import BaseIngestor, IngestResult, RawRecord
from app.models.issuer import Issuer


class FakeIngestor(BaseIngestor):
    """Test ingestor that creates issuers from fake raw records."""

    vendor_name = "fake"

    def fetch(self) -> list[RawRecord]:
        return [
            {"legal_name": "Fake Corp", "country": "US"},
            {"legal_name": "Fake Inc", "country": "CA"},
        ]

    def transform(self, raw: list[RawRecord]) -> list[Issuer]:
        return [
            Issuer(
                legal_name=r["legal_name"],
                country_incorporation=r["country"],
            )
            for r in raw
        ]


def test_ingestor_run(session):
    ingestor = FakeIngestor(session)
    result = ingestor.run()

    assert isinstance(result, IngestResult)
    assert result.records_fetched == 2
    assert result.records_loaded == 2
    assert result.errors == 0


def test_ingestor_load_persists_records(session):
    ingestor = FakeIngestor(session)
    ingestor.run()

    from sqlmodel import select
    issuers = session.exec(select(Issuer)).all()
    assert len(issuers) >= 2
