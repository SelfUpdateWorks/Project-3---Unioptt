"""
graph.py — The LangGraph skeleton of the Programme Research Agent.
Day 2: every node is a STUB (fake data) so we can test the flow end to end.
Day 3: we replace the stubs, one by one, with the real tools.
"""

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


from src.tools import ToolError, read_page, search_web

# The key facts every report must try to verify (Tier 1)
KEY_FACTS = [
    "teaching_language",
    "duration",
    "tuition_non_eu",
    "application_deadline",
    "language_requirement",
    "academic_requirement",
    "mandatory_placement",
    "thesis_required",
]
MAX_ATTEMPTS = 3  # how many search rounds before a fact becomes "Unknown"

# Extra search words for each fact, used when that fact is still missing
FACT_QUERIES = {
    "teaching_language": "language of instruction",
    "duration": "programme duration years ECTS",
    "tuition_non_eu": "tuition fee non-EU students",
    "application_deadline": "application deadline",
    "language_requirement": "English language requirements IELTS TOEFL",
    "academic_requirement": "admission requirements international diploma",
    "mandatory_placement": "internship placement",
    "thesis_required": "bachelor thesis",
}

# Words in a page address or title that mean "wrong degree level"
WRONG_DEGREE_WORDS = {
    "bachelor": ["master", "msc", "phd", "pre-master"],
    "master": ["bachelor", "bsc", "phd"],
}


# ---------- The shared state: the agent's "notebook" ----------

class AgentState(TypedDict, total=False):
    programme: dict          # university, programme name, country
    intake: str              # e.g. "Winter 2027/28"
    profile: dict            # synthetic student profile
    attempts: int            # how many search rounds so far
    candidate_urls: list     # pages found by search
    seen_urls: list
    pages: list              # downloaded page texts
    facts: dict              # fact name -> {value, quote, source_url, status}
    missing: list            # key facts still not found
    country_rules: list      # RAG results (admission / recognition)
    costs: dict              # EUR + TRY
    gaps: list               # profile vs requirements
    report_md: str           # the final report
    log: Annotated[list, operator.add]  # each node adds a line: the run's trace


# ---------- The 10 boxes of the diagram ----------

def load_input(state: AgentState) -> dict:                          # box 1
    p = state["programme"]
    return {"attempts": 0, "facts": {},
            "log": [f"1 load_input: {p['university']} – {p['name']}, {state['intake']}"]}


def is_wrong_degree(result: dict, degree: str) -> bool:
    """True if the address or title points to another degree level (e.g. a Master's page)."""
    text = (result["url"] + " " + result["title"]).lower()
    return any(word in text for word in WRONG_DEGREE_WORDS.get(degree, []))

def is_other_programme(result: dict, programme: dict) -> bool:
    """True if the page is about a different programme at the same level.
    Example: /bachelors/computing-science when we want /bachelors/artificial-intelligence."""
    url = result["url"].lower()
    slug = programme["name"].lower().replace(" ", "-")   # "artificial-intelligence"
    return programme["degree"] in url and slug not in url


def find_official_page(state: AgentState) -> dict:                  # box 2
    p = state["programme"]
    attempts = state["attempts"] + 1
    seen = state.get("seen_urls", [])
    base = f"{p['university']} {p['degree']} {p['name']}"

    # Round 1: one general search. Later rounds: one search per missing fact (max 3).
    if attempts == 1:
        queries = [f"{base} admission requirements tuition fees"]
    else:
        queries = [f"{base} {FACT_QUERIES[f]}" for f in state["missing"][:3]]

    # Search only the university's own website, except in the last round
    domains = [p["domain"]] if attempts < MAX_ATTEMPTS else None

    found, rejected = [], []
    for q in queries:
        try:
            results = search_web(q, max_results=5, include_domains=domains)
        except ToolError:
            continue                      # no results for this query: try the next one
        for r in results:
            if r["url"] in seen or r["url"] in found:
                continue                  # already have it
            if is_wrong_degree(r, p["degree"]) or is_other_programme(r, p):
                rejected.append(r["url"])
                continue
            found.append(r["url"])

    candidates = found[:3]                # read at most 3 new pages per round
    where = p["domain"] if domains else "whole web"
    return {"attempts": attempts,
            "candidate_urls": candidates,
            "seen_urls": seen + candidates,
            "log": [f"2 find_official_page: round {attempts} on {where}, "
                    f"{len(candidates)} new page(s), {len(rejected)} rejected (wrong degree or programme)"]
                   + [f"     → {u}" for u in candidates]}


def final_url(text: str, requested: str) -> str:
    """If the page redirected, Jina writes 'Final URL:' at the top. Use that as the real source."""
    for line in text.splitlines()[:10]:
        if line.startswith("Final URL:"):
            return line.split(":", 1)[1].strip()
    return requested


