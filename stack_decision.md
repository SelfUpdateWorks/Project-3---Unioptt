Decision

LangGraph is the primary stack. All research, verification and report logic lives there. n8n is a thin helper around it.

I think of it like this: LangGraph is the documented process with clear steps, decision points and an audit trail. n8n is the front desk: it takes the request, hands it to the process, and delivers the result.

Why LangGraph is primary

It can decide to try again. When a fact is missing, the agent goes back and searches again, up to 3 times, and then marks the fact Unknown instead of guessing. This happens through a conditional edge, a fork in the road: after checking the facts, a function decides "search again" or "continue". This loop is what makes it an agent rather than a fixed pipeline.

Every fact keeps its evidence until the end. Each fact carries four things: value, quote, source and status. They live in LangGraph's shared state, which every step reads and updates. Because nothing is lost between steps, every fact in the final report still knows where it came from and how sure we are about it. That is exactly what the report shows the student and their family.

The AI does not get to grade itself. The LLM extracts a fact and the sentence it came from. Then plain Python code (no AI) checks it: is there a source URL, does the quote really appear on the page, does the value appear in the quote? A fact only becomes Verified if every check passes. If the LLM could simply say "this is verified", we'd be back to "faithful ≠ true", the lesson from our RAG labs: an answer can cite a source and still be wrong.

It fits the product it will join. Unioptt's backend is Python/FastAPI, and the report JSON uses the same field names as the programme catalogue. So the agent can later move into the backend as a module without being rewritten, and its results can feed the catalogue directly.

Why not n8n as the main tool

I have built several n8n workflows in this bootcamp (a RAG chatbot and a Telegram → Airtable workflow), and n8n is great at triggers, credentials and delivery. But I tried to imagine this agent on the canvas: 8 facts, each with up to 3 search attempts, each attempt with its own check. That would mean loop nodes, IF nodes and Code nodes for every branch, and a canvas where it is hard to see which fact failed and why. The verification rules would be spread across many small boxes instead of one readable, testable file. For this problem, the logic matters more than the integrations, so it belongs in code.

What n8n does instead

n8n handles everything around the agent. A form starts the run, n8n calls the agent's API, and then it delivers the report via Telegram, logs each run in Airtable, and sends me an alert if something fails. No research logic lives in n8n.

Trade-offs
More code to own. In n8n I can see the whole flow at a glance. In LangGraph I have to read code to understand it, and I am responsible for testing and maintaining it.
A new way of thinking. The idea of shared state, where every step reads and updates the same object, took me time to understand. It felt abstract until I saw a fact pass through the graph with its source still attached.
The terminal and environment. Working in the terminal, managing my conda environment and keeping API keys safe in .env cost me more time than building in n8n would have.
One extra piece. For n8n to call the agent, I need a small API (Day 4). It is one more thing to build and test.

I accept these costs because the core of this project is verification, and verification needs logic I can read, test and trust.