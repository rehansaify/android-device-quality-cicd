"""Tests for HealthEvaluator, threshold boundaries, and status aggregation."""

import pytest

from device_quality.device import BootStatus, ConnectionStatus, Device
from device_quality.health import (
    CheckResult,
    HealthEvaluator,
    HealthStatus,
)


@pytest.fixture
def evaluator() -> HealthEvaluator:
    return HealthEvaluator()


def make_device(
    model: str = "Pixel 8",
    android_version: str = "14.0",
    battery_level: float = 85.0,
    storage_usage: float = 40.0,
    temperature: float = 30.0,
    connection_status: ConnectionStatus = ConnectionStatus.CONNECTED,
    boot_status: BootStatus = BootStatus.BOOTED,
) -> Device:
    return Device(
        model=model,
        android_version=android_version,
        battery_level=battery_level,
        storage_usage=storage_usage,
        temperature=temperature,
        connection_status=connection_status,
        boot_status=boot_status,
    )


def test_healthy_device_evaluation(evaluator: HealthEvaluator) -> None:
    """Ensure an optimal device evaluates to HEALTHY and eligible for testing."""
    device = make_device()
    report = evaluator.evaluate(device)

    assert report.overall_status == HealthStatus.HEALTHY
    assert report.is_eligible_for_testing is True
    assert len(report.rejection_reasons) == 0
    assert len(report.warnings) == 0
    assert len(report.checks) == 5
    assert all(c.status == HealthStatus.HEALTHY for c in report.checks)


@pytest.mark.parametrize(
    "battery_val,expected_status",
    [
        (100.0, HealthStatus.HEALTHY),
        (20.0, HealthStatus.HEALTHY),
        (19.9, HealthStatus.WARNING),
        (19.0, HealthStatus.WARNING),
        (10.0, HealthStatus.WARNING),
        (9.9, HealthStatus.CRITICAL),
        (9.0, HealthStatus.CRITICAL),
        (0.0, HealthStatus.CRITICAL),
    ],
)
def test_battery_level_boundaries(
    evaluator: HealthEvaluator, battery_val: float, expected_status: HealthStatus
) -> None:
    """Validate boundary thresholds for battery level."""
    device = make_device(battery_level=battery_val)
    report = evaluator.evaluate(device)

    check = next(c for c in report.checks if c.name == "battery_level")
    assert check.status == expected_status
    if expected_status == HealthStatus.CRITICAL:
        assert report.overall_status == HealthStatus.CRITICAL
        assert report.is_eligible_for_testing is False
        assert any("battery" in reason.lower() for reason in report.rejection_reasons)
    elif expected_status == HealthStatus.WARNING:
        assert report.overall_status == HealthStatus.WARNING
        assert report.is_eligible_for_testing is True
        assert any("battery" in warn.lower() for warn in report.warnings)


@pytest.mark.parametrize(
    "temp_val,expected_status",
    [
        (25.0, HealthStatus.HEALTHY),
        (40.0, HealthStatus.HEALTHY),
        (40.1, HealthStatus.WARNING),
        (45.0, HealthStatus.WARNING),
        (48.0, HealthStatus.WARNING),
        (48.1, HealthStatus.CRITICAL),
        (50.0, HealthStatus.CRITICAL),
        (75.0, HealthStatus.CRITICAL),
    ],
)
def test_temperature_boundaries(
    evaluator: HealthEvaluator, temp_val: float, expected_status: HealthStatus
) -> None:
    """Validate boundary thresholds for operating temperature."""
    device = make_device(temperature=temp_val)
    report = evaluator.evaluate(device)

    check = next(c for c in report.checks if c.name == "temperature")
    assert check.status == expected_status
    if expected_status == HealthStatus.CRITICAL:
        assert report.overall_status == HealthStatus.CRITICAL
        assert report.is_eligible_for_testing is False
        assert any("thermal" in reason.lower() for reason in report.rejection_reasons)
    elif expected_status == HealthStatus.WARNING:
        assert report.overall_status == HealthStatus.WARNING
        assert report.is_eligible_for_testing is True
        assert any("temperature" in warn.lower() for warn in report.warnings)


