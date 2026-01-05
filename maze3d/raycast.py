"""Raycasting and projection helpers."""

from __future__ import annotations

import curses
import math

from .constants import MAX_RAY_DIST, WALL, WALL_HEIGHT
from .maze import is_wall
from .style import Style, flat_floor_attr, flat_wall_attr


def cast_ray(grid: list[str], px: float, py: float, ang: float) -> tuple[float, int]:
    ray_dir_x = math.cos(ang)
    ray_dir_y = math.sin(ang)
    map_x = int(px)
    map_y = int(py)

    delta_dist_x = 1e30 if ray_dir_x == 0 else abs(1.0 / ray_dir_x)
    delta_dist_y = 1e30 if ray_dir_y == 0 else abs(1.0 / ray_dir_y)

    if ray_dir_x < 0:
        step_x = -1
        side_dist_x = (px - map_x) * delta_dist_x
    else:
        step_x = 1
        side_dist_x = (map_x + 1.0 - px) * delta_dist_x

    if ray_dir_y < 0:
        step_y = -1
        side_dist_y = (py - map_y) * delta_dist_y
    else:
        step_y = 1
        side_dist_y = (map_y + 1.0 - py) * delta_dist_y

    max_y = len(grid)
    max_x = len(grid[0])

    side = 0
    while True:
        if side_dist_x < side_dist_y:
            side_dist_x += delta_dist_x
            map_x += step_x
            side = 0
        else:
            side_dist_y += delta_dist_y
            map_y += step_y
            side = 1

        if map_x < 0 or map_x >= max_x or map_y < 0 or map_y >= max_y:
            return MAX_RAY_DIST, side

        if grid[map_y][map_x] == WALL:
            dist = (side_dist_x - delta_dist_x) if side == 0 else (side_dist_y - delta_dist_y)
            return min(max(dist, 0.0), MAX_RAY_DIST), side


def pitch_mid(height: float, pitch: float) -> float:
    return height * 0.5 - pitch * (height / math.pi)


def compute_wall_span(height: int, dist: float, cam_z: float, mid: float) -> tuple[int, int]:
    proj_plane = height * 1.25
    proj = proj_plane / max(0.0001, dist)
    top = int(mid - (WALL_HEIGHT - cam_z) * proj)
    bot = int(mid - (0.0 - cam_z) * proj)
    if top > bot:
        top, bot = bot, top
    return top, bot


def floorcast_sample_row(
    grid: list[str],
    px: float,
    py: float,
    cos_arr: list[float],
    sin_arr: list[float],
    dist_plane: float,
    dist_plane_top: float | None,
    style: Style,
    shadows_on: bool,
) -> tuple[list[bool], str, int, str, int]:
    cols = len(cos_arr)
    hit_top = [False] * cols

    if shadows_on:
        d_floor = min(dist_plane, MAX_RAY_DIST)
        floor_ch = style.floor_char_dist(d_floor)
        floor_attr = style.floor_attr_dist(d_floor) if style.colors_ok else curses.A_NORMAL
        top_ch = floor_ch
        top_attr = floor_attr
    else:
        floor_ch = "·" if style.unicode_ok else "."
        floor_attr = flat_floor_attr(style)
        top_ch = "▓" if style.unicode_ok else "#"
        top_attr = flat_wall_attr(style)

    if dist_plane_top is not None:
        if shadows_on:
            d_top = min(dist_plane_top, MAX_RAY_DIST)
            top_ch = style.wall_char_top(d_top)
            top_attr = style.wall_attr(d_top, 0) if style.colors_ok else curses.A_BOLD
        # compute top hit mask (same in both modes)
        for i in range(cols):
            wx = px + cos_arr[i] * dist_plane_top
            wy = py + sin_arr[i] * dist_plane_top
            if is_wall(grid, int(wx), int(wy)):
                hit_top[i] = True

    return hit_top, floor_ch, floor_attr, top_ch, top_attr
