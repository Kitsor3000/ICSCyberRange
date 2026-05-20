import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymodbus.client.sync import ModbusTcpClient
from influxdb_client import InfluxDBClient, Point, WritePrecision


load_dotenv()


PLC_HOST = "127.0.0.1"
PLC_PORT = 5020


INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "ICS")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "plc_telemetry")

if not INFLUXDB_TOKEN:
    raise ValueError("INFLUXDB_TOKEN не знайдено. Перевір файл .env")


def read_plc_state():
    """
    Зчитування 12 Modbus-регістрів з PLC.
    """

    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)

    if not client.connect():
        raise ConnectionError("Cannot connect to PLC")

    result = client.read_holding_registers(0, 12, unit=1)

    client.close()

    if result.isError():
        raise RuntimeError("Cannot read PLC registers")

    registers = result.registers

    return {
        # Pump Station
        "temperature": registers[0],
        "pressure": registers[1],
        "water_level": registers[2],
        "pump_status": registers[3],

        # Conveyor Line
        "conveyor_status": registers[4],
        "motor_speed": registers[5],
        "motor_current": registers[6],
        "emergency_stop": registers[7],

        # Cooling System
        "fan_status": registers[8],
        "coolant_temperature": registers[9],
        "valve_position": registers[10],
        "cooling_alarm": registers[11],
    }


def write_to_influx(write_api, state):
    """
    Запис усіх параметрів у InfluxDB з тегами підсистем.
    """

    point = (
        Point("plc_state")
        .tag("source", "plc_simulator")
        .tag("environment", "icscyberrange")

        # Pump Station
        .field("temperature", state["temperature"])
        .field("pressure", state["pressure"])
        .field("water_level", state["water_level"])
        .field("pump_status", state["pump_status"])

        # Conveyor Line
        .field("conveyor_status", state["conveyor_status"])
        .field("motor_speed", state["motor_speed"])
        .field("motor_current", state["motor_current"])
        .field("emergency_stop", state["emergency_stop"])

        # Cooling System
        .field("fan_status", state["fan_status"])
        .field("coolant_temperature", state["coolant_temperature"])
        .field("valve_position", state["valve_position"])
        .field("cooling_alarm", state["cooling_alarm"])

        .time(datetime.now(timezone.utc), WritePrecision.NS)
    )

    write_api.write(
        bucket=INFLUXDB_BUCKET,
        org=INFLUXDB_ORG,
        record=point
    )


def start_collector(interval=2):
    influx_client = InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG
    )

    write_api = influx_client.write_api()

    print("Telemetry collector started...")
    print("Systems: Pump Station + Conveyor Line + Cooling System")
    print("-" * 90)

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
                f"motor_current={state['motor_current']} | "
                f"emergency_stop={state['emergency_stop']} | "
                f"fan_status={state['fan_status']} | "
                f"coolant_temperature={state['coolant_temperature']} | "
                f"valve_position={state['valve_position']} | "
                f"cooling_alarm={state['cooling_alarm']}"
            )

        except Exception as error:
            print(f"Collector error: {error}")

        time.sleep(interval)


if __name__ == "__main__":
    start_collector(interval=2)