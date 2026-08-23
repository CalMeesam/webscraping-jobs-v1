"""Tests for Job Candidate Validator."""

from app.validation.candidate_validator import is_valid_job_candidate


def test_validator_rejects_social_domains():
    assert not is_valid_job_candidate("Facebook", "https://www.facebook.com/ExlService/")
    assert not is_valid_job_candidate("LinkedIn", "https://www.linkedin.com/company/exl-service")
    assert not is_valid_job_candidate("Twitter", "https://twitter.com/exl_service")
    assert not is_valid_job_candidate("YouTube", "https://www.youtube.com/user/EXL")


def test_validator_rejects_chrome_and_policy_titles():
    assert not is_valid_job_candidate("Home", "https://www.exlservice.com/")
    assert not is_valid_job_candidate("About Us", "https://www.exlservice.com/about-exl")
    assert not is_valid_job_candidate("Privacy Policy", "https://example.com/privacy")
    assert not is_valid_job_candidate("Terms of Use", "https://example.com/terms")


def test_validator_rejects_external_unrelated_domains():
    src = "https://fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2/jobs"
    assert not is_valid_job_candidate("Corporate Site", "https://www.exlservice.com/about-exl", source_url=src)


def test_validator_accepts_valid_job_postings():
    src = "https://fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2/jobs"
    valid_url = "https://fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2/job/6502"
    assert is_valid_job_candidate("Senior Manager-Data Science", valid_url, source_url=src)
