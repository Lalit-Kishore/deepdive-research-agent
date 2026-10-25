# DeepDive — a multi-agent research agent for technical questions

Ask DeepDive a technical question. It plans the research as a set of
sub-questions, searches the web for each one, writes an answer with
**every claim cited to a source**, has a critic agent check that
answer, and revises it if the critic finds gaps.

Example question:

> *How do I run a Frappe background job only after the current DB
> transaction commits?*

> Built with LangGraph. The headline feature is the **eval**: the agent
> is scored on ~20 real Frappe/Python problems, with the critic switched
> on and off, so the critic's value is a measured number rather than a
> claim.

## Architecture

```
        question
            |
            v
     +-------------+
     |   Planner   |  question -> 3-5 searchable sub-questions
     +-------------+
            |
            v
     +-------------+
     | Researcher  |  per sub-question: Tavily search -> read pages
     +-------------+  -> draft answer with [n] citations
            |
            v
     +-------------+
     |   Critic    |  checks the draft: unsupported claims,
     +-------------+  unanswered sub-questions, weak sources
        |       |
  revise|       | pass  (or iteration cap hit)
        |       |
        +-------+--> final cited answer
       back to
      Researcher
```

All three agents read and write **one shared LangGraph state object**
(`app/state.py`). That shared state is what lets the critic see the
researcher's draft and hand it back with feedback attached — a plain
linear chain cannot express that loop.

## Evaluation

The eval is what this project is for. A research agent that *looks*
good on one demo question says nothing; a score across a fixed
question set does.

- **Question set** — ~20 Frappe/ERPNext and Python problems that were
  actually solved at work, each with a known-correct answer and the
  key points a good answer must contain.
- **Two runs** — the same questions with the **critic on** and
  **critic off**, so the critic's contribution is isolated.
- **Scored on** — correctness against the known answer, citation
  coverage (share of claims backed by a source), and cost (search
  calls, tokens).
- **Reproducible** — one script, fixed question set, results written
  to `reports/`.

Results land here when v1 ships.

## Status

| Sprint week | Scope | State |
|---|---|---|
| 1 | Spec rewrite; planner on `gemini-3.6-flash` for general technical questions | **in progress** |
| 2 | Tavily search tool, page reader, researcher agent | not started |
| 3 | Critic agent + conditional loop-back edge | not started |
| 4 | Eval script + score, demo, ship v1 | not started |

The planner, shared state, graph skeleton and offline test suite
already exist from the earlier version of this project. The planner's
prompt is still tuned for its old domain and is the next thing to
change.

> **History.** DeepDive started as a mutual-fund / stock research tool.
> That version is preserved on the [`finance-v0`](../../tree/finance-v0)
> branch; `main` is the general research agent.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

copy .env.example .env        # then fill in both keys
```

- Gemini key: <https://aistudio.google.com/apikey>
- Tavily key (free plan, 1 credit per basic search): <https://app.tavily.com>

The model defaults to `gemini-3.6-flash`; override with the
`DEEPDIVE_MODEL` environment variable.

## Run

```bash
python run_planner.py "Why does frappe.db.commit inside a doc hook cause partial saves?"
```

Prints the planner's sub-questions. The full pipeline gets its own
entry point (`run.py`) once the researcher exists.

```bash
python eval_planner.py              # built-in query set
python eval_planner.py queries.txt  # your own, one per line
```

Batch-runs the planner and writes a timestamped report to `reports/`.
Prompt quality is judged by reading many outputs side by side.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

The suite injects a fake model, so it makes **no API calls** and needs
no key. Skipped tests are hand-written exercises; see
`tests/EXERCISES.md`.

## Layout

```
deepdive/
├── app/
│   ├── state.py      ResearchState — the shared state schema
│   ├── llm.py        one place the Gemini model is configured
│   ├── planner.py    planner agent: question -> sub-questions
│   └── graph.py      wires nodes into the StateGraph
├── run_planner.py    CLI: run the graph on one question, print the plan
├── eval_planner.py   batch-run many questions, write a report to reports/
├── tests/            pytest suite — runs offline, no API key needed
├── THEORY.md         the concepts behind each thing built here
└── DEVLOG.md         running log of issues hit and how they were fixed
```

## Why these choices

- **LangGraph over plain LangChain** — the critic needs a conditional
  edge that routes a weak draft *backwards*. Linear chains can't.
- **Pydantic + `with_structured_output`** — agents return typed data
  (a real `List[str]` of sub-questions), not free text scraped with regex.
- **Tavily for search** — returns cleaned page content built for LLM
  consumption, with a free tier. Calls are kept lean: one basic search
  per sub-question.
- **Critic as a separate agent** — and measured on/off in the eval, so
  it has to earn its extra tokens.
