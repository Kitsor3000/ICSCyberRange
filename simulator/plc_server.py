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
# 0 - temperature
# 1 - pressure
# 2 - water_level
# 3 - pump_status
# 4 - conveyor_status
# 5 - motor_speed
# 6 - item_count
# 7 - emergency_stop
# ------------------------------------------------


INITIAL_VALUES = [
    28,   # temperature
    5,    # pressure
    60,   # water_level
    1,    # pump_status
    1,    # conveyor_status
    70,   # motor_speed
    0,    # item_count
    0,    # emergency_stop
]


store = ModbusSlaveContext(
    hr=ModbusSequentialDataBlock(0, INITIAL_VALUES),
    zero_mode=True
)

context = ModbusServerContext(slaves=store, single=True)


# ------------------------------------------------
# PLC DEVICE INFO
# ------------------------------------------------

identity = ModbusDeviceIdentification()
identity.VendorName = "ICSCyberRange"
identity.ProductName = "Virtual PLC"
identity.ModelName = "Pump Station + Conveyor Line Simulator"
identity.MajorMinorRevision = "2.0"


# ------------------------------------------------
# SAFE MODBUS HELPERS
# ------------------------------------------------

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


# ------------------------------------------------
# PROCESS SIMULATION
# ------------------------------------------------

def process_simulation():
    """
    Симуляція двох промислових підсистем:
    1. Pump Station
    2. Conveyor Line
    """

    # Початкові внутрішні значення процесу
    temperature = 28
    pressure = 5
    water_level = 60

    conveyor_status = 1
    motor_speed = 70
    item_count = 0
    emergency_stop = 0

    while True:
        # ------------------------------------------------
        # READ CONTROL REGISTERS FROM MODBUS
        # ------------------------------------------------

        pump_status = read_register(3, default=1)
        conveyor_status = read_register(4, default=1)
        motor_speed_command = read_register(5, default=70)
        emergency_stop = read_register(7, default=0)

        # Нормалізація керуючих значень
        pump_status = 1 if pump_status == 1 else 0
        conveyor_status = 1 if conveyor_status == 1 else 0
        emergency_stop = 1 if emergency_stop == 1 else 0

        # ------------------------------------------------
        # PUMP STATION LOGIC
        # ------------------------------------------------

        if pump_status == 1:
            # Рівень води росте повільно, але не вище 100%
            if water_level < 100:
                water_level += random.choice([0, 1])

            # Тиск прагне до робочого діапазону 6-9 bar
            if pressure < 8:
                pressure += 1
            elif pressure > 9:
                pressure -= 1
            else:
                pressure += random.choice([-1, 0, 1])

            # Температура стабілізується в реалістичному діапазоні 28-38°C
            if temperature < 32:
                temperature += random.choice([0, 1])
            elif temperature > 38:
                temperature -= random.choice([0, 1])
            else:
                temperature += random.choice([-1, 0, 0, 1])

        else:
            # Якщо насос вимкнено — рівень і тиск падають
            if water_level > 0:
                water_level -= random.choice([0, 1, 1])

            if pressure > 0:
                pressure -= random.choice([0, 1])

            # Температура повільно повертається до кімнатної
            if temperature > 24:
                temperature -= random.choice([0, 1])

        # Фізичні межі Pump Station
        temperature = max(18, min(60, temperature))
        pressure = max(0, min(12, pressure))
        water_level = max(0, min(100, water_level))

        # ------------------------------------------------
        # CONVEYOR LINE LOGIC
        # ------------------------------------------------

        if emergency_stop == 1:
            # Аварійна зупинка має пріоритет
            conveyor_status = 0
            motor_speed = 0

        else:
            # Конвеєр працює, якщо немає аварійної зупинки
            if conveyor_status == 1:
                # Команда швидкості з Modbus, але в межах 0-120
                motor_speed = max(0, min(120, motor_speed_command))

                # Якщо швидкість нормальна — деталі обробляються
                if motor_speed > 0:
                    item_count += max(1, motor_speed // 40)

            else:
                motor_speed = 0

        # Захист від переповнення лічильника
        item_count = min(item_count, 9999)

        # ------------------------------------------------
        # WRITE CURRENT STATE TO MODBUS REGISTERS
        # ------------------------------------------------

        values = [
            temperature,
            pressure,
            water_level,
            pump_status,
            conveyor_status,
            motor_speed,
            item_count,
            emergency_stop,
        ]

        write_all_registers(values)

        # ------------------------------------------------
        # CONSOLE OUTPUT
        # ------------------------------------------------

        print("=" * 60)
        print("PUMP STATION")
        print(f"Temperature      : {temperature} °C")
        print(f"Pressure         : {pressure} bar")
        print(f"Water Level      : {water_level} %")
        print(f"Pump Status      : {'ON' if pump_status else 'OFF'}")

        print("-" * 60)
        print("CONVEYOR LINE")
        print(f"Conveyor Status  : {'ON' if conveyor_status else 'OFF'}")
        print(f"Motor Speed      : {motor_speed} %")
        print(f"Item Count       : {item_count}")
        print(f"Emergency Stop   : {'ACTIVE' if emergency_stop else 'OFF'}")

        time.sleep(2)


# ------------------------------------------------
# START SIMULATION THREAD
# ------------------------------------------------

thread = threading.Thread(target=process_simulation)
thread.daemon = True
thread.start()


# ------------------------------------------------
# START MODBUS TCP SERVER
# ------------------------------------------------

print("PLC Simulator started on port 5020")
print("Systems: Pump Station + Conveyor Line")

StartTcpServer(
    context,
    identity=identity,
    address=("0.0.0.0", 5020)
)