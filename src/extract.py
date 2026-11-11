"""
extract.py — Box 4: the LLM reads ONE page and pulls out the key facts.
Each fact comes back with a short value, the exact sentence it came from, and —
for requirements — EVERY accepted option, alternative route and exemption.
Principle: extract everything here; match it to the student later (box 9).
The LLM does NOT decide whether a fact is complete (Python, box 4) or true (Python, box 5).
"""
from typing import Literal, Optional

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

MAX_PAGE_CHARS = 60_000  # about 15,000 tokens: enough for one programme page


class Option(BaseModel):
    kind: Literal["requirement", "alternative", "exemption", "condition"] = Field(
        description="requirement = one accepted way to meet it (e.g. IELTS 6.5); "
                    "alternative = another admission route; exemption = when it does not apply; "
                    "condition = an extra rule attached to it (e.g. 'max 1 AP course from this list')")
    option: str = Field(description="The option in a few words, with all numbers")
    quote: str = Field(description="The exact text from the page for this option, copied word for word")


class Fact(BaseModel):
    found: bool = Field(description="True only if the page clearly says something about this fact")
    value: Optional[str] = Field(
        description="One short line, e.g. '€ 19,800 per year' or 'One of 6 accepted English tests'. "
                    "Do NOT put the list of options here; null if not found")
    quote: Optional[str] = Field(
        description="The exact sentence from the page that contains the value, "
                    "copied word for word (max 300 characters); null if not found")
    options: list[Option] = Field(
        description="For requirements: EVERY accepted option, alternative route, exemption and "
                    "condition listed on the page that applies to this student and faculty, "
                    "ONE item per option (e.g. IELTS and TOEFL are two items). "
                    "Empty list if the fact has a single value (e.g. duration).")
    detail_link: Optional[str] = Field(
        description="If this page links to another page with more details on this fact for this "
                    "student (e.g. their country, the programme's faculty), the full URL of that "
                    "link, copied exactly from the page. Otherwise null.")


class ProgrammeFacts(BaseModel):
    page_academic_year: Optional[str] = Field(
        description="The academic year this page's information applies to, exactly as written ON "
                    "THE PAGE (e.g. '2027/2028', '2015-16'). Do not copy the target intake. "
                    "Null if the page itself does not say")
    faculty: Optional[str] = Field(description="Name of the faculty that runs this programme, if the page says so")
    teaching_language: Fact = Field(description="Language the programme is taught in")
    duration: Fact = Field(description="Length of the programme (years and/or ECTS)")
    tuition_non_eu: Fact = Field(description="Yearly tuition fee for non-EU/EEA students, with currency and year")
    application_deadline: Fact = Field(description="Application deadline for non-EU/international students")
    language_requirement: Fact = Field(
        description="Proof of English: every accepted test with its minimum scores, and every exemption")
    academic_requirement: Fact = Field(
        description="Which high-school diploma is accepted for students from the student's country, "
                    "with all extra conditions, subject requirements (e.g. maths) and alternative routes")
    mandatory_placement: Fact = Field(description="Whether a compulsory internship or placement is part of the programme")
    thesis_required: Fact = Field(
        description="Whether a bachelor's thesis, final project or 'Bachelor's Project' is part of the programme")


SYSTEM_PROMPT = """You extract facts about one university programme from ONE web page.
Rules:
- Use ONLY the text of this page. Never use your own knowledge. Never guess.
- If the page says nothing about a fact, set found=false, options=[] and the rest null.
- Every quote must be copied word for word from the page: no paraphrasing, no fixing typos.
- Requirements are usually SETS of options: list EVERY accepted test, route, exemption and
  condition, not just the first one. Do not choose for the student.
- If a page lists rules for several countries or faculties, use ONLY those for this
  student's country and this programme's faculty.
- If the page points to another page for more details, copy that link's URL into detail_link.
- Report which academic year the page applies to, if it says so."""


def extract_from_page(page_text: str, programme: dict, intake: str,
                      student: str, faculty: str | None) -> ProgrammeFacts:
    """Ask gpt-4o-mini for the key facts on one page, in a fixed format."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(ProgrammeFacts)
    user_msg = (
        f"Programme: {programme['university']} – {programme['degree']} {programme['name']}\n"
        f"Faculty: {faculty or 'unknown'}\n"
        f"Target intake: {intake}\n"
        f"Student: {student}\n\n"
        f"PAGE TEXT:\n{page_text[:MAX_PAGE_CHARS]}"
    )
    return llm.invoke([("system", SYSTEM_PROMPT), ("human", user_msg)])
