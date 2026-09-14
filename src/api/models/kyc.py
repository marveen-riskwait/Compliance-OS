"""KYC/KYB profile fields (with provenance) and the requirement model.

ProfileField gives every important piece of customer data a provenance trail:
    value, source, verified, verified_by, confidence, last_changed_at
so the platform can answer "where did this come from and did we verify it?".

RequirementDefinition + RequirementInstance drive the "missing information"
feature: what a customer of a given type/risk/jurisdiction must provide, and
what is still outstanding — computed before the consultant opens the review.
"""
from datetime import datetime

from sqlalchemy import String, Boolean, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import db, utcnow

# KYC field categories (per the document's KYC module).
FIELD_CATEGORIES = (
    "IDENTITY", "PERSONAL", "ADDRESS", "TAX", "NATIONALITY", "RESIDENCY",
    "OCCUPATION", "SOURCE_OF_FUNDS", "SOURCE_OF_WEALTH", "PURPOSE",
    "BUSINESS", "REGISTRATION",
)

REQUIREMENT_KINDS = ("DATA", "DOCUMENT")
REQUIREMENT_STATUSES = ("MISSING", "RECEIVED", "VERIFIED", "WAIVED")

# Risk ordering so a requirement can apply "at HIGH risk and above".
RISK_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


_FIELD_LABELS = None


def field_label(key):
    """Human label from the KYC form schema, else the key itself."""
    global _FIELD_LABELS
    if _FIELD_LABELS is None:
        try:
            from api.kyc_form import field_index
            _FIELD_LABELS = {k: v.get("label") for k, v in field_index().items()}
        except Exception:      # schema import must never break serialisation
            _FIELD_LABELS = {}
    return _FIELD_LABELS.get(key) or key


_REGISTRY_NAMES = {
    "gleif": "GLEIF (global LEI register)", "companies_house": "Companies House (UK register)",
    "vies": "VIES (EU VAT validation)", "sec_edgar": "SEC EDGAR (US filings)",
    "sirene": "INSEE Sirene (French register)", "wikidata_pep": "Wikidata (PEP lead)",
    "adverse_media": "GDELT (adverse media)",
}


def provenance_label(source, verified=False, confidence=None):
    """Where a value comes from, in words an analyst reads at a glance —
    'source: registry:gleif · conf 90%' meant nothing to the reviewers."""
    src = (source or "manual")
    if src.startswith("registry:"):
        name = _REGISTRY_NAMES.get(src.split(":", 1)[1], src.split(":", 1)[1])
        who = f"Imported from {name}"
    elif src.startswith("provider:"):
        who = f"Reported by {src.split(':', 1)[1]} (verification provider)"
    elif src == "kyc_form":
        who = "Declared in the KYC form"
    elif src == "portal":
        who = "Declared by the customer in the portal"
    elif src == "enrichment":
        who = "Found by automatic enrichment"
    else:
        who = "Entered by staff"
    if verified:
        who += " · verified"
    elif confidence is not None:
        who += f" · {int(round(confidence * 100))}% confidence, not yet verified"
    else:
        who += " · not yet verified"
    return who


class ProfileField(db.Model):
    __tablename__ = "profile_field"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), nullable=False)

    field_key: Mapped[str] = mapped_column(String(60), nullable=False)   # e.g. date_of_birth
    category: Mapped[str] = mapped_column(String(40), nullable=True)
    value: Mapped[str] = mapped_column(Text, nullable=True)

    source: Mapped[str] = mapped_column(String(60), default="manual")     # passport / provider / manual
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)

    last_changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    def serialize(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "field_key": self.field_key,
            "label": field_label(self.field_key),
            "source_label": provenance_label(self.source, self.verified, self.confidence),
            "category": self.category,
            "value": self.value,
            "source": self.source,
            "verified": self.verified,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "confidence": self.confidence,
            "last_changed_at": self.last_changed_at.isoformat() if self.last_changed_at else None,
        }


class RequirementDefinition(db.Model):
    """What is required, for whom. Data-driven (seeded, org-overridable)."""
    __tablename__ = "requirement_definition"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)          # DATA / DOCUMENT

    applies_customer_type: Mapped[str] = mapped_column(String(20), default="ANY")  # INDIVIDUAL / COMPANY / ANY
    # Comma-separated company legal forms this applies to (PRIVATELY_HELD,
    # PARTNERSHIP, LISTED). NULL/empty = every form of the customer type — so a
    # listed company, absent from the UBO-heavy rows, gets a lighter (SDD) list.
    applies_legal_form: Mapped[str] = mapped_column(String(120), nullable=True)
    min_risk_rank: Mapped[int] = mapped_column(Integer, default=0)         # required at this risk and above
    jurisdiction: Mapped[str] = mapped_column(String(80), nullable=True)   # NULL = any

    data_field: Mapped[str] = mapped_column(String(60), nullable=True)     # ProfileField.field_key for DATA
    doc_type: Mapped[str] = mapped_column(String(60), nullable=True)       # Document.doc_type for DOCUMENT
    # Required once PER related party (a passport for each UBO/SMO/signatory)
    # rather than once for the customer. Expanded per party by the engine.
    per_party: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    def serialize(self):
        return {
            "id": self.id, "code": self.code, "label": self.label,
            "kind": self.kind, "applies_customer_type": self.applies_customer_type,
            "applies_legal_form": self.applies_legal_form,
            "min_risk_rank": self.min_risk_rank, "jurisdiction": self.jurisdiction,
            "data_field": self.data_field, "doc_type": self.doc_type,
            "per_party": self.per_party, "active": self.active,
        }


class RequirementInstance(db.Model):
    """A requirement as it applies to one customer, with its current status."""
    __tablename__ = "requirement_instance"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), nullable=False)
    definition_id: Mapped[int] = mapped_column(ForeignKey("requirement_definition.id"), nullable=True)
    # Set when this instance is one party's copy of a per-party requirement.
    party_id: Mapped[int] = mapped_column(ForeignKey("party.id"), nullable=True)

    code: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="MISSING")

    waived_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=True)
    waived_reason: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    def serialize(self):
        return {
            "id": self.id, "customer_id": self.customer_id,
            "definition_id": self.definition_id, "party_id": self.party_id,
            "code": self.code, "label": self.label, "kind": self.kind,
            "status": self.status, "waived_reason": self.waived_reason,
        }
