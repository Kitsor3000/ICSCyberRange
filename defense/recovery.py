from pymodbus.client.sync import ModbusTcpClient


PLC_HOST = "127.0.0.1"
PLC_PORT = 5020


NORMAL_STATE = {
    "temperature": 25,
    "pressure": 5,
    "water_level": 50,
    "pump_status": 1,
}


def read_plc_state(client):
    """
    Зчитування поточного стану PLC.
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


def print_state(title, state):
    """
    Виведення стану PLC у консоль.
    """

    print(f"\n{title}")
    print(f"Temperature : {state['temperature']}")
    print(f"Pressure    : {state['pressure']}")
    print(f"Water Level : {state['water_level']}")
    print(f"Pump Status : {state['pump_status']}")


def recover_system():
    """
    Відновлення нормального стану PLC після атаки.

    Register 0 — Temperature
    Register 1 — Pressure
    Register 2 — Water Level
    Register 3 — Pump Status
    """

    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)

    if not client.connect():
        print("Cannot connect to PLC")
        return

    print("Connected to PLC")
    print("Starting recovery procedure...")

    before = read_plc_state(client)
    print_state("Before recovery:", before)

    # Відновлення нормальних значень
    client.write_register(0, NORMAL_STATE["temperature"], unit=1)
    client.write_register(1, NORMAL_STATE["pressure"], unit=1)
    client.write_register(2, NORMAL_STATE["water_level"], unit=1)
    client.write_register(3, NORMAL_STATE["pump_status"], unit=1)

    after = read_plc_state(client)
    print_state("After recovery:", after)

    client.close()

    print("\nSystem recovery completed.")


if __name__ == "__main__":
    recover_system()