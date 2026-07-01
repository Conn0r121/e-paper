"""Dashboard rendering: turns data into a 1-bit PIL image for the panel.

All layout lives here. To redesign the display, this is the file to edit.
"""

import functools
import logging
import time

from PIL import Image, ImageDraw, ImageFont

import config
import data

log = logging.getLogger(__name__)

# --- Colours (1-bit) --------------------------------------------------------
BLACK = 0
WHITE = 255

# --- Layout -----------------------------------------------------------------
MARGIN = 20
HEADER_H = 100


@functools.lru_cache(maxsize=None)
def _font(size):
    """Load a font once per size (cached across refresh cycles)."""
    return ImageFont.truetype(config.FONT_PATH, size)


def render_dashboard(width, height):
    """Build and return the dashboard image at the given dimensions."""
    canvas = Image.new("1", (width, height), WHITE)
    draw = ImageDraw.Draw(canvas)

    font_lg = _font(80)
    font_md = _font(40)
    font_sm = _font(26)

    weather = data.get_weather()

    # --- Header: clock, city, date ---
    draw.rectangle((0, 0, width - 1, HEADER_H), fill=BLACK)
    draw.text((MARGIN, 10), time.strftime("%H:%M"), font=font_lg, fill=WHITE)
    draw.text((320, 20), weather["city"], font=font_sm, fill=WHITE)
    draw.text((320, 55), time.strftime("%A, %b %d"), font=font_sm, fill=WHITE)

    # --- Current conditions ---
    draw.text((MARGIN, 120), "CURRENT CONDITIONS", font=font_sm, fill=BLACK)
    draw.text((MARGIN, 155), weather["conditions"], font=font_md, fill=BLACK)
    draw.line((MARGIN, 225, width - MARGIN, 225), fill=BLACK, width=2)

    # --- System status (lower right) ---
    draw.line((400, 240, 400, 450), fill=BLACK, width=2)
    interval_min = max(1, config.REFRESH_INTERVAL // 60)
    draw.text((420, 240), "SYSTEM STATUS", font=font_sm, fill=BLACK)
    draw.text((420, 290), f"CPU: {data.get_cpu_temp()}", font=font_sm, fill=BLACK)
    draw.text((420, 330), f"UP: {data.get_uptime()}", font=font_sm, fill=BLACK)
    draw.text((420, 370), f"Interval: {interval_min}m", font=font_sm, fill=BLACK)

    return canvas
