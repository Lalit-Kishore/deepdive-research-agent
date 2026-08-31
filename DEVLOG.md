# DeepDive — development log

Running record of what was built, what broke, and how it was fixed.
Newest entries at the top. The point of this file is that six weeks
from now (or in an interview) you can reconstruct *why* the code looks
the way it does, not just *what* it does.

Format per entry: **What / Why it happened / Fix / Takeaway.**

---

## 2026-08-31 — Week 1 closed out: planner verified end to end

### Built

- `app/llm.py` **(new)** — single factory for the Gemini client.
  Previously `planner.py` constructed its own `ChatGoogleGenerativeAI`.
  With three agents coming (planner, researcher, critic), the model
  name would have been hardcoded in three places. Now it's one.
- `app/graph.py` **(new)** — `build_graph()` compiles
  `START -> planner -> END`. Every entry point (CLI now, FastAPI in
  Week 4) goes through this one function so they can't drift apart.
- `test_planner.py` **(new)** — CLI smoke test.
- `.gitignore`, `.env.example`, `README.md` **(new)**.
- `requirements.txt` — version floors corrected (see issue #2).

### Verified

Ran against three queries. Output was specific and researchable, and
the planner correctly adapted its framing to the query type — for the
stock ticker it asked about P/E and EV/EBITDA where for the funds it
asked about expense ratio. That generalisation came from the prompt
alone; no ticker/fund branching exists in the code.

| Query | Sub-questions | Judgement |
|---|---|---|
| HDFC Flexi Cap Fund | 4 | specific, all researchable |
| Parag Parikh Flexi Cap Fund | 5 | picked up the fund's foreign-equity angle unprompted |
| TATAMOTORS | 5 | switched to valuation/debt/JLR framing |

---

### Issue #1 — `404 NOT_FOUND` on `gemini-1.5-flash`, then on `gemini-2.0-flash`

**What.** First run of the planner failed:

```
ChatGoogleGenerativeAIError: Error calling model 'gemini-2.0-flash'
(NOT_FOUND): 404 ... This model models/gemini-2.0-flash is no longer
available. Please update your code to use models/gemini-3.6-flash
```

**Why it happened.** The model name was written months ago. Google
retires model IDs on the free API, and a retired ID returns 404 rather
than silently falling back. Hardcoded model strings rot.

**Fix.** Listed what the key can actually reach:

```python
import google.generativeai as genai
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
[m.name for m in genai.list_models()
 if "generateContent" in m.supported_generation_methods]
```

Moved the name into `app/llm.py` as `DEFAULT_MODEL`, overridable with
the `DEEPDIVE_MODEL` env var, and set it to `gemini-3.6-flash`.
`gemini-3.7-flash` is also live if a newer one is wanted later.

**Takeaway.** Read the 404 body — the API named its own replacement.
And a model ID is configuration, not a literal buried in an agent.

---

### Issue #2 — `requirements.txt` floors pointed at a dead major version

**What.** The file asked for `langgraph>=0.2.0` and
`langchain-core>=0.3.0`. Installed and working: langgraph **1.2.9**,
langchain-core **1.5.1**.

**Why it happened.** The floors were written against the 0.x line.
They're satisfied by 1.x today, so nothing broke locally — but a fresh
`pip install` on a machine with an old cache could resolve a 0.x that
this code no longer runs on, and the failure would look unrelated.

**Fix.** Pinned to verified major ranges: `langgraph>=1.2,<2`,
`langchain-core>=1.5,<2`, `langchain-google-genai>=4.3,<5`.

**Takeaway.** A floor that's *too low* is a silent trap. Pin the major
version you actually tested against.

---

### Issue #3 — `UserWarning: sampling parameter(s) temperature will be ignored`

**What.** `get_llm(temperature=0)` warned on every call.

**Why it happened.** Gemini 3.x flash models use fixed sampling and
reject a caller-supplied temperature. The old `temperature=0` was
carried over from the 1.5-era code.

**Fix.** `get_llm()` now defaults `temperature=None` and only forwards
the kwarg when it's explicitly set, so nothing is sent that the model
will reject.

**Takeaway.** Determinism here comes from the *structured output
schema*, not from `temperature=0`. Pydantic constrains the shape; the
temperature was never what made the planner reliable.

---

### Issue #4 — running inside the wrong virtualenv (open, not yet fixed)

**What.** Tracebacks show imports resolving to
`Dev Space\langchain\langchain-academy\lc-academy-env\Lib\site-packages`
— DeepDive is running inside the LangChain Academy course venv.

**Why it happens.** That venv is activated in the shell and DeepDive
has no venv of its own.

**Risk.** DeepDive's real dependency set is invisible. A package that
happens to be installed for the course (`langchain-tavily` already is)
would "work" locally and fail for anyone cloning the repo — including
on the Week 4 deploy.

**Fix (do this before Week 2 tools go in):**

```bash
cd "Dev Space/langchain/deepdive"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python test_planner.py "HDFC Flexi Cap Fund"   # must still pass
```

**Takeaway.** "It runs on my machine" is usually a venv statement.

---

---

### Issue #5 — commits were being authored by the wrong GitHub account

**What.** `git config --global user.email` was
`109962171+LalitKishore22@users.noreply.github.com`, but the repo was
headed for `github.com/Lalit-Kishore`. Checked the GitHub API: these
are two genuinely separate accounts.

| Account | ID | Created | Public repos |
|---|---|---|---|
| LalitKishore22 | 109962171 | 2022-07-25 | 2 |
| Lalit-Kishore | 162315192 | 2024-03-05 | 1 |

**Why it matters.** GitHub attributes a commit to an account by
matching the **author email**, not by who pushed it. Pushing to
Lalit-Kishore while authoring as LalitKishore22 gives you commits that
show a plain name with no avatar, no profile link, and *no square on
the Lalit-Kishore contribution graph*. It fails silently — the push
succeeds and looks fine until you notice the graph stayed empty.

**Fix.** Repo-local identity (global left alone, so other repos are
unaffected):

```bash
git config user.name  "Lalit Kishore C R"
git config user.email "162315192+Lalit-Kishore@users.noreply.github.com"
```

The two existing commits were already authored wrongly, so their
authorship was rewritten with `git filter-branch --env-filter` before
any push. Safe to rewrite here precisely because nothing was pushed
yet — after a push this becomes a force-push that breaks every clone.

**Takeaway.** The `ID+username@users.noreply.github.com` form is the
right email to commit with: it attributes correctly without publishing
your real address in a public git history. Verify attribution with
`git log --pretty=format:"%an <%ae>"` *before* the first push.

---

### Repo set up

- `git init -b main`, two commits (code, then docs) rather than one
  "initial commit" blob — the history should read as work, not a dump.
- `.gitignore` covers `.env`, `__pycache__`, venvs, editor dirs.
  Confirmed with `git check-ignore -v .env` before committing, not
  assumed.
- Remote set to
  `https://github.com/Lalit-Kishore/deepdive-research-agent.git`.
  Not yet pushed — the GitHub repo has to be created first.

## 2026-07-28 — Week 1 started

Created `app/state.py` (full `ResearchState` shape defined upfront —
`query`, `plan`, `findings`, `draft`, `critique`, `iteration` — even
though Week 1 only uses two fields, so later agents slot in without a
schema rewrite) and `app/planner.py` (`PlannerOutput` Pydantic model +
the system prompt that teaches the model what a researchable
sub-question looks like). Not run at this point.
