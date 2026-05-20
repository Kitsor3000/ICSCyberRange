# ICSCyberRange

**Платформа для симуляції кібератак на промислові ICS/SCADA системи**

ICSCyberRange — навчальний кіберполігон, що імітує реальне промислове середовище на базі протоколу Modbus TCP. Платформа дозволяє практикувати виявлення атак, захист та відновлення трьох промислових підсистем у контрольованому середовищі.

---

## Архітектура системи

```
┌─────────────────────────────────────────────────────────────────┐
│                        ICSCyberRange                            │
│                                                                 │
│  ┌──────────────┐    Modbus TCP     ┌──────────────────────┐   │
│  │  Red Team    │ ─────────────── ▶ │   PLC Simulator      │   │
│  │  (Attacker)  │    port 5020      │   plc_server.py      │   │
│  └──────────────┘                   │   3 subsystems       │   │
│                                     └──────────┬───────────┘   │
│  ┌──────────────┐    Modbus TCP               │               │
│  │  Blue Team   │ ◀──────────────             │               │
│  │  (Defender)  │    read state    │           │ read           │
│  └──────────────┘                  ▼           ▼               │
│                              ┌─────────────────────────────┐   │
│  ┌──────────────┐    HTTP    │   Telemetry Collector       │   │
│  │   Streamlit  │ ─────────▶│   collector.py              │   │
│  │   Web UI     │            │   every 2 seconds           │   │
│  │   port 8501  │            └──────────────┬──────────────┘   │
│  └──────────────┘                           │ write             │
│                                             ▼                   │
│  ┌──────────────┐    Flux     ┌─────────────────────────────┐  │
│  │   Grafana    │ ◀────────── │       InfluxDB 2.7          │  │
│  │   port 3000  │             │       port 8086             │  │
│  └──────────────┘             └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Компоненти платформи

| Компонент | Технологія | Призначення |
|-----------|-----------|-------------|
| PLC Simulator | Python, pymodbus | Віртуальний Modbus TCP сервер, 12 регістрів, 3 підсистеми |
| Streamlit UI | Python, Streamlit | Веб-інтерфейс: атаки, захист, навчання, аналітика |
| Telemetry Collector | Python, influxdb-client | Збір телеметрії з PLC кожні 2 секунди |
| InfluxDB 2.7 | Docker | Time-series база даних для зберігання телеметрії |
| Grafana | Docker | Візуалізація графіків та моніторинг в реальному часі |
| Attacker Container | Docker, Python | Ізольоване середовище для запуску атак |

---

## Промислові підсистеми (Modbus Register Map)

| Register | Параметр | Підсистема | Норма |
|---------:|----------|-----------|-------|
| 0 | `temperature` | Pump Station | 18–45 °C |
| 1 | `pressure` | Pump Station | 2–10 bar |
| 2 | `water_level` | Pump Station | 20–100 % |
| 3 | `pump_status` | Pump Station | 1 = ON |
| 4 | `conveyor_status` | Conveyor Line | 1 = ON |
| 5 | `motor_speed` | Conveyor Line | 40–100 % |
| 6 | `motor_current` | Conveyor Line | 5–25 A |
| 7 | `emergency_stop` | Conveyor Line | 0 = OFF |
| 8 | `fan_status` | Cooling System | 1 = ON |
| 9 | `coolant_temperature` | Cooling System | 18–40 °C |
| 10 | `valve_position` | Cooling System | 30–100 % |
| 11 | `cooling_alarm` | Cooling System | 0 = OFF |

---

## Сценарії атак (MITRE ATT&CK for ICS)

| Атака | Підсистема | Рівень | MITRE Technique |
|-------|-----------|--------|-----------------|
| Pump OFF Attack | Pump Station | Easy | T0855 — Unauthorized Command Message |
| Pump False Data Injection | Pump Station | Medium | T0836 — Modify Parameter |
| Water Level Spoofing | Pump Station | Medium | T0836 — Modify Parameter |
| Conveyor Stop Attack | Conveyor Line | Easy | T0855 — Unauthorized Command Message |
| Motor Speed Overdrive | Conveyor Line | Medium | T0836 — Modify Parameter |
| Emergency Stop Abuse | Conveyor Line | Hard | T0855 — Unauthorized Command Message |
| Fan Shutdown Attack | Cooling System | Easy | T0855 — Unauthorized Command Message |
| Valve Manipulation Attack | Cooling System | Medium | T0836 — Modify Parameter |
| Cooling Temperature Spoofing | Cooling System | Hard | T0836 — Modify Parameter |

---

## Навчальні сценарії

| Рівень | Сценарій | Вектори атаки |
|--------|---------|---------------|
| **Beginner** | Modbus Command Injection | 1 (Pump OFF) |
| **Intermediate** | Multi-Stage Conveyor Attack | 2 (Motor Overdrive + Emergency Stop) |
| **Advanced** | Coordinated Multi-System APT | 3 (Pump + Cooling + Water Level) |

---

## Швидкий старт

### Вимоги
- Docker Desktop (Windows / Linux / macOS)
- Python 3.11+
- PowerShell або bash

### 1. Клонувати репозиторій

```bash
git clone <repo-url>
cd ICSCyberRange
```

### 2. Налаштувати середовище

Створи або відредагуй файл `.env`:

```env
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_token_here
INFLUXDB_ORG=ICS
INFLUXDB_BUCKET=plc_telemetry
```

### 3. Запустити Docker-сервіси

```bash
docker compose up -d
```

Це запускає: InfluxDB (8086), Grafana (3000), Streamlit (8501), Attacker container.

### 4. Запустити PLC Simulator (Windows)

```powershell
.\venv\Scripts\Activate.ps1
python simulator/plc_server.py
```

### 5. Запустити Telemetry Collector (окрема консоль)

```powershell
python telemetry/collector.py
```

### 6. Відкрити інтерфейси

| Сервіс | URL |
|--------|-----|
| Streamlit Web UI | http://localhost:8501 |
| Grafana Dashboard | http://localhost:3000 |
| InfluxDB | http://localhost:8086 |
| PLC Modbus | 127.0.0.1:5020 |

---

## Структура проекту

```
ICSCyberRange/
├── simulator/
│   └── plc_server.py          # Modbus TCP PLC Simulator (3 підсистеми)
├── streamlit_app/
│   └── app.py                 # Веб-інтерфейс (9 сторінок)
├── attacks/
│   ├── attack_scenarios.py    # CLI-скрипт атак (9 сценаріїв)
│   ├── false_data.py          # Модуль підміни даних
│   └── modbus_injection.py    # Modbus Command Injection
├── defense/
│   ├── anomaly_detector.py    # Детектор аномалій
│   └── recovery.py            # Відновлення системи
├── telemetry/
│   └── collector.py           # Збір даних → InfluxDB
├── scenarios/
│   ├── beginner.json          # Навчальний сценарій (рівень 1)
│   ├── intermediate.json      # Навчальний сценарій (рівень 2)
│   └── advanced.json          # Навчальний сценарій (рівень 3)
├── labs/
│   └── templates/
│       ├── custom_attack_template.py   # Шаблон для власної атаки
│       ├── custom_defense_template.py  # Шаблон для правила захисту
│       └── recovery_template.py        # Шаблон відновлення
├── reports/
│   └── pdf_report.py          # Генерація PDF Incident Report
├── grafana/
│   └── icscyberrange_dashboard.json   # Grafana dashboard
├── utils/
│   └── event_logger.py        # CSV Event Logger
├── logs/
│   └── simulation_log.csv     # Журнал подій симуляції
├── docker-compose.yml         # Docker-сервіси
├── requirements.txt           # Python залежності
└── .env                       # Змінні середовища (не комітити!)
```

---

## Сторінки Streamlit UI

| Сторінка | Призначення |
|---------|-------------|
| **Overview** | Загальний стан системи, швидка перевірка аномалій |
| **Systems** | Поточні значення всіх 12 Modbus-регістрів |
| **Red Team** | Запуск 9 преднастроєних атак + власна атака |
| **Blue Team** | Виявлення аномалій, recovery, PDF-звіт, журнал подій |
| **Training** | Вікторина по всіх трьох підсистемах |
| **Code Lab** | Навчальний код атак, захисту та recovery |
| **Scenarios** | Покрокові навчальні сценарії (Beginner/Intermediate/Advanced) |
| **Statistics** | Аналітика журналу: атаки, виявлення, відновлення |
| **How It Works** | Пояснення архітектури простими словами |

---

## Запуск CLI-атаки

```bash
# Активувати venv
.\venv\Scripts\Activate.ps1

# Запустити атаку через CLI
python attacks/attack_scenarios.py --attack pump_off
python attacks/attack_scenarios.py --attack motor_speed_overdrive
python attacks/attack_scenarios.py --attack cooling_temp_spoofing --duration 15
```

Доступні атаки: `pump_off`, `pump_false_data`, `water_level_spoofing`, `conveyor_stop`, `motor_speed_overdrive`, `emergency_stop_abuse`, `fan_shutdown`, `valve_manipulation`, `cooling_temp_spoofing`

---

## Технічний стек

- **Python 3.11** — основна мова розробки
- **Streamlit** — веб-інтерфейс без фронтенд-розробки
- **pymodbus 2.5.3** — Modbus TCP клієнт і сервер
- **InfluxDB 2.7** — time-series БД для телеметрії
- **Grafana** — моніторинг та візуалізація
- **Docker Compose** — оркестрація сервісів
- **ReportLab** — генерація PDF-звітів
- **MITRE ATT&CK for ICS** — класифікація векторів атак
