"""Unit tests for JobDescriptionParser module."""

from app.parsing.job_description_parser import JobDescriptionParser


def test_parser_extracts_html_sections():
    parser = JobDescriptionParser()
    html_content = """
    <div>
        <h2>Responsibilities</h2>
        <ul>
            <li>Build scalable backend microservices using Python and FastAPI</li>
            <li>Design distributed systems and database schemas</li>
        </ul>
        <h2>Requirements</h2>
        <ul>
            <li>Bachelor's degree in Computer Science or related field</li>
            <li>3+ years of experience in backend development</li>
        </ul>
        <h2>Preferred Qualifications</h2>
        <ul>
            <li>Experience with cloud platforms like AWS</li>
            <li>Familiarity with Kubernetes and Docker</li>
        </ul>
        <h2>Benefits</h2>
        <ul>
            <li>Flexible PTO and remote work environment</li>
            <li>Health, dental, and vision insurance</li>
        </ul>
    </div>
    """

    res = parser.parse(html_content)
    assert len(res["responsibilities"]) == 2
    assert "Build scalable backend microservices" in res["responsibilities"][0]
    assert len(res["requirements"]) == 2
    assert "Bachelor's degree" in res["requirements"][0]
    assert len(res["preferred_qualifications"]) == 2
    assert "AWS" in res["preferred_qualifications"][0]
    assert len(res["benefits"]) == 2
    assert "Flexible PTO" in res["benefits"][0]


def test_parser_plain_text_fallback():
    parser = JobDescriptionParser()
    text_content = """
    Key Responsibilities:
    - Develop high throughput APIs
    - Maintain CI/CD pipelines

    Required Qualifications:
    - 5+ years of software engineering experience
    - Strong proficiency in SQL and PostgreSQL

    What We Offer:
    - Competitive salary and stock options
    """

    res = parser.parse(None, text_content)
    assert len(res["responsibilities"]) == 2
    assert "Develop high throughput APIs" in res["responsibilities"][0]
    assert len(res["requirements"]) == 2
    assert "5+ years of software engineering" in res["requirements"][0]
    assert len(res["benefits"]) == 1
    assert "Competitive salary" in res["benefits"][0]
