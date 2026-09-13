# THEORY — the concepts behind what DeepDive has built so far

Scope: **everything actually in the repo as of Week 1** — shared state,
the graph, structured output, and the planner. Week 2/3 concepts
(tools, ReAct, reflection loops) get a short preview at the end so you
know what you're building toward, but the depth is on what exists.

Read this once end to end. Then, for each section, try the
"check yourself" question without looking. If you can answer those out
loud, you can answer them in an interview.

---

## 0. The one-paragraph version

DeepDive is a **stateful multi-agent graph**. Instead of one giant
prompt that does everything, the work is split into specialised nodes
(plan → research → critique), each a small LLM call with a narrow job.
They coordinate not by passing messages to each other but by reading
and writing **one shared state object**. LangGraph is the runtime that
holds that state, decides which node runs next, and — critically —
allows an edge that points *backwards*, which is what makes
self-correction possible.

Every idea below is an elaboration of that paragraph.

---

## 1. Why a graph and not a chain

### The idea

A **chain** is a fixed pipeline: A → B → C. Whatever comes out of B
goes into C, always, exactly once. LangChain's LCEL (`prompt | llm |
parser`) is this, and for a lot of work it's the right tool.

A **graph** adds two things a chain structurally cannot express:

1. **Conditional routing** — after node B, *decide at runtime* whether
   to go to C or back to A.
2. **Cycles** — the same node can run more than once, with different
   input each time.

DeepDive needs both, for one reason: the critic. When the critic scores
a draft 4/10, the correct next step is to run the researcher *again*
with the critique attached. That's an edge pointing backwards. A chain
has no vocabulary for it. You could fake it with a Python `while` loop
around a chain, and people do — but then the loop logic, the iteration
counter, and the routing condition live in your application code
instead of in the pipeline definition, and you lose what the runtime
gives you for free: per-step state snapshots, streaming, checkpointing,
and resuming a run from the middle.

### The mental model

Think of a **state machine**, or a flowchart that executes.

- **Nodes** are functions. Input: the current state. Output: a dict of
  updates to the state.
- **Edges** are the arrows. Fixed edges always fire; conditional edges
  run a small router function that returns the name of the next node.
- **State** is the single object every node reads and writes.

That's the whole model. LangGraph is not conceptually complicated —
its power is that it makes control flow *data* instead of *code*.

### In our code

[app/graph.py](app/graph.py):

```python
builder = StateGraph(ResearchState)     # the state schema types the graph
builder.add_node("planner", build_planner_node())
builder.add_edge(START, "planner")
builder.add_edge("planner", END)
return builder.compile()
```

`START` and `END` are sentinels, not real nodes — they mark entry and
exit. `compile()` validates the graph (is every node reachable? does
every edge point at a node that exists?) and returns an immutable
runnable. That compile-time validation is why a typo in an edge name
fails at build time instead of three minutes into a run.

Right now the graph is a straight line, which is deliberately
anticlimactic. The shape matters, not the current size: Week 3 adds

```python
builder.add_conditional_edges("critic", route_after_critique,
                              {"revise": "researcher", "done": END})
```

and nothing else about the structure has to change.

> **Check yourself:** Why can't you express DeepDive's critic loop as a
> LangChain chain? What specifically do you lose if you wrap a chain in
> a Python `while` loop instead of using a graph?

---

## 2. Shared state — the actual architectural decision

### The idea

There are two ways to make several agents cooperate.

**Message passing.** Each agent has its own memory and sends messages
to the others. This is how CrewAI and AutoGen conversations work.
Flexible, but the system's "truth" is scattered across N private
histories, and debugging means reading a transcript.

**Shared state.** There is exactly one object. Every agent reads the
fields it needs and writes the fields it owns. This is what LangGraph
does, and what DeepDive uses.

Shared state wins here because the critic's job is *inherently* about
looking at someone else's work. The critic needs the researcher's
draft. With shared state that's `state["draft"]` — no message plumbing,
no protocol. And when the critic writes `state["critique"]`, the
researcher's next run sees it automatically, because it reads the same
object.

The deep version of the point: **shared state turns coordination into a
data-modelling problem instead of a communication problem.** Design the
state schema well and the agents almost wire themselves.

### In our code

[app/state.py](app/state.py):

```python
class ResearchState(TypedDict):
    query: str                 # user input
    plan: List[str]            # planner writes
    findings: Dict[str, str]   # researcher writes
    draft: str                 # researcher writes
    critique: str              # critic writes
    iteration: int             # critic increments — the loop guard
