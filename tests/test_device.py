"""Tests for Device data model, validation rules, and serialization."""

import json

import pytest

from device_quality.device import (
    BootStatus,
    ConnectionStatus,
    Device,
    DeviceValidationError,
)


def test_valid_device_instantiation() -> None:
    """Ensure a properly configured device instantiates and retains attributes."""
    device = Device(
        model="Pixel 8 Pro",
        android_version="14.0",
        battery_level=85.5,
        storage_usage=45.2,
        temperature=32.0,
        connection_status=ConnectionStatus.CONNECTED,
        boot_status=BootStatus.BOOTED,
    )

    assert device.model == "Pixel 8 Pro"
    assert device.android_version == "14.0"
    assert device.battery_level == 85.5
    assert device.storage_usage == 45.2
    assert device.temperature == 32.0
    assert device.connection_status == ConnectionStatus.CONNECTED
    assert device.boot_status == BootStatus.BOOTED


def test_device_to_dict_serialization() -> None:
    """Verify dictionary serialization preserves data formats."""
    device = Device(
        model="Galaxy S23",
        android_version="13.0",
        battery_level=90.0,
        storage_usage=25.0,
        temperature=28.5,
        connection_status=ConnectionStatus.CONNECTED,
        boot_status=BootStatus.BOOTED,
    )

    expected = {
        "model": "Galaxy S23",
        "android_version": "13.0",
        "battery_level": 90.0,
        "storage_usage": 25.0,
        "temperature": 28.5,
        "connection_status": "CONNECTED",
        "boot_status": "BOOTED",
    }
    assert device.to_dict() == expected


def test_device_from_dict_success() -> None:
    """Verify parsing from dictionary with string enum values and numeric conversion."""
    raw = {
        "model": "Xiaomi 13",
        "android_version": "13.0",
        "battery_level": "77.5",
        "storage_usage": 60,
        "temperature": 35.2,
        "connection_status": "connected",
        "boot_status": "booted",
    }

    device = Device.from_dict(raw)
    assert device.model == "Xiaomi 13"
    assert device.battery_level == 77.5
    assert device.storage_usage == 60.0
    assert device.connection_status == ConnectionStatus.CONNECTED
    assert device.boot_status == BootStatus.BOOTED


def test_device_from_json_success() -> None:
    """Verify parsing from a valid JSON string."""
    payload = json.dumps(
        {
            "model": "OnePlus 11",
            "android_version": "14",
            "battery_level": 80.0,
            "storage_usage": 50.0,
            "temperature": 30.0,
            "connection_status": "CONNECTED",
            "boot_status": "BOOTED",
        }
    )

    device = Device.from_json(payload)
    assert device.model == "OnePlus 11"
    assert device.connection_status == ConnectionStatus.CONNECTED


@pytest.mark.parametrize(
    "invalid_field,value,match",
    [
        ("model", "", "Device model must be a non-empty string"),
        ("model", "   ", "Device model must be a non-empty string"),
        ("android_version", "", "Android version must be a non-empty string"),
        ("battery_level", -1.0, "Battery level -1.0% is out of bounds"),
        ("battery_level", 100.1, "Battery level 100.1% is out of bounds"),
        ("battery_level", True, "Battery level must be a numeric percentage"),
        ("battery_level", "not-a-number", "Battery level must be a numeric percentage"),
        ("storage_usage", -0.5, "Storage usage -0.5% is out of bounds"),
        ("storage_usage", 101.0, "Storage usage 101.0% is out of bounds"),
        ("storage_usage", False, "Storage usage must be a numeric percentage"),
        ("temperature", -25.0, "outside valid operational bounds"),
        ("temperature", 105.0, "outside valid operational bounds"),
        ("connection_status", "ONLINE", "connection_status must be a ConnectionStatus enum"),
        ("boot_status", "READY", "boot_status must be a BootStatus enum"),
    ],
)
def test_device_post_init_validation_errors(invalid_field: str, value: object, match: str) -> None:
    """Ensure invalid field values trigger DeviceValidationError on instantiation."""
    valid_args: dict[str, object] = {
        "model": "Pixel 7",
        "android_version": "13.0",
        "battery_level": 80.0,
        "storage_usage": 50.0,
        "temperature": 30.0,
        "connection_status": ConnectionStatus.CONNECTED,
        "boot_status": BootStatus.BOOTED,
    }
    valid_args[invalid_field] = value

    with pytest.raises(DeviceValidationError, match=match):
        Device(**valid_args)  # type: ignore[arg-type]


def test_device_from_dict_missing_fields() -> None:
    """Verify missing required keys in dict raises DeviceValidationError."""
    incomplete_data = {
        "model": "Pixel 7",
        "android_version": "13.0",
    }
    with pytest.raises(DeviceValidationError, match="Missing required device fields"):
        Device.from_dict(incomplete_data)


def test_device_from_dict_non_dict_input() -> None:
    """Verify non-dict payload raises DeviceValidationError."""
    with pytest.raises(DeviceValidationError, match="Expected dictionary for device data"):
        Device.from_dict(["not", "a", "dict"])  # type: ignore[arg-type]


def test_device_from_json_malformed_syntax() -> None:
    """Verify invalid JSON syntax raises DeviceValidationError."""
    with pytest.raises(DeviceValidationError, match="Malformed JSON device payload"):
        Device.from_json("{invalid_json: true,}")


def test_device_from_json_non_dict_root() -> None:
    """Verify non-object JSON root raises DeviceValidationError."""
    with pytest.raises(DeviceValidationError, match="Root JSON value must be an object"):
        Device.from_json('["an", "array"]')


def test_invalid_enum_strings_in_from_dict() -> None:
    """Verify invalid enum strings provide descriptive errors listing valid values."""
    payload = {
        "model": "Pixel 7",
        "android_version": "13.0",
        "battery_level": 80.0,
        "storage_usage": 50.0,
        "temperature": 30.0,
        "connection_status": "UNKNOWN_CONN",
        "boot_status": "BOOTED",
    }
    with pytest.raises(DeviceValidationError, match="Invalid connection_status: 'UNKNOWN_CONN'"):
        Device.from_dict(payload)

    payload["connection_status"] = "CONNECTED"
    payload["boot_status"] = "FASTBOOT"
    with pytest.raises(DeviceValidationError, match="Invalid boot_status: 'FASTBOOT'"):
        Device.from_dict(payload)
