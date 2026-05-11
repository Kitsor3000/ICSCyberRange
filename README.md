# ICSCyberRange

Платформа для симуляції кібератак на ICS/SCADA системи.

## Запуск
```bash
docker compose up -d

.\venv\Scripts\Activate.ps1

Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

python simulator/plc_server.py

python telemetry/collector.py

python defense/recovery.py
