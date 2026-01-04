# -*- coding: utf-8 -*-
"""Braille renderer (high resolution using Unicode braille cells)."""
from __future__ import annotations

import curses
import math
from typing import Callable, List, Tuple

from .constants import EYE_HEIGHT, WALL_HEIGHT
from .models import Player, Settings
from .raycast import cast_ray, compute_wall_span, floorcast_sample_row, pitch_mid
from .render_common import draw_hud
from .render_text import render_text
from .style import Style, flat_floor_attr, flat_wall_attr
from .util import safe_addstr

_BRAILLE_BITS = {
    (0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (0, 3): 0x40,
    (1, 0): 0x08, (1, 1): 0x10, (1, 2): 0x20, (1, 3): 0x80,
}


def render_braille(
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
    if not style.unicode_ok:
        render_text(stdscr, tr, grid, player, goal_xy, settings, style, hud_visible, mouse_active)
        return

    h, w = stdscr.getmaxyx()
    if h < 8 or w < 24:
        stdscr.erase()
        safe_addstr(stdscr, 0, 0, tr("msg_too_small"))
        return

    shadows_on = settings.shadows == "on"
    wall_attr_flat = flat_wall_attr(style)
    floor_attr_flat = flat_floor_attr(style)
    floor_ch_flat = "·"

    hud_lines = 2 if hud_visible else 0
    view_h = max(1, h - hud_lines)
    view_w = max(1, w - 1)
    fov = settings.fov
    cam_z = player.z + EYE_HEIGHT

    sub_w = view_w * 2
    pix_h = view_h * 4
    mid_pix = pitch_mid(pix_h, player.pitch)

    use_floorcast = cam_z > 0.75 or abs(player.pitch) > 0.25
    proj_plane = pix_h * 1.25

    dist_sub = [0.0] * sub_w
    side_sub = [0] * sub_w
    top_p = [0] * sub_w
    bot_p = [0] * sub_w
    cos_col = [0.0] * view_w
    sin_col = [0.0] * view_w

    for x in range(view_w):
        ray_ang = player.ang - fov / 2.0 + (x / max(1, view_w - 1)) * fov
        cos_col[x] = math.cos(ray_ang)
        sin_col[x] = math.sin(ray_ang)

    for sx in range(sub_w):
        ray_ang = player.ang - fov / 2.0 + (sx / max(1, sub_w - 1)) * fov
        dist, side = cast_ray(grid, player.x, player.y, ray_ang)
        dist *= max(0.0001, math.cos(ray_ang - player.ang))
        dist = max(0.0001, dist)

        dist_sub[sx] = dist
        side_sub[sx] = side

        tp, bp = compute_wall_span(pix_h, dist, cam_z, mid_pix)
        top_p[sx] = tp
        bot_p[sx] = bp

    for y in range(view_h):
        row_top_mask = None
        floor_ch = floor_ch_flat
        floor_attr = floor_attr_flat
        top_ch = "▓"
        top_attr = wall_attr_flat

        if use_floorcast:
            py = y * 4 + 2
            den = (py + 0.5) - mid_pix
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
                    cos_col,
                    sin_col,
                    dist_floor,
                    dist_top,
                    style,
                    shadows_on,
                )

        x = 0
        while x < view_w:
            def cell(xi: int) -> Tuple[str, int]:
                bits = 0
                for sub_col in (0, 1):
                    sx = 2 * xi + sub_col
                    tp = top_p[sx]; bp = bot_p[sx]
                    base_y = 4 * y
                    for sub_row in range(4):
                        py = base_y + sub_row
                        if tp <= py < bp:
                            bits |= _BRAILLE_BITS[(sub_col, sub_row)]
                if bits:
                    sx0 = 2 * xi
                    sx1 = sx0 + 1
                    if dist_sub[sx0] <= dist_sub[sx1]:
                        d = dist_sub[sx0]; side = side_sub[sx0]
                    else:
                        d = dist_sub[sx1]; side = side_sub[sx1]
                    attr = style.wall_attr(d, side) if shadows_on else wall_attr_flat
                    return chr(0x2800 + bits), attr

                if use_floorcast and row_top_mask is not None:
                    if row_top_mask[xi]:
                        return top_ch, top_attr
                    return floor_ch, floor_attr

                if y < view_h // 2:
                    return " ", curses.A_NORMAL

                if shadows_on:
                    return style.floor_char_grad(y, view_h), style.floor_attr_grad(y, view_h)
                return floor_ch_flat, floor_attr_flat

            ch, attr = cell(x)
            start = x
            buf = [ch]
            x += 1
            while x < view_w:
                ch2, attr2 = cell(x)
                if attr2 != attr:
                    break
                buf.append(ch2); x += 1
            safe_addstr(stdscr, y, start, "".join(buf), attr)

    if hud_visible:
        draw_hud(stdscr, tr, player, goal_xy, settings, style, mouse_active)

