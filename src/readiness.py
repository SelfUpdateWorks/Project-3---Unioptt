"""
readiness.py — Box 9: compare the student's profile with the requirements.
Plain Python rules, no AI. No scores, no ranking, no psychometrics:
only "met", "gap" or "check" for each concrete requirement.

  met   = the profile clearly meets the requirement
  gap   = the profile clearly does not meet it (yet)
  check = we cannot tell from the profile — the student must check this
"""
import re
from datetime import date, datetime

# Exams/qualifications that a requirement may ask for on top of the school diploma
EXTRA_QUALIFICATIONS = {"AP": "AP courses (College Board)", "A-level": "A-levels",
                        "SAT": "SAT", "ACT": "ACT", "IB": "International Baccalaureate"}


def first_number(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text, re.IGNORECASE)
    return float(match.group(1)) if match else None


def item(area: str, status: str, finding: str, fact: dict | None) -> dict:
    return {"area": area, "status": status, "finding": finding,
            "fact_status": fact["status"] if fact else "Unknown"}


# ---------- One rule per area ----------

CEFR = ["A1", "A2", "B1", "B2", "C1", "C2"]
# German certificates and the CEFR level they stand for (approximate, for flagging only)
GERMAN_TESTS = {"dsh-3": "C2", "dsh 3": "C2", "dsh-2": "C1", "dsh 2": "C1", "dsh-1": "B2",
                "testdaf": "C1", "c1 hochschule": "C1"}


def required_cefr(fact: dict) -> str | None:
    """The LOWEST level among the accepted options (the student needs only one of them)."""
    levels = []
    for o in fact["options"] or [{"option": fact["value"] or ""}]:
        text = o["option"].lower()
        levels += [lvl.upper() for lvl in re.findall(r"\b([abc][12])\b", text)]
        levels += [lvl for test, lvl in GERMAN_TESTS.items() if test in text]
    return min(levels, key=CEFR.index) if levels else None


def check_german(profile: dict, fact: dict | None) -> dict:
    if not fact or fact["value"] is None:
        return item("German", "check", "German language requirement not found — check the official page.", fact)
    have = (profile.get("german") or {}).get("cefr")
    need = required_cefr(fact)
    if need is None:
        return item("German", "check", f"Required: {fact['value']}. Compare with your German level ({have}).", fact)
    if have is None or CEFR.index(have) < CEFR.index(need):
        return item("German", "gap", f"The programme is taught in German and needs about {need} level "
                    f"(e.g. DSH-2 / TestDaF); your profile shows {have or 'no German'}.", fact)
    return item("German", "check", f"Your German ({have}) reaches the needed {need} level — you still need "
                "an accepted certificate.", fact)


def check_language(profile: dict, fact: dict | None, teaching_language: str = "English") -> dict:
    if "german" in teaching_language.lower():
        return check_german(profile, fact)
    if not fact or not fact["options"]:
        return item("English", "check", "Language requirement not found — check the official page.", fact)
    exam, score = profile["english"]["exam"], profile["english"]["score"]
    option = next((o["option"] for o in fact["options"] if exam and exam.lower() in o["option"].lower()), None)
    if option is None:
        return item("English", "gap", f"Your test ({exam}) is not on the list of accepted tests.", fact)
    overall = first_number(r"overall score (\d+(?:\.\d+)?)", option)
    each = first_number(r"min\.? (\d+(?:\.\d+)?) in every", option)
    if overall is None:
        return item("English", "check", f"Accepted: {option}. Compare with your {exam} result.", fact)
    if score < overall:
        return item("English", "gap", f"{exam} {score} is below the required {overall} overall.", fact)
    if each is not None:
        return item("English", "check", f"{exam} {score} overall meets {overall} ✓ — but each section "
                    f"must be at least {each}. Your section scores are not in the profile.", fact)
    return item("English", "met", f"{exam} {score} meets the required {overall} overall.", fact)


def check_academic(profile: dict, fact: dict | None) -> list[dict]:
    if not fact or fact["value"] is None:
        return [item("Diploma", "check", "Diploma requirement not found — check the official page.", fact)]
    text = " ".join([fact["value"]] + [o["option"] for o in fact["options"]])
    results = []
    for key, name in EXTRA_QUALIFICATIONS.items():
        if re.search(rf"\b{re.escape(key)}\b", text) and not profile.get("extra_qualifications"):
            results.append(item("Diploma", "gap", f"Your diploma ({profile['high_school_type']}) alone is not "
                                f"enough: the rule also asks for {name}. Your profile shows none.", fact))
    if not fact["complete"]:
        results.append(item("Diploma", "check", "Only the general rule was found, not the one for your "
                            "diploma — check the country page.", fact))
    if re.search(r"math", text, re.IGNORECASE):
        results.append(item("Mathematics", "check", "A mathematics level is required — check that your "
                            "school maths matches it.", fact))
    return results or [item("Diploma", "met", "Your diploma type matches the stated rule.", fact)]


