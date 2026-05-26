import time
from contextlib import contextmanager


class LatencyProfiler:

    def __init__(self):

        self.samples = {}

    @contextmanager
    def measure(self, name):

        start = time.perf_counter()

        try:

            yield

        finally:

            elapsed_ms = (time.perf_counter() - start) * 1000.0

            self.record(name, elapsed_ms)

    def record(self, name, elapsed_ms):

        bucket = self.samples.setdefault(name, [])

        bucket.append(elapsed_ms)

        if len(bucket) > 100:

            del bucket[:-100]

    def summary(self):

        result = {}

        for name, values in self.samples.items():

            if not values:

                continue

            result[name] = {
                "avg_ms": round(sum(values) / len(values), 3),
                "max_ms": round(max(values), 3),
                "samples": len(values),
            }

        return result