```

Two things worth noticing.

**All six fields were defined in Week 1, when only two are used.** That
was intentional. The state schema is the contract between agents that
don't exist yet; defining it upfront makes adding the researcher "fill
in `findings` and `draft`" rather than "redesign the schema and touch
every node."

**`iteration` is a safety mechanism, not bookkeeping.** A critic that
can always send work back can loop forever, and every loop is a paid
LLM call. The cap (2–3) forces output regardless of score. This is the
single most likely thing an interviewer will poke at, so have the
answer ready: *bounded retries with a hard ceiling, and the last draft
ships with its critique attached rather than being discarded.*

### `TypedDict` vs Pydantic for state — why `TypedDict`

`TypedDict` is a **typing-only** construct. At runtime a `ResearchState`
is just a `dict`; there is no validation and no class instance. It
exists so your editor and type-checker catch `state["quary"]`.

That's the right trade for graph state, because state gets read and
merged on every node transition — you don't want validation overhead on
a hot path for an object your own code produced. LangGraph does support
Pydantic models for state if you want runtime validation; `TypedDict`
is the common default.

Note the contrast with §3: `TypedDict` for *internal* state (trusted,
our own code) and Pydantic for *LLM output* (untrusted, needs
validating). That distinction — **validate at the boundary, trust
inside** — is a genuinely good thing to say in an interview.

### How merging works (the part people get wrong)

A node returns a **partial dict**, not the whole state:

```python
return {"plan": result.subtasks}     # not the full ResearchState
```

LangGraph merges that into the state. The default merge is
**overwrite** — the new value replaces the old one for that key. Keys
you don't return are untouched.

If you want a field to *accumulate* instead of overwrite (appending
findings across several researcher passes, say), you annotate it with a
**reducer**:

```python
from typing import Annotated
import operator

findings: Annotated[Dict[str, str], operator.or_]   # merge dicts
messages: Annotated[list, operator.add]             # append
```

You will hit this in Week 2/3. When the researcher runs a second time
after a critique, should the new findings *replace* the old ones or
*merge into* them? That's a reducer decision, and getting it wrong is a
classic silent bug — the run completes, the output is just quietly
missing half its research.

> **Check yourself:** What happens to `state["query"]` when the planner
> returns `{"plan": [...]}`? What's the default merge strategy, and when
> would you override it with a reducer?

---

## 3. Structured output — how you get typed data out of a text model

### The problem

An LLM emits tokens. You need `List[str]`. The naive fix is asking for
JSON in the prompt and calling `json.loads()`, which fails on markdown
fences, trailing prose, single quotes, and a model that decided to be
chatty. Every regex you add is a bug waiting for a new phrasing.

### How it actually works under the hood

`with_structured_output(PlannerOutput)` is not prompt engineering. The
chain of events is:

1. **Pydantic → JSON Schema.** `PlannerOutput` is converted to a JSON
   Schema document. Your `Field(description=...)` text goes into it.
2. **Schema → the API's tool/function-calling field.** It is sent in a
   dedicated request parameter, not in the prompt text.
3. **Constrained decoding.** The provider restricts the model's token
   sampling so output *must* conform to the schema. Malformed JSON
   isn't rejected after the fact — at the token level it's largely not
   generatable.
4. **Parse and validate.** LangChain parses the response and validates
   it back through Pydantic, so you get a real `PlannerOutput` instance.

This is the same machinery as **tool calling**. "Call this function with
these arguments" and "return an object of this shape" are the same API
primitive. Understanding that pays off in Week 2, when the researcher
starts calling actual tools — you won't be learning a new mechanism,
just pointing the same one at a different target.

### The part people miss: the schema is prompt

```python
class PlannerOutput(BaseModel):
    subtasks: List[str] = Field(
        description=(
            "4 to 5 specific, researchable sub-questions about the "
            "given fund or stock. Cover: recent performance drivers, "
            "cost vs peers, manager/leadership track record, and "
            "concentration or sector risk."
        )
    )
