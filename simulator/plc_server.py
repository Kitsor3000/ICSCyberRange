import time
import random
import threading

from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext
from pymodbus.datastore import ModbusServerContext
from pymodbus.device import ModbusDeviceIdentification


# ------------------------------------------------
# PLC REGISTERS
# ------------------------------------------------
# Pump Station
# 0  - temperature
# 1  - pressure
# 2  - water_level
# 3  - pump_status
#
# Conveyor Line
# 4  - conveyor_status
# 5  - motor_speed
# 6  - motor_current
# 7  - emergency_stop
#
# Cooling System
# 8  - fan_status
# 9  - coolant_temperature
# 10 - valve_position
# 11 - cooling_alarm
# ------------------------------------------------


INITIAL_VALUES = [
    # Pump Station
    28,   # temperature
    5,    # pressure
    60,   # water_level
    1,    # pump_status

    # Conveyor Line
    1,    # conveyor_status
    70,   # motor_speed
    12,   # motor_current
    0,    # emergency_stop

    # Cooling System
    1,    # fan_status
    28,   # coolant_temperature
    70,   # valve_position
    0,    # cooling_alarm
]


store = ModbusSlaveContext(
    hr=ModbusSequentialDataBlock(0, INITIAL_VALUES),
    zero_mode=True
)

context = ModbusServerContext(slaves=store, single=True)


identity = ModbusDeviceIdentification()
identity.VendorName = "ICSCyberRange"
identity.ProductName = "Virtual PLC"
identity.ModelName = "Pump Station + Conveyor Line + Cooling System"
identity.MajorMinorRevision = "3.1"


def read_register(address, default=0):
    """
    Безпечне читання одного holding register.
    """

    try:
        values = store.getValues(3, address, count=1)

        if values and len(values) > 0:
            return values[0]

        return default

    except Exception:
        return default


def write_register(address, value):
    """
    Безпечний запис одного holding register.
    """

    store.setValues(3, address, [value])


def write_all_registers(values):
    """
    Запис усіх регістрів PLC.
    """

    for address, value in enumerate(values):
        write_register(address, value)


def process_simulation():
    """
    Симуляція трьох промислових підсистем:
    1. Pump Station
    2. Conveyor Line
    3. Cooling System
    """

    # Pump Station
    temperature = 28
    pressure = 5
    water_level = 60

    # Conveyor Line
    conveyor_status = 1
    motor_speed = 70
    motor_current = 12
    emergency_stop = 0

    # Cooling System
    fan_status = 1
    coolant_temperature = 28
    valve_position = 70
    cooling_alarm = 0

    while True:
        # ------------------------------------------------
        # READ CONTROL REGISTERS
        # ------------------------------------------------

        pump_status = read_register(3, default=1)

        conveyor_status = read_register(4, default=1)
        motor_speed_command = read_register(5, default=70)
        emergency_stop = read_register(7, default=0)

        fan_status = read_register(8, default=1)
        valve_position_command = read_register(10, default=70)

        pump_status = 1 if pump_status == 1 else 0
        conveyor_status = 1 if conveyor_status == 1 else 0
        emergency_stop = 1 if emergency_stop == 1 else 0
        fan_status = 1 if fan_status == 1 else 0

        # ------------------------------------------------
        # PUMP STATION LOGIC
        # ------------------------------------------------

        if pump_status == 1:
            if water_level < 100:
                water_level += random.choice([0, 1])

            if pressure < 7:
                pressure += 1
            elif pressure > 9:
                pressure -= 1
            else:
                pressure += random.choice([-1, 0, 0, 1])

            if temperature < 30:
                temperature += random.choice([0, 1])
            elif temperature > 38:
                temperature -= random.choice([0, 1])
            else:
                temperature += random.choice([-1, 0, 0, 1])

        else:
            if water_level > 0:
                water_level -= random.choice([0, 1, 1])

            if pressure > 0:
                pressure -= random.choice([0, 1])

            if temperature > 24:
                temperature -= random.choice([0, 1])

        temperature = max(18, min(60, temperature))
        pressure = max(0, min(12, pressure))
        water_level = max(0, min(100, water_level))

        # ------------------------------------------------
        # CONVEYOR LINE LOGIC
        # ------------------------------------------------

        if emergency_stop == 1:
            conveyor_status = 0
            motor_speed = 0
            motor_current = 0

        else:
            if conveyor_status == 1:
                motor_speed = max(0, min(120, motor_speed_command))

                # Реалістична залежність:
                # чим більша швидкість - тим більший струм двигуна
                base_current = 5
                load_current = motor_speed // 6
                noise = random.choice([-1, 0, 0, 1])

                motor_current = base_current + load_current + noise

                # якщо швидкість небезпечна, струм ще більший
                if motor_speed > 100:
                    motor_current += random.choice([3, 4, 5])

            else:
                motor_speed = 0
                motor_current = 0

        motor_current = max(0, min(40, motor_current))

        # ------------------------------------------------
        # COOLING SYSTEM LOGIC
        # ------------------------------------------------

        valve_position = max(0, min(100, valve_position_command))

        if fan_status == 1 and valve_position >= 30:
            if coolant_temperature > 28:
                coolant_temperature -= random.choice([0, 1])
            elif coolant_temperature < 24:
                coolant_temperature += random.choice([0, 1])
            else:
                coolant_temperature += random.choice([-1, 0, 0, 1])

        else:
            coolant_temperature += random.choice([1, 1, 2])

        coolant_temperature = max(15, min(80, coolant_temperature))

        if coolant_temperature > 45 or fan_status == 0 or valve_position < 30:
            cooling_alarm = 1
        else:
            cooling_alarm = 0

        # ------------------------------------------------
        # WRITE REGISTERS
        # ------------------------------------------------

        values = [
            temperature,
            pressure,
            water_level,
            pump_status,

            conveyor_status,
            motor_speed,
            motor_current,
            emergency_stop,

            fan_status,
            coolant_temperature,
            valve_position,
            cooling_alarm,
        ]

        write_all_registers(values)

        # ------------------------------------------------
        # CONSOLE OUTPUT
        # ------------------------------------------------

        print("=" * 70)

        print("PUMP STATION")
        print(f"Temperature       : {temperature} °C")
        print(f"Pressure          : {pressure} bar")
        print(f"Water Level       : {water_level} %")
        print(f"Pump Status       : {'ON' if pump_status else 'OFF'}")

        print("-" * 70)

        print("CONVEYOR LINE")
        print(f"Conveyor Status   : {'ON' if conveyor_status else 'OFF'}")
        print(f"Motor Speed       : {motor_speed} %")
        print(f"Motor Current     : {motor_current} A")
        print(f"Emergency Stop    : {'ACTIVE' if emergency_stop else 'OFF'}")

        print("-" * 70)

        print("COOLING SYSTEM")
        print(f"Fan Status        : {'ON' if fan_status else 'OFF'}")
        print(f"Coolant Temp      : {coolant_temperature} °C")
        print(f"Valve Position    : {valve_position} %")
        print(f"Cooling Alarm     : {'ACTIVE' if cooling_alarm else 'OFF'}")

        time.sleep(2)


thread = threading.Thread(target=process_simulation)
thread.daemon = True
thread.start()


print("PLC Simulator started on port 5020")
print("Systems: Pump Station + Conveyor Line + Cooling System")

StartTcpServer(
    context,
    identity=identity,
    address=("0.0.0.0", 5020)
)