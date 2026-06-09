"""
Tests for utils/event_logger.py

Covers: ensure_log_file(), normalize_state(), log_event(), read_logs()
Uses tmp_path + monkeypatch to redirect file I/O — no real logs are touched.
"""

import csv
import os
import pytest
import utils.event_logger as el

FULL_STATE = {
    "temperature": 28,
    "pressure": 5,
    "water_level": 60,
    "pump_status": 1,
    "conveyor_status": 1,
    "motor_speed": 70,
    "motor_current": 12,
    "emergency_stop": 0,
    "fan_status": 1,
    "coolant_temperature": 28,
    "valve_position": 70,
    "cooling_alarm": 0,
}


@pytest.fixture(autouse=True)
def redirect_log(tmp_path, monkeypatch):
    log_dir = str(tmp_path / "logs")
    log_file = str(tmp_path / "logs" / "simulation_log.csv")
    monkeypatch.setattr(el, "LOG_DIR", log_dir)
    monkeypatch.setattr(el, "LOG_FILE", log_file)
    return log_file


# ── normalize_state ───────────────────────────────────────────────────────────

def test_normalize_none_returns_empty_strings():
    result = el.normalize_state(None)
    assert all(v == "" for v in result.values())
    assert len(result) == 12


def test_normalize_empty_dict_returns_empty_strings():
    result = el.normalize_state({})
    assert all(v == "" for v in result.values())


def test_normalize_partial_state_fills_missing_with_empty():
    result = el.normalize_state({"temperature": 30})
    assert result["temperature"] == 30
    assert result["pressure"] == ""
    assert result["cooling_alarm"] == ""


def test_normalize_full_state_preserves_all_values():
    result = el.normalize_state(FULL_STATE)
    assert result["temperature"] == 28
    assert result["motor_speed"] == 70
    assert result["cooling_alarm"] == 0


def test_normalize_returns_all_12_keys():
    result = el.normalize_state({})
    expected = {
        "temperature", "pressure", "water_level", "pump_status",
        "conveyor_status", "motor_speed", "motor_current", "emergency_stop",
        "fan_status", "coolant_temperature", "valve_position", "cooling_alarm",
    }
    assert set(result.keys()) == expected


# ── ensure_log_file ───────────────────────────────────────────────────────────

def test_ensure_log_file_creates_directory_and_file(tmp_path, monkeypatch):
    log_dir = str(tmp_path / "new_logs")
    log_file = str(tmp_path / "new_logs" / "simulation_log.csv")
    monkeypatch.setattr(el, "LOG_DIR", log_dir)
    monkeypatch.setattr(el, "LOG_FILE", log_file)

    el.ensure_log_file()

    assert os.path.isdir(log_dir)
    assert os.path.isfile(log_file)


def test_ensure_log_file_writes_header(tmp_path, monkeypatch):
    log_dir = str(tmp_path / "logs2")
    log_file = str(tmp_path / "logs2" / "simulation_log.csv")
    monkeypatch.setattr(el, "LOG_DIR", log_dir)
    monkeypatch.setattr(el, "LOG_FILE", log_file)

    el.ensure_log_file()

    with open(log_file, "r", encoding="utf-8") as f:
        header = f.readline().strip()

    assert "timestamp" in header
    assert "event_type" in header
    assert "temperature" in header


def test_ensure_log_file_idempotent():
    el.ensure_log_file()
    el.ensure_log_file()  # second call must not raise or truncate


# ── log_event ─────────────────────────────────────────────────────────────────

def test_log_event_creates_one_row():
    el.log_event("TEST", "hello")
    rows = el.read_logs()
    assert len(rows) == 1


def test_log_event_stores_event_type():
    el.log_event("PUMP_ATTACK", "pump turned off")
    rows = el.read_logs()
    assert rows[0]["event_type"] == "PUMP_ATTACK"


def test_log_event_stores_description():
    el.log_event("INFO", "some description text")
    rows = el.read_logs()
    assert rows[0]["description"] == "some description text"


def test_log_event_with_state_stores_register_values():
    el.log_event("ATTACK", "test", FULL_STATE)
    rows = el.read_logs()
    assert rows[0]["temperature"] == "28"
    assert rows[0]["motor_speed"] == "70"
    assert rows[0]["cooling_alarm"] == "0"


def test_log_event_without_state_stores_empty_registers():
    el.log_event("INFO", "no state")
    rows = el.read_logs()
    assert rows[0]["temperature"] == ""
    assert rows[0]["fan_status"] == ""


def test_log_event_stores_timestamp():
    el.log_event("INFO", "ts check")
    rows = el.read_logs()
    ts = rows[0]["timestamp"]
    assert len(ts) == 19  # "YYYY-MM-DD HH:MM:SS"
    assert "-" in ts and ":" in ts


def test_log_event_multiple_rows_appended():
    for i in range(5):
        el.log_event(f"EVENT_{i}", f"desc {i}")
    rows = el.read_logs()
    assert len(rows) == 5


# ── read_logs ─────────────────────────────────────────────────────────────────

def test_read_logs_empty_file_returns_empty_list():
    result = el.read_logs()
    assert result == []


def test_read_logs_respects_limit():
    for i in range(20):
        el.log_event(f"EV_{i}", f"d {i}")
    result = el.read_logs(limit=7)
    assert len(result) == 7


def test_read_logs_returns_last_n_rows():
    for i in range(10):
        el.log_event(f"EV_{i}", f"d {i}")
    result = el.read_logs(limit=3)
    types = [r["event_type"] for r in result]
    assert types == ["EV_7", "EV_8", "EV_9"]


def test_read_logs_default_limit_100():
    for i in range(50):
        el.log_event("X", "y")
    result = el.read_logs()
    assert len(result) == 50  # all 50 fit within default limit of 100


def test_read_logs_row_has_all_columns():
    el.log_event("TEST", "check cols", FULL_STATE)
    row = el.read_logs()[0]
    for col in ("timestamp", "event_type", "description", "coolant_temperature", "valve_position"):
        assert col in row
