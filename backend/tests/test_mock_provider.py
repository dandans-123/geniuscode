from __future__ import annotations

import pytest
import asyncio

from app.schemas.chat import ChatMessage
from app.services.mock_provider import (
    generate_mock_response,
    generate_mock_stream,
    estimate_tokens,
)


def test_estimate_tokens():
    assert estimate_tokens("hello world") == int(2 * 1.3)
    assert estimate_tokens("one") == int(1 * 1.3)
    assert estimate_tokens("a b c d e f g h i j") == int(10 * 1.3)


def test_generate_mock_response_format():
    messages = [ChatMessage(role="user", content="Hello, how are you?")]
    response = generate_mock_response("gpt-4o", messages)

    assert "id" in response
    assert response["object"] == "chat.completion"
    assert response["model"] == "gpt-4o"
    assert len(response["choices"]) == 1
    assert response["choices"][0]["message"]["role"] == "assistant"
    assert response["choices"][0]["finish_reason"] == "stop"
    assert response["usage"]["prompt_tokens"] > 0
    assert response["usage"]["completion_tokens"] > 0
    assert response["usage"]["total_tokens"] == (
        response["usage"]["prompt_tokens"] + response["usage"]["completion_tokens"]
    )


def test_generate_mock_response_different_models():
    messages = [ChatMessage(role="user", content="test")]
    for model_name in ["gpt-4o", "claude-3.5-sonnet", "deepseek-v3", "claude-3-haiku"]:
        response = generate_mock_response(model_name, messages)
        assert response["model"] == model_name
        assert len(response["choices"][0]["message"]["content"]) > 0


@pytest.mark.asyncio
async def test_generate_mock_stream():
    messages = [ChatMessage(role="user", content="Hello")]
    chunks = []
    async for chunk in generate_mock_stream("gpt-4o", messages):
        chunks.append(chunk)

    assert len(chunks) > 2  # at least some content + final + DONE
    assert chunks[-1] == "data: [DONE]\n\n"
    assert "data:" in chunks[0]


@pytest.mark.asyncio
async def test_stream_chunks_format():
    messages = [ChatMessage(role="user", content="Hello")]
    import json

    chunks = []
    async for chunk in generate_mock_stream("gpt-4o-mini", messages):
        chunks.append(chunk)

    # Parse first content chunk
    first_data = chunks[0].replace("data: ", "").strip()
    parsed = json.loads(first_data)
    assert parsed["object"] == "chat.completion.chunk"
    assert "delta" in parsed["choices"][0]
