"""Unit tests for ATS Detector and Source Classifier."""

from app.discovery.ats_detector import ATSDetector
from app.discovery.source_classifier import SourceClassifier


def test_ats_detector_domain_patterns():
    detector = ATSDetector()

    ats, conf = detector.detect("https://boards.greenhouse.io/figma")
    assert ats == "greenhouse"
    assert conf == 1.0

    ats, conf = detector.detect("https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite")
    assert ats == "workday"
    assert conf == 1.0

    ats, conf = detector.detect("https://jobs.lever.co/spotify")
    assert ats == "lever"
    assert conf == 1.0

    ats, conf = detector.detect("https://company.smartrecruiters.com")
    assert ats == "smartrecruiters"
    assert conf == 1.0

    ats, conf = detector.detect("https://company.ashbyhq.com")
    assert ats == "ashby"
    assert conf == 1.0


def test_source_classifier_unknown_threshold():
    classifier = SourceClassifier()

    classification = classifier.classify("https://genericcompany.com/about")
    assert classification.source_type == "unknown"
    assert classification.ats is None
    assert classification.confidence < 0.6
