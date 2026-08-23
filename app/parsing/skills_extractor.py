"""Deterministic Skills Extractor module.

Identifies technical skills, tools, and frameworks from job descriptions and requirements using
word-boundary taxonomy matching.
"""

import re
from app.core.logging import get_logger

logger = get_logger(__name__)

# Skill Taxonomy mapping Canonical Skill Name -> list of regex patterns
SKILL_TAXONOMY: dict[str, list[str]] = {
    "Python": [r"\bpython3?\b", r"\bpy\b"],
    "Java": [r"\bjava\b"],  # Won't match JavaScript due to word boundary
    "C++": [r"\bc\+\+\b", r"\bcpp\b"],
    "C#": [r"\bc#\b", r"\b\.net\b", r"\bdotnet\b"],
    "JavaScript": [r"\bjavascript\b", r"\bjs\b", r"\becmascript\b"],
    "TypeScript": [r"\btypescript\b", r"\bts\b"],
    "Go": [r"\bgolang\b", r"\bgo\s+(?:developer|engineer|programming|code)\b"],
    "Rust": [r"\brust\b"],
    "Ruby": [r"\bruby\b", r"\bruby on rails\b", r"\brails\b"],
    "PHP": [r"\bphp\b", r"\blaravel\b"],
    "React": [r"\breact(?:js)?\b", r"\breact native\b"],
    "Angular": [r"\bangular(?:js)?\b"],
    "Vue": [r"\bvue(?:js)?\b"],
    "Next.js": [r"\bnext\.?js\b"],
    "Node.js": [r"\bnode\.?js\b", r"\bexpress\.?js\b"],
    "FastAPI": [r"\bfastapi\b"],
    "Django": [r"\bdjango\b"],
    "Flask": [r"\bflask\b"],
    "Spring": [r"\bspring\s*boot\b", r"\bspring\s*framework\b"],
    "PostgreSQL": [r"\bpostgresql\b", r"\bpostgres\b"],
    "MySQL": [r"\bmysql\b"],
    "MongoDB": [r"\bmongodb\b", r"\bmongo\b"],
    "Redis": [r"\bredis\b"],
    "SQL": [r"\bsql\b", r"\bno\s*sql\b"],
    "AWS": [r"\baws\b", r"\bamazon web services\b"],
    "Azure": [r"\bazure\b"],
    "GCP": [r"\bgcp\b", r"\bgoogle cloud\b"],
    "Docker": [r"\bdocker\b"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "Terraform": [r"\bterraform\b"],
    "Git": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"],
    "Linux": [r"\blinux\b", r"\bunix\b", r"\bbash\b"],
    "REST API": [r"\brest(?:ful)?\s*apis?\b"],
    "GraphQL": [r"\bgraphql\b"],
    "TensorFlow": [r"\btensorflow\b", r"\btf\b"],
    "PyTorch": [r"\bpytorch\b"],
    "Machine Learning": [r"\bmachine learning\b", r"\bml\b"],
    "Deep Learning": [r"\bdeep learning\b"],
    "Data Science": [r"\bdata science\b"],
}


class SkillsExtractor:
    """Extracts normalized technical skills from job text using regex taxonomy matching."""

    def __init__(self):
        self.compiled_taxonomy: dict[str, list[re.Pattern]] = {
            skill: [re.compile(p, re.IGNORECASE) for p in patterns]
            for skill, patterns in SKILL_TAXONOMY.items()
        }

    def extract_skills(self, text: str | None, section_lists: list[list[str]] | None = None) -> list[str]:
        """
        Extracts deduplicated normalized skills from text content and section item lists.
        """
        combined_text_parts = []
        if text:
            combined_text_parts.append(text)

        if section_lists:
            for section in section_lists:
                if section:
                    combined_text_parts.extend(section)

        full_text = " ".join(combined_text_parts)
        if not full_text:
            return []

        extracted: set[str] = set()

        for canonical_skill, regexes in self.compiled_taxonomy.items():
            for regex in regexes:
                if regex.search(full_text):
                    extracted.add(canonical_skill)
                    break

        return sorted(list(extracted))
