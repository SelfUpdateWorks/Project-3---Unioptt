"""
costs.py — Box 8: total yearly cost in EUR and TRY.

  tuition  — from the verified tuition fact (box 5)
  living   — a country-level estimate from the RAG library (official pages such as Study in NL);
             the LLM reads the passages, Python checks the number against the quote
  TRY      — converted with today's ECB rate (Frankfurter)

Living costs and every TRY amount are always "Inferred": an estimate or a calculation,
never a fact stated by the university for this programme.
"""
import re
from typing import Optional

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.rag import search
from src.tools import ToolError, get_exchange_rate
from src.verify import check_quote_on_page, numbers_in


class LivingCost(BaseModel):
    found: bool = Field(description="True only if the text gives a monthly cost of living for students")
    monthly_eur: Optional[float] = Field(
        description="Monthly living cost for one student in EUR (without tuition). If the text "
                    "gives a total, use it; if it lists items, add them up. Null if not found")
    quote: Optional[str] = Field(
        description="The exact text the number comes from (the total, or the full list of items), "
                    "copied word for word")


PROMPT = """From the text below, find the monthly cost of living for ONE student (rent, food,
insurance, transport, etc.), WITHOUT tuition fees. If the text only gives the yearly amount a
student must prove for a visa, use that divided by 12. Use only this text; never guess.
If you add up a list, copy the WHOLE list into the quote, every line, exactly as written."""


def euro_amounts(text: str) -> list[float]:
    """All amounts written with a euro sign: '€ 561' -> 561.0"""
    return [float(n.replace(",", "")) for n in re.findall(r"€\s?(\d[\d,]*(?:\.\d+)?)", text or "")]


def number_matches_quote(monthly: float, quote: str) -> bool:
    """Python checks the LLM: the number is in the quote, or is the sum of the € amounts in it,
    or the quote gives a yearly amount and the monthly number is that divided by 12."""
    if str(int(monthly)) in numbers_in(quote):
        return True
    if any(abs(int(n) - monthly * 12) <= 12 for n in numbers_in(quote)):
        return True   # e.g. '11,904 euros per year' -> 992 per month
    return abs(sum(euro_amounts(quote)) - monthly) <= 1


MAX_TRIES = 3  # the LLM sometimes skips a line in the quote; Python then asks again


def estimate_living_costs(country: str) -> dict:
    """Ask the RAG library for the monthly cost of living in this country.
    Python accepts the LLM's answer only if the quote is on the page and the number matches it;
    otherwise it asks again (max MAX_TRIES per passage)."""
    # Two searches: a cost-of-living overview, and the official minimum a student must show for
    # a visa (Germany's blocked account) — a legal estimate of living costs.
    hits = search("monthly cost of living for international students: rent, groceries, insurance",
                  country=country, topic="costs", top_k=4)
    hits += search("amount of money per year a student must prove for a visa, blocked account",
                   country=country, topic="costs", top_k=2)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(LivingCost)
    for hit in hits:
        for _ in range(MAX_TRIES):
            result = llm.invoke([("system", PROMPT), ("human", hit["text"])])
            if not (result.found and result.monthly_eur and result.quote):
                break                      # this passage has no living costs: try the next one
            if (check_quote_on_page(result.quote, hit["text"])
                    and number_matches_quote(result.monthly_eur, result.quote)):
                return {"monthly_eur": round(result.monthly_eur), "quote": result.quote,
                        "source_url": hit["url"], "source_title": hit["title"], "status": "Inferred"}
    return {"monthly_eur": None, "quote": None, "source_url": None, "source_title": None,
            "status": "Unknown"}


def tuition_eur(tuition_fact: dict | None) -> int | None:
    """Yearly tuition in EUR: '€19800 per year' -> 19800; '€3,000 per semester' -> 6000."""
    value = (tuition_fact or {}).get("value") or ""
    amounts = euro_amounts(value) + [float(n.replace(",", "")) for n in
                                     re.findall(r"(\d[\d,]*)\s?(?:EUR|euros?)", value, re.IGNORECASE)]
    amounts = [a for a in amounts if a >= 100] or [int(n) for n in numbers_in(value) if int(n) >= 1000]
    if not amounts:
        return None
    fee = max(amounts)
    quote = (tuition_fact or {}).get("quote") or ""
    if re.search(r"semester", value + " " + quote, re.IGNORECASE) and not re.search(
            r"per year|annual|yearly", value, re.IGNORECASE):
        fee *= 2   # the fee is per semester: two semesters per year
    return int(fee)


def build_costs(tuition_fact: dict | None, country: str) -> dict:
    tuition = tuition_eur(tuition_fact)
    living = estimate_living_costs(country)
    living_year = living["monthly_eur"] * 12 if living["monthly_eur"] else 0
    total = (tuition or 0) + living_year
    try:
        fx = get_exchange_rate("EUR", "TRY")
    except ToolError:
        fx = {"rate": None, "date": None, "source_url": None}
    to_try = (lambda eur: round(eur * fx["rate"])) if fx["rate"] else (lambda eur: None)
    return {
        "tuition_eur": tuition,
        "tuition_status": (tuition_fact or {}).get("status", "Unknown"),
        "living_eur_per_month": living["monthly_eur"],
        "living_eur_per_year": living_year,
        "living": living,
        "total_eur": total,
        "eur_try": fx["rate"], "rate_date": fx["date"], "rate_source": fx["source_url"],
        "tuition_try": to_try(tuition or 0),
        "living_try": to_try(living_year),
        "total_try": to_try(total),
        "status": "Inferred",   # a sum of a fact and an estimate, converted: always Inferred
    }
