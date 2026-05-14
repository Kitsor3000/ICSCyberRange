import os
import sys
import time
import json
import random
from pathlib import Path
from html import escape

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from pymodbus.client.sync import ModbusTcpClient

from utils.event_logger import log_event, read_logs


# ------------------------------------------------
# PLC SETTINGS
# ------------------------------------------------

PLC_PORT = 5020

PLC_HOSTS = [
    os.getenv("PLC_HOST", "host.docker.internal"),
    "127.0.0.1",
]


# ------------------------------------------------
# REGISTER MAP
# ------------------------------------------------

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


NORMAL_RANGES = {
    # Pump Station
    "temperature": (18, 45),
    "pressure": (2, 10),
    "water_level": (20, 100),
    "pump_status": (1, 1),

    # Conveyor Line
    "conveyor_status": (1, 1),
    "motor_speed": (40, 100),
    "motor_current": (5, 25),
    "emergency_stop": (0, 0),

    # Cooling System
    "fan_status": (1, 1),
    "coolant_temperature": (18, 40),
    "valve_position": (30, 100),
    "cooling_alarm": (0, 0),
}


NORMAL_STATE = {
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


SYSTEMS = {
    "Pump Station": {
        "variant": "pump",
        "icon": "⌁",
        "description": "Насосна станція: температура, тиск, рівень води та стан насоса.",
        "tags": ["temperature", "pressure", "water_level", "pump_status"],
    },
    "Conveyor Line": {
        "variant": "conveyor",
        "icon": "⬡",
        "description": "Конвеєрна лінія: стан конвеєра, швидкість двигуна, струм і аварійна зупинка.",
        "tags": ["conveyor_status", "motor_speed", "motor_current", "emergency_stop"],
    },
    "Cooling System": {
        "variant": "cooling",
        "icon": "✦",
        "description": "Система охолодження: вентилятор, температура охолоджувача, клапан і сигнал аварії.",
        "tags": ["fan_status", "coolant_temperature", "valve_position", "cooling_alarm"],
    },
}


SYSTEM_BY_TAG = {
    # Pump Station
    "temperature": "Pump Station",
    "pressure": "Pump Station",
    "water_level": "Pump Station",
    "pump_status": "Pump Station",

    # Conveyor Line
    "conveyor_status": "Conveyor Line",
    "motor_speed": "Conveyor Line",
    "motor_current": "Conveyor Line",
    "emergency_stop": "Conveyor Line",

    # Cooling System
    "fan_status": "Cooling System",
    "coolant_temperature": "Cooling System",
    "valve_position": "Cooling System",
    "cooling_alarm": "Cooling System",
}


ATTACKS = [
    # Pump Station
    {
        "system": "Pump Station",
        "name": "Pump OFF Attack",
        "level": "Easy",
        "event": "PUMP_OFF_ATTACK",
        "description": "Несанкціоноване вимкнення насоса.",
        "writes": [("pump_status", 0)],
        "duration": 0,
    },
    {
        "system": "Pump Station",
        "name": "Pump False Data Injection",
        "level": "Medium",
        "event": "PUMP_FALSE_DATA_INJECTION",
        "description": "Підміна температури та тиску насосної станції.",
        "writes": [("temperature", 999), ("pressure", 0)],
        "duration": 10,
    },
    {
        "system": "Pump Station",
        "name": "Water Level Spoofing",
        "level": "Medium",
        "event": "WATER_LEVEL_SPOOFING",
        "description": "Підміна рівня води в резервуарі.",
        "writes": [("water_level", 0)],
        "duration": 10,
    },

    # Conveyor Line
    {
        "system": "Conveyor Line",
        "name": "Conveyor Stop Attack",
        "level": "Easy",
        "event": "CONVEYOR_STOP_ATTACK",
        "description": "Примусова зупинка конвеєра.",
        "writes": [("conveyor_status", 0)],
        "duration": 0,
    },
    {
        "system": "Conveyor Line",
        "name": "Motor Speed Overdrive",
        "level": "Medium",
        "event": "MOTOR_SPEED_OVERDRIVE",
        "description": "Встановлення небезпечної швидкості двигуна.",
        "writes": [("motor_speed", 120)],
        "duration": 0,
    },
    {
        "system": "Conveyor Line",
        "name": "Emergency Stop Abuse",
        "level": "Hard",
        "event": "EMERGENCY_STOP_ABUSE",
        "description": "Активація аварійної зупинки конвеєра.",
        "writes": [("emergency_stop", 1)],
        "duration": 0,
    },

    # Cooling System
    {
        "system": "Cooling System",
        "name": "Fan Shutdown Attack",
        "level": "Easy",
        "event": "FAN_SHUTDOWN_ATTACK",
        "description": "Вимкнення вентилятора охолодження.",
        "writes": [("fan_status", 0)],
        "duration": 0,
    },
    {
        "system": "Cooling System",
        "name": "Valve Manipulation Attack",
        "level": "Medium",
        "event": "VALVE_MANIPULATION_ATTACK",
        "description": "Закриття клапана охолодження.",
        "writes": [("valve_position", 0)],
        "duration": 0,
    },
    {
        "system": "Cooling System",
        "name": "Cooling Temperature Spoofing",
        "level": "Hard",
        "event": "COOLING_TEMP_SPOOFING",
        "description": "Підміна температури охолоджуючої рідини.",
        "writes": [("coolant_temperature", 80)],
        "duration": 10,
    },
]


TRAINING_QUESTIONS = [
    {
        "system": "Pump Station",
        "question": "Який Modbus register відповідає за стан насоса?",
        "options": ["0", "1", "2", "3"],
        "answer": "3",
        "explanation": "Register 3 відповідає за pump_status. 1 — насос увімкнений, 0 — вимкнений.",
    },
    {
        "system": "Pump Station",
        "question": "Що станеться, якщо записати 0 у pump_status?",
        "options": [
            "Насос вимкнеться",
            "Конвеєр прискориться",
            "Охолодження увімкнеться",
            "Тиск стане нормальним",
        ],
        "answer": "Насос вимкнеться",
        "explanation": "pump_status = 0 означає примусове вимкнення насоса.",
    },
    {
        "system": "Pump Station",
        "question": "Який параметр показує рівень води?",
        "options": ["pressure", "water_level", "motor_speed", "cooling_alarm"],
        "answer": "water_level",
        "explanation": "water_level показує рівень води в резервуарі насосної станції.",
    },
    {
        "system": "Conveyor Line",
        "question": "Який параметр відповідає за швидкість конвеєра?",
        "options": ["motor_speed", "pressure", "fan_status", "valve_position"],
        "answer": "motor_speed",
        "explanation": "motor_speed показує швидкість двигуна конвеєра. Норма — 40–100%.",
    },
    {
        "system": "Conveyor Line",
        "question": "Що означає emergency_stop = 1?",
        "options": [
            "Аварійна зупинка активна",
            "Конвеєр працює нормально",
            "Насос вимкнений",
            "Температура в нормі",
        ],
        "answer": "Аварійна зупинка активна",
        "explanation": "emergency_stop = 1 означає, що аварійна зупинка конвеєра активна.",
    },
    {
        "system": "Conveyor Line",
        "question": "Який параметр показує струм двигуна?",
        "options": ["motor_current", "water_level", "coolant_temperature", "pump_status"],
        "answer": "motor_current",
        "explanation": "motor_current показує струм двигуна конвеєра в амперах.",
    },
    {
        "system": "Cooling System",
        "question": "Який register відповідає за вентилятор охолодження?",
        "options": ["8", "9", "10", "11"],
        "answer": "8",
        "explanation": "Register 8 — це fan_status. 1 — вентилятор ON, 0 — OFF.",
    },
    {
        "system": "Cooling System",
        "question": "Що означає cooling_alarm = 1?",
        "options": [
            "У системі охолодження аварія",
            "Насос працює нормально",
            "Конвеєр вимкнений",
            "Тиск у нормі",
        ],
        "answer": "У системі охолодження аварія",
        "explanation": "cooling_alarm = 1 означає аварійний стан системи охолодження.",
    },
    {
        "system": "Cooling System",
        "question": "Який параметр відповідає за положення клапана?",
        "options": ["valve_position", "pressure", "motor_current", "water_level"],
        "answer": "valve_position",
        "explanation": "valve_position показує, наскільки відкритий клапан охолодження.",
    },
]


# ------------------------------------------------
# STREAMLIT CONFIG
# ------------------------------------------------

st.set_page_config(
    page_title="ICSCyberRange",
    page_icon="🛡️",
    layout="wide"
)


# ------------------------------------------------
# DESIGN
# ------------------------------------------------

def apply_custom_styles():
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.15), transparent 28%),
                radial-gradient(circle at bottom right, rgba(147, 51, 234, 0.13), transparent 30%),
                linear-gradient(135deg, #020617 0%, #0f172a 48%, #111827 100%);
            color: #e5e7eb;
        }

        .block-container {
            padding-top: 1.4rem;
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

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #020617 0%, #0f172a 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.18);
        }

        section[data-testid="stSidebar"] * {
            color: #e5e7eb !important;
        }

        .main-header {
            padding: 24px 28px;
            border-radius: 22px;
            background:
                linear-gradient(135deg, rgba(37, 99, 235, 0.35), rgba(14, 165, 233, 0.10)),
                rgba(15, 23, 42, 0.92);
            border: 1px solid rgba(96, 165, 250, 0.30);
            margin-bottom: 22px;
            box-shadow: 0 16px 42px rgba(0, 0, 0, 0.30);
        }

        .main-header h1 {
            margin-bottom: 8px;
            font-size: 36px;
            font-weight: 850;
        }

        .main-header p {
            color: #cbd5e1;
            font-size: 16px;
            margin: 0;
            max-width: 980px;
        }

        .red-header {
            background:
                linear-gradient(135deg, rgba(220, 38, 38, 0.46), rgba(127, 29, 29, 0.28)),
                rgba(15, 23, 42, 0.92);
            border: 1px solid rgba(248, 113, 113, 0.52);
        }

        .blue-header {
            background:
                linear-gradient(135deg, rgba(37, 99, 235, 0.46), rgba(30, 64, 175, 0.28)),
                rgba(15, 23, 42, 0.92);
            border: 1px solid rgba(96, 165, 250, 0.52);
        }

        .purple-header {
            background:
                linear-gradient(135deg, rgba(147, 51, 234, 0.46), rgba(88, 28, 135, 0.30)),
                rgba(15, 23, 42, 0.92);
            border: 1px solid rgba(192, 132, 252, 0.52);
        }

        .system-card,
        .metric-card,
        .attack-card,
        .info-box,
        .log-box {
            padding: 18px;
            border-radius: 18px;
            background: rgba(15, 23, 42, 0.90);
            border: 1px solid rgba(148, 163, 184, 0.16);
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.23);
            margin-bottom: 16px;
            transition: transform 0.18s ease, border 0.18s ease, box-shadow 0.18s ease;
        }

        .system-card:hover,
        .metric-card:hover,
        .attack-card:hover,
        .info-box:hover {
            transform: translateY(-3px);
            border: 1px solid rgba(96, 165, 250, 0.48);
            box-shadow: 0 18px 42px rgba(0, 0, 0, 0.32);
        }

        .metric-label {
            color: #94a3b8;
            font-size: 12px;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        .metric-value {
            color: #f8fafc;
            font-size: 30px;
            font-weight: 850;
            line-height: 1.15;
            word-break: break-word;
        }

        .metric-sub {
            color: #64748b;
            font-size: 12px;
            margin-top: 8px;
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

        .pump {
            border-left: 5px solid #38bdf8;
        }

        .conveyor {
            border-left: 5px solid #f97316;
        }

        .cooling {
            border-left: 5px solid #a78bfa;
        }

        .status-card {
            padding: 20px;
            border-radius: 18px;
            background: rgba(15, 23, 42, 0.94);
            border: 1px solid rgba(148, 163, 184, 0.20);
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.25);
            margin-bottom: 18px;
        }

        .status-title {
            font-size: 12px;
            color: #94a3b8;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        .status-value {
            font-size: 28px;
            font-weight: 850;
            color: #f8fafc;
        }

        .attack-level {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            background: rgba(30, 41, 59, 0.9);
            border: 1px solid rgba(148, 163, 184, 0.25);
            margin-bottom: 10px;
        }

        div.stButton > button {
            width: 100%;
            border-radius: 12px;
            min-height: 46px;
            font-weight: 750;
            border: 1px solid rgba(148, 163, 184, 0.25);
            background: rgba(30, 41, 59, 0.92);
            color: #f8fafc;
            transition: all 0.15s ease;
        }

        div.stButton > button:hover {
            border: 1px solid rgba(96, 165, 250, 0.85);
            background: rgba(37, 99, 235, 0.32);
            color: #ffffff;
            transform: translateY(-1px);
        }

        div.stDownloadButton > button {
            width: 100%;
            border-radius: 12px;
            min-height: 46px;
            font-weight: 750;
        }

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

            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
                padding-top: 1rem;
            }

            .main-header {
                padding: 18px 16px;
                border-radius: 16px;
            }

            .main-header h1 {
                font-size: 24px;
                line-height: 1.18;
            }

            .main-header p {
                font-size: 14px;
                line-height: 1.5;
            }

            .metric-card,
            .system-card,
            .attack-card,
            .info-box,
            .log-box {
                padding: 15px;
                border-radius: 15px;
            }

            .metric-value {
                font-size: 25px;
            }

            .status-value {
                font-size: 23px;
            }

            div.stButton > button {
                min-height: 50px;
                font-size: 15px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_header(title, subtitle, variant="default"):
    css_class = "main-header"

    if variant == "red":
        css_class += " red-header"
    elif variant == "blue":
        css_class += " blue-header"
    elif variant == "purple":
        css_class += " purple-header"

    st.markdown(
        f"""
        <div class="{css_class}">
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


def render_system_intro(system_name, system_config):
    st.markdown(
        f"""
        <div class="system-card {system_config['variant']}">
            <h3>{system_config['icon']} {system_name}</h3>
            <p>{system_config['description']}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_attack_card(attack):
    writes_text = "<br>".join(
        [
            f"R{REGISTER_MAP[tag]}: <b>{escape(tag)}</b> → <b>{value}</b>"
            for tag, value in attack["writes"]
        ]
    )

    duration_text = "Single write" if attack["duration"] == 0 else f"{attack['duration']} seconds"

    st.markdown(
        f"""
        <div class="attack-card danger">
            <span class="attack-level">{escape(attack['level'])}</span>
            <h3>{escape(attack['name'])}</h3>
            <p>{escape(attack['description'])}</p>
            <p>{writes_text}</p>
            <p><b>Mode:</b> {duration_text}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


apply_custom_styles()


# ------------------------------------------------
# MODBUS HELPERS
# ------------------------------------------------

def get_client():
    for host in PLC_HOSTS:
        client = ModbusTcpClient(host, port=PLC_PORT)

        if client.connect():
            return client, host

        client.close()

    return None, None


def read_plc_state():
    client, host = get_client()

    if client is None:
        return None, None, "Cannot connect to PLC"

    result = client.read_holding_registers(0, 12, unit=1)

    if result.isError():
        client.close()
        return None, host, "Cannot read PLC registers"

    registers = result.registers

    state = {
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

    client.close()

    return state, host, None


def write_register(tag, value):
    client, host = get_client()

    if client is None:
        return False, "Cannot connect to PLC"

    address = REGISTER_MAP[tag]
    result = client.write_register(address, int(value), unit=1)

    client.close()

    if result.isError():
        return False, f"Cannot write register {address}"

    return True, f"{tag} set to {value}"


def run_repeated_write(writes, duration=10):
    progress = st.progress(0)
    status_box = st.empty()

    start_time = time.time()

    while time.time() - start_time < duration:
        for tag, value in writes:
            write_register(tag, value)

        current_state, _, error = read_plc_state()

        if error:
            status_box.error(error)
            break

        status_box.warning("Attack in progress...")

        elapsed = time.time() - start_time
        progress.progress(min(int((elapsed / duration) * 100), 100))

        time.sleep(1)

    progress.progress(100)


def execute_attack(attack):
    """
    Запускає атаку.
    Якщо duration = 0 — один запис у Modbus register.
    Якщо duration > 0 — повторює запис кілька секунд.
    """

    if attack["duration"] > 0:
        run_repeated_write(attack["writes"], duration=attack["duration"])
    else:
        for tag, value in attack["writes"]:
            ok, message = write_register(tag, value)

            if not ok:
                return False, message

    current_state, _, _ = read_plc_state()

    log_event(
        event_type=attack["event"],
        description=f"Запущено атаку: {attack['name']}",
        state=current_state
    )

    return True, f"Attack executed: {attack['name']}"


# ------------------------------------------------
# BLUE TEAM LOGIC
# ------------------------------------------------

def detect_anomalies(state):
    alerts = []

    for tag, value in state.items():
        min_value, max_value = NORMAL_RANGES[tag]

        if value < min_value or value > max_value:
            system_name = SYSTEM_BY_TAG.get(tag, "Unknown System")

            alerts.append({
                "system": system_name,
                "tag": tag,
                "value": value,
                "normal_range": f"{min_value} - {max_value}",
                "message": f"{system_name}: {tag} = {value}, норма: {min_value} - {max_value}",
            })

    return alerts


def get_system_status(state):
    if state is None:
        return "OFFLINE", "◆", "danger"

    alerts = detect_anomalies(state)

    if state["emergency_stop"] == 1 or state["cooling_alarm"] == 1:
        return "CRITICAL", "⛔", "danger"

    if state["pump_status"] == 0 or state["conveyor_status"] == 0 or state["fan_status"] == 0:
        return "UNDER ATTACK", "◇", "danger"

    if alerts:
        return "WARNING", "◇", "warning"

    return "NORMAL", "⌁", "normal"


def recover_pump_station():
    for tag in ["temperature", "pressure", "water_level", "pump_status"]:
        ok, message = write_register(tag, NORMAL_STATE[tag])

        if not ok:
            return False, message

    return True, "Pump Station recovered"


def recover_conveyor_line():
    for tag in ["conveyor_status", "motor_speed", "motor_current", "emergency_stop"]:
        ok, message = write_register(tag, NORMAL_STATE[tag])

        if not ok:
            return False, message

    return True, "Conveyor Line recovered"


def recover_cooling_system():
    for tag in ["fan_status", "coolant_temperature", "valve_position", "cooling_alarm"]:
        ok, message = write_register(tag, NORMAL_STATE[tag])

        if not ok:
            return False, message

    return True, "Cooling System recovered"


def recover_full_system():
    recovery_functions = [
        recover_pump_station,
        recover_conveyor_line,
        recover_cooling_system,
    ]

    for recovery_function in recovery_functions:
        ok, message = recovery_function()

        if not ok:
            return False, message

    return True, "Full system recovered"


def recover_by_system(system_name):
    if system_name == "Pump Station":
        return recover_pump_station()

    if system_name == "Conveyor Line":
        return recover_conveyor_line()

    if system_name == "Cooling System":
        return recover_cooling_system()

    return recover_full_system()


# ------------------------------------------------
# PDF REPORT
# ------------------------------------------------

def generate_pdf_report_safe():
    try:
        from reports.pdf_report import generate_pdf_report
        generate_pdf_report()
        return True, "reports/simulation_report.pdf"

    except Exception as error:
        return False, str(error)


# ------------------------------------------------
# SIDEBAR
# ------------------------------------------------

st.sidebar.title("ICSCyberRange")
st.sidebar.caption("ICS/SCADA Cyber Range Platform")

pages = [
    "Overview",
    "Systems",
    "Red Team",
    "Blue Team",
    "Training",
    "How It Works",
]

sidebar_page = st.sidebar.radio("Navigation", pages)

st.markdown('<div class="mobile-nav-label">Mobile navigation</div>', unsafe_allow_html=True)

page = st.selectbox(
    "Select page",
    pages,
    index=pages.index(sidebar_page),
    label_visibility="collapsed"
)

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
# PAGE: OVERVIEW
# ------------------------------------------------

if page == "Overview":
    render_header(
        "⌁ ICSCyberRange Control Center",
        "Симуляція атак і захисту трьох промислових ICS/SCADA підсистем."
    )

    if error:
        st.error(error)
        st.info("Запусти PLC simulator: `python simulator/plc_server.py`")
    else:
        status, icon, status_class = get_system_status(state)

        render_status_card(
            title="Global Security Status",
            value=status,
            icon=icon,
            status=status_class
        )

        s1, s2, s3 = st.columns(3)

        with s1:
            render_system_intro("Pump Station", SYSTEMS["Pump Station"])

        with s2:
            render_system_intro("Conveyor Line", SYSTEMS["Conveyor Line"])

        with s3:
            render_system_intro("Cooling System", SYSTEMS["Cooling System"])

        st.markdown(
            """
            <div class="info-box">
            <b>Як працювати з платформою:</b><br>
            1. Перевір стан систем у вкладці <b>Systems</b>.<br>
            2. Запусти атаку у вкладці <b>Red Team</b>.<br>
            3. Перейди в <b>Blue Team</b>, знайди аномалію і виконай recovery.<br>
            4. Після симуляції створи PDF-звіт у <b>Blue Team</b>.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.divider()

        alerts = detect_anomalies(state)

        st.subheader("Fast Health Check")

        if alerts:
            st.warning(f"Detected anomalies: {len(alerts)}")

            for alert in alerts:
                st.write(f"- {alert['message']}")
        else:
            st.success("All systems are operating normally.")

        st.divider()

        if st.button("Open Grafana Info"):
            st.info("Grafana dashboard: http://localhost:3000")


# ------------------------------------------------
# PAGE: SYSTEMS
# ------------------------------------------------

elif page == "Systems":
    render_header(
        "⬡ Industrial Systems Dashboard",
        "Поточний стан Pump Station, Conveyor Line та Cooling System."
    )

    top_col1, top_col2 = st.columns([1, 2])

    with top_col1:
        if st.button("Refresh PLC Status"):
            current_state, _, current_error = read_plc_state()

            if current_error:
                st.error(current_error)
            else:
                log_event(
                    event_type="PLC_STATUS_READ",
                    description="Користувач оновив стан PLC на сторінці Systems",
                    state=current_state
                )
                st.rerun()

    with top_col2:
        st.info("Ця сторінка показує поточний стан усіх трьох промислових підсистем.")

    st.divider()

    if error:
        st.error(error)
    else:
        for system_name, config in SYSTEMS.items():
            render_system_intro(system_name, config)

            cols = st.columns(4)

            for index, tag in enumerate(config["tags"]):
                min_value, max_value = NORMAL_RANGES[tag]
                value = state[tag]

                status_class = "normal"

                if value < min_value or value > max_value:
                    status_class = "danger"

                label = tag.replace("_", " ").title()

                unit = ""

                if "temperature" in tag:
                    unit = "°C"
                elif tag == "pressure":
                    unit = "bar"
                elif "level" in tag or "speed" in tag or "position" in tag:
                    unit = "%"
                elif tag == "motor_current":
                    unit = "A"

                with cols[index]:
                    display_value = value

                    if tag in ["pump_status", "conveyor_status", "fan_status"]:
                        display_value = "ON" if value == 1 else "OFF"

                    if tag in ["emergency_stop", "cooling_alarm"]:
                        display_value = "ACTIVE" if value == 1 else "OFF"

                    render_metric_card(
                        label=label,
                        value=display_value,
                        unit=unit,
                        subtext=f"Register {REGISTER_MAP[tag]} | Normal: {min_value}-{max_value}",
                        status=status_class
                    )


# ------------------------------------------------
# PAGE: RED TEAM
# ------------------------------------------------

elif page == "Red Team":
    render_header(
        "⛔ Red Team",
        "Запуск контрольованих атак. Виявлення та відновлення виконується тільки через Blue Team.",
        variant="red"
    )

    st.warning(
        "Red Team тільки запускає атаки. Для аналізу і відновлення перейдіть у вкладку Blue Team."
    )

    selected_system = st.selectbox(
        "Select target system",
        list(SYSTEMS.keys())
    )

    system_attacks = [
        attack for attack in ATTACKS
        if attack["system"] == selected_system
    ]

    cols = st.columns(3)

    for index, attack in enumerate(system_attacks):
        with cols[index]:
            render_attack_card(attack)

            if st.button(f"Run: {attack['name']}", key=f"run_{attack['event']}"):
                ok, message = execute_attack(attack)

                if ok:
                    st.error(message)
                else:
                    st.error(message)

    st.divider()

    st.subheader("Custom Simple Attack")

    st.markdown(
        """
        <div class="info-box">
        Тут користувач може створити просту власну атаку:
        вибрати параметр PLC, значення і тривалість запису.
        Це працює тільки в навчальному середовищі ICSCyberRange.
        </div>
        """,
        unsafe_allow_html=True
    )

    custom_col1, custom_col2, custom_col3 = st.columns(3)

    with custom_col1:
        custom_tag = st.selectbox(
            "Target parameter",
            list(REGISTER_MAP.keys())
        )

    with custom_col2:
        custom_value = st.number_input(
            "Value to write",
            min_value=0,
            max_value=999,
            value=0,
            step=1
        )

    with custom_col3:
        custom_duration = st.slider(
            "Duration, seconds",
            min_value=0,
            max_value=20,
            value=0
        )

    custom_description = st.text_input(
        "Custom attack description",
        value=f"Custom attack on {custom_tag}"
    )

    if st.button("Run Custom Attack"):
        custom_attack = {
            "system": SYSTEM_BY_TAG[custom_tag],
            "name": "Custom Simple Attack",
            "level": "Custom",
            "event": "CUSTOM_ATTACK",
            "description": custom_description,
            "writes": [(custom_tag, int(custom_value))],
            "duration": int(custom_duration),
        }

        ok, message = execute_attack(custom_attack)

        if ok:
            st.error(message)
        else:
            st.error(message)


# ------------------------------------------------
# PAGE: BLUE TEAM
# ------------------------------------------------

elif page == "Blue Team":
    render_header(
        "⬢ Blue Team",
        "Виявлення аномалій, відновлення системи та формування PDF-звіту після інциденту.",
        variant="blue"
    )

    if error:
        st.error(error)
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Anomaly Detection")

            st.markdown(
                """
                <div class="info-box">
                Blue Team перевіряє всі параметри PLC і показує, що вийшло за нормальні межі.
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("Run Full Anomaly Detection"):
                current_state, _, current_error = read_plc_state()

                if current_error:
                    st.error(current_error)
                else:
                    alerts = detect_anomalies(current_state)
                    st.session_state["last_alerts"] = alerts

                    if alerts:
                        log_event(
                            event_type="ANOMALY_DETECTION",
                            description="Виявлено аномалії: " + "; ".join([a["message"] for a in alerts]),
                            state=current_state
                        )

                        st.error("Anomalies detected:")

                        for alert in alerts:
                            st.write(f"- {alert['message']}")
                    else:
                        log_event(
                            event_type="ANOMALY_DETECTION",
                            description="Аномалій не виявлено",
                            state=current_state
                        )

                        st.success("System status: normal")

        with col2:
            st.subheader("Manual Recovery")

            st.markdown(
                """
                <div class="info-box">
                Recovery повертає параметри вибраної системи до безпечного нормального стану.
                </div>
                """,
                unsafe_allow_html=True
            )

            recovery_target = st.selectbox(
                "Select recovery target",
                ["Full System", "Pump Station", "Conveyor Line", "Cooling System"]
            )

            if st.button("Run Recovery"):
                ok, message = recover_by_system(recovery_target)
                current_state, _, _ = read_plc_state()

                if ok:
                    log_event(
                        event_type="RECOVERY_EXECUTED",
                        description=f"Виконано recovery: {recovery_target}",
                        state=current_state
                    )
                    st.success(message)
                else:
                    st.error(message)

        st.divider()

        st.subheader("Recommended Fixes")

        last_alerts = st.session_state.get("last_alerts", [])

        if last_alerts:
            affected_systems = sorted(set(alert["system"] for alert in last_alerts))

            for system_name in affected_systems:
                st.markdown(
                    f"""
                    <div class="info-box">
                    <b>{system_name}</b><br>
                    У цій підсистемі виявлено проблему. Рекомендована дія: recovery для {system_name}.
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if st.button(f"Recover {system_name}", key=f"recover_recommended_{system_name}"):
                    ok, message = recover_by_system(system_name)
                    current_state, _, _ = read_plc_state()

                    if ok:
                        log_event(
                            event_type="RECOMMENDED_RECOVERY",
                            description=f"Виконано рекомендоване recovery для {system_name}",
                            state=current_state
                        )
                        st.success(message)
                    else:
                        st.error(message)
        else:
            st.info("Спочатку запусти Anomaly Detection.")

        st.divider()

        st.subheader("Custom Simple Defense Rule")

        st.markdown(
            """
            <div class="info-box">
            Тут користувач може створити просте правило захисту:
            вибрати параметр, мінімальне і максимальне нормальне значення.
            </div>
            """,
            unsafe_allow_html=True
        )

        defense_col1, defense_col2, defense_col3 = st.columns(3)

        with defense_col1:
            defense_tag = st.selectbox(
                "Parameter to check",
                list(REGISTER_MAP.keys()),
                key="custom_defense_tag"
            )

        with defense_col2:
            defense_min = st.number_input(
                "Min normal value",
                min_value=0,
                max_value=999,
                value=0,
                step=1
            )

        with defense_col3:
            defense_max = st.number_input(
                "Max normal value",
                min_value=0,
                max_value=999,
                value=100,
                step=1
            )

        if st.button("Run Custom Defense Check"):
            current_state, _, current_error = read_plc_state()

            if current_error:
                st.error(current_error)
            else:
                current_value = current_state[defense_tag]

                if current_value < defense_min or current_value > defense_max:
                    st.error(
                        f"Custom rule alert: {defense_tag} = {current_value}, "
                        f"норма: {defense_min} - {defense_max}"
                    )

                    log_event(
                        event_type="CUSTOM_DEFENSE_ALERT",
                        description=(
                            f"Custom rule alert: {defense_tag} = {current_value}, "
                            f"норма: {defense_min} - {defense_max}"
                        ),
                        state=current_state
                    )
                else:
                    st.success(
                        f"Custom rule passed: {defense_tag} = {current_value}"
                    )

        st.divider()

        st.subheader("Incident Report")

        report_col1, report_col2 = st.columns(2)

        with report_col1:
            if st.button("Generate PDF Incident Report"):
                ok, result = generate_pdf_report_safe()

                if ok:
                    st.session_state["last_pdf_report"] = result
                    st.success("PDF-звіт успішно створено.")
                else:
                    st.error(result)

        with report_col2:
            try:
                pdf_path = Path(
                    st.session_state.get(
                        "last_pdf_report",
                        "reports/simulation_report.pdf"
                    )
                )

                if pdf_path.exists():
                    st.download_button(
                        label="Download PDF Report",
                        data=pdf_path.read_bytes(),
                        file_name="simulation_report.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.info("Спочатку створи PDF-звіт.")

            except Exception as pdf_error:
                st.warning("Не вдалося підготувати PDF до завантаження.")
                st.code(str(pdf_error))

        st.divider()

        st.subheader("Recent Security Events")

        try:
            logs = read_logs(limit=10)

            if logs:
                for event in reversed(logs):
                    timestamp = escape(event.get("timestamp", ""))
                    event_type = escape(event.get("event_type", ""))
                    description = escape(event.get("description", ""))

                    st.markdown(
                        f"""
                        <div class="log-box">
                            <b>{event_type}</b><br>
                            <span style="color:#94a3b8;">{timestamp}</span><br><br>
                            {description}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.info("Журнал подій поки порожній.")

        except Exception as log_error:
            st.warning("Не вдалося завантажити журнал подій.")
            st.code(str(log_error))

        st.divider()

        st.subheader("Normal Operating Ranges")

        markdown_rows = [
            "| Parameter | Register | Normal Min | Normal Max |",
            "|---|---:|---:|---:|",
        ]

        for tag, value_range in NORMAL_RANGES.items():
            markdown_rows.append(
                f"| `{tag}` | `{REGISTER_MAP[tag]}` | `{value_range[0]}` | `{value_range[1]}` |"
            )

        st.markdown("\n".join(markdown_rows))


# ------------------------------------------------
# PAGE: TRAINING
# ------------------------------------------------

elif page == "Training":
    render_header(
        "✦ Training Mode",
        "Перевірка знань користувача по всіх трьох промислових підсистемах.",
        variant="purple"
    )

    st.markdown(
        """
        <div class="info-box">
        У цьому режимі система випадково обирає питання по Pump Station,
        Conveyor Line або Cooling System. Користувач відповідає, а платформа
        пояснює правильну відповідь.
        </div>
        """,
        unsafe_allow_html=True
    )

    if "training_question" not in st.session_state:
        st.session_state["training_question"] = random.choice(TRAINING_QUESTIONS)

    question = st.session_state["training_question"]

    st.subheader(f"System: {question['system']}")
    st.write(question["question"])

    selected_answer = st.radio(
        "Choose answer",
        question["options"],
        key="training_answer"
    )

    quiz_col1, quiz_col2 = st.columns(2)

    with quiz_col1:
        if st.button("Check Answer"):
            if selected_answer == question["answer"]:
                st.success("Правильно")
                log_event(
                    event_type="TRAINING_CORRECT_ANSWER",
                    description=f"Правильна відповідь у Training Mode: {question['question']}",
                    state=state
                )
            else:
                st.error("Неправильно")
                log_event(
                    event_type="TRAINING_WRONG_ANSWER",
                    description=f"Неправильна відповідь у Training Mode: {question['question']}",
                    state=state
                )

            st.info(question["explanation"])

    with quiz_col2:
        if st.button("Next Random Question"):
            st.session_state["training_question"] = random.choice(TRAINING_QUESTIONS)
            st.rerun()

    st.divider()

    st.subheader("Short Guide")

    st.write(
        """
        - Red Team запускає атаку.
        - Blue Team знаходить проблему.
        - Recovery повертає систему в норму.
        - PDF Report зберігає результати симуляції.
        """
    )


# ------------------------------------------------
# PAGE: HOW IT WORKS
# ------------------------------------------------

elif page == "How It Works":
    render_header(
        "◇ How ICSCyberRange Works",
        "Пояснення простими словами: що відбувається всередині системи."
    )

    st.markdown(
        """
        <div class="info-box">
        <b>1. PLC Simulator</b><br>
        Це віртуальний контролер. Він зберігає 12 значень у Modbus-регістрах.
        </div>

        <div class="info-box">
        <b>2. Streamlit</b><br>
        Це головний веб-інтерфейс. Тут користувач запускає атаки, перевіряє стан систем і виконує recovery.
        </div>

        <div class="info-box">
        <b>3. Red Team</b><br>
        Це модуль атак. Він змінює Modbus-регістри так, ніби систему атакує зловмисник.
        </div>

        <div class="info-box">
        <b>4. Blue Team</b><br>
        Це модуль захисту. Він перевіряє параметри, знаходить аномалії, відновлює систему і формує PDF-звіт.
        </div>

        <div class="info-box">
        <b>5. InfluxDB</b><br>
        Це база телеметрії. Collector записує туди значення PLC кожні 2 секунди.
        </div>

        <div class="info-box">
        <b>6. Grafana</b><br>
        Це система графіків. Вона показує, як змінюються параметри після атак і recovery.
        </div>
        """,
        unsafe_allow_html=True
    )