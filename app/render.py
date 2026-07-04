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

from PIL import Image, ImageDraw, ImageFont, ImageOps

import config

# --- Colours (1-bit) --------------------------------------------------------
BLACK = 0
WHITE = 255

# E-ink has no grey: contrast = ink coverage. Fatten every glyph by a pixel and
# use thick rules so thin strokes don't average out to grey at viewing distance.
STROKE = 1
RULE_W = 3          # horizontal divider thickness
DIVIDER_W = 2       # vertical column divider thickness
MARKER_W_PX = 3     # bullet / checkbox outline thickness

# --- Layout -----------------------------------------------------------------
MARGIN = 28
HEADER_RULE_Y = 132       # hairline under the header
COL_TOP = 148             # column heading baseline
COL_FIRST_ROW = 186       # first item row in each column
LINE_H = 30               # height of one wrapped text line
ITEM_GAP = 12             # gap between items (each item may span 1-2 lines)
MAX_LINES = 2             # max wrapped lines per item before ellipsis
BOTTOM_MARGIN = 16        # space below the columns
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


def _text(draw, xy, s, font, fill=BLACK):
    """Draw text with a stroke so it renders as solid black ink on e-paper."""
    draw.text(xy, s, font=font, fill=fill, stroke_width=STROKE, stroke_fill=fill)


def _right(draw, x_right, y, text, font, fill=BLACK):
    """Draw text right-aligned to x_right."""
    _text(draw, (x_right - draw.textlength(text, font=font), y), text, font, fill)


def _bullet(draw, x, cy, filled, r=6):
    """Draw a calendar-source marker: filled = work, hollow = personal."""
    box = (x, cy - r, x + 2 * r, cy + r)
    draw.ellipse(box, fill=BLACK if filled else WHITE, outline=BLACK,
                 width=MARKER_W_PX)


