# DeepDive — development log

Running record of what was built, what broke, and how it was fixed.
Newest entries at the top. The point of this file is that six weeks
from now (or in an interview) you can reconstruct *why* the code looks
the way it does, not just *what* it does.

Format per entry: **What / Why it happened / Fix / Takeaway.**

---

---

---

## 2026-09-25 — batch evaluation harness, and a reliability problem it exposed

### Built

- **`eval_planner.py`** — runs the planner over a set of queries in one
  go and writes a timestamped markdown report to `reports/` (gitignored)
  as well as printing to screen.

  Written instead of a chat UI. The thing being evaluated in Week 1 is
  whether the *prompt* is good, and that judgement comes from reading
  many outputs together and spotting patterns — not from one pretty
  result at a time. A UI optimises for a single interaction; this
  optimises for comparison. The UI stays a Week 4 serving concern.

  The default query set is deliberately unkind: two equity funds, a debt
  fund, a stock, a plausible-but-fake fund name, and gibberish. Easy
  input tells you nothing.

- **`tests/test_planner.py` restructured** into three parts — reference
  tests, one fully worked exercise, then scaffolds with `# TODO` blanks.
  The previous version stated exercises as prose specs, which assumed
  pytest familiarity that wasn't there. Specs are not teaching material.

### Issue #10 — no retry on transient API failures

**What.** First batch run: **2 of 6 queries failed**, both with

```
GoogleAPIError: 503 UNAVAILABLE. This model is currently experiencing
high demand. Spikes in demand are usually temporary. Please try again
later.
```

They failed after **45s and 49s** — the client waits a long time before
giving up. The other four succeeded in 5–15s.

**Why single-query testing never showed this.** `run_planner.py` makes
one call. At a ~30% transient failure rate you would mostly see it work
and occasionally see a crash you'd write off as bad luck. Running six at
once turns an anecdote into a number.

**Why it gets worse, not better.** The Week 2 researcher will make
roughly one call per sub-question — call it 5 per run. At this failure
rate, the chance of at least one failure in a run goes from ~30% to
~83%. A pipeline with no retry becomes unusable exactly when it gets
more useful.

**Partial mitigation already in place.** `eval_planner.py` wraps each
query in try/except so one failure can't kill the batch, and records the
failure in the report. That is error *containment*, not error handling —
the query still produced nothing.

**Not yet fixed.** Wants a retry with exponential backoff around the LLM
call, and a decision about what a node should return when its model is
unreachable after N attempts. `langchain-core` has
`Runnable.with_retry(...)`, which is likely the smallest correct change
and belongs in `app/llm.py` so every agent inherits it.

**Status:** open. Exercise C in `tests/test_planner.py` pins down the
current behaviour (the error propagates and kills the run) so the change
can be made deliberately rather than by drift.

**Takeaway.** Any network call you make more than once needs a retry
policy, and "how often does this actually fail?" is a question you can
only answer by running it in bulk. Build the batch runner early — it is
cheap, and it converts intuitions into measurements.

### Also re-confirmed

Issue #9 (planner invents plans for nonexistent input) got *worse* under
scrutiny: given `asdfgh qwerty zxcvb` the planner now interpolates the
gibberish directly into each question — "annualized returns for asdfgh
qwerty zxcvb compared to its primary benchmark". Still open, assigned as
Part B in `tests/EXERCISES.md`.

## 2026-09-13 — Week 1 signed off: venv, offline test suite, one real gap found

### Built

- **`.venv/`** — DeepDive finally has its own virtualenv, closing
  issue #4. Installed from `requirements.txt` alone, which is what
  turned up issue #8 below.
- **`tests/`** — a pytest suite that makes **zero API calls** and runs
  in ~5s. `tests/conftest.py` has a `FakeChatModel` implementing only
  `with_structured_output(schema) -> object with .invoke()`, which is
  the entire contract the planner depends on.
- **`pytest.ini`** — `pythonpath = .` so tests can `import app...`
  without an editable install.
- **Dependency injection** — `build_planner_node(llm=None)` and
  `build_graph(planner_llm=None)`. Production passes nothing; tests
  pass the fake.
- **`test_planner.py` renamed to `run_planner.py`.** It was never a
  test — it is a CLI that makes a live API call. Left as
  `test_planner.py` it would have been collected by pytest *and*
  collided with the real `tests/test_planner.py` (duplicate module
  basename, a classic pytest import error).
- **`tests/EXERCISES.md`** — specs for 5 unwritten tests and one real
  bug fix, to be implemented by hand rather than generated.

