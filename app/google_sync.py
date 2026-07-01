"""Google Calendar + Google Tasks, fetched at runtime with a refresh token.

Deliberately dependency-light: only `requests`. The heavy google-auth libraries
are needed only once, locally, to mint the refresh token (see google_auth.py).
If Google isn't configured, every function returns [] so the dashboard still
runs on the work calendar alone.
"""

import datetime as dt
import logging

import requests

import config
from data import AgendaEvent, Task

log = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/{cal}/events"
TASKS_URL = "https://tasks.googleapis.com/tasks/v1/lists/@default/tasks"


def _configured():
    return all((config.GOOGLE_CLIENT_ID, config.GOOGLE_CLIENT_SECRET,
                config.GOOGLE_REFRESH_TOKEN))


def _access_token():
    """Exchange the long-lived refresh token for a short-lived access token."""
    resp = requests.post(TOKEN_URL, timeout=config.HTTP_TIMEOUT, data={
        "client_id": config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "refresh_token": config.GOOGLE_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def _fmt_time(when):
    hour12 = when.hour % 12 or 12
    ampm = "AM" if when.hour < 12 else "PM"
    return f"{hour12}:{when.minute:02d} {ampm}"


def _end_minutes(end_info, midnight, tz, start_min):
    """Minutes-from-midnight when a timed event ends; fallback start + 30."""
    when = end_info.get("dateTime")
    if when:
        end_local = dt.datetime.fromisoformat(
            when.replace("Z", "+00:00")).astimezone(tz)
        return int((end_local - midnight).total_seconds() // 60)
    return start_min + 30


def _today_bounds(tz):
    start = dt.datetime.combine(dt.datetime.now(tz).date(), dt.time.min, tzinfo=tz)
    return start, start + dt.timedelta(days=1)


def fetch_events():
    """Return today's Google Calendar events as list[AgendaEvent]."""
    if not _configured():
        return []
    try:
        tz = dt.datetime.now().astimezone().tzinfo
        start, end = _today_bounds(tz)
        token = _access_token()
        resp = requests.get(
            EVENTS_URL.format(cal=config.GOOGLE_CALENDAR_ID),
            headers={"Authorization": f"Bearer {token}"},
            timeout=config.HTTP_TIMEOUT,
            params={
                "timeMin": start.isoformat(),
                "timeMax": end.isoformat(),
                "singleEvents": "true",   # expand recurring events
                "orderBy": "startTime",
                "maxResults": 50,
            },
        )
        resp.raise_for_status()

        events = []
        for item in resp.json().get("items", []):
            if item.get("status") == "cancelled":
                continue
            title = (item.get("summary") or "(no title)").strip()
            start_info = item.get("start", {})
            if "date" in start_info:            # all-day event
                events.append(AgendaEvent(time_label="All day", title=title,
                                          source="personal", sort_key=(0, 0)))
            else:
                when = dt.datetime.fromisoformat(
                    start_info["dateTime"].replace("Z", "+00:00")).astimezone(tz)
                start_min = when.hour * 60 + when.minute
                events.append(AgendaEvent(
                    time_label=_fmt_time(when), title=title, source="personal",
                    sort_key=(1, start_min),
                    end_minutes=_end_minutes(item.get("end", {}), start, tz,
                                             start_min)))
        return events
    except Exception as e:
        log.error("Google Calendar fetch failed: %s", e)
        return []


def fetch_tasks():
    """Return open Google Tasks as list[Task]."""
    if not _configured():
        return []
    try:
        token = _access_token()
        resp = requests.get(
            TASKS_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=config.HTTP_TIMEOUT,
            params={"showCompleted": "false", "maxResults": 50},
        )
        resp.raise_for_status()

        tasks = []
        for item in resp.json().get("items", []):
            if item.get("status") == "completed":
                continue
            title = (item.get("title") or "").strip()
            if not title:
                continue  # Google returns blank placeholder tasks
            tasks.append(Task(title=title, due_label=_due_label(item.get("due"))))
        return tasks
    except Exception as e:
        log.error("Google Tasks fetch failed: %s", e)
        return []


def _due_label(due):
    """Turn a task's RFC3339 due date into a short label, or ''."""
    if not due:
        return ""
    try:
        due_date = dt.datetime.fromisoformat(due.replace("Z", "+00:00")).date()
    except ValueError:
        return ""
    today = dt.datetime.now().astimezone().date()
    if due_date < today:
        return "Overdue"
    if due_date == today:
        return "Today"
    return ""