def check_budget(profile: dict, tuition: dict | None, costs: dict) -> dict:
    fee = costs.get("tuition_eur")        # yearly tuition, worked out in costs.py (box 8)
    if fee is None:
        nums = [int(n) for n in re.findall(r"\d+", (tuition or {}).get("value", "").replace(",", "")
                                           .replace(".", "")) if int(n) >= 1000]
        if not nums:
            return item("Budget", "check", "Tuition fee not found — cannot compare with your budget.", tuition)
        fee = max(nums)
    living = costs.get("living_eur_per_year", 0)
    total = fee + living
    budget = profile["budget_eur_per_year"]
    what = "tuition + living costs" if living else "tuition alone"
    rate = costs.get("eur_try")
    in_try = (lambda eur: f" (≈ ₺{round(eur * rate):,})") if rate else (lambda eur: "")
    if total > budget:
        return item("Budget", "gap", f"{what.capitalize()} = €{total:,}/year{in_try(total)}; your budget is "
                    f"€{budget:,}. Shortfall: €{total - budget:,}/year{in_try(total - budget)}.", tuition)
    return item("Budget", "met", f"{what.capitalize()} = €{total:,}/year, within your €{budget:,} budget.", tuition)


def check_deadline(fact: dict | None, today: date) -> dict:
    if not fact or not fact["value"]:
        return item("Deadline", "check", "Application deadline not found.", fact)
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            deadline = datetime.strptime(fact["value"].strip(), fmt).date()
            break
        except ValueError:
            continue
    else:
        return item("Deadline", "check", f"Deadline: {fact['value']} — plan backwards from it.", fact)
    days = (deadline - today).days
    if days < 0:
        return item("Deadline", "gap", f"The deadline ({fact['value']}) has passed.", fact)
    return item("Deadline", "met", f"Apply by {fact['value']}: {days} days from today. "
                "Language tests and documents must be ready before then.", fact)


def check_scholarship(fact: dict | None, rules: list[dict]) -> dict:
    names = [o["option"] for o in (fact or {}).get("options", [])]
    national = next((r for r in rules if r["topic"] == "National scholarships" and r["points"]), None)
    if names:
        listed = "; ".join(names[:4])
        return item("Scholarship", "check", f"You need a scholarship. The university lists: {listed}. "
                    "Check who can apply, the amount and the deadline for each.", fact)
    if national:
        return item("Scholarship", "check", "You need a scholarship. No programme scholarship was found; "
                    "see the national scholarships in section 5.", None)
    return item("Scholarship", "check", "You need a scholarship, but none was found on the official pages — "
                "ask the university's admissions office.", fact)


def assess_readiness(profile: dict, facts: dict, costs: dict, rules: list[dict] | None = None,
                     today: date | None = None, teaching_language: str = "English") -> list[dict]:
    today = today or date.today()
    results = [check_language(profile, facts.get("language_requirement"), teaching_language)]
    results += check_academic(profile, facts.get("academic_requirement"))
    results.append(check_budget(profile, facts.get("tuition_non_eu"), costs))
    results.append(check_deadline(facts.get("application_deadline"), today))
    if profile.get("scholarship_need"):
        results.append(check_scholarship(facts.get("scholarships"), rules or []))
    return results


# ---------- Self-test: python -m src.readiness ----------

if __name__ == "__main__":
    profile = {"high_school_type": "Anatolian High School", "budget_eur_per_year": 12000,
               "scholarship_need": True, "english": {"exam": "IELTS", "score": 7.0}}
    f = lambda value, options=(), complete=True: {"value": value, "complete": complete, "status": "Verified",
                                                  "options": [{"option": o} for o in options]}
    facts = {
        "language_requirement": f("One of 6 tests", ["IELTS (Academic): overall score 6.5 (min. 6.5 in every category)"]),
        "academic_requirement": f("Lise Diploması with at least 4 AP courses", ["Lise Diploması with at least 4 AP courses"]),
        "tuition_non_eu": f("€19800 per year"),
        "application_deadline": f("01 May 2027"),
    }
    for r in assess_readiness(profile, facts, {}, [], today=date(2026, 11, 11)):
        print(f"[{r['status']:5}] {r['area']:12} {r['finding']}")
