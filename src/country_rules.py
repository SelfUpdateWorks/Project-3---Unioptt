"""
country_rules.py — Box 7: general rules for the country, from the RAG library
(official national sources: DAAD, Study in Germany, uni-assist, Study in NL, Nuffic, YÖK).

The LLM answers a few fixed questions from the retrieved passages, one quote per point.
Python keeps only the points whose quote really appears in a passage.
Every point is "Inferred" (source "country_default"): a national rule applied to this
programme, not a fact the university stated.
"""
from datetime import date

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.rag import search
from src.schemas import VerificationRecord
from src.verify import check_quote_on_page

COUNTRY_NAMES = {"NL": "the Netherlands", "DE": "Germany"}
MAX_TRIES = 2

# (topic shown in the report, question, which country's documents, RAG topic filter)
QUESTIONS = [
    ("Recognition of the Turkish diploma",
     "How is a Turkish high-school diploma (Lise Diploması) assessed for bachelor admission in {name}? "
     "Is a foundation year or Studienkolleg needed?", "{code}", "recognition"),
    ("How to apply",
     "How do international students apply for a bachelor's programme in {name}: which portal, which steps?",
     "{code}", "application"),
    ("National scholarships",
     "Which national scholarships exist for non-EU bachelor students in {name}?", "{code}", "scholarships"),
    ("Recognition back in Türkiye (YÖK)",
     "How is a foreign university degree recognised in Türkiye (YÖK denklik), and what does it cost?",
     "TR", "recognition"),
]


class RulePoint(BaseModel):
    point: str = Field(description="One short point in English that answers the question")
    quote: str = Field(description="The exact text from ONE passage that supports the point, word for word, "
                                   "in its original language")


class RuleSummary(BaseModel):
    found: bool = Field(description="True only if the passages answer the question")
    points: list[RulePoint] = Field(description="At most 3 points")


PROMPT = """Answer the question using ONLY the passages. Never use your own knowledge.
Give at most 3 short points. Each point needs a quote copied word for word from one passage.
If the passages do not answer the question, set found=false and points=[]."""


def answer(question: str, country: str, topic: str) -> list[dict]:
    hits = search(question, country=country, topic=topic, top_k=4)
    if not hits:
        return []
    passages = "\n\n".join(f"[Passage {i + 1}]\n{h['text']}" for i, h in enumerate(hits))
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(RuleSummary)
    for _ in range(MAX_TRIES):
        result = llm.invoke([("system", PROMPT), ("human", f"QUESTION: {question}\n\n{passages}")])
        if not result.found:
            return []
        points = []
        for p in result.points:
            source = next((h for h in hits if check_quote_on_page(p.quote, h["text"])), None)
            if source:   # Python keeps only points whose quote is really in a passage
                points.append({"point": p.point, "quote": p.quote,
                               "source_url": source["url"], "source_title": source["title"]})
        if points:
            return points
    return []


def fetch_country_rules(country: str) -> list[dict]:
    name = COUNTRY_NAMES.get(country, country)
    rules = []
    for topic, question, which, rag_topic in QUESTIONS:
        q = question.format(name=name, code=country)
        points = answer(q, which.format(code=country), rag_topic)
        rules.append({
            "topic": topic, "question": q, "points": points,
            "status": "Inferred" if points else "Unknown",
            "verification": VerificationRecord(
                status="Inferred" if points else "Unknown",
                source="country_default" if points else "unknown",
                source_url=points[0]["source_url"] if points else None,
                last_verified=date.today().isoformat(),
                confidence="low" if points else "none",
                notes="National rule from the curated library, applied to this programme"
                      if points else "No answer found in the curated library").model_dump(),
        })
    return rules
