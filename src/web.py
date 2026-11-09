"""Ask Albert in a web page: the live demo of the help-centre answerer, on this computer only.

    python -m src.web            # then open http://localhost:8000
    python -m src.web --port 8080

It runs exactly the deployed pipeline, like src/ask.py: the 3 closest passages of
the help centre, then the few-shot prompt through src/llm.py, every rule checked,
at most two re-prompts, and the second key of .env if the first one runs dry.
The page (web/) shows the passages found, the answer, its citations, and what
the question cost.

Two indexes are built at start-up: the real help centre, and the same one with the
course's tampered OZNaturals page, so the injection can be shown live.

Only this computer can reach it (127.0.0.1): the API key in .env is never exposed.
Demo calls are logged in cache/demo_calls.csv, never in the study's runs/calls.csv.
"""
import argparse
import datetime
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import anthropic

from src import ask, llm
from src.data import ROOT
from src.retrieve import TOP_K, default_index, is_untrusted

WEB = ROOT / "web"
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8", ".woff2": "font/woff2", ".svg": "image/svg+xml"}
MAX_QUESTION = 500      # characters: a customer's question, not a document

# One question at a time: the cache, the call log and the key switch are not made for parallel calls.
lock = threading.Lock()
indexes = {}
run_id = f"{datetime.datetime.now():%Y%m%d-%H%M%S}-web"


def answer(question, injected):
    """Retrieve and answer one question; return what the page shows, or an error it can explain."""
    passages = indexes[injected].search(question, TOP_K)
    found = [{"id": p["id"], "score": round(p["score"], 2), "seller": is_untrusted(p),
              "text": " ".join(p["text"].split())[:220]} for p in passages]
    try:
        try:
            result = llm.answer(question, ask.DEPLOYED_PROMPT, passages, case_id="web", run_id=run_id)
        except anthropic.APIStatusError as e:
            # The first key is out of credit or expired: switch to the second key and ask again, once.
            if not (ask.key_exhausted(e) and ask.switch_to_fallback()):
                raise
            result = llm.answer(question, ask.DEPLOYED_PROMPT, passages, case_id="web", run_id=run_id)
    except anthropic.APIConnectionError:
        return {"error": "network", "passages": found}
    except anthropic.APIStatusError as e:
        kind = "credit" if e.status_code == 402 or "credit" in str(e).lower() else "key" if e.status_code in (401, 403) else "api"
        return {"error": kind, "passages": found}

    attempts = result.attempts
    paid = [a for a in attempts if not a["cached"]]
    out = {
        "passages": found,
        "cached": all(a["cached"] for a in attempts),
        "cost": llm.cost(llm.MODEL, sum(a["input_tokens"] for a in paid), sum(a["output_tokens"] for a in paid)),
        "latency": result.latency_s,
        "model": llm.MODEL,
        "prompt": ask.DEPLOYED_PROMPT,
        "injected": injected,
        # A re-prompt happened: which rule the first answer broke (e.g. an invented citation).
        "refused": [a["error"].replace("Value error, ", "") for a in attempts if a["error"]],
    }
    if result.record is None:
        out["given_up"] = result.failure
    else:
        out.update(answer=result.record.answer, answerable=result.record.answerable, citations=result.record.citations)
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass                                    # quiet terminal: questions are logged in cache/

    def send(self, status, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/info":
            return self.send(200, {"model": llm.MODEL, "prompt": ask.DEPLOYED_PROMPT, "passages": len(indexes[False].passages),
                                   "top_k": TOP_K, "fallback": ask.using_fallback})
        # Static files of web/, and nothing outside it.
        name = "index.html" if self.path in ("/", "") else self.path.split("?")[0].lstrip("/")
        f = (WEB / name).resolve()
        if WEB.resolve() not in f.parents or not f.is_file() or f.suffix not in TYPES:
            return self.send(404, {"error": "not_found"})
        self.send(200, f.read_bytes(), TYPES[f.suffix])

    def do_POST(self):
        if self.path != "/api/ask":
            return self.send(404, {"error": "not_found"})
        # Only this page may ask: another site open in the browser cannot spend the key.
        if self.headers.get("X-Ask-Albert") != "1":
            return self.send(403, {"error": "forbidden"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self.send(400, {"error": "bad_request"})
        question = str(body.get("question", "")).strip()[:MAX_QUESTION]
        if not question:
            return self.send(400, {"error": "empty"})
        with lock:
            self.send(200, answer(question, bool(body.get("injected"))))


def main():
    p = argparse.ArgumentParser(description="Ask Albert: the help-centre answerer in a web page (this computer only).")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args()

    llm.CALLS = ROOT / "cache" / "demo_calls.csv"
    llm.load_dotenv(ROOT / ".env", override=True)
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        ask.switch_to_fallback()

    print("Loading the help centre and the embedding model…")
    indexes[False] = default_index()
    indexes[True] = default_index(injected=True)
    print(f"Ready: {len(indexes[False].passages)} passages · {ask.DEPLOYED_PROMPT} · {llm.MODEL}")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Ask Albert is open on http://localhost:{args.port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBye.")


if __name__ == "__main__":
    main()
