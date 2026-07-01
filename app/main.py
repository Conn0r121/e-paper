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

import config
import data
import render

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

if config.ON_PI:
    from waveshare_epd import epd5in83_V2


def update_display():
    """Render one frame and push it to the panel (or save a preview)."""
    try:
        frame = data.collect()
        if config.ON_PI:
            log.info("Waking up e-Paper...")
            epd = epd5in83_V2.EPD()
            epd.init()
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


def main():
    log.info("E-Paper Dashboard started.")
    if not config.ON_PI:
        update_display()
        return

    while True:
        update_display()
        log.info("Cycle complete. Sleeping for %ds...", config.REFRESH_INTERVAL)
        time.sleep(config.REFRESH_INTERVAL)


if __name__ == "__main__":
    main()
