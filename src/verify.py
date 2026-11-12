"""
verify.py — Box 5: the four verification checks. Plain Python, no AI.
The LLM proposed each fact with a quote; here we decide whether to trust it.

  1. official      — the source is the university's own website or an official application portal
  2. quote_on_page — the quoted text really appears in the downloaded page
  3. value_in_quote — the numbers in the value really appear in the quote
  4. right_intake  — the page is for the target intake (or does not say), not an older year

Status:  not official                  -> Inferred
         official + all 4 checks pass  -> Verified
         official + any check fails    -> Needs Review
         (never found -> Unknown, decided in graph.py)
"""
import re
import unicodedata
from datetime import date
from urllib.parse import urlparse

from src.schemas import VerificationRecord

# Official application portals that count as "official" besides the university's own site
OFFICIAL_PORTALS = ["studielink.nl", "uni-assist.de", "hochschulstart.de"]


def normalise(text: str) -> str:
    """Make texts comparable: same letters, no table/markdown symbols, single spaces, lower case."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[*_|#>`]", " ", text)          # markdown and table symbols
    return re.sub(r"\s+", " ", text).strip().lower()


def numbers_in(text: str) -> set[str]:
    """All numbers in a text, written the same way: '€ 19,800' -> '19800', '6.5' -> '65'."""
    return {re.sub(r"[.,]", "", n) for n in re.findall(r"\d+(?:[.,]\d+)*", text or "")}


def on_site(url: str, domain: str) -> bool:
    host = urlparse(url or "").netloc.lower()
    return host == domain or host.endswith("." + domain)


# ---------- The four checks ----------

def check_official(source_url: str, domain: str) -> bool:
    return on_site(source_url, domain) or any(on_site(source_url, p) for p in OFFICIAL_PORTALS)


def check_quote_on_page(quote: str, page_text: str) -> bool:
    return bool(quote) and normalise(quote) in normalise(page_text)


def check_value_in_quote(value: str, quote: str) -> bool:
    """Every number in the value must appear in the quote. Values without numbers
    (e.g. 'English') need at least one of their words in the quote."""
    nums = numbers_in(value)
    if nums:
        return nums <= numbers_in(quote)
    words = [w for w in re.findall(r"\w+", (value or "").lower()) if len(w) > 3]
    return any(w in normalise(quote) for w in words) if words else False


def check_right_intake(freshness: str) -> bool:
    return freshness in ("current", "unknown")   # "previous" or older -> fails


# ---------- Put it together for one fact ----------

def verify_fact(fact: dict, page_text: str, domain: str) -> dict:
    """Run the four checks on one fact and return its checks, status and VerificationRecord."""
    bad_options = []
    if fact["options"]:
        # Requirements with options: every option is checked with its own quote
        bad_options = [o["option"] for o in fact["options"]
                       if not check_quote_on_page(o["quote"], page_text)]
        quote_ok = not bad_options
        value_ok = all(check_value_in_quote(o["option"], o["quote"]) for o in fact["options"])
    else:
        quote_ok = check_quote_on_page(fact["quote"], page_text)
        value_ok = check_value_in_quote(fact["value"], fact["quote"])

    checks = {
        "official": check_official(fact["source_url"], domain),
        "quote_on_page": quote_ok,
        "value_in_quote": value_ok,
        "right_intake": check_right_intake(fact["freshness"]),
    }

    if not checks["official"]:
        status, source, confidence = "Inferred", "inferred", "low"
    elif all(checks.values()) and fact["complete"]:
        status, source, confidence = "Verified", "official", "high"
    else:
        status, source, confidence = "Needs Review", "official", "medium"

    failed = [name for name, ok in checks.items() if not ok]
    if bad_options:   # say WHICH option's quote was not word for word on the page
        failed[failed.index("quote_on_page")] = ("quote_on_page (not word for word: "
                                                 + "; ".join(o[:40] for o in bad_options) + ")")
    if not fact["complete"]:
        failed.append("incomplete")
    notes = f"Quote: \"{fact['quote'] or ''}\""
    if failed:
        notes = f"Failed: {', '.join(failed)}. " + notes

    record = VerificationRecord(status=status, source=source, source_url=fact["source_url"],
                                last_verified=date.today().isoformat(),
                                confidence=confidence, notes=notes)
    return {"checks": checks, "status": status, "verification": record.model_dump()}


# ---------- Self-test: python -m src.verify ----------

if __name__ == "__main__":
    page = "| non-EU/EEA | 2027-2028 | €19,800 | full-time |\nLanguage of instruction English"
    base = {"source_url": "https://www.rug.nl/bachelors/ai", "freshness": "current",
            "complete": True, "options": []}
    tests = [
        ("real quote, right number",  {**base, "value": "€19800", "quote": "non-EU/EEA | 2027-2028 | €19,800"}, "Verified"),
        ("made-up quote",             {**base, "value": "€15000", "quote": "Tuition is €15,000 per year"}, "Needs Review"),
        ("real quote, wrong number",  {**base, "value": "€18000", "quote": "non-EU/EEA | 2027-2028 | €19,800"}, "Needs Review"),
        ("blog source",               {**base, "source_url": "https://some-blog.com/groningen",
                                       "value": "€19800", "quote": "non-EU/EEA | 2027-2028 | €19,800"}, "Inferred"),
        ("last year's page",          {**base, "freshness": "previous", "value": "English",
                                       "quote": "Language of instruction English"}, "Needs Review"),
    ]
    for name, fact, expected in tests:
        got = verify_fact(fact, page, "rug.nl")["status"]
        print(f"{'✅' if got == expected else '❌'} {name:28} → {got} (expected {expected})")
