"""Calendar sources: fetch and parse ICS feeds into AgendaEvents.

Kept separate from data.py so the parsing (parse_ics) is a pure function that
can be tested offline against a fixture .ics file, with no network involved.
"""

import datetime as dt
import logging

import requests

import config
from data import AgendaEvent

log = logging.getLogger(__name__)


# Title prefixes that published feeds use for canceled meetings. Outlook uses
# "Canceled: <title>"; Google-origin invites use "Canceled event: <title>".
_CANCELLED_PREFIXES = (
    "canceled:", "cancelled:",
    "canceled event:", "cancelled event:",
)


def _is_cancelled(ev):
    """True for canceled meetings, which published feeds often still include."""
    if str(ev.get("STATUS", "")).upper() == "CANCELLED":
        return True
    summary = str(ev.get("SUMMARY", "")).strip().lower()
    return summary.startswith(_CANCELLED_PREFIXES)


def _fmt_time(when):
    """Format a datetime as a compact 12-hour label, e.g. '9:05 AM'."""
    hour12 = when.hour % 12 or 12
    ampm = "AM" if when.hour < 12 else "PM"
    return f"{hour12}:{when.minute:02d} {ampm}"


def parse_ics(text, day=None, tz=None, source="work"):
    """Parse ICS text into a sorted list[AgendaEvent] for a single day.

    Recurring events are expanded, so daily/weekly meetings appear. All-day
    events are labelled "All day" and sorted first. ``day`` defaults to today
    in the local timezone; ``tz`` defaults to the system local timezone.
    """
    import icalendar
    import recurring_ical_events

    tz = tz or dt.datetime.now().astimezone().tzinfo
    day = day or dt.datetime.now(tz).date()
    start = dt.datetime.combine(day, dt.time.min, tzinfo=tz)
    end = start + dt.timedelta(days=1)

    cal = icalendar.Calendar.from_ical(text)
    occurrences = recurring_ical_events.of(cal).between(start, end)

    rows = []
    for ev in occurrences:
        if _is_cancelled(ev):
            continue
        begin = ev.get("DTSTART").dt
        title = str(ev.get("SUMMARY", "(no title)")).strip() or "(no title)"
        all_day = isinstance(begin, dt.date) and not isinstance(begin, dt.datetime)
        if all_day:
            sort_key = (0, 0)
            label = "All day"
        else:
            local = begin.astimezone(tz)
            sort_key = (1, local.hour * 60 + local.minute)
            label = _fmt_time(local)
        rows.append(AgendaEvent(time_label=label, title=title, source=source,
                                sort_key=sort_key))

    rows.sort(key=lambda e: e.sort_key)
    return rows


def fetch_work_events():
    """Fetch and parse today's events from the configured work ICS URL."""
    if not config.WORK_ICS_URL:
        return []
    try:
        resp = requests.get(config.WORK_ICS_URL, timeout=config.HTTP_TIMEOUT)
        resp.raise_for_status()
        return parse_ics(resp.text, source="work")
    except Exception as e:
        log.error("Work calendar fetch failed: %s", e)
        return []
