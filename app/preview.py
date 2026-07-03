"""Local preview harness for the e-Paper dashboard.

Design the display without a Pi and without waiting on the network. By default
this renders a set of fixed sample scenarios into a single contact sheet so you
can eyeball every layout edge case (long text, offline state, night, fresh
boot) before pushing anything.

Usage:
    python preview.py            # contact sheet of sample scenarios (offline)
    python preview.py --live     # one frame from real weather/system data
    python preview.py --no-open  # write the file but don't pop it open

Output goes to preview.png (git-ignored).
"""

import argparse
import os


def _load_local_env():
    """Load google_creds.env / .env from the repo root so --live works with no
    manual env setup. Real environment values take precedence."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("google_creds.env", ".env"):
        path = os.path.join(repo_root, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


_load_local_env()  # must run before config is imported (it reads env at import)

from PIL import Image, ImageDraw, ImageFont

import config
import data
import render

# --- Sample scenarios -------------------------------------------------------
# Each is a (label, DashboardData) pair. Add cases here as we redesign so
# regressions in any state show up on the contact sheet.
def _ev(time_label, title, source="personal"):
    return data.AgendaEvent(time_label=time_label, title=title, source=source)


def _task(title, due_label=""):
    return data.Task(title=title, due_label=due_label)


SCENARIOS = [
    ("Typical day", data.DashboardData(
        clock="14:30", weekday="Tuesday", date_long="July 1", city="ROCHESTER",
        temp="+72°F", condition="Partly Cloudy",
        events=[
            _ev("9:00 AM", "Standup", "work"),
            _ev("11:30 AM", "Design review", "work"),
            _ev("2:00 PM", "1:1 with Sam", "work"),
            _ev("6:00 PM", "Gym", "personal"),
        ],
        tasks=[
            _task("Pay electric bill"),
            _task("Email Sam about PR"),
            _task("Order groceries"),
        ],
        cpu_temp="48.3°C", uptime="3d 4h", interval_min=5,
    )),
    ("Both columns empty", data.DashboardData(
        clock="07:12", weekday="Saturday", date_long="July 5", city="ROCHESTER",
        temp="+64°F", condition="Clear",
        events=[], tasks=[],
        cpu_temp="44.0°C", uptime="6d 1h", interval_min=5,
    )),
    ("Busy day (both overflow)", data.DashboardData(
        clock="08:05", weekday="Wednesday", date_long="July 2", city="ROCHESTER",
        temp="+70°F", condition="Cloudy",
        events=[
            _ev("8:30 AM", "Standup", "work"),
            _ev("9:00 AM", "Sprint planning", "work"),
            _ev("10:30 AM", "Architecture sync", "work"),
            _ev("12:00 PM", "Lunch with Alex", "personal"),
            _ev("1:00 PM", "Customer demo", "work"),
            _ev("3:30 PM", "Retro", "work"),
        ],
        tasks=[
            _task("Renew registration"), _task("Book flights"),
            _task("Reply to landlord"), _task("Submit expenses"),
            _task("Call dentist"), _task("Water plants"),
        ],
        cpu_temp="52.1°C", uptime="12h 8m", interval_min=5,
    )),
    ("Long titles + long city", data.DashboardData(
        clock="17:42", weekday="Thursday", date_long="July 3",
        city="FAIRPORT, NEW YORK, UNITED STATES",
        temp="+64°F", condition="Heavy Thunderstorm And Rain",
        events=[
            _ev("All day", "Quarterly planning offsite at the downtown office", "work"),
            _ev("6:30 PM", "Dinner reservation with the whole extended family", "personal"),
        ],
        tasks=[
            _task("Finish the end-of-quarter report for leadership review"),
            _task("Pick up dry cleaning before the shop closes at six"),
        ],
        cpu_temp="55.0°C", uptime="1d 2h", interval_min=5,
    )),
    ("Offline / error state", data.DashboardData(
        clock="00:00", weekday="Wednesday", date_long="July 1", city="OFFLINE",
        temp="--", condition="Offline",
        events=[], tasks=[],
        cpu_temp="N/A", uptime="N/A", interval_min=5,
    )),
]

# Contact-sheet chrome
PAD = 24
LABEL_H = 34
GAP = 20


def _label_font():
    try:
        return ImageFont.truetype(config.FONT_PATH, 22)
    except OSError:
        return ImageFont.load_default()


def _frame(d):
    """Render one panel-sized frame as an RGB image for the sheet."""
    img = render.render_dashboard(config.PANEL_WIDTH, config.PANEL_HEIGHT, d)
    return img.convert("RGB")


def build_contact_sheet():
    """Stack every sample scenario, labelled and bordered, into one image."""
    font = _label_font()
    w = config.PANEL_WIDTH
    cell_h = LABEL_H + config.PANEL_HEIGHT
    sheet_w = w + 2 * PAD + 2
    sheet_h = PAD + len(SCENARIOS) * (cell_h + GAP)

    sheet = Image.new("RGB", (sheet_w, sheet_h), (230, 230, 230))
    draw = ImageDraw.Draw(sheet)

    y = PAD
    for label, d in SCENARIOS:
        draw.text((PAD, y), label, font=font, fill=(20, 20, 20))
        top = y + LABEL_H
        # 1px frame around the panel so overflow past 648×480 is visible
        draw.rectangle((PAD - 1, top - 1, PAD + w, top + config.PANEL_HEIGHT),
                       outline=(200, 0, 0))
        sheet.paste(_frame(d), (PAD, top))
        y += cell_h + GAP

    return sheet


def _open(path):
    try:
        os.startfile(path)  # Windows
    except AttributeError:
        pass  # non-Windows: just leave the file


def main():
    parser = argparse.ArgumentParser(description="Render a dashboard preview.")
    parser.add_argument("--live", action="store_true",
                        help="render one frame from real data instead of samples")
    parser.add_argument("--no-open", action="store_true",
                        help="write the file but do not open it")
    args = parser.parse_args()

    if args.live:
        d = data.collect()
        img = render.render_dashboard(config.PANEL_WIDTH, config.PANEL_HEIGHT, d)
    else:
        img = build_contact_sheet()

    img.save(config.PREVIEW_FILE)
    print(f"Saved {config.PREVIEW_FILE} ({img.size[0]}x{img.size[1]})")
    if not args.no_open:
        _open(config.PREVIEW_FILE)


if __name__ == "__main__":
    main()
