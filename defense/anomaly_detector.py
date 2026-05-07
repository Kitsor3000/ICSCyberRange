import time
from pymodbus.client.sync import ModbusTcpClient


PLC_HOST = "127.0.0.1"
PLC_PORT = 5020


NORMAL_RANGES = {
    "temperature": (0, 80),
    "pressure": (1, 15),
    "water_level": (10, 90),
    "pump_status": (0, 1),
}


def read_plc_state(client):
    """
    Зчитування стану PLC через Modbus TCP.

    Register 0 — Temperature
    Register 1 — Pressure
    Register 2 — Water Level
    Register 3 — Pump Status
    """

    result = client.read_holding_registers(0, 4, unit=1)

    if result.isError():
        raise Exception("Не вдалося зчитати регістри PLC")

    return {
        "temperature": result.registers[0],
        "pressure": result.registers[1],
        "water_level": result.registers[2],
        "pump_status": result.registers[3],
    }


def detect_anomalies(state):
    """
    Перевірка значень PLC на вихід за нормальні межі.
    """

    alerts = []

    for tag, value in state.items():
        min_value, max_value = NORMAL_RANGES[tag]

        if value < min_value or value > max_value:
            alerts.append({
                "tag": tag,
                "value": value,
                "normal_range": f"{min_value} - {max_value}",
                "message": f"Аномалія: {tag} = {value}, норма: {min_value} - {max_value}"
            })

    return alerts


def monitor_plc(duration=20, interval=1):
    """
    Моніторинг PLC протягом заданого часу.
    """

    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)

    if not client.connect():
        print("Cannot connect to PLC")
        return

    print("Connected to PLC")
    print("Starting anomaly detection...")
    print("-" * 50)

    start_time = time.time()

    while time.time() - start_time < duration:
        state = read_plc_state(client)
        alerts = detect_anomalies(state)

        print("\nCurrent PLC state:")
        print(f"Temperature : {state['temperature']}")
        print(f"Pressure    : {state['pressure']}")
        print(f"Water Level : {state['water_level']}")
        print(f"Pump Status : {state['pump_status']}")

        if alerts:
            print("\nALERTS:")
            for alert in alerts:
                print(f"- {alert['message']}")
        else:
            print("\nStatus: normal")

        time.sleep(interval)

    client.close()
    print("\nAnomaly detection stopped.")


if __name__ == "__main__":
    monitor_plc(duration=30, interval=1)