"""PostgreSQL Database Inspector CLI
Run with: python -m scratch.view_postgres_data
"""

import sys
from sqlalchemy import select, func, desc
from app.db.database import get_db_session
from app.db.models import ExtractionRun, JobSnapshot

def main():
    print("=" * 75)
    print("           POSTGRESQL DATABASE INSPECTOR & VIEWER")
    print("=" * 75)

    with get_db_session() as session:
        # 1. Total statistics
        total_runs = session.scalar(select(func.count(ExtractionRun.id))) or 0
        total_snapshots = session.scalar(select(func.count(JobSnapshot.id))) or 0
        
        print(f"\n[*] DATABASE SUMMARY:")
        print(f"    - Total Extraction Runs : {total_runs}")
        print(f"    - Total Job Snapshots   : {total_snapshots}")

        # 2. Runs grouped by customer
        print("\n[*] RUNS PARTITIONED BY CUSTOMER:")
        customer_counts = session.execute(
            select(ExtractionRun.customer_id, func.count(ExtractionRun.id))
            .group_by(ExtractionRun.customer_id)
            .order_by(desc(func.count(ExtractionRun.id)))
        ).all()

        for cust_id, count in customer_counts:
            print(f"    - Customer '{cust_id}': {count} runs")

        # 3. Latest 10 Extraction Runs
        print("\n[*] RECENT EXTRACTION RUNS:")
        print(f"  {'ID':<5} {'Customer':<12} {'Run At (UTC)':<24} {'Status':<10} {'Jobs Ret/Found'}")
        print("  " + "-" * 68)
        
        recent_runs = session.scalars(
            select(ExtractionRun).order_by(ExtractionRun.id.desc()).limit(10)
        ).all()

        for r in recent_runs:
            print(f"  #{r.id:<4} {r.customer_id:<12} {str(r.run_at)[:22]:<24} {r.status.upper():<10} {r.jobs_returned_count}/{r.jobs_found_count}")

        # 4. Sample Job Snapshots from the latest run
        if recent_runs:
            latest = recent_runs[0]
            print(f"\n[*] SAMPLE SNAPSHOTS FROM LATEST RUN #{latest.id} ({latest.customer_id.upper()}):")
            snaps = session.scalars(
                select(JobSnapshot).where(JobSnapshot.run_id == latest.id).limit(5)
            ).all()

            for s in snaps:
                title = (s.title[:45] + '...') if len(s.title) > 48 else s.title
                loc = (s.location_raw[:25] + '...') if s.location_raw and len(s.location_raw) > 28 else (s.location_raw or 'N/A')
                print(f"    [Snap #{s.id}] {title:<48} | {loc:<28} | Key: {s.job_identity_key[:30]}")

    print("\n" + "=" * 75)

if __name__ == "__main__":
    main()
