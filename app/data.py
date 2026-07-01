"""Data sources for the dashboard: weather and local system stats."""

import logging
import time
from dataclasses import dataclass

import requests

import config

log = logging.getLogger(__name__)


@dataclass
class AgendaEvent:
    """One calendar event on today's agenda, pre-formatted for display."""

    time_label: str        # "9:00 AM" or "All day"
    title: str             # "Standup"
    source: str = "personal"  # "work" (filled marker) or "personal" (hollow)
    # Sort key for merging sources: all-day = (0, 0), timed = (1, minutes).
    sort_key: tuple = (1, 0)
    # Minutes-since-midnight when the event ends (may exceed 1440 for multi-day).
    # None = all-day / unknown end; such events are never treated as "past".
    end_minutes: int = None


@dataclass
class Task:
    """One to-do item (from Google Tasks)."""

    title: str             # "Pay electric bill"
    due_label: str = ""    # "" or "Today" / "Overdue" (optional)


@dataclass
class DashboardData:
    """Everything the renderer needs to draw a frame.

    Rendering reads only from this object, so a frame is fully determined by
    its contents. Build a real one with collect(); build fake ones in
    preview.py to design offline without hitting the network or hardware.
    """

    clock: str          # "14:30"
    weekday: str        # "Tuesday"
    date_long: str      # "July 1"
    city: str           # "ROCHESTER"
    temp: str           # "+72°F"
    condition: str      # "Partly Cloudy"
    events: list        # list[AgendaEvent], soonest first
    tasks: list         # list[Task]
    cpu_temp: str       # "48.3°C"
    uptime: str         # "3d 4h"
    interval_min: int   # 5


def collect():
    """Assemble a DashboardData from live sources and the current time."""
    weather = get_weather()
    now = time.localtime()
    return DashboardData(
        clock=time.strftime("%H:%M", now),
        weekday=time.strftime("%A", now),
        date_long=f"{time.strftime('%B', now)} {now.tm_mday}",
        city=weather["city"],
        temp=weather["temp"],
        condition=weather["condition"],
        events=get_agenda(),
        tasks=get_tasks(),
        cpu_temp=get_cpu_temp(),
        uptime=get_uptime(),
        interval_min=max(1, config.REFRESH_INTERVAL // 60),
    )


def get_weather():
    """Fetch location + current conditions from wttr.in in a single request.

    Returns {"city", "temp", "condition"}. wttr.in auto-detects the location
    from our IP when config.WEATHER_LOCATION is empty; the `%l` token gives the
    resolved location name, so no separate geo-IP lookup is needed.
    """
    location = config.WEATHER_LOCATION
    fmt = "%l|%C|%t"  # location | condition | temp
    url = f"https://wttr.in/{location}?{config.WEATHER_UNITS}&format={fmt}"
    try:
        text = requests.get(url, timeout=config.HTTP_TIMEOUT).text.strip()
        parts = (text.split("|") + ["", "", ""])[:3]
        city, condition, temp = parts
        return {
            "city": (city.strip() or "UNKNOWN").upper(),
            "condition": condition.strip() or "N/A",
            "temp": temp.strip() or "--",
        }
    except Exception as e:
        log.error("Weather fetch failed: %s", e)
        return {"city": "OFFLINE", "condition": "Offline", "temp": "--"}


def get_agenda():
    """Return today's merged calendar as a list[AgendaEvent], soonest first.

    Merges the work calendar (M365 published ICS) with Google Calendar, sorted
    on a shared key (all-day events first, then by start time).
    """
    import calendars     # lazy imports avoid a circular import at module load
    import google_sync

    events = calendars.fetch_work_events() + google_sync.fetch_events()
    if config.HIDE_PAST_EVENTS:
        events = _drop_ended(events)
    events.sort(key=lambda e: e.sort_key)
    return events


def _drop_ended(events):
    """Keep all-day events and any timed event that hasn't ended yet."""
    now = time.localtime()
    now_min = now.tm_hour * 60 + now.tm_min
    return [e for e in events
            if e.end_minutes is None or e.end_minutes > now_min]


def get_tasks():
    """Return open to-do items as a list[Task] (from Google Tasks)."""
    import google_sync

    return google_sync.fetch_tasks()


def get_cpu_temp():
    """Read the Pi CPU temperature from sysfs. Returns e.g. '48.3°C'."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return f"{int(f.read()) / 1000:.1f}°C"
    except (OSError, ValueError):
        return "N/A"


def get_uptime():
    """Read system uptime from /proc/uptime. Returns e.g. '3d 4h' or '12m'."""
    try:
        with open("/proc/uptime") as f:
            seconds = int(float(f.read().split()[0]))
    except (OSError, ValueError, IndexError):
        return "N/A"

    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