@pytest.mark.parametrize(
    "storage_val,expected_status",
    [
        (10.0, HealthStatus.HEALTHY),
        (85.0, HealthStatus.HEALTHY),
        (85.1, HealthStatus.WARNING),
        (90.0, HealthStatus.WARNING),
        (95.0, HealthStatus.WARNING),
        (95.1, HealthStatus.CRITICAL),
        (98.0, HealthStatus.CRITICAL),
        (100.0, HealthStatus.CRITICAL),
    ],
)
def test_storage_boundaries(
    evaluator: HealthEvaluator, storage_val: float, expected_status: HealthStatus
) -> None:
    """Validate boundary thresholds for storage utilization."""
    device = make_device(storage_usage=storage_val)
    report = evaluator.evaluate(device)

    check = next(c for c in report.checks if c.name == "storage_usage")
    assert check.status == expected_status
    if expected_status == HealthStatus.CRITICAL:
        assert report.overall_status == HealthStatus.CRITICAL
        assert report.is_eligible_for_testing is False
        assert any("storage" in reason.lower() for reason in report.rejection_reasons)
    elif expected_status == HealthStatus.WARNING:
        assert report.overall_status == HealthStatus.WARNING
        assert report.is_eligible_for_testing is True
        assert any("storage" in warn.lower() for warn in report.warnings)


@pytest.mark.parametrize(
    "conn_status",
    [ConnectionStatus.DISCONNECTED, ConnectionStatus.UNAUTHORIZED],
)
def test_connection_status_failure(
    evaluator: HealthEvaluator, conn_status: ConnectionStatus
) -> None:
    """Ensure non-CONNECTED connection state produces a CRITICAL result."""
    device = make_device(connection_status=conn_status)
    report = evaluator.evaluate(device)

    check = next(c for c in report.checks if c.name == "connection_status")
    assert check.status == HealthStatus.CRITICAL
    assert report.overall_status == HealthStatus.CRITICAL
    assert report.is_eligible_for_testing is False
    assert any("connection" in reason.lower() for reason in report.rejection_reasons)


@pytest.mark.parametrize(
    "boot_state",
    [BootStatus.BOOTING, BootStatus.RECOVERY, BootStatus.OFFLINE],
)
def test_boot_status_failure(evaluator: HealthEvaluator, boot_state: BootStatus) -> None:
    """Ensure non-BOOTED boot status produces a CRITICAL result."""
    device = make_device(boot_status=boot_state)
    report = evaluator.evaluate(device)

    check = next(c for c in report.checks if c.name == "boot_status")
    assert check.status == HealthStatus.CRITICAL
    assert report.overall_status == HealthStatus.CRITICAL
    assert report.is_eligible_for_testing is False
    assert any("boot" in reason.lower() for reason in report.rejection_reasons)


def test_severity_precedence_critical_overrides_warning(evaluator: HealthEvaluator) -> None:
    """Verify that a single CRITICAL check overrides WARNING checks."""
    # Battery is WARNING (18%), Temperature is CRITICAL (51°C)
    device = make_device(battery_level=18.0, temperature=51.0)
    report = evaluator.evaluate(device)

    assert report.overall_status == HealthStatus.CRITICAL
    assert report.is_eligible_for_testing is False
    assert len(report.warnings) == 1
    assert len(report.rejection_reasons) == 1


def test_multiple_warnings_aggregate_to_warning(evaluator: HealthEvaluator) -> None:
    """Verify multiple warnings maintain WARNING overall status without triggering CRITICAL."""
    # Battery 18%, Temperature 44°C, Storage 90%
    device = make_device(battery_level=18.0, temperature=44.0, storage_usage=90.0)
    report = evaluator.evaluate(device)

    assert report.overall_status == HealthStatus.WARNING
    assert report.is_eligible_for_testing is True
    assert len(report.warnings) == 3
    assert len(report.rejection_reasons) == 0


def test_health_report_to_dict_structure(evaluator: HealthEvaluator) -> None:
    """Verify dictionary serialization format of the health report."""
    device = make_device()
    report = evaluator.evaluate(device)
    raw = report.to_dict()

    assert raw["overall_status"] == "HEALTHY"
    assert raw["is_eligible_for_testing"] is True
    assert raw["rejection_reasons"] == []
    assert raw["warnings"] == []
    assert isinstance(raw["checks"], list)
    assert len(raw["checks"]) == 5


def test_check_result_to_dict() -> None:
    """Verify CheckResult serialization contains expected fields."""
    res = CheckResult(
        name="test_metric",
        status=HealthStatus.WARNING,
        value=42.0,
        threshold="<= 40.0",
        message="Metric threshold warning",
    )
    raw = res.to_dict()
    assert raw["name"] == "test_metric"
    assert raw["status"] == "WARNING"
    assert raw["value"] == 42.0
    assert raw["threshold"] == "<= 40.0"
    assert raw["message"] == "Metric threshold warning"
