"""Device model and validation logic for simulated Android devices."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ConnectionStatus(StrEnum):
    """Represents the connection state between the test harness and device."""

    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    UNAUTHORIZED = "UNAUTHORIZED"

    @classmethod
    def from_str(cls, value: str) -> ConnectionStatus:
        """Parse string to ConnectionStatus case-insensitively."""
        normalized = value.strip().upper()
        for item in cls:
            if item.value == normalized:
                return item
        valid = [item.value for item in cls]
        raise DeviceValidationError(
            f"Invalid connection_status: '{value}'. Expected one of: {valid}"
        )


class BootStatus(StrEnum):
    """Represents the operating boot state of the Android device."""

    BOOTED = "BOOTED"
    BOOTING = "BOOTING"
    RECOVERY = "RECOVERY"
    OFFLINE = "OFFLINE"

    @classmethod
    def from_str(cls, value: str) -> BootStatus:
        """Parse string to BootStatus case-insensitively."""
        normalized = value.strip().upper()
        for item in cls:
            if item.value == normalized:
                return item
        valid = [item.value for item in cls]
        raise DeviceValidationError(f"Invalid boot_status: '{value}'. Expected one of: {valid}")


class DeviceValidationError(ValueError):
    """Raised when device telemetry or configuration fails schema validation."""


@dataclass(frozen=True)
class Device:
    """Represents an Android device under test with simulated hardware metrics."""

    model: str
    android_version: str
    battery_level: float
    storage_usage: float
    temperature: float
    connection_status: ConnectionStatus
    boot_status: BootStatus

    def __post_init__(self) -> None:
        """Validate simulated device metric ranges and values."""
        if not isinstance(self.model, str) or not self.model.strip():
            raise DeviceValidationError("Device model must be a non-empty string.")

        if not isinstance(self.android_version, str) or not str(self.android_version).strip():
            raise DeviceValidationError("Android version must be a non-empty string.")

        # Validate numeric metrics
        if not isinstance(self.battery_level, (int, float)) or isinstance(self.battery_level, bool):
            raise DeviceValidationError("Battery level must be a numeric percentage.")
        if not (0.0 <= float(self.battery_level) <= 100.0):
            raise DeviceValidationError(
                f"Battery level {self.battery_level}% is out of bounds (0.0 - 100.0%)."
            )

        if not isinstance(self.storage_usage, (int, float)) or isinstance(self.storage_usage, bool):
            raise DeviceValidationError("Storage usage must be a numeric percentage.")
        if not (0.0 <= float(self.storage_usage) <= 100.0):
            raise DeviceValidationError(
                f"Storage usage {self.storage_usage}% is out of bounds (0.0 - 100.0%)."
            )

        if not isinstance(self.temperature, (int, float)) or isinstance(self.temperature, bool):
            raise DeviceValidationError("Temperature must be a numeric Celsius value.")
        if not (-20.0 <= float(self.temperature) <= 100.0):
            msg = (
                f"Temperature {self.temperature}°C is outside "
                "valid operational bounds (-20.0 - 100.0°C)."
            )
            raise DeviceValidationError(msg)

        if not isinstance(self.connection_status, ConnectionStatus):
            msg = (
                "connection_status must be a ConnectionStatus enum, "
                f"got: {type(self.connection_status).__name__}"
            )
            raise DeviceValidationError(msg)

        if not isinstance(self.boot_status, BootStatus):
            msg = f"boot_status must be a BootStatus enum, got: {type(self.boot_status).__name__}"
            raise DeviceValidationError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Serialize device state to dictionary."""
        return {
            "model": self.model,
            "android_version": self.android_version,
            "battery_level": round(float(self.battery_level), 2),
            "storage_usage": round(float(self.storage_usage), 2),
            "temperature": round(float(self.temperature), 2),
            "connection_status": self.connection_status.value,
            "boot_status": self.boot_status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Device:
        """Instantiate Device from a raw dictionary with validation."""
        if not isinstance(data, dict):
            raise DeviceValidationError(
                f"Expected dictionary for device data, got: {type(data).__name__}"
            )

        required_keys = {
            "model",
            "android_version",
            "battery_level",
            "storage_usage",
            "temperature",
            "connection_status",
            "boot_status",
        }
        missing_keys = required_keys - set(data.keys())
        if missing_keys:
            sorted_missing = sorted(missing_keys)
            raise DeviceValidationError(f"Missing required device fields: {sorted_missing}")

        try:
            battery = float(data["battery_level"])
        except (ValueError, TypeError) as err:
            raise DeviceValidationError(
                f"Invalid battery_level value: {data['battery_level']}"
            ) from err

        try:
            storage = float(data["storage_usage"])
        except (ValueError, TypeError) as err:
            raise DeviceValidationError(
                f"Invalid storage_usage value: {data['storage_usage']}"
            ) from err

        try:
            temp = float(data["temperature"])
        except (ValueError, TypeError) as err:
            raise DeviceValidationError(
                f"Invalid temperature value: {data['temperature']}"
            ) from err

        raw_conn = data["connection_status"]
        conn_status = (
            raw_conn
            if isinstance(raw_conn, ConnectionStatus)
            else ConnectionStatus.from_str(str(raw_conn))
        )

        raw_boot = data["boot_status"]
        boot_status = (
            raw_boot if isinstance(raw_boot, BootStatus) else BootStatus.from_str(str(raw_boot))
        )

        return cls(
            model=str(data["model"]),
            android_version=str(data["android_version"]),
            battery_level=battery,
            storage_usage=storage,
            temperature=temp,
            connection_status=conn_status,
            boot_status=boot_status,
        )

    @classmethod
    def from_json(cls, json_str: str) -> Device:
        """Instantiate Device from a JSON string."""
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as err:
            raise DeviceValidationError(f"Malformed JSON device payload: {err}") from err

        if not isinstance(parsed, dict):
            raise DeviceValidationError(
                "Root JSON value must be an object representing device properties."
            )

        return cls.from_dict(parsed)
