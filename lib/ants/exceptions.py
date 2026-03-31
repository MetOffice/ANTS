# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.


class NoCoverageError(IndexError):
    """
    Raised when the source has no coverage over the target.

    """

    def __init__(self):
        """
        Raised when the source has no coverage over the target.

        Args:

        * Message to explain the source has no coverage over the target.

        """
        msg = "The source has no coverage over the target"
        super(NoCoverageError, self).__init__(self, msg)


class FloodfillError(ValueError):
    """
    Raised where the seed point already has the value being flood filled.

    """

    def __init__(self, message):
        """
        Raised where the seed point already has the value being flood filled.

        Args:

        * Message to explain the seed point already has the value being flood filled.

        """
        self.message = message


class InvalidOutputPathException(RuntimeError):
    """
    Raised when the user may overwrite the source files with the output.
    """

    def __init__(self):
        """
        Provides the user with a message to explain the output path must be
        different from the source file.

        """
        self.message = "The output path must be different from the source file."
        super().__init__(self.message)


class TimeConstraintFormatException(RuntimeError):
    """
    Raised when the time format is not correctly formatted

    """

    def __init__(
        self,
        time_string,
    ):
        """
        Provides the user with a RuntimeError to explain how the request should be
        formatted.

        Args:

        * time_string: the years in the format requested by the user.

        * message: information on how the request should be formatted.

        """
        self.time_string = time_string
        self.message = (
            "The begin and end times should be of the format 'YYYY', not "
            f"{self.time_string}."
        )
        super().__init__(self.message)


class TimeConstraintUnorderedException(ValueError):
    """
    Raised when the cli arguments for a time constraint have been given out of
    order.

    """

    def __init__(self):
        """
        Raises a ValueError and lets the user know the begin time must be before
        the end time.

        """
        self.message = "The begin time must not be after the end time."
        super().__init__(self.message)


class TimeConstraintMissingException(ValueError):
    """
    Raised when the user only supplies one of the two required time
    constraints in the cli.

    """

    def __init__(self):
        """
        Provides users with information that both an end and start time must be
        provided. To request a single year, these can be the same.

        """
        self.message = "If a begin time is provided, an end time must also be provided."
        super().__init__(self.message)


class TimeConstraintOutOfBoundsException(ValueError):
    """
    Raised when the years requested in the cli are not found in the data.

    """

    def __init__(
        self,
        time_string,
    ):
        """
        Raises a ValueError that tells the user the years they requested are not
        available in the data.

        Args:

        * time_string: the years requested by the user.

        """
        self.time_string = time_string
        self.message = (
            "The time range requested was not found in the data - requested : "
            f"{self.time_string}."
        )
        super().__init__(self.message)


class DateRangeNotFullyAvailableException(ValueError):
    """
    Raised when the years requested in the cli are only partially found in the
    data.

    """

    def __init__(
        self,
        time_string,
        available_range,
    ):
        """
        Creates a ValueError that tells the user the years they requested are not
        all available in the source data and tells the user which years are available.

        Args:

        * time_string: the years requested by the user.

        * available_range: the years available in the source data.

        """
        message = (
            "The time range requested was only partially found in the data - "
            f"requested: {time_string} while only {available_range} was "
            "available."
        )
        self.message = message
        super().__init__(self.message)
