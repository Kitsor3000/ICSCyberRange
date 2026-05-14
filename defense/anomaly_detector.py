import time
from pymodbus.client.sync import ModbusTcpClient


PLC_HOST = "127.0.0.1"
PLC_PORT = 5020


NORMAL_RANGES = {
    # Pump Station
    "temperature": (18, 45),
    "pressure": (2, 10),
    "water_level": (20, 100),
    "pump_status": (1, 1),

    # Conveyor Line
    "conveyor_status": (1, 1),
    "motor_speed": (40, 100),
    "motor_current": (5, 25),
    "emergency_stop": (0, 0),

    # Cooling System
    "fan_status": (1, 1),
    "coolant_temperature": (18, 40),
    "valve_position": (30, 100),
    "cooling_alarm": (0, 0),
}


SYSTEM_MAP = {
    "temperature": "Pump Station",
    "pressure": "Pump Station",
    "water_level": "Pump Station",
    "pump_status": "Pump Station",

    "conveyor_status": "Conveyor Line",
    "motor_speed": "Conveyor Line",
    "motor_current": "Conveyor Line",
    "emergency_stop": "Conveyor Line",

    "fan_status": "Cooling System",
    "coolant_temperature": "Cooling System",
    "valve_position": "Cooling System",
    "cooling_alarm": "Cooling System",
}


RECOVERY_HINTS = {
    "Pump Station": "Run recover_pump_station",
    "Conveyor Line": "Run recover_conveyor_line",
    "Cooling System": "Run recover_cooling_system",
}


def get_client():
    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)

    if not client.connect():
        raise ConnectionError("Cannot connect to PLC simulator")

    return client


def read_plc_state():
    client = get_client()

    try:
        result = client.read_holding_registers(0, 12, unit=1)

        if result.isError():
            raise RuntimeError("Cannot read PLC registers")

        registers = result.registers

        return {
            "temperature": registers[0],
            "pressure": registers[1],
            "water_level": registers[2],
            "pump_status": registers[3],

            "conveyor_status": registers[4],
            "motor_speed": registers[5],
            "motor_current": registers[6],
            "emergency_stop": registers[7],

            "fan_status": registers[8],
            "coolant_temperature": registers[9],
            "valve_position": registers[10],
            "cooling_alarm": registers[11],
        }

    finally:
        client.close()


def detect_anomalies(state):
    alerts = []

    for tag, value in state.items():
        min_value, max_value = NORMAL_RANGES[tag]

        if value < min_value or value > max_value:
            system = SYSTEM_MAP[tag]

            alerts.append({
                "system": system,
                "tag": tag,
                "value": value,
                "normal_range": f"{min_value} - {max_value}",
                "message": f"{system}: {tag} = {value}, норма: {min_value} - {max_value}",
                "recovery_hint": RECOVERY_HINTS[system],
            })

    return alerts


def print_state(state):
    print("\nPUMP STATION")
    print(f"Temperature       : {state['temperature']} °C")
    print(f"Pressure          : {state['pressure']} bar")
    print(f"Water Level       : {state['water_level']} %")
    print(f"Pump Status       : {state['pump_status']}")

    print("\nCONVEYOR LINE")
    print(f"Conveyor Status   : {state['conveyor_status']}")
    print(f"Motor Speed       : {state['motor_speed']} %")
    print(f"Motor Current     : {state['motor_current']} A")
    print(f"Emergency Stop    : {state['emergency_stop']}")

    print("\nCOOLING SYSTEM")
    print(f"Fan Status        : {state['fan_status']}")
    print(f"Coolant Temp      : {state['coolant_temperature']} °C")
    print(f"Valve Position    : {state['valve_position']} %")
    print(f"Cooling Alarm     : {state['cooling_alarm']}")


def run_detection_once():
    state = read_plc_state()
    alerts = detect_anomalies(state)

    print("=" * 70)
    print_state(state)

    if alerts:
        print("\nALERTS")
        for alert in alerts:
            print(f"- {alert['message']}")
            print(f"  Recovery: {alert['recovery_hint']}")
    else:
        print("\nSystem status: NORMAL")

    return alerts


def monitor_plc(duration=30, interval=2):
    print("Starting Blue Team anomaly monitoring...")
    print("-" * 70)

    start_time = time.time()

    while time.time() - start_time < duration:
        run_detection_once()
        time.sleep(interval)


if __name__ == "__main__":
    monitor_plc(duration=30, interval=2)