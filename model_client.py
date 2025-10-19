import time
import requests
from config import settings


class CircuitBreaker:
    """Stops the Arbiter from hammering a broken endpoint."""
    def __init__(self, max_failures=3, reset_after=15.0):
        self.max_failures = max_failures
        self.reset_after = reset_after
        self.failures = 0
        self.opened_at = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if (time.time() - self.opened_at) >= self.reset_after:
            self.failures = 0
            self.opened_at = None
            return True
        return False

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.max_failures:
            self.opened_at = time.time()


breaker = CircuitBreaker()


def call_model(prompt: str, context: str, session_id: str) -> dict:
    """
    Safe call to the Mythos Model endpoint with retries and fall-back text.
    Always returns a dict with a 'response' key.
    """
    if not breaker.allow():
        return {"response": "[Model temporarily unavailable (circuit open)]"}

    payload = {"prompt": prompt, "context": context, "session_id": session_id}
    backoff = settings.RETRY_BACKOFF_SECS
    last_err = None

    for attempt in range(settings.MAX_RETRIES + 1):
        try:
            r = requests.post(
                settings.MODEL_URL,
                json=payload,
                timeout=settings.REQUEST_TIMEOUT_SECS,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            r.raise_for_status()
            data = r.json()
            breaker.failures = 0
            breaker.opened_at = None
            if isinstance(data, dict):
                return data
            return {"response": str(data)}

        except Exception as e:
            last_err = e
            breaker.record_failure()
            time.sleep(backoff)
            backoff *= 1.6

    print(f"⚠️ Mythos Model unreachable after retries: {last_err}")
    return {"response": "[Model temporarily unavailable — imagination mode engaged]"}
