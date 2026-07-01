"""Dashboard rendering: turns a DashboardData into a 1-bit PIL image.

This module is PURE: given the same DashboardData and size, it always draws
the same pixels. No network, no hardware, no clock reads happen here. That is
what makes preview.py able to design offline and deterministically.

Layout is a clean, minimal, two-column design:

    +------------------------------------------------+
    | Tuesday                         14:30          |
    | July 1                     72°F Partly Cloudy  |
    | ---------------------------------------------- |
    | SCHEDULE            |  TASKS                    |
    |  ● 9:00 Standup     |  □ Pay bill               |
    |  ○ 11:30 Review     |  □ Email Sam              |
    |  ● 2:00 1:1         |  □ PR review              |
    | ---------------------------------------------- |
    | ● work  ○ personal          CPU 48°C · up 3d   |
    +------------------------------------------------+

All layout lives here. To redesign the display, this is the file to edit.
"""

import functools

from PIL import Image, ImageDraw, ImageFont

import config

# --- Colours (1-bit) --------------------------------------------------------
BLACK = 0
WHITE = 255

# --- Layout -----------------------------------------------------------------
MARGIN = 28
HEADER_RULE_Y = 132       # hairline under the header
COL_TOP = 148             # column heading baseline
COL_FIRST_ROW = 186       # first item row in each column
ROW_H = 46                # vertical space per item
FOOTER_RULE_Y = 438       # hairline above the footer
COL_GAP = 28              # horizontal gap between the two columns

# --- Type scale -------------------------------------------------------------
F_WEEKDAY = 56
F_DATE = 26
F_CLOCK = 44
F_WEATHER = 24
F_LABEL = 20
F_ITEM = 24
F_ITEM_TIME = 22
F_EMPTY = 24
F_FOOTER = 18

TIME_COL_W = 112          # max width of the time sub-column inside SCHEDULE
MARKER_W = 22             # width reserved for the bullet / checkbox


@functools.lru_cache(maxsize=None)
def _font(size):
    """Load a font once per size (cached across refresh cycles)."""
    return ImageFont.truetype(config.FONT_PATH, size)


def _fit(draw, text, font, max_w):
    """Truncate text with an ellipsis so it never exceeds max_w pixels."""
    if draw.textlength(text, font=font) <= max_w:
        return text
    ellipsis = "…"
    while text and draw.textlength(text + ellipsis, font=font) > max_w:
        text = text[:-1]
    return (text.rstrip() + ellipsis) if text else ellipsis


def _right(draw, x_right, y, text, font, fill=BLACK):
    """Draw text right-aligned to x_right."""
    draw.text((x_right - draw.textlength(text, font=font), y), text,
              font=font, fill=fill)


def _bullet(draw, x, cy, filled, r=6):
    """Draw a calendar-source marker: filled = work, hollow = personal."""
    box = (x, cy - r, x + 2 * r, cy + r)
    draw.ellipse(box, fill=BLACK if filled else WHITE, outline=BLACK, width=2)


