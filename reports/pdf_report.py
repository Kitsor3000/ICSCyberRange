import csv
import os
from collections import Counter
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


LOG_FILE = "logs/simulation_log.csv"
REPORT_DIR = "reports"
REPORT_FILE = os.path.join(REPORT_DIR, "simulation_report.pdf")

ATTACK_KEYWORDS = [
    "ATTACK", "INJECTION", "SPOOFING", "OVERDRIVE",
    "ABUSE", "SHUTDOWN", "MANIPULATION", "CUSTOM_ATTACK",
]


def read_last_logs(limit=50):
    if not os.path.exists(LOG_FILE):
        return []

    with open(LOG_FILE, mode="r", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    return rows[-limit:]


def build_summary(logs):
    total = len(logs)
    attacks = sum(1 for r in logs if any(k in r.get("event_type", "") for k in ATTACK_KEYWORDS))
    detections = sum(1 for r in logs if r.get("event_type", "") == "ANOMALY_DETECTION")
    recoveries = sum(1 for r in logs if "RECOVERY" in r.get("event_type", ""))
    training = sum(1 for r in logs if "TRAINING" in r.get("event_type", ""))

    event_counts = Counter(r.get("event_type", "") for r in logs)
    top_events = event_counts.most_common(5)

    return {
        "total": total,
        "attacks": attacks,
        "detections": detections,
        "recoveries": recoveries,
        "training": training,
        "top_events": top_events,
    }


def draw_divider(pdf, y, width, margin=40):
    pdf.setStrokeColorRGB(0.75, 0.75, 0.75)
    pdf.setLineWidth(0.5)
    pdf.line(margin, y, width - margin, y)
    return y - 10


def draw_section_header(pdf, y, text, width, margin=40):
    pdf.setFillColorRGB(0.08, 0.10, 0.18)
    pdf.rect(margin, y - 4, width - 2 * margin, 20, fill=1, stroke=0)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin + 8, y + 3, text)
    pdf.setFillColorRGB(0, 0, 0)
    return y - 28


def draw_stat_box(pdf, x, y, label, value, box_w=110, box_h=44):
    pdf.setFillColorRGB(0.95, 0.97, 1.0)
    pdf.setStrokeColorRGB(0.70, 0.75, 0.90)
    pdf.setLineWidth(0.8)
    pdf.rect(x, y, box_w, box_h, fill=1, stroke=1)

    pdf.setFont("Helvetica-Bold", 18)
    pdf.setFillColorRGB(0.10, 0.20, 0.55)
    pdf.drawCentredString(x + box_w / 2, y + 20, str(value))

    pdf.setFont("Helvetica", 8)
    pdf.setFillColorRGB(0.35, 0.35, 0.35)
    pdf.drawCentredString(x + box_w / 2, y + 9, label)

    pdf.setFillColorRGB(0, 0, 0)


