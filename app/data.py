"""Data sources for the dashboard: weather and local system stats."""

import logging
import requests

import config

log = logging.getLogger(__name__)


def get_weather():
    """Fetch location + current conditions from wttr.in in a single request.

    Returns a dict: {"city": str, "conditions": str}. wttr.in auto-detects the
    location from our IP when config.WEATHER_LOCATION is empty. The `%l` token
    gives the resolved location name, so we no longer need a separate geo-IP
    lookup.
    """
    location = config.WEATHER_LOCATION
    fmt = "%l|%C %t %p"  # location | conditions temp precip
    url = f"https://wttr.in/{location}?{config.WEATHER_UNITS}&format={fmt}"
    try:
        text = requests.get(url, timeout=config.HTTP_TIMEOUT).text.strip()
        city, _, conditions = text.partition("|")
        return {
            "city": (city.strip() or "UNKNOWN").upper(),
            "conditions": conditions.strip() or "N/A",
        }
    except Exception as e:
        log.error("Weather fetch failed: %s", e)
        return {"city": "OFFLINE", "conditions": "Weather Offline"}


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
