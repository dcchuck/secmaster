from datetime import date
from uuid import UUID

from app.models.corporate_action import CorporateAction
from app.models.classification import IssuerClassificationHistory
from app.models.issuer import Issuer
from app.models.security import Security
from app.models.shares_outstanding import SharesOutstandingHistory
from app.models.vendor import VendorSecurityMap


def test_create_corporate_action(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    security = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(security)
    session.commit()

    action = CorporateAction(
        security_id=security.security_id,
        issuer_id=issuer.issuer_id,
        action_type="reverse_split",
        effective_date=date(2023, 3, 1),
        ratio_from=10,
        ratio_to=1,
        source="fidelity",
    )
    session.add(action)
    session.commit()
    session.refresh(action)

    assert isinstance(action.corporate_action_id, UUID)
    assert action.action_type == "reverse_split"
    assert action.ratio_from == 10
    assert action.ratio_to == 1


def test_create_shares_outstanding_history(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    security = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(security)
    session.commit()

    shares = SharesOutstandingHistory(
        security_id=security.security_id,
        as_of_date=date(2023, 6, 30),
        shares_outstanding=1_000_000,
        public_float=750_000,
        source="fidelity",
    )
    session.add(shares)
    session.commit()
    session.refresh(shares)

    assert shares.shares_outstanding == 1_000_000
    assert shares.public_float == 750_000


def test_create_issuer_classification_history(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    classification = IssuerClassificationHistory(
        issuer_id=issuer.issuer_id,
        classification_system="SIC",
        classification_code="7372",
        classification_name="Prepackaged Software",
        effective_start_date=date(2020, 1, 1),
        source="sec_edgar",
    )
    session.add(classification)
    session.commit()
    session.refresh(classification)

    assert classification.classification_system == "SIC"
    assert classification.classification_code == "7372"


def test_create_vendor_security_map(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    security = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(security)
    session.commit()

    vendor_map = VendorSecurityMap(
        vendor_name="fidelity",
        vendor_entity_type="security",
        vendor_id="FID-12345",
        issuer_id=issuer.issuer_id,
        security_id=security.security_id,
        effective_start_date=date(2020, 1, 1),
        confidence_score=0.95,
        mapping_method="exact_cusip",
    )
    session.add(vendor_map)
    session.commit()
    session.refresh(vendor_map)

    assert vendor_map.vendor_name == "fidelity"
    assert vendor_map.confidence_score == 0.95
