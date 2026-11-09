# Unioptt Programme Research Agent

> Project 3 · Ironhack AI Consulting Bootcamp (Berlin) · Approved by instructor
> Status: 🚧 Day 1 of 5

## 1. The problem
<!-- TODAY. 3–4 sentences, your words. Why do Turkish students look abroad
(YKS, private uni costs)? Why is the information they get unreliable
(agency commissions, scattered facts that change every year)?
You already wrote this well in your Slack approval message: rewrite it fresh. -->

## 2. What this agent does
<!-- TODAY. Input → what happens → output, one sentence each.
Input: one programme + a synthetic student profile.
Output: a Programme Due Diligence Report where every key fact has a value,
a status (Verified / Inferred / Unknown) and a source link. -->

## 3. Who the report is for, and what "useful" means
<!-- TODAY. The user = student + family deciding whether to apply.
"Useful" = list the key facts (tuition, deadline, language requirement,
scholarships, yearly cost in TRY) and the rule: unknowns are stated, never guessed.
Mention the two sample programmes: Groningen BSc AI (NL, English-taught)
and TUM Informatik (DE, German-taught), and WHY you chose this contrast. -->

## 4. Stack decision (short version)
<!-- TODAY. 3–5 sentences: LangGraph as primary, n8n as thin helper.
Your key argument: the research has clear stages with branching
(fact missing? sources disagree?), and each fact must carry its source
and status through the whole run. Plus: Unioptt's backend is already Python.
Full reasoning → link to stack_decision.md (we write that next). -->

## 5. Architecture
_Diagram coming Day 1–2._

## 6. Tools
_Coming Day 2: Tavily (search), Jina Reader (page reading), Frankfurter/ECB (EUR→TRY), Pinecone (RAG), OpenAI._

## 7. Setup & how to run
_Coming Day 5._

## 8. Sample reports
_Coming Days 3–4._

## 9. Scope & limitations
<!-- TODAY. Bullet points: synthetic profile only, no real personal data;
public programme data only; recognition/visa info is sourced information,
not legal advice; the agent verifies facts and never creates judgement scores
or interprets psychometric data (that stays in Unioptt's matching engine). -->

## 10. Next: go-to-market sprints
_See [gtm_future_sprints.md](gtm_future_sprints.md) (coming Day 4)._