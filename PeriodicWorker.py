import threading
from typing import Callable, Optional


class PeriodicWorker:
    def __init__(self, task: Callable[[], None], interval: int) -> None:
        self.task = task
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.task()
            except Exception as error:
                pass

            if self._stop_event.wait(self.interval):
                break

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
