from __future__ import annotations

import pytest


def test_chat_completions_basic(client, auth_headers):
    response = client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert data["choices"][0]["finish_reason"] == "stop"
    assert data["usage"]["total_tokens"] > 0
    assert "x_routing_strategy" in data
    assert "x_cost_usd" in data


def test_chat_completions_with_model(client, auth_headers):
    response = client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "deepseek-v3", "messages": [{"role": "user", "content": "Hello"}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "deepseek-v3"


def test_chat_completions_with_routing_headers(client, auth_headers):
    headers = {
        **auth_headers,
        "X-Routing-Strategy": "quality_optimized",
        "X-Industry": "finance",
        "X-Task-Type": "data_analysis",
    }
    response = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={"messages": [{"role": "user", "content": "Analyze this data"}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "x_routing_strategy" in data


def test_chat_completions_stream(client, auth_headers):
    response = client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"messages": [{"role": "user", "content": "Hello"}], "stream": True},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    content = response.text
    assert "data:" in content
    assert "data: [DONE]" in content


def test_chat_completions_no_auth(client):
    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )
    assert response.status_code == 401


def test_chat_completions_invalid_key(client):
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-invalid-key"},
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )
    assert response.status_code == 401


def test_chat_completions_model_override_header(client, auth_headers):
    headers = {**auth_headers, "X-Model-Override": "claude-3-haiku"}
    response = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "claude-3-haiku"