### Verified

`pytest -v` → 2 passed, 5 skipped (the exercises), no network.

Planner quality across four query types, all adapting with **no
branching logic in the code**:

| Query | Adapted by asking about | Verdict |
|---|---|---|
| HDFC Flexi Cap Fund | benchmark-relative returns, Sharpe, std dev | good |
| TATAMOTORS (equity) | P/E, EV/EBITDA, net debt, JLR | good |
| Parag Parikh Flexi Cap | foreign-equity allocation + regulatory limits | good |
| SBI Magnum Gilt (debt) | Macaulay duration, avg maturity, RBI sensitivity | good |

The gilt fund is the strongest result: nothing in the prompt mentions
debt funds, yet it produced duration and rate-sensitivity questions,
which are the *correct* domain questions for that asset class and
meaningless for an equity fund.

---

### Issue #8 — `pydantic` was imported but never declared

**What.** `app/planner.py:10` does `from pydantic import BaseModel,
Field`, but `requirements.txt` never listed pydantic.

**Why it happened.** pydantic arrives as a transitive dependency of
`langchain-core`, so it was always importable and nothing ever failed.
Running in the shared course venv hid it completely — the fresh venv
is the only reason it surfaced.

**Why it matters.** The dependency was real but undeclared. If
langchain-core ever dropped or loosened its pydantic pin, DeepDive
would break for a reason nothing in its own requirements explained.

**Fix.** Declared it: `pydantic>=2.13,<3`.

**Takeaway.** **Anything you `import` directly, you declare** — even if
something else already installs it. And you only find these in a clean
environment, which is the real argument for a per-project venv.

---

### Issue #9 — the planner invents a research plan for input that does not exist

**What.** Given deliberate gibberish, the planner returned a confident,
well-formed, entirely generic plan:

```
$ python run_planner.py "asdfgh qwerty zxcvb"
1. What has driven the recent 3-year and 5-year annualized returns of
   the target asset relative to its benchmark?
2. How does the expense ratio or management fee structure of this asset
   compare with its category peer average?
```

Note "the target asset" and "this asset" — the model had no idea what
it was planning for and said so only by omission.

**Why it happens.** `PlannerOutput` has exactly one field, `subtasks:
List[str]`, so "I don't recognise this input" is **not a representable
answer**. Constrained decoding forces a list of sub-questions, so the
model produces the most plausible list it can. The schema that makes
the planner reliable also makes refusal impossible.

That is the real lesson: a structured-output schema doesn't just shape
the answer, it bounds the space of answers — including the ones you
needed.

**Why it is not yet fixed.** Nothing downstream would catch it either:
the Week 2 researcher would search for a nonexistent asset, the Week 3
critic would score whatever prose came back, and DeepDive would emit a
cited-looking report about nothing. A silent failure, which is the
worst kind. Fixing it needs a decision about *where* validation lives
and what the graph does about it — the first real `add_conditional_edges`
in the project.

**Status:** open, assigned as exercise 6 in `tests/EXERCISES.md`.

**Takeaway.** When designing an output schema, ask what the model
should do when the honest answer is "none of the above" — and make sure
the schema can express it.

## 2026-08-31 — Week 1 closed out: planner verified end to end

### Built

- `app/llm.py` **(new)** — single factory for the Gemini client.
  Previously `planner.py` constructed its own `ChatGoogleGenerativeAI`.
  With three agents coming (planner, researcher, critic), the model
  name would have been hardcoded in three places. Now it's one.
- `app/graph.py` **(new)** — `build_graph()` compiles
  `START -> planner -> END`. Every entry point (CLI now, FastAPI in
  Week 4) goes through this one function so they can't drift apart.
- `run_planner.py` **(new)** — CLI smoke test.
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

### Issue #4 — running inside the wrong virtualenv (RESOLVED 2026-09-13)

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
python run_planner.py "HDFC Flexi Cap Fund"   # must still pass
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

---

### Issue #6 — private working notes got committed and pushed to a public repo

**What.** `PROJECT_CONTEXT.md` — personal planning notes, not code —
was committed in the first commit and pushed. It was public for a
short window before being caught.

**Why it happened.** It sat in the project root next to the source, so
`git add -A` swept it up with everything else. `.gitignore` covered
`.env` and `__pycache__` — the *obvious* secrets — but nothing had
asked the broader question: which files here are for me, and which are
for the public?

**Fix.** Three parts, and all three are needed:

