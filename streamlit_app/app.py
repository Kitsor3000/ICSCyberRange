import os
import sys
import time
import json

# Додаємо корінь проєкту в Python path, щоб Docker Streamlit бачив utils/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import streamlit as st
from pymodbus.client.sync import ModbusTcpClient

from utils.event_logger import log_event, read_logs


# ------------------------------------------------
# PLC CONNECTION SETTINGS
# ------------------------------------------------

PLC_PORT = 5020

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
# STREAMLIT CONFIG
# ------------------------------------------------

st.set_page_config(
    page_title="ICSCyberRange",
    page_icon="🛡️",
    layout="wide"
)


# ------------------------------------------------
# CUSTOM STYLES
# ------------------------------------------------

def apply_custom_styles():
    st.markdown(
        """
        <style>
        /* ---------- GLOBAL ---------- */

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.22), transparent 28%),
                radial-gradient(circle at bottom right, rgba(14, 165, 233, 0.18), transparent 30%),
                linear-gradient(135deg, #020617 0%, #0f172a 45%, #111827 100%);
            color: #e5e7eb;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }

        h1, h2, h3 {
            color: #f8fafc !important;
            letter-spacing: -0.03em;
        }

        p, span, label, div {
            color: #e5e7eb;
        }

        code {
            color: #bae6fd !important;
            background: rgba(15, 23, 42, 0.95) !important;
            border-radius: 8px;
            padding: 2px 6px;
        }

        /* ---------- SIDEBAR ---------- */

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #020617 0%, #0f172a 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.18);
        }

        section[data-testid="stSidebar"] * {
            color: #e5e7eb !important;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] label {
            padding: 8px 10px;
            border-radius: 10px;
            margin-bottom: 4px;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: rgba(59, 130, 246, 0.16);
        }

        /* ---------- HEADER ---------- */

        .main-header {
            padding: 26px 30px;
            border-radius: 24px;
            background:
                linear-gradient(135deg, rgba(37, 99, 235, 0.42), rgba(14, 165, 233, 0.14)),
                rgba(15, 23, 42, 0.92);
            border: 1px solid rgba(96, 165, 250, 0.36);
            margin-bottom: 24px;
            box-shadow: 0 18px 48px rgba(0, 0, 0, 0.34);
        }

        .red-header {
            background:
                linear-gradient(135deg, rgba(220, 38, 38, 0.50), rgba(127, 29, 29, 0.32)),
                rgba(15, 23, 42, 0.92);
            border: 1px solid rgba(248, 113, 113, 0.58);
        }

        .blue-header {
            background:
                linear-gradient(135deg, rgba(37, 99, 235, 0.50), rgba(30, 64, 175, 0.32)),
                rgba(15, 23, 42, 0.92);
            border: 1px solid rgba(96, 165, 250, 0.58);
        }

        .purple-header {
            background:
                linear-gradient(135deg, rgba(147, 51, 234, 0.50), rgba(88, 28, 135, 0.34)),
                rgba(15, 23, 42, 0.92);
            border: 1px solid rgba(192, 132, 252, 0.58);
        }

        .green-header {
            background:
                linear-gradient(135deg, rgba(22, 163, 74, 0.42), rgba(20, 83, 45, 0.32)),
                rgba(15, 23, 42, 0.92);
            border: 1px solid rgba(74, 222, 128, 0.50);
        }

        .main-header h1 {
            margin-bottom: 8px;
            font-size: 38px;
            font-weight: 850;
            color: #f8fafc !important;
        }

        .main-header p {
            color: #cbd5e1;
            font-size: 16px;
            margin: 0;
            max-width: 900px;
        }

        /* ---------- CARDS ---------- */

        .metric-card {
            padding: 22px;
            border-radius: 20px;
            background: rgba(15, 23, 42, 0.94);
            border: 1px solid rgba(51, 65, 85, 0.92);
            box-shadow: 0 12px 34px rgba(0, 0, 0, 0.30);
            min-height: 135px;
            transition: transform 0.15s ease, border 0.15s ease;
        }

        .metric-card:hover {
            transform: translateY(-2px);
            border: 1px solid rgba(96, 165, 250, 0.45);
        }

        .metric-label {
            color: #94a3b8;
            font-size: 13px;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        .metric-value {
            color: #f8fafc;
            font-size: 34px;
            font-weight: 850;
            line-height: 1.15;
            word-break: break-word;
        }

        .metric-sub {
            color: #64748b;
            font-size: 13px;
            margin-top: 10px;
        }

        .normal {
            border-left: 5px solid #22c55e;
        }

        .warning {
            border-left: 5px solid #eab308;
        }

        .danger {
            border-left: 5px solid #ef4444;
        }

        .status-card {
            padding: 22px;
            border-radius: 20px;
            background: rgba(15, 23, 42, 0.94);
            border: 1px solid rgba(148, 163, 184, 0.22);
            box-shadow: 0 12px 34px rgba(0, 0, 0, 0.28);
            margin-bottom: 18px;
        }

        .status-title {
            font-size: 13px;
            color: #94a3b8;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        .status-value {
            font-size: 32px;
            font-weight: 850;
            color: #f8fafc;
        }

        .info-box,
        .red-box,
        .blue-box,
        .edu-box,
        .log-box {
            padding: 20px;
            border-radius: 20px;
            margin-bottom: 18px;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.20);
            line-height: 1.65;
        }

        .info-box {
            background: rgba(30, 41, 59, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.18);
        }

        .red-box {
            background: rgba(127, 29, 29, 0.30);
            border: 1px solid rgba(248, 113, 113, 0.38);
        }

        .blue-box {
            background: rgba(30, 64, 175, 0.28);
            border: 1px solid rgba(96, 165, 250, 0.38);
        }

        .edu-box {
            background: rgba(88, 28, 135, 0.28);
            border: 1px solid rgba(192, 132, 252, 0.38);
        }

        .log-box {
            background: rgba(15, 23, 42, 0.88);
            border: 1px solid rgba(148, 163, 184, 0.18);
        }

        /* ---------- BUTTONS ---------- */

        div.stButton > button {
            width: 100%;
            border-radius: 14px;
            min-height: 48px;
            font-weight: 750;
            border: 1px solid rgba(148, 163, 184, 0.25);
            background: rgba(30, 41, 59, 0.92);
            color: #f8fafc;
            transition: all 0.15s ease;
        }

        div.stButton > button:hover {
            border: 1px solid rgba(96, 165, 250, 0.85);
            background: rgba(37, 99, 235, 0.34);
            color: #ffffff;
            transform: translateY(-1px);
        }

        div.stDownloadButton > button {
            width: 100%;
            border-radius: 14px;
            min-height: 48px;
            font-weight: 750;
        }

        /* ---------- TABLES ---------- */

        div[data-testid="stDataFrame"] {
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid rgba(148, 163, 184, 0.18);
        }

        /* ---------- MOBILE NAV ---------- */

        .mobile-nav-label {
            display: none;
        }

        @media (max-width: 768px) {
            .mobile-nav-label {
                display: block;
                margin-bottom: -10px;
                color: #94a3b8;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.06em;
            }
        }

        /* ---------- MOBILE RESPONSIVE ---------- */

        @media (max-width: 768px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
                padding-top: 1rem;
            }

            .main-header {
                padding: 20px 18px;
                border-radius: 18px;
                margin-bottom: 18px;
            }

            .main-header h1 {
                font-size: 26px;
                line-height: 1.18;
            }

            .main-header p {
                font-size: 14px;
                line-height: 1.5;
            }

            .metric-card {
                padding: 18px;
                min-height: auto;
                border-radius: 16px;
                margin-bottom: 10px;
            }

            .metric-value {
                font-size: 28px;
            }

            .status-card {
                padding: 18px;
                border-radius: 16px;
            }

            .status-value {
                font-size: 26px;
            }

            .info-box,
            .red-box,
            .blue-box,
            .edu-box,
            .log-box {
                padding: 16px;
                border-radius: 16px;
                font-size: 14px;
            }

            div.stButton > button {
                min-height: 50px;
                font-size: 15px;
            }

            section[data-testid="stSidebar"] {
                border-right: none;
            }

            h1 {
                font-size: 26px !important;
            }

            h2 {
                font-size: 22px !important;
            }

            h3 {
                font-size: 18px !important;
            }
        }

        @media (max-width: 480px) {
            .main-header h1 {
                font-size: 23px;
            }

            .metric-value {
                font-size: 25px;
            }

            .metric-label {
                font-size: 12px;
            }

            .metric-sub {
                font-size: 12px;
            }

            .status-value {
                font-size: 23px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_header(title, subtitle, variant="default"):
    header_class = "main-header"

    if variant == "red":
        header_class += " red-header"
    elif variant == "blue":
        header_class += " blue-header"
    elif variant == "purple":
        header_class += " purple-header"
    elif variant == "green":
        header_class += " green-header"

    st.markdown(
        f"""
        <div class="{header_class}">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_metric_card(label, value, unit="", subtext="", status="normal"):
    st.markdown(
        f"""
        <div class="metric-card {status}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value} {unit}</div>
            <div class="metric-sub">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_status_card(title, value, icon="⌁", status="normal"):
    st.markdown(
        f"""
        <div class="status-card {status}">
            <div class="status-title">{title}</div>
            <div class="status-value">{icon} {value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


apply_custom_styles()


# ------------------------------------------------
# SCENARIOS
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


# ------------------------------------------------
# MODBUS HELPERS
# ------------------------------------------------

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


def get_system_status(state):
    """
    Визначення загального стану системи.
    """

    if state is None:
        return "OFFLINE", "◆", "danger"

    alerts = detect_anomalies(state)

    if state["pump_status"] == 0:
        return "UNDER ATTACK", "⛔", "danger"

    if alerts:
        return "WARNING", "◇", "warning"

    return "NORMAL", "⌁", "normal"


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

    final_state, _, _ = read_plc_state()

    log_event(
        event_type="FALSE_DATA_INJECTION",
        description=f"False Data Injection виконано протягом {duration} секунд",
        state=final_state
    )


# ------------------------------------------------
# SIDEBAR + MOBILE NAVIGATION
# ------------------------------------------------

st.sidebar.title("ICSCyberRange")
st.sidebar.caption("ICS/SCADA Cyber Range Platform")

pages = [
    "Dashboard",
    "Red Team",
    "Blue Team",
    "Educational Mode",
    "Event Logs",
]

sidebar_page = st.sidebar.radio("Navigation", pages)

st.markdown(
    '<div class="mobile-nav-label">Mobile navigation</div>',
    unsafe_allow_html=True
)

mobile_page = st.selectbox(
    "Select page",
    pages,
    index=pages.index(sidebar_page),
    label_visibility="collapsed"
)

page = mobile_page

st.sidebar.divider()

state, connected_host, error = read_plc_state()

if error:
    st.sidebar.error("◆ PLC Offline")
else:
    status, icon, status_class = get_system_status(state)
    st.sidebar.success(f"{icon} {status}")
    st.sidebar.caption(f"PLC: {connected_host}:{PLC_PORT}")

st.sidebar.divider()

st.sidebar.markdown(
    """
    **Services**

    - Streamlit: `8501`
    - Grafana: `3000`
    - InfluxDB: `8086`
    - PLC Modbus: `5020`
    """
)

st.sidebar.divider()

st.sidebar.caption("Diploma project: ICSCyberRange")


# ------------------------------------------------
# PAGE: DASHBOARD
# ------------------------------------------------

if page == "Dashboard":
    render_header(
        "⌁ ICSCyberRange Dashboard",
        "Моніторинг віртуальної ICS/SCADA системи, стану PLC та безпеки промислового процесу."
    )

    if error:
        st.error(error)
        st.info("Запусти PLC simulator: `python simulator/plc_server.py`")
    else:
        status, icon, status_class = get_system_status(state)

        render_status_card(
            title="System Security Status",
            value=status,
            icon=icon,
            status=status_class
        )

        st.divider()

        col1, col2 = st.columns(2)
        col3, col4 = st.columns(2)

        with col1:
            render_metric_card(
                "Temperature",
                state["temperature"],
                "°C",
                "PLC register 0",
                "warning" if state["temperature"] > 80 else "normal"
            )

        with col2:
            render_metric_card(
                "Pressure",
                state["pressure"],
                "bar",
                "PLC register 1",
                "warning" if state["pressure"] > 15 or state["pressure"] < 1 else "normal"
            )

        with col3:
            render_metric_card(
                "Water Level",
                state["water_level"],
                "%",
                "PLC register 2",
                "warning" if state["water_level"] > 90 or state["water_level"] < 10 else "normal"
            )

        with col4:
            render_metric_card(
                "Pump Status",
                "ON" if state["pump_status"] == 1 else "OFF",
                "",
                "PLC register 3",
                "normal" if state["pump_status"] == 1 else "danger"
            )

        st.divider()

        left, right = st.columns([1.2, 1])

        with left:
            st.subheader("Current Anomaly Check")
            alerts = detect_anomalies(state)

            if alerts:
                st.warning("Detected anomalies:")
                for alert in alerts:
                    st.write(f"- {alert}")
            else:
                st.success("No anomalies detected.")

        with right:
            st.subheader("Quick Actions")

            if st.button("Refresh PLC Status"):
                current_state, _, current_error = read_plc_state()

                if current_error:
                    st.error(current_error)
                else:
                    log_event(
                        event_type="PLC_STATUS_READ",
                        description="Користувач оновив стан PLC",
                        state=current_state
                    )

                st.rerun()

            if st.button("Show Grafana Link"):
                st.info("Grafana dashboard доступний за адресою: http://localhost:3000")

    st.divider()

    st.subheader("Architecture Overview")

    st.markdown(
        """
        <div class="info-box">
        <b>Поточний ланцюг роботи системи:</b><br><br>
        Streamlit UI → Red/Blue Team Modules → Modbus TCP → PLC Simulator → Telemetry Collector → InfluxDB → Grafana
        </div>
        """,
        unsafe_allow_html=True
    )


# ------------------------------------------------
# PAGE: RED TEAM
# ------------------------------------------------

elif page == "Red Team":
    render_header(
        "⛔ Red Team — Attack Simulation",
        "Запуск контрольованих атак на віртуальну ICS/SCADA систему через Modbus TCP.",
        variant="red"
    )

    col_attack1, col_attack2 = st.columns(2)

    with col_attack1:
        st.subheader("Modbus Command Injection")

        st.markdown(
            """
            <div class="red-box">
                <b>Ціль атаки:</b> Pump Status<br>
                <b>Register:</b> 3<br>
                <b>Malicious value:</b> 0<br>
                <b>Наслідок:</b> насос примусово вимикається
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write(
            """
            Цей сценарій демонструє несанкціонований запис у Modbus-регістр,
            який керує виконавчим механізмом.
            """
        )

        if st.button("Run Pump OFF Attack"):
            ok, message = write_register(3, 0)

            current_state, _, _ = read_plc_state()

            if ok:
                log_event(
                    event_type="MODBUS_COMMAND_INJECTION",
                    description="Атака виконана: насос примусово вимкнено",
                    state=current_state
                )

                st.error("Attack executed: Pump forced OFF")
            else:
                st.error(message)

    with col_attack2:
        st.subheader("False Data Injection")

        st.markdown(
            """
            <div class="red-box">
                <b>Ціль атаки:</b> Sensor values<br>
                <b>Register 0:</b> temperature = 999<br>
                <b>Register 1:</b> pressure = 0<br>
                <b>Наслідок:</b> оператор бачить неправдиві дані
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write(
            """
            Цей сценарій демонструє підміну технологічних параметрів,
            які можуть використовуватись оператором або системою моніторингу.
            """
        )

        duration = st.slider("Attack duration, seconds", 3, 20, 10)

        if st.button("Run False Data Injection"):
            st.warning("False Data Injection started...")
            run_false_data_injection(duration=duration)
            st.warning("False Data Injection finished")

    st.divider()

    st.subheader("Attack Explanation")

    st.markdown(
        """
        <div class="info-box">
        У цьому модулі реалізовано два базові Red Team сценарії:<br><br>
        <b>1. Modbus Command Injection</b> — зміна стану виконавчого механізму.<br>
        <b>2. False Data Injection</b> — підміна технологічних параметрів.<br><br>
        Обидва сценарії демонструють ризики незахищеного Modbus TCP у промислових системах.
        </div>
        """,
        unsafe_allow_html=True
    )


# ------------------------------------------------
# PAGE: BLUE TEAM
# ------------------------------------------------

elif page == "Blue Team":
    render_header(
        "⬢ Blue Team — Detection and Recovery",
        "Виявлення аномалій, аналіз стану PLC та повернення системи до безпечного режиму.",
        variant="blue"
    )

    col_def1, col_def2 = st.columns(2)

    with col_def1:
        st.subheader("Anomaly Detection")

        st.markdown(
            """
            <div class="blue-box">
                <b>Метод:</b> rule-based anomaly detection<br>
                <b>Перевіряє:</b> температуру, тиск, рівень води, стан насоса<br>
                <b>Результат:</b> повідомлення про аномалію
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("Run Anomaly Detection"):
            current_state, _, current_error = read_plc_state()

            if current_error:
                st.error(current_error)
            else:
                alerts = detect_anomalies(current_state)

                if alerts:
                    log_event(
                        event_type="ANOMALY_DETECTION",
                        description="Виявлено аномалії: " + "; ".join(alerts),
                        state=current_state
                    )

                    st.error("Anomalies detected:")
                    for alert in alerts:
                        st.write(f"- {alert}")
                else:
                    log_event(
                        event_type="ANOMALY_DETECTION",
                        description="Аномалій не виявлено",
                        state=current_state
                    )

                    st.success("System status: normal")

    with col_def2:
        st.subheader("Recovery")

        st.markdown(
            """
            <div class="blue-box">
                <b>Recovery action:</b> повернення PLC до нормального стану<br>
                <b>Temperature:</b> 25<br>
                <b>Pressure:</b> 5<br>
                <b>Water Level:</b> 50<br>
                <b>Pump:</b> ON
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("Recover System"):
            errors = recover_system()

            current_state, _, _ = read_plc_state()

            if errors:
                st.error("Recovery failed:")
                for err in errors:
                    st.write(f"- {err}")
            else:
                log_event(
                    event_type="RECOVERY_EXECUTED",
                    description="Система відновлена до нормального стану",
                    state=current_state
                )

                st.success("System recovered to normal state")

    st.divider()

    st.subheader("Normal Operating Ranges")

    df_ranges = pd.DataFrame(
        [
            {
                "Parameter": key,
                "Min": value[0],
                "Max": value[1],
            }
            for key, value in NORMAL_RANGES.items()
        ]
    )

    st.dataframe(df_ranges, use_container_width=True)


# ------------------------------------------------
# PAGE: EDUCATIONAL MODE
# ------------------------------------------------

elif page == "Educational Mode":
    render_header(
        "✦ Educational Mode",
        "Навчальний режим для покрокового вивчення атак і захисту ICS/SCADA систем.",
        variant="purple"
    )

    scenario = load_training_scenario()

    if scenario is None:
        st.error("Не вдалося завантажити сценарій scenarios/beginner.json")
    else:
        st.subheader(scenario["title"])

        st.markdown(
            """
            <div class="edu-box">
                Цей сценарій допомагає студенту зрозуміти, як атака через Modbus TCP впливає
                на промисловий процес і які дії повинен виконати оператор після інциденту.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write(f"**Рівень:** {scenario['level']}")
        st.write(f"**Опис:** {scenario['description']}")
        st.write(f"**Мета:** {scenario['goal']}")

        st.divider()

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

        st.divider()

        st.markdown("### Практична частина")

        col_edu1, col_edu2, col_edu3 = st.columns(3)

        with col_edu1:
            if st.button("Educational: Check PLC State"):
                edu_state, _, edu_error = read_plc_state()

                if edu_error:
                    st.error(edu_error)
                else:
                    log_event(
                        event_type="EDUCATIONAL_STATUS_READ",
                        description="У навчальному режимі перевірено стан PLC",
                        state=edu_state
                    )

                    st.success("Поточний стан PLC:")
                    st.write(edu_state)

        with col_edu2:
            if st.button("Educational: Run Attack"):
                ok, message = write_register(
                    scenario["attack"]["target_register"],
                    scenario["attack"]["malicious_value"]
                )

                current_state, _, _ = read_plc_state()

                if ok:
                    log_event(
                        event_type="EDUCATIONAL_ATTACK",
                        description="Навчальна атака виконана: насос примусово вимкнено",
                        state=current_state
                    )

                    st.error("Навчальна атака виконана: насос примусово вимкнено")
                else:
                    st.error(message)

        with col_edu3:
            if st.button("Educational: Recover"):
                errors = recover_system()

                current_state, _, _ = read_plc_state()

                if errors:
                    st.error("Recovery failed")
                    for err in errors:
                        st.write(f"- {err}")
                else:
                    log_event(
                        event_type="EDUCATIONAL_RECOVERY",
                        description="У навчальному режимі виконано відновлення системи",
                        state=current_state
                    )

                    st.success("Система відновлена")

        st.divider()

        st.markdown("### Контрольне питання")

        question = scenario["question"]

        selected_option = st.radio(
            question["text"],
            question["options"],
            key="educational_question"
        )

        if st.button("Перевірити відповідь"):
            selected_index = question["options"].index(selected_option)

            current_state, _, _ = read_plc_state()

            if selected_index == question["correct_answer"]:
                log_event(
                    event_type="EDUCATIONAL_ANSWER",
                    description="Користувач дав правильну відповідь у навчальному сценарії",
                    state=current_state
                )

                st.success("Правильно")
            else:
                log_event(
                    event_type="EDUCATIONAL_ANSWER",
                    description="Користувач дав неправильну відповідь у навчальному сценарії",
                    state=current_state
                )

                st.error("Неправильно")

            st.info(question["explanation"])


# ------------------------------------------------
# PAGE: EVENT LOGS
# ------------------------------------------------

elif page == "Event Logs":
    render_header(
        "▣ Simulation Event Logs",
        "Історія дій користувача, атак, виявлення аномалій та recovery-процедур.",
        variant="green"
    )

    logs = read_logs(limit=100)

    if logs:
        df_logs = pd.DataFrame(logs)

        st.markdown(
            """
            <div class="log-box">
                Нижче відображено останні події симуляції.
                Цей журнал можна використати для аналізу сценарію атаки та формування звіту.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.dataframe(df_logs, use_container_width=True)

        st.download_button(
            label="Download logs as CSV",
            data=df_logs.to_csv(index=False).encode("utf-8"),
            file_name="simulation_log.csv",
            mime="text/csv"
        )
    else:
        st.info("Журнал подій поки порожній.")