```

That `description` is read by the model. Field names and descriptions
are instructions, and vague ones produce vague output. `subtasks:
List[str]` with no description would still be valid JSON — and useless
content. **The schema controls the shape; the descriptions control the
quality.**

### Where determinism actually comes from

Week 1 originally set `temperature=0` for reproducibility, and Gemini
3.x rejects the parameter outright (DEVLOG issue #3). The planner stayed
reliable anyway — because the reliability was never coming from
temperature. It comes from the schema: the output is *always* a list of
strings, whatever the sampling does. Temperature affects *which* words;
the schema guarantees *what shape*.

Worth being precise, because it's a real distinction:

- **Shape reliability** — guaranteed by the schema.
- **Content reproducibility** — affected by temperature, and never
  fully guaranteed for an LLM.

DeepDive needs the first. It does not need the second.

> **Check yourself:** Where does the JSON Schema get sent — in the
> prompt, or somewhere else? Why is that distinction more than trivia?

---

## 4. The planner — task decomposition as a design pattern

### The idea

The **planner-executor** split is one of the oldest ideas in agent
design — it long predates LLMs (see STRIPS and hierarchical task
networks in classical AI planning). One component decides *what needs
doing*; another does it.

Why not one prompt that researches everything at once? Three reasons,
in increasing order of how good they sound in an interview:

1. **Attention dilutes.** A model asked to research six aspects at once
   does all six shallowly. Ask it one question and its full capacity
   goes there.
2. **Sub-questions are independently checkable.** With a plan you can
   see *which* part of the research failed. Without one you get one
   opaque blob to debug.
3. **The plan is a parallelisation boundary and a caching boundary.**
   Five independent sub-questions can be researched concurrently, and an
   unchanged sub-question's finding can be reused across a revision loop
   instead of re-fetched. Neither is possible without the split.

Point 3 is the one that lands, because it's an engineering answer rather
than an LLM-vibes answer.

### The prompt, read as engineering

[app/planner.py](app/planner.py) does three specific things:

**It gives a worked positive example.**

```
"What has driven HDFC Flexi Cap Fund's returns over the past 3 years?"
```

**It gives a negative example with a reason.**

```
Avoid vague sub-questions like "Is this a good investment?" — that is
not researchable.
```

The reason matters more than the example. "Not researchable" is a
*criterion* the model can generalise from; a bare list of bad examples
only rules out those exact strings.

**It names the axes to cover** — performance, cost, management, risk.
Domain knowledge injected as structure. It's why output comes back
consistently shaped across different funds.

The evidence this works is in the DEVLOG: given `TATAMOTORS` instead of
a fund, the planner dropped "expense ratio" and asked about P/E and
EV/EBITDA — with **zero branching logic in the code**. The prompt taught
a criterion, and the model applied it to a case the prompt never
mentioned. That's the best story you have from Week 1, so remember it
concretely.

### Node construction — why `build_planner_node()` and not `planner_node()`

```python
def build_planner_node():
    llm = get_llm()                       # built once
    structured_llm = llm.with_structured_output(PlannerOutput)

    def planner_node(state: ResearchState) -> dict:
        result = structured_llm.invoke([...])
        return {"plan": result.subtasks}

    return planner_node
