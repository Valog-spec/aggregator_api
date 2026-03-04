import logging
import os
from typing import Literal

LOG_DIR = os.path.join(os.path.dirname(__file__), "log_files")
os.makedirs(LOG_DIR, exist_ok=True)


class LevelFileHandler(logging.Handler):
    """Кастомный обработчик логов, записывающий сообщения в разные файлы.

    В зависимости от уровня лога запись направляется в:
    - calc_warning.log — для WARNING
    - calc_error.log — для ERROR
    - calc_exception.log — для исключений (exc_info)
    - logger.log — для всех остальных уровней (DEBUG, INFO)

    Attributes:
        filename: Путь к файлу логов по умолчанию.
        mode: Режим открытия файла.
    """

    def __init__(
        self,
        filename: str,
        mode: Literal["r", "rb", "w", "wb", "a", "ab"] = "a",
    ) -> None:
        super().__init__()
        self.filename = filename
        self.mode = mode

    def emit(self, record: logging.LogRecord) -> None:
        """Записать лог в соответствующий файл в зависимости от уровня.

        Args:
            record: Объект записи лога.
        """
        if record.exc_info and record.exc_info[0] is not None:
            target = os.path.join(LOG_DIR, "calc_exception.log")
        elif record.levelname == "WARNING":
            target = os.path.join(LOG_DIR, "calc_warning.log")
        elif record.levelname == "ERROR":
            target = os.path.join(LOG_DIR, "calc_error.log")
        else:
            target = self.filename

        msg = self.format(record)
        with open(target, mode=self.mode) as f:
            f.write(msg + "\n")


dict_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "base": {
            "format": "%(levelname)s | %(name)s | %(asctime)s | %(lineno)s | %(message)s"
        }
    },
    "handlers": {
        "file": {
            "()": LevelFileHandler,
            "level": "DEBUG",
            "formatter": "base",
            "filename": os.path.join(LOG_DIR, "logger.log"),
            "mode": "a",
        },
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "base",
        },
    },
    "loggers": {
        "src": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        }
    },
}
