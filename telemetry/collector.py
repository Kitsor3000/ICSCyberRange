import os
import time
from datetime import datetime, timezone

from pymodbus.client.sync import ModbusTcpClient
from influxdb_client import InfluxDBClient, Point, WritePrecision

from dotenv import load_dotenv

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


def read_plc_state():
    """
    Зчитування поточного стану PLC через Modbus TCP.
    """

    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)

    if not client.connect():
        raise ConnectionError("Cannot connect to PLC")

    result = client.read_holding_registers(0, 4, unit=1)

    client.close()

    if result.isError():
        raise RuntimeError("Cannot read PLC registers")

    return {
        "temperature": result.registers[0],
        "pressure": result.registers[1],
        "water_level": result.registers[2],
        "pump_status": result.registers[3],
    }


def write_to_influx(write_api, state):
    """
    Запис PLC telemetry в InfluxDB.
    """

    point = (
        Point("plc_state")
        .field("temperature", state["temperature"])
        .field("pressure", state["pressure"])
        .field("water_level", state["water_level"])
        .field("pump_status", state["pump_status"])
        .time(datetime.now(timezone.utc), WritePrecision.NS)
    )

    write_api.write(
        bucket=INFLUXDB_BUCKET,
        org=INFLUXDB_ORG,
        record=point
    )


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
    print("-" * 50)

    while True:
        try:
            state = read_plc_state()
            write_to_influx(write_api, state)

            print(
                f"temperature={state['temperature']} | "
                f"pressure={state['pressure']} | "
                f"water_level={state['water_level']} | "
                f"pump_status={state['pump_status']}"
            )

        except Exception as error:
            print(f"Collector error: {error}")

        time.sleep(interval)


if __name__ == "__main__":
    start_collector(interval=2)