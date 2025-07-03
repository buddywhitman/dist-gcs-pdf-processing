import os
import threading
import time
from dist_gcs_pdf_processing.env import load_env_and_credentials

GEMINI_RATE_LIMIT = int(os.getenv("GEMINI_RATE_LIMIT", 10))  # requests/sec
GCS_RATE_LIMIT = int(os.getenv("GCS_RATE_LIMIT", 20))  # requests/sec

load_env_and_credentials()

class RateLimiter:
    def __init__(self, rate_per_sec):
        self.rate = rate_per_sec
        self.tokens = rate_per_sec
        self.last = time.time()
        self.lock = threading.Lock()
    def acquire(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last
            self.tokens += elapsed * self.rate
            if self.tokens > self.rate:
                self.tokens = self.rate
            if self.tokens < 1:
                time.sleep((1 - self.tokens) / self.rate)
                self.tokens = 0
            else:
                self.tokens -= 1
            self.last = time.time()

GEMINI_LIMITER = RateLimiter(GEMINI_RATE_LIMIT)
GCS_LIMITER = RateLimiter(GCS_RATE_LIMIT) 