"""Terminal capabilities and styling (unicode, colors, shading)."""

from __future__ import annotations

import curses
import locale
import os
import sys
from dataclasses import dataclass
from typing import Literal

from .constants import (
    ASCII_FLOOR_SHADES,
    ASCII_WALL_SHADES,
    MAX_RAY_DIST,
    UNICODE_FLOOR_CHARS,
)
from .models import Settings
from .util import clamp, safe_addstr


@dataclass
class Capabilities:
    unicode_ok: bool
    colors_ok: bool
    color_mode: Literal["none", "basic", "256"]
    mouse_motion_ok: bool


@dataclass
class Style:
    unicode_ok: bool
    colors_ok: bool
    color_mode: Literal["none", "basic", "256"]
    wall_pairs: list[int]
    floor_pairs: list[int]
    hud_pair: int
    map_wall_pair: int
    map_floor_pair: int
    map_player_pair: int
    map_goal_pair: int

    def wall_attr(self, dist: float, side: int) -> int:
        if not self.colors_ok or not self.wall_pairs:
            return curses.A_NORMAL
        t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
        idx = int(t * (len(self.wall_pairs) - 1))
        pair = self.wall_pairs[idx]
        attr = curses.color_pair(pair)
        if side == 1:
            attr |= curses.A_DIM
        if dist < 3.5:
            attr |= curses.A_BOLD
        return attr

    def floor_attr_dist(self, dist: float) -> int:
        if not self.colors_ok or not self.floor_pairs:
            return curses.A_NORMAL
        t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
        idx = int(t * (len(self.floor_pairs) - 1))
        return curses.color_pair(self.floor_pairs[idx])

    def floor_attr_grad(self, y: int, view_h: int) -> int:
        if not self.colors_ok or not self.floor_pairs:
            return curses.A_NORMAL
        t = clamp((y - view_h * 0.5) / max(1.0, view_h * 0.5), 0.0, 1.0)
        idx = int(t * (len(self.floor_pairs) - 1))
        return curses.color_pair(self.floor_pairs[idx])

    def wall_char_text(self, dist: float) -> str:
        if not self.unicode_ok:
            t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
            idx = int(t * (len(ASCII_WALL_SHADES) - 1))
            return ASCII_WALL_SHADES[idx]
        if dist < 2.5:
            return "█"
        if dist < 5.5:
            return "▓"
        if dist < 10.0:
            return "▒"
        return "░"

    def wall_char_top(self, dist: float) -> str:
        if not self.unicode_ok:
            t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
            idx = int(t * (len(ASCII_WALL_SHADES) - 1))
            return ASCII_WALL_SHADES[idx]
        if dist < 2.5:
            return "▓"
        if dist < 6.0:
            return "▒"
        if dist < 14.0:
            return "░"
        return "·"

    def floor_char_dist(self, dist: float) -> str:
        if not self.unicode_ok:
            t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
            idx = int(t * (len(ASCII_FLOOR_SHADES) - 1))
            return ASCII_FLOOR_SHADES[idx]
        t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
        idx = int(t * (len(UNICODE_FLOOR_CHARS) - 1))
        return UNICODE_FLOOR_CHARS[idx]

    def floor_char_grad(self, y: int, view_h: int) -> str:
        if not self.unicode_ok:
            t = clamp((y - view_h * 0.5) / max(1.0, view_h * 0.5), 0.0, 1.0)
            idx = int(t * (len(ASCII_FLOOR_SHADES) - 1))
            return ASCII_FLOOR_SHADES[idx]
        t = clamp((y - view_h * 0.5) / max(1.0, view_h * 0.5), 0.0, 1.0)
        idx = int(t * (len(UNICODE_FLOOR_CHARS) - 1))
        return UNICODE_FLOOR_CHARS[idx]


