"""
Tests for utils/modbus_client.py

Covers: ICSModbusClient — init, connect, read_registers, write_register,
        all pump/conveyor/cooling helper methods, REGISTER_MAP integrity.
Modbus TCP is fully mocked — no real PLC required.
"""

import pytest
from unittest.mock import MagicMock, patch
from utils.modbus_client import ICSModbusClient, REGISTER_MAP


def _make_modbus(connect_ok=True, read_ok=True, write_ok=True):
    """Return a mock ModbusTcpClient with configurable behaviour."""
    mock = MagicMock()
    mock.connect.return_value = connect_ok

    read_result = MagicMock()
    read_result.isError.return_value = not read_ok
    read_result.registers = [28, 5, 60, 1, 1, 70, 12, 0, 1, 28, 70, 0]
    mock.read_holding_registers.return_value = read_result

    write_result = MagicMock()
    write_result.isError.return_value = not write_ok
    mock.write_register.return_value = write_result

    return mock


# ── __init__ ──────────────────────────────────────────────────────────────────

@patch("utils.modbus_client.ModbusTcpClient")
def test_default_host_and_port(MockClient):
    plc = ICSModbusClient()
    assert plc.host == "127.0.0.1"
    assert plc.port == 5020


@patch("utils.modbus_client.ModbusTcpClient")
def test_custom_host_and_port(MockClient):
    plc = ICSModbusClient(host="10.0.0.1", port=502)
    assert plc.host == "10.0.0.1"
    assert plc.port == 502


@patch("utils.modbus_client.ModbusTcpClient")
def test_constructor_passes_host_port_to_underlying_client(MockClient):
    ICSModbusClient(host="192.168.1.5", port=5021)
    MockClient.assert_called_once_with(host="192.168.1.5", port=5021)


# ── connect / close ───────────────────────────────────────────────────────────

@patch("utils.modbus_client.ModbusTcpClient")
def test_connect_returns_true_on_success(MockClient):
    MockClient.return_value = _make_modbus(connect_ok=True)
    assert ICSModbusClient().connect() is True


@patch("utils.modbus_client.ModbusTcpClient")
def test_connect_returns_false_on_failure(MockClient):
    MockClient.return_value = _make_modbus(connect_ok=False)
    assert ICSModbusClient().connect() is False


@patch("utils.modbus_client.ModbusTcpClient")
def test_close_delegates_to_underlying_client(MockClient):
    mock_client = _make_modbus()
    MockClient.return_value = mock_client
    plc = ICSModbusClient()
    plc.close()
    mock_client.close.assert_called_once()


# ── read_registers ────────────────────────────────────────────────────────────

@patch("utils.modbus_client.ModbusTcpClient")
def test_read_registers_returns_12_key_dict(MockClient):
    MockClient.return_value = _make_modbus()
    data = ICSModbusClient().read_registers()
    assert isinstance(data, dict)
    assert len(data) == 12


@patch("utils.modbus_client.ModbusTcpClient")
def test_read_registers_maps_correctly(MockClient):
    MockClient.return_value = _make_modbus()
    data = ICSModbusClient().read_registers()
    assert data["temperature"] == 28
    assert data["pressure"] == 5
    assert data["water_level"] == 60
    assert data["pump_status"] == 1
    assert data["motor_speed"] == 70
    assert data["fan_status"] == 1
    assert data["valve_position"] == 70
    assert data["cooling_alarm"] == 0


@patch("utils.modbus_client.ModbusTcpClient")
def test_read_registers_raises_on_error(MockClient):
    MockClient.return_value = _make_modbus(read_ok=False)
    with pytest.raises(RuntimeError):
        ICSModbusClient().read_registers()


# ── write_register ────────────────────────────────────────────────────────────

@patch("utils.modbus_client.ModbusTcpClient")
def test_write_register_by_tag_name(MockClient):
    mock_client = _make_modbus()
    MockClient.return_value = mock_client
    result = ICSModbusClient().write_register("pump_status", 1)
    assert result is True
    mock_client.write_register.assert_called_once_with(3, 1, unit=1)


@patch("utils.modbus_client.ModbusTcpClient")
def test_write_register_by_numeric_address(MockClient):
    mock_client = _make_modbus()
    MockClient.return_value = mock_client
    ICSModbusClient().write_register(5, 80)
    mock_client.write_register.assert_called_once_with(5, 80, unit=1)


@patch("utils.modbus_client.ModbusTcpClient")
def test_write_register_raises_on_error(MockClient):
    MockClient.return_value = _make_modbus(write_ok=False)
    with pytest.raises(RuntimeError):
        ICSModbusClient().write_register("pump_status", 0)