def _checkbox(draw, x, cy, s=15):
    """Draw an empty checkbox centred vertically on cy."""
    draw.rectangle((x, cy - s // 2, x + s, cy + s // 2), outline=BLACK,
                   width=MARKER_W_PX)


def _task_icon(draw, x, cy, status):
    """Left marker encoding task status: ! overdue, filled dot today, else box."""
    if status == "overdue":
        _text(draw, (x + 1, cy - F_ITEM // 2), "!", _font(F_ITEM))
    elif status == "today":
        r = 6
        cx = x + 7
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BLACK)
    else:
        _checkbox(draw, x, cy)


def _wrap(draw, text, font, max_w, max_lines):
    """Word-wrap text into at most max_lines lines, ellipsizing the overflow."""
    words = text.split()
    lines, cur, i = [], "", 0
    while i < len(words):
        trial = words[i] if not cur else cur + " " + words[i]
        if not cur or draw.textlength(trial, font=font) <= max_w:
            cur, i = trial, i + 1
        else:
            lines.append(cur)
            cur = ""
            if len(lines) == max_lines - 1:
                cur = " ".join(words[i:])
                break
    if cur:
        lines.append(cur)
    return [_fit(draw, ln, font, max_w) for ln in lines[:max_lines]] or [""]


def _draw_header(draw, width, d):
    right_edge = width - MARGIN
    _text(draw, (MARGIN, 18), d.weekday, _font(F_WEEKDAY))
    _text(draw, (MARGIN, 88), d.date_long, _font(F_DATE))

    _right(draw, right_edge, 22, d.clock, _font(F_CLOCK))
    weather = _fit(draw, f"{d.temp}  {d.condition}", _font(F_WEATHER), width // 2)
    _right(draw, right_edge, 90, weather, _font(F_WEATHER))

    draw.line((MARGIN, HEADER_RULE_Y, right_edge, HEADER_RULE_Y), fill=BLACK,
              width=RULE_W)


def _draw_schedule(draw, x, w, events, bottom):
    """Left column: today's merged calendar, titles wrapping to 2 lines."""
    _text(draw, (x, COL_TOP), "SCHEDULE", _font(F_LABEL))
    if not events:
        _text(draw, (x, COL_FIRST_ROW + 6), "Nothing scheduled", _font(F_EMPTY))
        return

    # Size the time sub-column to the widest time label so it never collides
    # with the title, but cap it so long titles still get room.
    time_font = _font(F_ITEM_TIME)
    time_x = x + MARKER_W
    widest = max(draw.textlength(ev.time_label, font=time_font) for ev in events)
    title_x = time_x + min(int(widest) + 12, TIME_COL_W)
    title_w = x + w - title_x
    item_font = _font(F_ITEM)

    # Reserve a line so the "+N more" note stays inside the column.
    limit = bottom - LINE_H
    y = COL_FIRST_ROW
    shown = 0
    for ev in events:
        lines = _wrap(draw, ev.title, item_font, title_w, MAX_LINES)
        h = len(lines) * LINE_H
        if y + h > limit:
            break
        _bullet(draw, x, y + F_ITEM // 2, filled=(ev.source == "work"))
        _text(draw, (time_x, y), ev.time_label, time_font)
        for li, line in enumerate(lines):
            _text(draw, (title_x, y + li * LINE_H), line, item_font)
        y += h + ITEM_GAP
        shown += 1

    if shown < len(events):
        _text(draw, (time_x, y), f"+{len(events) - shown} more", time_font)


def _draw_tasks(draw, x, w, tasks, bottom):
    """Right column: open to-do items, titles wrapping to 2 lines."""
    _text(draw, (x, COL_TOP), "TASKS", _font(F_LABEL))
    if not tasks:
        _text(draw, (x, COL_FIRST_ROW + 6), "No tasks", _font(F_EMPTY))
        return

    title_x = x + MARKER_W + 4
    title_w = x + w - title_x
    item_font = _font(F_ITEM)

    # Reserve a line so the "+N more" note stays inside the column.
    limit = bottom - LINE_H
    y = COL_FIRST_ROW
    shown = 0
    for task in tasks:
        lines = _wrap(draw, task.title, item_font, title_w, MAX_LINES)
        h = len(lines) * LINE_H
        if y + h > limit:
            break
        _task_icon(draw, x, y + F_ITEM // 2, _task_status(task))
        for li, line in enumerate(lines):
            _text(draw, (title_x, y + li * LINE_H), line, item_font)
        y += h + ITEM_GAP
        shown += 1

    if shown < len(tasks):
        _text(draw, (title_x, y), f"+{len(tasks) - shown} more", _font(F_ITEM_TIME))


def _task_status(task):
    label = (task.due_label or "").lower()
    if label == "overdue":
        return "overdue"
    if label == "today":
        return "today"
    return "normal"


def render_dashboard(width, height, d, dark=None):
    """Build and return the dashboard image for DashboardData ``d``.

    When ``dark`` is true (defaults to config.DARK_MODE) the finished image is
    inverted to white-on-black — a mostly-black screen that a fading panel holds
    far better than a mostly-white one.
    """
    dark = config.DARK_MODE if dark is None else dark

    canvas = Image.new("1", (width, height), WHITE)
    draw = ImageDraw.Draw(canvas)

    _draw_header(draw, width, d)

    col_w = (width - 2 * MARGIN - COL_GAP) // 2
    col1_x = MARGIN
    col2_x = MARGIN + col_w + COL_GAP
    divider_x = MARGIN + col_w + COL_GAP // 2
    bottom = height - BOTTOM_MARGIN
    draw.line((divider_x, COL_TOP, divider_x, bottom), fill=BLACK,
              width=DIVIDER_W)

    _draw_schedule(draw, col1_x, col_w, d.events, bottom)
    _draw_tasks(draw, col2_x, col_w, d.tasks, bottom)

    if dark:
        canvas = ImageOps.invert(canvas.convert("L")).convert("1")
    return canvas
