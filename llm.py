"""
Everything that talks to Gemini lives behind one function: call_gemini().

Two names are kept so the two jobs can be pointed at different models:
- MODEL_MAIN   for question generation and scoring, which happen once per
               dimension.
- MODEL_JUDGE  for the judge, which runs *inside* the follow-up loop (at
               most twice per question) while the candidate waits, so it
               needs to be fast.

Both currently point at gemini-3.5-flash-lite. The judge used to run on
gemini-3.1-flash-lite to give it its own free-tier quota pool, but on voice
calls it took 5-19 s per answer (and returned 503 "overloaded"), against
about 1 s for gemini-3.5-flash-lite on the same test prompt - and that
silence made candidates talk over the agent. The cost of sharing one model
is one shared quota pool; call_gemini() backs off and retries on a 429.

Both are pinned lite-tier models rather than gemini-2.5-flash /
gemini-2.5-flash-lite from the original plan, or the "-latest" aliases:
- gemini-2.5-flash and gemini-2.5-flash-lite are both 404 for this key
  ("no longer available to new users") - confirmed live.
- The "-latest" alias for the full (non-lite) flash tier silently resolved
  to gemini-3.8-flash, a preview-ish model whose free tier is capped at 20
  requests/DAY - confirmed live, and exhausted mid-testing.
- Pinning avoids a model swap happening silently under an alias the night
  before the demo.

MOCK controls whether call_gemini is even reachable. main.py flips it based
on --mock before anything else runs; every module that needs a "did the demo
lose wifi" fallback checks llm.MOCK directly instead of duplicating the flag.
"""

import os
import random
import time

from dotenv import load_dotenv

load_dotenv()

MODEL_MAIN = "gemini-3.5-flash-lite"
MODEL_JUDGE = "gemini-3.5-flash-lite"

MOCK = False  # flipped by main.py when --mock is passed

MAX_RETRIES = 5
BASE_DELAY_SECONDS = 2.0  # free tier is ~10-15 RPM, so backoff needs real weight

_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and fill "
                "it in, or run with --mock."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def call_gemini(model: str, prompt: str, schema):
    """
    Send `prompt` to `model` and parse the response as `schema`.
    `schema` is a pydantic model, or a list of one (e.g. list[Dimension]) -
    Gemini's structured output supports both, and response.parsed mirrors
    whichever shape you asked for.
    Retries with exponential backoff on 429 (rate limited) or 503 (model
    temporarily overloaded - seen live during testing, and transient).
    Never called when MOCK is True - callers branch on llm.MOCK themselves.
    """
    from google.genai import types

    client = _get_client()
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
    )

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model, contents=prompt, config=config
            )
            return response.parsed
        except Exception as e:
            last_error = e
            msg = str(e)
            is_retryable = any(
                marker in msg
                for marker in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")
            )
            if not is_retryable:
                raise
            delay = BASE_DELAY_SECONDS * (2 ** attempt) + random.uniform(0, 1)
            print(f"  [{msg[:60]}... retrying in {delay:.1f}s]")
            time.sleep(delay)

    raise RuntimeError(f"Gemini call failed after {MAX_RETRIES} retries: {last_error}")
