# Albert's Marketplace LLM component: group 9

**Our component: a help-centre answerer with retrieval** (deployment recommendation and all figures: [`docs/component.md`](docs/component.md); oral preparation: [`docs/defence-notes.md`](docs/defence-notes.md); **slides: [`slides/`](slides/)**). It answers a customer's
question from the company's help centre, cites the passages it used, says
"I don't know" when the help centre does not say, and never repeats what a
seller's page claims about policies.

This repository is your group's LLM component for **Albert's Marketplace**, the
fictional European beauty marketplace of the LLM Fundamentals, Prompting & API
Integration course (MSA-DATI07-08, Albert School).

It starts almost empty. Every lesson adds a layer on top of the previous one. By
the end of the course it holds the component your group defends orally: one of
- a prompt-driven **classifier** (support tickets)
- a **structured-extraction** tool (product reviews)
- a **retrieval** layer that answers from the company's own documents

with reproducible code, a comparison of prompting strategies on 30 test cases,
an evaluation report, prompt-injection guardrails and a cost per 1,000 calls.

## Team

| Name | GitHub | Role |
|---|---|---|
| CHOLET Philomène | [@Philomenechlt](https://github.com/Philomenechlt) | Clown |
| HERVY Lélia | [@lhervy](https://github.com/lhervy) | BOSS'BOSS'BOSS |
| PASQUIER--GUILARD Thomas | [@tpasquier-gif](https://github.com/tpasquier-gif) | Boss' Boss |
| SIMOND-CHARBINAT Inès | [@ins64](https://github.com/ins64) | to be defined |
| CACARIE Robin | [@rcacarie-png](https://github.com/rcacarie-png) | boss |

## How this repo grows

| Lesson | What your group adds | Where |
|---|---|---|
| L01 · Tokens and prompting | The business task your component serves, a first prompt, its first 10 test cases | `docs/component.md`, `prompts/`, `evals/` |
| L02 · API and structured outputs | Calls through the API with retries and validated output; how keys are handled | `src/`, `requirements.txt` |
| L03 · Retrieval-augmented generation | Retrieval, if your task needs it, **or a decision record saying why not** | `src/`, `docs/decisions/` |
| L04 · Evaluation, cost and guardrails | The evaluation report: golden set, rubric, 30 cases × 3 strategies, failure modes, cost per 1,000 calls, an injection test that must refuse | `evals/`, `docs/` |
| L05 · Review | Project clinic: what the defence will ask | |
| L06 · Project defences | The deployment recommendation you defend | `docs/component.md` |

Starter files for later lessons arrive as **pull requests** opened by the
teaching team. Review and merge them like any other change.

## How we work

- **Every change goes through a pull request,** reviewed by another member
  before it reaches `main`.
- **One decision, one record** in `docs/decisions/`: a prompt pattern, a model,
  a schema, a retrieval setting. Every member writes at least one. At the oral
  defence, each of you defends a choice unprepared.
- **The commit history is graded.** Commit in small steps, with messages that
  say why.
- **A prompt is code.** It lives in `prompts/`, under version control, and a
  change to it is measured on the test cases before it is merged.
- **Every figure says where it came from:** the model, the date, the
  parameters and the test file. A model does not give the same answer twice.

## Your API key

**Each of you has your own Anthropic key, with a spending limit.** It is
personal: it never goes in this repository, in a notebook, in a screenshot or in
a chat message.

- Keep it in a `.env` file, which `.gitignore` already excludes, and copy the
  variable names from `.env.example`.
- **If a key reaches GitHub, even for a minute, tell the teaching team at once**
  so it can be revoked. Deleting the commit does not help: the key has already
  been copied.

### Key handling, for a new member (five lines)

1. Your key is yours: copy `.env.example` to `.env` next to it and paste your key after `ANTHROPIC_API_KEY=` (an OpenRouter key: the two `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` lines instead).
2. `.env` never reaches Git: `.gitignore` excludes it, because anything pushed is copied by GitHub, forks and scrapers within minutes.
3. The code never takes a key argument: `src/llm.py` creates the client, which reads the key from the environment.
4. Never paste a key in a notebook, a screenshot, an issue or a chat, and never use a teammate's.
5. If a key is pushed, even for a minute: tell the school coordinator at once so it is revoked. Deleting the commit does not help.

## Run it

Python 3.12, from the repository root:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                      # the guarantees of src/llm.py, on a fake API: free, no key
python -m evals.retrieval_sweep          # chunk size and k, measured: free, no LLM call
python -m evals.run answer --cases 30 --prompts answer_zero_shot_v1 answer_few_shot_v1 answer_cot_v1
python -m evals.run injection --runs 5   # the course's tampered product page
python -m evals.judge runs/*-answer30__*.csv   # faithfulness, scored by claude-opus-5-5
python -m evals.score                    # the tables of docs/component.md, from runs/
```

The whole study cost $1.59 (see `runs/calls.csv`); a second run of the same
requests is answered from `cache/` and costs nothing. The first run downloads
the six PDFs (checked against the release's CHECKSUMS) and the embedding model
(`intfloat/multilingual-e5-small`, ~470 MB, from Hugging Face).

## Layout

```
slides/            the oral presentation (PDF)
docs/
  component.md     the task, the users, the deployment recommendation
  decisions/       one record per decision
prompts/           every prompt, versioned, from L01
evals/             the 30 test questions, the retrieval sweep, the scripts that run, judge and score
runs/              every call (calls.csv), every run's predictions, summary.csv
src/               data.py (the PDFs + checksums), retrieve.py (chunks, embeddings, FAISS), schema.py
                   (the answer and its rules), prompts.py, llm.py (the only API caller)
tests/             the module's guarantees, on a fake API
```

## Data

The company's help centre is release
[`policy-corpus-v1.0.0`](https://github.com/TangoAI-AlbertSchool-Data-Eng-Cloud/albert-marketplace/releases/tag/policy-corpus-v1.0.0)
of the company repo: six PDFs, 31 pages, CC BY-SA 4.0. `src/data.py`
downloads them into `data/` (not committed) and refuses any file whose sha256
differs from the release's CHECKSUMS. The injection test uses the course's
tampered product page (`l03-rag/data/05-product-pages-injected.pdf` in the
course labs, sha256 `4cd2b1ee…69d1`).

## Ownership

**No licence is granted for this repository.**
- **The template:** this README, the `docs/` templates and the folder structure
  remain the course author's intellectual property. Do not reuse them outside
  the course.
- **Your work:** what your group writes here belongs to your group.
