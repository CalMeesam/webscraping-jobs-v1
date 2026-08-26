"""CSV export utilities for job data."""

import csv
from io import StringIO
from typing import List

from app.models.normalized_job import NormalizedJob, JobLocation


class JobCSVExporter:
    """Exports NormalizedJob records to CSV format."""
    
    # Define column order for CSV
    CSV_COLUMNS = [
        "id",
        "external_job_id",
        "requisition_id",
        "title",
        "location_raw",
        "location_city",
        "location_state",
        "location_country",
        "department",
        "employment_type",
        "workplace_type",
        "experience_level",
        "description",
        "responsibilities",
        "requirements",
        "preferred_qualifications",
        "benefits",
        "skills",
        "job_url",
        "application_url",
        "posted_at",
        "source",
        "ats"
    ]
    
    @staticmethod
    def flatten_job(job: NormalizedJob) -> dict:
        """Flatten a NormalizedJob into a flat dictionary for CSV export."""
        
        # Handle location (can be JobLocation object or string)
        if isinstance(job.location, JobLocation):
            location_raw = job.location.raw
            location_city = job.location.city
            location_state = job.location.state
            location_country = job.location.country
        elif isinstance(job.location, str):
            location_raw = job.location
            location_city = None
            location_state = None
            location_country = None
        else:
            location_raw = None
            location_city = None
            location_state = None
            location_country = None
        
        # Join list fields with semicolons
        responsibilities = "; ".join(job.responsibilities) if job.responsibilities else ""
        requirements = "; ".join(job.requirements) if job.requirements else ""
        preferred_qualifications = "; ".join(job.preferred_qualifications) if job.preferred_qualifications else ""
        benefits = "; ".join(job.benefits) if job.benefits else ""
        skills = "; ".join(job.skills) if job.skills else ""
        
        return {
            "id": job.id or "",
            "external_job_id": job.external_job_id or "",
            "requisition_id": job.requisition_id or "",
            "title": job.title or "",
            "location_raw": location_raw or "",
            "location_city": location_city or "",
            "location_state": location_state or "",
            "location_country": location_country or "",
            "department": job.department or "",
            "employment_type": job.employment_type or "",
            "workplace_type": job.workplace_type or "",
            "experience_level": job.experience_level or "",
            "description": job.description or "",
            "responsibilities": responsibilities,
            "requirements": requirements,
            "preferred_qualifications": preferred_qualifications,
            "benefits": benefits,
            "skills": skills,
            "job_url": job.job_url or "",
            "application_url": job.application_url or "",
            "posted_at": job.posted_at or "",
            "source": job.source or "",
            "ats": job.ats or ""
        }
    
    @classmethod
    def export_to_csv(cls, jobs: List[NormalizedJob]) -> str:
        """Export a list of jobs to CSV string.
        
        Args:
            jobs: List of NormalizedJob objects
            
        Returns:
            CSV string with all jobs
        """
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=cls.CSV_COLUMNS)
        
        # Write header
        writer.writeheader()
        
        # Write data rows
        for job in jobs:
            flattened = cls.flatten_job(job)
            writer.writerow(flattened)
        
        return output.getvalue()
