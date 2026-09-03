"""Android Device Quality Simulator and CI/CD Quality Gate Package."""

from device_quality.device import (
    BootStatus,
    ConnectionStatus,
    Device,
    DeviceValidationError,
)
from device_quality.health import (
    CheckResult,
    HealthEvaluator,
    HealthReport,
    HealthStatus,
)

__all__ = [
    "BootStatus",
    "CheckResult",
    "ConnectionStatus",
    "Device",
    "DeviceValidationError",
    "HealthEvaluator",
    "HealthReport",
    "HealthStatus",
]

__version__ = "0.1.0"