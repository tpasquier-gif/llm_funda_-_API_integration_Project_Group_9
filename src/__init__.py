"""Albert's Marketplace help-centre answerer (LLM Fundamentals, group 9).

This file marks the `src/` folder as a Python *package*: it is what lets the
other files write `from src.data import ...` or `from src import llm`.
It is intentionally almost empty.

How the package fits together (read the files in this order):

    src/data.py      1. download the six PDFs of the help centre and check they are the right ones
    src/retrieve.py  2. cut them into passages, turn the passages into vectors, search them (the "R" of RAG)
    src/prompts.py   3. load the prompt templates written in prompts/*.md
    src/schema.py    4. describe the answer we expect back, and the safety rules it must obey
    src/llm.py       5. the only file that talks to the Claude API: asks, checks, re-asks (the "G" of RAG)
"""
