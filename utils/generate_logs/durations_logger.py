# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""Module to configure logging for scripts that generate the test duration log file.

Configures logging handlers for log files and console. Use the rich library for console
logging if rich is available. Console log level is user configurable via the command
line flag ``verbosity``, which calls ``set_console_handler_log_level`` in ``main.py``.

"""
import logging
import sys
from typing import TextIO


class Utf8ToAsciiStreamHandler(logging.StreamHandler):
    """Custom StreamHandler to convert UTF-8 text to renderable ASCII."""

    def __init__(self, stream: TextIO) -> None:
        super().__init__(stream)

    def emit(self, record: logging.LogRecord) -> None:
        """Implement `logging.Handler` abstract method.

        Convert UTF-8 logging statements to ASCII renderable text. Non-ASCII characters
        are ignored.

        Parameters
        ----------
        record
            Contains all the information pertinent to the event being logged.

        """
        msg = self.format(record)
        ascii_msg = msg.encode("ascii", errors="ignore").decode("ascii")
        self.stream.write(ascii_msg)
        self.stream.write(self.terminator)
        self.stream.flush()


# Configure logger.
logger = logging.getLogger("generate_logs_logger")
logger.setLevel(logging.DEBUG)
custom_stream_handler = Utf8ToAsciiStreamHandler(sys.stdout)
console_handler = custom_stream_handler
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

console_handler.setLevel(logging.ERROR)
logger.addHandler(console_handler)


def set_console_handler_log_level(log_level: int) -> None:
    """Set the ``console_handler`` log level.

    Note
    ----
    ``log_level`` is type ``int` as logging constants are ints.
    E.g. ``logging.DEBUG`` == 10, ``logging.INFO`` == 20 etc. See more here:
    https://docs.python.org/3/library/logging.html#logging-levels

    Parameters
    ----------
    log_level
        The required logging level.

    """
    console_handler.setLevel(log_level)
