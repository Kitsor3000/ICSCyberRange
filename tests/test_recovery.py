"""
Tests for defense/recovery.py

Covers: recover_by_attack(), ATTACK_TO_RECOVERY mapping, NORMAL_VALUES,
        recover_pump_station/conveyor_line/cooling_system/full_system.
Modbus TCP is fully mocked — no real PLC required.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from defense.recovery import (
    recover_by_attack,
    ATTACK_TO_RECOVERY,
    NORMAL_VALUES,
    REGISTER_MAP,
)


def _make_modbus():
    mock = MagicMock()
    mock.connect.return_value = True

    read_result = MagicMock()
    read_result.isError.return_value = False
    read_result.registers = [28, 5, 60, 1, 1, 70, 12, 0, 1, 28, 70, 0]
    mock.read_holding_registers.return_value = read_result

    write_result = MagicMock()
    write_result.isError.return_value = False
    mock.write_register.return_value = write_result

    return mock


# ── recover_by_attack ─────────────────────────────────────────────────────────

def test_recover_by_attack_unknown_raises_value_error():
    with pytest.raises(ValueError, match="Unknown attack"):
        recover_by_attack("no_such_attack")


@patch("defense.recovery.ModbusTcpClient")
def test_recover_by_attack_pump_off_calls_pump_recovery(MockClient):
    MockClient.return_value = _make_modbus()
    recover_by_attack("pump_off")
    assert MockClient.called


@patch("defense.recovery.ModbusTcpClient")
def test_recover_by_attack_conveyor_stop_calls_conveyor_recovery(MockClient):
    MockClient.return_value = _make_modbus()
    recover_by_attack("conveyor_stop")
    assert MockClient.called


@patch("defense.recovery.ModbusTcpClient")
def test_recover_by_attack_fan_shutdown_calls_cooling_recovery(MockClient):
    MockClient.return_value = _make_modbus()
    recover_by_attack("fan_shutdown")
    assert MockClient.called


@patch("defense.recovery.ModbusTcpClient")
def test_recover_pump_station_writes_four_registers(MockClient):
    from defense.recovery import recover_pump_station
    mock_client = _make_modbus()
    MockClient.return_value = mock_client

    recover_pump_station()

    written_addresses = [c.args[0] for c in mock_client.write_register.call_args_list]
    pump_addresses = {REGISTER_MAP[t] for t in ["temperature", "pressure", "water_level", "pump_status"]}
    assert pump_addresses.issubset(set(written_addresses))


@patch("defense.recovery.ModbusTcpClient")
def test_recover_conveyor_line_writes_four_registers(MockClient):
    from defense.recovery import recover_conveyor_line
    mock_client = _make_modbus()
    MockClient.return_value = mock_client

    recover_conveyor_line()

    written_addresses = [c.args[0] for c in mock_client.write_register.call_args_list]
    conveyor_addresses = {REGISTER_MAP[t] for t in ["conveyor_status", "motor_speed", "motor_current", "emergency_stop"]}
    assert conveyor_addresses.issubset(set(written_addresses))


@patch("defense.recovery.ModbusTcpClient")
def test_recover_cooling_system_writes_four_registers(MockClient):
    from defense.recovery import recover_cooling_system
    mock_client = _make_modbus()
    MockClient.return_value = mock_client

    recover_cooling_system()

    written_addresses = [c.args[0] for c in mock_client.write_register.call_args_list]
    cooling_addresses = {REGISTER_MAP[t] for t in ["fan_status", "coolant_temperature", "valve_position", "cooling_alarm"]}
    assert cooling_addresses.issubset(set(written_addresses))


@patch("defense.recovery.ModbusTcpClient")
def test_recover_full_system_writes_all_12_registers(MockClient):
    from defense.recovery import recover_full_system
    mock_client = _make_modbus()
    MockClient.return_value = mock_client

    recover_full_system()

    written_addresses = {c.args[0] for c in mock_client.write_register.call_args_list}
    assert written_addresses == set(range(12))


@patch("defense.recovery.ModbusTcpClient")
def test_recover_pump_station_restores_pump_on(MockClient):
    from defense.recovery import recover_pump_station
    mock_client = _make_modbus()
    MockClient.return_value = mock_client

    recover_pump_station()

    pump_writes = [
        (c.args[0], c.args[1])
        for c in mock_client.write_register.call_args_list
        if c.args[0] == REGISTER_MAP["pump_status"]
    ]
    assert pump_writes, "pump_status was never written"
    assert pump_writes[-1][1] == NORMAL_VALUES["pump_status"]


@patch("defense.recovery.ModbusTcpClient")
def test_recover_cooling_restores_fan_on(MockClient):
    from defense.recovery import recover_cooling_system
    mock_client = _make_modbus()
    MockClient.return_value = mock_client

    recover_cooling_system()

    fan_writes = [
        (c.args[0], c.args[1])
        for c in mock_client.write_register.call_args_list
        if c.args[0] == REGISTER_MAP["fan_status"]
    ]
    assert fan_writes
    assert fan_writes[-1][1] == NORMAL_VALUES["fan_status"]


# ── ATTACK_TO_RECOVERY mapping ────────────────────────────────────────────────

def test_all_pump_attacks_map_to_pump():
    for attack in ["pump_off", "pump_false_data", "water_level_spoofing"]:
        assert ATTACK_TO_RECOVERY[attack] == "pump", f"{attack} should map to pump"


def test_all_conveyor_attacks_map_to_conveyor():
    for attack in ["conveyor_stop", "motor_speed_overdrive", "emergency_stop_abuse"]:
        assert ATTACK_TO_RECOVERY[attack] == "conveyor", f"{attack} should map to conveyor"


def test_all_cooling_attacks_map_to_cooling():
    for attack in ["fan_shutdown", "valve_manipulation", "cooling_temp_spoofing"]:
        assert ATTACK_TO_RECOVERY[attack] == "cooling", f"{attack} should map to cooling"


def test_attack_to_recovery_covers_9_attacks():
    assert len(ATTACK_TO_RECOVERY) == 9


# ── NORMAL_VALUES integrity ───────────────────────────────────────────────────

def test_normal_values_has_all_12_tags():
    expected = {
        "temperature", "pressure", "water_level", "pump_status",
        "conveyor_status", "motor_speed", "motor_current", "emergency_stop",
        "fan_status", "coolant_temperature", "valve_position", "cooling_alarm",
    }
    assert set(NORMAL_VALUES.keys()) == expected


def test_normal_values_safe_statuses():
    assert NORMAL_VALUES["pump_status"] == 1
    assert NORMAL_VALUES["conveyor_status"] == 1
    assert NORMAL_VALUES["fan_status"] == 1
    assert NORMAL_VALUES["emergency_stop"] == 0
    assert NORMAL_VALUES["cooling_alarm"] == 0


def test_normal_values_tags_match_register_map():
    for tag in NORMAL_VALUES:
        assert tag in REGISTER_MAP, f"{tag} in NORMAL_VALUES but missing from REGISTER_MAP"
