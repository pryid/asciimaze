# -*- coding: utf-8 -*-
"""Main game loop and curses entrypoint."""
from __future__ import annotations

import curses
import locale
import random
import time
from typing import List, Optional, Tuple

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
from .style import detect_caps, effective_style, init_style
from .ui import confirm_yes_no, run_menu, set_mouse_tracking, win_screen
from .util import clamp, normalize_angle


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
