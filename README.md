# Albert's Marketplace LLM component: group repo

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
| | | |
| | | |
| | | |
| | | |
| CACARIE Robin|rcacarie-png|boss|

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

## Layout

```
docs/
  component.md     the task, the users, the deployment recommendation
  decisions/       one record per decision
prompts/           every prompt, versioned, from L01
evals/             test cases, golden set and results, from L01
src/               the code that calls the model, from L02
```

## Data

Albert's Marketplace's data, and its 120 labelled support tickets, are in the
company repo (link on the course site). They are synthetic or derived from
public datasets; their licence and attribution are stated there.

## Ownership

**No licence is granted for this repository.**
- **The template:** this README, the `docs/` templates and the folder structure
  remain the course author's intellectual property. Do not reuse them outside
  the course.
- **Your work:** what your group writes here belongs to your group.