@patch("utils.modbus_client.ModbusTcpClient")
def test_write_register_casts_value_to_int(MockClient):
    mock_client = _make_modbus()
    MockClient.return_value = mock_client
    ICSModbusClient().write_register("motor_speed", 75.9)
    mock_client.write_register.assert_called_once_with(5, 75, unit=1)


# ── Pump helpers ──────────────────────────────────────────────────────────────

@patch("utils.modbus_client.ModbusTcpClient")
def test_turn_pump_on(MockClient):
    m = _make_modbus(); MockClient.return_value = m
    ICSModbusClient().turn_pump_on()
    m.write_register.assert_called_once_with(3, 1, unit=1)


@patch("utils.modbus_client.ModbusTcpClient")
def test_turn_pump_off(MockClient):
    m = _make_modbus(); MockClient.return_value = m
    ICSModbusClient().turn_pump_off()
    m.write_register.assert_called_once_with(3, 0, unit=1)


@patch("utils.modbus_client.ModbusTcpClient")
def test_set_fake_temperature(MockClient):
    m = _make_modbus(); MockClient.return_value = m
    ICSModbusClient().set_fake_temperature(200)
    m.write_register.assert_called_once_with(0, 200, unit=1)


# ── Conveyor helpers ──────────────────────────────────────────────────────────

@patch("utils.modbus_client.ModbusTcpClient")
def test_set_motor_speed(MockClient):
    m = _make_modbus(); MockClient.return_value = m
    ICSModbusClient().set_motor_speed(85)
    m.write_register.assert_called_once_with(5, 85, unit=1)


@patch("utils.modbus_client.ModbusTcpClient")
def test_trigger_emergency_stop(MockClient):
    m = _make_modbus(); MockClient.return_value = m
    ICSModbusClient().trigger_emergency_stop()
    m.write_register.assert_called_once_with(7, 1, unit=1)


@patch("utils.modbus_client.ModbusTcpClient")
def test_clear_emergency_stop(MockClient):
    m = _make_modbus(); MockClient.return_value = m
    ICSModbusClient().clear_emergency_stop()
    m.write_register.assert_called_once_with(7, 0, unit=1)


# ── Cooling helpers ───────────────────────────────────────────────────────────

@patch("utils.modbus_client.ModbusTcpClient")
def test_turn_fan_on(MockClient):
    m = _make_modbus(); MockClient.return_value = m
    ICSModbusClient().turn_fan_on()
    m.write_register.assert_called_once_with(8, 1, unit=1)


@patch("utils.modbus_client.ModbusTcpClient")
def test_turn_fan_off(MockClient):
    m = _make_modbus(); MockClient.return_value = m
    ICSModbusClient().turn_fan_off()
    m.write_register.assert_called_once_with(8, 0, unit=1)


@patch("utils.modbus_client.ModbusTcpClient")
def test_set_valve_position(MockClient):
    m = _make_modbus(); MockClient.return_value = m
    ICSModbusClient().set_valve_position(50)
    m.write_register.assert_called_once_with(10, 50, unit=1)


# ── REGISTER_MAP integrity ────────────────────────────────────────────────────

def test_register_map_has_all_12_tags():
    expected = {
        "temperature", "pressure", "water_level", "pump_status",
        "conveyor_status", "motor_speed", "motor_current", "emergency_stop",
        "fan_status", "coolant_temperature", "valve_position", "cooling_alarm",
    }
    assert set(REGISTER_MAP.keys()) == expected


def test_register_map_addresses_are_sequential_0_to_11():
    assert sorted(REGISTER_MAP.values()) == list(range(12))


def test_register_map_pump_station_addresses():
    assert REGISTER_MAP["temperature"] == 0
    assert REGISTER_MAP["pressure"] == 1
    assert REGISTER_MAP["water_level"] == 2
    assert REGISTER_MAP["pump_status"] == 3


def test_register_map_conveyor_line_addresses():
    assert REGISTER_MAP["conveyor_status"] == 4
    assert REGISTER_MAP["motor_speed"] == 5
    assert REGISTER_MAP["motor_current"] == 6
    assert REGISTER_MAP["emergency_stop"] == 7


def test_register_map_cooling_system_addresses():
    assert REGISTER_MAP["fan_status"] == 8
    assert REGISTER_MAP["coolant_temperature"] == 9
    assert REGISTER_MAP["valve_position"] == 10
    assert REGISTER_MAP["cooling_alarm"] == 11
