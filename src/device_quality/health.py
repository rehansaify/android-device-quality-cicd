"""Device health evaluation rules, metric thresholds, and status aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from device_quality.device import BootStatus, ConnectionStatus, Device


class HealthStatus(StrEnum):
    """Aggregate health state of the simulated Android device."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

    @property
    def severity(self) -> int:
        """Numeric weight used for severity comparisons and aggregation."""
        if self.value == "HEALTHY":
            return 0
        if self.value == "WARNING":
            return 1
        return 2

    def __lt__(self, other: object) -> bool:
        if isinstance(other, HealthStatus):
            return self.severity < other.severity
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, HealthStatus):
            return self.severity <= other.severity
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, HealthStatus):
            return self.severity > other.severity
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, HealthStatus):
            return self.severity >= other.severity
        return NotImplemented


@dataclass(frozen=True)
class CheckResult:
    """Individual health check inspection result."""

    name: str
    status: HealthStatus
    value: Any
    threshold: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert check result to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
        }


@dataclass(frozen=True)
class HealthReport:
    """Consolidated health report summarizing all rule evaluations."""

    overall_status: HealthStatus
    checks: list[CheckResult]
    is_eligible_for_testing: bool
    rejection_reasons: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert health report to dictionary."""
        return {
            "overall_status": self.overall_status.value,
            "is_eligible_for_testing": self.is_eligible_for_testing,
            "rejection_reasons": self.rejection_reasons,
            "warnings": self.warnings,
            "checks": [c.to_dict() for c in self.checks],
        }


class HealthEvaluator:
    """Evaluates an Android device against defined hardware quality thresholds."""

    BATTERY_CRITICAL_THRESHOLD: float = 10.0
    BATTERY_WARNING_THRESHOLD: float = 20.0

    TEMP_WARNING_THRESHOLD: float = 40.0
    TEMP_CRITICAL_THRESHOLD: float = 48.0

    STORAGE_WARNING_THRESHOLD: float = 85.0
    STORAGE_CRITICAL_THRESHOLD: float = 95.0

    def evaluate(self, device: Device) -> HealthReport:
        """Run all device checks and compute overall quality status."""
        checks: list[CheckResult] = [
            self._check_connection(device),
            self._check_boot(device),
            self._check_battery(device),
            self._check_temperature(device),
            self._check_storage(device),
        ]

        overall_status = max(checks, key=lambda c: c.status.severity).status
        is_eligible = overall_status != HealthStatus.CRITICAL

        rejection_reasons = [c.message for c in checks if c.status == HealthStatus.CRITICAL]
        warnings = [c.message for c in checks if c.status == HealthStatus.WARNING]

        return HealthReport(
            overall_status=overall_status,
            checks=checks,
            is_eligible_for_testing=is_eligible,
            rejection_reasons=rejection_reasons,
            warnings=warnings,
        )

    def _check_connection(self, device: Device) -> CheckResult:
        if device.connection_status == ConnectionStatus.CONNECTED:
            return CheckResult(
                name="connection_status",
                status=HealthStatus.HEALTHY,
                value=device.connection_status.value,
                threshold="CONNECTED",
                message="Device is connected via simulated ADB.",
            )
        msg = (
            f"Device connection status is '{device.connection_status.value}'; required: CONNECTED."
        )
        return CheckResult(
            name="connection_status",
            status=HealthStatus.CRITICAL,
            value=device.connection_status.value,
            threshold="CONNECTED",
            message=msg,
        )

    def _check_boot(self, device: Device) -> CheckResult:
        if device.boot_status == BootStatus.BOOTED:
            return CheckResult(
                name="boot_status",
                status=HealthStatus.HEALTHY,
                value=device.boot_status.value,
                threshold="BOOTED",
                message="Device system server has completed boot sequence.",
            )
        msg = f"Device boot status is '{device.boot_status.value}'; required: BOOTED."
        return CheckResult(
            name="boot_status",
            status=HealthStatus.CRITICAL,
            value=device.boot_status.value,
            threshold="BOOTED",
            message=msg,
        )

    def _check_battery(self, device: Device) -> CheckResult:
        val = float(device.battery_level)
        if val >= self.BATTERY_WARNING_THRESHOLD:
            return CheckResult(
                name="battery_level",
                status=HealthStatus.HEALTHY,
                value=round(val, 2),
                threshold=f">= {self.BATTERY_WARNING_THRESHOLD}%",
                message=f"Battery level is optimal ({val:.1f}%).",
            )
        if val >= self.BATTERY_CRITICAL_THRESHOLD:
            threshold_desc = (
                f">= {self.BATTERY_WARNING_THRESHOLD}% "
                f"(Warning: {self.BATTERY_CRITICAL_THRESHOLD}% - "
                f"{self.BATTERY_WARNING_THRESHOLD - 0.1:.1f}%)"
            )
            return CheckResult(
                name="battery_level",
                status=HealthStatus.WARNING,
                value=round(val, 2),
                threshold=threshold_desc,
                message=f"Low battery warning: {val:.1f}%. Device may discharge during test runs.",
            )
        crit_msg = (
            f"Critical battery level: {val:.1f}%. "
            "Insufficient power to sustain automated test suite."
        )
        return CheckResult(
            name="battery_level",
            status=HealthStatus.CRITICAL,
            value=round(val, 2),
            threshold=f">= {self.BATTERY_CRITICAL_THRESHOLD}%",
            message=crit_msg,
        )

    def _check_temperature(self, device: Device) -> CheckResult:
        temp = float(device.temperature)
        if temp <= self.TEMP_WARNING_THRESHOLD:
            return CheckResult(
                name="temperature",
                status=HealthStatus.HEALTHY,
                value=round(temp, 2),
                threshold=f"<= {self.TEMP_WARNING_THRESHOLD}°C",
                message=f"Device thermal profile is normal ({temp:.1f}°C).",
            )
        if temp <= self.TEMP_CRITICAL_THRESHOLD:
            threshold_desc = (
                f"<= {self.TEMP_WARNING_THRESHOLD}°C "
                f"(Warning: {self.TEMP_WARNING_THRESHOLD + 0.1:.1f}°C - "
                f"{self.TEMP_CRITICAL_THRESHOLD}°C)"
            )
            warn_msg = f"Elevated temperature warning: {temp:.1f}°C. Thermal throttling may occur."
            return CheckResult(
                name="temperature",
                status=HealthStatus.WARNING,
                value=round(temp, 2),
                threshold=threshold_desc,
                message=warn_msg,
            )
        crit_msg = (
            f"Critical thermal threshold exceeded: {temp:.1f}°C. "
            "Automated tests aborted to prevent damage."
        )
        return CheckResult(
            name="temperature",
            status=HealthStatus.CRITICAL,
            value=round(temp, 2),
            threshold=f"<= {self.TEMP_CRITICAL_THRESHOLD}°C",
            message=crit_msg,
        )

    def _check_storage(self, device: Device) -> CheckResult:
        storage = float(device.storage_usage)
        if storage <= self.STORAGE_WARNING_THRESHOLD:
            return CheckResult(
                name="storage_usage",
                status=HealthStatus.HEALTHY,
                value=round(storage, 2),
                threshold=f"<= {self.STORAGE_WARNING_THRESHOLD}%",
                message=f"Storage capacity is healthy ({storage:.1f}% utilized).",
            )
        if storage <= self.STORAGE_CRITICAL_THRESHOLD:
            threshold_desc = (
                f"<= {self.STORAGE_WARNING_THRESHOLD}% "
                f"(Warning: {self.STORAGE_WARNING_THRESHOLD + 0.1:.1f}% - "
                f"{self.STORAGE_CRITICAL_THRESHOLD}%)"
            )
            warn_msg = f"High storage warning: {storage:.1f}% used. Limited capacity for artifacts."
            return CheckResult(
                name="storage_usage",
                status=HealthStatus.WARNING,
                value=round(storage, 2),
                threshold=threshold_desc,
                message=warn_msg,
            )
        crit_msg = (
            f"Critical storage utilization: {storage:.1f}% utilized. "
            "Insufficient space to install build APK."
        )
        return CheckResult(
            name="storage_usage",
            status=HealthStatus.CRITICAL,
            value=round(storage, 2),
            threshold=f"<= {self.STORAGE_CRITICAL_THRESHOLD}%",
            message=crit_msg,
        )
