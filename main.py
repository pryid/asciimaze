#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D лабиринт в терминале (псевдо‑3D raycasting).

Требования:
- Работает в терминале, адаптируется к размеру окна (включая resize).
- Совместимо с fish (это просто Python-скрипт).
- Управление: W/S — вперед/назад, A/D — поворот, M — 2D карта сверху, Q — выход (с подтверждением Y/N).
- Лабиринт генерируется случайно каждый запуск и гарантированно проходим.
- Перед стартом спрашивает сложность 1..100.

Запуск:
  python3 maze3d.py
или:
  chmod +x maze3d.py && ./maze3d.py
"""

from __future__ import annotations

import curses
import math
import random
import time
from dataclasses import dataclass
from typing import List, Tuple


WALL = "#"
OPEN = " "

FOV = math.pi / 3.0          # 60°
MAX_RAY_DIST = 40.0          # дальность лучей (эффект «тумана»)
MOVE_SPEED = 3.2             # клеток/сек (в координатах карты)
ROT_SPEED = 2.2              # рад/сек
HOLD_TIMEOUT = 0.14          # сек — «удержание» по автоповтору клавиш

WALL_SHADES = "@%#*+=-:."    # ближе -> левее (темнее)
FLOOR_SHADES = ".,-~:;=!*#$@"


@dataclass
class Player:
    x: float
    y: float
    ang: float


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def normalize_angle(a: float) -> float:
    while a < -math.pi:
        a += 2 * math.pi
    while a > math.pi:
        a -= 2 * math.pi
    return a


def generate_maze(cell_w: int, cell_h: int, rng: random.Random) -> List[str]:
    """
    Генерация идеального лабиринта DFS (perfect maze).
    Гарантированно проходим (между любыми двумя клетками есть путь).
    Карта в «символьной» сетке: (2*cell_h+1) x (2*cell_w+1).
    """
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
            grid[(y1 + y2) // 2][(x1 + x2) // 2] = OPEN  # ломаем стену между клетками

            stack.append((nx, ny))
        else:
            stack.pop()

    return ["".join(row) for row in grid]


def is_wall(grid: List[str], x: int, y: int) -> bool:
    if y < 0 or y >= len(grid) or x < 0 or x >= len(grid[0]):
        return True
    return grid[y][x] == WALL


def cast_ray(grid: List[str], px: float, py: float, ang: float) -> Tuple[float, int]:
    """
    DDA‑рейкаст: (distance_along_ray, side),
    side=0 — удар о вертикальную грань, side=1 — о горизонтальную.
    """
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
            if dist < 0:
                dist = 0.0
            return min(dist, MAX_RAY_DIST), side


def player_dir_glyph(ang: float) -> str:
    a = normalize_angle(ang)
    if -math.pi / 4 <= a < math.pi / 4:
        return ">"
    if math.pi / 4 <= a < 3 * math.pi / 4:
        return "v"
    if -3 * math.pi / 4 <= a < -math.pi / 4:
        return "^"
    return "<"


def wall_glyph(dist: float, side: int) -> str:
    t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
    idx = int(t * (len(WALL_SHADES) - 1))
    if side == 1:
        idx = min(idx + 1, len(WALL_SHADES) - 1)  # чуть светлее для контраста
    return WALL_SHADES[idx]


def floor_glyph(y: int, h: int) -> str:
    if h <= 1:
        return FLOOR_SHADES[-1]
    t = clamp(y / (h - 1), 0.0, 1.0)
    idx = int(t * (len(FLOOR_SHADES) - 1))
    return FLOOR_SHADES[idx]


def confirm_exit(stdscr) -> bool:
    """Спрашивает Y/N внизу экрана. True => выходим."""
    h, w = stdscr.getmaxyx()
    prompt = "Выйти из игры? Y/N "
    stdscr.addstr(h - 1, 0, prompt[: max(0, w - 1)])
    stdscr.clrtoeol()
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


def render_3d(stdscr, grid: List[str], player: Player, goal_xy: Tuple[int, int], difficulty: int) -> None:
    h, w = stdscr.getmaxyx()
    if h < 10 or w < 30:
        stdscr.erase()
        msg = "Окно слишком маленькое. Увеличьте терминал."
        stdscr.addstr(0, 0, msg[: max(0, w - 1)])
        return

    hud_lines = 2
    view_h = h - hud_lines
    view_w = w

    dists = [0.0] * view_w
    sides = [0] * view_w

    for x in range(view_w):
        ray_ang = player.ang - FOV / 2.0 + (x / max(1, view_w - 1)) * FOV
        dist, side = cast_ray(grid, player.x, player.y, ray_ang)

        # fish‑eye fix: проекция на направление взгляда
        dist *= max(0.0001, math.cos(ray_ang - player.ang))

        dists[x] = max(0.0001, dist)
        sides[x] = side

    for y in range(view_h):
        row_chars = []
        for x in range(view_w):
            dist = dists[x]
            wall_h = int(view_h * 1.25 / dist)
            top = (view_h - wall_h) // 2
            bot = top + wall_h

            if y < top:
                row_chars.append(" ")
            elif y >= bot:
                floor_y = y - view_h // 2
                row_chars.append(floor_glyph(floor_y, max(2, view_h // 2)))
            else:
                row_chars.append(wall_glyph(dist, sides[x]))

        stdscr.addstr(y, 0, "".join(row_chars)[: max(0, view_w - 1)])

    gx, gy = goal_xy
    goal_cx = gx + 0.5
    goal_cy = gy + 0.5
    dist_goal = math.hypot(goal_cx - player.x, goal_cy - player.y)

    line1 = "W/S:движение  A/D:поворот  M:карта  Q:выход"
    line2 = f"Сложность:{difficulty:3d}  До выхода:{dist_goal:6.1f}"
    stdscr.addstr(view_h, 0, line1[: max(0, view_w - 1)])
    stdscr.addstr(view_h + 1, 0, line2[: max(0, view_w - 1)])


def render_map(stdscr, grid: List[str], player: Player, goal_xy: Tuple[int, int], difficulty: int) -> None:
    h, w = stdscr.getmaxyx()
    if h < 10 or w < 30:
        stdscr.erase()
        msg = "Окно слишком маленькое. Увеличьте терминал."
        stdscr.addstr(0, 0, msg[: max(0, w - 1)])
        return

    hud_lines = 2
    view_h = h - hud_lines
    view_w = w

    map_h = len(grid)
    map_w = len(grid[0])

    px_i = int(player.x)
    py_i = int(player.y)

    start_x = int(clamp(px_i - view_w // 2, 0, max(0, map_w - view_w)))
    start_y = int(clamp(py_i - view_h // 2, 0, max(0, map_h - view_h)))

    gx, gy = goal_xy

    for sy in range(view_h):
        my = start_y + sy
        if my >= map_h:
            break

        segment = grid[my][start_x : start_x + view_w]
        row = ["." if ch == OPEN else "#" for ch in segment]

        if my == gy and start_x <= gx < start_x + view_w:
            row[gx - start_x] = "X"

        if my == py_i and start_x <= px_i < start_x + view_w:
            row[px_i - start_x] = player_dir_glyph(player.ang)

        stdscr.addstr(sy, 0, "".join(row)[: max(0, view_w - 1)])

    line1 = "КАРТА (M — назад). W/S:движение  A/D:поворот  Q:выход"
    line2 = f"Сложность:{difficulty:3d}  Выход:X  Игрок:{player_dir_glyph(player.ang)}"
    stdscr.addstr(view_h, 0, line1[: max(0, view_w - 1)])
    stdscr.addstr(view_h + 1, 0, line2[: max(0, view_w - 1)])


def win_screen(stdscr, seconds: float) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    msg1 = "Вы нашли выход!"
    msg2 = f"Время: {seconds:.1f} c"
    msg3 = "Нажмите любую клавишу…"

    y = h // 2
    for i, msg in enumerate((msg1, msg2, msg3)):
        x = max(0, (w - len(msg)) // 2)
        if 0 <= y + i < h:
            stdscr.addstr(y + i, x, msg[: max(0, w - x - 1)])

    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()


def main_curses(stdscr, grid: List[str], difficulty: int, goal_xy: Tuple[int, int]) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    curses.noecho()
    curses.cbreak()

    player = Player(x=1.5, y=1.5, ang=0.0)
    show_map = False

    start_time = time.monotonic()
    last = start_time

    move_dir = 0        # -1 назад, +1 вперед
    rot_dir = 0         # -1 влево, +1 вправо
    move_until = 0.0
    rot_until = 0.0

    old_h, old_w = stdscr.getmaxyx()

    while True:
        now = time.monotonic()
        dt = now - last
        last = now

        new_h, new_w = stdscr.getmaxyx()
        if (new_h, new_w) != (old_h, old_w):
            try:
                curses.resize_term(new_h, new_w)
            except Exception:
                pass
            old_h, old_w = new_h, new_w

        while True:
            ch = stdscr.getch()
            if ch == -1:
                break

            if ch in (ord("m"), ord("M")):
                show_map = not show_map
                continue

            if ch in (ord("q"), ord("Q")):
                if confirm_exit(stdscr):
                    return
                continue

            if ch in (ord("w"), ord("W")):
                move_dir = 1
                move_until = now + HOLD_TIMEOUT
            elif ch in (ord("s"), ord("S")):
                move_dir = -1
                move_until = now + HOLD_TIMEOUT
            elif ch in (ord("a"), ord("A")):
                rot_dir = -1
                rot_until = now + HOLD_TIMEOUT
            elif ch in (ord("d"), ord("D")):
                rot_dir = 1
                rot_until = now + HOLD_TIMEOUT

        if now > move_until:
            move_dir = 0
        if now > rot_until:
            rot_dir = 0

        if rot_dir != 0:
            player.ang = normalize_angle(player.ang + rot_dir * ROT_SPEED * dt)

        if move_dir != 0:
            move = move_dir * MOVE_SPEED * dt
            dx = math.cos(player.ang) * move
            dy = math.sin(player.ang) * move

            nx = player.x + dx
            ny = player.y + dy

            if not is_wall(grid, int(nx), int(player.y)):
                player.x = nx
            if not is_wall(grid, int(player.x), int(ny)):
                player.y = ny

        gx, gy = goal_xy
        if int(player.x) == gx and int(player.y) == gy:
            win_screen(stdscr, time.monotonic() - start_time)
            return

        stdscr.erase()
        if show_map:
            render_map(stdscr, grid, player, goal_xy, difficulty)
        else:
            render_3d(stdscr, grid, player, goal_xy, difficulty)
        stdscr.refresh()

        time.sleep(0.01)


def ask_difficulty() -> int:
    while True:
        try:
            raw = input("Выберите сложность (1..100): ").strip()
            d = int(raw)
        except (ValueError, EOFError, KeyboardInterrupt):
            print()
            continue
        if 1 <= d <= 100:
            return d
        print("Нужно число от 1 до 100.")


def difficulty_to_size(d: int) -> Tuple[int, int]:
    """
    Размер в «клетках» (потом будет 2* + 1 в символах).
    1  -> ~8x8
    100-> ~58x43
    """
    cw = 8 + int(d * 0.50)
    ch = 8 + int(d * 0.35)
    return cw, ch


def run() -> None:
    d = ask_difficulty()

    rng = random.Random()      # каждый запуск новый лабиринт
    cw, ch = difficulty_to_size(d)
    grid = generate_maze(cw, ch, rng)

    goal_x = 2 * (cw - 1) + 1
    goal_y = 2 * (ch - 1) + 1

    curses.wrapper(lambda stdscr: main_curses(stdscr, grid, d, (goal_x, goal_y)))


if __name__ == "__main__":
    run()
