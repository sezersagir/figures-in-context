"""One thin layer per provider. All of them return the same result dict.

ask(target, system, text, schema=None, context=None) -> {
    "text": str, "tokens_in": int, "tokens_out": int, "stop_reason": str, "attempts": int
}

target is an entry from config/run.json, e.g. {"provider": "openai", "model": "gpt-5"}.
schema (JSON Schema) forces a JSON answer through the provider's structured output feature.

Standard library only (urllib) on purpose: nothing needs to be installed with pip.
API keys come from the .env file (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY).
"""

import json
import os
import random
import time
import urllib.error
import urllib.request

from . import data
from .data import BASE

KEYS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "google": "GEMINI_API_KEY"}
ENV_FILE = BASE / ".env"
ATTEMPTS = 5
TIMEOUT = 600


class ApiError(Exception):
    pass


def load_env():
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            if value:
                os.environ[name.strip()] = value


load_env()


def api_key(provider):
    name = KEYS[provider]
    value = os.environ.get(name) or (os.environ.get("GOOGLE_API_KEY") if provider == "google" else None)
    if not value:
        raise ApiError(f"No API key for {provider}. Add {name} to the .env file.")
    return value


def model_name(target):
    return f"{target['provider']}:{target['model']}"


def ask(target, system, text, schema=None, context=None):
    provider = target["provider"]
    if provider == "anthropic":
        return _anthropic(target, system, text, schema)
    if provider == "openai":
        return _openai(target, system, text, schema)
    if provider == "google":
        return _google(target, system, text, schema)
    if provider == "test":
        return _test(target, schema, context)
    raise ApiError(f"Unknown provider: {provider}")


def _post(url, headers, body):
    """POST with JSON. Retries on rate limits, overload, server errors and network problems.
    → (response JSON, number of attempts)"""
    payload = json.dumps(body).encode("utf-8")
    for attempt in range(1, ATTEMPTS + 1):
        request = urllib.request.Request(url, data=payload, method="POST",
                                         headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8")), attempt
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")[:500]
            retryable = e.code in (408, 409, 429) or e.code >= 500
            if not retryable or attempt == ATTEMPTS:
                raise ApiError(f"HTTP {e.code}: {text}") from None
            wait = float(e.headers.get("retry-after") or 0) or min(60, 2 ** attempt)
            reason = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == ATTEMPTS:
                raise ApiError(f"No connection: {e}") from None
            wait = min(60, 2 ** attempt)
            reason = "no connection"
        data.report_progress(f"  {reason} from {url.split('/')[2]}, attempt {attempt + 1}/{ATTEMPTS} in {wait:.0f} s")
        time.sleep(wait + random.random())


def _anthropic(target, system, text, schema):
    body = {
        "model": target["model"],
        "max_tokens": 16000,
        "system": system,
        "messages": [{"role": "user", "content": text}],
    }
    if target.get("effort"):
        body["output_config"] = {"effort": target["effort"]}
    if schema:
        body.setdefault("output_config", {})["format"] = {"type": "json_schema", "schema": schema}
    # No fallback to another model on purpose: an answer from a substitute model
    # would distort the measurement of the model under test.
    r, attempts = _post("https://api.anthropic.com/v1/messages",
                        {"x-api-key": api_key("anthropic"), "anthropic-version": "2023-06-01"}, body)
    return {
        "text": "".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text"),
        "tokens_in": r.get("usage", {}).get("input_tokens"),
        "tokens_out": r.get("usage", {}).get("output_tokens"),
        "stop_reason": r.get("stop_reason"),
        "attempts": attempts,
    }


def _openai(target, system, text, schema):
    body = {"model": target["model"], "instructions": system, "input": text}
    if target.get("effort"):
        body["reasoning"] = {"effort": target["effort"]}
    if schema:
        body["text"] = {"format": {"type": "json_schema", "name": "verdict", "schema": schema, "strict": True}}
    r, attempts = _post("https://api.openai.com/v1/responses",
                        {"Authorization": f"Bearer {api_key('openai')}"}, body)
    parts = [c.get("text", "") for item in r.get("output", []) if item.get("type") == "message"
             for c in item.get("content", []) if c.get("type") == "output_text"]
    usage = r.get("usage") or {}
    return {
        "text": "".join(parts),
        "tokens_in": usage.get("input_tokens"),
        "tokens_out": usage.get("output_tokens"),
        "stop_reason": r.get("status"),
        "attempts": attempts,
    }


def _google(target, system, text, schema):
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
    }
    if schema:
        body["generationConfig"] = {"responseMimeType": "application/json", "responseJsonSchema": schema}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target['model']}:generateContent"
    r, attempts = _post(url, {"x-goog-api-key": api_key("google")}, body)
    candidate = (r.get("candidates") or [{}])[0]
    parts = [p.get("text", "") for p in candidate.get("content", {}).get("parts", []) if not p.get("thought")]
    usage = r.get("usageMetadata") or {}
    return {
        "text": "".join(parts),
        "tokens_in": usage.get("promptTokenCount"),
        "tokens_out": usage.get("candidatesTokenCount"),
        "stop_reason": candidate.get("finishReason"),
        "attempts": attempts,
    }


# --- Test model: rehearses the pipeline without API keys and without cost -------

def _test(target, schema, context):
    rnd = random.Random(json.dumps(context, sort_keys=True, default=str) + target["model"])
    if schema:
        allowed = schema["properties"]["error_types"]["items"]["enum"]
        types = [rnd.choice(allowed)] if rnd.random() < 0.25 else []
        verdict = {
            "flag": bool(types),
            "error_types": types,
            # The test model rolls dice: about one answer in four gets a random error type, so that
            # routing and review have something to do in a test run. Not a real finding.
            "finding": "Test run: random test verdict, not a real finding." if types
                       else "Test run: random test verdict (no error rolled).",
            "evidence": [],
            "confidence": "medium",
        }
        return {"text": json.dumps(verdict), "tokens_in": 0, "tokens_out": 0, "stop_reason": "test", "attempts": 1}

    solution = context["reference_answer"]
    roll = rnd.random() if target["model"] == "random" else 0.0
    if roll < 0.6:
        line = f"RESULT: {solution['value']} {solution['unit']}"
    elif roll < 0.85:
        line = f"RESULT: {solution['value']}1 {solution['unit']}"
    elif roll < 0.95:
        line = f"RESULT: {solution['value']} million {solution['unit']}"
    else:
        line = "The result could not be determined."
    return {"text": "Test run: answer from the test model, no real working.\n\n" + line,
            "tokens_in": 0, "tokens_out": 0, "stop_reason": "test", "attempts": 1}
