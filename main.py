#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D maze in terminal (raycasting) with settings menu, multiple renderers, demo/auto-solve mode,
and localization (English default, Russian optional).

Controls (in game):
- W/S: move forward/back
- A/D: turn left/right
- M: map
- ESC: menu
- Q: quit (with Y/N confirmation)

Render modes:
- text: classic chars
- half: half-block (2 vertical pixels per cell)
- braille: braille dots (2x4 pixels per cell; UTF-8)
- auto: best available

Demo mode:
- If enabled from the start menu, the game finds a path and walks it automatically.
"""

from __future__ import annotations

import curses
import locale
import math
import os
import random
import sys
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Literal, Callable

WALL = "#"
OPEN = " "

FOV_DEFAULT = math.pi / 3.0
MAX_RAY_DIST = 40.0

MOVE_SPEED = 3.2
ROT_SPEED = 2.2
HOLD_TIMEOUT = 0.14

MOUSE_SENS_DEFAULT = 0.012

ASCII_WALL_SHADES = "@%#*+=-:."
ASCII_FLOOR_SHADES = ".,-~:;=!*#$@"
UNICODE_FLOOR_CHARS = "·⋅∘°ˑ"

RenderMode = Literal["auto", "text", "half", "braille"]
GameMode = Literal["play", "demo"]


LOCALES: Dict[str, Dict[str, str]] = {
    "en": {
        # Language names
        "lang_name": "English",
        "lang_label": "Language",

        # Generic / prompts
        "msg_too_small": "Terminal too small. Enlarge it.",
        "prompt_yes_no": "{prompt} Y/N ",
        "prompt_exit": "Exit the game?",
        "prompt_quit_short": "Quit?",
        "prompt_restart_short": "Restart?",

        # Menu chrome
        "menu_title": " SETTINGS / MENU ",
        "menu_terminal": "Terminal: {caps}",
        "menu_footer": "←/→: change   Enter: select   ESC: back",
        "menu_small": "Terminal too small for the menu. Enlarge it.",
        "menu_small_hint": "Enter: continue   Q: quit",

        # Menu items (labels)
        "menu_action_start": "Start",
        "menu_action_resume": "Resume",
        "menu_action_restart": "Restart",
        "menu_action_quit": "Quit",

        "menu_item_mode": "Mode",
        "menu_item_difficulty": "Difficulty",
        "menu_item_render": "Renderer",
        "menu_item_colors": "Color",
        "menu_item_unicode": "Unicode",
        "menu_item_mouse": "Mouse look",
        "menu_item_hud": "HUD",
        "menu_item_fov": "FOV",
        "menu_item_language": "Language",

        # Menu selection / help
        "help_selected": "Selected: {label}",
        "help_nav_title": "Navigation:",
        "help_nav_updown": "  ↑/↓ or W/S — select",
        "help_nav_leftright": "  ←/→ or A/D — change",
        "help_nav_enter": "  Enter/Space — apply",
        "help_nav_esc": "  ESC — close",
        "help_in_game": "In game: W/S move, A/D turn, M map, ESC menu, Q quit",

        "help_render_title": "Render modes:",
        "help_render_text": "  text    — fast/simple",
        "help_render_half": "  half    — half blocks (smoother)",
        "help_render_braille": "  braille — max detail (UTF-8)",
        "help_render_auto": "  auto    — best available",

        "help_hud_title": "HUD:",
        "help_hud_auto5": "  auto5 — first 5 seconds",
        "help_hud_always": "  always — always visible",
        "help_hud_off": "  off — hidden",

        "help_mouse_title": "Mouse look:",
        "help_mouse_desc1": "  Needs mouse motion events (kitty often supports).",
        "help_mouse_desc2": "  If it does not work — set to off.",

        "help_mode_title": "Mode:",
        "help_mode_play": "  play — you control the player",
        "help_mode_demo": "  demo — auto-solver walks the maze",

        # Options (display)
        "opt_auto": "auto",
        "opt_on": "on",
        "opt_off": "off",
        "opt_text": "text",
        "opt_half": "half",
        "opt_braille": "braille",
        "opt_auto5": "auto5",
        "opt_always": "always",
        "opt_play": "play",
        "opt_demo": "demo",

        # Capabilities tags
        "cap_utf8_ok": "UTF-8✓",
        "cap_utf8_no": "UTF-8×",
        "cap_color_256": "256c",
        "cap_color": "color",
        "cap_mono": "mono",
        "cap_mouse_ok": "mouse✓",
        "cap_mouse_no": "mouse×",
        "warn_mouse": "(!)",

        # HUD / map / win
        "hud_line1": "W/S move  A/D turn  M map  ESC menu  Q quit",
        "hud_line2": "Diff:{diff:3d}  To exit:{dist:6.1f}  Render:{render}  {tags}",
        "tag_ascii": "ASCII",
        "tag_utf8": "UTF-8",
        "tag_color": "color",
        "tag_mono": "mono",
        "tag_mouse": "mouse",
        "tag_demo": "DEMO",

        "map_title": "MAP — M back  ESC menu  Q quit",

        "win_title": "You found the exit!",
        "win_time": "Time: {sec:.1f}s",
        "win_press_key": "Press any key…",
        "win_demo_next": "Demo: next maze…",
    },
    "ru": {
        "lang_name": "Русский",
        "lang_label": "Язык",

        "msg_too_small": "Окно слишком маленькое. Увеличьте терминал.",
        "prompt_yes_no": "{prompt} Y/N ",
        "prompt_exit": "Выйти из игры?",
        "prompt_quit_short": "Выйти?",
        "prompt_restart_short": "Перезапуск?",

        "menu_title": " НАСТРОЙКИ / МЕНЮ ",
        "menu_terminal": "Терминал: {caps}",
        "menu_footer": "←/→: изменить   Enter: выбрать   ESC: назад",
        "menu_small": "Окно слишком маленькое для меню. Увеличьте терминал.",
        "menu_small_hint": "Enter: продолжить   Q: выйти",

        "menu_action_start": "Начать",
        "menu_action_resume": "Продолжить",
        "menu_action_restart": "Перезапуск",
        "menu_action_quit": "Выход",

        "menu_item_mode": "Режим",
        "menu_item_difficulty": "Сложность",
        "menu_item_render": "Рендер",
        "menu_item_colors": "Цвет",
        "menu_item_unicode": "Unicode",
        "menu_item_mouse": "Мышь",
        "menu_item_hud": "HUD",
        "menu_item_fov": "FOV",
        "menu_item_language": "Язык",

        "help_selected": "Выбрано: {label}",
        "help_nav_title": "Навигация:",
        "help_nav_updown": "  ↑/↓ или W/S — выбор",
        "help_nav_leftright": "  ←/→ или A/D — изменить",
        "help_nav_enter": "  Enter/Space — применить",
        "help_nav_esc": "  ESC — закрыть",
        "help_in_game": "В игре: W/S ход, A/D поворот, M карта, ESC меню, Q выход",

        "help_render_title": "Рендеры:",
        "help_render_text": "  text    — быстро/просто",
        "help_render_half": "  half    — полублоки (гладче)",
        "help_render_braille": "  braille — максимум деталей (UTF-8)",
        "help_render_auto": "  auto    — лучший доступный",

        "help_hud_title": "HUD:",
        "help_hud_auto5": "  auto5 — первые 5 секунд",
        "help_hud_always": "  always — всегда",
        "help_hud_off": "  off — скрыт",

        "help_mouse_title": "Поворот мышью:",
        "help_mouse_desc1": "  Нужны события движения (kitty обычно умеет).",
        "help_mouse_desc2": "  Если не работает — выключи (off).",

        "help_mode_title": "Режим:",
        "help_mode_play": "  play — управление вручную",
        "help_mode_demo": "  demo — авто-прохождение лабиринта",

        "opt_auto": "auto",
        "opt_on": "on",
        "opt_off": "off",
        "opt_text": "text",
        "opt_half": "half",
        "opt_braille": "braille",
        "opt_auto5": "auto5",
        "opt_always": "always",
        "opt_play": "play",
        "opt_demo": "demo",

        "cap_utf8_ok": "UTF-8✓",
        "cap_utf8_no": "UTF-8×",
        "cap_color_256": "256c",
        "cap_color": "color",
        "cap_mono": "mono",
        "cap_mouse_ok": "мышь✓",
        "cap_mouse_no": "мышь×",
        "warn_mouse": "(!)",

        "hud_line1": "W/S:движ  A/D:поворот  M:карта  ESC:меню  Q:выход",
        "hud_line2": "Сложн:{diff:3d}  До выхода:{dist:6.1f}  Рендер:{render}  {tags}",
        "tag_ascii": "ASCII",
        "tag_utf8": "UTF-8",
        "tag_color": "цвет",
        "tag_mono": "моно",
        "tag_mouse": "мышь",
        "tag_demo": "ДЕМО",

        "map_title": "КАРТА — M:назад  ESC:меню  Q:выход",

        "win_title": "Вы нашли выход!",
        "win_time": "Время: {sec:.1f} c",
        "win_press_key": "Нажмите любую клавишу…",
        "win_demo_next": "Демо: следующий лабиринт…",
    },
}


def make_tr(lang: str) -> Callable[[str], str]:
    def tr(key: str, **kwargs) -> str:
        table = LOCALES.get(lang) or LOCALES["en"]
        s = table.get(key) or LOCALES["en"].get(key) or key
        if kwargs:
            try:
                return s.format(**kwargs)
            except Exception:
                return s
        return s
    return tr


@dataclass
class Player:
    x: float
    y: float
    ang: float


@dataclass
class Settings:
    difficulty: int = 30
    game_mode: GameMode = "play"           # play/demo
    language: str = "en"                   # default English

    render_mode: RenderMode = "auto"
    colors: Literal["auto", "on", "off"] = "auto"
    unicode: Literal["auto", "on", "off"] = "auto"
    mouse_look: Literal["auto", "on", "off"] = "auto"
    hud: Literal["auto5", "always", "off"] = "auto5"
    fov: float = FOV_DEFAULT
    mouse_sens: float = MOUSE_SENS_DEFAULT


@dataclass
class Capabilities:
    unicode_ok: bool
    colors_ok: bool
    color_mode: Literal["none", "basic", "256"]
    mouse_motion_ok: bool


@dataclass
class Style:
    unicode_ok: bool
    colors_ok: bool
    color_mode: Literal["none", "basic", "256"]
    wall_pairs: List[int]
    floor_pairs: List[int]
    hud_pair: int
    map_wall_pair: int
    map_floor_pair: int
    map_player_pair: int
    map_goal_pair: int

    def wall_attr(self, dist: float, side: int) -> int:
        if not self.colors_ok or not self.wall_pairs:
            return curses.A_NORMAL
        t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
        idx = int(t * (len(self.wall_pairs) - 1))
        pair = self.wall_pairs[idx]
        attr = curses.color_pair(pair)
        if side == 1:
            attr |= curses.A_DIM
        if dist < 3.5:
            attr |= curses.A_BOLD
        return attr

    def floor_attr(self, y: int, view_h: int) -> int:
        if not self.colors_ok or not self.floor_pairs:
            return curses.A_NORMAL
        t = clamp((y - view_h * 0.5) / max(1.0, view_h * 0.5), 0.0, 1.0)
        idx = int(t * (len(self.floor_pairs) - 1))
        return curses.color_pair(self.floor_pairs[idx])

    def wall_char_text(self, dist: float) -> str:
        if not self.unicode_ok:
            t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
            idx = int(t * (len(ASCII_WALL_SHADES) - 1))
            return ASCII_WALL_SHADES[idx]
        if dist < 2.5:
            return "█"
        if dist < 5.5:
            return "▓"
        if dist < 10.0:
            return "▒"
        return "░"

    def floor_char(self, y: int, view_h: int) -> str:
        if not self.unicode_ok:
            t = clamp((y - view_h * 0.5) / max(1.0, view_h * 0.5), 0.0, 1.0)
            idx = int(t * (len(ASCII_FLOOR_SHADES) - 1))
            return ASCII_FLOOR_SHADES[idx]
        t = clamp((y - view_h * 0.5) / max(1.0, view_h * 0.5), 0.0, 1.0)
        idx = int(t * (len(UNICODE_FLOOR_CHARS) - 1))
        return UNICODE_FLOOR_CHARS[idx]


def safe_addstr(stdscr, y: int, x: int, s: str, attr: int = 0) -> None:
    try:
        stdscr.addstr(y, x, s, attr)
    except curses.error:
        pass


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
    unicode_ok = prefer_utf8()

    colors_ok = False
    color_mode: Literal["none", "basic", "256"] = "none"
    wall_pairs: List[int] = []
    floor_pairs: List[int] = []
    hud_pair = 0
    map_wall_pair = 0
    map_floor_pair = 0
    map_player_pair = 0
    map_goal_pair = 0

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
        bg = -1

        if color_mode == "256":
            wall_colors = list(range(255, 231, -1))  # 24
            floor_colors = list(range(244, 235, -1))  # 9

            for fg in wall_colors:
                if pid >= pairs:
                    break
                if safe_init_pair(pid, fg, bg):
                    wall_pairs.append(pid)
                    pid += 1

            for fg in floor_colors:
                if pid >= pairs:
                    break
                if safe_init_pair(pid, fg, bg):
                    floor_pairs.append(pid)
                    pid += 1

            if pid < pairs and safe_init_pair(pid, 15, bg):
                hud_pair = pid; pid += 1
            if pid < pairs and safe_init_pair(pid, 250, bg):
                map_wall_pair = pid; pid += 1
            if pid < pairs and safe_init_pair(pid, 238, bg):
                map_floor_pair = pid; pid += 1
            if pid < pairs and safe_init_pair(pid, 226, bg):
                map_player_pair = pid; pid += 1
            if pid < pairs and safe_init_pair(pid, 46, bg):
                map_goal_pair = pid; pid += 1
        else:
            wall_colors = [curses.COLOR_WHITE, curses.COLOR_CYAN, curses.COLOR_BLUE]
            floor_colors = [curses.COLOR_YELLOW, curses.COLOR_MAGENTA, curses.COLOR_RED]

            for fg in wall_colors:
                if pid >= pairs:
                    break
                if safe_init_pair(pid, fg, bg):
                    wall_pairs.append(pid); pid += 1
            for fg in floor_colors:
                if pid >= pairs:
                    break
                if safe_init_pair(pid, fg, bg):
                    floor_pairs.append(pid); pid += 1

            if pid < pairs and safe_init_pair(pid, curses.COLOR_WHITE, bg):
                hud_pair = pid; pid += 1
            if pid < pairs and safe_init_pair(pid, curses.COLOR_WHITE, bg):
                map_wall_pair = pid; pid += 1
            if pid < pairs and safe_init_pair(pid, curses.COLOR_BLACK, bg):
                map_floor_pair = pid; pid += 1
            if pid < pairs and safe_init_pair(pid, curses.COLOR_YELLOW, bg):
                map_player_pair = pid; pid += 1
            if pid < pairs and safe_init_pair(pid, curses.COLOR_GREEN, bg):
                map_goal_pair = pid; pid += 1

    return Style(
        unicode_ok=unicode_ok,
        colors_ok=colors_ok,
        color_mode=color_mode,
        wall_pairs=wall_pairs,
        floor_pairs=floor_pairs,
        hud_pair=hud_pair,
        map_wall_pair=map_wall_pair,
        map_floor_pair=map_floor_pair,
        map_player_pair=map_player_pair,
        map_goal_pair=map_goal_pair,
    )


def effective_style(base: Style, settings: Settings) -> Style:
    unicode_ok = base.unicode_ok
    if settings.unicode == "on":
        unicode_ok = True
    elif settings.unicode == "off":
        unicode_ok = False

    colors_ok = base.colors_ok
    if settings.colors == "off":
        colors_ok = False
    elif settings.colors == "on":
        colors_ok = base.colors_ok

    wall_pairs = base.wall_pairs if colors_ok else []
    floor_pairs = base.floor_pairs if colors_ok else []
    hud_pair = base.hud_pair if colors_ok else 0
    map_wall_pair = base.map_wall_pair if colors_ok else 0
    map_floor_pair = base.map_floor_pair if colors_ok else 0
    map_player_pair = base.map_player_pair if colors_ok else 0
    map_goal_pair = base.map_goal_pair if colors_ok else 0
    color_mode = base.color_mode if colors_ok else "none"

    return Style(
        unicode_ok=unicode_ok,
        colors_ok=colors_ok,
        color_mode=color_mode,
        wall_pairs=wall_pairs,
        floor_pairs=floor_pairs,
        hud_pair=hud_pair,
        map_wall_pair=map_wall_pair,
        map_floor_pair=map_floor_pair,
        map_player_pair=map_player_pair,
        map_goal_pair=map_goal_pair,
    )


def detect_caps(base_style: Style, mouse_motion_ok: bool) -> Capabilities:
    return Capabilities(
        unicode_ok=base_style.unicode_ok,
        colors_ok=base_style.colors_ok,
        color_mode=base_style.color_mode if base_style.colors_ok else "none",
        mouse_motion_ok=mouse_motion_ok,
    )


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


def cast_ray(grid: List[str], px: float, py: float, ang: float) -> Tuple[float, int]:
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


def confirm_yes_no(stdscr, tr: Callable[[str], str], prompt_key: str) -> bool:
    prompt = tr(prompt_key)
    h, w = stdscr.getmaxyx()
    line = tr("prompt_yes_no", prompt=prompt)
    safe_addstr(stdscr, h - 1, 0, line[: max(0, w - 1)], curses.A_REVERSE)
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


def set_mouse_tracking(enable: bool) -> bool:
    try:
        if not enable:
            curses.mousemask(0)
            return False
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


# -------------------- Pathfinding (demo mode) --------------------

def find_path_cells(grid: List[str], start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
    """BFS shortest path on open tiles; returns list of (x,y) including start and goal."""
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


def demo_step(grid: List[str], player: Player, path: List[Tuple[int, int]], idx: int, dt: float) -> int:
    """
    Advance the player along the path (grid cells).
    Returns updated index (the last reached path cell).
    """
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

    # Keep centered in corridors
    if dx != 0:
        target_y = cur_cell[1] + 0.5
        player.y += (target_y - player.y) * min(1.0, dt * 8.0)
    if dy != 0:
        target_x = cur_cell[0] + 0.5
        player.x += (target_x - player.x) * min(1.0, dt * 8.0)

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


# -------------------- Renderer helpers --------------------

def option_display(tr: Callable[[str], str], key: str, value: str) -> str:
    mapping = {
        "auto": "opt_auto",
        "on": "opt_on",
        "off": "opt_off",
        "text": "opt_text",
        "half": "opt_half",
        "braille": "opt_braille",
        "auto5": "opt_auto5",
        "always": "opt_always",
        "play": "opt_play",
        "demo": "opt_demo",
    }
    if key == "language":
        return (LOCALES.get(value) or LOCALES["en"]).get("lang_name", value)
    return tr(mapping.get(value, value))


def draw_hud(
    stdscr,
    tr: Callable[[str], str],
    player: Player,
    goal_xy: Tuple[int, int],
    settings: Settings,
    style: Style,
    mouse_active: bool,
) -> None:
    h, w = stdscr.getmaxyx()
    gx, gy = goal_xy
    dist_goal = math.hypot((gx + 0.5) - player.x, (gy + 0.5) - player.y)

    line1 = tr("hud_line1")

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
    if settings.game_mode == "demo":
        tags.append(tr("tag_demo"))

    tag_str = "+".join(tags)
    render_disp = option_display(tr, "render_mode", settings.render_mode)

    line2 = tr(
        "hud_line2",
        diff=settings.difficulty,
        dist=dist_goal,
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

    hud_lines = 2 if hud_visible else 0
    view_h = max(1, h - hud_lines)
    view_w = max(1, w - 1)
    fov = settings.fov

    tops = [0] * view_w
    bots = [0] * view_w
    wall_chars = [" "] * view_w
    wall_attrs = [0] * view_w

    for x in range(view_w):
        ray_ang = player.ang - fov / 2.0 + (x / max(1, view_w - 1)) * fov
        dist, side = cast_ray(grid, player.x, player.y, ray_ang)
        dist *= max(0.0001, math.cos(ray_ang - player.ang))
        dist = max(0.0001, dist)

        wall_h = int(view_h * 1.25 / dist)
        top = (view_h - wall_h) // 2
        bot = top + wall_h
        tops[x] = top
        bots[x] = bot

        wall_chars[x] = style.wall_char_text(dist)
        wall_attrs[x] = style.wall_attr(dist, side)

    for y in range(view_h):
        x = 0
        while x < view_w:
            if y < tops[x]:
                ch = " "; attr = curses.A_NORMAL
            elif y >= bots[x]:
                ch = style.floor_char(y, view_h); attr = style.floor_attr(y, view_h)
            else:
                ch = wall_chars[x]; attr = wall_attrs[x]

            start = x
            buf = [ch]
            x += 1
            while x < view_w:
                if y < tops[x]:
                    ch2 = " "; attr2 = curses.A_NORMAL
                elif y >= bots[x]:
                    ch2 = style.floor_char(y, view_h); attr2 = style.floor_attr(y, view_h)
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

    hud_lines = 2 if hud_visible else 0
    view_h = max(1, h - hud_lines)
    view_w = max(1, w - 1)
    fov = settings.fov

    pix_h = view_h * 2
    top_half = [0] * view_w
    bot_half = [0] * view_w
    attr_col = [0] * view_w
    full_char_col = ["█"] * view_w

    for x in range(view_w):
        ray_ang = player.ang - fov / 2.0 + (x / max(1, view_w - 1)) * fov
        dist, side = cast_ray(grid, player.x, player.y, ray_ang)
        dist *= max(0.0001, math.cos(ray_ang - player.ang))
        dist = max(0.0001, dist)

        wall_h = int(pix_h * 1.25 / dist)
        th = (pix_h - wall_h) // 2
        bh = th + wall_h
        top_half[x] = th
        bot_half[x] = bh

        attr_col[x] = style.wall_attr(dist, side)
        full_char_col[x] = style.wall_char_text(dist) if not style.colors_ok else "█"

    for y in range(view_h):
        y_top = 2 * y
        y_bot = y_top + 1

        x = 0
        while x < view_w:
            def cell(xi: int) -> Tuple[str, int]:
                th = top_half[xi]; bh = bot_half[xi]
                top_on = th <= y_top < bh
                bot_on = th <= y_bot < bh
                if top_on and bot_on:
                    return full_char_col[xi], attr_col[xi]
                if top_on and not bot_on:
                    return ("▀" if style.unicode_ok else full_char_col[xi]), attr_col[xi]
                if not top_on and bot_on:
                    return ("▄" if style.unicode_ok else full_char_col[xi]), attr_col[xi]
                if y < view_h // 2:
                    return " ", curses.A_NORMAL
                return style.floor_char(y, view_h), style.floor_attr(y, view_h)

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

    hud_lines = 2 if hud_visible else 0
    view_h = max(1, h - hud_lines)
    view_w = max(1, w - 1)
    fov = settings.fov

    sub_w = view_w * 2
    pix_h = view_h * 4

    dist_sub = [0.0] * sub_w
    side_sub = [0] * sub_w
    top_pix = [0] * sub_w
    bot_pix = [0] * sub_w

    for sx in range(sub_w):
        ray_ang = player.ang - fov / 2.0 + (sx / max(1, sub_w - 1)) * fov
        dist, side = cast_ray(grid, player.x, player.y, ray_ang)
        dist *= max(0.0001, math.cos(ray_ang - player.ang))
        dist = max(0.0001, dist)

        dist_sub[sx] = dist
        side_sub[sx] = side

        wall_h = int(pix_h * 1.25 / dist)
        tp = (pix_h - wall_h) // 2
        bp = tp + wall_h
        top_pix[sx] = tp
        bot_pix[sx] = bp

    for y in range(view_h):
        x = 0
        while x < view_w:
            def cell(xi: int) -> Tuple[str, int]:
                bits = 0
                for sub_col in (0, 1):
                    sx = 2 * xi + sub_col
                    tp = top_pix[sx]; bp = bot_pix[sx]
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
                    return chr(0x2800 + bits), style.wall_attr(d, side)
                if y < view_h // 2:
                    return " ", curses.A_NORMAL
                return style.floor_char(y, view_h), style.floor_attr(y, view_h)

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


def choose_renderer(settings: Settings, style: Style) -> RenderMode:
    if settings.render_mode != "auto":
        if settings.render_mode in ("half", "braille") and not style.unicode_ok:
            return "text"
        return settings.render_mode
    return "braille" if style.unicode_ok else "text"


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


# -------------------- Map view --------------------

def render_map(
    stdscr,
    tr: Callable[[str], str],
    grid: List[str],
    player: Player,
    goal_xy: Tuple[int, int],
    settings: Settings,
    style: Style,
) -> None:
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


# -------------------- Menu UI --------------------

def box_chars(unicode_ok: bool):
    if unicode_ok:
        return {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "│"}
    return {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|"}


def draw_box(stdscr, y: int, x: int, h: int, w: int, unicode_ok: bool, attr: int = 0) -> None:
    bc = box_chars(unicode_ok)
    safe_addstr(stdscr, y, x, bc["tl"] + bc["h"] * (w - 2) + bc["tr"], attr)
    for yy in range(y + 1, y + h - 1):
        safe_addstr(stdscr, yy, x, bc["v"], attr)
        safe_addstr(stdscr, yy, x + w - 1, bc["v"], attr)
    safe_addstr(stdscr, y + h - 1, x, bc["bl"] + bc["h"] * (w - 2) + bc["br"], attr)


def cycle_value(values: List[str], cur: str, delta: int) -> str:
    try:
        i = values.index(cur)
    except ValueError:
        i = 0
    return values[(i + delta) % len(values)]


def run_menu(
    stdscr,
    base_style: Style,
    caps: Capabilities,
    settings: Settings,
    mode: Literal["start", "pause"],
) -> str:
    stdscr.nodelay(False)
    sel = 0

    render_choices = ["auto", "text", "half", "braille"]
    onoffauto = ["auto", "on", "off"]
    hud_choices = ["auto5", "always", "off"]
    mode_choices = ["play", "demo"]

    lang_choices = list(LOCALES.keys())
    if "en" in lang_choices:
        lang_choices = ["en"] + [l for l in lang_choices if l != "en"]

    items: List[Tuple[str, str, str]] = []
    if mode == "pause":
        items.append(("menu_action_resume", "action", "resume"))
    else:
        items.append(("menu_action_start", "action", "start"))

    items += [
        ("menu_item_mode", "choice", "game_mode"),
        ("menu_item_difficulty", "range", "difficulty"),
        ("menu_item_render", "choice", "render_mode"),
        ("menu_item_colors", "choice", "colors"),
        ("menu_item_unicode", "choice", "unicode"),
        ("menu_item_mouse", "choice", "mouse_look"),
        ("menu_item_hud", "choice", "hud"),
        ("menu_item_fov", "range", "fov"),
        ("menu_item_language", "choice", "language"),
    ]

    if mode == "pause":
        items.append(("menu_action_restart", "action", "restart"))
    items.append(("menu_action_quit", "action", "quit"))

    while True:
        tr = make_tr(settings.language)

        stdscr.erase()
        H, W = stdscr.getmaxyx()

        if H < 14 or W < 44:
            safe_addstr(stdscr, 0, 0, tr("menu_small"))
            safe_addstr(stdscr, 2, 0, tr("menu_small_hint"))
            stdscr.refresh()
            ch = stdscr.getch()
            if ch in (ord("q"), ord("Q")):
                if confirm_yes_no(stdscr, tr, "prompt_quit_short"):
                    stdscr.nodelay(True)
                    return "quit"
            if ch in (10, 13, curses.KEY_ENTER):
                stdscr.nodelay(True)
                return "resume" if mode == "pause" else "start"
            continue

        box_w = min(88, W - 4)
        box_h = min(28, H - 4)
        box_x = (W - box_w) // 2
        box_y = (H - box_h) // 2

        unicode_ui = base_style.unicode_ok
        border_attr = curses.A_NORMAL
        if base_style.colors_ok and base_style.hud_pair:
            border_attr |= curses.color_pair(base_style.hud_pair)

        draw_box(stdscr, box_y, box_x, box_h, box_w, unicode_ui, border_attr)
        title = tr("menu_title")
        safe_addstr(stdscr, box_y, box_x + 2, title[: box_w - 4], border_attr | curses.A_BOLD)

        cap_parts = []
        cap_parts.append(tr("cap_utf8_ok") if caps.unicode_ok else tr("cap_utf8_no"))
        if caps.colors_ok and caps.color_mode == "256":
            cap_parts.append(tr("cap_color_256"))
        elif caps.colors_ok:
            cap_parts.append(tr("cap_color"))
        else:
            cap_parts.append(tr("cap_mono"))
        cap_parts.append(tr("cap_mouse_ok") if caps.mouse_motion_ok else tr("cap_mouse_no"))

        caps_line = tr("menu_terminal", caps=", ".join(cap_parts))
        safe_addstr(stdscr, box_y + 1, box_x + 2, caps_line[: box_w - 4], curses.A_DIM)

        left_w = int(box_w * 0.56)
        right_w = box_w - left_w - 3
        left_x = box_x + 2
        right_x = left_x + left_w + 2
        top_y = box_y + 3

        sep = "│" if unicode_ui else "|"
        for yy in range(top_y - 1, box_y + box_h - 2):
            safe_addstr(stdscr, yy, right_x - 2, sep, border_attr)

        list_h = box_y + box_h - 4 - top_y + 1
        sel = max(0, min(sel, len(items) - 1))

        label_width = 12

        for i, (label_key, kind, key) in enumerate(items):
            y = top_y + i
            if y >= top_y + list_h:
                break
            is_sel = (i == sel)
            prefix = "▶ " if unicode_ui else "> "
            pad = "  "
            attr = curses.A_REVERSE if is_sel else curses.A_NORMAL

            label = tr(label_key)

            value = ""
            warn = ""
            if kind == "range":
                if key == "difficulty":
                    value = f"[ {settings.difficulty:3d} ]"
                elif key == "fov":
                    value = f"[ {settings.fov * 180.0 / math.pi:5.1f}° ]"
            elif kind == "choice":
                cur = getattr(settings, key)
                disp = option_display(tr, key, str(cur))
                value = f"[ {disp} ]"
                if key == "mouse_look" and not caps.mouse_motion_ok and str(cur) != "off":
                    warn = " " + tr("warn_mouse")

            line = (prefix if is_sel else pad) + f"{label:<{label_width}} {value}{warn}"
            safe_addstr(stdscr, y, left_x, line[: left_w], attr)

        label_key, kind, key = items[sel]
        label = tr(label_key)

        help_lines = [
            tr("help_selected", label=label),
            "",
            tr("help_nav_title"),
            tr("help_nav_updown"),
            tr("help_nav_leftright"),
            tr("help_nav_enter"),
            tr("help_nav_esc"),
            "",
            tr("help_in_game"),
            "",
        ]

        if key == "render_mode":
            help_lines += [
                tr("help_render_title"),
                tr("help_render_text"),
                tr("help_render_half"),
                tr("help_render_braille"),
                tr("help_render_auto"),
            ]
        elif key == "hud":
            help_lines += [
                tr("help_hud_title"),
                tr("help_hud_auto5"),
                tr("help_hud_always"),
                tr("help_hud_off"),
            ]
        elif key == "mouse_look":
            help_lines += [
                tr("help_mouse_title"),
                tr("help_mouse_desc1"),
                tr("help_mouse_desc2"),
            ]
        elif key == "game_mode":
            help_lines += [
                tr("help_mode_title"),
                tr("help_mode_play"),
                tr("help_mode_demo"),
            ]

        for i, line in enumerate(help_lines):
            yy = top_y + i
            if yy >= box_y + box_h - 2:
                break
            safe_addstr(stdscr, yy, right_x, line[: right_w], curses.A_DIM if i not in (0,) else curses.A_BOLD)

        footer = tr("menu_footer")
        safe_addstr(stdscr, box_y + box_h - 2, box_x + 2, footer[: box_w - 4], curses.A_DIM)

        stdscr.refresh()
        ch = stdscr.getch()

        if ch == 27:  # ESC
            if mode == "start":
                if confirm_yes_no(stdscr, tr, "prompt_exit"):
                    stdscr.nodelay(True)
                    return "quit"
                continue
            stdscr.nodelay(True)
            return "resume"

        if ch in (curses.KEY_UP, ord("w"), ord("W")):
            sel = (sel - 1) % len(items)
            continue
        if ch in (curses.KEY_DOWN, ord("s"), ord("S")):
            sel = (sel + 1) % len(items)
            continue

        if ch in (curses.KEY_LEFT, ord("a"), ord("A")):
            label_key, kind, key = items[sel]
            if kind == "range":
                if key == "difficulty":
                    settings.difficulty = int(clamp(settings.difficulty - 1, 1, 100))
                elif key == "fov":
                    settings.fov = clamp(settings.fov - math.radians(2.0), math.radians(40), math.radians(120))
            elif kind == "choice":
                cur = str(getattr(settings, key))
                if key == "render_mode":
                    settings.render_mode = cycle_value(render_choices, cur, -1)  # type: ignore
                elif key in ("colors", "unicode", "mouse_look"):
                    setattr(settings, key, cycle_value(onoffauto, cur, -1))
                elif key == "hud":
                    settings.hud = cycle_value(hud_choices, cur, -1)  # type: ignore
                elif key == "game_mode":
                    settings.game_mode = cycle_value(mode_choices, cur, -1)  # type: ignore
                elif key == "language":
                    settings.language = cycle_value(lang_choices, cur, -1)
            continue

        if ch in (curses.KEY_RIGHT, ord("d"), ord("D")):
            label_key, kind, key = items[sel]
            if kind == "range":
                if key == "difficulty":
                    settings.difficulty = int(clamp(settings.difficulty + 1, 1, 100))
                elif key == "fov":
                    settings.fov = clamp(settings.fov + math.radians(2.0), math.radians(40), math.radians(120))
            elif kind == "choice":
                cur = str(getattr(settings, key))
                if key == "render_mode":
                    settings.render_mode = cycle_value(render_choices, cur, 1)  # type: ignore
                elif key in ("colors", "unicode", "mouse_look"):
                    setattr(settings, key, cycle_value(onoffauto, cur, 1))
                elif key == "hud":
                    settings.hud = cycle_value(hud_choices, cur, 1)  # type: ignore
                elif key == "game_mode":
                    settings.game_mode = cycle_value(mode_choices, cur, 1)  # type: ignore
                elif key == "language":
                    settings.language = cycle_value(lang_choices, cur, 1)
            continue

        if ch in (10, 13, curses.KEY_ENTER, ord(" "), ord("\n")):
            label_key, kind, key = items[sel]
            if kind == "action":
                if key == "quit":
                    if confirm_yes_no(stdscr, tr, "prompt_exit"):
                        stdscr.nodelay(True)
                        return "quit"
                    continue
                stdscr.nodelay(True)
                return key

            if kind == "choice":
                cur = str(getattr(settings, key))
                if key == "render_mode":
                    settings.render_mode = cycle_value(render_choices, cur, 1)  # type: ignore
                elif key in ("colors", "unicode", "mouse_look"):
                    setattr(settings, key, cycle_value(onoffauto, cur, 1))
                elif key == "hud":
                    settings.hud = cycle_value(hud_choices, cur, 1)  # type: ignore
                elif key == "game_mode":
                    settings.game_mode = cycle_value(mode_choices, cur, 1)  # type: ignore
                elif key == "language":
                    settings.language = cycle_value(lang_choices, cur, 1)
                continue

        if ch in (ord("q"), ord("Q")):
            if confirm_yes_no(stdscr, tr, "prompt_exit"):
                stdscr.nodelay(True)
                return "quit"


# -------------------- Win screen --------------------

def win_screen(stdscr, tr: Callable[[str], str], seconds: float, style: Style, wait: bool) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    msg1 = tr("win_title")
    msg2 = tr("win_time", sec=seconds)
    msg3 = tr("win_press_key") if wait else tr("win_demo_next")

    y = h // 2 - 1
    for i, msg in enumerate((msg1, msg2, msg3)):
        x = max(0, (w - len(msg)) // 2)
        safe_addstr(stdscr, y + i, x, msg[: max(0, w - x - 1)], curses.A_BOLD)

    stdscr.refresh()

    if wait:
        stdscr.nodelay(False)
        stdscr.getch()
        stdscr.nodelay(True)
    else:
        time.sleep(0.9)


# -------------------- Game loop --------------------

def main(stdscr) -> None:
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.noecho()
    curses.cbreak()

    base_style = init_style(stdscr)

    mouse_possible = set_mouse_tracking(True)
    set_mouse_tracking(False)

    settings = Settings()  # default language is English
    caps = detect_caps(base_style, mouse_possible)

    action = run_menu(stdscr, base_style, caps, settings, mode="start")
    if action == "quit":
        return

    rng = random.Random()

    while True:
        tr = make_tr(settings.language)

        cw, ch = difficulty_to_size(settings.difficulty)
        grid = generate_maze(cw, ch, rng)
        goal_xy = (2 * (cw - 1) + 1, 2 * (ch - 1) + 1)

        style = effective_style(base_style, settings)

        if settings.mouse_look == "off":
            mouse_active = False
            set_mouse_tracking(False)
        elif settings.mouse_look == "on":
            mouse_active = mouse_possible and set_mouse_tracking(True)
        else:
            mouse_active = mouse_possible and set_mouse_tracking(True)

        player = Player(x=1.5, y=1.5, ang=0.0)
        show_map = False

        demo_path: Optional[List[Tuple[int, int]]] = None
        demo_idx = 0
        if settings.game_mode == "demo":
            demo_path = find_path_cells(grid, (int(player.x), int(player.y)), goal_xy)
            demo_idx = 0

        start_time = time.monotonic()
        hud_until = start_time + 5.0
        last = start_time

        move_dir = 0
        rot_dir = 0
        move_until = 0.0
        rot_until = 0.0

        last_mouse_x: Optional[int] = None

        stdscr.nodelay(True)

        restart_level = False

        while True:
            now = time.monotonic()
            dt = now - last
            last = now

            tr = make_tr(settings.language)

            if settings.hud == "always":
                hud_visible = True
            elif settings.hud == "off":
                hud_visible = False
            else:
                hud_visible = now < hud_until

            while True:
                chkey = stdscr.getch()
                if chkey == -1:
                    break

                if chkey == 27:
                    menu_action = run_menu(stdscr, base_style, caps, settings, mode="pause")
                    if menu_action == "quit":
                        return
                    if menu_action == "restart":
                        restart_level = True
                        break

                    style = effective_style(base_style, settings)
                    if settings.mouse_look == "off":
                        mouse_active = False
                        set_mouse_tracking(False)
                    elif settings.mouse_look == "on":
                        mouse_active = mouse_possible and set_mouse_tracking(True)
                    else:
                        mouse_active = mouse_possible and set_mouse_tracking(True)

                    if settings.game_mode == "demo" and demo_path is None:
                        demo_path = find_path_cells(grid, (int(player.x), int(player.y)), goal_xy)
                        demo_idx = 0
                    if settings.game_mode == "play":
                        demo_path = None

                    last = time.monotonic()
                    continue

                if chkey in (ord("m"), ord("M")):
                    show_map = not show_map
                    continue

                if chkey in (ord("q"), ord("Q")):
                    if confirm_yes_no(stdscr, tr, "prompt_exit"):
                        return
                    continue

                if settings.game_mode == "play":
                    if chkey in (ord("w"), ord("W")):
                        move_dir = 1
                        move_until = now + HOLD_TIMEOUT
                    elif chkey in (ord("s"), ord("S")):
                        move_dir = -1
                        move_until = now + HOLD_TIMEOUT
                    elif chkey in (ord("a"), ord("A")):
                        rot_dir = -1
                        rot_until = now + HOLD_TIMEOUT
                    elif chkey in (ord("d"), ord("D")):
                        rot_dir = 1
                        rot_until = now + HOLD_TIMEOUT

                if chkey == curses.KEY_MOUSE and mouse_active:
                    try:
                        _id, mx, _my, _mz, bstate = curses.getmouse()
                    except Exception:
                        continue
                    if hasattr(curses, "REPORT_MOUSE_POSITION") and (bstate & curses.REPORT_MOUSE_POSITION):
                        if last_mouse_x is not None:
                            dxm = mx - last_mouse_x
                            if dxm:
                                player.ang = normalize_angle(player.ang + dxm * settings.mouse_sens)
                        last_mouse_x = mx
                    else:
                        last_mouse_x = mx

            if restart_level:
                break

            if settings.game_mode == "demo":
                if demo_path is None:
                    demo_path = find_path_cells(grid, (int(player.x), int(player.y)), goal_xy)
                    demo_idx = 0
                else:
                    demo_idx = demo_step(grid, player, demo_path, demo_idx, dt)
            else:
                if now > move_until:
                    move_dir = 0
                if now > rot_until:
                    rot_dir = 0

                if rot_dir:
                    player.ang = normalize_angle(player.ang + rot_dir * ROT_SPEED * dt)

                if move_dir:
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
                seconds = time.monotonic() - start_time
                wait = (settings.game_mode != "demo")
                win_screen(stdscr, tr, seconds, style, wait=wait)
                restart_level = True
                break

            stdscr.erase()
            if show_map:
                render_map(stdscr, tr, grid, player, goal_xy, settings, style)
            else:
                renderer = choose_renderer(settings, style)
                render_scene(stdscr, tr, renderer, grid, player, goal_xy, settings, style, hud_visible, mouse_active)
            stdscr.refresh()

            time.sleep(0.01)


def run() -> None:
    try:
        locale.setlocale(locale.LC_ALL, "")
    except Exception:
        pass
    curses.wrapper(main)


if __name__ == "__main__":
    run()
