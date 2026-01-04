# -*- coding: utf-8 -*-
"""Minimap rendering."""
from __future__ import annotations

import curses
import math
from typing import Callable, List, Tuple

from .constants import WALL
from .models import Player, Settings
from .style import Style
from .util import normalize_angle, safe_addstr


def player_dir_glyph(style: Style, ang: float) -> str:
    a = normalize_angle(ang)
    if not style.unicode_ok:
        if -math.pi / 4 <= a < math.pi / 4:
            return ">"
        if math.pi / 4 <= a < 3 * math.pi / 4:
            return "v"
        if -3 * math.pi / 4 <= a < -math.pi / 4:
            return "^"
        return "<"
    if -math.pi / 4 <= a < math.pi / 4:
        return "►"
    if math.pi / 4 <= a < 3 * math.pi / 4:
        return "▼"
    if -3 * math.pi / 4 <= a < -math.pi / 4:
        return "▲"
    return "◄"


def render_map(stdscr, tr: Callable[[str], str], grid: List[str], player: Player, goal_xy: Tuple[int, int], settings: Settings, style: Style) -> None:
    h, w = stdscr.getmaxyx()
    if h < 8 or w < 24:
        stdscr.erase()
        safe_addstr(stdscr, 0, 0, tr("msg_too_small"))
        return

    header_lines = 1
    out_h = max(1, h - header_lines)
    out_w = max(1, w - 1)

    map_h = len(grid)
    map_w = len(grid[0])

    title = tr("map_title")
    hdr_attr = curses.A_REVERSE
    if style.colors_ok and style.hud_pair:
        hdr_attr |= curses.color_pair(style.hud_pair)
    safe_addstr(stdscr, 0, 0, title[: max(0, w - 1)], hdr_attr)

    gx, gy = goal_xy
    px_i = int(player.x)
    py_i = int(player.y)

    wall_attr = curses.A_NORMAL
    floor_attr = curses.A_NORMAL
    player_attr = curses.A_BOLD
    goal_attr = curses.A_BOLD
    if style.colors_ok:
        if style.map_wall_pair:
            wall_attr = curses.color_pair(style.map_wall_pair)
        if style.map_floor_pair:
            floor_attr = curses.color_pair(style.map_floor_pair)
        if style.map_player_pair:
            player_attr = curses.color_pair(style.map_player_pair) | curses.A_BOLD
        if style.map_goal_pair:
            goal_attr = curses.color_pair(style.map_goal_pair) | curses.A_BOLD

    if style.unicode_ok:
        half_rows = out_h * 2
        scale_x = map_w / out_w
        scale_y = map_h / half_rows

        ox_p = int(px_i * out_w / map_w)
        oy_p = (int(py_i * half_rows / map_h)) // 2

        ox_g = int(gx * out_w / map_w)
        oy_g = (int(gy * half_rows / map_h)) // 2

        player_ch = player_dir_glyph(style, player.ang)
        goal_ch = "✚"

        for oy in range(out_h):
            y_top = int((2 * oy) * scale_y)
            y_bot = int((2 * oy + 1) * scale_y)
            if y_top >= map_h:
                break
            if y_bot >= map_h:
                y_bot = map_h - 1

            x = 0
            while x < out_w:
                mx = int(x * scale_x)
                if mx >= map_w:
                    break

                top_wall = grid[y_top][mx] == WALL
                bot_wall = grid[y_bot][mx] == WALL

                if top_wall and bot_wall:
                    ch = "█"; attr = wall_attr
                elif top_wall and not bot_wall:
                    ch = "▀"; attr = wall_attr
                elif not top_wall and bot_wall:
                    ch = "▄"; attr = wall_attr
                else:
                    ch = " " if style.colors_ok else "·"
                    attr = floor_attr if style.colors_ok else curses.A_NORMAL

                if oy == oy_g and x == ox_g:
                    ch = goal_ch; attr = goal_attr
                if oy == oy_p and x == ox_p:
                    ch = player_ch; attr = player_attr

                start = x
                buf = [ch]
                x += 1
                while x < out_w:
                    mx2 = int(x * scale_x)
                    if mx2 >= map_w:
                        break
                    top_wall2 = grid[y_top][mx2] == WALL
                    bot_wall2 = grid[y_bot][mx2] == WALL
                    if top_wall2 and bot_wall2:
                        ch2 = "█"; attr2 = wall_attr
                    elif top_wall2 and not bot_wall2:
                        ch2 = "▀"; attr2 = wall_attr
                    elif not top_wall2 and bot_wall2:
                        ch2 = "▄"; attr2 = wall_attr
                    else:
                        ch2 = " " if style.colors_ok else "·"
                        attr2 = floor_attr if style.colors_ok else curses.A_NORMAL
                    if oy == oy_g and x == ox_g:
                        ch2 = goal_ch; attr2 = goal_attr
                    if oy == oy_p and x == ox_p:
                        ch2 = player_ch; attr2 = player_attr
                    if attr2 != attr:
                        break
                    buf.append(ch2); x += 1
                safe_addstr(stdscr, oy + header_lines, start, "".join(buf), attr)
    else:
        scale_x = map_w / out_w
        scale_y = map_h / out_h
        ox_p = int(px_i * out_w / map_w)
        oy_p = int(py_i * out_h / map_h)
        ox_g = int(gx * out_w / map_w)
        oy_g = int(gy * out_h / map_h)
        player_ch = player_dir_glyph(style, player.ang)
        goal_ch = "X"

        for oy in range(out_h):
            my = int(oy * scale_y)
            if my >= map_h:
                break
            row = []
            for ox in range(out_w):
                mx = int(ox * scale_x)
                if mx >= map_w:
                    row.append(" ")
                    continue
                ch = "#" if grid[my][mx] == WALL else "."
                if ox == ox_g and oy == oy_g:
                    ch = goal_ch
                if ox == ox_p and oy == oy_p:
                    ch = player_ch
                row.append(ch)
            safe_addstr(stdscr, oy + header_lines, 0, "".join(row))
