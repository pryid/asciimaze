# Terminal 3D Maze (Raycasting)

A small terminal game that renders a randomly generated maze in pseudo-3D using raycasting.
It includes an in-game settings menu, multiple rendering backends, optional demo auto-solve,
and basic localization (English by default, Russian optional).

## Features

- **Raycasting pseudo-3D** view rendered in a terminal (curses).
- **Random perfect maze** generation (guaranteed solvable each run).
- **Settings / menu (ESC)** with runtime toggles:
  - Renderer selection: `text`, `half`, `braille`, `auto`
  - Color / Unicode: `on/off/auto` (best-effort)
  - Mouse look: `on/off/auto` (terminal-dependent)
  - HUD mode and visibility behavior
  - FOV and mouse sensitivity
  - Difficulty (maze size scaling)
  - Game mode: `play` or `demo`
  - Language: `en` / `ru`
- **Full-screen map view** (`M`) for navigation.
- **Demo mode**: automatically finds a path and walks it to the goal.

## Requirements

- Python 3 (recommended: 3.8+)
- A Unix-like terminal with `curses` support (Linux/macOS are the best experience)
- For best visuals: UTF-8 + 256 colors terminal

### Windows notes
Python on Windows does not ship with `curses` by default. You may need:

```bash
pip install windows-curses
```

## Quick start

```bash
python3 main.py
```

Tip: you can rename the file to `maze3d.py` if you prefer—entrypoint is the script itself.

## Controls

In game:

- `W` / `S` — move forward / back
- `A` / `D` — turn left / right
- `M` — map
- `ESC` — settings / menu
- `Q` — quit (with Y/N confirmation)

## Render modes

- `text` — classic characters (most compatible)
- `half` — half-block renderer (higher vertical resolution)
- `braille` — braille dots renderer (2x4 “pixels” per cell; requires UTF-8)
- `auto` — selects the best available based on terminal capabilities

## Demo mode

Enable **Demo** in the start menu to showcase the renderers.
The game will compute a solution path (BFS on the grid) and automatically walk to the exit.

## Troubleshooting

- **“Terminal too small”**: enlarge the terminal window.
- **Broken characters / blocks**: ensure the terminal uses UTF-8 and a font with block/braille glyphs.
- **No colors**: some terminals report limited color support; switch Color to `off` or try another terminal.
- **Mouse look not working**: depends on terminal support for mouse motion reporting.

## Project layout

- `main.py` — the full game (single-file implementation)
