from collections.abc import Callable
from datetime import datetime
from functools import wraps
from threading import Lock
from time import perf_counter
from typing import Any
from config import Config

_log_lock = Lock()


def method_logger(func: Callable[..., Any]) -> Callable[..., Any]:
    cf = Config()
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

            method_name = f"{func.__qualname__}()"
            method_name = method_name[:30]

            date_text = finished_at.strftime("%Y-%m-%d")
            time_text = finished_at.strftime("%H:%M:%S")
            elapsed_text = f"{elapsed:08.3f}"

            log_text = (
                f"{date_text} | "
                f"{time_text} | "
                f"{method_name:<30} | "
                f"{elapsed_text} | "
                f"E: {error_message}"
            )

            with open(f"{cf.systemlog_dir}MethodLogger_{datetime.now().strftime("%Y%m%d")}.txt", mode="a", encoding="utf-8") as file:
                file.write(log_text + "\n")

            with _log_lock:
                if hasattr(self, "log") and callable(self.log):
                    self.log(log_text)
                else:
                    print(log_text)

    return wrapper
