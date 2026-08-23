import re
import json
from bs4 import BeautifulSoup

figma_html = """<div><p>Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all...</p><p>We are looking for an Enterprise Account Executive...</p><h4><strong>What you'll do at Figma:</strong></h4><ul><li>Create and manage a pipeline of Enterprise accounts to consistently meet or exceed quarterly and annual sales targets</li><li>Apply effective discovery and value-selling techniques to build and strengthen relationships</li></ul><h4><strong>We'd love to hear from you if you have:</strong></h4><ul><li>Experience closing sales, over multiple years, for a software or SaaS business</li><li>Consistent performance meeting pipeline generation targets</li></ul><h4><strong>While it’s not required, it’s an added plus if you also have:</strong></h4><ul><li>Experience selling solutions to technical audiences at a strategic level</li><li>Certified in deal qualification and prospect discovery</li></ul><div class="content-pay-transparency"><div class="pay-input"><div class="description"><p><strong>Pay Transparency Disclosure</strong></p><p>Job level and actual compensation will be decided based on factors...</p></div></div></div><div class="content-conclusion"><p>At Figma we celebrate and support our differences. Figma is an equal opportunity workplace...</p></div></div>"""

BOILERPLATE_PATTERNS = [
    r"\bequal opportunity\b",
    r"\beeoc\b",
    r"\baccommodations?\b",
    r"\bpay transparency\b",
    r"\bprivacy notice\b",
    r"\bcandidate privacy\b",
    r"\bcriminal histories\b",
    r"\bdisability\b",
    r"\bcameras on\b",
    r"\bonboarding\b",
    r"\bcompensation\b",
    r"\bsalary range\b",
    r"\blegal requirements\b",
]
compiled_bp = [re.compile(p, re.IGNORECASE) for p in BOILERPLATE_PATTERNS]

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

compiled_sec = {
    sec: [re.compile(p, re.IGNORECASE) for p in pats]
    for sec, pats in SECTION_PATTERNS.items()
}


def match_sec(text: str) -> str | None:
    if not text or len(text) > 100:
        return None
    for sec, regexes in compiled_sec.items():
        for r in regexes:
            if r.search(text):
                return sec
    return None


def parse_html_dom(html: str):
    soup = BeautifulSoup(html, "lxml")
    results = {
        "responsibilities": [],
        "requirements": [],
        "preferred_qualifications": [],
        "benefits": [],
    }

    tags = soup.find_all(["h1", "h2", "h3", "h4", "h5", "strong", "b", "p", "ul", "ol"])
    current_sec = None

    for tag in tags:
        text = tag.get_text(strip=True)
        if not text:
            continue

        # Stop condition: boilerplate header or disclaimer block
        if any(p.search(text) for p in compiled_bp):
            current_sec = None
            continue

        sec = match_sec(text)
        if sec:
            current_sec = sec
            continue

        if current_sec:
            if tag.name in ("ul", "ol"):
                for li in tag.find_all("li", recursive=False):
                    li_text = li.get_text(strip=True)
                    if li_text and not any(p.search(li_text) for p in compiled_bp) and li_text not in results[current_sec]:
                        results[current_sec].append(li_text)
            elif tag.name in ("p", "strong", "b") and len(text) > 10 and not tag.find_parent(["ul", "ol"]):
                if text not in results[current_sec]:
                    results[current_sec].append(text)

    return results


print(json.dumps(parse_html_dom(figma_html), indent=2))
