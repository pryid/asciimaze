# -*- coding: utf-8 -*-
"""UI helpers: prompts, mouse tracking, settings menu, win screen."""
from __future__ import annotations

import curses
import math
import time
import textwrap
from typing import Callable, List, Literal, Tuple

from .constants import FOV_MAX, FOV_MIN
from .i18n import LOCALES, make_tr, option_display
from .models import Settings
from .style import Capabilities, Style, draw_box
from .util import clamp, safe_addstr

def confirm_yes_no(stdscr, tr: Callable[[str], str], prompt_key: str) -> bool:
    prompt = tr(prompt_key)
    h, w = stdscr.getmaxyx()
    line = tr("prompt_yes_no", prompt=prompt)
    safe_addstr(stdscr, h - 1, 0, line[: max(0, w - 1)], curses.A_REVERSE)
    stdscr.refresh()

    stdscr.nodelay(False)
    try:
        while True:
            ch = stdscr.getch()
            if ch in (ord("y"), ord("Y")):
                return True
            if ch in (ord("n"), ord("N")):
                return False
    finally:
        stdscr.nodelay(True)

def set_mouse_tracking(enable: bool) -> bool:
    try:
        if not enable:
            curses.mousemask(0)
            return False
        if not hasattr(curses, "REPORT_MOUSE_POSITION"):
            return False
        mask = curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION
        avail, _old = curses.mousemask(mask)
        try:
            curses.mouseinterval(0)
        except Exception:
            pass
        return bool(avail & curses.REPORT_MOUSE_POSITION)
    except Exception:
        return False

def cycle_value(values: List[str], cur: str, delta: int) -> str:
    try:
        i = values.index(cur)
    except ValueError:
        i = 0
    return values[(i + delta) % len(values)]