```

This is a **closure factory**. The outer function runs once at graph
build time and does the expensive setup — constructing the client,
binding the schema. The inner function runs per invocation and closes
over that already-built client.

If the model were constructed inside `planner_node`, you'd rebuild the
client on every graph run — and in Week 3, on every revision loop. It
also makes testing easy: `build_planner_node()` can take an injected
LLM, so tests pass a fake and never hit the network.

> **Check yourself:** What runs once versus per-invocation in
> `build_planner_node()`, and why does that distinction get *more*
> important once the critic loop exists?

---

## 5. Configuration and secrets

`app/llm.py` exists so the model name lives in exactly one place —
which is precisely the failure mode DEVLOG issue #1 records: a
hardcoded `gemini-1.5-flash` 404'd because the ID had been retired.

```python
DEFAULT_MODEL = os.getenv("DEEPDIVE_MODEL", "gemini-3.6-flash")
```

Env var with a sane default: override without editing code, works with
no configuration at all. The general principle is **anything that varies
per environment is configuration, not a literal** — model names,
timeouts, thresholds, endpoints.

On secrets: `.env` holds the real key and is gitignored; `.env.example`
is committed with placeholders so a cloner knows what to provide.
`load_dotenv()` must run *before* the client is constructed — in
`run_planner.py` that's why the `app.graph` import sits below
`load_dotenv()` with a `# noqa: E402`, a deliberate exception to the
usual imports-at-top rule.

**Never commit a key.** Once pushed it's in git history forever; the fix
is to revoke and reissue, not to delete the file in a later commit.

---

## 6. What's coming — enough to see the shape

**Week 2, the researcher.** A tool-calling agent. Same structured-output
mechanism as §3, pointed at real functions (`web_search`,
`get_fund_nav`). The loop: model emits a tool call → your code runs it →
the result goes back as a message → the model either calls another tool
or answers. That loop is **ReAct** (Reason + Act). Read at least the
paper's abstract; interviewers name it.

**Week 3, the critic.** This is the **reflection** pattern: generate,
evaluate, revise. It works because *evaluating* a draft against criteria
is an easier task than *producing* a perfect one — the same reason code
review catches what the author missed. The critic gets a clean context
containing only the draft and the rubric, unpolluted by the reasoning
that produced the draft.

The subtle failure mode to be ready for: a critic sharing the
generator's blind spots will approve its own bad output. Mitigations are
a rubric with explicit criteria, and a bounded loop so a self-satisfied
critic can't spin. This is genuinely an open problem — saying
"self-critique has real limits, here's how I bounded them" is a much
stronger answer than claiming it solves quality.

---

## 7. Interview questions you should be able to answer now

Practise these out loud. Terse, concrete answers beat complete ones.

1. Why LangGraph rather than LangChain for this?
2. What's in your state object and who writes each field?
3. What stops the critic loop from running forever?
4. How do you get structured data out of an LLM without regex parsing?
5. `TypedDict` or Pydantic for state — which, and why?
6. What happens when two nodes write the same state key?
7. Why decompose into sub-questions instead of one big prompt?
   *(Lead with parallelisation and per-step debuggability.)*
8. How would you evaluate whether this agent is actually any good?
9. What's the cost profile of one run, and where would you cut it?
10. If the LLM returns garbage for one sub-question, what happens to the
    rest of the run?

**8, 9 and 10 have no answers in the code yet.** That's fine at Week 1 —
but they're the questions that separate "I followed a tutorial" from "I
built this." Develop your own answers as you go, and write them into
this file when you have them.

---

## 8. Reading list — short, and in this order

1. **LangGraph docs → "Low Level Concepts"** — state, nodes, edges,
   reducers. The highest-value page for this project.
2. **LangChain docs → "Structured outputs"** — what
   `with_structured_output` compiles down to.
3. **ReAct: Synergizing Reasoning and Acting in Language Models**
   (Yao et al., 2022) — abstract and figure 1 are enough. Week 2.
4. **Reflexion** (Shinn et al., 2023) — the self-critique pattern Week 3
   implements. Skim it.
5. **Pydantic docs → Fields** — `Field(description=...)`, and how models
   become JSON Schema.

Skip anything promising "10 AI agent frameworks compared." Depth in one
framework interviews far better than shallow familiarity with six.
