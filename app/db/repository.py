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

            raw_json_data = None
            try:
                if hasattr(job, "model_dump"):
                    raw_json_data = job.model_dump()
                elif hasattr(job, "dict"):
                    raw_json_data = job.dict()
                else:
                    raw_json_data = json.loads(json.dumps(job))
            except Exception as e:
                logger.warning(f"Failed to serialize job for raw_json: {e}")

            snapshot = JobSnapshot(
                run_id=run.id,
                job_identity_key=identity_key,
                title=job.title,
                location_raw=loc_raw,
                job_url=job.job_url,
                raw_json=raw_json_data,
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


def extract_snapshot_job_dict(snapshot: JobSnapshot) -> dict[str, Any]:
    """Helper to get a full dictionary representation of a snapshot."""
    raw = snapshot.raw_json if isinstance(snapshot.raw_json, dict) else {}
    
    loc_val = snapshot.location_raw
    if not loc_val and isinstance(raw.get("location"), dict):
        loc_val = raw.get("location", {}).get("raw") or ""
    elif not loc_val:
        loc_val = str(raw.get("location") or "")

    return {
        "id": snapshot.id,
        "job_identity_key": snapshot.job_identity_key,
        "title": snapshot.title or raw.get("title") or "",
        "location": loc_val or "",
        "department": raw.get("department") or "",
        "employment_type": raw.get("employment_type") or "",
        "workplace_type": raw.get("workplace_type") or "",
        "experience_level": raw.get("experience_level") or "",
        "description": raw.get("description") or "",
        "responsibilities": raw.get("responsibilities") or [],
        "requirements": raw.get("requirements") or [],
        "preferred_qualifications": raw.get("preferred_qualifications") or [],
        "benefits": raw.get("benefits") or [],
        "skills": raw.get("skills") or [],
        "job_url": snapshot.job_url or raw.get("job_url") or "",
        "application_url": raw.get("application_url") or "",
        "posted_at": raw.get("posted_at") or "",
        "source": raw.get("source") or "",
        "ats": raw.get("ats") or "",
    }


def compute_field_diffs(base_job: dict[str, Any], target_job: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare fields between base job and target job to find what changed."""
    changes = []

    scalar_fields = [
        ("title", "Job Title"),
        ("location", "Location"),
        ("department", "Department"),
        ("employment_type", "Employment Type"),
        ("workplace_type", "Workplace Type"),
        ("experience_level", "Experience Level"),
        ("job_url", "Job URL"),
        ("application_url", "Application URL"),
        ("posted_at", "Posted Date"),
        ("description", "Description"),
    ]

    for field_key, field_label in scalar_fields:
        old_v = str(base_job.get(field_key) or "").strip()
        new_v = str(target_job.get(field_key) or "").strip()
        if old_v != new_v:
            changes.append({
                "field": field_key,
                "label": field_label,
                "old_value": old_v,
                "new_value": new_v,
            })

    list_fields = [
        ("skills", "Skills"),
        ("responsibilities", "Responsibilities"),
        ("requirements", "Requirements"),
        ("benefits", "Benefits"),
    ]

    for field_key, field_label in list_fields:
        old_list = [str(x).strip() for x in (base_job.get(field_key) or []) if str(x).strip()]
        new_list = [str(x).strip() for x in (target_job.get(field_key) or []) if str(x).strip()]
        if old_list != new_list:
            old_str = ", ".join(old_list)
            new_str = ", ".join(new_list)
            changes.append({
                "field": field_key,
                "label": field_label,
                "old_value": old_str,
                "new_value": new_str,
            })

    return changes


def compare_runs(
    base_run_id: int,
    target_run_id: int,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Compare two specific extraction runs (base_run vs target_run)."""
    init_db(db_path)

    with get_db_session(db_path) as session:
        base_run = session.scalar(select(ExtractionRun).where(ExtractionRun.id == base_run_id))
        target_run = session.scalar(select(ExtractionRun).where(ExtractionRun.id == target_run_id))

        if not base_run or not target_run:
            raise ValueError(f"Run not found (base_run_id={base_run_id}, target_run_id={target_run_id})")

        base_snapshots = session.scalars(select(JobSnapshot).where(JobSnapshot.run_id == base_run_id)).all()
        target_snapshots = session.scalars(select(JobSnapshot).where(JobSnapshot.run_id == target_run_id)).all()

        base_map = {s.job_identity_key: extract_snapshot_job_dict(s) for s in base_snapshots}
        target_map = {s.job_identity_key: extract_snapshot_job_dict(s) for s in target_snapshots}

        base_keys = set(base_map.keys())
        target_keys = set(target_map.keys())

        added_keys = sorted(list(target_keys - base_keys))
        removed_keys = sorted(list(base_keys - target_keys))
        common_keys = sorted(list(base_keys & target_keys))

        added_jobs = [target_map[k] for k in added_keys]
        removed_jobs = [base_map[k] for k in removed_keys]

        changed_jobs = []
        unchanged_jobs = []

        for k in common_keys:
            base_job = base_map[k]
            target_job = target_map[k]
            field_changes = compute_field_diffs(base_job, target_job)
            if field_changes:
                changed_jobs.append({
                    "job_identity_key": k,
                    "title": target_job.get("title") or base_job.get("title"),
                    "location": target_job.get("location") or base_job.get("location"),
                    "job_url": target_job.get("job_url") or base_job.get("job_url"),
                    "field_changes": field_changes,
                    "base_job": base_job,
                    "target_job": target_job,
                })
            else:
                unchanged_jobs.append({
                    "job_identity_key": k,
                    "title": target_job.get("title"),
                    "location": target_job.get("location"),
                    "job_url": target_job.get("job_url"),
                })

        return {
            "base_run": base_run.to_dict(),
            "target_run": target_run.to_dict(),
            "summary": {
                "added_count": len(added_jobs),
                "removed_count": len(removed_jobs),
                "changed_count": len(changed_jobs),
                "unchanged_count": len(unchanged_jobs),
                "total_base_jobs": len(base_snapshots),
                "total_target_jobs": len(target_snapshots),
            },
            "added_jobs": added_jobs,
            "removed_jobs": removed_jobs,
            "changed_jobs": changed_jobs,
            "unchanged_jobs": unchanged_jobs,
        }


def export_comparison_to_csv(comparison: dict[str, Any]) -> str:
    """Export run comparison results to CSV."""
    import csv
    from io import StringIO

    output = StringIO()
    columns = [
        "Change Type",
        "Job Identity Key",
        "Job Title",
        "Location",
        "Changed Field",
        "Previous Value",
        "Current Value",
        "Job URL",
        "Base Run Date",
        "Target Run Date",
    ]
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()

    base_run = comparison.get("base_run", {})
    target_run = comparison.get("target_run", {})
    base_date = base_run.get("run_at", "")
    target_date = target_run.get("run_at", "")

    # 1. Added Jobs
    for job in comparison.get("added_jobs", []):
        writer.writerow({
            "Change Type": "Added",
            "Job Identity Key": job.get("job_identity_key", ""),
            "Job Title": job.get("title", ""),
            "Location": job.get("location", ""),
            "Changed Field": "N/A (New Job)",
            "Previous Value": "",
            "Current Value": "Added in newer run",
            "Job URL": job.get("job_url", ""),
            "Base Run Date": base_date,
            "Target Run Date": target_date,
        })

    # 2. Removed Jobs
    for job in comparison.get("removed_jobs", []):
        writer.writerow({
            "Change Type": "Removed",
            "Job Identity Key": job.get("job_identity_key", ""),
            "Job Title": job.get("title", ""),
            "Location": job.get("location", ""),
            "Changed Field": "N/A (Removed Job)",
            "Previous Value": "Present in previous run",
            "Current Value": "",
            "Job URL": job.get("job_url", ""),
            "Base Run Date": base_date,
            "Target Run Date": target_date,
        })

    # 3. Changed Jobs (one row per changed field)
    for c_job in comparison.get("changed_jobs", []):
        for ch in c_job.get("field_changes", []):
            writer.writerow({
                "Change Type": "Changed",
                "Job Identity Key": c_job.get("job_identity_key", ""),
                "Job Title": c_job.get("title", ""),
                "Location": c_job.get("location", ""),
                "Changed Field": ch.get("label", ch.get("field", "")),
                "Previous Value": ch.get("old_value", ""),
                "Current Value": ch.get("new_value", ""),
                "Job URL": c_job.get("job_url", ""),
                "Base Run Date": base_date,
                "Target Run Date": target_date,
            })

    # 4. Unchanged Jobs
    for job in comparison.get("unchanged_jobs", []):
        writer.writerow({
            "Change Type": "Unchanged",
            "Job Identity Key": job.get("job_identity_key", ""),
            "Job Title": job.get("title", ""),
            "Location": job.get("location", ""),
            "Changed Field": "None",
            "Previous Value": "Identical",
            "Current Value": "Identical",
            "Job URL": job.get("job_url", ""),
            "Base Run Date": base_date,
            "Target Run Date": target_date,
        })

    return output.getvalue()

