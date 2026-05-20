from pymodbus.client.sync import ModbusTcpClient


PLC_HOST = "127.0.0.1"
PLC_PORT = 5020

REGISTER_MAP = {
    # Pump Station
    "temperature":        0,
    "pressure":           1,
    "water_level":        2,
    "pump_status":        3,
    # Conveyor Line
    "conveyor_status":    4,
    "motor_speed":        5,
    "motor_current":      6,
    "emergency_stop":     7,
    # Cooling System
    "fan_status":         8,
    "coolant_temperature": 9,
    "valve_position":     10,
    "cooling_alarm":      11,
}


class ICSModbusClient:
    """
    Клієнт для взаємодії з віртуальним PLC через Modbus TCP.
    Підтримує всі 12 регістрів трьох підсистем.
    """

    def __init__(self, host=PLC_HOST, port=PLC_PORT):
        self.host = host
        self.port = port
        self.client = ModbusTcpClient(host=self.host, port=self.port)

    def connect(self):
        return self.client.connect()

    def close(self):
        self.client.close()

    def read_registers(self):
        result = self.client.read_holding_registers(0, 12, unit=1)

        if result.isError():
            raise RuntimeError("Не вдалося зчитати регістри PLC")

        regs = result.registers

        return {
            "temperature":         regs[0],
            "pressure":            regs[1],
            "water_level":         regs[2],
            "pump_status":         regs[3],
            "conveyor_status":     regs[4],
            "motor_speed":         regs[5],
            "motor_current":       regs[6],
            "emergency_stop":      regs[7],
            "fan_status":          regs[8],
            "coolant_temperature": regs[9],
            "valve_position":      regs[10],
            "cooling_alarm":       regs[11],
        }

    def write_register(self, tag_or_address, value):
        address = REGISTER_MAP.get(tag_or_address, tag_or_address)
        result = self.client.write_register(address, int(value), unit=1)

        if result.isError():
            raise RuntimeError(f"Не вдалося записати register {address}")

        return True

    # ---- Pump Station helpers ----
    def turn_pump_on(self):
        return self.write_register("pump_status", 1)

    def turn_pump_off(self):
        return self.write_register("pump_status", 0)

    def set_fake_temperature(self, value):
        return self.write_register("temperature", value)

    # ---- Conveyor Line helpers ----
    def set_motor_speed(self, value):
        return self.write_register("motor_speed", value)

    def trigger_emergency_stop(self):
        return self.write_register("emergency_stop", 1)

    def clear_emergency_stop(self):
        return self.write_register("emergency_stop", 0)

    # ---- Cooling System helpers ----
    def turn_fan_on(self):
        return self.write_register("fan_status", 1)

    def turn_fan_off(self):
        return self.write_register("fan_status", 0)

    def set_valve_position(self, value):
        return self.write_register("valve_position", value)


if __name__ == "__main__":
    plc = ICSModbusClient()

    if not plc.connect():
        print("Cannot connect to PLC")
        raise SystemExit(1)

    print("Connected to PLC Simulator")
    data = plc.read_registers()

    print("\nPUMP STATION")
    print(f"  Temperature       : {data['temperature']} °C")
    print(f"  Pressure          : {data['pressure']} bar")
    print(f"  Water Level       : {data['water_level']} %")
    print(f"  Pump Status       : {'ON' if data['pump_status'] else 'OFF'}")

    print("\nCONVEYOR LINE")
    print(f"  Conveyor Status   : {'ON' if data['conveyor_status'] else 'OFF'}")
    print(f"  Motor Speed       : {data['motor_speed']} %")
    print(f"  Motor Current     : {data['motor_current']} A")
    print(f"  Emergency Stop    : {'ACTIVE' if data['emergency_stop'] else 'OFF'}")

    print("\nCOOLING SYSTEM")
    print(f"  Fan Status        : {'ON' if data['fan_status'] else 'OFF'}")
    print(f"  Coolant Temp      : {data['coolant_temperature']} °C")
    print(f"  Valve Position    : {data['valve_position']} %")
    print(f"  Cooling Alarm     : {'ACTIVE' if data['cooling_alarm'] else 'OFF'}")

    plc.close()
