"""Ask the help-centre answerer a question of your own, live: the demo command.

    python -m src.ask "Can I return a lipstick I have opened?"
    python -m src.ask                          # interactive: type questions one after another
    python -m src.ask --prompt answer_cot_v1 "..."   # another strategy (default: the deployed few-shot)
    python -m src.ask --injected "Can I return the OZNaturals Retinol Serum after opening it?"

It runs exactly the deployed pipeline (decision 0004): the 3 closest passages
of the help centre (src/retrieve.py), then the few-shot prompt through
src/llm.py, with every rule checked and at most two re-prompts. It prints what
was retrieved, the answer, its citations, and what the question cost.

For beginners — what you need before a live demo
------------------------------------------------
- Your OWN Anthropic key in `.env` (copy `.env.example`); never a teammate's.
- One run done in advance, on the demo machine, with its internet connection:
  the first run downloads the six PDFs and the embedding model (~470 MB).
- A new question costs about $0.002 (few-shot, Claude Haiku 4.5). A question
  already asked with the same passages is answered from cache/ for free.
- These demo calls are logged in cache/demo_calls.csv (not committed), so the
  study's own log, runs/calls.csv, and its figures never change.

A second key, as a back-up
--------------------------
If `.env` also holds ANTHROPIC_API_KEY_FALLBACK, a question refused because
the first key has no credit left or has expired is asked again, at once, with
the second key; the rest of the session keeps using it. The second key can be
an Anthropic key (sk-ant-...) or an OpenRouter key (sk-or-...). It lives only
in `.env`, which Git never commits: never write a key in the code.
`--second-key` uses it from the start (to check it works before the demo).
"""
import argparse     # reads the command-line options
import datetime     # a timestamp for the run id
import os           # reads the keys from the environment (loaded from .env)
import sys

import anthropic    # only to recognise the API's errors and explain them

from src import llm
from src.data import ROOT
from src.retrieve import TOP_K, default_index, is_untrusted

# The strategy we recommend deploying (decision 0004).
DEPLOYED_PROMPT = "answer_few_shot_v1"

# The name of the back-up key's variable in .env.
FALLBACK_VAR = "ANTHROPIC_API_KEY_FALLBACK"
OPENROUTER_URL = "https://openrouter.ai/api"
using_fallback = False      # becomes True once the session has switched to the second key