def generate_pdf_report():
    os.makedirs(REPORT_DIR, exist_ok=True)

    logs = read_last_logs(limit=50)
    summary = build_summary(logs)

    pdf = canvas.Canvas(REPORT_FILE, pagesize=A4)
    width, height = A4
    margin = 40

    # --------------------------------------------------------
    # HEADER BLOCK
    # --------------------------------------------------------
    pdf.setFillColorRGB(0.05, 0.08, 0.20)
    pdf.rect(0, height - 80, width, 80, fill=1, stroke=0)

    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(margin, height - 38, "ICSCyberRange")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(margin, height - 56, "Incident Simulation Report")

    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(
        width - margin,
        height - 56,
        f"Generated: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}"
    )

    pdf.setFillColorRGB(0.27, 0.53, 0.91)
    pdf.rect(0, height - 84, width, 4, fill=1, stroke=0)

    pdf.setFillColorRGB(0, 0, 0)

    y = height - 110

    # --------------------------------------------------------
    # PROJECT INFO
    # --------------------------------------------------------
    y = draw_section_header(pdf, y, "Project Overview", width, margin)

    pdf.setFont("Helvetica", 9)
    pdf.setFillColorRGB(0.2, 0.2, 0.2)

    lines = [
        "Platform: ICSCyberRange — ICS/SCADA Cyber Range Simulation",
        "Systems: Pump Station  |  Conveyor Line  |  Cooling System",
        "Protocol: Modbus TCP (port 5020)  |  Telemetry: InfluxDB  |  Monitoring: Grafana",
        "Report scope: last 50 simulation events from logs/simulation_log.csv",
    ]
    for line in lines:
        pdf.drawString(margin, y, line)
        y -= 14

    pdf.setFillColorRGB(0, 0, 0)
    y -= 8

    # --------------------------------------------------------
    # SUMMARY STATISTICS
    # --------------------------------------------------------
    y = draw_section_header(pdf, y, "Simulation Summary", width, margin)

    box_gap = 12
    box_w = (width - 2 * margin - 4 * box_gap) / 5
    box_h = 44
    stats = [
        ("Total Events", summary["total"]),
        ("Attacks", summary["attacks"]),
        ("Detections", summary["detections"]),
        ("Recoveries", summary["recoveries"]),
        ("Training", summary["training"]),
    ]
    for i, (label, value) in enumerate(stats):
        bx = margin + i * (box_w + box_gap)
        draw_stat_box(pdf, bx, y, label, value, box_w=box_w, box_h=box_h)

    y -= box_h + 18

    # --------------------------------------------------------
    # TOP EVENT TYPES
    # --------------------------------------------------------
    if summary["top_events"]:
        y = draw_section_header(pdf, y, "Top Event Types", width, margin)

        for event_type, count in summary["top_events"]:
            bar_max_w = width - 2 * margin - 160
            bar_w = min(bar_max_w, int((count / max(1, summary["total"])) * bar_max_w))

            pdf.setFont("Helvetica", 8)
            pdf.setFillColorRGB(0.2, 0.2, 0.2)
            pdf.drawString(margin, y, event_type)

            pdf.setFillColorRGB(0.27, 0.53, 0.91)
            pdf.rect(margin + 155, y - 2, bar_w, 10, fill=1, stroke=0)

            pdf.setFillColorRGB(0.1, 0.1, 0.1)
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawString(margin + 160 + bar_w + 4, y, str(count))

            pdf.setFillColorRGB(0, 0, 0)
            y -= 16

        y -= 6

    # --------------------------------------------------------
    # EVENT LOG
    # --------------------------------------------------------
    y = draw_section_header(pdf, y, "Simulation Event Log", width, margin)

    if not logs:
        pdf.setFont("Helvetica", 9)
        pdf.drawString(margin, y, "No events found in logs/simulation_log.csv")
        y -= 20
    else:
        col_ts = margin
        col_ev = margin + 120
        col_ds = margin + 258

        pdf.setFont("Helvetica-Bold", 8)
        pdf.setFillColorRGB(0.35, 0.35, 0.35)
        pdf.drawString(col_ts, y, "Timestamp")
        pdf.drawString(col_ev, y, "Event Type")
        pdf.drawString(col_ds, y, "Description")
        y -= 4
        y = draw_divider(pdf, y, width, margin)

        for index, row in enumerate(logs):
            if y < 90:
                pdf.showPage()
                y = height - 50

                pdf.setFont("Helvetica-Bold", 8)
                pdf.setFillColorRGB(0.35, 0.35, 0.35)
                pdf.drawString(col_ts, y, "Timestamp")
                pdf.drawString(col_ev, y, "Event Type")
                pdf.drawString(col_ds, y, "Description")
                y -= 4
                y = draw_divider(pdf, y, width, margin)

            row_bg = 0.97 if index % 2 == 0 else 1.0
            pdf.setFillColorRGB(row_bg, row_bg, row_bg)
            pdf.rect(margin, y - 3, width - 2 * margin, 13, fill=1, stroke=0)

            event_type = row.get("event_type", "")
            is_attack = any(k in event_type for k in ATTACK_KEYWORDS)
            is_recovery = "RECOVERY" in event_type
            is_alert = "ANOMALY" in event_type

            if is_attack:
                pdf.setFillColorRGB(0.80, 0.10, 0.10)
            elif is_alert:
                pdf.setFillColorRGB(0.75, 0.45, 0.0)
            elif is_recovery:
                pdf.setFillColorRGB(0.05, 0.55, 0.15)
            else:
                pdf.setFillColorRGB(0.15, 0.15, 0.15)

            pdf.setFont("Helvetica", 7)
            pdf.drawString(col_ts, y, row.get("timestamp", "")[:19])

            pdf.setFont("Helvetica-Bold", 7)
            pdf.drawString(col_ev, y, event_type[:18])

            pdf.setFont("Helvetica", 7)
            pdf.setFillColorRGB(0.15, 0.15, 0.15)
            description = row.get("description", "")
            if len(description) > 58:
                description = description[:58] + "..."
            pdf.drawString(col_ds, y, description)

            y -= 14

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------
    if y > 70:
        y = draw_divider(pdf, y, width, margin)

    pdf.setFont("Helvetica", 8)
    pdf.setFillColorRGB(0.5, 0.5, 0.5)
    pdf.drawString(margin, 30, "ICSCyberRange Diploma Project  |  Modbus TCP ICS/SCADA Simulation Platform")
    pdf.drawRightString(width - margin, 30, f"Page 1")

    pdf.setFillColorRGB(0, 0, 0)
    pdf.save()

    print(f"PDF report generated: {REPORT_FILE}")


if __name__ == "__main__":
    generate_pdf_report()
