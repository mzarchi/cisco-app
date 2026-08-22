from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any
from config import Config
import inspect

cf = Config()
_log_lock = Lock()


def _get_log_path() -> Path:
    return Path(cf.systemlog_dir) / f"MethodLogger_{datetime.now().strftime("%Y%m%d")}.txt"


def append_log(contents: str) -> None:
    log_path = _get_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with _log_lock:
        with log_path.open(mode="a", encoding="utf-8") as file:
            file.write(contents + "\n")


def method_logger(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        started_at = perf_counter()
        error_message = ""

        try:
            return func(self, *args, **kwargs)

        except Exception as error:
            error_message = f"{type(error).__name__}: {error}"
            raise

        finally:
            finished_at = datetime.now()
            elapsed = perf_counter() - started_at

            method_name = f"{func.__qualname__}()"[:30]
            log_text = (
                f"{finished_at:%Y-%m-%d} | "
                f"{finished_at:%H:%M:%S} | "
                f"{method_name:<30} | "
                f"{elapsed:08.3f} | "
                f"E: {error_message}"
            )

            append_log(log_text)

            if hasattr(self, "log") and callable(self.log):
                self.log(log_text)
            else:
                print(log_text)

    return wrapper


def lg(step_name: str, error_message: str = "") -> None: # Line Logger, maybe i am mhz ?! :)
    caller_frame = inspect.currentframe().f_back

    try:
        class_name = ""
        self_object = caller_frame.f_locals.get("self")
        if self_object is not None:
            class_name = f"{self_object.__class__.__name__}."

        function_name = caller_frame.f_code.co_name
        line_number = caller_frame.f_lineno
        step_id = f"{class_name}{function_name}():L{line_number} {step_name}"
        step_id = step_id[:30]
        now = datetime.now()
        log_text = (
            f"{now:%Y-%m-%d} | "
            f"{now:%H:%M:%S} | "
            f"{step_id:<30} | "
            f"0000.000 | "
            f"E: {error_message}"
        )

        append_log(log_text)

    finally:
        del caller_frame