"""Conformance suite error hierarchy."""

from __future__ import annotations

from pathlib import Path


class ConformanceError(Exception):
    """Base class for all conformance runner failures."""


class SuiteDataMissingError(ConformanceError):
    """The expected suite data directory or index file is not present."""

    def __init__(self, suite_id: str, expected_path: Path) -> None:
        self.suite_id = suite_id
        self.expected_path = expected_path
        super().__init__(
            f"Suite data for '{suite_id}' not found at '{expected_path}'. "
            "Ensure the conformance suite data is present."
        )


class TestCaseParseError(ConformanceError):
    """A test case XML file could not be parsed."""

    def __init__(self, file_path: Path, reason: str) -> None:
        self.file_path = file_path
        self.reason = reason
        super().__init__(f"Failed to parse test case '{file_path}': {reason}")


class ConformanceConfigError(ConformanceError):
    """Invalid configuration passed to the conformance runner."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