```bash
# 1. stop tracking it, but keep it on disk
git rm --cached PROJECT_CONTEXT.md

# 2. make it un-committable by accident
echo "PROJECT_CONTEXT.md" >> .gitignore

# 3. erase it from every commit that ever contained it
git filter-branch -f --index-filter   'git rm --cached --ignore-unmatch -q PROJECT_CONTEXT.md'   --prune-empty -- --all
git reflog expire --expire=now --all && git gc --prune=now
```

Then `git push --force-with-lease`. Verified with
`git log --all --oneline -- PROJECT_CONTEXT.md` returning nothing.

**Why step 3 is not optional.** Deleting a file in a *new* commit
leaves every previous commit intact — the content stays one
`git show <old-sha>:<file>` away, forever. A deletion commit is not a
removal; it is an announcement of where to look.

**Why `--force-with-lease` over `--force`.** It refuses the push if
the remote moved since your last fetch, so you can't silently
overwrite work you haven't seen. Plain `--force` overwrites
unconditionally. Prefer the lease every time.

**Takeaway.** Write `.gitignore` *before* the first commit, and think
about it as two categories, not one: **secrets** (keys, `.env`) and
**private-but-not-secret** (planning notes, scratch files, personal
TODOs). The second category is the one that gets missed, because
nothing about it looks dangerous.

---

### Issue #7 — `git pull` after a history rewrite tried to resurrect the purged file

**What.** After the force-push in issue #6, a `git pull` was run. It
left the repo mid-merge with conflicts in `DEVLOG.md` and `README.md`,
and — much worse — `PROJECT_CONTEXT.md` staged as added again:

```
$ git status -sb
## main...origin/main
AA DEVLOG.md
A  PROJECT_CONTEXT.md      <-- the file that was just purged
AA README.md
```

**Why it happened.** `git pull` is `git fetch` + `git merge`. The pull
ran while the remote still pointed at the **old, pre-purge** history
(`19d4d6b`), so git did exactly what it was asked: merge that old
branch into the clean one. The old branch still contained
`PROJECT_CONTEXT.md`, and a file that exists on one side of a merge
and not the other is not a conflict — it is an **addition**. Git added
it back silently while flagging only the two genuinely-conflicting
files.

`.gitignore` does not save you here. It only stops *untracked* files
from being added; it has no say over a file arriving through a merge.

**Why committing that merge would have been the real damage.** The
merge commit would have listed `19d4d6b` as a parent. That single
pointer makes every purged commit reachable again — so the file would
come back *and* the whole history the rewrite deleted would be
relinked. The force-push would have been undone by a merge.

**Fix.** Nothing in the merge was wanted; it only carried the old
version:

```bash
cp PROJECT_CONTEXT.md /tmp/backup      # abort deletes it - it is not in HEAD
git merge --abort                      # back to clean HEAD, conflicts gone
cp /tmp/backup PROJECT_CONTEXT.md      # restore as a local, ignored file

git reflog expire --expire=now --all   # drop the dangling old commits
git gc --prune=now                     # so nothing can re-merge them
```

Then verified rather than assumed:

```bash
git log --all --oneline -- PROJECT_CONTEXT.md   # empty
git rev-parse main origin/main                  # identical - nothing to push
```

**Takeaway.** After rewriting history, **never `git pull`** — your
local branch is the source of truth and the remote is the thing that
is wrong. `pull` merges the remote *into* you, which is backwards.
Push, and if you must sync afterwards use
`git fetch && git reset --hard origin/main`.

Also: `git merge --abort` restores the working tree to HEAD, so any
file that only exists because of the merge is deleted. Back up before
aborting if the file matters locally.

### Repo set up

- `git init -b main`, two commits (code, then docs) rather than one
  "initial commit" blob — the history should read as work, not a dump.
- `.gitignore` covers `.env`, `__pycache__`, venvs, editor dirs.
  Confirmed with `git check-ignore -v .env` before committing, not
  assumed.
- Remote: `https://github.com/Lalit-Kishore/deepdive-research-agent.git`,
  public. Pushed, then force-pushed once to drop issue #6.
- `LalitKishore22` retired; the Lalit-Kishore identity is now set
  in `--global` config, so new repos get it by default and the
  repo-local override was removed as redundant.

## 2026-07-28 — Week 1 started

Created `app/state.py` (full `ResearchState` shape defined upfront —
`query`, `plan`, `findings`, `draft`, `critique`, `iteration` — even
though Week 1 only uses two fields, so later agents slot in without a
schema rewrite) and `app/planner.py` (`PlannerOutput` Pydantic model +
the system prompt that teaches the model what a researchable
sub-question looks like). Not run at this point.
