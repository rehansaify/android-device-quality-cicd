"""Tests for QualityRunner, simulated test suite execution, and CLI interface."""

import json
from pathlib import Path

import pytest

from device_quality.device import (
    BootStatus,
    ConnectionStatus,
    Device,
)
from device_quality.runner import (
    QualityRunner,
    get_sample_device,
    main,
)


@pytest.fixture
def runner() -> QualityRunner:
    return QualityRunner()


def test_runner_healthy_device_passes_gate(runner: QualityRunner) -> None:
    """Ensure healthy device passes the gate and executes all simulated tests."""
    device = get_sample_device("healthy")
    report = runner.run(device)

    assert report.gate_passed is True
    assert report.test_suite_executed is True
    assert report.summary["gate_status"] == "PASSED"
    assert report.summary["overall_health"] == "HEALTHY"
    assert report.summary["tests_total"] == 4
    assert report.summary["tests_passed"] == 4
    assert report.summary["tests_failed"] == 0
    assert report.summary["tests_skipped"] == 0
    assert len(report.tests) == 4
    assert all(t.status == "PASSED" for t in report.tests)


def test_runner_warning_device_passes_gate_with_notices(runner: QualityRunner) -> None:
    """Ensure warning device passes gate but logs warning metrics."""
    device = get_sample_device("warning")
    report = runner.run(device)

    assert report.gate_passed is True
    assert report.test_suite_executed is True
    assert report.summary["gate_status"] == "PASSED"
    assert report.summary["overall_health"] == "WARNING"
    assert len(report.health_report["warnings"]) > 0
    assert report.summary["tests_total"] == 4


def test_runner_critical_device_blocks_testing(runner: QualityRunner) -> None:
    """Ensure critical device fails gate and aborts test suite execution."""
    device = get_sample_device("critical")
    report = runner.run(device)

    assert report.gate_passed is False
    assert report.test_suite_executed is False
    assert report.summary["gate_status"] == "BLOCKED"
    assert report.summary["overall_health"] == "CRITICAL"
    assert report.summary["tests_total"] == 0
    assert len(report.tests) == 0
    assert "Testing aborted" in report.summary["reason"]


def test_get_sample_device_unknown_variant() -> None:
    """Ensure invalid variant name raises ValueError."""
    with pytest.raises(ValueError, match="Unknown sample variant 'unknown'"):
        get_sample_device("unknown")


def test_cli_sample_healthy(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI with --sample runs healthy simulation, writes JSON, and returns exit code 0."""
    exit_code = main(["--sample"])
    captured = capsys.readouterr()

    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["gate_passed"] is True
    assert data["summary"]["gate_status"] == "PASSED"
    assert data["health_report"]["overall_status"] == "HEALTHY"


def test_cli_sample_warning(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI with --sample-warning returns 0 with WARNING health."""
    exit_code = main(["--sample-warning"])
    captured = capsys.readouterr()

    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["gate_passed"] is True
    assert data["summary"]["gate_status"] == "PASSED"
    assert data["health_report"]["overall_status"] == "WARNING"


def test_cli_sample_critical(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI with --sample-critical blocks gate and returns exit code 1."""
    exit_code = main(["--sample-critical"])
    captured = capsys.readouterr()

    assert exit_code == 1
    data = json.loads(captured.out)
    assert data["gate_passed"] is False
    assert data["summary"]["gate_status"] == "BLOCKED"
    assert data["health_report"]["overall_status"] == "CRITICAL"


def test_cli_with_inline_json_data(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI with --data evaluates inline JSON payload."""
    payload = json.dumps(
        {
            "model": "Test Phone",
            "android_version": "14",
            "battery_level": 95.0,
            "storage_usage": 30.0,
            "temperature": 29.0,
            "connection_status": "CONNECTED",
            "boot_status": "BOOTED",
        }
    )
    exit_code = main(["--data", payload])
    captured = capsys.readouterr()

    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["gate_passed"] is True
    assert data["device"]["model"] == "Test Phone"


def test_cli_with_file_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI with --file evaluates device JSON from disk."""
    file_path = tmp_path / "custom_device.json"
    device_data = {
        "model": "OnePlus 12",
        "android_version": "14",
        "battery_level": 75.0,
        "storage_usage": 50.0,
        "temperature": 33.0,
        "connection_status": "CONNECTED",
        "boot_status": "BOOTED",
    }
    file_path.write_text(json.dumps(device_data), encoding="utf-8")

    exit_code = main(["--file", str(file_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["gate_passed"] is True
    assert data["device"]["model"] == "OnePlus 12"


def test_cli_with_output_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI with --output writes the full report to the specified file."""
    output_path = tmp_path / "reports" / "gate_report.json"
    exit_code = main(["--sample", "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.exists()
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["gate_passed"] is True
    assert saved["summary"]["gate_status"] == "PASSED"


def test_cli_file_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI with non-existent file returns exit code 1 with error JSON."""
    missing = tmp_path / "non_existent.json"
    exit_code = main(["--file", str(missing)])
    captured = capsys.readouterr()

    assert exit_code == 1
    error_data = json.loads(captured.err)
    assert error_data["gate_passed"] is False
    assert "FileNotFoundError" in error_data["error"]


def test_cli_invalid_json_data(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI with malformed JSON string returns exit code 1 with error JSON."""
    exit_code = main(["--data", "not-valid-json{"])
    captured = capsys.readouterr()

    assert exit_code == 1
    error_data = json.loads(captured.err)
    assert error_data["gate_passed"] is False
    assert "DeviceValidationError" in error_data["error"]


def test_cli_device_validation_failure(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI with out-of-bounds telemetry returns exit code 1 with error JSON."""
    payload = json.dumps(
        {
            "model": "Broken Phone",
            "android_version": "14",
            "battery_level": 150.0,  # Invalid: > 100%
            "storage_usage": 30.0,
            "temperature": 29.0,
            "connection_status": "CONNECTED",
            "boot_status": "BOOTED",
        }
    )
    exit_code = main(["--data", payload])
    captured = capsys.readouterr()

    assert exit_code == 1
    error_data = json.loads(captured.err)
    assert error_data["gate_passed"] is False
    assert "out of bounds" in error_data["error"]


def test_run_report_serialization() -> None:
    """Verify RunReport to_dict and to_json methods."""
    device = Device(
        model="Test",
        android_version="14",
        battery_level=90.0,
        storage_usage=40.0,
        temperature=30.0,
        connection_status=ConnectionStatus.CONNECTED,
        boot_status=BootStatus.BOOTED,
    )
    runner = QualityRunner()
    report = runner.run(device)

    data = report.to_dict()
    assert isinstance(data, dict)
    assert data["gate_passed"] is True

    json_str = report.to_json()
    assert isinstance(json_str, str)
    assert json.loads(json_str)["gate_passed"] is True
