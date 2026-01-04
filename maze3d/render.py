# -*- coding: utf-8 -*-
"""Rendering (raycast view + minimap) for text / half-block / braille modes."""
from __future__ import annotations

import curses
import math
from typing import Callable, List, Optional, Tuple

from .constants import EYE_HEIGHT, WALL_HEIGHT, WALL, RenderMode
from .i18n import option_display
from .models import Player, Settings
from .raycast import cast_ray, compute_wall_span, floorcast_sample_row, pitch_mid
from .style import Style, flat_floor_attr, flat_wall_attr
from .util import safe_addstr, normalize_angle

def choose_renderer(settings: Settings, style: Style) -> RenderMode:
    if settings.render_mode != "auto":
        if settings.render_mode in ("half", "braille") and not style.unicode_ok:
            return "text"
        return settings.render_mode
    return "braille" if style.unicode_ok else "text"

def draw_hud(stdscr, tr: Callable[[str], str], player: Player, goal_xy: Tuple[int, int], settings: Settings, style: Style, mouse_active: bool) -> None:
    h, w = stdscr.getmaxyx()

    gx, gy = goal_xy
    dist_goal = math.hypot((gx + 0.5) - player.x, (gy + 0.5) - player.y)

    is_free = settings.mode in ("free", "demo_free")
    line1 = tr("hud_line1_free") if is_free else tr("hud_line1_default")

    tags = []
    tags.append(tr("tag_utf8") if style.unicode_ok else tr("tag_ascii"))
    if style.colors_ok and style.color_mode == "256":
        tags.append(tr("cap_color_256"))
    elif style.colors_ok:
        tags.append(tr("tag_color"))
    else:
        tags.append(tr("tag_mono"))
    if mouse_active:
        tags.append(tr("tag_mouse"))
    if settings.mode in ("demo_default", "demo_free"):
        tags.append(tr("tag_demo"))
    if is_free:
        tags.append(tr("tag_free"))
    if settings.shadows == "off":
        tags.append(tr("tag_noshadow"))

    tag_str = "+".join(tags)
    render_disp = option_display(tr, "render_mode", settings.render_mode)
    mode_disp = option_display(tr, "mode", settings.mode)

    line2 = tr(
        "hud_line2",
        mode=mode_disp,
        diff=settings.difficulty,
        dist=dist_goal,
        fov=settings.fov * 180.0 / math.pi,
        render=render_disp,
        tags=tag_str,
    )

    attr = curses.A_BOLD
    if style.colors_ok and style.hud_pair:
        attr |= curses.color_pair(style.hud_pair)
    safe_addstr(stdscr, h - 2, 0, line1[: max(0, w - 1)], attr)
    safe_addstr(stdscr, h - 1, 0, line2[: max(0, w - 1)], attr)

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

def render_halfblock(
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
            def cell(xi: int) -> Tuple[str, int]:
                tp = top_pix[xi]; bp = bot_pix[xi]
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
                buf.append(ch2); x += 1
            safe_addstr(stdscr, y, start, "".join(buf), attr)

    if hud_visible:
        draw_hud(stdscr, tr, player, goal_xy, settings, style, mouse_active)

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

def render_scene(
    stdscr,
    tr: Callable[[str], str],
    renderer: RenderMode,
    grid: List[str],
    player: Player,
    goal_xy: Tuple[int, int],
    settings: Settings,
    style: Style,
    hud_visible: bool,
    mouse_active: bool,
) -> None:
    if renderer == "text":
        render_text(stdscr, tr, grid, player, goal_xy, settings, style, hud_visible, mouse_active)
    elif renderer == "half":
        render_halfblock(stdscr, tr, grid, player, goal_xy, settings, style, hud_visible, mouse_active)
    elif renderer == "braille":
        render_braille(stdscr, tr, grid, player, goal_xy, settings, style, hud_visible, mouse_active)
    else:
        render_text(stdscr, tr, grid, player, goal_xy, settings, style, hud_visible, mouse_active)

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
