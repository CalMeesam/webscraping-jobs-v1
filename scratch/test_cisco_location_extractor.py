import re

def extract_location_from_title_or_parent(title: str, parent_text: str | None = None) -> str | None:
    # 1. Delimited by pipe, dash, or parentheses at the end of title
    # e.g. "ASIC Engineering Design Verification Leader (SystemVerilog, Python, C and UVM |8-12 years| Pune)"
    # e.g. "ASIC Physical Design Engineer - 7 to 10 years - Pune"
    m_pipe = re.search(r"\|\s*([A-Za-z\s,]+)\s*\)?$", title)
    if m_pipe:
        loc = m_pipe.group(1).strip()
        if len(loc) >= 2 and not any(x in loc.lower() for x in ["year", "years", "month", "full time", "part time"]):
            return loc

    m_dash = re.search(r"\-\s*([A-Za-z\s,]+)\s*$", title)
    if m_dash:
        loc = m_dash.group(1).strip()
        if len(loc) >= 2 and not any(x in loc.lower() for x in ["year", "years", "month", "full time", "part time", "leader", "engineer"]):
            return loc

    # 2. Check parent text for city/location keywords
    if parent_text:
        m_loc = re.search(r"\b(Pune|Bengaluru|Bangalore|San Jose|Research Triangle Park|RTP|London|Singapore|Sydney|Berlin|Tokyo|Toronto)\b", parent_text, re.IGNORECASE)
        if m_loc:
            return m_loc.group(1).title()

    return None

test_titles = [
    "ASIC Engineering Design Verification Leader (SystemVerilog, Python, C and UVM |8-12 years| Pune)",
    "ASIC Engineering Design Verification Leader (SystemVerilog, Python, C and UVM |12-16 years| Pune)",
    "ASIC Physical Design Engineer - 7 to 10 years - Pune",
]

for t in test_titles:
    print("Title:", t)
    print("  Extracted Location:", extract_location_from_title_or_parent(t))
