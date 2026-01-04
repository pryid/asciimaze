# -*- coding: utf-8 -*-
"""Core data models (player state, configuration)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .constants import (
    FOV_DEFAULT,
    MOUSE_SENS_DEFAULT,
    Mode,
    RenderMode,
    Shadows,
)


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
