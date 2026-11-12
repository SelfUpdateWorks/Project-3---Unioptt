# Unioptt Programme Research Agent

> Project 3 · Ironhack AI Consulting Bootcamp (Berlin) · Approved by instructor
>
> Status: ✅ Complete · two sample reports (Groningen, TUM) · n8n wrapper · demo on Day 5

An autonomous research agent that checks the facts about one university programme and writes a **Programme Due Diligence Report** for a Turkish student and their family. Every key fact carries a **value, a verification status and a source link**, and anything the agent cannot confirm is marked as such instead of guessed.

---

## 1. The problem

In Türkiye, university entry depends on one central exam (YKS). Good public universities need very high scores, and good private universities are too expensive for most families. That is why many students look abroad.

Abroad, they meet a second problem: many consultancies and agencies are paid commission by foreign institutions. They steer students toward the institutions that pay them, so students and families rarely get an objective selection process.

**Unioptt** ([unioptt.netlify.app](https://unioptt.netlify.app)) is my answer to that: a matching platform that ranks programmes by how well they fit the student (interests, academic profile, budget, lifestyle), not by who pays a commission.

**The gap this project closes:** a matching engine is only as trustworthy as its programme data. Today Unioptt's 94 programmes are hand-entered in one static file with no provenance: no source URL, no verification date, no record of who entered a value. Tuition, deadlines and language requirements change every year, and nobody can say where a number came from or whether it is still true.

## 2. What this agent does

- **Input:** one programme (university + programme name), a target intake, and a synthetic student profile.
- **What happens:** the agent finds the official programme page, reads it, and extracts the key facts together with the exact sentence each fact came from. Python code (not the LLM) then checks every fact against the source. If a fact is missing or two sources disagree, the agent searches again (a limited number of times) before marking it Unknown or Needs Review. It adds country-level admission and recognition rules from a small curated knowledge base (RAG), converts costs from EUR to TRY, and compares the requirements with the student profile.
- **Output:** a one-page Programme Due Diligence Report (Markdown) **and** a machine-readable JSON record in the same format as Unioptt's backend schema (`ProgramRequirements` + `VerificationRecord`).
- **Boundary:** the agent does **not** rank programmes or judge fit. That is the job of Unioptt's deterministic matching engine. The agent may quote the engine's result, but it never recalculates it.

## 3. Who the report is for, and what "useful" means

**Primary user:** a Turkish student and their family deciding **whether to apply to one specific programme**. Secondary users are teachers and school counsellors who advise them.

**"Useful" means:**
- every key fact (tuition, application deadline, language requirement, academic requirements, scholarships, total yearly cost in TRY) has a **source link** and a **status**;
- facts that could not be confirmed are **named clearly**, never guessed;
- the report ends with the student's concrete **gaps** (e.g. language level, budget) and **next steps**.

**Sample programmes** (both taken from Unioptt's own catalogue):

| Programme | Country | Teaching language | Why it was chosen |
|---|---|---|---|
| University of Groningen, BSc Artificial Intelligence | Netherlands | English | Tests the Dutch non-EEA tuition fee that Turkish citizens pay, and an English-language requirement |
| Technical University of Munich (TUM), BSc Informatics | Germany | German | Tests a German-language requirement, Turkish diploma recognition, and whether "German universities are free" is still true for non-EU students |

The same synthetic student profile is used for both, so the reports show how one student's readiness differs between two programmes.

## 4. How this serves Unioptt

This project is the first building block of Unioptt's **data verification layer**. The agent connects to the product in two places:

```
(A) DATA SUPPLY      official pages → agent checks facts → JSON record → catalogue (with sources)
                                                                              │
                     student profile ────────────────────────────→ matching engine (unchanged)
                                                                              │
(B) DUE DILIGENCE    student picks a programme from the shortlist → agent → report
```

- **(A) Before matching:** the agent fills Unioptt's empty `ProgramRequirements` records, so the Prepare page can show real, sourced requirements instead of country defaults.
- **(B) After matching:** the student picks a programme, and the agent produces the due diligence report. This is the Project 3 MVP.

Because the agent's output uses the backend's own Pydantic schema, it can later move into the Unioptt FastAPI backend with few changes.

## 5. Stack decision (short version)

**Primary: LangGraph (Python). Helper: n8n (thin wrapper only).**

Researching a programme is not a straight line. After finding and reading the official page, the agent must decide what to do when a fact is missing or two sources disagree: search again, or mark the fact Unknown or Needs Review. LangGraph models these decisions as explicit nodes and conditional edges, so every branch is visible and testable, and its shared state lets each fact carry its value, status and source through the whole run. Unioptt's backend is already Python, so the agent can later become a module there.

n8n would be faster for the trigger and delivery, but loops with per-fact state and verification rules are hard to read and test on a visual canvas. So n8n only wraps the agent: form trigger → call the agent's API → Telegram delivery and Airtable run log. No research logic lives in n8n.

Full reasoning: [stack_decision.md](stack_decision.md) 

## 6. Architecture

```mermaid
flowchart TD
    A["1 · Input<br/>programme + intake + profile"] --> B["2 · Find pages<br/>follow saved official links first,<br/>then search (Tavily, university site only)"]
    B --> C["3 · Read pages<br/>(Jina Reader, keep final URL)"]
    C --> D["4 · Extract facts + quotes + all options<br/>(LLM) — Python decides: complete?<br/>which year? which link to follow?"]
    D --> E["5 · Four verification checks<br/>(Python, no AI)"]
    E --> F{"6 · Fact missing or incomplete<br/>and rounds left (max 4)?"}
    F -- "yes: follow links / search again" --> B
    F -- "no" --> U["Never found → Unknown"]
    U --> G["7 · Country rules & scholarships<br/>(Pinecone RAG, quotes checked)"]
    G --> H["8 · Total cost in EUR + TRY<br/>(RAG living costs, ECB rate)"]
    H --> I["9 · Readiness & gaps<br/>(rules: met / gap / check)"]
    I --> J["10 · Report (Markdown) + JSON<br/>assembled by Python, no AI"]
```

Code: [src/graph.py](src/graph.py) (the 10 nodes and the loop) · [src/extract.py](src/extract.py) (LLM extraction) · [src/verify.py](src/verify.py) (the four checks) · [src/country_rules.py](src/country_rules.py) · [src/costs.py](src/costs.py) · [src/readiness.py](src/readiness.py) · [src/report.py](src/report.py) · [api.py](api.py) (web API for n8n).

**The core principle: the AI proposes, Python decides.** The LLM only reads pages and proposes facts with quotes. Plain Python decides whether a fact is complete, which academic year a page is for, which link to follow next, which version of a fact wins, and its final status. Every time testing showed the LLM was inconsistent, a Python rule took over that decision.

## 7. Verification rules

The agent uses Unioptt's existing four-state vocabulary. **Python code decides the status, not the LLM.**

| Status | When the agent uses it |
|---|---|
| **Verified** | All four checks pass: (1) the source is the university's own website or an official application portal; (2) the quoted sentence appears word for word in the downloaded page; (3) the value appears in that sentence; (4) the page refers to the target intake (or is not clearly outdated). |
| **Needs Review** | Found on an official page, but a check fails, or two official pages disagree (both links are kept). |
| **Inferred** | From an unofficial source, calculated (e.g. cost in TRY), or a general country rule from the knowledge base applied to this programme. |
| **Unknown** | Not found after the allowed number of searches. Never guessed. |

**Extra rules added after testing** (each one fixed a real failure):

| Rule | Why |
|---|---|
| A fact is only **complete** if it gives the concrete answer *for this student* (a score, an amount, the rule for a Turkish diploma). Otherwise the agent follows the page's "more info" link. | The programme page said "equivalent to Dutch VWO"; the real rule (Lise Diploması **+ 4 AP courses**) was two clicks deeper. |
| Pages **two or more years older** than the intake are ignored; last year's pages count but fail check 4. | Search returned a 2015-16 regulations PDF. |
| Only real **academic years** (2027/28) count, not dates like "Last modified: 2026" or Jina's "Published Time". | A footer date was mistaken for the academic year. |
| When versions of a fact compete: **official source > complete > quote really on the page > current year**. | A blog's "B2" replaced the university's own rule; an invented quote replaced a real one. |
| If the LLM forgets a link or skips a line in a quote, **Python finds the link itself** or **asks again**. | Run-to-run variation in the LLM's answers. |
| Every requirement keeps **all options** (all accepted tests, routes, exemptions), each with its own quote. Matching to the student happens only in box 9. | "IELTS 6.5" alone hid the other five accepted tests and the per-section minimums. |

## 8. Tools

| Role | Tool | Notes |
|---|---|---|
| Web search | Tavily | Finds the official programme pages |
| Page → clean text | Jina Reader | Separate provider from search |
| Exchange rates | Frankfurter (ECB data) | Free, no key; EUR → TRY |
| Knowledge base (RAG) | Pinecone | Curated public documents on DE/NL admission, scholarships and Turkish diploma recognition |
| LLM | OpenAI `gpt-4o-mini` | Fact extraction only (structured output); `text-embedding-3-small` for embeddings. The report itself is written by Python. |
| Orchestration | LangGraph | 10 nodes, shared state, conditional loop |
| API | FastAPI | `POST /research` so n8n can start a run |
| Wrapper | n8n | Form trigger → API → Telegram summary + Airtable run log; Telegram alert on failure |

## 9. Report structure

| # | Section | Contents |
|---|---|---|
| 0 | Header | Programme, university, target intake, run date, Unioptt match result (quoted, if given) |
| 1 | Programme snapshot | City, degree, teaching language, duration, mandatory placement, thesis requirement |
| 2 | Key requirements | Language, academic, application platform, deadlines, documents |
| 3 | Total yearly cost | Tuition + living costs in EUR and TRY |
| 4 | Recognition | How a Turkish high-school diploma is treated (YKS, Studienkolleg, YÖK rules) |
| 5 | Scholarships | Which exist; automatic vs apply-required |
| 6 | Readiness & gaps | Profile vs requirements: language, GPA, budget |
| 7 | What's missing & next steps | Unknown / Needs Review facts + 3 concrete actions |
| 8 | Sources & verification log | Every fact: value, status, source link, quote |

Target length: sections 0–7 on about one page; section 8 has no length limit.

## 10. Repository structure

```
├── README.md
├── stack_decision.md            why LangGraph is primary and n8n the helper
├── gtm_future_sprints.md        go-to-market: the next three sprints
├── requirements.txt
├── .env.example                 keys needed (empty values)
├── run.py                       command line: python run.py groningen | tum
├── api.py                       FastAPI: POST /research (used by n8n)
├── src/
│   ├── graph.py                 the LangGraph agent (10 nodes + loop)
│   ├── tools.py                 Tavily search, Jina reader, Frankfurter rate
│   ├── extract.py               LLM fact extraction (structured output)
│   ├── verify.py                the four verification checks
│   ├── rag.py · build_corpus.py RAG library: download, chunk, embed, search (Pinecone)
│   ├── country_rules.py         national rules and scholarships from RAG
│   ├── costs.py                 total cost in EUR and TRY
│   ├── readiness.py             student vs requirements (met / gap / check)
│   ├── report.py                Markdown report + JSON record
│   └── schemas.py               VerificationRecord (Unioptt's field names)
├── corpus/sources.json          the 15 official sources of the RAG library
├── data/                        programmes.json · sample_profile.json (synthetic)
├── reports/                     the two sample reports (.md + .json)
└── n8n/                         exported n8n workflow
```

## 11. Setup & how to run

```bash
conda activate bootcamp-env            # Python 3.11
pip install -r requirements.txt
cp .env.example .env                    # then add your own keys (OpenAI, Tavily, Jina, Pinecone)
python -m src.build_corpus              # download the 15 reference pages (once)
python -m src.rag build                 # chunk, embed and upload them to Pinecone (once)
python run.py groningen                 # writes reports/university-of-groningen_artificial-intelligence.md + .json
python run.py tum --print               # TUM, and show the report in the terminal
```

Self-tests (no API calls): `python -m src.verify` · `python -m src.readiness`

**With n8n:** start the API with `uvicorn api:app --port 8000`, open a tunnel (`ngrok http 8000`), paste the tunnel URL into the HTTP node of [n8n/unioptt_research_wrapper.json](n8n/unioptt_research_wrapper.json), add your Telegram chat ID and Airtable table, then submit the form.

## 12. Sample reports

| Report | Verified | Main findings for the synthetic student (IELTS 7.0, German B1, €12,000 budget) |
|---|---|---|
| [Groningen, BSc Artificial Intelligence](reports/university-of-groningen_artificial-intelligence.md) | 6–7 of 9 | ❌ A Lise Diploması alone is not enough: **4 AP courses** are required (found by following official links to the Turkey page). ❌ Budget gap ≈ **€23,000/year** (≈ ₺1.3M). 🔍 IELTS needs 6.5 in **every** section. |
| [TUM, BSc Informatics](reports/technical-university-of-munich_informatics.md) | 3–5 of 9 | ❌ German-taught: needs about **C1**, student has B1. ❌ Budget gap: TUM now charges non-EU tuition, so "German universities are free" is no longer true. 🔍 Diploma rule for Turkey not found on TUM's pages (Needs Review). |

**Why TUM scores lower — the generalisation test.** No code was written for either university. TUM's site is built differently: ~80,000 characters of menus before the content (now stripped by Python), facts spread over fee and application pages, and generic pages that look relevant. The agent still produced a report, and the checks **flagged weak evidence as Needs Review instead of passing it** — e.g. an invented quote and a fee *payment* deadline offered as the application deadline were both caught by check 2.

**Hand check:** for each report, two Verified facts were checked by hand against the official page.

## 13. Scope & limitations

- **Data:** the student profile is synthetic. No real personal data, no assessment data, no database.
- **Sources:** only public programme pages and public reference documents; robots.txt and site terms are respected.
- **Not legal advice:** information on diploma recognition (YÖK denklik) and visas is reported with its source, not as a legal opinion.
- **Facts, not judgements:** the agent never creates scores, ranks programmes or interprets psychometric data.
- **Agent-verified vs human-verified:** "Verified" here means the agent's automatic checks passed. In Unioptt's backend, `last_verified` currently means a human confirmed the data; a `verified_by` field will be needed when the agent is integrated. A sample of Verified facts is checked by hand for each report.
- **MVP scope:** Germany and the Netherlands only; English-language reports; runs locally; no user accounts or production deployment.
- **Run-to-run variation:** the LLM's answers vary slightly, so two runs can differ by a fact or two. Each report therefore shows its checks, sources and quotes, so a reader can see exactly what was verified.
- **Country rules are paraphrased by the LLM.** Python checks that each quote is real, but not that the paraphrase says no more than the quote (e.g. a scholarship "available for non-EU bachelor students" when the source only names it). The report marks national scholarships "check eligibility for Turkish citizens".
- **Tuition ranges:** when a page lists several fees ("€2,300 or €3,400 per semester"), the agent uses the highest, to stay on the safe side for the budget.
- **RAG library gaps:** the Nuffic "Türkiye" page could not be read (its content sits behind tabs), so the Dutch recognition rule comes from the university's own country page instead.
- **Living costs** are national averages or the official visa minimum (Germany: €11,904/year), not city-specific budgets.

## 14. Next: go-to-market sprints

See [gtm_future_sprints.md](gtm_future_sprints.md).