def _checkbox(draw, x, cy, s=15):
    """Draw an empty checkbox centred vertically on cy."""
    draw.rectangle((x, cy - s // 2, x + s, cy + s // 2), outline=BLACK, width=2)


def _fit_rows(top, bottom):
    return max(0, (bottom - top) // ROW_H)


def _draw_header(draw, width, d):
    right_edge = width - MARGIN
    draw.text((MARGIN, 18), d.weekday, font=_font(F_WEEKDAY), fill=BLACK)
    draw.text((MARGIN, 88), d.date_long, font=_font(F_DATE), fill=BLACK)

    _right(draw, right_edge, 22, d.clock, _font(F_CLOCK))
    weather = _fit(draw, f"{d.temp}  {d.condition}", _font(F_WEATHER), width // 2)
    _right(draw, right_edge, 90, weather, _font(F_WEATHER))

    draw.line((MARGIN, HEADER_RULE_Y, right_edge, HEADER_RULE_Y), fill=BLACK)


def _draw_schedule(draw, x, w, events):
    """Left column: today's merged calendar."""
    draw.text((x, COL_TOP), "SCHEDULE", font=_font(F_LABEL), fill=BLACK)
    if not events:
        draw.text((x, COL_FIRST_ROW + 6), "Nothing scheduled",
                  font=_font(F_EMPTY), fill=BLACK)
        return

    rows = _fit_rows(COL_FIRST_ROW, FOOTER_RULE_Y)
    shown, overflow = _paginate(events, rows)

    # Size the time sub-column to the widest time label so it never collides
    # with the title, but cap it so long titles still get room.
    time_font = _font(F_ITEM_TIME)
    time_x = x + MARKER_W
    widest = max(draw.textlength(ev.time_label, font=time_font) for ev in shown)
    title_x = time_x + min(int(widest) + 12, TIME_COL_W)
    title_w = x + w - title_x
    y = COL_FIRST_ROW
    for ev in shown:
        cy = y + F_ITEM // 2
        _bullet(draw, x, cy, filled=(ev.source == "work"))
        draw.text((time_x, y), ev.time_label, font=_font(F_ITEM_TIME), fill=BLACK)
        draw.text((title_x, y),
                  _fit(draw, ev.title, _font(F_ITEM), title_w),
                  font=_font(F_ITEM), fill=BLACK)
        y += ROW_H
    if overflow:
        draw.text((time_x, y), f"+{overflow} more",
                  font=_font(F_ITEM_TIME), fill=BLACK)


def _draw_tasks(draw, x, w, tasks):
    """Right column: open to-do items."""
    draw.text((x, COL_TOP), "TASKS", font=_font(F_LABEL), fill=BLACK)
    if not tasks:
        draw.text((x, COL_FIRST_ROW + 6), "No tasks",
                  font=_font(F_EMPTY), fill=BLACK)
        return

    rows = _fit_rows(COL_FIRST_ROW, FOOTER_RULE_Y)
    shown, overflow = _paginate(tasks, rows)

    title_x = x + MARKER_W + 4
    title_w = x + w - title_x
    y = COL_FIRST_ROW
    for task in shown:
        _checkbox(draw, x, y + F_ITEM // 2)
        draw.text((title_x, y),
                  _fit(draw, task.title, _font(F_ITEM), title_w),
                  font=_font(F_ITEM), fill=BLACK)
        y += ROW_H
    if overflow:
        draw.text((title_x, y), f"+{overflow} more",
                  font=_font(F_ITEM_TIME), fill=BLACK)


def _paginate(items, rows):
    """Return (visible items, hidden count), reserving a row for '+N more'."""
    if len(items) <= rows:
        return items, 0
    shown = items[:max(0, rows - 1)]
    return shown, len(items) - len(shown)


def _draw_footer(draw, width, d):
    right_edge = width - MARGIN
    draw.line((MARGIN, FOOTER_RULE_Y, right_edge, FOOTER_RULE_Y), fill=BLACK)
    y = FOOTER_RULE_Y + 12

    # Legend on the left: ● work  ○ personal
    font = _font(F_FOOTER)
    cy = y + F_FOOTER // 2
    _bullet(draw, MARGIN, cy, filled=True, r=5)
    draw.text((MARGIN + 16, y), "work", font=font, fill=BLACK)
    off = MARGIN + 16 + draw.textlength("work", font=font) + 18
    _bullet(draw, int(off), cy, filled=False, r=5)
    draw.text((int(off) + 16, y), "personal", font=font, fill=BLACK)
    legend_end = int(off) + 16 + draw.textlength("personal", font=font)

    # System status on the right, using whatever width the legend leaves
    status = _fit(draw, f"{d.city} · CPU {d.cpu_temp} · up {d.uptime}",
                  font, right_edge - legend_end - 20)
    _right(draw, right_edge, y, status, font)


def render_dashboard(width, height, d):
    """Build and return the dashboard image for DashboardData ``d``."""
    canvas = Image.new("1", (width, height), WHITE)
    draw = ImageDraw.Draw(canvas)

    _draw_header(draw, width, d)

    col_w = (width - 2 * MARGIN - COL_GAP) // 2
    col1_x = MARGIN
    col2_x = MARGIN + col_w + COL_GAP
    divider_x = MARGIN + col_w + COL_GAP // 2
    draw.line((divider_x, COL_TOP, divider_x, FOOTER_RULE_Y - 8), fill=BLACK)

    _draw_schedule(draw, col1_x, col_w, d.events)
    _draw_tasks(draw, col2_x, col_w, d.tasks)
    _draw_footer(draw, width, d)

    return canvas
