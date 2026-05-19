from pymodbus.client.sync import ModbusTcpClient


PLC_HOST = "127.0.0.1"
PLC_PORT = 5020


REGISTER_NAMES = {
    0: "temperature",
    1: "pressure",
    2: "water_level",
    3: "pump_status",
    4: "conveyor_status",
    5: "motor_speed",
    6: "motor_current",
    7: "emergency_stop",
    8: "fan_status",
    9: "coolant_temperature",
    10: "valve_position",
    11: "cooling_alarm",
}


def read_registers():
    """
    Зчитує всі 12 Modbus-регістрів з PLC Simulator.
    """

    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)

    if not client.connect():
        print("Cannot connect to PLC Simulator")
        return None

    result = client.read_holding_registers(0, 12, unit=1)
    client.close()

    if result.isError():
        print("Cannot read PLC registers")
        return None

    return result.registers


def print_registers(registers):
    """
    Виводить усі значення PLC у зрозумілому вигляді.
    """

    print("\nCURRENT PLC STATE")
    print("-" * 50)

    for index, value in enumerate(registers):
        name = REGISTER_NAMES.get(index, f"register_{index}")
        print(f"R{index:02d} | {name:22s} | {value}")

    print("-" * 50)


def detect_custom_rule(registers):
    """
    Приклад простого правила захисту.
    Перевіряє, чи швидкість двигуна конвеєра не перевищує норму.
    """

    motor_speed = registers[5]

    if motor_speed > 100:
        print("ALERT: motor_speed is too high")
        print(f"Current motor_speed = {motor_speed}")
        print("Recommended recovery: set motor_speed back to 70")
    else:
        print("OK: motor_speed is normal")
        print(f"Current motor_speed = {motor_speed}")


if __name__ == "__main__":
    registers = read_registers()

    if registers:
        print_registers(registers)
        detect_custom_rule(registers)