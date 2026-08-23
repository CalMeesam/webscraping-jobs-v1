"""Unit tests for SkillsExtractor module."""

from app.parsing.skills_extractor import SkillsExtractor


def test_skills_extraction_normalizes_aliases():
    extractor = SkillsExtractor()
    text = "We are seeking a Python3 developer proficient in JS, PostgreSQL, and Amazon Web Services (AWS)."
    requirements = ["Experience with Docker and k8s", "Strong understanding of RESTful APIs"]

    skills = extractor.extract_skills(text, [requirements])

    assert "Python" in skills
    assert "JavaScript" in skills
    assert "PostgreSQL" in skills
    assert "AWS" in skills
    assert "Docker" in skills
    assert "Kubernetes" in skills
    assert "REST API" in skills


def test_skills_word_boundary_prevents_false_positives():
    extractor = SkillsExtractor()
    # "category" should NOT match "Go", "Java" should NOT match "JavaScript"
    text = "Join our category team to work on Java microservices and JavaScript web applications."

    skills = extractor.extract_skills(text)

    assert "Java" in skills
    assert "JavaScript" in skills
    # Ensure false positives like 'Go' (inside category) are avoided
    assert "Go" not in skills