def key_exhausted(e):
    """True when an API error means the KEY is the problem (no credit left, expired or revoked),
    i.e. when trying again with another key can help. Not for network errors or bad requests."""
    if isinstance(e, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return True                                   # 401 / 403: expired, revoked or blocked key
    if isinstance(e, anthropic.APIStatusError):
        text = str(e).lower()
        # 402: OpenRouter's "insufficient credits"; 400 with "credit": Anthropic's "credit balance is too low".
        return e.status_code == 402 or (e.status_code == 400 and "credit" in text)
    return False


def switch_to_fallback():
    """Replace the API client by one using the second key. Returns False when there is no second key.

    src/llm.py creates its client once, from the first key; here we build the new client ourselves and
    put it in its place (llm._client), so every later call of this session uses the second key.
    """
    global using_fallback
    key = os.environ.get(FALLBACK_VAR, "").strip()
    if not key or using_fallback:
        return False
    # The first key may go through OpenRouter (ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN): remove those
    # settings from this process, or the SDK would send them along with the second key.
    for var in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"):
        os.environ.pop(var, None)
    if key.startswith("sk-or-"):
        # An OpenRouter key: same SDK, OpenRouter's address, the key sent as a bearer token.
        llm._client = anthropic.Anthropic(base_url=OPENROUTER_URL, auth_token=key, max_retries=0)
    else:
        # An Anthropic key: Anthropic's own address.
        llm._client = anthropic.Anthropic(base_url="https://api.anthropic.com", api_key=key, max_retries=0)
    using_fallback = True
    return True


def show_passages(passages):
    """Print the passages found for the question: id, similarity score and the start of the text.

    Seller passages (documents 05 and 06) are marked: the answerer uses them for
    product facts only, never for policies.
    """
    print(f"\n  {len(passages)} passages found (multilingual-e5-small, FAISS, top {TOP_K}):")
    for p in passages:
        tag = "  [seller text, untrusted]" if is_untrusted(p) else ""
        snippet = " ".join(p["text"].split())[:110]
        print(f"   · {p['id']:<28} similarity {p['score']:.2f}{tag}\n     “{snippet}…”")


def show_result(result):
    """Print the answer (or why there is none), its citations, and the cost and time of the question."""
    attempts = result.attempts
    if result.record is None:
        # Every attempt broke a rule: nothing is sent to the customer, and we say why.
        print(f"\n  No answer sent: the model broke a rule {len(attempts)} times ({result.failure}).")
    else:
        rec = result.record
        print(f"\n  Answer: {rec.answer}")
        if rec.answerable:
            print(f"  Sources: {', '.join(rec.citations)}")
        else:
            print("  (The help centre does not answer this: the assistant says so instead of guessing.)")
        if len(attempts) > 1:
            # A re-prompt happened: show which rule the first answer broke (e.g. an invented citation).
            print(f"  Corrected after {len(attempts) - 1} re-prompt(s); first answer refused because: {attempts[0]['error'].replace('Value error, ', '')}")
    cached = all(a["cached"] for a in attempts)
    # Only real calls cost money: answers read from the cache are free.
    paid = [a for a in attempts if not a["cached"]]
    dollars = llm.cost(llm.MODEL, sum(a["input_tokens"] for a in paid), sum(a["output_tokens"] for a in paid))
    if cached:
        print(f"  From the cache: $0.000 (this exact question was already asked) · {llm.MODEL}")
    else:
        print(f"  Cost ${dollars:.4f} · {result.latency_s:.1f} s · {llm.MODEL}, {len(attempts)} call(s)")


def ask(question, index, prompt, use_cache, run_id, injected):
    """Retrieve, answer and print one question. Returns False when the API refused the call."""
    passages = index.search(question, TOP_K)
    show_passages(passages)
    try:
        try:
            result = llm.answer(question, prompt, passages, case_id="live", run_id=run_id, use_cache=use_cache)
        except anthropic.APIStatusError as e:
            # The first key is out of credit or expired: switch to the second key and ask again, once.
            if not (key_exhausted(e) and switch_to_fallback()):
                raise
            print("\n  The first key is out of credit or expired: switching to the second key (.env) and asking again.")
            result = llm.answer(question, prompt, passages, case_id="live", run_id=run_id, use_cache=use_cache)
    except anthropic.AuthenticationError:
        print(f"\n  The API key was refused{' (second key too)' if using_fallback else ''}: check the keys in .env.")
        return False
    except anthropic.APIStatusError as e:
        # A 400 about credits, or a 402, means the key has no money left.
        if e.status_code == 402 or "credit" in str(e).lower():
            print(f"\n  The key has no credit left{' (second key too)' if using_fallback else ''}. Add credit, or set {FALLBACK_VAR} in .env.")
        else:
            print(f"\n  The API answered an error ({e.status_code}): {e}")
        return False
    except anthropic.APIConnectionError:
        print("\n  The API could not be reached (network). Check the connection and ask again.")
        return False
    show_result(result)
    if injected:
        print("  (Run with the course's tampered product page in place of the real one.)")
    return True


def main():
    """Read the options, build the index once, then answer one question or loop on questions."""
    p = argparse.ArgumentParser(description="Ask the help-centre answerer a question, live.")
    p.add_argument("question", nargs="*", help="the question (leave empty for interactive mode)")
    p.add_argument("--prompt", default=DEPLOYED_PROMPT, help=f"prompt file in prompts/ (default {DEPLOYED_PROMPT})")
    p.add_argument("--no-cache", action="store_true", help="always call the API, even for a question already asked")
    p.add_argument("--injected", action="store_true", help="use the course's tampered product page (injection demo)")
    p.add_argument("--second-key", action="store_true", help=f"use {FALLBACK_VAR} from the start (to test it)")
    args = p.parse_args()

    # Demo calls go to their own log in cache/ (not committed): the study's runs/calls.csv stays as it is.
    llm.CALLS = ROOT / "cache" / "demo_calls.csv"
    run_id = f"{datetime.datetime.now():%Y%m%d-%H%M%S}-demo"

    # Load .env now (src/llm.py would do it at the first call) so the keys can be checked up front.
    llm.load_dotenv(ROOT / ".env", override=True)
    has_first = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    if args.second_key or not has_first:
        if switch_to_fallback():
            print(f"Using the second key ({FALLBACK_VAR}).")
        elif args.second_key:
            sys.exit(f"--second-key: {FALLBACK_VAR} is empty in .env.")

    print("Loading the help centre and the embedding model (the first run downloads them)…")
    index = default_index(injected=args.injected)
    print(f"Ready: {len(index.passages)} passages · strategy {args.prompt}")

    if args.question:
        ok = ask(" ".join(args.question), index, args.prompt, not args.no_cache, run_id, args.injected)
        sys.exit(0 if ok else 1)
    # Interactive mode: one question per line; an empty line (or Ctrl+C) quits.
    try:
        while True:
            q = input("\nYour question (empty to quit): ").strip()
            if not q:
                break
            ask(q, index, args.prompt, not args.no_cache, run_id, args.injected)
    except (KeyboardInterrupt, EOFError):
        pass
    print("\nBye.")


if __name__ == "__main__":
    main()
