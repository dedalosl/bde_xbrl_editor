"""Entry point for running the conformance suite as a module:
    python -m bde_xbrl_editor.conformance [options]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bde_xbrl_editor.conformance.registry import SUITE_REGISTRY
from bde_xbrl_editor.conformance.reporters.console import ConsoleReporter
from bde_xbrl_editor.conformance.reporters.json_reporter import JsonReporter
from bde_xbrl_editor.conformance.runner import ConformanceRunner


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m bde_xbrl_editor.conformance",
        description="Run XBRL conformance suites against the BDE XBRL Editor engine.",
    )
    parser.add_argument(
        "--suite-data-dir",
        default="tests/conformance/suite-data",
        help="Root directory containing suite data subdirectories (default: tests/conformance/suite-data)",
    )
    parser.add_argument(
        "--suite",
        choices=list(SUITE_REGISTRY.keys()) + ["all"],
        default="all",
        help="Which suite(s) to run (default: all)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed information about failures",
    )
    parser.add_argument(
        "--stop-on-first-failure",
        action="store_true",
        help="Stop after the first mandatory failure",
    )
    parser.add_argument(
        "--output-file",
        help="Write report to this file",
    )
    parser.add_argument(
        "--output-format",
        choices=["json"],
        default="json",
        help="Output file format (default: json)",
    )
    return parser.parse_args(argv)


def _normalise_suite(suite_arg: str) -> list[str] | None:
    if suite_arg == "all":
        return None
    return [suite_arg]


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    selected = _normalise_suite(args.suite)

    runner = ConformanceRunner(
        suite_data_dir=Path(args.suite_data_dir),
        selected_suites=selected,
        verbose=args.verbose,
        stop_on_first_failure=args.stop_on_first_failure,
    )

    reporter = ConsoleReporter(verbose=args.verbose)
    report = runner.run(progress_callback=reporter.print_progress)
    reporter.print_report(report)

    if args.output_file:
        if args.output_format == "json":
            JsonReporter().write(report, Path(args.output_file))

    sys.exit(report.exit_code)


if __name__ == "__main__":
    main()
