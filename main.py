#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D maze in terminal (raycasting).

This is the refactored (modular) entrypoint. Run:

    python main.py

or, from the project root:

    python -m maze3d
"""
from __future__ import annotations

from maze3d.game import run

if __name__ == "__main__":
    run()
