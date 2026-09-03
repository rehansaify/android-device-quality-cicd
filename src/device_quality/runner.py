"""Simulation runner executing device quality checks and mock test suites."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from device_quality.device import (
    BootStatus,
    ConnectionStatus,
    Device,
    DeviceValidationError,
)
from device_quality.health import HealthEvaluator, HealthReport, HealthStatus


@dataclass(frozen=True)
class TestCaseResult:
    """Outcome of a single simulated test check."""

    name: str
    status: str
    duration_ms: float
    details: str

    def to_dict(self) -> dict[str, Any]:
        """Convert test case result to dictionary."""
        return {
            "name": self.name,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "details": self.details,
        }


@dataclass(frozen=True)
class RunReport:
    """Comprehensive machine-readable execution report consumed by CI/CD pipelines."""

    device: dict[str, Any]
    health_report: dict[str, Any]
    gate_passed: bool
    test_suite_executed: bool
    tests: list[TestCaseResult]
    summary: dict[str, Any]
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """Convert run report to dictionary."""
        return {
            "timestamp": self.timestamp,
            "gate_passed": self.gate_passed,
            "test_suite_executed": self.test_suite_executed,
            "device": self.device,
            "health_report": self.health_report,
            "tests": [t.to_dict() for t in self.tests],
            "summary": self.summary,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize run report to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class QualityRunner:
    """Orchestrates pre-flight device health gating and simulated test execution."""

    def __init__(self, evaluator: HealthEvaluator | None = None) -> None:
        self.evaluator = evaluator or HealthEvaluator()

    def run(self, device: Device) -> RunReport:
        """Evaluate device health and run automated test suite if gate passes."""
        iso_timestamp = datetime.now(UTC).isoformat()
        health_report: HealthReport = self.evaluator.evaluate(device)

        if not health_report.is_eligible_for_testing:
            reasons = ", ".join(health_report.rejection_reasons)
            summary = {
                "gate_status": "BLOCKED",
                "overall_health": health_report.overall_status.value,
                "reason": f"Device quality gate failed. Testing aborted: {reasons}",
                "tests_total": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_skipped": 0,
                "total_duration_ms": 0.0,
            }
            return RunReport(
                device=device.to_dict(),
                health_report=health_report.to_dict(),
                gate_passed=False,
                test_suite_executed=False,
                tests=[],
                summary=summary,
                timestamp=iso_timestamp,
            )

        test_results = self._execute_simulated_test_suite(device, health_report)
        passed_count = sum(1 for t in test_results if t.status == "PASSED")
        failed_count = sum(1 for t in test_results if t.status == "FAILED")
        skipped_count = sum(1 for t in test_results if t.status == "SKIPPED")
        total_duration = sum(t.duration_ms for t in test_results)

        summary = {
            "gate_status": "PASSED",
            "overall_health": health_report.overall_status.value,
            "tests_total": len(test_results),
            "tests_passed": passed_count,
            "tests_failed": failed_count,
            "tests_skipped": skipped_count,
            "total_duration_ms": round(total_duration, 2),
        }

        return RunReport(
            device=device.to_dict(),
            health_report=health_report.to_dict(),
            gate_passed=True,
            test_suite_executed=True,
            tests=test_results,
            summary=summary,
            timestamp=iso_timestamp,
        )

    def _execute_simulated_test_suite(
        self, device: Device, health_report: HealthReport
    ) -> list[TestCaseResult]:
        """Execute deterministic simulated test cases."""
        tests: list[TestCaseResult] = []

        # 1. OS Environment Sanity
        tests.append(
            TestCaseResult(
                name="test_os_environment",
                status="PASSED",
                duration_ms=45.2,
                details=f"Android {device.android_version} verified on {device.model}.",
            )
        )

        # 2. Storage Allocation
        free_storage = 100.0 - device.storage_usage
        tests.append(
            TestCaseResult(
                name="test_storage_allocation",
                status="PASSED",
                duration_ms=62.8,
                details=(f"Storage capacity verified ({free_storage:.1f}% free). Staging ready."),
            )
        )

        # 3. Thermal Stability
        if health_report.overall_status == HealthStatus.HEALTHY:
            thermal_detail = f"Device operating at {device.temperature:.1f}°C."
        else:
            thermal_detail = (
                f"Elevated temperature ({device.temperature:.1f}°C) noted; "
                "execution permitted with thermal monitoring."
            )
        tests.append(
            TestCaseResult(
                name="test_thermal_stability",
                status="PASSED",
                duration_ms=88.4,
                details=thermal_detail,
            )
        )

        # 4. App Launch Readiness
        tests.append(
            TestCaseResult(
                name="test_app_launch_readiness",
                status="PASSED",
                duration_ms=115.0,
                details="ActivityManager and PackageManager responsive. Ready for UI tests.",
            )
        )

        return tests


def get_sample_device(variant: str = "healthy") -> Device:
    """Generate preset sample devices for simulation and testing."""
    if variant == "healthy":
        return Device(
            model="Pixel 8 Pro",
            android_version="14.0",
            battery_level=85.0,
            storage_usage=42.0,
            temperature=31.5,
            connection_status=ConnectionStatus.CONNECTED,
            boot_status=BootStatus.BOOTED,
        )
    if variant == "warning":
        return Device(
            model="Galaxy S23",
            android_version="14.0",
            battery_level=18.0,
            storage_usage=89.5,
            temperature=44.0,
            connection_status=ConnectionStatus.CONNECTED,
            boot_status=BootStatus.BOOTED,
        )
    if variant == "critical":
        return Device(
            model="Pixel 6a",
            android_version="13.0",
            battery_level=6.5,
            storage_usage=97.8,
            temperature=52.3,
            connection_status=ConnectionStatus.DISCONNECTED,
            boot_status=BootStatus.BOOTING,
        )
    raise ValueError(f"Unknown sample variant '{variant}'. Expected: healthy, warning, critical.")


def create_cli_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="device-quality",
        description="Android Device Quality Simulator and CI/CD Pre-Flight Quality Gate",
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "-f",
        "--file",
        type=Path,
        help="Path to JSON file containing device specification.",
    )
    group.add_argument(
        "-d",
        "--data",
        type=str,
        help="Inline JSON string containing device specification.",
    )
    group.add_argument(
        "--sample",
        action="store_const",
        const="healthy",
        dest="sample_variant",
        help="Run gate evaluation with a healthy sample device.",
    )
    group.add_argument(
        "--sample-warning",
        action="store_const",
        const="warning",
        dest="sample_variant",
        help="Run gate evaluation with a warning-level sample device.",
    )
    group.add_argument(
        "--sample-critical",
        action="store_const",
        const="critical",
        dest="sample_variant",
        help="Run gate evaluation with a critical-level sample device.",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional path to write the JSON quality report.",
    )
    return parser


def parse_device_from_cli(args: argparse.Namespace) -> Device:
    """Resolve and parse a Device instance from parsed CLI arguments."""
    if args.sample_variant:
        return get_sample_device(args.sample_variant)

    if args.file:
        if not args.file.exists():
            raise FileNotFoundError(f"Device configuration file not found: {args.file}")
        content = args.file.read_text(encoding="utf-8")
        return Device.from_json(content)

    if args.data:
        return Device.from_json(args.data)

    # Default fallback when no argument provided: healthy sample
    return get_sample_device("healthy")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint returning 0 on gate pass, 1 on failure or invalid input."""
    parser = create_cli_parser()
    args = parser.parse_args(argv)

    try:
        device = parse_device_from_cli(args)
    except (DeviceValidationError, FileNotFoundError, ValueError, json.JSONDecodeError) as err:
        error_payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "gate_passed": False,
            "error": f"{type(err).__name__}: {err}",
            "summary": {
                "gate_status": "ERROR",
                "overall_health": "UNKNOWN",
                "tests_total": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_skipped": 0,
            },
        }
        output_json = json.dumps(error_payload, indent=2)
        sys.stderr.write(output_json + "\n")
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output_json + "\n", encoding="utf-8")
        return 1

    runner = QualityRunner()
    report = runner.run(device)
    report_json = report.to_json(indent=2)

    sys.stdout.write(report_json + "\n")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report_json + "\n", encoding="utf-8")

    return 0 if report.gate_passed else 1


if __name__ == "__main__":
    sys.exit(main())
