"""Tests for CSV export functionality."""

import pytest
from app.models.normalized_job import NormalizedJob, JobLocation
from app.utils.csv_exporter import JobCSVExporter


class TestCSVExporter:
    """Test CSV export utilities."""
    
    def test_flatten_job_with_location_object(self):
        """Test flattening a job with JobLocation object."""
        job = NormalizedJob(
            id="123",
            title="Software Engineer",
            location=JobLocation(
                raw="San Francisco, CA, USA",
                city="San Francisco",
                state="CA",
                country="USA"
            ),
            department="Engineering",
            employment_type="Full-time",
            description="Great job",
            responsibilities=["Code", "Review"],
            requirements=["Python", "FastAPI"],
            skills=["API", "Testing"],
            job_url="https://example.com/job/123",
            source="example",
            ats="greenhouse"
        )
        
        flattened = JobCSVExporter.flatten_job(job)
        
        assert flattened["id"] == "123"
        assert flattened["title"] == "Software Engineer"
        assert flattened["location_raw"] == "San Francisco, CA, USA"
        assert flattened["location_city"] == "San Francisco"
        assert flattened["location_state"] == "CA"
        assert flattened["location_country"] == "USA"
        assert flattened["department"] == "Engineering"
        assert flattened["responsibilities"] == "Code; Review"
        assert flattened["requirements"] == "Python; FastAPI"
        assert flattened["skills"] == "API; Testing"
    
    def test_flatten_job_with_string_location(self):
        """Test flattening a job with string location."""
        job = NormalizedJob(
            title="Designer",
            location="Remote",
            source="test"
        )
        
        flattened = JobCSVExporter.flatten_job(job)
        
        assert flattened["location_raw"] == "Remote"
        assert flattened["location_city"] == ""
        assert flattened["location_state"] == ""
        assert flattened["location_country"] == ""
    
    def test_flatten_job_with_empty_lists(self):
        """Test flattening a job with empty list fields."""
        job = NormalizedJob(
            title="Manager",
            responsibilities=[],
            requirements=[],
            skills=[],
            source="test"
        )
        
        flattened = JobCSVExporter.flatten_job(job)
        
        assert flattened["responsibilities"] == ""
        assert flattened["requirements"] == ""
        assert flattened["skills"] == ""
    
    def test_export_to_csv(self):
        """Test exporting multiple jobs to CSV."""
        jobs = [
            NormalizedJob(
                id="1",
                title="Engineer",
                location=JobLocation(raw="NYC", city="New York", state="NY", country="USA"),
                source="company1",
                ats="greenhouse"
            ),
            NormalizedJob(
                id="2",
                title="Designer",
                location="London, UK",
                source="company2",
                ats="lever"
            )
        ]
        
        csv_output = JobCSVExporter.export_to_csv(jobs)
        
        # Check CSV structure
        lines = csv_output.strip().split("\n")
        assert len(lines) == 3  # Header + 2 data rows
        
        # Check header
        header = lines[0]
        assert "id" in header
        assert "title" in header
        assert "location_city" in header
        assert "location_state" in header
        assert "location_country" in header
        assert "source" in header
        assert "ats" in header
        
        # Check first data row
        assert "1" in lines[1]
        assert "Engineer" in lines[1]
        assert "New York" in lines[1]
        
        # Check second data row
        assert "2" in lines[2]
        assert "Designer" in lines[2]
        assert "London, UK" in lines[2]
    
    def test_export_empty_jobs_list(self):
        """Test exporting empty job list."""
        csv_output = JobCSVExporter.export_to_csv([])
        
        # Should still have header
        lines = csv_output.strip().split("\n")
        assert len(lines) == 1  # Just header
        assert "id,external_job_id,requisition_id,title" in lines[0]
