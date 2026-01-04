# -*- coding: utf-8 -*-
"""Player movement and demo/autosolve logic."""
from __future__ import annotations

import math
from typing import List, Tuple

from .constants import (
    FREE_ACCEL,
    FREE_DAMP,
    FREE_MAX_V,
    MOVE_SPEED,
    ROT_SPEED,
)
from .maze import can_enter_cell, cell_floor_height, is_wall, resolve_floor_collision
from .models import Player
from .util import clamp, normalize_angle

def demo_walk_step(grid: List[str], player: Player, path: List[Tuple[int, int]], idx: int, dt: float) -> int:
    if not path or idx >= len(path) - 1:
        return idx

    cur_cell = (int(player.x), int(player.y))

    while idx + 1 < len(path) and cur_cell == path[idx + 1]:
        idx += 1
        if idx >= len(path) - 1:
            return idx

    nxt = path[idx + 1]
    dx = nxt[0] - cur_cell[0]
    dy = nxt[1] - cur_cell[1]

    if dx > 0:
        desired = 0.0
    elif dx < 0:
        desired = math.pi
    elif dy > 0:
        desired = math.pi / 2.0
    else:
        desired = -math.pi / 2.0

    diff = normalize_angle(desired - player.ang)
    max_rot = ROT_SPEED * dt

    if abs(diff) > 0.07:
        player.ang = normalize_angle(player.ang + clamp(diff, -max_rot, max_rot))
        return idx

    move = MOVE_SPEED * dt
    dxm = math.cos(player.ang) * move
    dym = math.sin(player.ang) * move

    nx = player.x + dxm
    ny = player.y + dym

    if not is_wall(grid, int(nx), int(player.y)):
        player.x = nx
    if not is_wall(grid, int(player.x), int(ny)):
        player.y = ny

    return idx

def update_free_vertical(grid: List[str], player: Player, vert_dir: int, dt: float) -> None:
    if vert_dir > 0:
        player.vz += FREE_ACCEL * dt
    elif vert_dir < 0:
        player.vz -= FREE_ACCEL * dt
    else:
        k = min(1.0, FREE_DAMP * dt)
        player.vz *= (1.0 - k)

    player.vz = clamp(player.vz, -FREE_MAX_V, FREE_MAX_V)
    player.z += player.vz * dt

    resolve_floor_collision(grid, player)


def move_horizontal_default(grid: List[str], player: Player, forward: float, dt: float) -> None:
    move = forward * MOVE_SPEED * dt
    dx = math.cos(player.ang) * move
    dy = math.sin(player.ang) * move
    nx = player.x + dx
    ny = player.y + dy
    if not is_wall(grid, int(nx), int(player.y)):
        player.x = nx
    if not is_wall(grid, int(player.x), int(ny)):
        player.y = ny


def move_horizontal_free(grid: List[str], player: Player, forward: float, dt: float) -> None:
    move = forward * MOVE_SPEED * dt
    dx = math.cos(player.ang) * move
    dy = math.sin(player.ang) * move
    nx = player.x + dx
    ny = player.y + dy
    if can_enter_cell(grid, nx, player.y, player.z):
        player.x = nx
    if can_enter_cell(grid, player.x, ny, player.z):
        player.y = ny
    resolve_floor_collision(grid, player)


def demo_free_step(grid: List[str], player: Player, goal_xy: Tuple[int, int], dt: float) -> None:
    tx = goal_xy[0] + 0.5
    ty = goal_xy[1] + 0.5

    dx = tx - player.x
    dy = ty - player.y
    dist = math.hypot(dx, dy)

    cruise = 1.35
    if dist > 2.0:
        target_z = cruise
    else:
        target_z = cell_floor_height(grid, goal_xy[0], goal_xy[1])

    if player.z < target_z - 0.05:
        vdir = 1
    elif player.z > target_z + 0.05:
        vdir = -1
    else:
        vdir = 0
    update_free_vertical(grid, player, vdir, dt)

    desired = math.atan2(ty - player.y, tx - player.x)
    diff = normalize_angle(desired - player.ang)
    max_rot = ROT_SPEED * dt
    if abs(diff) > 0.01:
        player.ang = normalize_angle(player.ang + clamp(diff, -max_rot, max_rot))

    if abs(diff) < 0.45:
        move_horizontal_free(grid, player, forward=1.0, dt=dt)
