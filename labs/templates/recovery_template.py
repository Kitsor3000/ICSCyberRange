from pymodbus.client.sync import ModbusTcpClient


PLC_HOST = "127.0.0.1"
PLC_PORT = 5020


def recover_conveyor_line():
    """
    Приклад recovery для Conveyor Line.
    Повертає конвеєр у нормальний безпечний стан.
    """

    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)

    if not client.connect():
        print("Cannot connect to PLC Simulator")
        return

    # Register 4 = conveyor_status
    # 1 означає ON
    client.write_register(4, 1, unit=1)

    # Register 5 = motor_speed
    # 70% — нормальна швидкість
    client.write_register(5, 70, unit=1)

    # Register 6 = motor_current
    # 12A — нормальний струм двигуна
    client.write_register(6, 12, unit=1)

    # Register 7 = emergency_stop
    # 0 означає OFF
    client.write_register(7, 0, unit=1)

    client.close()

    print("Conveyor Line recovered")


if __name__ == "__main__":
    recover_conveyor_line()