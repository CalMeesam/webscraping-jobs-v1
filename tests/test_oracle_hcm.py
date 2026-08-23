"""Unit tests for Oracle Fusion HCM Extractor."""

import pytest
from app.extractors.ats.oracle_hcm import OracleHCMExtractor
from app.models.extraction_models import ExtractionContext


def test_oracle_hcm_url_parser():
    extractor = OracleHCMExtractor()

    dell_url = "https://enterpriseplatform.dell.com/hcmUI/CandidateExperience/en/sites/careers/jobs?mode=location"
    res = extractor.parse_oracle_hcm_url(dell_url)
    assert res is not None
    host, lang, site = res
    assert host == "enterpriseplatform.dell.com"
    assert lang == "en"
    assert site == "careers"

    exl_url = "https://fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2/jobs?location=India"
    res2 = extractor.parse_oracle_hcm_url(exl_url)
    assert res2 is not None
    host2, lang2, site2 = res2
    assert host2 == "fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com"
    assert lang2 == "en"
    assert site2 == "CX_2"
