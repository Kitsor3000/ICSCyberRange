"""
Tests for reports/pdf_report.py

Covers: build_summary(), read_last_logs(), ATTACK_KEYWORDS.
No real PDF is generated — only the pure-Python helper functions are tested.
"""

import csv
import os
import pytest
import reports.pdf_report as pr


# ── build_summary ─────────────────────────────────────────────────────────────

def test_build_summary_empty_logs():
    s = pr.build_summary([])
    assert s["total"] == 0
    assert s["attacks"] == 0
    assert s["detections"] == 0
    assert s["recoveries"] == 0
    assert s["training"] == 0
    assert s["top_events"] == []


def test_build_summary_counts_total():
    logs = [{"event_type": "A"}, {"event_type": "B"}, {"event_type": "C"}]
    assert pr.build_summary(logs)["total"] == 3


def test_build_summary_counts_attacks_by_keyword():
    logs = [
        {"event_type": "PUMP_ATTACK"},
        {"event_type": "INJECTION"},
        {"event_type": "SPOOFING"},
        {"event_type": "OVERDRIVE"},
        {"event_type": "ABUSE"},
        {"event_type": "SHUTDOWN"},
        {"event_type": "MANIPULATION"},
        {"event_type": "CUSTOM_ATTACK"},
        {"event_type": "NORMAL_EVENT"},
    ]
    s = pr.build_summary(logs)
    assert s["attacks"] == 8
    assert s["total"] == 9


def test_build_summary_counts_detections():
    logs = [
        {"event_type": "ANOMALY_DETECTION"},
        {"event_type": "ANOMALY_DETECTION"},
        {"event_type": "OTHER"},
    ]
    assert pr.build_summary(logs)["detections"] == 2


def test_build_summary_counts_recoveries():
    logs = [
        {"event_type": "PUMP_RECOVERY"},
        {"event_type": "FULL_RECOVERY"},
        {"event_type": "COOLING_RECOVERY"},
        {"event_type": "ATTACK"},
    ]
    assert pr.build_summary(logs)["recoveries"] == 3


def test_build_summary_counts_training():
    logs = [
        {"event_type": "TRAINING_START"},
        {"event_type": "TRAINING_COMPLETE"},
        {"event_type": "ATTACK"},
    ]
    assert pr.build_summary(logs)["training"] == 2


def test_build_summary_top_events_sorted_by_frequency():
    logs = [
        {"event_type": "ATTACK"},
        {"event_type": "ATTACK"},
        {"event_type": "ATTACK"},
        {"event_type": "ANOMALY_DETECTION"},
        {"event_type": "ANOMALY_DETECTION"},
        {"event_type": "RECOVERY"},
    ]
    s = pr.build_summary(logs)
    assert s["top_events"][0] == ("ATTACK", 3)


def test_build_summary_top_events_max_5():
    logs = [{"event_type": f"EV_{i}"} for i in range(20)]
    s = pr.build_summary(logs)
    assert len(s["top_events"]) <= 5


def test_build_summary_missing_event_type_key():
    logs = [{"description": "no event_type key"}]
    s = pr.build_summary(logs)
    assert s["total"] == 1
    assert s["attacks"] == 0


# ── read_last_logs ─────────────────────────────────────────────────────────────

def test_read_last_logs_returns_empty_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(pr, "LOG_FILE", str(tmp_path / "nonexistent.csv"))
    assert pr.read_last_logs() == []


def test_read_last_logs_returns_all_rows_when_under_limit(tmp_path, monkeypatch):
    log_file = str(tmp_path / "test.csv")
    with open(log_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "event_type", "description"])
        for i in range(10):
            writer.writerow([f"2024-01-01 00:00:{i:02d}", f"EV_{i}", f"desc {i}"])

    monkeypatch.setattr(pr, "LOG_FILE", log_file)
    result = pr.read_last_logs(limit=50)
    assert len(result) == 10


def test_read_last_logs_respects_limit(tmp_path, monkeypatch):
    log_file = str(tmp_path / "test2.csv")
    with open(log_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "event_type", "description"])
        for i in range(30):
            writer.writerow([f"2024-01-01 00:00:{i:02d}", f"EV_{i}", f"d {i}"])

    monkeypatch.setattr(pr, "LOG_FILE", log_file)
    result = pr.read_last_logs(limit=5)
    assert len(result) == 5


def test_read_last_logs_returns_last_rows(tmp_path, monkeypatch):
    log_file = str(tmp_path / "test3.csv")
    with open(log_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "event_type", "description"])
        for i in range(20):
            writer.writerow([f"2024-01-01 00:00:{i:02d}", f"EV_{i}", f"d {i}"])

    monkeypatch.setattr(pr, "LOG_FILE", log_file)
    result = pr.read_last_logs(limit=3)
    types = [r["event_type"] for r in result]
    assert types == ["EV_17", "EV_18", "EV_19"]


# ── ATTACK_KEYWORDS integrity ─────────────────────────────────────────────────

def test_attack_keywords_list_is_not_empty():
    assert len(pr.ATTACK_KEYWORDS) > 0


def test_attack_keywords_contains_core_terms():
    for kw in ("ATTACK", "INJECTION", "SPOOFING", "SHUTDOWN", "MANIPULATION"):
        assert kw in pr.ATTACK_KEYWORDS, f"Missing keyword: {kw}"
