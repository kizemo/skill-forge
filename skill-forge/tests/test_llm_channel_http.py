"""P0-2: the HTTP judge channel (Anthropic-compatible endpoint).

The llm-call script on this host needs a MiniMax token that only the
MiniMax app can refresh, so it 401s on a standalone call. The session's
own Anthropic-compatible endpoint (ANTHROPIC_BASE_URL + a key) IS
authenticated and synchronous, and its model pool is layered: the author
of a candidate runs on ANTHROPIC_MODEL, the judge can run on a
DIFFERENT model (e.g. ANTHROPIC_DEFAULT_OPUS_MODEL) — an independent
reviewer, in its own process, with no shared context.
"""
import json
import urllib.error
import urllib.request
import pytest
from scripts._lib.llm_channel import RubricError, make_http_llm_call


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload
        self.status = 200

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _ok(text: str) -> dict:
    return {"content": [{"type": "thinking", "thinking": "hmm 1 2 3"},
                        {"type": "text", "text": text}]}


def test_http_call_returns_none_without_base_url():
    assert make_http_llm_call(base_url=None, api_key="k", model="m") is None


def test_http_call_returns_none_without_api_key():
    assert make_http_llm_call(base_url="https://x", api_key=None, model="m") is None


def test_http_call_returns_none_without_model():
    assert make_http_llm_call(base_url="https://x", api_key="k", model=None) is None


def test_http_call_parses_the_score_from_the_text_block(monkeypatch):
    seen: list[dict] = []

    def fake_urlopen(req, timeout=None):
        seen.append({"url": req.full_url, "body": json.loads(req.data)})
        return _FakeResponse(_ok("0.75"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    fn = make_http_llm_call(base_url="https://api.example/anthropic",
                            api_key="secret", model="judge-model")
    assert fn is not None
    assert fn("the rubric prompt") == pytest.approx(0.75)


def test_http_call_posts_to_the_messages_endpoint_with_the_prompt(monkeypatch):
    seen: list[dict] = []

    def fake_urlopen(req, timeout=None):
        seen.append({"url": req.full_url, "body": json.loads(req.data),
                     "headers": dict(req.headers)})
        return _FakeResponse(_ok("0.5"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    fn = make_http_llm_call(base_url="https://api.example/anthropic",
                            api_key="secret", model="judge-model")
    fn("the rubric prompt")
    assert seen[0]["url"] == "https://api.example/anthropic/v1/messages"
    body = seen[0]["body"]
    assert body["model"] == "judge-model"
    assert body["messages"][0]["content"] == "the rubric prompt"
    assert "secret" in str(seen[0]["headers"])


def test_http_call_ignores_numbers_in_the_thinking_block(monkeypatch):
    """The thinking block carries numbers of its own; only the TEXT block
    is the verdict. A judge that thinks '1 2 3' then answers 0.75 must
    score 0.75, not 3."""
    def fake_urlopen(req, timeout=None):
        return _FakeResponse(_ok("0.75"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    fn = make_http_llm_call(base_url="https://api.example/anthropic",
                            api_key="secret", model="judge-model")
    assert fn("p") == pytest.approx(0.75)


def test_http_call_raises_rubric_error_on_http_failure(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            "https://api.example", 401, "Unauthorized", {}, None
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    fn = make_http_llm_call(base_url="https://api.example/anthropic",
                            api_key="secret", model="judge-model")
    with pytest.raises(RubricError):
        fn("p")


def test_http_call_raises_rubric_error_on_unreadable_answer(monkeypatch):
    def fake_urlopen(req, timeout=None):
        return _FakeResponse({"content": [{"type": "text", "text": "I decline."}]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    fn = make_http_llm_call(base_url="https://api.example/anthropic",
                            api_key="secret", model="judge-model")
    with pytest.raises(RubricError):
        fn("p")


def test_http_call_raises_rubric_error_when_no_text_block(monkeypatch):
    def fake_urlopen(req, timeout=None):
        return _FakeResponse({"content": [{"type": "thinking", "thinking": "0.9"}]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    fn = make_http_llm_call(base_url="https://api.example/anthropic",
                            api_key="secret", model="judge-model")
    with pytest.raises(RubricError):
        fn("p")
