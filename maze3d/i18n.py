# -*- coding: utf-8 -*-
"""Localization utilities (English + Russian)."""
from __future__ import annotations

from typing import Callable, Dict


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
