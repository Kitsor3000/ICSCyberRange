import csv
import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


LOG_FILE = "logs/simulation_log.csv"
REPORT_DIR = "reports"
REPORT_FILE = os.path.join(REPORT_DIR, "simulation_report.pdf")


def read_last_logs(limit=20):
    if not os.path.exists(LOG_FILE):
        return []

    with open(LOG_FILE, mode="r", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    return rows[-limit:]


def generate_pdf_report():
    os.makedirs(REPORT_DIR, exist_ok=True)

    logs = read_last_logs(limit=20)

    pdf = canvas.Canvas(REPORT_FILE, pagesize=A4)
    width, height = A4

    y = height - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, "ICSCyberRange Simulation Report")

    y -= 25
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    y -= 35
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, "Project systems:")

    y -= 18
    pdf.setFont("Helvetica", 10)
    pdf.drawString(55, y, "- Pump Station")
    y -= 15
    pdf.drawString(55, y, "- Conveyor Line")
    y -= 15
    pdf.drawString(55, y, "- Cooling System")

    y -= 30
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, "Last simulation events:")

    y -= 20

    if not logs:
        pdf.setFont("Helvetica", 10)
        pdf.drawString(40, y, "No events found in logs/simulation_log.csv")
    else:
        for index, row in enumerate(logs, start=1):
            if y < 90:
                pdf.showPage()
                y = height - 50

            pdf.setFont("Helvetica-Bold", 9)
            pdf.drawString(40, y, f"{index}. {row.get('timestamp', '')} | {row.get('event_type', '')}")

            y -= 13
            pdf.setFont("Helvetica", 8)
            description = row.get("description", "")

            if len(description) > 95:
                description = description[:95] + "..."

            pdf.drawString(55, y, f"Description: {description}")

            y -= 13
            pdf.drawString(
                55,
                y,
                "Pump: "
                f"T={row.get('temperature', '')}, "
                f"P={row.get('pressure', '')}, "
                f"Level={row.get('water_level', '')}, "
                f"Pump={row.get('pump_status', '')}"
            )

            y -= 13
            pdf.drawString(
                55,
                y,
                "Conveyor: "
                f"Status={row.get('conveyor_status', '')}, "
                f"Speed={row.get('motor_speed', '')}, "
                f"Current={row.get('motor_current', '')}, "
                f"E-Stop={row.get('emergency_stop', '')}"
            )

            y -= 13
            pdf.drawString(
                55,
                y,
                "Cooling: "
                f"Fan={row.get('fan_status', '')}, "
                f"Temp={row.get('coolant_temperature', '')}, "
                f"Valve={row.get('valve_position', '')}, "
                f"Alarm={row.get('cooling_alarm', '')}"
            )

            y -= 20

    pdf.save()

    print(f"PDF report generated: {REPORT_FILE}")


if __name__ == "__main__":
    generate_pdf_report()