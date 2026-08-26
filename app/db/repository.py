"""Data access repository for extraction persistence and diff calculations."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from sqlalchemy import select
from app.core.logging import get_logger
from app.db.database import get_db_session, init_db
from app.db.models import ExtractionRun, JobSnapshot
from app.models.normalized_job import NormalizedJob
from app.utils.identity_utils import compute_job_identity_key

logger = get_logger(__name__)


def format_iso_utc(dt: datetime | None) -> str | None:
    """Format datetime into explicit ISO 8601 string with UTC indicator."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    iso = dt.isoformat()
    return iso if ("+" in iso or iso.endswith("Z")) else iso + "Z"


def save_extraction_run(
    customer_id: str,
    career_link_url: str,
    status: str,
    strategy_used: str | None,
    jobs_found_count: int,
    jobs_returned_count: int,
    jobs: list[NormalizedJob],
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Persist an extraction run and its job snapshots."""
    init_db(db_path)

    with get_db_session(db_path) as session:
        run = ExtractionRun(
            customer_id=customer_id,
            career_link_url=career_link_url,
            status=status,
            strategy_used=strategy_used,
            jobs_found_count=jobs_found_count,
            jobs_returned_count=jobs_returned_count,
        )
        session.add(run)
        session.flush()

        snapshots = []
        for job in jobs:
            identity_key = compute_job_identity_key(job)

            loc_raw = None
            if job.location:
                if hasattr(job.location, "raw"):
                    loc_raw = job.location.raw
                elif isinstance(job.location, dict):
                    loc_raw = job.location.get("raw") or str(job.location)
                else:
                    loc_raw = str(job.location)

            raw_json_str = None
            try:
                if hasattr(job, "model_dump_json"):
                    raw_json_str = job.model_dump_json()
                else:
                    raw_json_str = json.dumps(job)
            except Exception as e:
                logger.warning(f"Failed to serialize job for raw_json: {e}")

            snapshot = JobSnapshot(
                run_id=run.id,
                job_identity_key=identity_key,
                title=job.title,
                location_raw=loc_raw,
                job_url=job.job_url,
                raw_json=raw_json_str,
            )
            snapshots.append(snapshot)

        session.add_all(snapshots)
        session.commit()

        run_dict = run.to_dict()
        logger.info(
            f"Persisted extraction run id={run.id} for customer='{customer_id}' "
            f"with {len(snapshots)} job snapshots"
        )
        return run_dict


def compute_customer_diff(
    customer_id: str,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Compare the two most recent extraction runs for a customer_id."""
    init_db(db_path)

    with get_db_session(db_path) as session:
        stmt = (
            select(ExtractionRun)
            .where(ExtractionRun.customer_id == customer_id)
            .order_by(ExtractionRun.run_at.desc(), ExtractionRun.id.desc())
            .limit(2)
        )
        runs = session.scalars(stmt).all()

        if len(runs) < 2:
            latest_run = runs[0] if len(runs) == 1 else None
            return {
                "has_previous_run": False,
                "latest_run_id": latest_run.id if latest_run else None,
                "previous_run_id": None,
                "latest_run_at": format_iso_utc(latest_run.run_at) if latest_run else None,
                "previous_run_at": None,
                "new_jobs_count": 0,
                "removed_jobs_count": 0,
                "unchanged_jobs_count": 0,
                "new_job_keys": [],
                "removed_job_keys": [],
                "unchanged_job_keys": [],
                "message": "Baseline run, no comparison available",
            }

        latest_run, previous_run = runs[0], runs[1]

        latest_keys_stmt = select(JobSnapshot.job_identity_key).where(
            JobSnapshot.run_id == latest_run.id
        )
        latest_keys = set(session.scalars(latest_keys_stmt).all())

        prev_keys_stmt = select(JobSnapshot.job_identity_key).where(
            JobSnapshot.run_id == previous_run.id
        )
        prev_keys = set(session.scalars(prev_keys_stmt).all())

        new_keys = sorted(list(latest_keys - prev_keys))
        removed_keys = sorted(list(prev_keys - latest_keys))
        unchanged_keys = sorted(list(latest_keys & prev_keys))

        prev_iso = format_iso_utc(previous_run.run_at)

        return {
            "has_previous_run": True,
            "latest_run_id": latest_run.id,
            "previous_run_id": previous_run.id,
            "latest_run_at": format_iso_utc(latest_run.run_at),
            "previous_run_at": prev_iso,
            "new_jobs_count": len(new_keys),
            "removed_jobs_count": len(removed_keys),
            "unchanged_jobs_count": len(unchanged_keys),
            "new_job_keys": new_keys,
            "removed_job_keys": removed_keys,
            "unchanged_job_keys": unchanged_keys,
            "message": f"{len(new_keys)} new jobs, {len(removed_keys)} removed since last check on {prev_iso}",
        }


def get_customer_history(
    customer_id: str,
    limit: int = 20,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Fetch run history and diff for a customer."""
    init_db(db_path)

    with get_db_session(db_path) as session:
        stmt = (
            select(ExtractionRun)
            .where(ExtractionRun.customer_id == customer_id)
            .order_by(ExtractionRun.run_at.desc(), ExtractionRun.id.desc())
            .limit(limit)
        )
        runs = session.scalars(stmt).all()
        runs_list = [run.to_dict() for run in runs]

    diff_summary = compute_customer_diff(customer_id, db_path=db_path)

    return {
        "customer_id": customer_id,
        "total_runs": len(runs_list),
        "runs": runs_list,
        "diff_summary": diff_summary,
    }
