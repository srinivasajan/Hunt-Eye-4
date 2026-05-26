import time


class Monitor:

    def __init__(self, orchestrator, stale_after_seconds=2.0):

        self.orchestrator = orchestrator

        self.stale_after_seconds = stale_after_seconds

    def print_status(self):

        print("\n=== Worker Status ===")

        now = time.time()

        for worker in self.orchestrator.workers:

            delta = now - worker.last_update

            print(
                f"{worker.name} | alive={worker.is_alive()} | failed={worker.failed} | "
                f"stale={delta > self.stale_after_seconds} | last_update={delta:.2f}s"
            )
