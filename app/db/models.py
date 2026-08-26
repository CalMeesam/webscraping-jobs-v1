"""SQLAlchemy ORM models for extraction persistence."""

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class ExtractionRun(Base):
    """Represents a single job extraction execution for a customer."""

    __tablename__ = "extraction_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    career_link_url: Mapped[str] = mapped_column(Text, nullable=False)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True, nullable=False
    )
    jobs_found_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_returned_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="success")
    strategy_used: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Linked job snapshots
    snapshots: Mapped[list["JobSnapshot"]] = relationship(
        "JobSnapshot",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="JobSnapshot.id",
    )

    def to_dict(self) -> dict:
        """Convert run record to dictionary format with explicit UTC timezone suffix."""
        run_at_str = None
        if self.run_at:
            dt = self.run_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            iso = dt.isoformat()
            run_at_str = iso if ("+" in iso or iso.endswith("Z")) else iso + "Z"

        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "career_link_url": self.career_link_url,
            "run_at": run_at_str,
            "jobs_found_count": self.jobs_found_count,
            "jobs_returned_count": self.jobs_returned_count,
            "status": self.status,
            "strategy_used": self.strategy_used,
        }


class JobSnapshot(Base):
    """Represents a snapshot of an individual job extracted during a run."""

    __tablename__ = "job_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("extraction_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_identity_key: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    location_raw: Mapped[str | None] = mapped_column(String(512), nullable=True)
    job_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Parent extraction run
    run: Mapped["ExtractionRun"] = relationship("ExtractionRun", back_populates="snapshots")

    def to_dict(self) -> dict:
        """Convert snapshot record to dictionary format."""
        return {
            "id": self.id,
            "run_id": self.run_id,
            "job_identity_key": self.job_identity_key,
            "title": self.title,
            "location_raw": self.location_raw,
            "job_url": self.job_url,
        }
