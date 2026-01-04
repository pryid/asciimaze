#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D лабиринт в терминале (псевдо‑3D raycasting) — улучшенная версия.

Фишки:
- Авто-детект UTF-8 и цветов (8/16/256). Если доступно — Unicode-блоки и цветовые градиенты.
- HUD показывается первые 5 секунд, потом скрывается. ESC — показать/скрыть HUD.
- M — полноэкранная 2D карта сверху (авто-масштабирование, читабельные символы).
- Q — выход с подтверждением Y/N.
- Лабиринт генерируется случайно каждый запуск и гарантированно проходим (perfect maze).
- Перед стартом спрашивает сложность 1..100.
- Опционально: поворот "головой" мышью/тачпадом через terminal mouse tracking, если терминал поддерживает REPORT_MOUSE_POSITION.

Запуск:
  python3 maze3d.py
"""

from __future__ import annotations

import curses
import locale
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional


WALL = "#"
OPEN = " "

FOV = math.pi / 3.0          # 60°
MAX_RAY_DIST = 40.0          # дальность лучей
MOVE_SPEED = 3.2             # клеток/сек
ROT_SPEED = 2.2              # рад/сек
HOLD_TIMEOUT = 0.14          # сек — «удержание» по автоповтору клавиш
MOUSE_SENS = 0.012           # рад на 1 "колонку" движения мыши

# ASCII (совместимость)
ASCII_WALL_SHADES = "@%#*+=-:."
ASCII_FLOOR_SHADES = ".,-~:;=!*#$@"


@dataclass
class Player:
    x: float
    y: float
    ang: float


@dataclass
class Style:
    unicode_ok: bool
    colors_ok: bool
    color_mode: str  # "none" | "basic" | "256"
    wall_chars: str
    floor_chars: str
    # цветовые пары/атрибуты
    wall_pairs: List[int]
    floor_pairs: List[int]
    map_wall_pair: int
    map_floor_pair: int
    map_player_pair: int
    map_goal_pair: int
    hud_pair: int

    def wall_attr(self, dist: float, side: int) -> int:
        if not self.colors_ok or not self.wall_pairs:
            return curses.A_NORMAL

        t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
        idx = int(t * (len(self.wall_pairs) - 1))
        pair = self.wall_pairs[idx]

        attr = curses.color_pair(pair)
        # немного "объёма": одна сторона чуть темнее
        if side == 1:
            attr |= curses.A_DIM
        # ближние стены — чуть жирнее
        if dist < 3.5:
            attr |= curses.A_BOLD
        return attr

    def wall_char(self, dist: float) -> str:
        # Больше различий даём через цвет; символ — дополнительно.
        if not self.unicode_ok:
            t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
            idx = int(t * (len(ASCII_WALL_SHADES) - 1))
            return ASCII_WALL_SHADES[idx]
        # Unicode: ближе — более "плотный" блок
        if dist < 2.5:
            return "█"
        if dist < 5.5:
            return "▓"
        if dist < 10.0:
            return "▒"
        return "░"

    def floor_attr(self, y: int, view_h: int) -> int:
        if not self.colors_ok or not self.floor_pairs:
            return curses.A_NORMAL
        # y ниже середины => пол (градиент по вертикали)
        t = clamp((y - view_h * 0.5) / max(1.0, view_h * 0.5), 0.0, 1.0)
        idx = int(t * (len(self.floor_pairs) - 1))
        return curses.color_pair(self.floor_pairs[idx])

    def floor_char(self, y: int, view_h: int) -> str:
        if not self.unicode_ok:
            t = clamp((y - view_h * 0.5) / max(1.0, view_h * 0.5), 0.0, 1.0)
            idx = int(t * (len(ASCII_FLOOR_SHADES) - 1))
            return ASCII_FLOOR_SHADES[idx]
        # Unicode "зерно" пола
        t = clamp((y - view_h * 0.5) / max(1.0, view_h * 0.5), 0.0, 1.0)
        idx = int(t * (len(self.floor_chars) - 1))
        return self.floor_chars[idx]


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def normalize_angle(a: float) -> float:
    while a < -math.pi:
        a += 2 * math.pi
    while a > math.pi:
        a -= 2 * math.pi
    return a


def prefer_utf8() -> bool:
    enc = (
        (sys.stdout.encoding or "") +
        "|" + locale.getpreferredencoding(False) +
        "|" + (os.environ.get("LC_ALL") or "") +
        "|" + (os.environ.get("LANG") or "")
    ).upper()
    return ("UTF-8" in enc) or ("UTF8" in enc)


def init_style(stdscr) -> Style:
    """
    Определяем: есть ли UTF-8 и цвета (и сколько).
    Создаём цветовые пары под градиенты.
    """
    unicode_ok = prefer_utf8()

    colors_ok = False
    color_mode = "none"

    wall_pairs: List[int] = []
    floor_pairs: List[int] = []
    map_wall_pair = 0
    map_floor_pair = 0
    map_player_pair = 0
    map_goal_pair = 0
    hud_pair = 0

    wall_chars = "█▓▒░"
    floor_chars = "·⋅∘°ˑ"  # аккуратные одноширинные точки

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
        bg = -1  # default

        if color_mode == "256":
            # Градации серого (232..255) — near bright, far dark
            wall_colors = list(range(255, 231, -1))  # 24
            # Пол чуть темнее: 244..236
            floor_colors = list(range(244, 235, -1))  # 9

            max_wall = min(len(wall_colors), max(0, pairs - 10))
            for i in range(max_wall):
                if safe_init_pair(pid, wall_colors[i], bg):
                    wall_pairs.append(pid)
                    pid += 1

            max_floor = min(len(floor_colors), max(0, pairs - pid - 10))
            for i in range(max_floor):
                if safe_init_pair(pid, floor_colors[i], bg):
                    floor_pairs.append(pid)
                    pid += 1

            # специальные пары
            if safe_init_pair(pid, 15, bg):   # HUD — белый
                hud_pair = pid
                pid += 1
            if safe_init_pair(pid, 250, bg):  # карта: стены
                map_wall_pair = pid
                pid += 1
            if safe_init_pair(pid, 238, bg):  # карта: фон/проходы (если рисуются точками)
                map_floor_pair = pid
                pid += 1
            if safe_init_pair(pid, 226, bg):  # игрок — yellow
                map_player_pair = pid
                pid += 1
            if safe_init_pair(pid, 46, bg):   # выход — green
                map_goal_pair = pid
                pid += 1

        else:
            # 8/16 цветов: несколько ступеней
            wall_colors = [curses.COLOR_WHITE, curses.COLOR_CYAN, curses.COLOR_BLUE]
            floor_colors = [curses.COLOR_YELLOW, curses.COLOR_MAGENTA, curses.COLOR_RED]

            for fg in wall_colors:
                if pid < pairs and safe_init_pair(pid, fg, bg):
                    wall_pairs.append(pid)
                    pid += 1
            for fg in floor_colors:
                if pid < pairs and safe_init_pair(pid, fg, bg):
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
        wall_chars=wall_chars,
        floor_chars=floor_chars,
        wall_pairs=wall_pairs,
        floor_pairs=floor_pairs,
        map_wall_pair=map_wall_pair,
        map_floor_pair=map_floor_pair,
        map_player_pair=map_player_pair,
        map_goal_pair=map_goal_pair,
        hud_pair=hud_pair,
    )


def generate_maze(cell_w: int, cell_h: int, rng: random.Random) -> List[str]:
    """
    Perfect maze через DFS (гарантированно проходим).
    Итоговая карта: (2*cell_h+1) x (2*cell_w+1).
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
            grid[(y1 + y2) // 2][(x1 + x2) // 2] = OPEN
            stack.append((nx, ny))
        else:
            stack.pop()

    return ["".join(row) for row in grid]


def is_wall(grid: List[str], x: int, y: int) -> bool:
    if y < 0 or y >= len(grid) or x < 0 or x >= len(grid[0]):
        return True
    return grid[y][x] == WALL


def cast_ray(grid: List[str], px: float, py: float, ang: float) -> Tuple[float, int]:
    """DDA raycast: (dist, side). side=0 vertical, side=1 horizontal."""
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


def safe_addstr(stdscr, y: int, x: int, s: str, attr: int = 0) -> None:
    try:
        stdscr.addstr(y, x, s, attr)
    except curses.error:
        pass


def confirm_exit(stdscr) -> bool:
    """Спрашивает Y/N снизу экрана. True => выходим."""
    h, w = stdscr.getmaxyx()
    prompt = "Выйти из игры? Y/N "
    safe_addstr(stdscr, h - 1, 0, prompt[: max(0, w - 1)])
    try:
        stdscr.clrtoeol()
    except curses.error:
        pass
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


def render_3d(
    stdscr,
    grid: List[str],
    player: Player,
    goal_xy: Tuple[int, int],
    difficulty: int,
    style: Style,
    hud_visible: bool,
    mouse_enabled: bool,
) -> None:
    h, w = stdscr.getmaxyx()
    if h < 8 or w < 24:
        stdscr.erase()
        safe_addstr(stdscr, 0, 0, "Окно слишком маленькое. Увеличьте терминал.")
        return

    hud_lines = 2 if hud_visible else 0
    view_h = max(1, h - hud_lines)
    view_w = max(1, w - 1)  # не пишем в самый последний столбец

    dists = [0.0] * view_w
    sides = [0] * view_w
    tops = [0] * view_w
    bots = [0] * view_w
    wall_chars = [" "] * view_w
    wall_attrs = [0] * view_w

    for x in range(view_w):
        ray_ang = player.ang - FOV / 2.0 + (x / max(1, view_w - 1)) * FOV
        dist, side = cast_ray(grid, player.x, player.y, ray_ang)

        dist *= max(0.0001, math.cos(ray_ang - player.ang))  # fish-eye fix
        dist = max(0.0001, dist)

        dists[x] = dist
        sides[x] = side

        wall_h = int(view_h * 1.25 / dist)
        top = (view_h - wall_h) // 2
        bot = top + wall_h
        tops[x] = top
        bots[x] = bot

        wall_chars[x] = style.wall_char(dist)
        wall_attrs[x] = style.wall_attr(dist, side)

    for y in range(view_h):
        x = 0
        while x < view_w:
            if y < tops[x]:
                ch = " "
                attr = curses.A_NORMAL
            elif y >= bots[x]:
                ch = style.floor_char(y, view_h)
                attr = style.floor_attr(y, view_h)
            else:
                ch = wall_chars[x]
                attr = wall_attrs[x]

            start = x
            buf = [ch]
            x += 1

            while x < view_w:
                if y < tops[x]:
                    ch2 = " "
                    attr2 = curses.A_NORMAL
                elif y >= bots[x]:
                    ch2 = style.floor_char(y, view_h)
                    attr2 = style.floor_attr(y, view_h)
                else:
                    ch2 = wall_chars[x]
                    attr2 = wall_attrs[x]

                if attr2 != attr:
                    break
                buf.append(ch2)
                x += 1

            safe_addstr(stdscr, y, start, "".join(buf), attr)

    if hud_visible and hud_lines >= 2:
        gx, gy = goal_xy
        dist_goal = math.hypot((gx + 0.5) - player.x, (gy + 0.5) - player.y)

        mode_parts = []
        mode_parts.append("UTF-8" if style.unicode_ok else "ASCII")
        if style.colors_ok:
            mode_parts.append("256c" if style.color_mode == "256" else "color")
        else:
            mode_parts.append("mono")
        if mouse_enabled:
            mode_parts.append("mouse")
        mode = "+".join(mode_parts)

        line1 = "W/S:движение  A/D:поворот  M:карта  ESC:HUD  Q:выход"
        line2 = f"Сложность:{difficulty:3d}  До выхода:{dist_goal:6.1f}  Режим:{mode}"

        hud_attr = (
            (curses.color_pair(style.hud_pair) | curses.A_BOLD)
            if style.colors_ok and style.hud_pair
            else curses.A_BOLD
        )
        safe_addstr(stdscr, h - 2, 0, line1[: max(0, w - 1)], hud_attr)
        safe_addstr(stdscr, h - 1, 0, line2[: max(0, w - 1)], hud_attr)


def render_map(
    stdscr,
    grid: List[str],
    player: Player,
    goal_xy: Tuple[int, int],
    difficulty: int,
    style: Style,
) -> None:
    h, w = stdscr.getmaxyx()
    if h < 8 or w < 24:
        stdscr.erase()
        safe_addstr(stdscr, 0, 0, "Окно слишком маленькое. Увеличьте терминал.")
        return

    header_lines = 1
    out_h = max(1, h - header_lines)
    out_w = max(1, w - 1)

    map_h = len(grid)
    map_w = len(grid[0])

    title = "КАРТА — M:назад  W/S:шаг  A/D:поворот  Q:выход"
    hdr_attr = curses.A_REVERSE | (
        curses.color_pair(style.hud_pair) if style.colors_ok and style.hud_pair else 0
    )
    safe_addstr(stdscr, 0, 0, title[: max(0, w - 1)], hdr_attr)

    use_halfblocks = style.unicode_ok

    gx, gy = goal_xy
    px_i = int(player.x)
    py_i = int(player.y)

    if use_halfblocks:
        half_rows = out_h * 2
        scale_x = map_w / out_w
        scale_y = map_h / half_rows

        ox_p = int(px_i * out_w / map_w)
        hy_p = int(py_i * half_rows / map_h)
        oy_p = hy_p // 2

        ox_g = int(gx * out_w / map_w)
        hy_g = int(gy * half_rows / map_h)
        oy_g = hy_g // 2

        player_ch = player_dir_glyph(style, player.ang)
        goal_ch = "✚" if style.unicode_ok else "X"

        wall_attr = (
            curses.color_pair(style.map_wall_pair) if style.colors_ok and style.map_wall_pair else curses.A_NORMAL
        )
        floor_attr = (
            curses.color_pair(style.map_floor_pair) if style.colors_ok and style.map_floor_pair else curses.A_NORMAL
        )
        player_attr = (
            (curses.color_pair(style.map_player_pair) | curses.A_BOLD)
            if style.colors_ok and style.map_player_pair else curses.A_BOLD
        )
        goal_attr = (
            (curses.color_pair(style.map_goal_pair) | curses.A_BOLD)
            if style.colors_ok and style.map_goal_pair else curses.A_BOLD
        )

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
                    ch = "█"
                    attr = wall_attr
                elif top_wall and not bot_wall:
                    ch = "▀"
                    attr = wall_attr
                elif not top_wall and bot_wall:
                    ch = "▄"
                    attr = wall_attr
                else:
                    # пустота: если есть цвета — можно оставить "воздух"
                    if style.colors_ok:
                        ch = " "
                        attr = floor_attr
                    else:
                        ch = "·" if style.unicode_ok else "."
                        attr = curses.A_NORMAL

                if oy == oy_g and x == ox_g:
                    ch = goal_ch
                    attr = goal_attr
                if oy == oy_p and x == ox_p:
                    ch = player_ch
                    attr = player_attr

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
                        ch2 = "█"
                        attr2 = wall_attr
                    elif top_wall2 and not bot_wall2:
                        ch2 = "▀"
                        attr2 = wall_attr
                    elif not top_wall2 and bot_wall2:
                        ch2 = "▄"
                        attr2 = wall_attr
                    else:
                        if style.colors_ok:
                            ch2 = " "
                            attr2 = floor_attr
                        else:
                            ch2 = "·" if style.unicode_ok else "."
                            attr2 = curses.A_NORMAL

                    if oy == oy_g and x == ox_g:
                        ch2 = goal_ch
                        attr2 = goal_attr
                    if oy == oy_p and x == ox_p:
                        ch2 = player_ch
                        attr2 = player_attr

                    if attr2 != attr:
                        break
                    buf.append(ch2)
                    x += 1

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


def try_enable_mouse() -> bool:
    """
    Просим терминал присылать события мыши, включая позицию.
    Возвращаем True, если ncurses говорит, что REPORT_MOUSE_POSITION доступен.
    """
    try:
        if not hasattr(curses, "REPORT_MOUSE_POSITION"):
            return False
        mask = curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION
        avail, _old = curses.mousemask(mask)
        try:
            curses.mouseinterval(0)
        except Exception:
            pass
        return bool(avail & curses.REPORT_MOUSE_POSITION)
    except Exception:
        return False


def win_screen(stdscr, seconds: float, style: Style) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    msg1 = "Вы нашли выход!" if style.unicode_ok else "YOU WIN!"
    msg2 = f"Время: {seconds:.1f} c" if style.unicode_ok else f"Time: {seconds:.1f}s"
    msg3 = "Нажмите любую клавишу…" if style.unicode_ok else "Press any key..."

    y = h // 2 - 1
    for i, msg in enumerate((msg1, msg2, msg3)):
        x = max(0, (w - len(msg)) // 2)
        safe_addstr(stdscr, y + i, x, msg[: max(0, w - x - 1)], curses.A_BOLD)

    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()
    stdscr.nodelay(True)


def main_curses(stdscr, grid: List[str], difficulty: int, goal_xy: Tuple[int, int]) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    style = init_style(stdscr)

    start_time = time.monotonic()
    hud_until = start_time + 5.0  # HUD первые 5 секунд

    show_map = False

    last = start_time
    move_dir = 0        # -1 назад, +1 вперед
    rot_dir = 0         # -1 влево, +1 вправо
    move_until = 0.0
    rot_until = 0.0

    mouse_enabled = try_enable_mouse()
    last_mouse_x: Optional[int] = None

    player = Player(x=1.5, y=1.5, ang=0.0)

    while True:
        now = time.monotonic()
        dt = now - last
        last = now

        while True:
            ch = stdscr.getch()
            if ch == -1:
                break

            # ESC: показать/скрыть HUD (на 5 секунд при включении)
            if ch == 27:
                if now < hud_until:
                    hud_until = now
                else:
                    hud_until = now + 5.0
                continue

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
            elif ch == curses.KEY_MOUSE and mouse_enabled:
                try:
                    _id, mx, _my, _mz, bstate = curses.getmouse()
                except Exception:
                    continue

                if bstate & curses.REPORT_MOUSE_POSITION:
                    if last_mouse_x is not None:
                        dx = mx - last_mouse_x
                        if dx:
                            player.ang = normalize_angle(player.ang + dx * MOUSE_SENS)
                    last_mouse_x = mx
                else:
                    last_mouse_x = mx

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
            win_screen(stdscr, time.monotonic() - start_time, style)
            return

        stdscr.erase()
        if show_map:
            render_map(stdscr, grid, player, goal_xy, difficulty, style)
        else:
            render_3d(
                stdscr,
                grid,
                player,
                goal_xy,
                difficulty,
                style,
                hud_visible=(now < hud_until),
                mouse_enabled=mouse_enabled,
            )
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
    try:
        locale.setlocale(locale.LC_ALL, "")
    except Exception:
        pass

    d = ask_difficulty()

    rng = random.Random()
    cw, ch = difficulty_to_size(d)
    grid = generate_maze(cw, ch, rng)

    goal_x = 2 * (cw - 1) + 1
    goal_y = 2 * (ch - 1) + 1

    curses.wrapper(lambda stdscr: main_curses(stdscr, grid, d, (goal_x, goal_y)))


if __name__ == "__main__":
    run()
