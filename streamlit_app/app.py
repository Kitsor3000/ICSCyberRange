import os
import sys
import time
import json
import threading
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
        "mitre_id": "T0855",
        "mitre_name": "Unauthorized Command Message",
    },
    {
        "system": "Pump Station",
        "name": "Pump False Data Injection",
        "level": "Medium",
        "event": "PUMP_FALSE_DATA_INJECTION",
        "description": "Підміна температури та тиску насосної станції.",
        "writes": [("temperature", 999), ("pressure", 0)],
        "duration": 10,
        "mitre_id": "T0836",
        "mitre_name": "Modify Parameter",
    },
    {
        "system": "Pump Station",
        "name": "Water Level Spoofing",
        "level": "Medium",
        "event": "WATER_LEVEL_SPOOFING",
        "description": "Підміна рівня води в резервуарі.",
        "writes": [("water_level", 0)],
        "duration": 10,
        "mitre_id": "T0836",
        "mitre_name": "Modify Parameter",
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
        "mitre_id": "T0855",
        "mitre_name": "Unauthorized Command Message",
    },
    {
        "system": "Conveyor Line",
        "name": "Motor Speed Overdrive",
        "level": "Medium",
        "event": "MOTOR_SPEED_OVERDRIVE",
        "description": "Встановлення небезпечної швидкості двигуна.",
        "writes": [("motor_speed", 120)],
        "duration": 0,
        "mitre_id": "T0836",
        "mitre_name": "Modify Parameter",
    },
    {
        "system": "Conveyor Line",
        "name": "Emergency Stop Abuse",
        "level": "Hard",
        "event": "EMERGENCY_STOP_ABUSE",
        "description": "Активація аварійної зупинки конвеєра.",
        "writes": [("emergency_stop", 1)],
        "duration": 0,
        "mitre_id": "T0855",
        "mitre_name": "Unauthorized Command Message",
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
        "mitre_id": "T0855",
        "mitre_name": "Unauthorized Command Message",
    },
    {
        "system": "Cooling System",
        "name": "Valve Manipulation Attack",
        "level": "Medium",
        "event": "VALVE_MANIPULATION_ATTACK",
        "description": "Закриття клапана охолодження.",
        "writes": [("valve_position", 0)],
        "duration": 0,
        "mitre_id": "T0836",
        "mitre_name": "Modify Parameter",
    },
    {
        "system": "Cooling System",
        "name": "Cooling Temperature Spoofing",
        "level": "Hard",
        "event": "COOLING_TEMP_SPOOFING",
        "description": "Підміна температури охолоджуючої рідини.",
        "writes": [("coolant_temperature", 80)],
        "duration": 10,
        "mitre_id": "T0836",
        "mitre_name": "Modify Parameter",
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

if "theme" not in st.session_state:
    st.session_state.theme = "dark"


# ------------------------------------------------
# DESIGN
# ------------------------------------------------

_DARK_CSS = """
/* ═══════════════ DARK THEME ════════════════
   App bg   #0d1117   Card bg  #161b22
   Text     #e6edf3   Muted    #8d96a0
   Border   #30363d   Accent   #58a6ff
   Code bg  #1c2128   Code txt #79c0ff
   ════════════════════════════════════════ */
.stApp {
    background: linear-gradient(160deg, #0d1117 0%, #161b22 100%);
    color: #e6edf3;
}
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1400px; }
h1, h2, h3 { color: #e6edf3 !important; letter-spacing: -0.03em; }
h4, h5, h6 { color: #cdd9e5 !important; }
p, span, label, div { color: #e6edf3; }
a { color: #58a6ff !important; } a:hover { color: #79c0ff !important; }

/* code & pre — critical for readability */
code { color: #79c0ff !important; background: #1c2128 !important; border-radius: 6px; padding: 2px 7px; border: 1px solid #30363d; font-size: 0.88em; }
pre { background: #1c2128 !important; border: 1px solid #30363d !important; border-radius: 10px; padding: 16px !important; }
pre code { background: transparent !important; border: none !important; }
pre * { color: #cdd9e5 !important; }

/* sidebar */
section[data-testid="stSidebar"] { background: #0d1117 !important; border-right: 1px solid #30363d !important; }
section[data-testid="stSidebar"] * { color: #e6edf3 !important; }
section[data-testid="stSidebar"] hr { border-color: #30363d !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #8d96a0 !important; }

/* custom cards */
.main-header { padding: 24px 28px; border-radius: 16px; background: linear-gradient(135deg, rgba(56,189,248,0.12), rgba(99,102,241,0.08)), #161b22; border: 1px solid rgba(56,189,248,0.22); margin-bottom: 22px; box-shadow: 0 8px 32px rgba(0,0,0,0.40); }
.main-header h1 { margin-bottom: 8px; font-size: 36px; font-weight: 850; color: #e6edf3 !important; }
.main-header p { color: #8d96a0 !important; font-size: 16px; margin: 0; max-width: 980px; }
.red-header { background: linear-gradient(135deg, rgba(220,38,38,0.20), rgba(127,29,29,0.12)), #161b22; border: 1px solid rgba(248,113,113,0.30) !important; }
.blue-header { background: linear-gradient(135deg, rgba(37,99,235,0.20), rgba(30,64,175,0.12)), #161b22; border: 1px solid rgba(96,165,250,0.30) !important; }
.purple-header { background: linear-gradient(135deg, rgba(124,58,237,0.20), rgba(88,28,135,0.12)), #161b22; border: 1px solid rgba(167,139,250,0.30) !important; }

.system-card, .metric-card, .attack-card, .info-box, .log-box { padding: 18px; border-radius: 14px; background: #161b22; border: 1px solid #30363d; box-shadow: 0 4px 16px rgba(0,0,0,0.35); margin-bottom: 16px; transition: transform 0.18s, border-color 0.18s, box-shadow 0.18s; }
.system-card:hover, .metric-card:hover, .attack-card:hover, .info-box:hover { transform: translateY(-2px); border-color: #58a6ff; box-shadow: 0 8px 28px rgba(0,0,0,0.50); }

/* log-box: monospace dark bg, light text */
.log-box { background: #1c2128 !important; font-family: 'Consolas','Courier New',monospace !important; }
.log-box p, .log-box span, .log-box div, .log-box pre { color: #cdd9e5 !important; background: transparent !important; }
.log-box code { color: #79c0ff !important; background: rgba(255,255,255,0.06) !important; }

.metric-label { color: #8d96a0 !important; font-size: 12px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.06em; }
.metric-value { color: #e6edf3 !important; font-size: 30px; font-weight: 850; line-height: 1.15; word-break: break-word; }
.metric-sub { color: #8d96a0 !important; font-size: 12px; margin-top: 8px; }

.normal { border-left: 5px solid #3fb950; }
.warning { border-left: 5px solid #d29922; }
.danger { border-left: 5px solid #f85149; }
.pump { border-left: 5px solid #79c0ff; }
.conveyor { border-left: 5px solid #ffa657; }
.cooling { border-left: 5px solid #bc8cff; }

.status-card { padding: 20px; border-radius: 14px; background: #161b22; border: 1px solid #30363d; box-shadow: 0 4px 16px rgba(0,0,0,0.35); margin-bottom: 18px; }
.status-title { font-size: 12px; color: #8d96a0 !important; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.06em; }
.status-value { font-size: 28px; font-weight: 850; color: #e6edf3 !important; }
.attack-level { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; background: #1c2128; border: 1px solid #30363d; color: #8d96a0 !important; margin-bottom: 10px; }

div.stButton > button { width: 100%; border-radius: 10px; min-height: 44px; font-weight: 700; border: 1px solid #30363d; background: #21262d; color: #e6edf3; transition: all 0.15s; }
div.stButton > button:hover { border-color: #58a6ff; background: rgba(88,166,255,0.12); color: #79c0ff; transform: translateY(-1px); box-shadow: 0 4px 14px rgba(0,0,0,0.35); }
div.stDownloadButton > button { width: 100%; border-radius: 10px; min-height: 44px; font-weight: 700; }

/* alerts */
div.stInfo { background: rgba(56,139,253,0.10) !important; border-left: 4px solid #388bfd !important; border-radius: 8px; }
div.stInfo * { color: #79c0ff !important; }
div.stWarning { background: rgba(187,128,9,0.12) !important; border-left: 4px solid #d29922 !important; border-radius: 8px; }
div.stWarning * { color: #e3b341 !important; }
div.stError { background: rgba(248,81,73,0.10) !important; border-left: 4px solid #f85149 !important; border-radius: 8px; }
div.stError * { color: #ff7b72 !important; }
div.stSuccess { background: rgba(63,185,80,0.10) !important; border-left: 4px solid #3fb950 !important; border-radius: 8px; }
div.stSuccess * { color: #56d364 !important; }

/* caption / hr */
[data-testid="stCaptionContainer"] p { color: #8d96a0 !important; }
hr { border-color: #30363d !important; }
[data-testid="stMetricLabel"] * { color: #8d96a0 !important; }
[data-testid="stMetricValue"] * { color: #e6edf3 !important; }

.mobile-nav-label { display: none; }
@media (max-width: 768px) {
    .mobile-nav-label { display: block; margin-bottom: -10px; color: #8d96a0; font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em; }
    .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: 1rem; }
    .main-header { padding: 18px 16px; border-radius: 14px; }
    .main-header h1 { font-size: 24px; line-height: 1.18; }
    .main-header p { font-size: 14px; line-height: 1.5; }
    .metric-card, .system-card, .attack-card, .info-box, .log-box { padding: 14px; border-radius: 12px; }
    .metric-value { font-size: 25px; }
    .status-value { font-size: 23px; }
    div.stButton > button { min-height: 48px; font-size: 15px; }
}
"""

_LIGHT_CSS = """
/* ═══════════════════════════════════════════
   LIGHT THEME  —  Palette:
   bg        #f0f5ff → #f8fafc
   cards     #ffffff
   sidebar   #eef2ff → #f1f5f9
   text-1    #0f172a   text-2  #475569   muted  #94a3b8
   border    #e2e8f0   accent  #3b82f6
   ═══════════════════════════════════════════ */

/* ── App root ─────────────────────────────── */
.stApp { background: linear-gradient(135deg, #f0f5ff 0%, #f8fafc 50%, #f0f9ff 100%); color: #0f172a; }
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1400px; }

/* ── Top toolbar / header bar ─────────────── */
[data-testid="stHeader"], header[data-testid="stHeader"] {
    background: rgba(240, 245, 255, 0.97) !important;
    border-bottom: 1px solid #e2e8f0 !important;
    backdrop-filter: blur(8px);
}
[data-testid="stHeader"] * { color: #475569 !important; fill: #475569 !important; }
[data-testid="stHeader"] button { background: transparent !important; border: none !important; }
[data-testid="stHeader"] button:hover { background: #e2e8f0 !important; }
[data-testid="stToolbar"] { background: rgba(240, 245, 255, 0.97) !important; }

/* ── Headings & text ──────────────────────── */
h1, h2, h3 { color: #0f172a !important; letter-spacing: -0.03em; }
h4, h5, h6 { color: #1e293b !important; }
p { color: #334155 !important; }
span { color: #334155; }
label { color: #475569 !important; }
a { color: #3b82f6 !important; }
a:hover { color: #2563eb !important; }

/* ── Code ─────────────────────────────────── */
code { color: #1d4ed8 !important; background: rgba(219, 234, 254, 0.80) !important; border-radius: 6px; padding: 2px 6px; }
pre { background: #f1f5f9 !important; border: 1px solid #e2e8f0; border-radius: 8px; }
pre * { color: #1e293b !important; }

/* ── Sidebar ──────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #eef2ff 0%, #f1f5f9 100%) !important;
    border-right: 1px solid #e2e8f0 !important;
}
section[data-testid="stSidebar"] * { color: #1e293b !important; }
section[data-testid="stSidebar"] hr { border-color: #cbd5e1 !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #64748b !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * { color: #334155 !important; }

/* ── Sidebar navigation radio ─────────────── */
[data-testid="stSidebar"] .stRadio > label { color: #475569 !important; }
[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p { color: #1e293b !important; }
[data-testid="stSidebar"] .stRadio label div p { color: #1e293b !important; }

/* ── Markdown containers ──────────────────── */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 { color: #1e293b !important; }
[data-testid="stCaptionContainer"] p { color: #64748b !important; }

/* ── Input / Textarea ─────────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #ffffff !important; color: #0f172a !important;
    border: 1px solid #cbd5e1 !important; border-radius: 8px;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12) !important;
}
[data-baseweb="input"] { background: #ffffff !important; }
[data-baseweb="input"] input { color: #0f172a !important; background: #ffffff !important; }

/* ── Selectbox ────────────────────────────── */
.stSelectbox > div > div,
[data-testid="stSelectbox"] > div > div { background: #ffffff !important; color: #0f172a !important; border: 1px solid #cbd5e1 !important; border-radius: 8px; }
[data-testid="stSelectbox"] * { color: #0f172a !important; }
[data-baseweb="select"] { background: #ffffff !important; }
[data-baseweb="select"] * { color: #0f172a !important; background: #ffffff !important; }
[data-baseweb="select"] > div { background: #ffffff !important; border-color: #cbd5e1 !important; }

/* Dropdown popover list */
[data-baseweb="popover"] { background: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 10px; box-shadow: 0 8px 24px rgba(15,23,42,0.10) !important; }
[data-baseweb="popover"] * { color: #0f172a !important; background: #ffffff !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="menu"] li:hover { background: #eff6ff !important; }
[data-baseweb="menu"] { background: #ffffff !important; }
[data-baseweb="menu"] * { color: #0f172a !important; }

/* ── Radio buttons ────────────────────────── */
.stRadio > label { color: #475569 !important; }
.stRadio [data-testid="stMarkdownContainer"] p { color: #334155 !important; }
.stRadio label { color: #334155 !important; }

/* ── Checkbox ─────────────────────────────── */
.stCheckbox label { color: #334155 !important; }

/* ── Native Streamlit alerts ──────────────── */
[data-testid="stNotification"],
[data-baseweb="notification"] { border-radius: 10px !important; }

div[data-testid="stAlert"] { border-radius: 10px !important; }

/* info */
div.stInfo, [data-testid="stAlertContainer"].st-info,
[data-baseweb="notification"].st-info { background: #eff6ff !important; border-left: 4px solid #3b82f6 !important; }
div.stInfo *, [data-baseweb="notification"].st-info * { color: #1e40af !important; }

/* warning */
div.stWarning, [data-testid="stAlertContainer"].st-warning { background: #fffbeb !important; border-left: 4px solid #f59e0b !important; }
div.stWarning * { color: #92400e !important; }

/* error */
div.stError, [data-testid="stAlertContainer"].st-error { background: #fef2f2 !important; border-left: 4px solid #ef4444 !important; }
div.stError * { color: #991b1b !important; }

/* success */
div.stSuccess, [data-testid="stAlertContainer"].st-success { background: #f0fdf4 !important; border-left: 4px solid #22c55e !important; }
div.stSuccess * { color: #166534 !important; }

/* sidebar alerts */
[data-testid="stSidebar"] div.stSuccess { background: #f0fdf4 !important; }
[data-testid="stSidebar"] div.stSuccess * { color: #166534 !important; }
[data-testid="stSidebar"] div.stError { background: #fef2f2 !important; }
[data-testid="stSidebar"] div.stError * { color: #991b1b !important; }

/* ── Dividers ─────────────────────────────── */
hr { border-color: #e2e8f0 !important; }

/* ── Expander ─────────────────────────────── */
[data-testid="stExpander"] { background: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 12px !important; }
.streamlit-expanderHeader { background: #f8fafc !important; border-radius: 12px; }
.streamlit-expanderHeader *, [data-testid="stExpander"] * { color: #1e293b !important; }
[data-testid="stExpanderToggleIcon"] { color: #64748b !important; fill: #64748b !important; }

/* ── Metrics (native st.metric) ───────────── */
[data-testid="stMetric"] { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; }
[data-testid="stMetricLabel"] * { color: #64748b !important; }
[data-testid="stMetricValue"] * { color: #0f172a !important; }
[data-testid="stMetricDelta"] * { color: #16a34a !important; }

/* ── Dataframe / table ────────────────────── */
[data-testid="stDataFrame"] { background: #ffffff !important; border-radius: 10px; border: 1px solid #e2e8f0; }
[data-testid="stDataFrame"] * { color: #0f172a !important; background: #ffffff !important; }

/* ── Tabs ─────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { background: #f1f5f9; border-radius: 10px; padding: 4px; }
.stTabs [data-baseweb="tab"] { color: #64748b !important; border-radius: 8px; }
.stTabs [aria-selected="true"] { background: #ffffff !important; color: #0f172a !important; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }

/* ── Spinner ──────────────────────────────── */
[data-testid="stSpinner"] * { color: #3b82f6 !important; }

/* ── Tooltip ──────────────────────────────── */
[data-baseweb="tooltip"] { background: #1e293b !important; color: #f8fafc !important; border-radius: 6px; }
[data-baseweb="tooltip"] * { color: #f8fafc !important; }

/* ══ Custom card components ═══════════════════════════════════════════ */
.main-header { padding: 24px 28px; border-radius: 22px; background: linear-gradient(135deg, rgba(59, 130, 246, 0.09), rgba(14, 165, 233, 0.04)), #ffffff; border: 1px solid rgba(59, 130, 246, 0.20); margin-bottom: 22px; box-shadow: 0 4px 20px rgba(59, 130, 246, 0.07); }
.main-header h1 { margin-bottom: 8px; font-size: 36px; font-weight: 850; color: #0f172a !important; }
.main-header p { color: #475569 !important; font-size: 16px; margin: 0; max-width: 980px; }

.red-header { background: linear-gradient(135deg, rgba(220, 38, 38, 0.09), rgba(127, 29, 29, 0.04)), #ffffff; border: 1px solid rgba(220, 38, 38, 0.22) !important; }
.blue-header { background: linear-gradient(135deg, rgba(37, 99, 235, 0.09), rgba(30, 64, 175, 0.04)), #ffffff; border: 1px solid rgba(37, 99, 235, 0.22) !important; }
.purple-header { background: linear-gradient(135deg, rgba(124, 58, 237, 0.09), rgba(88, 28, 135, 0.04)), #ffffff; border: 1px solid rgba(124, 58, 237, 0.22) !important; }

.system-card, .metric-card, .attack-card, .info-box, .log-box { padding: 18px; border-radius: 18px; background: #ffffff; border: 1px solid #e8edf4; box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05); margin-bottom: 16px; transition: transform 0.18s ease, border 0.18s ease, box-shadow 0.18s ease; }
.system-card:hover, .metric-card:hover, .attack-card:hover, .info-box:hover { transform: translateY(-3px); border: 1px solid rgba(59, 130, 246, 0.40); box-shadow: 0 8px 24px rgba(59, 130, 246, 0.10); }

.metric-label { color: #64748b; font-size: 12px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.06em; }
.metric-value { color: #0f172a; font-size: 30px; font-weight: 850; line-height: 1.15; word-break: break-word; }
.metric-sub { color: #94a3b8; font-size: 12px; margin-top: 8px; }

.normal { border-left: 5px solid #22c55e; }
.warning { border-left: 5px solid #f59e0b; }
.danger { border-left: 5px solid #ef4444; }
.pump { border-left: 5px solid #0ea5e9; }
.conveyor { border-left: 5px solid #f97316; }
.cooling { border-left: 5px solid #8b5cf6; }

.status-card { padding: 20px; border-radius: 18px; background: #ffffff; border: 1px solid #e8edf4; box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05); margin-bottom: 18px; }
.status-title { font-size: 12px; color: #64748b; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.06em; }
.status-value { font-size: 28px; font-weight: 850; color: #0f172a; }

.attack-level { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; background: #f1f5f9; border: 1px solid #cbd5e1; color: #475569; margin-bottom: 10px; }

div.stButton > button { width: 100%; border-radius: 12px; min-height: 46px; font-weight: 750; border: 1px solid #cbd5e1; background: #ffffff; color: #1e293b; transition: all 0.15s ease; }
div.stButton > button:hover { border: 1px solid #3b82f6; background: #eff6ff; color: #1d4ed8; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(59, 130, 246, 0.14); }
div.stDownloadButton > button { width: 100%; border-radius: 12px; min-height: 46px; font-weight: 750; background: #ffffff !important; color: #1e293b !important; border: 1px solid #d0d7de !important; transition: all 0.15s ease; }
div.stDownloadButton > button:hover { background: #f3f4f6 !important; border-color: #0969da !important; color: #0969da !important; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(9,105,218,0.14); }

.mobile-nav-label { display: none; }
@media (max-width: 768px) {
    .mobile-nav-label { display: block; margin-bottom: -10px; color: #64748b; font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em; }
    .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: 1rem; }
    .main-header { padding: 18px 16px; border-radius: 16px; }
    .main-header h1 { font-size: 24px; line-height: 1.18; }
    .main-header p { font-size: 14px; line-height: 1.5; }
    .metric-card, .system-card, .attack-card, .info-box, .log-box { padding: 15px; border-radius: 15px; }
    .metric-value { font-size: 25px; }
    .status-value { font-size: 23px; }
    div.stButton > button { min-height: 50px; font-size: 15px; }
}

/* ── Log box (light theme: white bg, dark text) ── */
.log-box { background: #f6f8fa !important; font-family: 'Consolas','Courier New',monospace !important; border: 1px solid #d0d7de !important; }
.log-box p, .log-box span, .log-box div, .log-box pre { color: #1f2328 !important; background: transparent !important; }
.log-box code { color: #0550ae !important; background: rgba(175,184,193,0.20) !important; }

/* ── Force light bg on all app containers (overrides base=dark) ── */
[data-testid="stApp"], [data-testid="stAppViewContainer"],
section.main, .main, [data-testid="stMain"],
.stMainBlockContainer, [data-testid="stMainBlockContainer"] { background: #f6f8fa !important; }
[data-testid="stHeader"], header[data-testid="stHeader"],
[data-testid="stToolbar"] { background: #f6f8fa !important; }
[data-testid="stToolbarActions"] svg, [data-testid="stToolbarActions"] button { color: #1f2328 !important; fill: #1f2328 !important; }
[data-testid="stToolbarActions"] button:hover { background: #eaeef2 !important; }
[data-testid="stDecoration"] { background: linear-gradient(90deg, #0969da, #0ea5e9) !important; }

/* ── Native dark input/select overrides ── */
[data-baseweb="base-input"] { background: #ffffff !important; }
[data-baseweb="base-input"] input,
[data-baseweb="base-input"] textarea { color: #1f2328 !important; background: #ffffff !important; }
div[data-baseweb="input"] { background: #ffffff !important; border-color: #d0d7de !important; }
div[data-baseweb="input"] input { color: #1f2328 !important; }
[data-baseweb="tag"] { background: #dde3ec !important; }
[data-baseweb="tag"] * { color: #1f2328 !important; }
[data-testid="stWidgetLabel"] label,
[data-testid="stWidgetLabel"] p { color: #1f2328 !important; }
[data-testid="stNumberInputField"] { background: #ffffff !important; color: #1f2328 !important; }
.stNumberInput button { background: #f3f4f6 !important; color: #1f2328 !important; border-color: #d0d7de !important; }
"""


def apply_custom_styles():
    theme = st.session_state.get("theme", "dark")
    css = _DARK_CSS if theme == "dark" else _LIGHT_CSS
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


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

    mitre_id = attack.get("mitre_id", "")
    mitre_name = attack.get("mitre_name", "")
    mitre_block = (
        f'<p style="font-size:11px;color:#94a3b8;margin-top:8px;">'
        f'MITRE ATT&amp;CK ICS: <b>{escape(mitre_id)}</b> — {escape(mitre_name)}</p>'
        if mitre_id else ""
    )

    st.markdown(
        f"""
        <div class="attack-card danger">
            <span class="attack-level">{escape(attack['level'])}</span>
            <h3>{escape(attack['name'])}</h3>
            <p>{escape(attack['description'])}</p>
            <p>{writes_text}</p>
            <p style="font-size:11px;color:#94a3b8;">Persistent — runs until Blue Team stops it</p>
            {mitre_block}
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


# ------------------------------------------------
# PERSISTENT ATTACKS ENGINE
# ------------------------------------------------

ACTIVE_ATTACKS_FILE = "data/active_attacks.json"
_thread_lock = threading.Lock()
_thread_started: list = []


def load_active_attacks() -> dict:
    try:
        with open(ACTIVE_ATTACKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_active_attacks(attacks: dict) -> None:
    try:
        os.makedirs("data", exist_ok=True)
        with open(ACTIVE_ATTACKS_FILE, "w", encoding="utf-8") as f:
            json.dump(attacks, f)
    except OSError:
        pass


def arm_attack(event_name: str, writes: list) -> None:
    attacks = load_active_attacks()
    attacks[event_name] = {"writes": [[tag, value] for tag, value in writes]}
    save_active_attacks(attacks)


def disarm_attack(event_name: str) -> None:
    attacks = load_active_attacks()
    attacks.pop(event_name, None)
    save_active_attacks(attacks)


def disarm_system_attacks(system_tags: list) -> None:
    attacks = load_active_attacks()
    updated = {
        name: data
        for name, data in attacks.items()
        if not any(w[0] in system_tags for w in data.get("writes", []))
    }
    save_active_attacks(updated)


def disarm_tag_attacks(tag: str) -> None:
    attacks = load_active_attacks()
    updated = {
        name: data
        for name, data in attacks.items()
        if not any(w[0] == tag for w in data.get("writes", []))
    }
    save_active_attacks(updated)


def _persistent_attack_loop() -> None:
    while True:
        try:
            attacks = load_active_attacks()
            if attacks:
                client, _ = get_client()
                if client:
                    for attack_data in attacks.values():
                        for write_pair in attack_data.get("writes", []):
                            tag, value = write_pair[0], write_pair[1]
                            address = REGISTER_MAP.get(tag)
                            if address is not None:
                                client.write_register(address, int(value), unit=1)
                    client.close()
        except Exception:
            pass
        time.sleep(1)


def _ensure_attack_thread() -> None:
    with _thread_lock:
        if not _thread_started:
            t = threading.Thread(target=_persistent_attack_loop, daemon=True)
            t.start()
            _thread_started.append(True)


_ensure_attack_thread()


def execute_attack(attack: dict):
    for tag, value in attack["writes"]:
        ok, message = write_register(tag, value)
        if not ok:
            return False, message

    arm_attack(attack["event"], attack["writes"])

    current_state, _, _ = read_plc_state()
    log_event(
        event_type=attack["event"],
        description=f"Запущено атаку: {attack['name']}",
        state=current_state
    )
    return True, f"Attack launched: {attack['name']}"


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
    disarm_system_attacks(["temperature", "pressure", "water_level", "pump_status"])
    for tag in ["temperature", "pressure", "water_level", "pump_status"]:
        ok, message = write_register(tag, NORMAL_STATE[tag])

        if not ok:
            return False, message

    return True, "Pump Station recovered"


def recover_conveyor_line():
    disarm_system_attacks(["conveyor_status", "motor_speed", "motor_current", "emergency_stop"])
    for tag in ["conveyor_status", "motor_speed", "motor_current", "emergency_stop"]:
        ok, message = write_register(tag, NORMAL_STATE[tag])

        if not ok:
            return False, message

    return True, "Conveyor Line recovered"


def recover_cooling_system():
    disarm_system_attacks(["fan_status", "coolant_temperature", "valve_position", "cooling_alarm"])
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



def read_code_template(path):
    """
    Зчитує Python-шаблон з папки labs/templates.
    Якщо файл не знайдено — повертає повідомлення.
    """

    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return f"File not found: {path}"
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
    "Code Lab",
    "Scenarios",
    "Statistics",
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

theme_label = "☀ Світла тема" if st.session_state.theme == "dark" else "🌙 Темна тема"
if st.sidebar.button(theme_label, key="theme_toggle"):
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
    st.rerun()

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
        "Red Team тільки запускає атаки. Вони тривають постійно до відновлення через Blue Team."
    )

    # ── Active attacks banner ─────────────────────────────────────────
    active_attacks = load_active_attacks()

    if active_attacks:
        names_html = "".join(
            f'<span style="display:inline-block;background:rgba(239,68,68,0.18);'
            f'border:1px solid rgba(248,113,113,0.40);border-radius:8px;'
            f'padding:2px 10px;margin:2px 4px 2px 0;font-size:12px;color:#fca5a5;">'
            f'{escape(n)}</span>'
            for n in active_attacks
        )
        st.markdown(
            f"""
            <div class="info-box" style="border-left:5px solid #ef4444;">
                <b style="color:#fca5a5;">⚠ {len(active_attacks)} ACTIVE ATTACK(S)</b>
                &nbsp;—&nbsp; Ці атаки зараз активні та тривають безперервно:<br>
                <div style="margin-top:8px;">{names_html}</div>
                <div style="margin-top:8px;font-size:12px;color:#94a3b8;">
                Для зупинки: натисни «Stop» нижче або виконай Recovery у вкладці Blue Team.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.success("Немає активних атак. Всі системи в нормальному стані.")

    st.divider()

    # ── Prebuilt attacks ──────────────────────────────────────────────
    selected_system = st.selectbox("Select target system", list(SYSTEMS.keys()))

    system_attacks = [a for a in ATTACKS if a["system"] == selected_system]

    cols = st.columns(3)

    for index, attack in enumerate(system_attacks):
        is_active = attack["event"] in active_attacks

        with cols[index]:
            render_attack_card(attack)

            if is_active:
                st.markdown(
                    '<div style="color:#f87171;font-size:12px;font-weight:700;'
                    'margin-bottom:6px;">▶ АТАКА АКТИВНА</div>',
                    unsafe_allow_html=True
                )
                if st.button(f"Stop: {attack['name']}", key=f"stop_{attack['event']}"):
                    disarm_attack(attack["event"])
                    for tag, _ in attack["writes"]:
                        write_register(tag, NORMAL_STATE[tag])
                    current_state, _, _ = read_plc_state()
                    log_event(
                        event_type="ATTACK_STOPPED",
                        description=f"Атаку зупинено через Red Team: {attack['name']}",
                        state=current_state
                    )
                    st.success(f"Атаку зупинено: {attack['name']}")
                    st.rerun()
            else:
                if st.button(f"Launch: {attack['name']}", key=f"run_{attack['event']}"):
                    ok, message = execute_attack(attack)
                    if ok:
                        st.warning(f"⚠️ {message}")
                        st.rerun()
                    else:
                        st.error(f"Failed: {message}")

    st.divider()

    # ── Custom Attack ─────────────────────────────────────────────────
    st.subheader("Custom Attack Builder")

    ATTACK_TYPE_TEMPLATES = {
        "Parameter Override": {
            "mitre_id": "T0836",
            "mitre_name": "Modify Parameter",
            "description": "Встановлює керуючий параметр на небезпечне значення (швидкість, позиція клапана).",
            "value_hint": "Введи значення ВИЩЕ норми (перевантаження) або 0 (блокування).",
            "suggested_value": lambda tag: NORMAL_RANGES[tag][1] + 20 if NORMAL_RANGES[tag][1] > 0 else 0,
        },
        "Sensor Data Spoofing": {
            "mitre_id": "T0836",
            "mitre_name": "Modify Parameter",
            "description": "Підміняє показники сенсора на хибні критичні значення, щоб ввести SCADA в оману.",
            "value_hint": "Введи критичне хибне значення (наприклад, 999 для температури, 0 для тиску).",
            "suggested_value": lambda tag: 999 if "temperature" in tag else 0,
        },
        "Device Shutdown": {
            "mitre_id": "T0855",
            "mitre_name": "Unauthorized Command Message",
            "description": "Вимикає обладнання несанкціонованим записом 0 у командний register.",
            "value_hint": "Запиши 0 щоб вимкнути (1 = ON, 0 = OFF). Стосується status-параметрів.",
            "suggested_value": lambda _: 0,
        },
        "Emergency Command Injection": {
            "mitre_id": "T0855",
            "mitre_name": "Unauthorized Command Message",
            "description": "Активує аварійний стан PLC через несанкціонований запис командного register.",
            "value_hint": "Запиши 1 для активації аварії (0 = normal, 1 = ACTIVE).",
            "suggested_value": lambda _: 1,
        },
    }

    ca_col1, ca_col2 = st.columns([1, 2])

    with ca_col1:
        ca_type = st.selectbox("Attack type", list(ATTACK_TYPE_TEMPLATES.keys()), key="ca_type")
        ca_system = st.selectbox("Target system", list(SYSTEMS.keys()), key="ca_system")

        ca_tags = SYSTEMS[ca_system]["tags"]
        ca_tag = st.selectbox("Target parameter", ca_tags, key="ca_tag")

        ca_tpl = ATTACK_TYPE_TEMPLATES[ca_type]
        ca_norm_min, ca_norm_max = NORMAL_RANGES[ca_tag]
        ca_suggested = ca_tpl["suggested_value"](ca_tag)

        st.caption(
            f"Register R{REGISTER_MAP[ca_tag]}  ·  "
            f"Normal range: {ca_norm_min} – {ca_norm_max}"
        )
        st.caption(f"💡 {ca_tpl['value_hint']}")

        ca_value = st.number_input(
            "Value to write",
            min_value=0,
            max_value=999,
            value=int(ca_suggested),
            step=1,
            key="ca_value"
        )

    with ca_col2:
        st.markdown(
            f"""
            <div class="attack-card danger" style="height:100%;box-sizing:border-box;">
                <span class="attack-level">Custom · {escape(ca_type)}</span>
                <h3>Custom: {escape(ca_tag)} → {ca_value}</h3>
                <p>{escape(ca_tpl['description'])}</p>
                <p>R{REGISTER_MAP[ca_tag]}: <b>{escape(ca_tag)}</b> → <b>{ca_value}</b></p>
                <p style="font-size:11px;color:#94a3b8;margin-top:8px;">
                    MITRE ATT&amp;CK ICS: <b>{escape(ca_tpl['mitre_id'])}</b>
                    — {escape(ca_tpl['mitre_name'])}
                </p>
                <p style="font-size:11px;color:#94a3b8;">
                    System: <b>{escape(ca_system)}</b> · Persistent until stopped
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    custom_event = f"CUSTOM_ATTACK_{ca_tag.upper()}"
    ca_is_active = custom_event in active_attacks

    btn_c1, btn_c2 = st.columns(2)
    with btn_c1:
        if ca_is_active:
            st.markdown(
                '<div style="color:#f87171;font-size:12px;font-weight:700;margin-bottom:6px;">'
                '▶ КАСТОМНА АТАКА АКТИВНА</div>',
                unsafe_allow_html=True
            )
            if st.button("Stop Custom Attack", key="stop_custom"):
                disarm_attack(custom_event)
                write_register(ca_tag, NORMAL_STATE[ca_tag])
                current_state, _, _ = read_plc_state()
                log_event("ATTACK_STOPPED", f"Кастомну атаку зупинено: {ca_tag}", current_state)
                st.success(f"Атаку зупинено: {ca_tag}")
                st.rerun()
        else:
            if st.button("Launch Custom Attack", key="launch_custom"):
                custom_attack = {
                    "system": ca_system,
                    "name": f"Custom: {ca_tag} → {ca_value}",
                    "level": "Custom",
                    "event": custom_event,
                    "description": ca_tpl["description"],
                    "writes": [(ca_tag, int(ca_value))],
                    "mitre_id": ca_tpl["mitre_id"],
                    "mitre_name": ca_tpl["mitre_name"],
                }
                ok, message = execute_attack(custom_attack)
                if ok:
                    st.warning(f"⚠️ {message}")
                    st.rerun()
                else:
                    st.error(f"Failed: {message}")


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

        # ── Active attacks status ─────────────────────────────────────
        bt_active = load_active_attacks()
        if bt_active:
            st.markdown(
                f'<div class="info-box" style="border-left:5px solid #ef4444;">'
                f'<b style="color:#fca5a5;">⚠ {len(bt_active)} активних атак зараз:</b><br>'
                + "".join(
                    f'<span style="display:inline-block;background:rgba(239,68,68,0.15);'
                    f'border:1px solid rgba(248,113,113,0.35);border-radius:6px;'
                    f'padding:1px 8px;margin:2px 4px 2px 0;font-size:12px;color:#fca5a5;">'
                    f'{escape(n)}</span>'
                    for n in bt_active
                )
                + "</div>",
                unsafe_allow_html=True
            )

        st.divider()

        # ── Custom Parameter Recovery ─────────────────────────────────
        st.subheader("Custom Parameter Recovery")

        st.markdown(
            """
            <div class="info-box">
            Точкове відновлення: вибери конкретний параметр PLC,
            встанови безпечне значення і запиши його в register.
            Автоматично зупиняє будь-яку активну атаку на цей параметр.
            </div>
            """,
            unsafe_allow_html=True
        )

        cr_col1, cr_col2 = st.columns([1, 2])

        with cr_col1:
            cr_system = st.selectbox(
                "Subsystem",
                list(SYSTEMS.keys()),
                key="cr_system"
            )
            cr_tags = SYSTEMS[cr_system]["tags"]
            cr_tag = st.selectbox(
                "Parameter to recover",
                cr_tags,
                key="cr_tag"
            )

            cr_norm_min, cr_norm_max = NORMAL_RANGES[cr_tag]
            cr_normal_val = NORMAL_STATE[cr_tag]
            cr_reg = REGISTER_MAP[cr_tag]

            st.caption(
                f"Register R{cr_reg}  ·  Normal range: {cr_norm_min} – {cr_norm_max}  ·  "
                f"Default: {cr_normal_val}"
            )

            cr_value = st.number_input(
                "Recovery value",
                min_value=0,
                max_value=999,
                value=int(cr_normal_val),
                step=1,
                key="cr_value"
            )

        with cr_col2:
            cr_current_state, _, _ = read_plc_state()
            cr_current_val = cr_current_state[cr_tag] if cr_current_state else "N/A"
            cr_in_normal = (
                cr_norm_min <= cr_current_val <= cr_norm_max
                if isinstance(cr_current_val, int) else False
            )
            cr_status_color = "#22c55e" if cr_in_normal else "#ef4444"
            cr_status_label = "NORMAL" if cr_in_normal else "OUT OF RANGE"

            cr_tag_attacked = any(
                cr_tag in [w[0] for w in d.get("writes", [])]
                for d in bt_active.values()
            )

            st.markdown(
                f"""
                <div class="system-card" style="border-left:5px solid {cr_status_color};">
                    <div style="font-size:11px;color:#94a3b8;text-transform:uppercase;
                                letter-spacing:.06em;margin-bottom:8px;">
                        {escape(cr_system)} · R{cr_reg} · {escape(cr_tag)}
                    </div>
                    <div style="font-size:28px;font-weight:900;color:{cr_status_color};">
                        {cr_current_val}
                    </div>
                    <div style="font-size:12px;color:{cr_status_color};margin-top:4px;">
                        {cr_status_label} &nbsp;·&nbsp; нормa: {cr_norm_min} – {cr_norm_max}
                    </div>
                    {'<div style="font-size:12px;color:#fca5a5;margin-top:8px;">⚠ Параметр під атакою</div>'
                     if cr_tag_attacked else ''}
                    <div style="font-size:12px;color:#94a3b8;margin-top:8px;">
                        Відновити до: <b style="color:#f8fafc;">{cr_value}</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        if st.button("Apply Custom Recovery", key="apply_cr"):
            disarm_tag_attacks(cr_tag)
            ok, message = write_register(cr_tag, cr_value)
            cr_state_after, _, _ = read_plc_state()

            if ok:
                log_event(
                    event_type="CUSTOM_RECOVERY",
                    description=(
                        f"Custom recovery: {cr_tag} → {cr_value} "
                        f"(попереднє: {cr_current_val})"
                    ),
                    state=cr_state_after
                )
                st.success(f"Відновлено: {cr_tag} = {cr_value}")
            else:
                st.error(message)

        st.divider()

        st.subheader("Custom Anomaly Detection Rule")

        st.markdown(
            """
            <div class="info-box">
            Тут користувач може створити власне правило захисту:
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

        known_min, known_max = NORMAL_RANGES[defense_tag]

        with defense_col2:
            defense_min = st.number_input(
                f"Min normal value (known: {known_min})",
                min_value=0,
                max_value=999,
                value=known_min,
                step=1
            )

        with defense_col3:
            defense_max = st.number_input(
                f"Max normal value (known: {known_max})",
                min_value=0,
                max_value=999,
                value=known_max,
                step=1
            )

        if defense_min > defense_max:
            st.warning(
                f"Min ({defense_min}) більший за Max ({defense_max}) — правило некоректне. "
                f"Встанови Min < Max."
            )
        elif st.button("Run Custom Anomaly Check"):
            current_state, _, current_error = read_plc_state()

            if current_error:
                st.error(current_error)
            else:
                current_value = current_state[defense_tag]

                if current_value < defense_min or current_value > defense_max:
                    st.error(
                        f"ALERT: {defense_tag} = {current_value} "
                        f"(норма: {defense_min} – {defense_max})"
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
                        f"OK: {defense_tag} = {current_value} "
                        f"(в нормі: {defense_min} – {defense_max})"
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
# PAGE: CODE LAB
# ------------------------------------------------

elif page == "Code Lab":
    render_header(
        "⌘ Code Lab",
        "Практичний режим: як атаки, захист і recovery працюють під капотом."
    )

    st.markdown(
        """
        <div class="info-box">
        Code Lab створений для того, щоб користувач не просто натискав кнопки,
        а розумів, як працюють атаки через Modbus TCP, як Blue Team виявляє
        аномалії та як recovery повертає систему в нормальний стан.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader("1. Modbus Register Map")

    register_rows = [
        "| Register | Parameter | System | Normal value/range |",
        "|---:|---|---|---|",
        "| 0 | `temperature` | Pump Station | 18–45 °C |",
        "| 1 | `pressure` | Pump Station | 2–10 bar |",
        "| 2 | `water_level` | Pump Station | 20–100 % |",
        "| 3 | `pump_status` | Pump Station | 1 = ON |",
        "| 4 | `conveyor_status` | Conveyor Line | 1 = ON |",
        "| 5 | `motor_speed` | Conveyor Line | 40–100 % |",
        "| 6 | `motor_current` | Conveyor Line | 5–25 A |",
        "| 7 | `emergency_stop` | Conveyor Line | 0 = OFF |",
        "| 8 | `fan_status` | Cooling System | 1 = ON |",
        "| 9 | `coolant_temperature` | Cooling System | 18–40 °C |",
        "| 10 | `valve_position` | Cooling System | 30–100 % |",
        "| 11 | `cooling_alarm` | Cooling System | 0 = OFF |",
    ]

    st.markdown("\n".join(register_rows))

    st.divider()

    st.subheader("2. Як працює атака")

    st.markdown(
        """
        <div class="info-box">
        У цьому проєкті атака — це запис небезпечного значення у Modbus-регістр.
        Наприклад, якщо записати <code>0</code> у register <code>3</code>,
        то <code>pump_status</code> стане OFF, і насос вимкнеться.
        </div>
        """,
        unsafe_allow_html=True
    )

    attack_example = """
from pymodbus.client.sync import ModbusTcpClient

client = ModbusTcpClient("127.0.0.1", port=5020)
client.connect()

# Register 3 = pump_status
# 1 = ON, 0 = OFF
client.write_register(3, 0, unit=1)

client.close()
"""

    st.code(attack_example, language="python")

    st.markdown(
        """
        <div class="info-box">
        Простими словами: код підключається до PLC Simulator,
        знаходить потрібний register і записує туди нове значення.
        PLC Simulator сприймає це як команду керування.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.subheader("3. Приклад атаки на Conveyor Line")

    conveyor_attack_example = """
from pymodbus.client.sync import ModbusTcpClient

client = ModbusTcpClient("127.0.0.1", port=5020)
client.connect()

# Register 5 = motor_speed
# Normal value: 40-100
# Attack value: 120
client.write_register(5, 120, unit=1)

client.close()
"""

    st.code(conveyor_attack_example, language="python")

    st.markdown(
        """
        <div class="info-box">
        Цей приклад змінює швидкість двигуна конвеєра на 120%.
        Для системи це небезпечне значення, тому Blue Team має виявити аномалію.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.subheader("4. Як працює захист")

    defense_example = """
def detect_anomalies(state):
    alerts = []

    for tag, value in state.items():
        min_value, max_value = NORMAL_RANGES[tag]

        if value < min_value or value > max_value:
            alerts.append(
                f"{tag} = {value}, normal: {min_value}-{max_value}"
            )

    return alerts
"""

    st.code(defense_example, language="python")

    st.markdown(
        """
        <div class="info-box">
        Blue Team працює за простим принципом:
        зчитує поточний стан PLC і порівнює кожне значення з нормальним діапазоном.
        Якщо значення вийшло за межі — це аномалія.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.subheader("5. Як працює recovery")

    recovery_example = """
from pymodbus.client.sync import ModbusTcpClient

client = ModbusTcpClient("127.0.0.1", port=5020)
client.connect()

client.write_register(4, 1, unit=1)   # conveyor_status = ON
client.write_register(5, 70, unit=1)  # motor_speed = 70
client.write_register(6, 12, unit=1)  # motor_current = 12
client.write_register(7, 0, unit=1)   # emergency_stop = OFF

client.close()
"""

    st.code(recovery_example, language="python")

    st.markdown(
        """
        <div class="info-box">
        Recovery не є магією. Це звичайний запис нормальних безпечних значень
        назад у Modbus-регістри.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.subheader("6. Готові шаблони для практики")

    template_choice = st.selectbox(
        "Choose code template",
        [
            "custom_attack_template.py",
            "custom_defense_template.py",
            "recovery_template.py",
        ]
    )

    template_path = f"labs/templates/{template_choice}"
    template_code = read_code_template(template_path)

    st.code(template_code, language="python")

    st.markdown(
        """
        <div class="info-box">
        Щоб використати шаблон:
        <br>1. Відкрий файл у папці <code>labs/templates</code>.
        <br>2. Зміни register, value або rule.
        <br>3. Запусти файл через термінал.
        <br>4. Перевір результат у Streamlit, Blue Team і Grafana.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.subheader("7. Практичне завдання")

    st.markdown(
        """
        <div class="info-box">
        <b>Завдання 1 — власна атака:</b><br>
        1. Відкрий <code>labs/templates/custom_attack_template.py</code>.<br>
        2. Зміни <code>REGISTER = 5</code> і <code>VALUE = 120</code>.<br>
        3. Запусти файл командою <code>python labs/templates/custom_attack_template.py</code>.<br>
        4. У Blue Team натисни <b>Run Full Anomaly Detection</b>.<br>
        5. Перевір, що система знайшла аномалію <code>motor_speed</code>.<br>
        6. Запусти recovery через інтерфейс або файл <code>recovery_template.py</code>.<br>
        7. Перевір зміни в Grafana.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="info-box">
        <b>Завдання 2 — власне правило захисту:</b><br>
        1. Відкрий <code>labs/templates/custom_defense_template.py</code>.<br>
        2. Зміни функцію <code>detect_custom_rule()</code>.<br>
        3. Додай перевірку іншого параметра, наприклад <code>coolant_temperature</code>.<br>
        4. Якщо температура більша за 40 — виведи ALERT.<br>
        5. Запусти файл і перевір результат.
        </div>
        """,
        unsafe_allow_html=True
    )

# ------------------------------------------------
# PAGE: SCENARIOS
# ------------------------------------------------

elif page == "Scenarios":
    _t = st.session_state.get("theme", "dark")
    _dark = _t == "dark"
    # ── palette variables ───────────────────────────────────────────────
    _card_bg      = "rgba(15,23,42,0.92)"    if _dark else "#ffffff"
    _card_bdr     = "rgba(148,163,184,0.18)" if _dark else "#d0d7de"
    _hover_bdr    = "rgba(96,165,250,0.5)"   if _dark else "rgba(9,105,218,0.45)"
    _sdone_bg     = "rgba(34,197,94,0.08)"   if _dark else "rgba(26,127,55,0.07)"
    _sact_bg      = "rgba(234,179,8,0.10)"   if _dark else "rgba(154,103,0,0.08)"
    _sact_bdr     = "rgba(234,179,8,0.40)"   if _dark else "rgba(154,103,0,0.30)"
    _spnd_bg      = "rgba(15,23,42,0.60)"    if _dark else "rgba(246,248,250,0.85)"
    _spnd_bdr     = "rgba(148,163,184,0.12)" if _dark else "#e8ecf0"
    _quiz_bg      = "rgba(15,23,42,0.92)"    if _dark else "#ffffff"
    _quiz_q       = "#f1f5f9"                if _dark else "#1f2328"
    _score_bg     = "rgba(15,23,42,0.95)"    if _dark else "#ffffff"
    _score_lbl    = "#94a3b8"                if _dark else "#57606a"
    _bs_bg        = "rgba(37,99,235,0.25)"   if _dark else "rgba(9,105,218,0.10)"
    _bs_col       = "#93c5fd"                if _dark else "#0969da"
    _bs_bdr       = "rgba(96,165,250,0.35)"  if _dark else "rgba(9,105,218,0.30)"
    _bm_bg        = "rgba(147,51,234,0.25)"  if _dark else "rgba(130,80,223,0.10)"
    _bm_col       = "#c4b5fd"                if _dark else "#8250df"
    _bm_bdr       = "rgba(192,132,252,0.35)" if _dark else "rgba(130,80,223,0.30)"
    _mitre_bg     = "rgba(220,38,38,0.15)"   if _dark else "rgba(207,34,46,0.08)"
    _mitre_col    = "#fca5a5"                if _dark else "#cf222e"
    _mitre_bdr    = "rgba(248,113,113,0.30)" if _dark else "rgba(207,34,46,0.25)"
    # inline text
    _muted        = "#94a3b8"  if _dark else "#6e7781"
    _desc_text    = "#cbd5e1"  if _dark else "#57606a"
    _bold_text    = "#f8fafc"  if _dark else "#1f2328"
    _done_col     = "#86efac"  if _dark else "#1a7f37"
    _act_col      = "#fde68a"  if _dark else "#9a6700"
    _pnd_col      = "#94a3b8"  if _dark else "#9198a1"
    _step_desc    = "#cbd5e1"  if _dark else "#57606a"
    _hint_col     = "#64748b"  if _dark else "#6e7781"

    st.markdown(f"""
        <style>
        .lvl-card {{
            padding: 18px 14px; border-radius: 16px;
            background: {_card_bg}; border: 1px solid {_card_bdr};
            text-align: center; cursor: pointer;
            transition: all 0.18s ease; margin-bottom: 4px;
        }}
        .lvl-card:hover {{ border-color: {_hover_bdr}; transform: translateY(-2px); }}
        .lvl-beginner     {{ border-left: 5px solid #22c55e; }}
        .lvl-intermediate {{ border-left: 5px solid #eab308; }}
        .lvl-advanced     {{ border-left: 5px solid #ef4444; }}

        .step-done {{
            padding: 12px 16px; border-radius: 12px; margin-bottom: 8px;
            background: {_sdone_bg}; border: 1px solid rgba(34,197,94,0.25);
            border-left: 4px solid #22c55e;
        }}
        .step-active {{
            padding: 14px 18px; border-radius: 14px; margin-bottom: 8px;
            background: {_sact_bg}; border: 1px solid {_sact_bdr};
            border-left: 5px solid #eab308; box-shadow: 0 4px 16px rgba(0,0,0,0.10);
        }}
        .step-pending {{
            padding: 12px 16px; border-radius: 12px; margin-bottom: 8px;
            background: {_spnd_bg}; border: 1px solid {_spnd_bdr};
            border-left: 4px solid rgba(100,116,139,0.35); opacity: 0.60;
        }}

        .quiz-card {{
            padding: 20px; border-radius: 16px; margin-bottom: 14px;
            background: {_quiz_bg}; border: 1px solid {_card_bdr};
            box-shadow: 0 4px 14px rgba(0,0,0,0.08);
        }}
        .quiz-badge-single {{
            display: inline-block; padding: 3px 10px; border-radius: 999px;
            font-size: 11px; font-weight: 700; letter-spacing: 0.06em;
            background: {_bs_bg}; color: {_bs_col};
            border: 1px solid {_bs_bdr}; margin-bottom: 10px;
        }}
        .quiz-badge-multi {{
            display: inline-block; padding: 3px 10px; border-radius: 999px;
            font-size: 11px; font-weight: 700; letter-spacing: 0.06em;
            background: {_bm_bg}; color: {_bm_col};
            border: 1px solid {_bm_bdr}; margin-bottom: 10px;
        }}
        .quiz-question {{ font-size: 15px; font-weight: 600; color: {_quiz_q}; margin-bottom: 12px; }}

        .score-block {{
            padding: 22px; border-radius: 18px; text-align: center;
            background: {_score_bg}; border: 1px solid {_card_bdr};
            box-shadow: 0 8px 24px rgba(0,0,0,0.10); margin-top: 8px;
        }}
        .score-number {{ font-size: 52px; font-weight: 900; line-height: 1; }}
        .score-label  {{ font-size: 14px; color: {_score_lbl}; margin-top: 6px; }}

        .mitre-badge {{
            display: inline-block; padding: 5px 14px; border-radius: 999px;
            font-size: 12px; font-weight: 600;
            background: {_mitre_bg}; color: {_mitre_col};
            border: 1px solid {_mitre_bdr};
        }}
        </style>
    """, unsafe_allow_html=True)

    render_header(
        "◈ Training Scenarios",
        "Покрокові навчальні сценарії з тестами: Beginner, Intermediate, Advanced.",
        variant="purple"
    )

    SCENARIO_FILES = {
        "Beginner":     "scenarios/beginner.json",
        "Intermediate": "scenarios/intermediate.json",
        "Advanced":     "scenarios/advanced.json",
    }
    LEVEL_COLORS = {
        "Beginner":     ("#22c55e", "lvl-beginner",     "Easy",   "5 питань"),
        "Intermediate": ("#eab308", "lvl-intermediate",  "Medium", "5 питань"),
        "Advanced":     ("#ef4444", "lvl-advanced",      "Hard",   "5 питань"),
    }

    # ── Level selector ────────────────────────────────────────────────
    lc1, lc2, lc3 = st.columns(3)
    for col, (lvl, (color, css, diff, q_count)) in zip(
        [lc1, lc2, lc3], LEVEL_COLORS.items()
    ):
        with col:
            st.markdown(
                f"""
                <div class="lvl-card {css}">
                    <div style="font-size:22px;font-weight:900;color:{color};">{lvl}</div>
                    <div style="font-size:12px;color:#94a3b8;margin-top:4px;">
                        {diff} · {q_count}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    scenario_level = st.radio(
        "Рівень сценарію",
        list(SCENARIO_FILES.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="scenario_level_radio"
    )

    if st.session_state.get("_prev_scenario_level") != scenario_level:
        st.session_state["scenario_step"] = 0
        st.session_state[f"quiz_submitted_{scenario_level}"] = False
        st.session_state["_prev_scenario_level"] = scenario_level

    scenario_path = SCENARIO_FILES[scenario_level]

    try:
        with open(scenario_path, "r", encoding="utf-8") as f:
            scenario = json.load(f)

        color, _, diff, _ = LEVEL_COLORS[scenario_level]
        mitre = scenario.get("mitre_technique", {})

        # ── Scenario info ─────────────────────────────────────────────
        st.markdown(
            f"""
            <div class="system-card" style="border-left:5px solid {color};margin-top:6px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
                    <div>
                        <div style="font-size:11px;color:{_muted};text-transform:uppercase;
                                    letter-spacing:.06em;margin-bottom:6px;">{escape(diff)} level</div>
                        <h3 style="margin:0 0 8px;">{escape(scenario.get('title',''))}</h3>
                        <p style="margin:0 0 8px;color:{_desc_text};">{escape(scenario.get('description',''))}</p>
                        <p style="margin:0;"><b>Мета:</b> {escape(scenario.get('goal',''))}</p>
                    </div>
                    {
                        f'<span class="mitre-badge">MITRE {escape(mitre.get("id",""))}<br>'
                        f'<span style="font-weight:400;">{escape(mitre.get("name",""))}</span></span>'
                        if mitre else ""
                    }
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # ── Steps ─────────────────────────────────────────────────────
        steps = scenario.get("steps", [])
        total_steps = len(steps)
        current_step = st.session_state.get("scenario_step", 0)

        st.markdown(
            f"<div style='margin:18px 0 6px;font-size:13px;color:{_muted};'>"
            f"PROGRESS &nbsp; <b style='color:{_bold_text};'>{min(current_step, total_steps)}/{total_steps}</b>"
            f" steps completed</div>",
            unsafe_allow_html=True
        )
        st.progress(
            min(current_step, total_steps) / max(total_steps, 1),
        )

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        for i, step in enumerate(steps):
            if i < current_step:
                css_cls, icon, title_color = "step-done",    "✓", _done_col
            elif i == current_step:
                css_cls, icon, title_color = "step-active",  "▶", _act_col
            else:
                css_cls, icon, title_color = "step-pending", "○", _pnd_col

            st.markdown(
                f"""
                <div class="{css_cls}">
                    <div style="font-size:13px;color:{title_color};font-weight:700;margin-bottom:5px;">
                        {icon} &nbsp; Step {step['step']}: {escape(step['title'])}
                    </div>
                    <div style="font-size:13px;color:{_step_desc};line-height:1.55;">
                        {escape(step['description'])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        nav1, nav2, nav3, nav4 = st.columns([1, 1, 1, 2])
        with nav1:
            if st.button("← Back", disabled=current_step == 0):
                st.session_state["scenario_step"] = current_step - 1
                st.rerun()
        with nav2:
            if st.button("Next →", disabled=current_step >= total_steps):
                st.session_state["scenario_step"] = current_step + 1
                st.rerun()
        with nav3:
            if st.button("Reset"):
                st.session_state["scenario_step"] = 0
                st.session_state[f"quiz_submitted_{scenario_level}"] = False
                st.rerun()

        if current_step >= total_steps:
            st.success("Всі кроки сценарію пройдено! Переходь до Knowledge Check.")

        # ── Quiz ──────────────────────────────────────────────────────
        st.divider()
        st.markdown(
            f"<h3 style='margin-bottom:4px;'>Knowledge Check</h3>"
            f"<p style='color:{_muted};font-size:13px;margin-top:0;'>"
            "Перевір своє розуміння сценарію. Деякі питання мають кілька правильних відповідей.</p>",
            unsafe_allow_html=True
        )

        quizzes = scenario.get("quizzes", [])
        quiz_submitted_key = f"quiz_submitted_{scenario_level}"

        if not quizzes:
            st.info("Для цього сценарію тести ще не додані.")
        else:
            user_answers = {}

            for qi, quiz in enumerate(quizzes):
                qid = quiz.get("id", str(qi))
                qtype = quiz.get("type", "single")
                badge_cls = "quiz-badge-multi" if qtype == "multi" else "quiz-badge-single"
                badge_txt = "MULTI-SELECT" if qtype == "multi" else "SINGLE"
                hint = " (обери всі правильні)" if qtype == "multi" else " (одна правильна відповідь)"

                st.markdown(
                    f"""
                    <div class="quiz-card">
                        <span class="{badge_cls}">{badge_txt}</span>
                        <div class="quiz-question">
                            Q{qi + 1}. {escape(quiz['text'])}<span style="color:{_hint_col};font-weight:400;font-size:13px;">{hint}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                opts = quiz.get("options", [])
                widget_key = f"quiz_{scenario_level}_{qid}"

                if qtype == "multi":
                    chosen = st.multiselect(
                        f"Відповідь на Q{qi+1}",
                        opts,
                        key=widget_key,
                        label_visibility="collapsed"
                    )
                    user_answers[qid] = [opts.index(c) for c in chosen if c in opts]
                else:
                    chosen = st.radio(
                        f"Відповідь на Q{qi+1}",
                        opts,
                        key=widget_key,
                        label_visibility="collapsed"
                    )
                    user_answers[qid] = (
                        [opts.index(chosen)] if chosen in opts else []
                    )

                if st.session_state.get(quiz_submitted_key):
                    correct = sorted(quiz.get("correct_answers", []))
                    given   = sorted(user_answers[qid])
                    if given == correct:
                        st.success("Правильно!")
                    else:
                        correct_labels = ", ".join(opts[i] for i in correct if i < len(opts))
                        st.error(f"Неправильно. Правильно: {correct_labels}")
                    st.info(quiz.get("explanation", ""))

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            btn_col1, btn_col2 = st.columns([1, 3])

            with btn_col1:
                if st.button("Перевірити відповіді", type="primary"):
                    st.session_state[quiz_submitted_key] = True
                    st.session_state[f"quiz_answers_{scenario_level}"] = user_answers
                    st.rerun()

            with btn_col2:
                if st.button("Скинути тести"):
                    st.session_state[quiz_submitted_key] = False
                    for quiz in quizzes:
                        qid = quiz.get("id", "")
                        key = f"quiz_{scenario_level}_{qid}"
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()

            if st.session_state.get(quiz_submitted_key):
                saved = st.session_state.get(f"quiz_answers_{scenario_level}", {})
                correct_count = sum(
                    1 for quiz in quizzes
                    if sorted(saved.get(quiz.get("id", ""), [])) == sorted(quiz.get("correct_answers", []))
                )
                total_q = len(quizzes)
                pct = int(correct_count / total_q * 100) if total_q else 0

                if pct == 100:
                    score_color, verdict = "#22c55e", "Відмінно!"
                elif pct >= 60:
                    score_color, verdict = "#eab308", "Добре!"
                else:
                    score_color, verdict = "#ef4444", "Потрібно повторити"

                st.markdown(
                    f"""
                    <div class="score-block">
                        <div class="score-number" style="color:{score_color};">{correct_count}/{total_q}</div>
                        <div class="score-label">{pct}% правильних відповідей &nbsp;·&nbsp; {verdict}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    except FileNotFoundError:
        st.warning(f"Файл сценарію не знайдено: {scenario_path}")
    except Exception as scenario_error:
        st.error(f"Помилка завантаження сценарію: {scenario_error}")


# ------------------------------------------------
# PAGE: STATISTICS
# ------------------------------------------------

elif page == "Statistics":
    render_header(
        "◈ Statistics & Analytics",
        "Аналіз журналу симуляції: атаки, виявлення аномалій, відновлення системи.",
        variant="blue"
    )

    from collections import Counter

    all_logs = read_logs(limit=1000)

    if not all_logs:
        st.info("Журнал порожній. Запусти симуляцію, атаки та recovery — статистика з'явиться тут.")
    else:
        ATTACK_KEYS = [
            "ATTACK", "INJECTION", "SPOOFING", "OVERDRIVE",
            "ABUSE", "SHUTDOWN", "MANIPULATION",
        ]

        attack_count = sum(
            1 for r in all_logs
            if any(k in r.get("event_type", "") for k in ATTACK_KEYS)
            or r.get("event_type") == "CUSTOM_ATTACK"
        )
        detection_count = sum(1 for r in all_logs if r.get("event_type") == "ANOMALY_DETECTION")
        recovery_count = sum(1 for r in all_logs if "RECOVERY" in r.get("event_type", ""))
        training_count = sum(1 for r in all_logs if "TRAINING" in r.get("event_type", ""))

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            render_metric_card("Total Events", len(all_logs), "", "All recorded")
        with c2:
            render_metric_card("Attacks", attack_count, "", "Red Team", status="danger")
        with c3:
            render_metric_card("Detections", detection_count, "", "Blue Team", status="warning")
        with c4:
            render_metric_card("Recoveries", recovery_count, "", "System restored", status="normal")
        with c5:
            render_metric_card("Training", training_count, "", "Quiz answers")

        st.divider()

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Events by Type")
            event_counts = Counter(r.get("event_type", "") for r in all_logs)
            for event_type, count in sorted(event_counts.items(), key=lambda x: -x[1]):
                bar_pct = count / len(all_logs)
                bar_w = max(1, int(bar_pct * 100))
                is_atk = any(k in event_type for k in ATTACK_KEYS)
                bar_color = "#ef4444" if is_atk else ("#22c55e" if "RECOVERY" in event_type else "#60a5fa")
                st.markdown(
                    f"""
                    <div style="margin-bottom:8px;">
                        <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">
                            <span style="color:#e5e7eb;"><code>{escape(event_type)}</code></span>
                            <b style="color:#f8fafc;">{count}</b>
                        </div>
                        <div style="background:rgba(30,41,59,0.8);border-radius:4px;height:8px;width:100%;">
                            <div style="background:{bar_color};border-radius:4px;height:8px;width:{bar_w}%;"></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        with col_right:
            st.subheader("Attack Coverage")
            attacked_systems = set()
            for r in all_logs:
                et = r.get("event_type", "")
                if "PUMP" in et:
                    attacked_systems.add("Pump Station")
                if "CONVEYOR" in et or "MOTOR" in et or "EMERGENCY" in et:
                    attacked_systems.add("Conveyor Line")
                if "FAN" in et or "VALVE" in et or "COOLING" in et:
                    attacked_systems.add("Cooling System")

            all_systems = ["Pump Station", "Conveyor Line", "Cooling System"]
            for sys_name in all_systems:
                was_attacked = sys_name in attacked_systems
                color = "#ef4444" if was_attacked else "#22c55e"
                label = "Under Attack" if was_attacked else "Not Attacked"
                st.markdown(
                    f"""
                    <div class="system-card" style="border-left:5px solid {color};margin-bottom:10px;">
                        <b style="color:#f8fafc;">{escape(sys_name)}</b><br>
                        <span style="color:{color};font-size:13px;">{label}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.divider()
        st.subheader("Event Log Table")

        try:
            import pandas as pd

            df = pd.DataFrame(all_logs)

            filter_options = ["All"] + sorted(set(r.get("event_type", "") for r in all_logs))
            filter_type = st.selectbox("Filter by event type", filter_options)

            if filter_type != "All":
                df = df[df["event_type"] == filter_type]

            display_cols = [c for c in ["timestamp", "event_type", "description"] if c in df.columns]

            if st.session_state.get("theme", "dark") == "light":
                headers = "".join(
                    f"<th style='padding:8px 14px;background:#f1f5f9;color:#57606a;"
                    f"font-size:12px;font-weight:700;text-transform:uppercase;"
                    f"letter-spacing:.05em;border-bottom:2px solid #d0d7de;"
                    f"text-align:left;white-space:nowrap;'>{col}</th>"
                    for col in display_cols
                )
                rows_html = ""
                for _, row in df[display_cols].iterrows():
                    cells = "".join(
                        f"<td style='padding:7px 14px;border-bottom:1px solid #e8ecf0;"
                        f"color:#1f2328;font-size:13px;'>{escape(str(row[col]))}</td>"
                        for col in display_cols
                    )
                    rows_html += f"<tr>{cells}</tr>"
                st.markdown(
                    f"<div style='overflow:auto;max-height:320px;border-radius:10px;"
                    f"border:1px solid #d0d7de;'>"
                    f"<table style='width:100%;border-collapse:collapse;background:#ffffff;'>"
                    f"<thead><tr>{headers}</tr></thead>"
                    f"<tbody>{rows_html}</tbody>"
                    f"</table></div>",
                    unsafe_allow_html=True
                )
            else:
                st.dataframe(df[display_cols], use_container_width=True, height=320)

        except ImportError:
            for row in reversed(all_logs[-20:]):
                timestamp = escape(row.get("timestamp", ""))
                event_type = escape(row.get("event_type", ""))
                description = escape(row.get("description", ""))
                st.markdown(
                    f"""
                    <div class="log-box">
                        <b>{event_type}</b><br>
                        <span style="color:#94a3b8;">{timestamp}</span><br>
                        {description}
                    </div>
                    """,
                    unsafe_allow_html=True
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

        <div class="info-box">
        <b>7. Code Lab</b><br>
        Це практичний режим, де користувач бачить код атак, захисту і recovery.
        Він може змінити шаблони, написати власну просту атаку або правило захисту,
        а потім перевірити результат у Streamlit, Blue Team і Grafana.
        </div>
        """,
        unsafe_allow_html=True
    )