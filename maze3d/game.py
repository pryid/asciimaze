"""Main game loop and curses entrypoint.

The runtime is split into three phases per frame:
- input: read keys/mouse and update intent/state
- update: simulate player motion/camera and check win conditions
- render: draw either 3D scene or minimap
"""

from __future__ import annotations
from typing import Optional

import curses
import locale
import random
import time
from collections.abc import Callable
from dataclasses import dataclass

from .constants import (
    FOV_DEFAULT,
    FOV_MAX,
    FOV_MIN,
    FOV_STEP,
    HOLD_TIMEOUT,
    PITCH_MAX,
    PITCH_SPEED,
    ROT_SPEED,
)
from .i18n import make_tr
from .maze import difficulty_to_size, find_path_cells, generate_maze, resolve_floor_collision
from .models import Player, Settings
from .movement import (
    demo_free_step,
    demo_walk_step,
    move_horizontal_default,
    move_horizontal_free,
    update_free_vertical,
)
from .render import choose_renderer, render_map, render_scene
from .style import Style, detect_caps, effective_style, init_style
from .ui import confirm_yes_no, run_menu, set_mouse_tracking, win_screen
from .util import clamp, normalize_angle


@dataclass
class ControlState:
    """Transient controls driven by key holds and mouse."""

    move_dir: int = 0
    rot_dir: int = 0
    pitch_dir: int = 0
    vert_dir: int = 0

    move_until: float = 0.0
    rot_until: float = 0.0
    pitch_until: float = 0.0
    vert_until: float = 0.0

    last_mouse_x: Optional[int] = None


@dataclass
class LevelState:
    """All state tied to a single generated level."""

    grid: list[str]
    goal_xy: tuple[int, int]
    player: Player

    show_map: bool = False

    demo_path: Optional[list[tuple[int, int]]] = None
    demo_idx: int = 0

    start_time: float = 0.0
    hud_until: float = 0.0
    last_tick: float = 0.0

    restart_level: bool = False


def _configure_mouse(settings: Settings, mouse_possible: bool) -> bool:
    """Apply mouse tracking based on settings. Returns whether mouse is active."""
    if settings.mouse_look == "off":
        set_mouse_tracking(False)
        return False
    if settings.mouse_look == "on":
        return mouse_possible and set_mouse_tracking(True)
    # "auto": enable if possible
    return mouse_possible and set_mouse_tracking(True)


def _new_level(
    settings: Settings, base_style, rng: random.Random, mouse_possible: bool
) -> tuple[LevelState, Style, bool]:
    """Generate a new maze + initialize player, style and mouse tracking."""
    cw, ch = difficulty_to_size(settings.difficulty)
    grid = generate_maze(cw, ch, rng)
    goal_xy = (2 * (cw - 1) + 1, 2 * (ch - 1) + 1)

    style = effective_style(base_style, settings)
    mouse_active = _configure_mouse(settings, mouse_possible)

    player = Player(x=1.5, y=1.5, z=0.0, ang=0.0, pitch=0.0, vz=0.0)
    resolve_floor_collision(grid, player)

    demo_path: Optional[list[tuple[int, int]]] = None
    demo_idx = 0
    if settings.mode == "demo_default":
        demo_path = find_path_cells(grid, (int(player.x), int(player.y)), goal_xy)
        demo_idx = 0

    now = time.monotonic()
    hud_until = now + 5.0

    state = LevelState(
        grid=grid,
        goal_xy=goal_xy,
        player=player,
        show_map=False,
        demo_path=demo_path,
        demo_idx=demo_idx,
        start_time=now,
        hud_until=hud_until,
        last_tick=now,
        restart_level=False,
    )
    return state, style, mouse_active


def _hud_visible(settings: Settings, now: float, hud_until: float) -> bool:
    if settings.hud == "always":
        return True
    if settings.hud == "off":
        return False
    return now < hud_until


