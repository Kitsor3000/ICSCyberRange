import csv
import os
from datetime import datetime


LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "simulation_log.csv")


def ensure_log_file():
    """
    Створює папку logs і CSV-файл журналу, якщо вони ще не існують.
    """

    os.makedirs(LOG_DIR, exist_ok=True)

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "timestamp",
                "event_type",
                "description",
                "temperature",
                "pressure",
                "water_level",
                "pump_status"
            ])


def log_event(event_type, description, state=None):
    """
    Записує подію симуляції у CSV-журнал.

    Args:
        event_type: тип події, наприклад MODBUS_COMMAND_INJECTION
        description: короткий опис події
        state: поточний стан PLC
    """

    ensure_log_file()

    if state is None:
        state = {}

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [
        timestamp,
        event_type,
        description,
        state.get("temperature", ""),
        state.get("pressure", ""),
        state.get("water_level", ""),
        state.get("pump_status", "")
    ]

    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(row)


def read_logs(limit=20):
    """
    Зчитує останні записи журналу.
    """

    ensure_log_file()

    with open(LOG_FILE, mode="r", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    return rows[-limit:]


if __name__ == "__main__":
    test_state = {
        "temperature": 25,
        "pressure": 5,
        "water_level": 50,
        "pump_status": 1
    }

    log_event(
        event_type="TEST_EVENT",
        description="Перевірка роботи event logger",
        state=test_state
    )

    print("Test event written to logs/simulation_log.csv")