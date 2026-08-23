"""Job Description Section Parser module.

Performs deterministic, rule-based parsing of unstructured job descriptions (HTML or plain text)
into structured sections (responsibilities, requirements, preferred_qualifications, benefits).
"""

import html
import re
from bs4 import BeautifulSoup
from app.core.logging import get_logger
from app.utils.html_utils import strip_html_tags

logger = get_logger(__name__)

# Stop condition patterns for legal disclaimers, EEOC notices, pay disclosures, culture/values blurbs, etc.
BOILERPLATE_PATTERNS = [
    r"\bequal opportunity\b",
    r"\beeoc\b",
    r"\baccommodations?\b",
    r"\bpay transparency\b",
    r"\bprivacy notice\b",
    r"\bcandidate privacy\b",
    r"\bcriminal histories\b",
    r"\bdisability\b",
    r"\bonboarding\b",
    r"\bsalary range\b",
    r"\blegal requirements\b",
    r"\baffirmative action\b",
    r"\bbackground check\b",
    r"\bgrow as you go\b",
    r"\bone of our values\b",
    r"\b#li-\b",
]

# Section patterns (preferred_qualifications evaluated before requirements to avoid 'qualifications' ambiguity)
SECTION_PATTERNS = {
    "preferred_qualifications": [
        r"\bpreferred qualifications\b",
        r"\bpreferred skills\b",
        r"\bnice to have\b",
        r"\bgood to have\b",
        r"\bbonus points\b",
        r"\bdesirable skills\b",
        r"\bpreferred experience\b",
        r"\badded plus\b",
        r"\bit(?:['’\u2019]s| is) an added plus\b",
        r"\bways to stand out from the crowd\b",
        r"\bhow to stand out\b",
        r"\bwhile it(?:['’\u2019]s| is) not required\b",
    ],
    "responsibilities": [
        r"\bresponsibilities\b",
        r"\bwhat you(?:['’\u2019]ll| will) do\b",
        r"\bwhat you(?:['’\u2019]ll| will) do at\b",
        r"\bwhat you(?:['’\u2019]ll| will) be doing\b",
        r"\bkey responsibilities\b",
        r"\byour role\b",
        r"\bthe role\b",
        r"\bduties\b",
        r"\bday-to-day\b",
        r"\bwhat you do\b",
        r"\brole responsibilities\b",
    ],
    "requirements": [
        r"\brequirements\b",
        r"\bminimum qualifications\b",
        r"\brequired qualifications\b",
        r"\bbasic qualifications\b",
        r"\bwhat we(?:['’\u2019]re| are) looking for\b",
        r"\bwe(?:['’\u2019]d| would) love to hear from you\b",
        r"\bwhat we need to see\b",
        r"\bwhat you bring\b",
        r"\bskills and experience\b",
        r"\bwho you are\b",
        r"\bqualifications\b",
    ],
    "benefits": [
        r"\bbenefits\b",
        r"\bperks\b",
        r"\bwhat we offer\b",
        r"\bwhy join us\b",
        r"\babout company\b",
        r"\babout us\b",
        r"\babout the company\b",
        r"\bwho we are\b",
    ],
}


class JobDescriptionParser:
    """Parses unstructured HTML or text job descriptions into structured section lists."""

    def __init__(self):
        self.compiled_sections = {
            section: [re.compile(p, re.IGNORECASE) for p in patterns]
            for section, patterns in SECTION_PATTERNS.items()
        }
        self.compiled_boilerplate = [re.compile(p, re.IGNORECASE) for p in BOILERPLATE_PATTERNS]

    def _is_boilerplate(self, text: str) -> bool:
        """Returns True if text matches legal disclaimers, EEOC, accommodations, or pay disclosures."""
        return any(p.search(text) for p in self.compiled_boilerplate)

    def _match_section(self, text: str) -> str | None:
        """Determines if a header text matches any known section pattern."""
        text_clean = text.strip()
        if not text_clean or len(text_clean) > 100:
            return None

        # Do not match headers that are legal disclaimers
        if self._is_boilerplate(text_clean):
            return None

        for section, regexes in self.compiled_sections.items():
            for regex in regexes:
                if regex.search(text_clean):
                    return section
        return None

    def parse(self, html_content: str | None, text_content: str | None = None) -> dict[str, list[str]]:
        """
        Parses description into structured sections.
        Returns dict with keys: responsibilities, requirements, preferred_qualifications, benefits.
        """
        results: dict[str, list[str]] = {
            "responsibilities": [],
            "requirements": [],
            "preferred_qualifications": [],
            "benefits": [],
        }

        # HTML parsing path (operated strictly via DOM tags, never string character slicing)
        if html_content:
            try:
                clean_html = html_content
                for _ in range(3):
                    nxt = html.unescape(clean_html)
                    if nxt == clean_html:
                        break
                    clean_html = nxt
                self._parse_html(clean_html, results)
                return results
            except Exception as e:
                logger.warning(f"Error parsing HTML description: {e}")

        # Plain text parsing path (operated on clean plain text strings)
        if text_content:
            self._parse_text(text_content, results)

        return results

    def _parse_html(self, html_content: str, results: dict[str, list[str]]) -> None:
        soup = BeautifulSoup(html_content, "html.parser")
        tags = soup.find_all(["h1", "h2", "h3", "h4", "h5", "strong", "b", "p", "ul", "ol"])
        current_sec: str | None = None

        for tag in tags:
            text = tag.get_text(strip=True)
            if not text:
                continue

            # Stop condition 1: explicit legal/compliance disclaimer or values block
            if self._is_boilerplate(text):
                current_sec = None
                continue

            # Check if element is a section heading
            sec = self._match_section(text)
            if sec:
                current_sec = sec
                continue

            if current_sec:
                if tag.name in ("ul", "ol"):
                    for li in tag.find_all("li", recursive=False):
                        li_text = li.get_text(strip=True)
                        if li_text and not self._is_boilerplate(li_text) and li_text not in results[current_sec]:
                            results[current_sec].append(li_text)
                elif tag.name in ("p", "strong", "b") and len(text) > 10 and not tag.find_parent(["ul", "ol"]):
                    if not self._is_boilerplate(text) and text not in results[current_sec]:
                        results[current_sec].append(text)

    def _parse_text(self, text: str, results: dict[str, list[str]]) -> None:
        matches = []
        for sec, regexes in self.compiled_sections.items():
            for r in regexes:
                for m in r.finditer(text):
                    matches.append((m.start(), m.end(), sec, m.group(0)))

        if not matches:
            return

        matches.sort(key=lambda x: x[0])

        # Filter overlapping matches
        filtered_matches = []
        last_end = -1
        for m in matches:
            if m[0] >= last_end:
                filtered_matches.append(m)
                last_end = m[1]

        for i, m in enumerate(filtered_matches):
            start_idx = m[1]
            end_idx = filtered_matches[i + 1][0] if i + 1 < len(filtered_matches) else len(text)
            block = text[start_idx:end_idx].strip()
            block = re.sub(r"^\s*[:\-]\s*", "", block)

            raw_items = re.split(r"\n+|(?:(?<=[a-z0-9\)])\.\s+(?=[A-Z0-9]))", block)
            for item in raw_items:
                clean_item = re.sub(r"^[\-*•\d+\.]+\s*", "", item).strip()
                # Stop if item reaches legal disclaimers
                if self._is_boilerplate(clean_item):
                    break
                if clean_item and len(clean_item) > 5 and clean_item not in results[m[2]]:
                    results[m[2]].append(clean_item)
