from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any
import inspect

from config import Config

cf = Config()
_log_lock = Lock()


def _get_log_path() -> Path:
    return Path(cf.systemlog_dir) / f"MethodLogger_{datetime.now():%Y%m%d}.txt"


def _clean_text(text: str) -> str:
    if not text:
        return ""
    return str(text).replace("\r", "").replace("\n", " ")


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
            error_message = _clean_text(f"{type(error).__name__}: {error}")
            raise

        finally:
            finished_at = datetime.now()
            elapsed = perf_counter() - started_at
            method_name = f"{func.__qualname__}()"
            
            file_path = func.__code__.co_filename
            filename = Path(file_path).name

            log_text = (
                f"{finished_at:%Y-%m-%d} | "
                f"{finished_at:%H:%M:%S} | "
                f"{elapsed:08.3f} | "
                f"{filename:<20} | "
                f"{method_name} "
                f"{error_message}"
            )

            append_log(log_text)

    return wrapper


def lg(step_name: str, error_message: str = "") -> None:
    caller_frame = inspect.currentframe().f_back

    try:
        self_object = caller_frame.f_locals.get("self")
        class_name = (
            self_object.__class__.__name__
            if self_object is not None
            else ""
        )

        function_name = caller_frame.f_code.co_name
        line_number = caller_frame.f_lineno
        
        file_path = caller_frame.f_code.co_filename
        filename = Path(file_path).name

        clean_step_name = _clean_text(step_name)
        clean_error_message = _clean_text(error_message)

        if class_name:
            step_id = f"L{line_number}, {class_name}.{function_name}: {clean_step_name}"
        else:
            step_id = f"L{line_number}, {function_name}: {clean_step_name}"

        now = datetime.now()

        log_text = (
            f"{now:%Y-%m-%d} | "
            f"{now:%H:%M:%S} | "
            f"----.--- | "
            f"{filename:<20} | "
            f"{step_id} "
            f"{clean_error_message}"
        )

        append_log(log_text)

    finally:
        del caller_frame