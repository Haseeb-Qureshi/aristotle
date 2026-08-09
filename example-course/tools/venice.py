#!/usr/bin/env python3
"""Venice AI client — an OpenAI-compatible endpoint, used by bootstrap's
research sweep to distill sources into a course's `sources/` notes.

Deliberately stdlib-only, like the rest of this repo: Venice speaks plain
OpenAI-shaped JSON over HTTPS, so an SDK buys nothing here. If you would
rather use the official client, it is a drop-in:

    from openai import OpenAI
    client = OpenAI(api_key=os.environ["VENICE_API_KEY"],
                    base_url="https://api.venice.ai/api/v1")

The key is read from the environment, or from a gitignored .env at the
repo root. It is never hardcoded and never logged.

    python3 tools/venice.py --models
    python3 tools/venice.py "explain brew ratio in two sentences"
    python3 tools/venice.py --video https://youtu.be/ID "summarise the argument"

YouTube: a Gemini model on Venice really does ingest the video, but ONLY
through a structured `video_url` content part — see watch(). Pasting the
URL into the text of a message does not work: the model answers from
training data for famous videos and correctly disclaims access for the
rest, which is the worst possible failure mode (confident and wrong).
Most models, including the GLM 5.2 default, reject video outright.

Token budget: these are reasoning models and their thinking counts
against `max_tokens`. A tight cap truncates mid-thought and surfaces the
scratchpad instead of the answer, which reads like the model being
chatty. Leave max_tokens unset, or budget several hundred tokens more
than the answer needs.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://api.venice.ai/api/v1"
DEFAULT_MODEL = "zai-org-glm-5-2"          # GLM 5.2 — text only
VIDEO_MODEL = "gemini-3-6-flash"           # video-capable; see watch()
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
TIMEOUT = 300                              # video ingestion is slow


class VeniceError(RuntimeError):
    """The API refused, or the response was not what we asked for."""


def load_key() -> str:
    """Environment wins; .env is the local-dev fallback."""
    key = os.environ.get("VENICE_API_KEY")
    if not key and ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("VENICE_API_KEY=") and not line.startswith("#"):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not key:
        raise VeniceError(
            "VENICE_API_KEY is not set. Export it, or put it in .env at the "
            "repo root (which is gitignored). See .env.example.")
    return key


def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {load_key()}",
                 "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # surface the API's own message; it never contains the key
        detail = e.read().decode("utf-8", "replace")[:600]
        raise VeniceError(f"HTTP {e.code} from {path}: {detail}") from None
    except urllib.error.URLError as e:
        raise VeniceError(f"could not reach {BASE_URL}: {e.reason}") from None


def list_models() -> list:
    req = urllib.request.Request(
        f"{BASE_URL}/models",
        headers={"Authorization": f"Bearer {load_key()}"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return sorted(m["id"] for m in json.load(r).get("data", []))


def chat(messages, model: str = DEFAULT_MODEL, **kwargs) -> str:
    """One /chat/completions round trip. Returns the assistant's text."""
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    body = _post("/chat/completions",
                 {"model": model, "messages": messages, **kwargs})
    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise VeniceError(
            f"unexpected response shape: {json.dumps(body)[:400]}") from None


def watch(url: str, prompt: str, model: str = VIDEO_MODEL, **kwargs) -> str:
    """Ask a video-capable model about a YouTube video it actually ingests.

    The URL must go in a `video_url` part, not in the text — that is the
    difference between the model watching the video and the model
    recalling it. A nonexistent id fails at the API with HTTP 400 rather
    than being answered, which is how we know the fetch is real.
    """
    content = [{"type": "text", "text": prompt},
               {"type": "video_url", "video_url": {"url": url}}]
    try:
        return chat([{"role": "user", "content": content}],
                    model=model, **kwargs)
    except VeniceError as e:
        msg = str(e)
        if "not supported by this model" in msg:
            raise VeniceError(
                f"{model!r} cannot read video. Use a Gemini model, e.g. "
                f"{VIDEO_MODEL!r}.") from None
        if "invalid argument" in msg.lower():
            raise VeniceError(
                f"Venice could not fetch {url} — check the video exists and "
                "is public (private, deleted, and age-gated videos fail "
                "here rather than being guessed at).") from None
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description="Venice AI chat completion")
    ap.add_argument("prompt", nargs="?", help="the user message")
    ap.add_argument("--model", help=f"default {DEFAULT_MODEL}, "
                                    f"or {VIDEO_MODEL} with --video")
    ap.add_argument("--system", help="optional system message")
    ap.add_argument("--video", metavar="URL", help="a public YouTube URL")
    ap.add_argument("--models", action="store_true", help="list model ids")
    ap.add_argument("--max-tokens", type=int)
    a = ap.parse_args(argv)
    try:
        if a.models:
            print("\n".join(list_models()))
            return 0
        if not a.prompt:
            ap.error("give a prompt, or --models")
        kw = {"max_tokens": a.max_tokens} if a.max_tokens else {}
        if a.video:
            print(watch(a.video, a.prompt, model=a.model or VIDEO_MODEL, **kw))
            return 0
        msgs = ([{"role": "system", "content": a.system}] if a.system else [])
        msgs.append({"role": "user", "content": a.prompt})
        print(chat(msgs, model=a.model or DEFAULT_MODEL, **kw))
        return 0
    except VeniceError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