def run_menu(stdscr, base_style: Style, caps: Capabilities, settings: Settings, mode: Literal["start", "pause"]) -> str:
    stdscr.nodelay(False)
    sel = 0

    render_choices = ["auto", "text", "half", "braille"]
    onoff = ["on", "off"]
    onoffauto = ["auto", "on", "off"]
    hud_choices = ["auto5", "always", "off"]
    mode_choices = ["default", "free", "demo_default", "demo_free"]

    lang_choices = list(LOCALES.keys())
    if "en" in lang_choices:
        lang_choices = ["en"] + [l for l in lang_choices if l != "en"]

    items: List[Tuple[str, str, str]] = []
    if mode == "pause":
        items.append(("menu_action_resume", "action", "resume"))
    else:
        items.append(("menu_action_start", "action", "start"))

    items += [
        ("menu_item_mode", "choice", "mode"),
        ("menu_item_difficulty", "range", "difficulty"),
        ("menu_item_render", "choice", "render_mode"),
        ("menu_item_shadows", "choice", "shadows"),
        ("menu_item_colors", "choice", "colors"),
        ("menu_item_unicode", "choice", "unicode"),
        ("menu_item_mouse", "choice", "mouse_look"),
        ("menu_item_hud", "choice", "hud"),
        ("menu_item_fov", "range", "fov"),
        ("menu_item_language", "choice", "language"),
    ]

    if mode == "pause":
        items.append(("menu_action_restart", "action", "restart"))
    items.append(("menu_action_quit", "action", "quit"))

    while True:
        tr = make_tr(settings.language)

        stdscr.erase()
        H, W = stdscr.getmaxyx()

        if H < 14 or W < 44:
            safe_addstr(stdscr, 0, 0, tr("menu_small"))
            safe_addstr(stdscr, 2, 0, tr("menu_small_hint"))
            stdscr.refresh()
            ch = stdscr.getch()
            if ch in (ord("q"), ord("Q")):
                if confirm_yes_no(stdscr, tr, "prompt_quit_short"):
                    stdscr.nodelay(True)
                    return "quit"
            if ch in (10, 13, curses.KEY_ENTER):
                stdscr.nodelay(True)
                return "resume" if mode == "pause" else "start"
            continue

        box_w = min(94, W - 4)
        box_h = min(30, H - 4)
        box_x = (W - box_w) // 2
        box_y = (H - box_h) // 2

        unicode_ui = base_style.unicode_ok
        border_attr = curses.A_NORMAL
        if base_style.colors_ok and base_style.hud_pair:
            border_attr |= curses.color_pair(base_style.hud_pair)

        draw_box(stdscr, box_y, box_x, box_h, box_w, unicode_ui, border_attr)
        title = tr("menu_title")
        safe_addstr(stdscr, box_y, box_x + 2, title[: box_w - 4], border_attr | curses.A_BOLD)

        cap_parts = []
        cap_parts.append(tr("cap_utf8_ok") if caps.unicode_ok else tr("cap_utf8_no"))
        if caps.colors_ok and caps.color_mode == "256":
            cap_parts.append(tr("cap_color_256"))
        elif caps.colors_ok:
            cap_parts.append(tr("cap_color"))
        else:
            cap_parts.append(tr("cap_mono"))
        cap_parts.append(tr("cap_mouse_ok") if caps.mouse_motion_ok else tr("cap_mouse_no"))

        caps_line = tr("menu_terminal", caps=", ".join(cap_parts))
        safe_addstr(stdscr, box_y + 1, box_x + 2, caps_line[: box_w - 4], curses.A_DIM)

        left_w = int(box_w * 0.56)
        left_x = box_x + 2
        right_x = left_x + left_w + 2
        # Right panel width: keep one-char padding before the border to prevent curses auto-wrap.
        text_right = box_x + box_w - 3
        right_w = max(0, text_right - right_x + 1)
        top_y = box_y + 3

        sep = "│" if unicode_ui else "|"
        for yy in range(top_y - 1, box_y + box_h - 2):
            safe_addstr(stdscr, yy, right_x - 2, sep, border_attr)

        list_h = box_y + box_h - 4 - top_y + 1
        sel = max(0, min(sel, len(items) - 1))

        label_width = 12

        for i, (label_key, kind, key) in enumerate(items):
            y = top_y + i
            if y >= top_y + list_h:
                break
            is_sel = (i == sel)
            prefix = "▶ " if unicode_ui else "> "
            pad = "  "
            attr = curses.A_REVERSE if is_sel else curses.A_NORMAL

            label = tr(label_key)

            value = ""
            warn = ""
            if kind == "range":
                if key == "difficulty":
                    value = f"[ {settings.difficulty:3d} ]"
                elif key == "fov":
                    value = f"[ {settings.fov * 180.0 / math.pi:5.1f}° ]"
            elif kind == "choice":
                cur = str(getattr(settings, key))
                disp = option_display(tr, key, cur)
                value = f"[ {disp} ]"
                if key == "mouse_look" and not caps.mouse_motion_ok and cur != "off":
                    warn = " " + tr("warn_mouse")

            line = (prefix if is_sel else pad) + f"{label:<{label_width}} {value}{warn}"
            safe_addstr(stdscr, y, left_x, line[: left_w], attr)

        label_key, kind, key = items[sel]
        label = tr(label_key)
        help_lines = [
            tr("help_selected", label=label),
            "",
            tr("help_nav_title"),
            tr("help_nav_updown"),
            tr("help_nav_leftright"),
            tr("help_nav_enter"),
            tr("help_nav_esc"),
            "",
            tr("help_in_game"),
            "",
        ]

        if key == "render_mode":
            help_lines += [
                tr("help_render_title"),
                tr("help_render_text"),
                tr("help_render_half"),
                tr("help_render_braille"),
                tr("help_render_auto"),
            ]
        elif key == "hud":
            help_lines += [
                tr("help_hud_title"),
                tr("help_hud_auto5"),
                tr("help_hud_always"),
                tr("help_hud_off"),
            ]
        elif key == "mouse_look":
            help_lines += [
                tr("help_mouse_title"),
                tr("help_mouse_desc1"),
                tr("help_mouse_desc2"),
            ]
        elif key == "mode":
            help_lines += [
                tr("help_mode_title"),
                tr("help_mode_default"),
                tr("help_mode_free"),
                tr("help_mode_demo_default"),
                tr("help_mode_demo_free"),
            ]
        elif key == "shadows":
            help_lines += [
                tr("help_shadows_title"),
                tr("help_shadows_on"),
                tr("help_shadows_off"),
            ]

        # Wrap help text so it never draws outside the frame.
        yy = top_y
        for i, line in enumerate(help_lines):
            if yy >= box_y + box_h - 2:
                break
            base_attr = (curses.A_BOLD if i == 0 else curses.A_DIM)
            if not line:
                yy += 1
                continue
            # textwrap.wrap ensures long lines are wrapped within right_w.
            for seg in textwrap.wrap(line, width=max(1, right_w), break_long_words=True, break_on_hyphens=True):
                if yy >= box_y + box_h - 2:
                    break
                safe_addstr(stdscr, yy, right_x, seg, base_attr)
                yy += 1

        footer = tr("menu_footer")
        safe_addstr(stdscr, box_y + box_h - 2, box_x + 2, footer[: box_w - 4], curses.A_DIM)

        stdscr.refresh()
        ch = stdscr.getch()

        if ch == 27:  # ESC
            if mode == "start":
                if confirm_yes_no(stdscr, tr, "prompt_exit"):
                    stdscr.nodelay(True)
                    return "quit"
                continue
            stdscr.nodelay(True)
            return "resume"

        if ch in (curses.KEY_UP, ord("w"), ord("W")):
            sel = (sel - 1) % len(items)
            continue
        if ch in (curses.KEY_DOWN, ord("s"), ord("S")):
            sel = (sel + 1) % len(items)
            continue

        def adjust(delta: int) -> None:
            label_key, kind, key = items[sel]
            if kind == "range":
                if key == "difficulty":
                    settings.difficulty = int(clamp(settings.difficulty + delta, 1, 100))
                elif key == "fov":
                    settings.fov = clamp(settings.fov + math.radians(2.0) * delta, FOV_MIN, FOV_MAX)
            elif kind == "choice":
                cur = str(getattr(settings, key))
                if key == "render_mode":
                    settings.render_mode = cycle_value(render_choices, cur, delta)  # type: ignore
                elif key == "shadows":
                    settings.shadows = cycle_value(onoff, cur, delta)  # type: ignore
                elif key in ("colors", "unicode", "mouse_look"):
                    setattr(settings, key, cycle_value(onoffauto, cur, delta))
                elif key == "hud":
                    settings.hud = cycle_value(hud_choices, cur, delta)  # type: ignore
                elif key == "mode":
                    settings.mode = cycle_value(mode_choices, cur, delta)  # type: ignore
                elif key == "language":
                    settings.language = cycle_value(lang_choices, cur, delta)

        if ch in (curses.KEY_LEFT, ord("a"), ord("A")):
            adjust(-1)
            continue
        if ch in (curses.KEY_RIGHT, ord("d"), ord("D")):
            adjust(1)
            continue

        if ch in (10, 13, curses.KEY_ENTER, ord(" "), ord("\n")):
            label_key, kind, key = items[sel]
            if kind == "action":
                if key == "quit":
                    if confirm_yes_no(stdscr, tr, "prompt_exit"):
                        stdscr.nodelay(True)
                        return "quit"
                    continue
                stdscr.nodelay(True)
                return key
            if kind == "choice":
                adjust(1)
                continue

        if ch in (ord("q"), ord("Q")):
            if confirm_yes_no(stdscr, tr, "prompt_exit"):
                stdscr.nodelay(True)
                return "quit"

def win_screen(stdscr, tr: Callable[[str], str], seconds: float, wait: bool) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    msg1 = tr("win_title")
    msg2 = tr("win_time", sec=seconds)
    msg3 = tr("win_press_key") if wait else tr("win_demo_next")

    y = h // 2 - 1
    for i, msg in enumerate((msg1, msg2, msg3)):
        x = max(0, (w - len(msg)) // 2)
        safe_addstr(stdscr, y + i, x, msg[: max(0, w - x - 1)], curses.A_BOLD)

    stdscr.refresh()
    if wait:
        stdscr.nodelay(False)
        stdscr.getch()
        stdscr.nodelay(True)
    else:
        time.sleep(0.9)
