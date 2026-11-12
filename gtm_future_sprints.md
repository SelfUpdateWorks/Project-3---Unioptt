# Go-to-market: the next three sprints

The agent proves one thing: a programme report where **every fact has a source and a status** can be produced automatically, and its weak spots are visible instead of hidden. The next three sprints turn that into something families, schools and the Unioptt catalogue can use.

| Sprint | Who it serves | What we build | How we reach them | How we measure it |
|---|---|---|---|---|
| **1. Turkish reports + a parent version** | Turkish families (the decision is usually made with parents) | The same report in Turkish, plus a one-page parent summary: total cost in TRY, the 3 main gaps, the deadline | Instagram and WhatsApp groups of Turkish parents | % of reports read to the end · % shared |
| **2. School counsellor pilot** | Counsellors at private high schools in Istanbul and Ankara (the buyer) | Batch reports for a whole class, with each student's profile | A free pilot with 2–3 schools | Counsellor time saved per student · schools that continue after the pilot |
| **3. Catalogue integration** (bridge to the final project) | Unioptt itself: its matching engine and Prepare page | Provenance fields in Supabase; weekly verification runs with human approval before anything goes live | Internal | % of the 94 programmes with a source and verified in the last 90 days |

## Why this order
1. **Families first:** they feel the problem most (agency commissions, unclear costs in TRY) and can be reached cheaply.
2. **Schools second:** one counsellor serves many students, so the pilot tests whether the report saves real advisory time.
3. **Catalogue third:** once reports are trusted, the same verified facts feed Unioptt's matching engine (touchpoint A in the README).

## Risks to watch
- **Trust:** one wrong "Verified" fact can damage trust, so human approval stays in the loop for the catalogue, and Needs Review facts are always shown.
- **Freshness:** requirements change every year, so reports carry their run date and page years, and catalogue facts are re-verified on a schedule.
- **Scope creep into advice:** reports state facts with sources; recognition and visa questions are pointed to the official bodies (not legal advice).
