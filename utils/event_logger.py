import csv
import os
from datetime import datetime


LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "simulation_log.csv")


CSV_COLUMNS = [
    "timestamp",
    "event_type",
    "description",

    # Pump Station
    "temperature",
    "pressure",
    "water_level",
    "pump_status",

    # Conveyor Line
    "conveyor_status",
    "motor_speed",
    "motor_current",
    "emergency_stop",

    # Cooling System
    "fan_status",
    "coolant_temperature",
    "valve_position",
    "cooling_alarm",
]


def ensure_log_file():
    os.makedirs(LOG_DIR, exist_ok=True)

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(CSV_COLUMNS)


def normalize_state(state=None):
    if state is None:
        state = {}

    return {
        "temperature": state.get("temperature", ""),
        "pressure": state.get("pressure", ""),
        "water_level": state.get("water_level", ""),
        "pump_status": state.get("pump_status", ""),

        "conveyor_status": state.get("conveyor_status", ""),
        "motor_speed": state.get("motor_speed", ""),
        "motor_current": state.get("motor_current", ""),
        "emergency_stop": state.get("emergency_stop", ""),

        "fan_status": state.get("fan_status", ""),
        "coolant_temperature": state.get("coolant_temperature", ""),
        "valve_position": state.get("valve_position", ""),
        "cooling_alarm": state.get("cooling_alarm", ""),
    }


def log_event(event_type, description, state=None):
    ensure_log_file()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    normalized_state = normalize_state(state)

    row = [
        timestamp,
        event_type,
        description,

        normalized_state["temperature"],
        normalized_state["pressure"],
        normalized_state["water_level"],
        normalized_state["pump_status"],

        normalized_state["conveyor_status"],
        normalized_state["motor_speed"],
        normalized_state["motor_current"],
        normalized_state["emergency_stop"],

        normalized_state["fan_status"],
        normalized_state["coolant_temperature"],
        normalized_state["valve_position"],
        normalized_state["cooling_alarm"],
    ]

    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(row)


def read_logs(limit=100):
    ensure_log_file()

    with open(LOG_FILE, mode="r", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    return rows[-limit:]


if __name__ == "__main__":
    test_state = {
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

    log_event(
        event_type="TEST_EVENT",
        description="Logger test for 3 ICS systems",
        state=test_state
    )

    print("Test event written to logs/simulation_log.csv")