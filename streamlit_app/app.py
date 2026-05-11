import os
import time
import json

import streamlit as st
from pymodbus.client.sync import ModbusTcpClient


# ------------------------------------------------
# PLC CONNECTION SETTINGS
# ------------------------------------------------

PLC_PORT = 5020

# Якщо Streamlit запущений у Docker, він звертається до хоста через host.docker.internal.
# Якщо запускаєш Streamlit локально, буде використано fallback на 127.0.0.1.
PLC_HOSTS = [
    os.getenv("PLC_HOST", "host.docker.internal"),
    "127.0.0.1",
]


NORMAL_RANGES = {
    "temperature": (0, 80),
    "pressure": (1, 15),
    "water_level": (10, 90),
    "pump_status": (0, 1),
}


NORMAL_STATE = {
    "temperature": 25,
    "pressure": 5,
    "water_level": 50,
    "pump_status": 1,
}


# ------------------------------------------------
# MODBUS HELPERS
# ------------------------------------------------

def load_training_scenario(path="scenarios/beginner.json"):
    """
    Завантаження навчального сценарію з JSON-файлу.
    """

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None
    

def get_client():
    """
    Підключення до PLC.
    Спочатку пробує host.docker.internal, потім 127.0.0.1.
    """

    for host in PLC_HOSTS:
        client = ModbusTcpClient(host, port=PLC_PORT)

        if client.connect():
            return client, host

        client.close()

    return None, None


def read_plc_state():
    """
    Зчитування поточного стану PLC.
    """

    client, host = get_client()

    if client is None:
        return None, None, "Cannot connect to PLC"

    result = client.read_holding_registers(0, 4, unit=1)

    if result.isError():
        client.close()
        return None, host, "Cannot read PLC registers"

    state = {
        "temperature": result.registers[0],
        "pressure": result.registers[1],
        "water_level": result.registers[2],
        "pump_status": result.registers[3],
    }

    client.close()

    return state, host, None


def write_register(address, value):
    """
    Запис одного значення в holding register.
    """

    client, host = get_client()

    if client is None:
        return False, "Cannot connect to PLC"

    result = client.write_register(address, value, unit=1)

    client.close()

    if result.isError():
        return False, f"Cannot write register {address}"

    return True, f"Register {address} set to {value}"


def detect_anomalies(state):
    """
    Виявлення аномалій за нормальними діапазонами.
    """

    alerts = []

    for tag, value in state.items():
        min_value, max_value = NORMAL_RANGES[tag]

        if value < min_value or value > max_value:
            alerts.append(
                f"{tag} = {value}, норма: {min_value} - {max_value}"
            )

    return alerts


def recover_system():
    """
    Відновлення нормального стану PLC.
    """

    operations = [
        (0, NORMAL_STATE["temperature"]),
        (1, NORMAL_STATE["pressure"]),
        (2, NORMAL_STATE["water_level"]),
        (3, NORMAL_STATE["pump_status"]),
    ]

    errors = []

    for address, value in operations:
        ok, message = write_register(address, value)

        if not ok:
            errors.append(message)

    return errors


def run_false_data_injection(duration=10):
    """
    False Data Injection.
    Протягом кількох секунд постійно підмінює температуру та тиск.
    """

    progress = st.progress(0)
    status_box = st.empty()

    start_time = time.time()

    while time.time() - start_time < duration:
        write_register(0, 999)
        write_register(1, 0)

        state, _, error = read_plc_state()

        if error:
            status_box.error(error)
            break

        status_box.warning(
            f"Injected data: Temperature={state['temperature']}, "
            f"Pressure={state['pressure']}"
        )

        elapsed = time.time() - start_time
        progress.progress(min(int((elapsed / duration) * 100), 100))

        time.sleep(1)

    progress.progress(100)

    


# ------------------------------------------------
# UI
# ------------------------------------------------

st.set_page_config(
    page_title="ICSCyberRange",
    page_icon="🛡️",
    layout="wide"
)

st.title("ICSCyberRange — ICS/SCADA Cyber Range")
st.write("Панель керування симуляцією промислової системи та кібератак.")

state, connected_host, error = read_plc_state()

if error:
    st.error(error)
    st.info("Перевір, чи запущений PLC simulator: python simulator/plc_server.py")
else:
    st.success(f"Connected to PLC: {connected_host}:{PLC_PORT}")

st.divider()


# ------------------------------------------------
# PLC STATUS
# ------------------------------------------------

st.header("1. PLC Status")

if state:
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Temperature", state["temperature"])
    col2.metric("Pressure", state["pressure"])
    col3.metric("Water Level", state["water_level"])
    col4.metric(
        "Pump Status",
        "ON" if state["pump_status"] == 1 else "OFF"
    )

