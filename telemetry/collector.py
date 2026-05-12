import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymodbus.client.sync import ModbusTcpClient
from influxdb_client import InfluxDBClient, Point, WritePrecision


# ------------------------------------------------
# LOAD ENV
# ------------------------------------------------

load_dotenv()


# ------------------------------------------------
# PLC SETTINGS
# ------------------------------------------------

PLC_HOST = "127.0.0.1"
PLC_PORT = 5020


# ------------------------------------------------
# INFLUXDB SETTINGS
# ------------------------------------------------

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "ICS")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "plc_telemetry")

if not INFLUXDB_TOKEN:
    raise ValueError("INFLUXDB_TOKEN не знайдено. Перевір файл .env")


# ------------------------------------------------
# PLC READ
# ------------------------------------------------

def read_plc_state():
    """
    Зчитування стану PLC через Modbus TCP.

    Registers:
    0 - temperature
    1 - pressure
    2 - water_level
    3 - pump_status
    4 - conveyor_status
    5 - motor_speed
    6 - item_count
    7 - emergency_stop
    """

    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)

    if not client.connect():
        raise ConnectionError("Cannot connect to PLC")

    result = client.read_holding_registers(0, 8, unit=1)

    client.close()

    if result.isError():
        raise RuntimeError("Cannot read PLC registers")

    registers = result.registers

    return {
        "temperature": registers[0],
        "pressure": registers[1],
        "water_level": registers[2],
        "pump_status": registers[3],
        "conveyor_status": registers[4],
        "motor_speed": registers[5],
        "item_count": registers[6],
        "emergency_stop": registers[7],
    }


# ------------------------------------------------
# INFLUX WRITE
# ------------------------------------------------

def write_to_influx(write_api, state):
    """
    Запис телеметрії PLC в InfluxDB.
    """

    point = (
        Point("plc_state")
        .field("temperature", state["temperature"])
        .field("pressure", state["pressure"])
        .field("water_level", state["water_level"])
        .field("pump_status", state["pump_status"])
        .field("conveyor_status", state["conveyor_status"])
        .field("motor_speed", state["motor_speed"])
        .field("item_count", state["item_count"])
        .field("emergency_stop", state["emergency_stop"])
        .time(datetime.now(timezone.utc), WritePrecision.NS)
    )

    write_api.write(
        bucket=INFLUXDB_BUCKET,
        org=INFLUXDB_ORG,
        record=point
    )


# ------------------------------------------------
# COLLECTOR LOOP
# ------------------------------------------------

def start_collector(interval=2):
    """
    Основний цикл збору телеметрії.
    """

    influx_client = InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG
    )

    write_api = influx_client.write_api()

    print("Telemetry collector started...")
    print("Reading PLC data and writing to InfluxDB")
    print("Systems: Pump Station + Conveyor Line")
    print("-" * 70)

    while True:
        try:
            state = read_plc_state()
            write_to_influx(write_api, state)

            print(
                f"temperature={state['temperature']} | "
                f"pressure={state['pressure']} | "
                f"water_level={state['water_level']} | "
                f"pump_status={state['pump_status']} | "
                f"conveyor_status={state['conveyor_status']} | "
                f"motor_speed={state['motor_speed']} | "
                f"item_count={state['item_count']} | "
                f"emergency_stop={state['emergency_stop']}"
            )

        except Exception as error:
            print(f"Collector error: {error}")

        time.sleep(interval)


if __name__ == "__main__":
    start_collector(interval=2)