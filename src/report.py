"""
report.py — Box 10: write the Programme Due Diligence Report (Markdown) and the JSON record.

No AI here: every sentence is built from the checked data, so the last step cannot add
new mistakes. Statuses are copied exactly as box 5 set them.

Sections (README template):
  0 Header · 1 Snapshot · 2 Key requirements · 3 Total yearly cost · 4 Recognition
  5 Scholarships · 6 Readiness & gaps · 7 Missing info & next steps · 8 Sources & verification log
"""
import json
import re
from datetime import date
from pathlib import Path

REPORTS_DIR = Path("reports")

LABELS = {
    "teaching_language": "Teaching language",
    "duration": "Duration",
    "tuition_non_eu": "Tuition (non-EU)",
    "application_deadline": "Application deadline",
    "language_requirement": "English requirement",
    "academic_requirement": "Diploma requirement",
    "mandatory_placement": "Mandatory placement",
    "thesis_required": "Thesis / final project",
    "scholarships": "Scholarships (university)",
}
STATUS_ICON = {"Verified": "✅", "Needs Review": "⚠️", "Inferred": "🔹", "Unknown": "❓"}
GAP_ICON = {"met": "✅", "gap": "❌", "check": "🔍"}

# Next step for each readiness area that is a gap or needs checking (rule-based, no AI)
NEXT_STEPS = {
    "Diploma": "Ask the admissions office which routes exist for a Turkish Lise Diploması without AP "
               "courses (e.g. AP exams in your last school year, a foundation year, or another route).",
    "Budget": "Close the funding gap: apply for the scholarships listed in section 5 and plan "
              "a family budget in TRY with a safety margin for exchange-rate changes.",
    "English": "Check your IELTS section scores against the requirement; retake the test if any "
               "section is below the minimum.",
    "Mathematics": "Compare your school maths with the required level and keep your course "
                   "descriptions ready for the Admissions Board.",
    "Scholarship": "Check each scholarship's eligibility for Turkish citizens, its amount and its "
                   "deadline — many close months before the application deadline.",
    "Deadline": "Work backwards from the deadline: language test, documents, application.",
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def status_cell(fact: dict) -> str:
    return f"{STATUS_ICON.get(fact['status'], '')} {fact['status']}"


def value_cell(fact: dict) -> str:
    if fact["value"] is None:
        return "not found on the official pages"
    return fact["value"] + ("" if fact["complete"] else " (incomplete)")


def options_lines(fact: dict) -> list[str]:
    return [f"  - _{o['kind']}_: {o['option']}" for o in fact.get("options", [])]


def tidy(quote: str | None, limit: int = 250) -> str:
    """One line, without list bullets or stray quote marks, for the sources log."""
    text = " / ".join(line.strip(" *\"") for line in (quote or "").splitlines() if line.strip(" *\""))
    return text[:limit]


def rule(rules: list[dict], topic: str) -> dict | None:
    return next((r for r in rules if r["topic"] == topic), None)


# ---------- Markdown ----------

def build_markdown(state: dict) -> str:
    p, prof, facts = state["programme"], state["profile"], state["facts"]
    costs, rules, gaps = state["costs"], state["country_rules"], state["gaps"]
    f = lambda name: facts.get(name)
    today = date.today().isoformat()
    counts = {s: sum(1 for x in facts.values() if x["status"] == s)
              for s in ("Verified", "Needs Review", "Inferred", "Unknown")}
    main_gaps = [g["area"] for g in gaps if g["status"] == "gap"]
    L = []

    # 0 Header
    L += [f"# Programme Due Diligence Report",
          f"## {p['university']} — {p['degree'].capitalize()} {p['name']}",
          f"**Target intake:** {state['intake']} · **Report date:** {today} · "
          f"**Student:** {prof['name']} ({prof['persona_id']})", ""]
    em = prof.get("engine_match")
    if em:
        L += [f"**Unioptt match (quoted from the matching engine, not recalculated):** "
              f"{em['label']} — {em['score']}/100 ({em['engine_version']})", ""]
    L += [f"**At a glance:** {counts['Verified']} of {len(facts)} key facts Verified, "
          f"{counts['Needs Review']} Needs Review, {counts['Unknown']} Unknown. "
          f"Main gaps: {', '.join(main_gaps) or 'none found'}.", ""]

    # 1 Snapshot
    L += ["## 1. Programme snapshot", "| | Value | Status |", "|---|---|---|"]
    for name in ["teaching_language", "duration", "mandatory_placement", "thesis_required"]:
        if f(name):
            L.append(f"| {LABELS[name]} | {value_cell(f(name))} | {status_cell(f(name))} |")
    L.append("")

    # 2 Key requirements
    L += ["## 2. Key requirements"]
    for name in ["language_requirement", "academic_requirement", "application_deadline"]:
        if f(name):
            L.append(f"- **{LABELS[name]}:** {value_cell(f(name))} — {status_cell(f(name))}")
            L += options_lines(f(name))
    apply_rule = rule(rules, "How to apply")
    if apply_rule and apply_rule["points"]:
        L.append(f"- **How to apply:** {apply_rule['points'][0]['point']} — 🔹 Inferred (national rule)")
    L.append("")

    # 3 Total yearly cost
    c = costs
    L += ["## 3. Total yearly cost", "| | EUR | TRY | Status |", "|---|---|---|---|",
          f"| Tuition (non-EU) | €{c['tuition_eur'] or 0:,} | ₺{c['tuition_try'] or 0:,} | "
          f"{c['tuition_status']} (TRY: Inferred) |"]
    if c["living_eur_per_month"]:
        L.append(f"| Living costs (€{c['living_eur_per_month']:,}/month) | €{c['living_eur_per_year']:,} | "
                 f"₺{c['living_try'] or 0:,} | Inferred |")
    else:
        L.append("| Living costs | Unknown | Unknown | Unknown |")
    L += [f"| **Total per year** | **€{c['total_eur']:,}** | **₺{c['total_try'] or 0:,}** | Inferred |", ""]
    if c["eur_try"]:
        L.append(f"1 EUR = {c['eur_try']} TRY (ECB, {c['rate_date']}). Lira amounts change with the rate. "
                 "Living costs are a national average, not specific to this city.")
    L.append("")

    # 4 Recognition
    L += ["## 4. Recognition of the Turkish diploma"]
    if f("academic_requirement"):
        a = f("academic_requirement")
        L.append(f"- **This university:** {value_cell(a)} — {status_cell(a)}")
    for topic in ["Recognition of the Turkish diploma", "Recognition back in Türkiye (YÖK)"]:
        r = rule(rules, topic)
        if r and r["points"]:
            L.append(f"- **{topic}:** " + " ".join(pt["point"] for pt in r["points"]) + " — 🔹 Inferred")
    L += ["- _Not legal advice: recognition rules are reported with their source._", ""]

    # 5 Scholarships
    L += ["## 5. Scholarships"]
    s = f("scholarships")
    if s and s["options"]:
        L.append(f"- **From the university** — {status_cell(s)}:")
        L += options_lines(s)
    else:
        L.append("- **From the university:** none found on the official pages.")
    nat = rule(rules, "National scholarships")
    if nat and nat["points"]:
        L.append("- **National (🔹 Inferred — check eligibility for Turkish citizens before relying on them):**")
        L += [f"  - {pt['point']}" for pt in nat["points"]]
    L.append("")

    # 6 Readiness & gaps
    L += ["## 6. Readiness & gaps"]
    L += [f"- {GAP_ICON[g['status']]} **{g['area']}:** {g['finding']}" for g in gaps]
    L.append("")

    # 7 Missing info & next steps
    L += ["## 7. What's missing & next steps"]
    for name, x in facts.items():
        if x["status"] in ("Unknown", "Needs Review"):
            why = x["verification"]["notes"].split(". Quote:")[0] if x["status"] == "Needs Review" \
                else "not found on the official pages"
            L.append(f"- {status_cell(x)} **{LABELS[name]}** — {why}")
    L.append("")
    steps = [NEXT_STEPS[g["area"]] for g in gaps if g["status"] == "gap" and g["area"] in NEXT_STEPS]
    steps += [NEXT_STEPS[g["area"]] for g in gaps if g["status"] == "check" and g["area"] in NEXT_STEPS]
    L += ["**Next steps:**"] + [f"{i}. {step}" for i, step in enumerate(dict.fromkeys(steps), 1) if i <= 3]
    L.append("")

    # 8 Sources & verification log
    L += ["---", "## 8. Sources & verification log",
          "Checks: official source · quote found on the page · value in the quote · right intake year. "
          "_Verified_ means all four automatic checks passed (agent-verified, not human-verified).", ""]
    for name, x in facts.items():
        L.append(f"**{LABELS[name]}** — {status_cell(x)}")
        if x.get("checks"):
            L.append("Checks: " + " · ".join(f"{'✓' if ok else '✗'} {k}" for k, ok in x["checks"].items()))
        if x["source_url"]:
            L += [f"Source: {x['source_url']} (page year: {x['page_year'] or 'not stated'})",
                  f"Quote: “{tidy(x['quote'])}”"]
        L.append("")
    L.append("**Country rules (national sources, Inferred):**")
    for r in rules:
        for pt in r["points"]:
            L.append(f"- {r['topic']}: “{tidy(pt['quote'], 200)}” — {pt['source_url']}")
    if c["living"]["source_url"]:
        L.append(f"- Living costs: “{tidy(c['living']['quote'])}” — {c['living']['source_url']}")
    if c["rate_source"]:
        L.append(f"- Exchange rate: {c['rate_source']}")
    L += ["", "_Generated by the Unioptt Programme Research Agent. Public sources only; synthetic student "
          "profile. Not legal or financial advice._"]
    return "\n".join(L)


# ---------- JSON (shaped like Unioptt's ProgramRequirements) ----------

def section(fact: dict | None) -> dict | None:
    if not fact:
        return None
    return {"value": fact["value"], "options": fact.get("options", []),
            "complete": fact["complete"], "verification": fact["verification"]}


def build_json(state: dict) -> dict:
    facts, rules = state["facts"], state["country_rules"]
    apply_rule = rule(rules, "How to apply")
    return {
        "programme": state["programme"],
        "intake": state["intake"],
        "report_date": date.today().isoformat(),
        "profile_id": state["profile"]["persona_id"],
        "engine_match_quoted": state["profile"].get("engine_match"),
        # Unioptt ProgramRequirements sections
        "requirements": {
            "language": section(facts.get("language_requirement")),
            "academic": section(facts.get("academic_requirement")),
            "application_deadlines": section(facts.get("application_deadline")),
            "application_platform": {"value": apply_rule["points"][0]["point"],
                                     "verification": apply_rule["verification"]}
                                    if apply_rule and apply_rule["points"] else None,
            "financial": {"tuition_non_eu": section(facts.get("tuition_non_eu")),
                          "yearly_cost": {k: v for k, v in state["costs"].items() if k != "living"},
                          "living_cost_source": state["costs"]["living"]},
            "portfolio": None, "interview": None, "required_documents": None,  # not researched yet
        },
        "programme_facts": {n: section(facts.get(n)) for n in
                            ["teaching_language", "duration", "mandatory_placement",
                             "thesis_required", "scholarships"]},
        "country_rules": rules,
        "readiness": state["gaps"],
    }


def save_report(state: dict) -> tuple[str, Path, Path]:
    REPORTS_DIR.mkdir(exist_ok=True)
    p = state["programme"]
    name = f"{slug(p['university'])}_{slug(p['name'])}"
    md, js = build_markdown(state), build_json(state)
    md_path, json_path = REPORTS_DIR / f"{name}.md", REPORTS_DIR / f"{name}.json"
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps(js, indent=2, ensure_ascii=False), encoding="utf-8")
    return md, md_path, json_path
