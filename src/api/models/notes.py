"""Analyst notes on a customer file: one pinned analysis summary + a thread
of dated comments. Notes are working knowledge, not evidence — they never
change risk or completeness, and the audit trail records who wrote what."""
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from api.models.base import db, utcnow

NOTE_KINDS = ("COMMENT", "ANALYSIS_SUMMARY")


class CustomerNote(db.Model):
    __tablename__ = "customer_note"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False, default="COMMENT")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    def serialize(self, author_name=None):
        return {
            "id": self.id, "customer_id": self.customer_id, "author_id": self.author_id,
            "author_name": author_name, "kind": self.kind, "text": self.text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
