#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D maze in terminal (raycasting) with:
- Adaptive terminal rendering
- Multiple renderers (text/half-block/braille/auto)
- Pseudo-graphics menu (ESC)
- Localization (English default + Russian)
- Demo/autosolve modes
- "Free" mode: vertical movement (fly) with basic collision vs floor/walls
- On-the-fly FOV: 1 decrease, 2 increase, 3 reset to 60°
- Toggle shadows: 4 (and in menu)
- Camera pitch via arrows up/down; yaw via arrows left/right; R resets camera pitch
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
from typing import Callable, Dict, List, Optional, Tuple, Literal

# ----- World constants -----
WALL = "#"
OPEN = " "

WALL_HEIGHT = 1.0
EYE_HEIGHT = 0.5  # camera above feet

MAX_RAY_DIST = 40.0

MOVE_SPEED = 3.2
ROT_SPEED = 2.2
PITCH_SPEED = 1.7
PITCH_MAX = math.radians(75.0)
HOLD_TIMEOUT = 0.14

# Free-mode vertical movement (minecraft-ish creative flight feel)
FREE_ACCEL = 18.0         # blocks/s^2
FREE_MAX_V = 6.0          # blocks/s
FREE_DAMP = 12.0          # 1/s velocity damping when no vertical input
FREE_MAX_Z = 6.0          # clamp height (feet)

# FOV control
FOV_DEFAULT = math.pi / 3.0  # 60°
FOV_MIN = math.radians(40.0)
FOV_MAX = math.radians(120.0)
FOV_STEP = math.radians(5.0)

# Mouse look
MOUSE_SENS_DEFAULT = 0.012

# ASCII fallback shading
ASCII_WALL_SHADES = "@%#*+=-:."
ASCII_FLOOR_SHADES = ".,-~:;=!*#$@"
UNICODE_FLOOR_CHARS = "·⋅∘°ˑ"

RenderMode = Literal["auto", "text", "half", "braille"]
Mode = Literal["default", "free", "demo_default", "demo_free"]
Shadows = Literal["on", "off"]

