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
# Register 0 - Temperature
# Register 1 - Pressure
# Register 2 - Water Level
# Register 3 - Pump Status
#
# Pump Status:
# 1 - ON
# 0 - OFF
# ------------------------------------------------

store = ModbusSlaveContext(
    hr=ModbusSequentialDataBlock(0, [25, 5, 50, 1]),
    zero_mode=True
)

context = ModbusServerContext(slaves=store, single=True)


# ------------------------------------------------
# PLC INFO
# ------------------------------------------------

identity = ModbusDeviceIdentification()
identity.VendorName = "ICSCyberRange"
identity.ProductName = "Virtual PLC"
identity.ModelName = "PLC Simulator"
identity.MajorMinorRevision = "1.0"


# ------------------------------------------------
# SAFE REGISTER READ
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


def write_registers(temperature, pressure, water_level, pump_status):
    """
    Запис поточного стану процесу в Modbus-регістри.
    """
    store.setValues(3, 0, [temperature])
    store.setValues(3, 1, [pressure])
    store.setValues(3, 2, [water_level])
    store.setValues(3, 3, [pump_status])


# ------------------------------------------------
# PROCESS SIMULATION
# ------------------------------------------------

def process_simulation():
    """
    Основна логіка віртуального промислового процесу.
    """

    temperature = 25
    pressure = 5
    water_level = 50

    while True:
        # Головне виправлення:
        # насос читається з Modbus register 3,
        # тому зовнішня атака може змінити його стан.
        pump_status = read_register(3, default=1)

        if pump_status not in [0, 1]:
            pump_status = 0

        # ----------------------------
        # Process logic
        # ----------------------------

        if pump_status == 1:
            water_level += 1
            pressure += 1
            temperature += random.choice([0, 1])
        else:
            water_level -= 1
            pressure -= 1
            temperature -= random.choice([0, 1])

        # ----------------------------
        # Limits
        # ----------------------------

        temperature = max(0, min(120, temperature))
        pressure = max(0, min(15, pressure))
        water_level = max(0, min(100, water_level))

        # ----------------------------
        # Write current process state
        # ----------------------------

        write_registers(
            temperature=temperature,
            pressure=pressure,
            water_level=water_level,
            pump_status=pump_status
        )

        # ----------------------------
        # Console output
        # ----------------------------

        print("=" * 50)
        print(f"Temperature : {temperature}")
        print(f"Pressure    : {pressure}")
        print(f"Water Level : {water_level}")
        print(f"Pump Status : {'ON' if pump_status == 1 else 'OFF'}")

        time.sleep(2)


# ------------------------------------------------
# START THREAD
# ------------------------------------------------

thread = threading.Thread(target=process_simulation)
thread.daemon = True
thread.start()


# ------------------------------------------------
# START SERVER
# ------------------------------------------------

print("PLC Simulator started on port 5020")

StartTcpServer(
    context,
    identity=identity,
    address=("0.0.0.0", 5020)
)