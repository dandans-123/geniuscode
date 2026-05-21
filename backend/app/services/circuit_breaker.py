from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ProviderHealth:
    failure_count: int = 0
    last_failure_time: float = 0.0
    is_open: bool = False
    threshold: int = 5
    recovery_timeout: float = 60.0  # seconds


class CircuitBreaker:
    def __init__(self):
        self._providers: dict[int, ProviderHealth] = {}

    def get_health(self, provider_id: int) -> ProviderHealth:
        if provider_id not in self._providers:
            self._providers[provider_id] = ProviderHealth()
        return self._providers[provider_id]

    def is_available(self, provider_id: int) -> bool:
        health = self.get_health(provider_id)
        if not health.is_open:
            return True
        # Check if recovery timeout has passed
        if time.time() - health.last_failure_time > health.recovery_timeout:
            health.is_open = False
            health.failure_count = 0
            return True
        return False

    def record_success(self, provider_id: int):
        health = self.get_health(provider_id)
        health.failure_count = 0
        health.is_open = False

    def record_failure(self, provider_id: int):
        health = self.get_health(provider_id)
        health.failure_count += 1
        health.last_failure_time = time.time()
        if health.failure_count >= health.threshold:
            health.is_open = True


# Singleton for the application
circuit_breaker = CircuitBreaker()
