import requests
from icalendar import Calendar
from datetime import datetime, timedelta
from dateutil.parser import parse

# ===============================
# CONFIGURAÇÃO: coloque seus links iCal
# ===============================
ICAL_BOOKING_URL = "https://ical.booking.com/v1/export?t=c6d876b9-e989-4b05-a792-47d79d7ffced"
ICAL_AIRBNB_URL = "https://www.airbnb.com.br/calendar/ical/1296556470938698085.ics?s=b422fe67205d2d394dbc3958bcc154e0"


def download_ical(url):
    """Baixa o arquivo ICS e retorna o conteúdo."""
    r = requests.get(url)
    r.raise_for_status()
    return r.text


def parse_ical(ical_text, source_name):
    """
    Lê um iCal e retorna uma lista de eventos:
    [
        {"start": date, "end": date, "source": "Booking/Airbnb"},
        ...
    ]
    """
    cal = Calendar.from_ical(ical_text)
    events = []

    for component in cal.walk():
        if component.name == "VEVENT":
            start = component.get("DTSTART").dt
            end = component.get("DTEND").dt

            # Normaliza para datas (caso venha datetime)
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
    """Detecta conflitos entre reservas/bloqueios."""
    conflicts = []
    sorted_events = sorted(events, key=lambda x: x["start"])

    for i in range(len(sorted_events) - 1):
        current = sorted_events[i]
        next_event = sorted_events[i+1]

        # Há overlap se o próximo começa antes do atual terminar
        if next_event["start"] < current["end"]:
            conflicts.append((current, next_event))

    return conflicts


# ===============================
# EXECUÇÃO
# ===============================
print("Baixando calendários...")

booking_ical = download_ical(ICAL_BOOKING_URL)
airbnb_ical = download_ical(ICAL_AIRBNB_URL)

print("Lendo eventos...")

booking_events = parse_ical(booking_ical, "Booking")
airbnb_events = parse_ical(airbnb_ical, "Airbnb")

# Agenda unificada
all_events = booking_events + airbnb_events

print("\n=== AGENDA UNIFICADA ===")
for ev in sorted(all_events, key=lambda x: x["start"]):
    print(f"{ev['start']} → {ev['end']}  |  fonte: {ev['source']}")

print("\n=== VERIFICANDO OVERBOOKING ===")
conflicts = check_overbooking(all_events)

if not conflicts:
    print("✔ Nenhum overbooking detectado.")
else:
    print("❌ OVERBOOKING ENCONTRADO:")
    for a, b in conflicts:
        print(f"""
        Conflito:
        - {a['source']} {a['start']} → {a['end']}
        - {b['source']} {b['start']} → {b['end']}
        """)

print("\nConcluído.")
