from pymodbus.client.sync import ModbusTcpClient


PLC_HOST = "127.0.0.1"
PLC_PORT = 5020


class ICSModbusClient:
    """
    Клієнт для взаємодії з віртуальним PLC через Modbus TCP.
    """

    def __init__(self, host=PLC_HOST, port=PLC_PORT):
        self.host = host
        self.port = port
        self.client = ModbusTcpClient(host=self.host, port=self.port)

    def connect(self):
        """
        Підключення до PLC.
        """
        return self.client.connect()

    def close(self):
        """
        Закриття підключення.
        """
        self.client.close()

    def read_registers(self):
        """
        Зчитування основних регістрів PLC.

        Register 0 — temperature
        Register 1 — pressure
        Register 2 — water_level
        Register 3 — pump_status
        """

        result = self.client.read_holding_registers(0, 4, unit=1)

        if result.isError():
            raise Exception("Не вдалося зчитати регістри PLC")

        registers = result.registers

        return {
            "temperature": registers[0],
            "pressure": registers[1],
            "water_level": registers[2],
            "pump_status": registers[3],
        }

    def write_register(self, address, value):
        """
        Запис значення в holding register.
        """
        result = self.client.write_register(address, value, unit=1)

        if result.isError():
            raise Exception(f"Не вдалося записати register {address}")

        return True

    def turn_pump_on(self):
        """
        Увімкнення насоса.
        """
        return self.write_register(3, 1)

    def turn_pump_off(self):
        """
        Вимкнення насоса.
        """
        return self.write_register(3, 0)

    def set_fake_temperature(self, value):
        """
        Підміна значення температури.
        """
        return self.write_register(0, value)


if __name__ == "__main__":
    plc = ICSModbusClient()

    if plc.connect():
        print("Connected to PLC")

        data = plc.read_registers()

        print("PLC DATA:")
        print(f"Temperature : {data['temperature']}")
        print(f"Pressure    : {data['pressure']}")
        print(f"Water Level : {data['water_level']}")
        print(f"Pump Status : {data['pump_status']}")

        plc.close()
    else:
        print("Cannot connect to PLC")