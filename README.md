# DeepDive — an AI research analyst for mutual funds and stocks

Give DeepDive a fund name or a stock ticker. It plans the research,
answers each sub-question with real tools, drafts a report, critiques
its own draft, revises it if the critique is harsh, and returns a
cited markdown report with a risk-flag section.

> **Not investment advice.** DeepDive produces a research summary with
> sources. Every judgement call stays with the reader.

## Architecture

```
        user query
             |
             v
      +-------------+
      |   Planner   |  query -> 4-5 researchable sub-questions
      +-------------+
             |
             v
      +-------------+
      | Researcher  |  web search + fund/stock data per sub-question
      +-------------+
             |
             v
      +-------------+
      |   Critic    |  scores the draft 1-10, names the gaps
      +-------------+
         |        |
 score < 7|        | score >= 7  (or iteration cap hit)
         |        |
         +--------+--> final report
        back to
       Researcher
```

All three agents read and write **one shared LangGraph state object**
(`app/state.py`). That shared state is what lets the critic see the
researcher's draft and hand it back with feedback attached — a plain
linear chain cannot express that loop.

## Status

| Week | Scope | State |
|---|---|---|
| 1 | Planner agent, shared state, graph skeleton | **done — offline test suite green** |
| 2 | Researcher agent + real tools (web search, `yfinance`, `mfapi.in`) | next |
| 3 | Critic agent + conditional loop-back edge | not started |
| 4 | FastAPI endpoint, HTML frontend, deploy | not started |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

copy .env.example .env        # then paste your Google AI Studio key
```

Get a key at <https://aistudio.google.com/apikey>.

## Run

```bash
python run_planner.py "HDFC Flexi Cap Fund"
python run_planner.py "TATAMOTORS"
```

## Evaluate the planner in bulk

```bash
python eval_planner.py              # built-in query set
python eval_planner.py queries.txt  # your own, one per line
```

Runs many queries in one pass and writes a timestamped report to
`reports/`. Prompt quality is judged by reading many outputs together,
not one at a time.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

The suite injects a fake model, so it makes **no API calls** and needs
no key — a rate limit is not a bug in your graph. Skipped tests are
hand-written exercises; see `tests/EXERCISES.md`.

## Layout

```
deepdive/
├── app/
│   ├── state.py      ResearchState — the shared state schema
│   ├── llm.py        one place the Gemini model is configured
│   ├── planner.py    planner agent: query -> sub-questions
│   └── graph.py      wires nodes into the StateGraph
├── run_planner.py    CLI: run the graph on one query and print the plan
├── eval_planner.py   batch-run many queries, write a report to reports/
├── tests/            pytest suite — runs offline, no API key needed
├── THEORY.md         the concepts behind each thing built here
└── DEVLOG.md         running log of issues hit and how they were fixed
```

## Why these choices

- **LangGraph over plain LangChain** — the critic needs a conditional
  edge that routes a weak draft *backwards*. Linear chains can't.
- **Pydantic + `with_structured_output`** — the planner returns a real
  typed `List[str]`, not free text scraped with regex.
- **Gemini flash** — free tier, fast enough for a multi-node graph.
