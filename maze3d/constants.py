# -*- coding: utf-8 -*-
"""Project-wide constants and type aliases for the 3D terminal maze."""
from __future__ import annotations

import math
from typing import Literal

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
