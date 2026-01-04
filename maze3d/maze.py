# -*- coding: utf-8 -*-
"""Maze generation and grid helpers."""
from __future__ import annotations

import random
from collections import deque
from typing import Dict, List, Optional, Tuple

from .constants import OPEN, WALL, WALL_HEIGHT, FREE_MAX_Z
from .models import Player
from .util import clamp

def difficulty_to_size(d: int) -> Tuple[int, int]:
    d = int(clamp(d, 1, 100))
    cw = 8 + int(d * 0.50)
    ch = 8 + int(d * 0.35)
    return cw, ch


def generate_maze(cell_w: int, cell_h: int, rng: random.Random) -> List[str]:
    cell_w = max(2, int(cell_w))
    cell_h = max(2, int(cell_h))
    W = cell_w * 2 + 1
    H = cell_h * 2 + 1
    grid = [[WALL] * W for _ in range(H)]
    visited = [[False] * cell_w for _ in range(cell_h)]

    def cell_to_map(cx: int, cy: int) -> Tuple[int, int]:
        return 2 * cx + 1, 2 * cy + 1

    stack = [(0, 0)]
    visited[0][0] = True
    sx, sy = cell_to_map(0, 0)
    grid[sy][sx] = OPEN

    while stack:
        cx, cy = stack[-1]
        neigh = []
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < cell_w and 0 <= ny < cell_h and not visited[ny][nx]:
                neigh.append((nx, ny))
        if neigh:
            nx, ny = rng.choice(neigh)
            visited[ny][nx] = True
            x1, y1 = cell_to_map(cx, cy)
            x2, y2 = cell_to_map(nx, ny)
            grid[y2][x2] = OPEN
            grid[(y1 + y2) // 2][(x1 + x2) // 2] = OPEN
            stack.append((nx, ny))
        else:
            stack.pop()

    return ["".join(row) for row in grid]


def is_wall(grid: List[str], x: int, y: int) -> bool:
    if y < 0 or y >= len(grid) or x < 0 or x >= len(grid[0]):
        return True
    return grid[y][x] == WALL


def cell_floor_height(grid: List[str], x: int, y: int) -> float:
    if y < 0 or y >= len(grid) or x < 0 or x >= len(grid[0]):
        return WALL_HEIGHT
    return WALL_HEIGHT if grid[y][x] == WALL else 0.0


def can_enter_cell(grid: List[str], x: float, y: float, z_feet: float) -> bool:
    fx = int(x)
    fy = int(y)
    floor = cell_floor_height(grid, fx, fy)
    return z_feet >= floor - 0.01


def resolve_floor_collision(grid: List[str], player: Player) -> None:
    floor = cell_floor_height(grid, int(player.x), int(player.y))
    if player.z < floor:
        player.z = floor
        if player.vz < 0:
            player.vz = 0.0
    if player.z > FREE_MAX_Z:
        player.z = FREE_MAX_Z
        if player.vz > 0:
            player.vz = 0.0

def find_path_cells(grid: List[str], start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
    H = len(grid)
    W = len(grid[0]) if H else 0
    sx, sy = start
    gx, gy = goal
    if not (0 <= sx < W and 0 <= sy < H and 0 <= gx < W and 0 <= gy < H):
        return [start]

    q = deque([start])
    prev: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}

    while q:
        x, y = q.popleft()
        if (x, y) == goal:
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and grid[ny][nx] == OPEN and (nx, ny) not in prev:
                prev[(nx, ny)] = (x, y)
                q.append((nx, ny))

    if goal not in prev:
        return [start]

    path: List[Tuple[int, int]] = []
    cur: Optional[Tuple[int, int]] = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path
