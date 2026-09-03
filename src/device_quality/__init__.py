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
from device_quality.runner import (
    QualityRunner,
    RunReport,
    TestCaseResult,
    get_sample_device,
    main,
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
    "QualityRunner",
    "RunReport",
    "TestCaseResult",
    "get_sample_device",
    "main",
]

__version__ = "0.1.0"
