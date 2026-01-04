# 3D Maze in Terminal (Raycasting) — Refactored

This project is a modular refactor of the single-file `main.py` version.

## Run

From the project folder:

```bash
python main.py
```

Or using the module entrypoint:

```bash
python -m maze3d
```

> Note: `curses` must be available (Linux/macOS terminals usually OK).

## Controls (in game)

- `W/S` — move forward/back
- `A/D` — turn (in default/free modes)
- Arrow keys — camera yaw/pitch
- `R` — reset camera pitch
- `M` — toggle map
- `1/2/3` — FOV -, FOV +, reset to 60°
- `4` — toggle shadows
- `ESC` — menu
- `Q` — quit

Free mode:
- `Space` — up
- `X` — down
- `PageUp/PageDown` — up/down

## Code layout

- `maze3d/constants.py` — constants and literal types
- `maze3d/i18n.py` — localization dictionaries + helpers
- `maze3d/models.py` — dataclasses (`Player`, `Settings`)
- `maze3d/util.py` — tiny helpers (`clamp`, `normalize_angle`, `safe_addstr`)
- `maze3d/style.py` — terminal capabilities + colors/unicode style
- `maze3d/maze.py` — maze generation + grid/collision helpers
- `maze3d/raycast.py` — raycasting + projection helpers
- `maze3d/movement.py` — movement + demo/autosolve logic
- `maze3d/render.py` — rendering facade (dispatcher)
- `maze3d/render_common.py` — HUD + renderer selection helpers
- `maze3d/render_text.py` — text renderer
- `maze3d/render_halfblock.py` — half-block renderer
- `maze3d/render_braille.py` — braille renderer
- `maze3d/render_map.py` — minimap renderer
- `maze3d/ui.py` — menu + prompts + win screen
- `maze3d/game.py` — main loop + `run()`
