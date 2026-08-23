import threading
from typing import Callable, Optional
from decorators import lg


class PeriodicWorker:
    def __init__(self, task: Callable[[], None], interval: int, run_immediately: bool = True,) -> None:
        self.task = task
        self.interval = interval
        self.run_immediately = run_immediately
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _run(self) -> None:
        lg("Started!")
        if self.run_immediately:
            try:
                self.task()
            except Exception as e:
                lg(type(e).__name__)
                pass

        while not self._stop_event.is_set():
            if self._stop_event.wait(self.interval):
                break

            try:
                self.task()
            except Exception as e:
                lg(type(e).__name__)
                pass

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="PeriodicWorkerThread",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
