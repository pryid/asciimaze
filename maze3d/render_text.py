# -*- coding: utf-8 -*-
"""Text-mode renderer (ASCII/Unicode full blocks)."""
from __future__ import annotations

import curses
import math
from typing import Callable, List, Tuple

from .constants import EYE_HEIGHT, WALL_HEIGHT
from .models import Player, Settings
from .raycast import cast_ray, compute_wall_span, floorcast_sample_row, pitch_mid
from .render_common import draw_hud
from .style import Style, flat_floor_attr, flat_wall_attr
from .util import safe_addstr


def render_text(
    stdscr,
    tr: Callable[[str], str],
    grid: List[str],
    player: Player,
    goal_xy: Tuple[int, int],
    settings: Settings,
    style: Style,
    hud_visible: bool,
    mouse_active: bool,
) -> None:
    h, w = stdscr.getmaxyx()
    if h < 8 or w < 24:
        stdscr.erase()
        safe_addstr(stdscr, 0, 0, tr("msg_too_small"))
        return

    shadows_on = settings.shadows == "on"
    wall_ch_flat = "█" if style.unicode_ok else "#"
    floor_ch_flat = "·" if style.unicode_ok else "."
    wall_attr_flat = flat_wall_attr(style)
    floor_attr_flat = flat_floor_attr(style)

    hud_lines = 2 if hud_visible else 0
    view_h = max(1, h - hud_lines)
    view_w = max(1, w - 1)
    fov = settings.fov
    cam_z = player.z + EYE_HEIGHT
    mid = pitch_mid(view_h, player.pitch)

    use_floorcast = cam_z > 0.75 or abs(player.pitch) > 0.25
    proj_plane = view_h * 1.25

    tops = [0] * view_w
    bots = [0] * view_w
    wall_chars = [" "] * view_w
    wall_attrs = [0] * view_w
    cos_arr = [0.0] * view_w
    sin_arr = [0.0] * view_w

    for x in range(view_w):
        ray_ang = player.ang - fov / 2.0 + (x / max(1, view_w - 1)) * fov
        ca = math.cos(ray_ang)
        sa = math.sin(ray_ang)
        cos_arr[x] = ca
        sin_arr[x] = sa

        dist, side = cast_ray(grid, player.x, player.y, ray_ang)
        dist *= max(0.0001, math.cos(ray_ang - player.ang))
        dist = max(0.0001, dist)

        top, bot = compute_wall_span(view_h, dist, cam_z, mid)
        tops[x] = top
        bots[x] = bot

        if shadows_on:
            wall_chars[x] = style.wall_char_text(dist)
            wall_attrs[x] = style.wall_attr(dist, side)
        else:
            wall_chars[x] = wall_ch_flat
            wall_attrs[x] = wall_attr_flat

    for y in range(view_h):
        row_top_mask = None
        floor_ch = floor_ch_flat
        floor_attr = floor_attr_flat
        top_ch = wall_ch_flat
        top_attr = wall_attr_flat

        if use_floorcast:
            den = (y + 0.5) - mid
            if den > 0.0001:
                dist_floor = cam_z * proj_plane / den
                dist_top = None
                if cam_z > WALL_HEIGHT + 0.02:
                    dist_top = (cam_z - WALL_HEIGHT) * proj_plane / den
                    if dist_top <= 0:
                        dist_top = None
                row_top_mask, floor_ch, floor_attr, top_ch, top_attr = floorcast_sample_row(
                    grid,
                    player.x,
                    player.y,
                    cos_arr,
                    sin_arr,
                    dist_floor,
                    dist_top,
                    style,
                    shadows_on,
                )

        x = 0
        while x < view_w:
            if y < tops[x]:
                ch = " "; attr = curses.A_NORMAL
            elif y >= bots[x]:
                if use_floorcast and row_top_mask is not None:
                    if row_top_mask[x]:
                        ch = top_ch; attr = top_attr
                    else:
                        ch = floor_ch; attr = floor_attr
                else:
                    if shadows_on:
                        ch = style.floor_char_grad(y, view_h)
                        attr = style.floor_attr_grad(y, view_h)
                    else:
                        ch = floor_ch_flat
                        attr = floor_attr_flat
            else:
                ch = wall_chars[x]; attr = wall_attrs[x]

            start = x
            buf = [ch]
            x += 1
            while x < view_w:
                if y < tops[x]:
                    ch2 = " "; attr2 = curses.A_NORMAL
                elif y >= bots[x]:
                    if use_floorcast and row_top_mask is not None:
                        if row_top_mask[x]:
                            ch2 = top_ch; attr2 = top_attr
                        else:
                            ch2 = floor_ch; attr2 = floor_attr
                    else:
                        if shadows_on:
                            ch2 = style.floor_char_grad(y, view_h)
                            attr2 = style.floor_attr_grad(y, view_h)
                        else:
                            ch2 = floor_ch_flat
                            attr2 = floor_attr_flat
                else:
                    ch2 = wall_chars[x]; attr2 = wall_attrs[x]
                if attr2 != attr:
                    break
                buf.append(ch2); x += 1
            safe_addstr(stdscr, y, start, "".join(buf), attr)

    if hud_visible:
        draw_hud(stdscr, tr, player, goal_xy, settings, style, mouse_active)