if st.button("Refresh PLC Status"):
    st.rerun()


st.divider()


# ------------------------------------------------
# RED TEAM
# ------------------------------------------------

st.header("2. Red Team — Attacks")

col_attack1, col_attack2 = st.columns(2)

with col_attack1:
    st.subheader("Modbus Command Injection")
    st.write("Несанкціоноване вимкнення насоса через запис у register 3.")

    if st.button("Run Pump OFF Attack"):
        ok, message = write_register(3, 0)

        if ok:
            st.error("Attack executed: Pump forced OFF")
        else:
            st.error(message)

with col_attack2:
    st.subheader("False Data Injection")
    st.write("Підміна значень температури та тиску.")

    duration = st.slider("Attack duration, seconds", 3, 20, 10)

    if st.button("Run False Data Injection"):
        st.warning("False Data Injection started...")
        run_false_data_injection(duration=duration)
        st.warning("False Data Injection finished")


st.divider()


# ------------------------------------------------
# BLUE TEAM
# ------------------------------------------------

st.header("3. Blue Team — Detection and Recovery")

col_def1, col_def2 = st.columns(2)

with col_def1:
    st.subheader("Anomaly Detection")

    if st.button("Run Anomaly Detection"):
        current_state, _, current_error = read_plc_state()

        if current_error:
            st.error(current_error)
        else:
            alerts = detect_anomalies(current_state)

            if alerts:
                st.error("Anomalies detected:")
                for alert in alerts:
                    st.write(f"- {alert}")
            else:
                st.success("System status: normal")

with col_def2:
    st.subheader("Recovery")

    if st.button("Recover System"):
        errors = recover_system()

        if errors:
            st.error("Recovery failed:")
            for err in errors:
                st.write(f"- {err}")
        else:
            st.success("System recovered to normal state")


st.divider()


# ------------------------------------------------
# EXPLANATION
# ------------------------------------------------

st.header("4. Реалізований сценарій")

st.markdown(
    """
    У цій версії реалізовано базовий цикл роботи кіберполігону:

    1. **Нормальна робота PLC** — процес змінює температуру, тиск і рівень води.
    2. **Modbus Command Injection** — атакуючий вимикає насос.
    3. **False Data Injection** — атакуючий підмінює показники датчиків.
    4. **Anomaly Detection** — система виявляє значення поза нормальними межами.
    5. **Recovery** — система повертається до нормального стану.
    """
)

# ------------------------------------------------
# EDUCATIONAL MODE
# ------------------------------------------------

st.header("5. Educational Mode — навчальний сценарій")

scenario = load_training_scenario()

if scenario is None:
    st.error("Не вдалося завантажити сценарій scenarios/beginner.json")
else:
    st.subheader(scenario["title"])

    st.write(f"**Рівень:** {scenario['level']}")
    st.write(f"**Опис:** {scenario['description']}")
    st.write(f"**Мета:** {scenario['goal']}")

    st.markdown("### Нормальний стан системи")

    normal_state = scenario["normal_state"]

    st.write(f"- Температура: {normal_state['temperature']}")
    st.write(f"- Тиск: {normal_state['pressure']}")
    st.write(f"- Рівень води: {normal_state['water_level']}")
    st.write(f"- Стан насоса: {normal_state['pump_status']}")

    st.markdown("### Кроки сценарію")

    for step in scenario["steps"]:
        st.write(f"**Крок {step['step']}. {step['title']}**")
        st.write(step["description"])

    st.markdown("### Практична частина")

    col_edu1, col_edu2, col_edu3 = st.columns(3)

    with col_edu1:
        if st.button("Educational: Check PLC State"):
            edu_state, _, edu_error = read_plc_state()

            if edu_error:
                st.error(edu_error)
            else:
                st.success("Поточний стан PLC:")
                st.write(edu_state)

    with col_edu2:
        if st.button("Educational: Run Attack"):
            ok, message = write_register(
                scenario["attack"]["target_register"],
                scenario["attack"]["malicious_value"]
            )

            if ok:
                st.error("Навчальна атака виконана: насос примусово вимкнено")
            else:
                st.error(message)

    with col_edu3:
        if st.button("Educational: Recover"):
            errors = recover_system()

            if errors:
                st.error("Recovery failed")
                for err in errors:
                    st.write(f"- {err}")
            else:
                st.success("Система відновлена")

    st.markdown("### Контрольне питання")

    question = scenario["question"]

    selected_option = st.radio(
        question["text"],
        question["options"],
        key="educational_question"
    )

    if st.button("Перевірити відповідь"):
        selected_index = question["options"].index(selected_option)

        if selected_index == question["correct_answer"]:
            st.success("Правильно")
        else:
            st.error("Неправильно")

        st.info(question["explanation"])