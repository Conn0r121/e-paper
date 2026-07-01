"""E-Paper desk dashboard entry point.

On the Pi: initializes the Waveshare panel and refreshes it on a loop.
On Windows: renders a single preview.png and opens it.
"""

import logging
import os
import sys
import time

# Ensure sibling modules resolve whether run as `python main.py` or imported.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image

import config
import data
import render

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

if config.ON_PI:
    from waveshare_epd import epd5in83_V2


def _deep_clean(epd):
    """Flash the panel fully black then white a few times to scrub ghosting.

    E-paper accumulates a faint residue of prior frames; a normal refresh does
    not always fully clear it. Driving every pixel hard to both extremes resets
    them to a clean white baseline.
    """
    log.info("Deep-cleaning panel (ghost-busting)...")
    black = Image.new("1", (epd.width, epd.height), 0)
    white = Image.new("1", (epd.width, epd.height), 255)
    for _ in range(2):
        epd.display(epd.getbuffer(black))
        epd.display(epd.getbuffer(white))


def update_display(deep_clean=False):
    """Render one frame and push it to the panel (or save a preview)."""
    try:
        frame = data.collect()
        if config.ON_PI:
            log.info("Waking up e-Paper...")
            epd = epd5in83_V2.EPD()
            epd.init()
            if deep_clean:
                _deep_clean(epd)
            canvas = render.render_dashboard(epd.width, epd.height, frame)
            epd.display(epd.getbuffer(canvas))
            epd.sleep()
        else:
            log.info("Running in Windows preview mode")
            canvas = render.render_dashboard(config.PANEL_WIDTH, config.PANEL_HEIGHT, frame)
            canvas.save(config.PREVIEW_FILE)
            log.info("Saved preview to %s", config.PREVIEW_FILE)
            os.startfile(config.PREVIEW_FILE)
    except Exception as e:
        log.error("Display update failed: %s", e)


def _should_deep_clean(cycle):
    """Deep-clean at startup and every DEEP_CLEAN_EVERY cycles thereafter."""
    every = config.DEEP_CLEAN_EVERY
    return every > 0 and cycle % every == 0


def main():
    log.info("E-Paper Dashboard started.")
    if not config.ON_PI:
        update_display()
        return

    cycle = 0
    while True:
        update_display(deep_clean=_should_deep_clean(cycle))
        cycle += 1
        log.info("Cycle complete. Sleeping for %ds...", config.REFRESH_INTERVAL)
        time.sleep(config.REFRESH_INTERVAL)


if __name__ == "__main__":
    main()
