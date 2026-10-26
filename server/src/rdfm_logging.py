import logging

# This module configures the global logger with nicer to look at formatting.
# Note that this only needs to be done once per Python interpreter, and you
# usually won't need to import rdfm_logging; you should instead import the
# regular logging module.


class PrettyFormatter(logging.Formatter):
    # use ansi escape styles
    # https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797#colors--graphics-mode
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[33m"  # ;21;5
    red = "\x1b[31m"  # ;21
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"  # clears formating
    format_str = "[%(asctime)s] [%(name)s] (%(levelname)s) %(message)s"
    FORMATS = {
        logging.DEBUG: blue + format_str + reset,
        logging.INFO: format_str,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset,
    }

    def format(self, record: logging.LogRecord) -> str:
        """Define custom logger format."""
        datefmt = "%Y-%m-%dT%H:%M:%S%z"
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt)
        return formatter.format(record)


def set_logging() -> None:
    """Configure global logger to use the pretty formatter."""
    root = logging.getLogger()
    level = logging.INFO
    root.setLevel(level)
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(PrettyFormatter())
    root.addHandler(stdout_handler)


set_logging()