def read_pages(state: AgentState) -> dict:                          # box 3
    pages, failed = [], []
    for url in state["candidate_urls"]:
        try:
            page = read_page(url)
        except (ToolError, ValueError):
            failed.append(url)            # skip this page, keep going
            continue
        pages.append({
            "url": final_url(page["text"], url),   # where the text really came from
            "requested_url": url,
            "text": page["text"],
            "chars": page["chars"],
        })
    log = [f"3 read_pages: {len(pages)} read, {len(failed)} failed"]
    log += [f"     ✓ {p['chars']:>6} chars  {p['url']}" for p in pages]
    log += [f"     ✗ {u}" for u in failed]
    return {"pages": pages, "log": log}


def extract_facts(state: AgentState) -> dict:                       # box 4
    if not state["pages"]:
        return {"log": ["4 extract_facts: no pages to read (STUB)"]}
    # STUB: pretend tuition is only found in round 2, so the loop runs once
    found = [f for f in KEY_FACTS if f != "tuition_non_eu" or state["attempts"] >= 2]
    facts = dict(state["facts"])
    for name in found:
        facts[name] = {"value": "STUB", "quote": "STUB", "source_url": state["pages"][0]["url"]}
    return {"facts": facts, "log": [f"4 extract_facts: {len(found)}/{len(KEY_FACTS)} facts (STUB)"]}


def check_facts(state: AgentState) -> dict:                         # box 5
    facts = {name: {**f, "status": "Needs Review"} for name, f in state["facts"].items()}
    missing = [name for name in KEY_FACTS if name not in facts]
    return {"facts": facts, "missing": missing,
            "log": [f"5 check_facts: missing = {missing or 'none'} (STUB rules)"]}


def route_after_check(state: AgentState) -> str:                    # box 6 (decision)
    if state["missing"] and state["attempts"] < MAX_ATTEMPTS:
        return "search_again"
    return "continue"


def mark_unknown(state: AgentState) -> dict:
    """Facts still missing after all rounds become Unknown — never guessed."""
    facts = dict(state["facts"])
    for name in state["missing"]:
        facts[name] = {"value": None, "quote": None, "source_url": None, "status": "Unknown"}
    return {"facts": facts, "log": [f"6 decision: continue ({len(state['missing'])} marked Unknown)"]}


def country_rules(state: AgentState) -> dict:                       # box 7
    return {"country_rules": [{"text": "STUB rule", "url": "STUB", "status": "Inferred"}],
            "log": [f"7 country_rules: RAG for country={state['programme']['country']} (STUB)"]}


def cost_in_try(state: AgentState) -> dict:                         # box 8
    return {"costs": {"total_eur": 0, "total_try": 0, "status": "Inferred"},
            "log": ["8 cost_in_try: EUR → TRY (STUB)"]}


def readiness(state: AgentState) -> dict:                           # box 9
    return {"gaps": ["STUB gap"], "log": ["9 readiness: profile vs requirements (STUB)"]}


def write_report(state: AgentState) -> dict:                        # box 10
    p = state["programme"]
    rows = "\n".join(f"| {n} | {f['value']} | {f['status']} |" for n, f in state["facts"].items())
    md = (f"# Programme Due Diligence Report (SKELETON)\n\n"
          f"**{p['university']} – {p['name']}** · intake {state['intake']}\n\n"
          f"| Fact | Value | Status |\n|---|---|---|\n{rows}\n")
    return {"report_md": md, "log": ["10 write_report: report ready (STUB)"]}


# ---------- Wiring: nodes + edges ----------

def build_graph():
    g = StateGraph(AgentState)
    for name, fn in [
        ("load_input", load_input),
        ("find_official_page", find_official_page),
        ("read_pages", read_pages),
        ("extract_facts", extract_facts),
        ("check_facts", check_facts),
        ("mark_unknown", mark_unknown),
        ("country_rules", country_rules),
        ("cost_in_try", cost_in_try),
        ("readiness", readiness),
        ("write_report", write_report),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "load_input")
    g.add_edge("load_input", "find_official_page")
    g.add_edge("find_official_page", "read_pages")
    g.add_edge("read_pages", "extract_facts")
    g.add_edge("extract_facts", "check_facts")
    g.add_conditional_edges("check_facts", route_after_check,
                            {"search_again": "find_official_page", "continue": "mark_unknown"})
    g.add_edge("mark_unknown", "country_rules")
    g.add_edge("country_rules", "cost_in_try")
    g.add_edge("cost_in_try", "readiness")
    g.add_edge("readiness", "write_report")
    g.add_edge("write_report", END)
    return g.compile()