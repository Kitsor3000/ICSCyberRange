import argparse
import time
from pymodbus.client.sync import ModbusTcpClient


PLC_HOST = "127.0.0.1"
PLC_PORT = 5020


REGISTER_MAP = {
    # Pump Station
    "temperature": 0,
    "pressure": 1,
    "water_level": 2,
    "pump_status": 3,

    # Conveyor Line
    "conveyor_status": 4,
    "motor_speed": 5,
    "motor_current": 6,
    "emergency_stop": 7,

    # Cooling System
    "fan_status": 8,
    "coolant_temperature": 9,
    "valve_position": 10,
    "cooling_alarm": 11,
}


NORMAL_VALUES = {
    # Pump Station
    "temperature": 28,
    "pressure": 5,
    "water_level": 60,
    "pump_status": 1,

    # Conveyor Line
    "conveyor_status": 1,
    "motor_speed": 70,
    "motor_current": 12,
    "emergency_stop": 0,

    # Cooling System
    "fan_status": 1,
    "coolant_temperature": 28,
    "valve_position": 70,
    "cooling_alarm": 0,
}


ATTACK_TO_RECOVERY = {
    # Pump Station
    "pump_off": "pump",
    "pump_false_data": "pump",
    "water_level_spoofing": "pump",

    # Conveyor Line
    "conveyor_stop": "conveyor",
    "motor_speed_overdrive": "conveyor",
    "emergency_stop_abuse": "conveyor",

    # Cooling System
    "fan_shutdown": "cooling",
    "valve_manipulation": "cooling",
    "cooling_temp_spoofing": "cooling",
}


def get_client():
    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)

    if not client.connect():
        raise ConnectionError("Cannot connect to PLC simulator")

    return client


def write_register(client, tag):
    address = REGISTER_MAP[tag]
    value = NORMAL_VALUES[tag]

    result = client.write_register(address, value, unit=1)

    if result.isError():
        raise RuntimeError(f"Cannot write register {address}")

    print(f"{tag} restored to {value}")


def read_plc_state(client):
    result = client.read_holding_registers(0, 12, unit=1)

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
        "motor_current": registers[6],
        "emergency_stop": registers[7],

        "fan_status": registers[8],
        "coolant_temperature": registers[9],
        "valve_position": registers[10],
        "cooling_alarm": registers[11],
    }


def print_state(title, state):
    print(f"\n{title}")

    print("PUMP STATION")
    print(f"Temperature       : {state['temperature']} °C")
    print(f"Pressure          : {state['pressure']} bar")
    print(f"Water Level       : {state['water_level']} %")
    print(f"Pump Status       : {state['pump_status']}")

    print("\nCONVEYOR LINE")
    print(f"Conveyor Status   : {state['conveyor_status']}")
    print(f"Motor Speed       : {state['motor_speed']} %")
    print(f"Motor Current     : {state['motor_current']} A")
    print(f"Emergency Stop    : {state['emergency_stop']}")

    print("\nCOOLING SYSTEM")
    print(f"Fan Status        : {state['fan_status']}")
    print(f"Coolant Temp      : {state['coolant_temperature']} °C")
    print(f"Valve Position    : {state['valve_position']} %")
    print(f"Cooling Alarm     : {state['cooling_alarm']}")


def recover_pump_station():
    client = get_client()

    try:
        before = read_plc_state(client)
        print_state("Before Pump Station recovery:", before)

        for tag in ["temperature", "pressure", "water_level", "pump_status"]:
            write_register(client, tag)

        time.sleep(1)

        after = read_plc_state(client)
        print_state("After Pump Station recovery:", after)

    finally:
        client.close()


def recover_conveyor_line():
    client = get_client()

    try:
        before = read_plc_state(client)
        print_state("Before Conveyor Line recovery:", before)

        for tag in ["conveyor_status", "motor_speed", "motor_current", "emergency_stop"]:
            write_register(client, tag)

        time.sleep(1)

        after = read_plc_state(client)
        print_state("After Conveyor Line recovery:", after)

    finally:
        client.close()


def recover_cooling_system():
    client = get_client()

    try:
        before = read_plc_state(client)
        print_state("Before Cooling System recovery:", before)

        for tag in ["fan_status", "coolant_temperature", "valve_position", "cooling_alarm"]:
            write_register(client, tag)

        time.sleep(1)

        after = read_plc_state(client)
        print_state("After Cooling System recovery:", after)

    finally:
        client.close()


def recover_full_system():
    client = get_client()

    try:
        before = read_plc_state(client)
        print_state("Before full system recovery:", before)

        for tag in NORMAL_VALUES.keys():
            write_register(client, tag)

        time.sleep(1)

        after = read_plc_state(client)
        print_state("After full system recovery:", after)

    finally:
        client.close()


def recover_by_attack(attack_name):
    if attack_name not in ATTACK_TO_RECOVERY:
        raise ValueError(f"Unknown attack name: {attack_name}")

    target = ATTACK_TO_RECOVERY[attack_name]

    if target == "pump":
        recover_pump_station()
    elif target == "conveyor":
        recover_conveyor_line()
    elif target == "cooling":
        recover_cooling_system()


def main():
    parser = argparse.ArgumentParser(
        description="ICSCyberRange Blue Team recovery module"
    )

    parser.add_argument(
        "--target",
        choices=["pump", "conveyor", "cooling", "full"],
        help="System to recover"
    )

    parser.add_argument(
        "--attack",
        choices=ATTACK_TO_RECOVERY.keys(),
        help="Recover system based on attack name"
    )

    args = parser.parse_args()

    if args.attack:
        recover_by_attack(args.attack)
        return

    if args.target == "pump":
        recover_pump_station()
    elif args.target == "conveyor":
        recover_conveyor_line()
    elif args.target == "cooling":
        recover_cooling_system()
    elif args.target == "full":
        recover_full_system()
    else:
        parser.error("Use --target or --attack")


if __name__ == "__main__":
    main()