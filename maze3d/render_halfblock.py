"""Half-block renderer."""

from __future__ import annotations

import curses
import math
from collections.abc import Callable

from .constants import EYE_HEIGHT, WALL_HEIGHT
from .models import Player, Settings
from .raycast import cast_ray, compute_wall_span, floorcast_sample_row, pitch_mid
from .render_common import draw_hud
from .style import Style, flat_floor_attr, flat_wall_attr
from .util import safe_addstr


def render_halfblock(
    stdscr,
    tr: Callable[[str], str],
    grid: list[str],
    player: Player,
    goal_xy: tuple[int, int],
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
    wall_attr_flat = flat_wall_attr(style)
    floor_attr_flat = flat_floor_attr(style)
    floor_ch_flat = "·" if style.unicode_ok else "."
    top_ch_flat = "▓" if style.unicode_ok else "#"

    hud_lines = 2 if hud_visible else 0
    view_h = max(1, h - hud_lines)
    view_w = max(1, w - 1)
    fov = settings.fov
    cam_z = player.z + EYE_HEIGHT

    pix_h = view_h * 2
    mid_pix = pitch_mid(pix_h, player.pitch)

    use_floorcast = cam_z > 0.75 or abs(player.pitch) > 0.25
    proj_plane = pix_h * 1.25

    top_pix = [0] * view_w
    bot_pix = [0] * view_w
    attr_col = [0] * view_w
    full_char_col = ["█"] * view_w
    cos_arr = [0.0] * view_w
    sin_arr = [0.0] * view_w

    for x in range(view_w):
        ray_ang = player.ang - fov / 2.0 + (x / max(1, view_w - 1)) * fov
        cos_arr[x] = math.cos(ray_ang)
        sin_arr[x] = math.sin(ray_ang)

        dist, side = cast_ray(grid, player.x, player.y, ray_ang)
        dist *= max(0.0001, math.cos(ray_ang - player.ang))
        dist = max(0.0001, dist)

        tp, bp = compute_wall_span(pix_h, dist, cam_z, mid_pix)
        top_pix[x] = tp
        bot_pix[x] = bp

        if shadows_on:
            attr_col[x] = style.wall_attr(dist, side)
            full_char_col[x] = style.wall_char_text(dist) if not style.colors_ok else "█"
        else:
            attr_col[x] = wall_attr_flat
            full_char_col[x] = "█" if style.unicode_ok else "#"

    for y in range(view_h):
        y_top = 2 * y
        y_bot = y_top + 1

        row_top_mask = None
        floor_ch = floor_ch_flat
        floor_attr = floor_attr_flat
        top_ch = top_ch_flat
        top_attr = wall_attr_flat

        if use_floorcast:
            den = (y_bot + 0.5) - mid_pix
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

            def cell(
                xi: int,
                *,
                y=y,
                y_top=y_top,
                y_bot=y_bot,
                row_top_mask=row_top_mask,
                floor_ch=floor_ch,
                floor_attr=floor_attr,
                top_ch=top_ch,
                top_attr=top_attr,
            ) -> tuple[str, int]:
                tp = top_pix[xi]
                bp = bot_pix[xi]

                top_on = tp <= y_top < bp
                bot_on = tp <= y_bot < bp
                if top_on and bot_on:
                    return full_char_col[xi], attr_col[xi]
                if top_on and not bot_on:
                    return ("▀" if style.unicode_ok else full_char_col[xi]), attr_col[xi]
                if not top_on and bot_on:
                    return ("▄" if style.unicode_ok else full_char_col[xi]), attr_col[xi]

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
                buf.append(ch2)
                x += 1
            safe_addstr(stdscr, y, start, "".join(buf), attr)

    if hud_visible:
        draw_hud(stdscr, tr, player, goal_xy, settings, style, mouse_active)