def _read_input(
    stdscr,
    tr: Callable[[str], str],
    base_style,
    caps,
    settings: Settings,
    level: LevelState,
    ctrl: ControlState,
    style: Style,
    mouse_possible: bool,
    mouse_active: bool,
    now: float,
) -> tuple[str, Style, bool]:
    """Consume all pending input events.

    Returns (action, new_style, new_mouse_active) where action is one of:
    - "continue" (default)
    - "restart"
    - "quit"
    """

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
            level.player.pitch = 0.0
            ctrl.last_mouse_x = None
            if settings.mode in ("free", "demo_free"):
                level.player.vz = 0.0
            continue

        # ESC: pause menu
        if chkey == 27:
            menu_action = run_menu(stdscr, base_style, caps, settings, mode="pause")
            if menu_action == "quit":
                return "quit", style, mouse_active
            if menu_action == "restart":
                return "restart", style, mouse_active

            # Re-apply derived state after settings changes.
            style = effective_style(base_style, settings)
            mouse_active = _configure_mouse(settings, mouse_possible)

            if settings.mode == "demo_default":
                level.demo_path = find_path_cells(
                    level.grid, (int(level.player.x), int(level.player.y)), level.goal_xy
                )
                level.demo_idx = 0
            else:
                level.demo_path = None

            level.last_tick = time.monotonic()
            if settings.hud == "auto5":
                level.hud_until = level.last_tick + 5.0
            continue

        # Map toggle
        if chkey in (ord("m"), ord("M")):
            level.show_map = not level.show_map
            continue

        # Quit confirm
        if chkey in (ord("q"), ord("Q")):
            if confirm_yes_no(stdscr, tr, "prompt_exit"):
                return "quit", style, mouse_active
            continue

        # Arrow keys: camera control (always)
        if chkey == curses.KEY_LEFT:
            ctrl.rot_dir = -1
            ctrl.rot_until = now + HOLD_TIMEOUT
            continue
        if chkey == curses.KEY_RIGHT:
            ctrl.rot_dir = 1
            ctrl.rot_until = now + HOLD_TIMEOUT
            continue
        if chkey == curses.KEY_UP:
            ctrl.pitch_dir = -1
            ctrl.pitch_until = now + HOLD_TIMEOUT
            continue
        if chkey == curses.KEY_DOWN:
            ctrl.pitch_dir = 1
            ctrl.pitch_until = now + HOLD_TIMEOUT
            continue

        # WASD + vertical motion (depending on mode)
        if settings.mode in ("default", "free"):
            if chkey in (ord("w"), ord("W")):
                ctrl.move_dir = 1
                ctrl.move_until = now + HOLD_TIMEOUT
                continue
            if chkey in (ord("s"), ord("S")):
                ctrl.move_dir = -1
                ctrl.move_until = now + HOLD_TIMEOUT
                continue
            if chkey in (ord("a"), ord("A")):
                ctrl.rot_dir = -1
                ctrl.rot_until = now + HOLD_TIMEOUT
                continue
            if chkey in (ord("d"), ord("D")):
                ctrl.rot_dir = 1
                ctrl.rot_until = now + HOLD_TIMEOUT
                continue

            if settings.mode == "free":
                if chkey == ord(" "):
                    ctrl.vert_dir = 1
                    ctrl.vert_until = now + HOLD_TIMEOUT
                    continue
                if chkey in (ord("x"), ord("X")):
                    ctrl.vert_dir = -1
                    ctrl.vert_until = now + HOLD_TIMEOUT
                    continue
                if chkey == curses.KEY_PPAGE:
                    ctrl.vert_dir = 1
                    ctrl.vert_until = now + HOLD_TIMEOUT
                    continue
                if chkey == curses.KEY_NPAGE:
                    ctrl.vert_dir = -1
                    ctrl.vert_until = now + HOLD_TIMEOUT
                    continue

        # Mouse look
        if chkey == curses.KEY_MOUSE and mouse_active:
            try:
                _id, mx, _my, _mz, bstate = curses.getmouse()
            except Exception:
                continue

            if hasattr(curses, "REPORT_MOUSE_POSITION") and (bstate & curses.REPORT_MOUSE_POSITION):
                if ctrl.last_mouse_x is not None:
                    dxm = mx - ctrl.last_mouse_x
                    if dxm:
                        level.player.ang = normalize_angle(
                            level.player.ang + dxm * settings.mouse_sens
                        )
                ctrl.last_mouse_x = mx
            else:
                ctrl.last_mouse_x = mx

    return "continue", style, mouse_active


