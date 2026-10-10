"""Custom exceptions used across the project."""


class InputError(Exception):
    """Raised when the input is malformed or fails validation.

    The message is written to be shown directly to the user.
    """
