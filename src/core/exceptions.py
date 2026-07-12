"""Custom exceptions used across the automation framework."""


class AutomationBaseError(Exception):
    """Base class for all errors raised by this project."""


class EmulatorNotFoundError(AutomationBaseError):
    """Raised when no MuMuPlayer window/instance could be found or resolved."""


class AdbConnectionError(AutomationBaseError):
    """Raised when connecting to, or communicating with, an ADB device fails."""


class AdbCommandError(AutomationBaseError):
    """Raised when an adb shell/exec-out command returns a non-zero exit code."""


class TemplateNotFoundError(AutomationBaseError):
    """Raised when a required template image file is missing on disk."""


class StepVerificationError(AutomationBaseError):
    """Raised when a step's expected screen/template could not be verified."""


class AutomationError(AutomationBaseError):
    """Raised when a step fails after exhausting all retries/recovery actions."""


class AutomationCancelled(AutomationBaseError):
    """Raised to unwind a running automation loop when the user cancels it (GUI Stop/Cancel)."""