def _expire_controls(ctrl: ControlState, now: float) -> None:
    if now > ctrl.move_until:
        ctrl.move_dir = 0
    if now > ctrl.rot_until:
        ctrl.rot_dir = 0
    if now > ctrl.pitch_until:
        ctrl.pitch_dir = 0
    if now > ctrl.vert_until:
        ctrl.vert_dir = 0


def _update_simulation(
    settings: Settings, level: LevelState, ctrl: ControlState, dt: float
) -> None:
    """Update player motion/camera based on settings and current control state."""
    player = level.player

    if ctrl.pitch_dir:
        player.pitch = clamp(
            player.pitch + ctrl.pitch_dir * PITCH_SPEED * dt, -PITCH_MAX, PITCH_MAX
        )

    if ctrl.rot_dir and settings.mode in ("default", "free"):
        player.ang = normalize_angle(player.ang + ctrl.rot_dir * ROT_SPEED * dt)
    elif ctrl.rot_dir and settings.mode in ("demo_default", "demo_free"):
        player.ang = normalize_angle(player.ang + ctrl.rot_dir * ROT_SPEED * dt * 0.6)

    if settings.mode == "demo_default":
        if level.demo_path is None:
            level.demo_path = find_path_cells(
                level.grid, (int(player.x), int(player.y)), level.goal_xy
            )
            level.demo_idx = 0
        level.demo_idx = demo_walk_step(level.grid, player, level.demo_path, level.demo_idx, dt)
        player.z = 0.0
        player.vz = 0.0
    elif settings.mode == "demo_free":
        demo_free_step(level.grid, player, level.goal_xy, dt)
    elif settings.mode == "default":
        if ctrl.move_dir:
            move_horizontal_default(level.grid, player, forward=ctrl.move_dir, dt=dt)
        player.z = 0.0
        player.vz = 0.0
    elif settings.mode == "free":
        update_free_vertical(level.grid, player, ctrl.vert_dir, dt)
        if ctrl.move_dir:
            move_horizontal_free(level.grid, player, forward=ctrl.move_dir, dt=dt)


def _check_win(level: LevelState) -> bool:
    gx, gy = level.goal_xy
    return int(level.player.x) == gx and int(level.player.y) == gy


def _render_frame(
    stdscr,
    tr: Callable[[str], str],
    level: LevelState,
    settings: Settings,
    style: Style,
    hud_visible: bool,
    mouse_active: bool,
) -> None:
    stdscr.erase()
    if level.show_map:
        render_map(stdscr, tr, level.grid, level.player, level.goal_xy, settings, style)
    else:
        renderer = choose_renderer(settings, style)
        render_scene(
            stdscr,
            tr,
            renderer,
            level.grid,
            level.player,
            level.goal_xy,
            settings,
            style,
            hud_visible,
            mouse_active,
        )
    stdscr.refresh()


def main(stdscr) -> None:
    # curses setup
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
        level, style, mouse_active = _new_level(settings, base_style, rng, mouse_possible)
        ctrl = ControlState()

        stdscr.nodelay(True)
        level.restart_level = False

        while True:
            now = time.monotonic()
            dt = now - level.last_tick
            level.last_tick = now

            tr = make_tr(settings.language)
            hud_visible = _hud_visible(settings, now, level.hud_until)

            action, style, mouse_active = _read_input(
                stdscr,
                tr,
                base_style,
                caps,
                settings,
                level,
                ctrl,
                style,
                mouse_possible,
                mouse_active,
                now,
            )
            if action == "quit":
                return
            if action == "restart":
                break

            _expire_controls(ctrl, now)
            _update_simulation(settings, level, ctrl, dt)

            if _check_win(level):
                seconds = time.monotonic() - level.start_time
                wait = settings.mode not in ("demo_default", "demo_free")
                win_screen(stdscr, tr, seconds, wait=wait)
                break

            _render_frame(stdscr, tr, level, settings, style, hud_visible, mouse_active)

            time.sleep(0.01)


def run() -> None:
    try:
        locale.setlocale(locale.LC_ALL, "")
    except Exception:
        pass
    curses.wrapper(main)