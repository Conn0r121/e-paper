"""Central configuration for the e-Paper dashboard.

Everything tunable lives here. Values can be overridden with environment
variables (handy from docker-compose without touching code).
"""

import os
import platform

# --- Platform detection -----------------------------------------------------
# We run on the Pi (Linux) against real hardware, and on Windows for previews.
ON_PI = platform.system() == "Linux"


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# --- Refresh loop -----------------------------------------------------------
# How often the display redraws, in seconds. Single source of truth: the loop
# sleep and the on-screen "Interval" label both read from here.
REFRESH_INTERVAL = _env_int("REFRESH_INTERVAL", 300)

# Ghost-busting: flash the panel fully black/white every N refresh cycles to
# scrub accumulated ghosting haze. Also runs once at startup. 0 disables.
DEEP_CLEAN_EVERY = _env_int("DEEP_CLEAN_EVERY", 12)

# One-shot hardware test: when set (DIAGNOSTIC=1), run a hold-and-observe
# sequence instead of the normal loop, to tell "pixels don't hold" (hardware)
# apart from "deep sleep relaxes the image" (software). See main.run_diagnostic.
DIAGNOSTIC = os.environ.get("DIAGNOSTIC", "").strip() not in ("", "0")

# Dark mode: draw white-on-black instead of black-on-white. A mostly-black
# screen holds far better on a panel that can't sustain a mostly-white image,
# so this is the workaround for the fading-panel issue. DARK_MODE=1 to enable.
DARK_MODE = os.environ.get("DARK_MODE", "").strip() not in ("", "0")

# --- Weather ----------------------------------------------------------------
# Leave WEATHER_LOCATION empty to let wttr.in auto-detect from the Pi's IP.
WEATHER_LOCATION = os.environ.get("WEATHER_LOCATION", "").strip()
# "u" = imperial (F/mph), "m" = metric (C/km/h). See wttr.in docs.
WEATHER_UNITS = os.environ.get("WEATHER_UNITS", "u")
HTTP_TIMEOUT = _env_int("HTTP_TIMEOUT", 10)

# --- Calendars --------------------------------------------------------------
# Secret published-calendar ICS URL (e.g. from Outlook/M365). Keep this out of
# git and out of shared logs. Set it via the environment only.
WORK_ICS_URL = os.environ.get("WORK_ICS_URL", "").strip()

# Google (Calendar + Tasks) OAuth. All secrets — set via the environment only,
# never commit them. Generate the refresh token once with app/google_auth.py.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN", "").strip()
GOOGLE_CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "primary").strip()

# Hide events that have already ended, so the schedule shows only what's in
# progress or upcoming (all-day events always stay). HIDE_PAST_EVENTS=0 to show
# the full day.
HIDE_PAST_EVENTS = os.environ.get("HIDE_PAST_EVENTS", "1").strip() not in ("", "0")

# Shuffle the task list on each refresh. SHUFFLE_TASKS=0 to keep Google's order.
SHUFFLE_TASKS = os.environ.get("SHUFFLE_TASKS", "1").strip() not in ("", "0")

# --- Panel ------------------------------------------------------------------
# Waveshare 5.83" V2 is 648 x 480. Used directly for the Windows preview and
# as a fallback if the hardware doesn't report its own dimensions.
PANEL_WIDTH = 648
PANEL_HEIGHT = 480

# --- Fonts ------------------------------------------------------------------
if ON_PI:
    FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
else:
    FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"

# --- Preview ----------------------------------------------------------------
PREVIEW_FILE = "preview.png"
