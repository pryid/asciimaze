"""Rendering facade.

This module keeps the public rendering API stable while the actual renderers live
in dedicated modules:
- render_text.py
- render_halfblock.py
- render_braille.py
- render_map.py

Shared helpers (HUD, renderer selection) are in render_common.py.
"""

from __future__ import annotations

from collections.abc import Callable

from .constants import RenderMode
from .models import Player, Settings
from .render_braille import render_braille
from .render_common import choose_renderer, draw_hud
from .render_halfblock import render_halfblock
from .render_map import player_dir_glyph, render_map
from .render_text import render_text
from .style import Style

__all__ = [
    "choose_renderer",
    "draw_hud",
    "render_scene",
    "render_text",
    "render_halfblock",
    "render_braille",
    "player_dir_glyph",
    "render_map",
]


def render_scene(
    stdscr,
    tr: Callable[[str], str],
    renderer: RenderMode,
    grid: list[str],
    player: Player,
    goal_xy: tuple[int, int],
    settings: Settings,
    style: Style,
    hud_visible: bool,
    mouse_active: bool,
) -> None:
    """Dispatch scene rendering to the selected renderer."""
    if renderer == "text":
        render_text(stdscr, tr, grid, player, goal_xy, settings, style, hud_visible, mouse_active)
    elif renderer == "half":
        render_halfblock(
            stdscr, tr, grid, player, goal_xy, settings, style, hud_visible, mouse_active
        )
    elif renderer == "braille":
        render_braille(
            stdscr, tr, grid, player, goal_xy, settings, style, hud_visible, mouse_active
        )
    else:
        render_text(stdscr, tr, grid, player, goal_xy, settings, style, hud_visible, mouse_active)
