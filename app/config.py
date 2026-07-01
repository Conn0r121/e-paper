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
