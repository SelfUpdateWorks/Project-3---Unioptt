"""
graph.py — The LangGraph skeleton of the Programme Research Agent.
Day 2: every node is a STUB (fake data) so we can test the flow end to end.
Day 3: we replace the stubs, one by one, with the real tools.
"""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

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


# ---------- The shared state: the agent's "notebook" ----------

class AgentState(TypedDict, total=False):
    programme: dict          # university, programme name, country
    intake: str              # e.g. "Winter 2027/28"
    profile: dict            # synthetic student profile
    attempts: int            # how many search rounds so far
    candidate_urls: list     # pages found by search
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


def find_official_page(state: AgentState) -> dict:                  # box 2
    attempts = state["attempts"] + 1
    return {"attempts": attempts,
            "candidate_urls": ["https://example.org/STUB-official-page"],
            "log": [f"2 find_official_page: search round {attempts} (STUB)"]}


def read_pages(state: AgentState) -> dict:                          # box 3
    return {"pages": [{"url": u, "text": "STUB page text"} for u in state["candidate_urls"]],
            "log": [f"3 read_pages: {len(state['candidate_urls'])} page(s) (STUB)"]}


def extract_facts(state: AgentState) -> dict:                       # box 4
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