"""
Tests for defense/anomaly_detector.py

Covers: detect_anomalies(), NORMAL_RANGES, SYSTEM_MAP, RECOVERY_HINTS
All tests are pure-Python — no Modbus connection required.
"""

import pytest
from defense.anomaly_detector import detect_anomalies, NORMAL_RANGES, SYSTEM_MAP, RECOVERY_HINTS

NORMAL_STATE = {
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


# ── detect_anomalies ──────────────────────────────────────────────────────────

def test_normal_state_produces_no_alerts():
    assert detect_anomalies(NORMAL_STATE) == []


def test_pump_off_triggers_alert():
    alerts = detect_anomalies({**NORMAL_STATE, "pump_status": 0})
    tags = [a["tag"] for a in alerts]
    assert "pump_status" in tags


def test_pump_off_alert_has_correct_system():
    alerts = detect_anomalies({**NORMAL_STATE, "pump_status": 0})
    pump_alert = next(a for a in alerts if a["tag"] == "pump_status")
    assert pump_alert["system"] == "Pump Station"


def test_high_temperature_triggers_alert():
    alerts = detect_anomalies({**NORMAL_STATE, "temperature": 60})
    assert any(a["tag"] == "temperature" for a in alerts)


def test_low_temperature_triggers_alert():
    alerts = detect_anomalies({**NORMAL_STATE, "temperature": 5})
    assert any(a["tag"] == "temperature" for a in alerts)


def test_temperature_at_lower_bound_is_normal():
    alerts = detect_anomalies({**NORMAL_STATE, "temperature": 18})
    assert not any(a["tag"] == "temperature" for a in alerts)


def test_temperature_at_upper_bound_is_normal():
    alerts = detect_anomalies({**NORMAL_STATE, "temperature": 45})
    assert not any(a["tag"] == "temperature" for a in alerts)


def test_emergency_stop_active_triggers_alert():
    alerts = detect_anomalies({**NORMAL_STATE, "emergency_stop": 1})
    assert any(a["tag"] == "emergency_stop" for a in alerts)
    assert any(a["system"] == "Conveyor Line" for a in alerts)


def test_cooling_alarm_active_triggers_alert():
    alerts = detect_anomalies({**NORMAL_STATE, "cooling_alarm": 1})
    assert any(a["tag"] == "cooling_alarm" for a in alerts)
    assert any(a["system"] == "Cooling System" for a in alerts)


def test_fan_off_triggers_alert():
    alerts = detect_anomalies({**NORMAL_STATE, "fan_status": 0})
    assert any(a["tag"] == "fan_status" for a in alerts)


def test_motor_speed_overdrive_triggers_alert():
    alerts = detect_anomalies({**NORMAL_STATE, "motor_speed": 130})
    assert any(a["tag"] == "motor_speed" for a in alerts)


def test_low_water_level_triggers_alert():
    alerts = detect_anomalies({**NORMAL_STATE, "water_level": 10})
    assert any(a["tag"] == "water_level" for a in alerts)


def test_valve_closed_triggers_alert():
    alerts = detect_anomalies({**NORMAL_STATE, "valve_position": 0})
    assert any(a["tag"] == "valve_position" for a in alerts)


def test_multiple_anomalies_all_reported():
    state = {**NORMAL_STATE, "pump_status": 0, "fan_status": 0, "emergency_stop": 1}
    alerts = detect_anomalies(state)
    tags = {a["tag"] for a in alerts}
    assert "pump_status" in tags
    assert "fan_status" in tags
    assert "emergency_stop" in tags


def test_alert_contains_required_fields():
    alerts = detect_anomalies({**NORMAL_STATE, "temperature": 99})
    alert = alerts[0]
    for field in ("system", "tag", "value", "normal_range", "message", "recovery_hint"):
        assert field in alert, f"Missing field: {field}"


def test_alert_value_matches_input():
    alerts = detect_anomalies({**NORMAL_STATE, "temperature": 99})
    temp_alert = next(a for a in alerts if a["tag"] == "temperature")
    assert temp_alert["value"] == 99


def test_alert_normal_range_format():
    alerts = detect_anomalies({**NORMAL_STATE, "temperature": 99})
    alert = alerts[0]
    assert " - " in alert["normal_range"]


def test_coolant_temp_high_triggers_alert():
    alerts = detect_anomalies({**NORMAL_STATE, "coolant_temperature": 55})
    assert any(a["tag"] == "coolant_temperature" for a in alerts)


def test_conveyor_off_triggers_alert():
    alerts = detect_anomalies({**NORMAL_STATE, "conveyor_status": 0})
    assert any(a["tag"] == "conveyor_status" for a in alerts)


# ── Constants integrity ───────────────────────────────────────────────────────

def test_normal_ranges_covers_all_12_tags():
    expected = {
        "temperature", "pressure", "water_level", "pump_status",
        "conveyor_status", "motor_speed", "motor_current", "emergency_stop",
        "fan_status", "coolant_temperature", "valve_position", "cooling_alarm",
    }
    assert set(NORMAL_RANGES.keys()) == expected


def test_system_map_covers_all_12_tags():
    assert len(SYSTEM_MAP) == 12


def test_recovery_hints_cover_three_systems():
    assert "Pump Station" in RECOVERY_HINTS
    assert "Conveyor Line" in RECOVERY_HINTS
    assert "Cooling System" in RECOVERY_HINTS


def test_normal_ranges_are_valid_tuples():
    for tag, (lo, hi) in NORMAL_RANGES.items():
        assert lo <= hi, f"Invalid range for {tag}: ({lo}, {hi})"
