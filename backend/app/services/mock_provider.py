from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from typing import AsyncIterator

from app.schemas.chat import ChatMessage


MODEL_STYLES = {
    "gpt-4o": {"avg_words": 80, "latency_base": 800, "jitter": 200, "style": "professional"},
    "gpt-4o-mini": {"avg_words": 60, "latency_base": 400, "jitter": 100, "style": "concise"},
    "claude-3.5-sonnet": {"avg_words": 100, "latency_base": 900, "jitter": 250, "style": "thoughtful"},
    "claude-3-haiku": {"avg_words": 40, "latency_base": 300, "jitter": 80, "style": "brief"},
    "deepseek-chat": {"avg_words": 70, "latency_base": 600, "jitter": 150, "style": "technical"},
    "deepseek-reasoner": {"avg_words": 120, "latency_base": 1200, "jitter": 300, "style": "analytical"},
    "qwen-max": {"avg_words": 75, "latency_base": 700, "jitter": 180, "style": "balanced"},
    "ernie-4.0": {"avg_words": 65, "latency_base": 650, "jitter": 160, "style": "formal"},
    "glm-4": {"avg_words": 55, "latency_base": 500, "jitter": 120, "style": "clear"},
    "moonshot-v1": {"avg_words": 50, "latency_base": 450, "jitter": 100, "style": "creative"},
}

RESPONSES = {
    "professional": [
        "Based on my analysis, I can provide you with a comprehensive response. The key factors to consider include the underlying requirements, potential constraints, and optimal approaches. Let me elaborate on the specific aspects that are most relevant to your query.",
        "Thank you for your question. I'd be happy to help with that. From a professional standpoint, there are several important considerations. First, let's establish the context, then we can explore the most effective solutions available.",
    ],
    "concise": [
        "Here's a quick answer: the most efficient approach would be to focus on the core requirements and implement them iteratively. Start with the basics and build from there.",
        "Sure! The short answer is that you'll want to consider both the immediate needs and long-term scalability. I'd recommend starting with a minimal viable approach.",
    ],
    "thoughtful": [
        "That's an interesting question that touches on several important areas. Let me think through this carefully. There are multiple perspectives to consider, and the best approach often depends on specific context and constraints. I'll walk you through my reasoning step by step.",
        "I appreciate the depth of this question. Let me provide a thorough analysis. The situation involves several interconnected factors, and I want to make sure I address each one thoughtfully. Here's how I'd approach this problem from first principles.",
    ],
    "brief": [
        "Got it! Here's the key point: focus on simplicity and clarity. The most effective solution is often the most straightforward one.",
        "Quick answer: Yes, that's definitely achievable. The main thing to keep in mind is maintaining a clean, simple approach.",
    ],
    "technical": [
        "From a technical perspective, this involves several layers of implementation. The architecture should follow established patterns for scalability and maintainability. Let me outline the key technical considerations and recommended implementation strategy.",
        "Looking at this technically, the optimal solution involves careful consideration of performance characteristics, data flow patterns, and system constraints. Here's a structured breakdown of the implementation approach.",
    ],
    "analytical": [
        "Let me analyze this systematically. First, I'll identify the core problem, then examine the available options, evaluate trade-offs, and finally recommend the optimal path forward. Step 1: Understanding the requirements... Step 2: Evaluating alternatives... Step 3: Considering constraints... Based on this analysis, the recommended approach is to prioritize reliability while maintaining flexibility for future changes.",
        "This requires careful analytical reasoning. Let me break it down into components: the fundamental requirements, the technical constraints, and the business objectives. By examining each factor independently and then synthesizing the findings, we can arrive at a well-informed decision. My analysis suggests a phased approach would be most effective.",
    ],
    "balanced": [
        "Good question! Let me provide a balanced perspective. There are pros and cons to consider for each approach. The key is finding the right trade-off between complexity and capability for your specific use case.",
        "I'd recommend considering this from multiple angles. The balanced approach would be to start with a solid foundation and iterate based on real feedback. This gives you both immediate value and long-term flexibility.",
    ],
    "formal": [
        "In response to your inquiry, I would like to present the following analysis. The matter at hand requires careful consideration of multiple factors. Please find below a structured overview of the recommended approach and its rationale.",
        "Thank you for your question. I shall provide a formal assessment of the situation. The primary considerations include operational requirements, resource constraints, and strategic objectives. My recommendation is as follows.",
    ],
    "clear": [
        "Let me explain this clearly. The main idea is straightforward: identify what you need, choose the simplest path that meets those needs, and implement it step by step. Here's how that applies to your situation.",
        "Here's a clear breakdown: First, understand the goal. Second, map out the steps. Third, execute them in order. The important thing is keeping each step simple and well-defined.",
    ],
    "creative": [
        "Here's an interesting way to think about it! Imagine approaching this like building blocks — each piece fits together to create something larger. The creative solution here is to combine familiar patterns in a novel way.",
        "Let me offer a fresh perspective on this. Sometimes the best solutions come from thinking outside conventional boundaries. What if we approached this from a completely different angle?",
    ],
}


def estimate_tokens(text: str) -> int:
    """Estimate token count: words × 1.3"""
    words = len(text.split())
    return max(1, int(words * 1.3))


def generate_mock_response(model_name: str, messages: list[ChatMessage]) -> dict:
    """Generate a complete mock response in OpenAI format."""
    style_config = MODEL_STYLES.get(model_name, MODEL_STYLES["gpt-4o"])
    style = style_config["style"]

    # Simulate latency
    latency = style_config["latency_base"] + random.randint(-style_config["jitter"], style_config["jitter"])

    # Pick a response
    response_text = random.choice(RESPONSES.get(style, RESPONSES["professional"]))

    # Calculate tokens
    prompt_text = " ".join(m.content for m in messages)
    prompt_tokens = estimate_tokens(prompt_text)
    completion_tokens = estimate_tokens(response_text)

    return {
        "id": f"chatcmpl-mock-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "latency_ms": latency,
    }


async def generate_mock_stream(model_name: str, messages: list[ChatMessage]):
    """Generate SSE stream chunks."""
    style_config = MODEL_STYLES.get(model_name, MODEL_STYLES["gpt-4o"])
    style = style_config["style"]
    response_text = random.choice(RESPONSES.get(style, RESPONSES["professional"]))

    request_id = f"chatcmpl-mock-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    # Split response into word chunks
    words = response_text.split()
    chunk_size = 3  # words per chunk

    prompt_text = " ".join(m.content for m in messages)
    prompt_tokens = estimate_tokens(prompt_text)
    completion_tokens = 0

    for i in range(0, len(words), chunk_size):
        chunk_words = words[i : i + chunk_size]
        chunk_text = " ".join(chunk_words)
        if i > 0:
            chunk_text = " " + chunk_text
        completion_tokens += estimate_tokens(chunk_text)

        chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": chunk_text},
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.05)  # simulate streaming delay

    # Final chunk with finish_reason
    final_chunk = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"


class MockProvider:
    """`LLMProvider` adapter wrapping the legacy module-level mock helpers.

    Kept so the dispatch layer can treat mock and real providers
    uniformly. Module-level `generate_mock_response` / `generate_mock_stream`
    remain for backward compatibility with the existing test suite.
    """

    name = "mock"

    async def complete(
        self,
        model_name: str,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> dict:
        # The mock helper is sync; wrap so callers can `await` uniformly.
        return generate_mock_response(model_name, messages)

    def stream(
        self,
        model_name: str,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> AsyncIterator[str]:
        return generate_mock_stream(model_name, messages)
