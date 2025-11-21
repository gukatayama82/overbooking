import os
import requests
from flask import Flask, jsonify, send_from_directory
from icalendar import Calendar
from datetime import datetime
from dateutil.parser import parse
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

app = Flask(__name__)

ICAL_BOOKING_URL = os.getenv("ICAL_BOOKING_URL")
ICAL_AIRBNB_URL = os.getenv("ICAL_AIRBNB_URL")


def download_ical(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.text


def parse_ical(ical_text, source_name):
    cal = Calendar.from_ical(ical_text)
    events = []

    for component in cal.walk():
        if component.name == "VEVENT":
            start = component.get("DTSTART").dt
            end = component.get("DTEND").dt

            # Normaliza para date
            if isinstance(start, datetime):
                start = start.date()
            if isinstance(end, datetime):
                end = end.date()

            events.append({
                "start": start,
                "end": end,
                "source": source_name
            })
    return events


def check_overbooking(events):
    conflicts = []
    sorted_events = sorted(events, key=lambda x: x["start"])

    for i in range(len(sorted_events) - 1):
        a = sorted_events[i]
        b = sorted_events[i + 1]
        if b["start"] < a["end"]:
            conflicts.append((a, b))

    return conflicts


# -------------------------
# 🔥 ROTA PRINCIPAL (Front)
# -------------------------
@app.get("/")
def calendario():
    return send_from_directory("static", "calendario.html")


# -----------------------------
# 🔥 ROTA QUE O FRONT CONSUME
# -----------------------------
@app.get("/reservas")
def reservas():
    try:
        booking_ical = download_ical(ICAL_BOOKING_URL)
        airbnb_ical = download_ical(ICAL_AIRBNB_URL)

        booking_events = parse_ical(booking_ical, "Booking")
        airbnb_events = parse_ical(airbnb_ical, "Airbnb")

        reservas_por_origem = {
            "Booking": [
                {"start": str(ev["start"]), "end": str(ev["end"])}
                for ev in booking_events
            ],
            "Airbnb": [
                {"start": str(ev["start"]), "end": str(ev["end"])}
                for ev in airbnb_events
            ]
        }

        return jsonify(reservas_por_origem)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.get("/mock/overbooking")
def overbooking_mock():
    # --- MOCK DE RESERVAS ---
    airbnb_mock = [
        {"start": "2025-11-19", "end": "2025-11-24"},
        {"start": "2025-11-26", "end": "2025-11-30"}
    ]

    booking_mock = [
        {"start": "2025-11-22", "end": "2025-11-25"},  # <-- ESTE CRIA CONFLITO
        {"start": "2026-06-01", "end": "2027-05-21"}
    ]

    reservas_por_origem = {
        "Airbnb": airbnb_mock,
        "Booking": booking_mock
    }

    # --- DEFINIÇÃO DO CONFLITO ---
    conflict = {
        "event1": {
            "start": "2025-11-19",
            "end": "2025-11-24",
            "source": "Airbnb"
        },
        "event2": {
            "start": "2025-11-22",
            "end": "2025-11-25",
            "source": "Booking"
        }
    }

    return jsonify({
        "overbooking": True,
        "details": "Conflito encontrado entre reservas.",
        "reservas": reservas_por_origem,
        "conflicts": [conflict]
    })


# -------------------------
# 🔥 ROTA DETALHADA (JSON)
# -------------------------
@app.get("/overbooking")
def overbooking():
    try:
        booking_ical = download_ical(ICAL_BOOKING_URL)
        airbnb_ical = download_ical(ICAL_AIRBNB_URL)

        booking_events = parse_ical(booking_ical, "Booking")
        airbnb_events = parse_ical(airbnb_ical, "Airbnb")

        all_events = booking_events + airbnb_events

        conflicts = check_overbooking(all_events)

        reservas_por_origem = {
            "Booking": [
                {"start": str(ev["start"]), "end": str(ev["end"])}
                for ev in booking_events
            ],
            "Airbnb": [
                {"start": str(ev["start"]), "end": str(ev["end"])}
                for ev in airbnb_events
            ]
        }

        if not conflicts:
            return jsonify({
                "overbooking": False,
                "details": "Nenhum conflito encontrado.",
                "reservas": reservas_por_origem
            })

        formatted_conflicts = []
        for a, b in conflicts:
            formatted_conflicts.append({
                "event1": {"start": str(a["start"]), "end": str(a["end"]), "source": a["source"]},
                "event2": {"start": str(b["start"]), "end": str(b["end"]), "source": b["source"]}
            })

        return jsonify({
            "overbooking": True,
            "conflicts": formatted_conflicts,
            "reservas": reservas_por_origem
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
