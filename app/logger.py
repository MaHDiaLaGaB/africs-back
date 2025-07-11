import logging
import sys
import os
from logging.handlers import TimedRotatingFileHandler
from colorlog import ColoredFormatter

class ColoredCustomFormatter(ColoredFormatter):
    def format(self, record):
        # Inject the folder name where the logging call originated
        record.folder = os.path.basename(os.path.dirname(record.pathname))
        return super().format(record)

class Logger:
    @staticmethod
    def get_logger(name: str = None) -> logging.Logger:
        """
        Return a configured logger.
        - name: usually __name__; defaults to PROJECT_NAME env var or "__main__".
        """
        name = name or os.getenv("PROJECT_NAME", "__main__")
        logger = logging.getLogger(name)

        if not logger.handlers:
            logger.setLevel(logging.DEBUG)

            # --- 1) Console handler with colors ---
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.DEBUG)
            console_fmt = "%(log_color)s%(levelname)-8s [%(folder)s/%(filename)s:%(lineno)d] %(message)s"
            ch.setFormatter(
                ColoredCustomFormatter(
                    console_fmt,
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "bold_red",
                    },
                )
            )
            logger.addHandler(ch)

            # --- 2) File handler (rotates at midnight) ---
            log_dir = os.getenv("LOG_DIR", "logs")

            # Try to use /tmp if /logs is not writable
            if not os.access(log_dir, os.W_OK):
                log_dir = "/tmp"

            try:
                os.makedirs(log_dir, exist_ok=True)
                log_path = os.path.join(log_dir, f"{name}.log")

                fh = TimedRotatingFileHandler(
                    filename=log_path,
                    when="midnight",
                    backupCount=30,
                    encoding="utf-8",
                )
                fh.setLevel(logging.INFO)
                file_fmt = "%(asctime)s %(levelname)-8s [%(folder)s/%(filename)s:%(lineno)d] %(message)s"
                fh.setFormatter(logging.Formatter(file_fmt))
                logger.addHandler(fh)
            except (OSError, IOError) as e:
                logger.warning(f"Failed to set up file logging: {e}")

        return logger