# ----- Localization -----
LOCALES: Dict[str, Dict[str, str]] = {
    "en": {
        "lang_name": "English",
        "lang_label": "Language",

        "msg_too_small": "Terminal too small. Enlarge it.",

        "prompt_yes_no": "{prompt} Y/N ",
        "prompt_exit": "Exit the game?",
        "prompt_quit_short": "Quit?",
        "prompt_restart_short": "Restart?",

        "menu_title": " SETTINGS / MENU ",
        "menu_terminal": "Terminal: {caps}",
        "menu_footer": "←/→: change   Enter: select   ESC: back",
        "menu_small": "Terminal too small for the menu. Enlarge it.",
        "menu_small_hint": "Enter: continue   Q: quit",

        "menu_action_start": "Start",
        "menu_action_resume": "Resume",
        "menu_action_restart": "Restart",
        "menu_action_quit": "Quit",

        "menu_item_mode": "Mode",
        "menu_item_difficulty": "Difficulty",
        "menu_item_render": "Renderer",
        "menu_item_shadows": "Shadows",
        "menu_item_colors": "Color",
        "menu_item_unicode": "Unicode",
        "menu_item_mouse": "Mouse look",
        "menu_item_hud": "HUD",
        "menu_item_fov": "FOV",
        "menu_item_language": "Language",

        "help_selected": "Selected: {label}",
        "help_nav_title": "Navigation:",
        "help_nav_updown": "  ↑/↓ or W/S — select",
        "help_nav_leftright": "  ←/→ or A/D — change",
        "help_nav_enter": "  Enter/Space — apply",
        "help_nav_esc": "  ESC — close",
        "help_in_game": "In game: W/S move, A/D turn, arrows camera, R reset, M map, 1/2/3 FOV, 4 shadows, ESC menu, Q quit",

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
        "help_mode_default": "  default      — normal walking",
        "help_mode_free": "  free         — fly (Space up, X down) + collision",
        "help_mode_demo_default": "  demo default — auto-solve (walk)",
        "help_mode_demo_free": "  demo free    — auto-solve (fly)",

        "help_shadows_title": "Shadows:",
        "help_shadows_on": "  on  — distance/side shading",
        "help_shadows_off": "  off — flat (no shading)",

        "opt_auto": "auto",
        "opt_on": "on",
        "opt_off": "off",
        "opt_text": "text",
        "opt_half": "half",
        "opt_braille": "braille",
        "opt_auto5": "auto5",
        "opt_always": "always",

        "opt_default": "default",
        "opt_free": "free",
        "opt_demo_default": "demo default",
        "opt_demo_free": "demo free",

        "cap_utf8_ok": "UTF-8✓",
        "cap_utf8_no": "UTF-8×",
        "cap_color_256": "256c",
        "cap_color": "color",
        "cap_mono": "mono",
        "cap_mouse_ok": "mouse✓",
        "cap_mouse_no": "mouse×",
        "warn_mouse": "(!)",

        "hud_line1_default": "W/S move  A/D turn  Arrows camera  R reset  M map  1/2/3 FOV  4 shadows  ESC menu  Q quit",
        "hud_line1_free": "W/S move  A/D turn  Arrows camera  Space up  X down  R reset  1/2/3 FOV  4 shadows  ESC menu  Q quit",
        "hud_line2": "Mode:{mode}  Diff:{diff:3d}  To exit:{dist:6.1f}  FOV:{fov:5.1f}°  Render:{render}  {tags}",

        "tag_ascii": "ASCII",
        "tag_utf8": "UTF-8",
        "tag_color": "color",
        "tag_mono": "mono",
        "tag_mouse": "mouse",
        "tag_demo": "DEMO",
        "tag_free": "FREE",
        "tag_noshadow": "NO-SHD",

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
        "menu_item_shadows": "Тени",
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
        "help_in_game": "В игре: W/S ход, A/D поворот, стрелки камера, R сброс, M карта, 1/2/3 FOV, 4 тени, ESC меню, Q выход",

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
        "help_mode_default": "  default      — обычная ходьба",
        "help_mode_free": "  free         — полёт (Space вверх, X вниз) + коллизии",
        "help_mode_demo_default": "  demo default — авто-прохождение (ходьба)",
        "help_mode_demo_free": "  demo free    — авто-прохождение (полёт)",

        "help_shadows_title": "Тени:",
        "help_shadows_on": "  on  — затемнение (дальность/сторона)",
        "help_shadows_off": "  off — плоско (без теней)",

        "opt_auto": "auto",
        "opt_on": "on",
        "opt_off": "off",
        "opt_text": "text",
        "opt_half": "half",
        "opt_braille": "braille",
        "opt_auto5": "auto5",
        "opt_always": "always",

        "opt_default": "default",
        "opt_free": "free",
        "opt_demo_default": "demo default",
        "opt_demo_free": "demo free",

        "cap_utf8_ok": "UTF-8✓",
        "cap_utf8_no": "UTF-8×",
        "cap_color_256": "256c",
        "cap_color": "цвет",
        "cap_mono": "моно",
        "cap_mouse_ok": "мышь✓",
        "cap_mouse_no": "мышь×",
        "warn_mouse": "(!)",

        "hud_line1_default": "W/S:движ  A/D:поворот  Стрелки:камера  R:сброс  M:карта  1/2/3:FOV  4:тени  ESC:меню  Q:выход",
        "hud_line1_free": "W/S:движ  A/D:поворот  Стрелки:камера  Space:вверх  X:вниз  R:сброс  1/2/3:FOV  4:тени  ESC:меню  Q:выход",
        "hud_line2": "Режим:{mode}  Сложн:{diff:3d}  До выхода:{dist:6.1f}  FOV:{fov:5.1f}°  Рендер:{render}  {tags}",

        "tag_ascii": "ASCII",
        "tag_utf8": "UTF-8",
        "tag_color": "цвет",
        "tag_mono": "моно",
        "tag_mouse": "мышь",
        "tag_demo": "ДЕМО",
        "tag_free": "FREE",
        "tag_noshadow": "NO-SHD",

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
    z: float
    ang: float
    pitch: float = 0.0
    vz: float = 0.0  # vertical velocity (free mode)


@dataclass
class Settings:
    difficulty: int = 30
    mode: Mode = "default"
    language: str = "en"

    render_mode: RenderMode = "auto"
    shadows: Shadows = "on"
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

    def floor_attr_dist(self, dist: float) -> int:
        if not self.colors_ok or not self.floor_pairs:
            return curses.A_NORMAL
        t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
        idx = int(t * (len(self.floor_pairs) - 1))
        return curses.color_pair(self.floor_pairs[idx])

    def floor_attr_grad(self, y: int, view_h: int) -> int:
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

    def wall_char_top(self, dist: float) -> str:
        if not self.unicode_ok:
            t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
            idx = int(t * (len(ASCII_WALL_SHADES) - 1))
            return ASCII_WALL_SHADES[idx]
        if dist < 2.5:
            return "▓"
        if dist < 6.0:
            return "▒"
        if dist < 14.0:
            return "░"
        return "·"

    def floor_char_dist(self, dist: float) -> str:
        if not self.unicode_ok:
            t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
            idx = int(t * (len(ASCII_FLOOR_SHADES) - 1))
            return ASCII_FLOOR_SHADES[idx]
        t = clamp(dist / MAX_RAY_DIST, 0.0, 1.0)
        idx = int(t * (len(UNICODE_FLOOR_CHARS) - 1))
        return UNICODE_FLOOR_CHARS[idx]

    def floor_char_grad(self, y: int, view_h: int) -> str:
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

    return Style(
        unicode_ok=unicode_ok,
        colors_ok=colors_ok,
        color_mode=base.color_mode if colors_ok else "none",
        wall_pairs=base.wall_pairs if colors_ok else [],
        floor_pairs=base.floor_pairs if colors_ok else [],
        hud_pair=base.hud_pair if colors_ok else 0,
        map_wall_pair=base.map_wall_pair if colors_ok else 0,
        map_floor_pair=base.map_floor_pair if colors_ok else 0,
        map_player_pair=base.map_player_pair if colors_ok else 0,
        map_goal_pair=base.map_goal_pair if colors_ok else 0,
    )


def detect_caps(base_style: Style, mouse_motion_ok: bool) -> Capabilities:
    return Capabilities(
        unicode_ok=base_style.unicode_ok,
        colors_ok=base_style.colors_ok,
        color_mode=base_style.color_mode if base_style.colors_ok else "none",
        mouse_motion_ok=mouse_motion_ok,
    )


def prefer_utf8() -> bool:
    enc = (
        (sys.stdout.encoding or "") +
        "|" + locale.getpreferredencoding(False) +
        "|" + (os.environ.get("LC_ALL") or "") +
        "|" + (os.environ.get("LANG") or "")
    ).upper()
    return ("UTF-8" in enc) or ("UTF8" in enc)


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


def pitch_mid(height: float, pitch: float) -> float:
    return height * 0.5 - pitch * (height / math.pi)


def compute_wall_span(height: int, dist: float, cam_z: float, mid: float) -> Tuple[int, int]:
    proj_plane = height * 1.25
    proj = proj_plane / max(0.0001, dist)
    top = int(mid - (WALL_HEIGHT - cam_z) * proj)
    bot = int(mid - (0.0 - cam_z) * proj)
    if top > bot:
        top, bot = bot, top
    return top, bot


def choose_renderer(settings: Settings, style: Style) -> RenderMode:
    if settings.render_mode != "auto":
        if settings.render_mode in ("half", "braille") and not style.unicode_ok:
            return "text"
        return settings.render_mode
    return "braille" if style.unicode_ok else "text"


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
        "default": "opt_default",
        "free": "opt_free",
        "demo_default": "opt_demo_default",
        "demo_free": "opt_demo_free",
    }
    if key == "language":
        return (LOCALES.get(value) or LOCALES["en"]).get("lang_name", value)
    return tr(mapping.get(value, value))


def flat_wall_attr(style: Style) -> int:
    if style.colors_ok and style.wall_pairs:
        return curses.color_pair(style.wall_pairs[0]) | curses.A_BOLD
    return curses.A_BOLD if style.unicode_ok else curses.A_NORMAL


def flat_floor_attr(style: Style) -> int:
    if style.colors_ok and style.floor_pairs:
        if style.color_mode == "256":
            idx = len(style.floor_pairs) // 2
        else:
            idx = 0
        return curses.color_pair(style.floor_pairs[idx])
    return curses.A_NORMAL


def floorcast_sample_row(
    grid: List[str],
    px: float,
    py: float,
    cos_arr: List[float],
    sin_arr: List[float],
    dist_plane: float,
    dist_plane_top: Optional[float],
    style: Style,
    shadows_on: bool,
) -> Tuple[List[bool], str, int, str, int]:
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


def run_menu(stdscr, base_style: Style, caps: Capabilities, settings: Settings, mode: Literal["start", "pause"]) -> str:
    stdscr.nodelay(False)
    sel = 0

    render_choices = ["auto", "text", "half", "braille"]
    onoff = ["on", "off"]
    onoffauto = ["auto", "on", "off"]
    hud_choices = ["auto5", "always", "off"]
    mode_choices = ["default", "free", "demo_default", "demo_free"]

    lang_choices = list(LOCALES.keys())
    if "en" in lang_choices:
        lang_choices = ["en"] + [l for l in lang_choices if l != "en"]

    items: List[Tuple[str, str, str]] = []
    if mode == "pause":
        items.append(("menu_action_resume", "action", "resume"))
    else:
        items.append(("menu_action_start", "action", "start"))

    items += [
        ("menu_item_mode", "choice", "mode"),
        ("menu_item_difficulty", "range", "difficulty"),
        ("menu_item_render", "choice", "render_mode"),
        ("menu_item_shadows", "choice", "shadows"),
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

        box_w = min(94, W - 4)
        box_h = min(30, H - 4)
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
                cur = str(getattr(settings, key))
                disp = option_display(tr, key, cur)
                value = f"[ {disp} ]"
                if key == "mouse_look" and not caps.mouse_motion_ok and cur != "off":
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
        elif key == "mode":
            help_lines += [
                tr("help_mode_title"),
                tr("help_mode_default"),
                tr("help_mode_free"),
                tr("help_mode_demo_default"),
                tr("help_mode_demo_free"),
            ]
        elif key == "shadows":
            help_lines += [
                tr("help_shadows_title"),
                tr("help_shadows_on"),
                tr("help_shadows_off"),
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

        def adjust(delta: int) -> None:
            label_key, kind, key = items[sel]
            if kind == "range":
                if key == "difficulty":
                    settings.difficulty = int(clamp(settings.difficulty + delta, 1, 100))
                elif key == "fov":
                    settings.fov = clamp(settings.fov + math.radians(2.0) * delta, FOV_MIN, FOV_MAX)
            elif kind == "choice":
                cur = str(getattr(settings, key))
                if key == "render_mode":
                    settings.render_mode = cycle_value(render_choices, cur, delta)  # type: ignore
                elif key == "shadows":
                    settings.shadows = cycle_value(onoff, cur, delta)  # type: ignore
                elif key in ("colors", "unicode", "mouse_look"):
                    setattr(settings, key, cycle_value(onoffauto, cur, delta))
                elif key == "hud":
                    settings.hud = cycle_value(hud_choices, cur, delta)  # type: ignore
                elif key == "mode":
                    settings.mode = cycle_value(mode_choices, cur, delta)  # type: ignore
                elif key == "language":
                    settings.language = cycle_value(lang_choices, cur, delta)

        if ch in (curses.KEY_LEFT, ord("a"), ord("A")):
            adjust(-1)
            continue
        if ch in (curses.KEY_RIGHT, ord("d"), ord("D")):
            adjust(1)
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
                adjust(1)
                continue

        if ch in (ord("q"), ord("Q")):
            if confirm_yes_no(stdscr, tr, "prompt_exit"):
                stdscr.nodelay(True)
                return "quit"


def win_screen(stdscr, tr: Callable[[str], str], seconds: float, wait: bool) -> None:
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


def main(stdscr) -> None:
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.noecho()
    curses.cbreak()

    base_style = init_style(stdscr)

    mouse_possible = set_mouse_tracking(True)
    set_mouse_tracking(False)

    settings = Settings()
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

        player = Player(x=1.5, y=1.5, z=0.0, ang=0.0, pitch=0.0, vz=0.0)
        resolve_floor_collision(grid, player)

        show_map = False

        demo_path: Optional[List[Tuple[int, int]]] = None
        demo_idx = 0
        if settings.mode == "demo_default":
            demo_path = find_path_cells(grid, (int(player.x), int(player.y)), goal_xy)
            demo_idx = 0

        start_time = time.monotonic()
        hud_until = start_time + 5.0
        last = start_time

        move_dir = 0
        rot_dir = 0
        pitch_dir = 0
        vert_dir = 0

        move_until = 0.0
        rot_until = 0.0
        pitch_until = 0.0
        vert_until = 0.0

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

                # FOV hotkeys
                if chkey == ord("1"):
                    settings.fov = clamp(settings.fov - FOV_STEP, FOV_MIN, FOV_MAX)
                    continue
                if chkey == ord("2"):
                    settings.fov = clamp(settings.fov + FOV_STEP, FOV_MIN, FOV_MAX)
                    continue
                if chkey == ord("3"):
                    settings.fov = FOV_DEFAULT
                    continue

                # Shadows toggle
                if chkey == ord("4"):
                    settings.shadows = "off" if settings.shadows == "on" else "on"
                    continue

                # Camera reset
                if chkey in (ord("r"), ord("R")):
                    player.pitch = 0.0
                    last_mouse_x = None
                    if settings.mode in ("free", "demo_free"):
                        player.vz = 0.0
                    continue

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

                    if settings.mode == "demo_default":
                        demo_path = find_path_cells(grid, (int(player.x), int(player.y)), goal_xy)
                        demo_idx = 0
                    else:
                        demo_path = None

                    last = time.monotonic()
                    if settings.hud == "auto5":
                        hud_until = last + 5.0
                    continue

                if chkey in (ord("m"), ord("M")):
                    show_map = not show_map
                    continue

                if chkey in (ord("q"), ord("Q")):
                    if confirm_yes_no(stdscr, tr, "prompt_exit"):
                        return
                    continue

                # Arrow keys: camera control (always)
                if chkey == curses.KEY_LEFT:
                    rot_dir = -1
                    rot_until = now + HOLD_TIMEOUT
                    continue
                if chkey == curses.KEY_RIGHT:
                    rot_dir = 1
                    rot_until = now + HOLD_TIMEOUT
                    continue
                if chkey == curses.KEY_UP:
                    pitch_dir = -1
                    pitch_until = now + HOLD_TIMEOUT
                    continue
                if chkey == curses.KEY_DOWN:
                    pitch_dir = 1
                    pitch_until = now + HOLD_TIMEOUT
                    continue

                if settings.mode in ("default", "free"):
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

                    if settings.mode == "free":
                        if chkey == ord(" "):
                            vert_dir = 1
                            vert_until = now + HOLD_TIMEOUT
                        elif chkey in (ord("x"), ord("X")):
                            vert_dir = -1
                            vert_until = now + HOLD_TIMEOUT
                        elif chkey == curses.KEY_PPAGE:
                            vert_dir = 1
                            vert_until = now + HOLD_TIMEOUT
                        elif chkey == curses.KEY_NPAGE:
                            vert_dir = -1
                            vert_until = now + HOLD_TIMEOUT

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

            if now > move_until:
                move_dir = 0
            if now > rot_until:
                rot_dir = 0
            if now > pitch_until:
                pitch_dir = 0
            if now > vert_until:
                vert_dir = 0

            if pitch_dir:
                player.pitch = clamp(player.pitch + pitch_dir * PITCH_SPEED * dt, -PITCH_MAX, PITCH_MAX)

            if rot_dir and settings.mode in ("default", "free"):
                player.ang = normalize_angle(player.ang + rot_dir * ROT_SPEED * dt)
            elif rot_dir and settings.mode in ("demo_default", "demo_free"):
                player.ang = normalize_angle(player.ang + rot_dir * ROT_SPEED * dt * 0.6)

            if settings.mode == "demo_default":
                if demo_path is None:
                    demo_path = find_path_cells(grid, (int(player.x), int(player.y)), goal_xy)
                    demo_idx = 0
                demo_idx = demo_walk_step(grid, player, demo_path, demo_idx, dt)
                player.z = 0.0
                player.vz = 0.0
            elif settings.mode == "demo_free":
                demo_free_step(grid, player, goal_xy, dt)
            elif settings.mode == "default":
                if move_dir:
                    move_horizontal_default(grid, player, forward=move_dir, dt=dt)
                player.z = 0.0
                player.vz = 0.0
            elif settings.mode == "free":
                update_free_vertical(grid, player, vert_dir, dt)
                if move_dir:
                    move_horizontal_free(grid, player, forward=move_dir, dt=dt)

            gx, gy = goal_xy
            if int(player.x) == gx and int(player.y) == gy:
                seconds = time.monotonic() - start_time
                wait = settings.mode not in ("demo_default", "demo_free")
                win_screen(stdscr, tr, seconds, wait=wait)
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
