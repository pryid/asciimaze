# ASCII Maze (Terminal 3D Raycasting)

A single-file terminal game that renders a 3D maze using classic raycasting.  
Designed to adapt to different terminal capabilities (UTF-8, colors, mouse reporting) and offer multiple renderers.

## Features

- **3D raycasting** in terminal (curses)
- **Multiple renderers**
  - `text` — classic character-based
  - `half` — half-block rendering (2 vertical “pixels” per cell)
  - `braille` — braille dots (2×4 “pixels” per cell, requires UTF-8)
  - `auto` — picks the best available renderer
- **In-game settings menu (ESC)**
  - Change renderer, difficulty, language, HUD mode, mouse look, FOV, shadows, etc.
- **Modes**
  - `default` — normal walking
  - `free` — flight mode (vertical movement) with basic collision
  - `demo` variants — auto-solve / auto-walk the maze
- **Camera controls**
  - Runtime FOV adjustment (1/2/3)
  - Camera controls via arrow keys + reset hotkey
- **Optional shading**
  - Toggle shadows on/off for readability and performance

## Requirements

- Python 3.9+ (likely works on older 3.x too)
- A terminal that supports `curses`
- Recommended:
  - UTF-8 locale for braille renderer
  - 256-color terminal for best gradients
  - Mouse reporting support (e.g., kitty) if using mouse-look

## Run

If your file is named `main.py`:

```bash
python3 main.py
```

Or if you renamed it:

```bash
python3 maze.py
```

## Controls (Default)

- **W / S** — move forward / backward  
- **A / D** — turn left / right  
- **Arrow keys** — camera control  
- **R** — reset camera orientation  
- **M** — map  
- **1 / 2 / 3** — decrease / increase / reset FOV  
- **4** — toggle shadows  
- **ESC** — settings menu  
- **Q** — quit (with confirmation)

### Free mode

- **Space** — move up  
- **X** — move down

## Tips / Troubleshooting

- If braille renderer looks broken, ensure your locale is UTF-8:

  ```bash
  locale
  ```

- If colors are odd, try a different terminal theme or disable color in the menu.
- If mouse look does not work, your terminal might not support mouse motion events.
  Switch mouse look to `off` in settings.

## Development Notes

- The project is intentionally kept as a single script for easy distribution.
- The menu is designed to be usable without a mouse and work on narrow terminals.
