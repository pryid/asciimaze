# -*- coding: utf-8 -*-
"""Shared rendering helpers (HUD, renderer selection)."""
from __future__ import annotations

import curses
import math
from typing import Callable, Tuple

from .constants import RenderMode
from .i18n import option_display
from .models import Player, Settings
from .style import Style
from .util import safe_addstr


def choose_renderer(settings: Settings, style: Style) -> RenderMode:
    """Resolve effective renderer mode based on settings + terminal capabilities."""
    if settings.render_mode != "auto":
        if settings.render_mode in ("half", "braille") and not style.unicode_ok:
            return "text"
        return settings.render_mode
    return "braille" if style.unicode_ok else "text"


def draw_hud(
    stdscr,
    tr: Callable[[str], str],
    player: Player,
    goal_xy: Tuple[int, int],
    settings: Settings,
    style: Style,
    mouse_active: bool,
) -> None:
    """Draw 2-line HUD at the bottom of the screen."""
    h, w = stdscr.getmaxyx()

    gx, gy = goal_xy
    dist_goal = math.hypot((gx + 0.5) - player.x, (gy + 0.5) - player.y)

    is_free = settings.mode in ("free", "demo_free")
    line1 = tr("hud_line1_free") if is_free else tr("hud_line1_default")

    tags: list[str] = []
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
