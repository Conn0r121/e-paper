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

# Apply the TZ environment variable so clock/date reflect local time, not UTC.
if hasattr(time, "tzset"):
    time.tzset()

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


def run_diagnostic():
    """Hold images WITHOUT sleeping, then sleep, to localize the fade.

    Watch the panel and match it to the log lines:
      * If BLACK or the DASHBOARD fade during their "holding, powered" window
        (before we ever call sleep) -> the pixels are not holding charge, which
        is a hardware fault -> the (new) panel is likely defective; return it.
      * If they stay sharp while powered but fade only after "entering deep
        sleep" -> deep sleep is relaxing the image, and we fix it in software
        by not deep-sleeping between refreshes.
    """
    hold = 25
    black = Image.new("1", (config.PANEL_WIDTH, config.PANEL_HEIGHT), 0)
    frame = render.render_dashboard(config.PANEL_WIDTH, config.PANEL_HEIGHT,
                                    data.collect())

    epd = epd5in83_V2.EPD()
    epd.init()

    log.info("DIAG 1/3: full BLACK, holding %ds powered (NOT sleeping) — "
             "does it stay deep black?", hold)
    epd.display(epd.getbuffer(black))
    time.sleep(hold)

    log.info("DIAG 2/3: DASHBOARD, holding %ds powered (NOT sleeping) — "
             "does it stay sharp?", hold)
    epd.display(epd.getbuffer(frame))
    time.sleep(hold)

    log.info("DIAG 3/3: entering DEEP SLEEP now — watch %ds for the image to "
             "change/fade after sleep", hold)
    epd.sleep()
    time.sleep(hold)
    log.info("DIAG done. Unset DIAGNOSTIC to resume the normal dashboard.")


def main():
    log.info("E-Paper Dashboard started.")
    if config.ON_PI and config.DIAGNOSTIC:
        run_diagnostic()
        return
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