def init_style(stdscr) -> Style:
    unicode_ok = prefer_utf8()

    colors_ok = False
    color_mode: Literal["none", "basic", "256"] = "none"
    wall_pairs: list[int] = []
    floor_pairs: list[int] = []
    hud_pair = 0
    map_wall_pair = 0
    map_floor_pair = 0
    map_player_pair = 0
    map_goal_pair = 0

    if curses.has_colors():
        try:
            curses.start_color()
            try:
                curses.use_default_colors()
            except Exception:
                pass
            colors_ok = True
        except Exception:
            colors_ok = False

    if colors_ok:
        colors = getattr(curses, "COLORS", 0) or 0
        pairs = getattr(curses, "COLOR_PAIRS", 0) or 0
        if colors >= 256 and pairs >= 64:
            color_mode = "256"
        else:
            color_mode = "basic"

        def safe_init_pair(pid: int, fg: int, bg: int) -> bool:
            try:
                curses.init_pair(pid, fg, bg)
                return True
            except Exception:
                return False

        pid = 1
        bg = -1

        if color_mode == "256":
            wall_colors = list(range(255, 231, -1))  # 24
            floor_colors = list(range(244, 235, -1))  # 9

            for fg in wall_colors:
                if pid >= pairs:
                    break
                if safe_init_pair(pid, fg, bg):
                    wall_pairs.append(pid)
                    pid += 1

            for fg in floor_colors:
                if pid >= pairs:
                    break
                if safe_init_pair(pid, fg, bg):
                    floor_pairs.append(pid)
                    pid += 1

            if pid < pairs and safe_init_pair(pid, 15, bg):
                hud_pair = pid
                pid += 1
            if pid < pairs and safe_init_pair(pid, 250, bg):
                map_wall_pair = pid
                pid += 1
            if pid < pairs and safe_init_pair(pid, 238, bg):
                map_floor_pair = pid
                pid += 1
            if pid < pairs and safe_init_pair(pid, 226, bg):
                map_player_pair = pid
                pid += 1
            if pid < pairs and safe_init_pair(pid, 46, bg):
                map_goal_pair = pid
                pid += 1
        else:
            wall_colors = [curses.COLOR_WHITE, curses.COLOR_CYAN, curses.COLOR_BLUE]
            floor_colors = [curses.COLOR_YELLOW, curses.COLOR_MAGENTA, curses.COLOR_RED]

            for fg in wall_colors:
                if pid >= pairs:
                    break
                if safe_init_pair(pid, fg, bg):
                    wall_pairs.append(pid)
                    pid += 1
            for fg in floor_colors:
                if pid >= pairs:
                    break
                if safe_init_pair(pid, fg, bg):
                    floor_pairs.append(pid)
                    pid += 1

            if pid < pairs and safe_init_pair(pid, curses.COLOR_WHITE, bg):
                hud_pair = pid
                pid += 1
            if pid < pairs and safe_init_pair(pid, curses.COLOR_WHITE, bg):
                map_wall_pair = pid
                pid += 1
            if pid < pairs and safe_init_pair(pid, curses.COLOR_BLACK, bg):
                map_floor_pair = pid
                pid += 1
            if pid < pairs and safe_init_pair(pid, curses.COLOR_YELLOW, bg):
                map_player_pair = pid
                pid += 1
            if pid < pairs and safe_init_pair(pid, curses.COLOR_GREEN, bg):
                map_goal_pair = pid
                pid += 1

    return Style(
        unicode_ok=unicode_ok,
        colors_ok=colors_ok,
        color_mode=color_mode,
        wall_pairs=wall_pairs,
        floor_pairs=floor_pairs,
        hud_pair=hud_pair,
        map_wall_pair=map_wall_pair,
        map_floor_pair=map_floor_pair,
        map_player_pair=map_player_pair,
        map_goal_pair=map_goal_pair,
    )


def effective_style(base: Style, settings: Settings) -> Style:
    unicode_ok = base.unicode_ok
    if settings.unicode == "on":
        unicode_ok = True
    elif settings.unicode == "off":
        unicode_ok = False

    colors_ok = base.colors_ok
    if settings.colors == "off":
        colors_ok = False
    elif settings.colors == "on":
        colors_ok = base.colors_ok

    return Style(
        unicode_ok=unicode_ok,
        colors_ok=colors_ok,
        color_mode=base.color_mode if colors_ok else "none",
        wall_pairs=base.wall_pairs if colors_ok else [],
        floor_pairs=base.floor_pairs if colors_ok else [],
        hud_pair=base.hud_pair if colors_ok else 0,
        map_wall_pair=base.map_wall_pair if colors_ok else 0,
        map_floor_pair=base.map_floor_pair if colors_ok else 0,
        map_player_pair=base.map_player_pair if colors_ok else 0,
        map_goal_pair=base.map_goal_pair if colors_ok else 0,
    )


def detect_caps(base_style: Style, mouse_motion_ok: bool) -> Capabilities:
    return Capabilities(
        unicode_ok=base_style.unicode_ok,
        colors_ok=base_style.colors_ok,
        color_mode=base_style.color_mode if base_style.colors_ok else "none",
        mouse_motion_ok=mouse_motion_ok,
    )


def prefer_utf8() -> bool:
    enc = (
        (sys.stdout.encoding or "")
        + "|"
        + locale.getpreferredencoding(False)
        + "|"
        + (os.environ.get("LC_ALL") or "")
        + "|"
        + (os.environ.get("LANG") or "")
    ).upper()
    return ("UTF-8" in enc) or ("UTF8" in enc)


def flat_wall_attr(style: Style) -> int:
    if style.colors_ok and style.wall_pairs:
        return curses.color_pair(style.wall_pairs[0]) | curses.A_BOLD
    return curses.A_BOLD if style.unicode_ok else curses.A_NORMAL


def flat_floor_attr(style: Style) -> int:
    if style.colors_ok and style.floor_pairs:
        if style.color_mode == "256":
            idx = len(style.floor_pairs) // 2
        else:
            idx = 0
        return curses.color_pair(style.floor_pairs[idx])
    return curses.A_NORMAL


def box_chars(unicode_ok: bool):
    if unicode_ok:
        return {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "│"}
    return {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|"}


def draw_box(stdscr, y: int, x: int, h: int, w: int, unicode_ok: bool, attr: int = 0) -> None:
    bc = box_chars(unicode_ok)
    safe_addstr(stdscr, y, x, bc["tl"] + bc["h"] * (w - 2) + bc["tr"], attr)
    for yy in range(y + 1, y + h - 1):
        safe_addstr(stdscr, yy, x, bc["v"], attr)
        safe_addstr(stdscr, yy, x + w - 1, bc["v"], attr)
    safe_addstr(stdscr, y + h - 1, x, bc["bl"] + bc["h"] * (w - 2) + bc["br"], attr)
